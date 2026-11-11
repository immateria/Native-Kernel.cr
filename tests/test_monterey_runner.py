import ast
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("monterey_runner", ROOT / "scripts/compat/monterey_runner.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class RunnerContracts(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="monterey-runner-tests-")
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name).resolve()
        self.bundle = self.base / "bundle"
        self.bundle.mkdir()
        self.output = self.base / "results"
        self.output.mkdir()
        (self.bundle / "monterey_runner.py").write_text("# shipped runner\n")
        (self.bundle / "README.md").write_text("fixture\n")
        (self.bundle / "bin").mkdir()
        builds = []
        for name, (compiler, optimization) in runner.BUILD_ROSTER.items():
            build = {"name": name, "compiler_version": compiler, "optimization": optimization,
                     "path": "bin/probe-" + name, "exec_path": "bin/exec-" + name}
            for key in ("path", "exec_path"):
                path = self.bundle / build[key]
                path.write_text("#!/bin/sh\nexit 0\n")
                path.chmod(0o700)
            builds.append(build)
        files = {str(path.relative_to(self.bundle)): runner.digest(path)
                 for path in self.bundle.rglob("*") if path.is_file()}
        self.manifest = {"schema": 1, "expected_host": runner.EXPECTED_HOST.copy(), "files": files,
                         "builds": builds, "cases": [{"id": name, "exit_code": value[0], "stdout": value[1], "stderr": value[2]}
                                                      for name, value in runner.CASE_ROSTER.items()]}
        self.save_manifest()
        self.host = dict(runner.EXPECTED_HOST, system="Darwin", hardware_arm64=False, translated=False)

    def save_manifest(self):
        (self.bundle / "manifest.json").write_text(json.dumps(self.manifest))

    def run_success(self, command, cwd):
        rc, stdout, stderr = runner.CASE_ROSTER[command[1]]
        return {"status": "completed", "exit_code": rc, "stdout": stdout, "stderr": stderr, "started": True,
                "completion_observed": True, "output_truncated": False, "timed_out": False, "cleanup": "already-absent"}

    def quiet_run(self, preflight=False, side_effect=None, host=None):
        with mock.patch.object(runner, "identify_host", return_value=host or self.host), \
                mock.patch.object(runner, "run_bounded", side_effect=side_effect or self.run_success), \
                contextlib.redirect_stdout(io.StringIO()):
            return runner.run_bundle(self.bundle, self.output, preflight)

    def test_accepts_reviewed_manifest_and_detects_payload_mutation(self):
        manifest = runner.load_manifest(self.bundle)
        stamp = runner.digest(self.bundle / "manifest.json")
        self.assertEqual(runner.verify_payload(self.bundle, manifest, stamp), manifest["files"])
        (self.bundle / "README.md").write_text("changed")
        with self.assertRaisesRegex(runner.ProbeError, "Payload hash mismatch"):
            runner.verify_payload(self.bundle, manifest, stamp)

    def test_manifest_mutation_is_separate_from_payload_mutation(self):
        manifest = runner.load_manifest(self.bundle)
        stamp = runner.digest(self.bundle / "manifest.json")
        (self.bundle / "manifest.json").write_text("{}")
        with self.assertRaisesRegex(runner.ProbeError, "Manifest changed"):
            runner.verify_payload(self.bundle, manifest, stamp)

    def test_path_traversal_normalization_and_symlinks_are_refused(self):
        for path in ("../README.md", "/README.md", "bin/../README.md", "bin//probe", "./README.md", "bin\\probe"):
            with self.subTest(path=path), self.assertRaises(runner.ProbeError):
                runner.payload_path(self.bundle, path)
        (self.bundle / "link").symlink_to(self.bundle / "README.md")
        with self.assertRaisesRegex(runner.ProbeError, "Symlink"):
            runner.payload_path(self.bundle, "link")
        (self.bundle / "linked").symlink_to(self.bundle / "bin", target_is_directory=True)
        with self.assertRaisesRegex(runner.ProbeError, "Symlink"):
            runner.payload_path(self.bundle, "linked/probe-current-release")

    def test_manifest_contracts_cannot_silently_drop_a_build_or_case(self):
        for key in ("builds", "cases"):
            original = copy.deepcopy(self.manifest)
            self.manifest[key].pop()
            self.save_manifest()
            with self.subTest(key=key), self.assertRaises(runner.ProbeError):
                runner.load_manifest(self.bundle)
            self.manifest = original
        self.manifest["cases"][0]["stdout"] = "new meaning"
        self.save_manifest()
        with self.assertRaisesRegex(runner.ProbeError, "case contract"):
            runner.load_manifest(self.bundle)

    def test_duplicate_manifest_keys_and_forged_target_are_refused(self):
        (self.bundle / "manifest.json").write_text('{"schema":1,"schema":1}')
        with self.assertRaisesRegex(runner.ProbeError, "Duplicate"):
            runner.load_manifest(self.bundle)
        self.manifest["expected_host"]["os_version"] = "15.4.1"
        self.save_manifest()
        with self.assertRaisesRegex(runner.ProbeError, "reviewed Monterey"):
            runner.load_manifest(self.bundle)

    def test_output_cannot_be_inside_bundle_or_any_source_checkout(self):
        with self.assertRaises(runner.ProbeError):
            runner.safe_output(self.bundle / "results", self.bundle)
        repo = self.base / "source"
        repo.mkdir()
        (repo / ".git").write_text("gitdir: somewhere")
        with self.assertRaises(runner.ProbeError):
            runner.safe_output(repo / "results", self.bundle)
        self.assertEqual(runner.safe_output(self.output, self.bundle), self.output)
        with self.assertRaises(FileExistsError):
            runner.create_output(str(self.output), self.bundle)

    def test_default_output_can_be_a_sibling_when_bundle_is_inside_tempdir(self):
        with mock.patch.object(runner.tempfile, "tempdir", str(self.base)):
            result = runner.create_output(None, self.bundle)
        self.assertEqual(result.parent, self.base)
        self.assertNotEqual(result, self.bundle)
        self.assertTrue(result.is_dir())

    def test_host_refusal_runs_no_probe_and_still_archives_failure(self):
        wrong = dict(self.host, os_build="different")
        with mock.patch.object(runner, "identify_host", return_value=wrong), \
                mock.patch.object(runner, "run_bounded") as execute, contextlib.redirect_stdout(io.StringIO()):
            result = runner.run_bundle(self.bundle, self.output)
        execute.assert_not_called()
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["target_runtime_observed"])
        self.assertFalse(result["target_qualified"])
        archive = runner.archive_results(self.output)
        with zipfile.ZipFile(archive) as z:
            receipt = json.loads(z.read("results/receipt.json"))
        self.assertEqual(receipt["status"], "failed")

    def test_all_thirty_two_cases_required_for_native_target_pass(self):
        result = self.quiet_run()
        self.assertEqual(result["status"], "passed")
        self.assertTrue(result["target_runtime_observed"])
        self.assertTrue(result["target_qualified"])
        self.assertTrue(result["source_unchanged"])
        self.assertEqual(len(result["cases"]), 32)
        self.assertTrue(all(case["status"] == "passed" for case in result["cases"]))

    def test_preflight_on_arm_host_is_always_unqualified_and_artifacts_translated(self):
        arm = dict(self.host, architecture="arm64", hardware_arm64=True, translated=False, os_version="15.4.1")
        result = self.quiet_run(preflight=True, host=arm)
        self.assertEqual(result["status"], "preflight_passed")
        self.assertFalse(result["target_runtime_observed"])
        self.assertFalse(result["target_qualified"])
        self.assertTrue(result["artifact_execution_translated"])
        with self.assertRaises(runner.ProbeError):
            runner.require_host(arm, False)

    def test_positive_translation_survives_failed_hardware_query(self):
        translated = dict(self.host, hardware_arm64=False, translated=True)
        result = self.quiet_run(preflight=True, host=translated)
        self.assertTrue(result["artifact_execution_translated"])
        self.assertFalse(result["target_qualified"])

    def test_archive_failure_revokes_qualification_but_keeps_runtime_observation(self):
        result = {"status": "passed", "target_qualified": True, "target_runtime_observed": True}
        with mock.patch.object(runner, "create_output", return_value=self.output), \
                mock.patch.object(runner, "run_bundle", return_value=result), \
                mock.patch.object(runner, "archive_results", side_effect=OSError("injected archive failure")), \
                contextlib.redirect_stderr(io.StringIO()):
            code = runner.main([], bundle_root=self.bundle)
        self.assertEqual(code, 1)
        receipt = json.loads((self.output / "receipt.json").read_text())
        self.assertEqual(receipt["status"], "failed")
        self.assertFalse(receipt["target_qualified"])
        self.assertTrue(receipt["target_runtime_observed"])

    def test_one_wrong_result_fails_complete_campaign_but_target_is_observed(self):
        def wrong(command, cwd):
            result = self.run_success(command, cwd)
            if command[1] == "session":
                result["stdout"] = "wrong\n"
            return result
        result = self.quiet_run(side_effect=wrong)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["target_runtime_observed"])
        self.assertFalse(result["target_qualified"])
        self.assertEqual(sum(case["status"] == "wrong_result" for case in result["cases"]), 4)

    def test_mid_campaign_payload_mutation_stops_further_execution(self):
        def changed(command, cwd):
            (self.bundle / "README.md").write_text("changed")
            return self.run_success(command, cwd)
        result = self.quiet_run(side_effect=changed)
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["source_unchanged"])
        self.assertTrue(result["target_runtime_observed"])
        self.assertEqual(len(result["cases"]), 1)
        self.assertIn("Payload hash mismatch", result["error"])

    def test_runner_parses_as_python_38(self):
        ast.parse((ROOT / "scripts/compat/monterey_runner.py").read_text(), feature_version=(3, 8))


class BoundedCapture(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="monterey-capture-tests-")
        self.addCleanup(self.directory.cleanup)
        self.cwd = Path(self.directory.name)

    def execute(self, code, **options):
        return runner.run_bounded([sys.executable, "-c", code], self.cwd, **options)

    def test_exact_output_and_nonzero_expected_exit(self):
        result = self.execute("import os;os.write(1,b'NK_EXEC_OK\\n');raise SystemExit(37)")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["exit_code"], 37)
        self.assertEqual(runner.classify_case(result, {"exit_code":37,"stdout":"NK_EXEC_OK\n","stderr":""})["status"], "passed")

    def test_observer_setup_failure_closes_unregistered_pipes(self):
        original_spawn = runner.subprocess.Popen
        created = []
        def spawn(*args, **kwargs):
            process = original_spawn(*args, **kwargs)
            created.append(process)
            return process
        with mock.patch.object(runner.subprocess, "Popen", side_effect=spawn), \
                mock.patch.object(runner, "ExitObserver", side_effect=runner.ProbeError("injected observer error")):
            result = self.execute("import time;time.sleep(10)")
        self.assertEqual(result["status"], "incomplete")
        self.assertTrue(result["completion_observed"])
        self.assertTrue(created[0].stdout.closed)
        self.assertTrue(created[0].stderr.closed)

    def test_timeout_kills_and_collects_leader(self):
        result = self.execute("import time;time.sleep(10)", timeout=0.15)
        self.assertEqual(result["status"], "timed_out")
        self.assertTrue(result["completion_observed"])
        self.assertLess(result["duration_seconds"], 2)

    def test_output_flood_is_bounded_and_not_a_pass(self):
        result = self.execute("import os;os.write(1,b'x'*1000000);os.write(2,b'y'*1000000)", limit=1024)
        self.assertEqual(result["status"], "output_limit")
        self.assertLessEqual(len(result["stdout"].encode()), 1024)
        self.assertLessEqual(len(result["stderr"].encode()), 1024)
        self.assertTrue(result["completion_observed"])

    def test_invalid_utf8_cannot_expand_the_log_beyond_its_bound(self):
        result = self.execute("import os;os.write(1,b'\\xff'*1024)", limit=1024)
        self.assertEqual(result["status"], "output_limit")
        self.assertLessEqual(len(result["stdout"].encode()), 1024)

    @unittest.skipUnless(hasattr(os, "fork"), "requires POSIX process groups")
    def test_inherited_output_writer_is_cleaned_after_leader_exit(self):
        code = "import os,time;child=os.fork();time.sleep(10) if child==0 else None;os._exit(0)"
        original_cleanup = runner.cleanup_group
        def retained_cleanup(process, observer=None):
            self.assertIsNone(process.returncode, "leader must remain unreaped through group cleanup")
            return original_cleanup(process, observer)
        with mock.patch.object(runner, "cleanup_group", side_effect=retained_cleanup) as cleanup:
            result = self.execute(code, timeout=2)
        cleanup.assert_called_once()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["exit_code"], 0)
        self.assertLess(result["duration_seconds"], 1.5)

    def test_permission_cleanup_is_accepted_only_for_observed_unreaped_exit(self):
        process = mock.Mock(pid=123)
        observer = mock.Mock()
        with mock.patch.object(runner.os, "killpg", side_effect=PermissionError("injected")):
            observer.exited.return_value = False
            self.assertTrue(runner.cleanup_group(process, observer).startswith("failed"))
            observer.exited.return_value = True
            self.assertEqual(runner.cleanup_group(process, observer), "exited-zombie")

    def test_crash_is_distinct_from_wrong_native_result(self):
        result = self.execute("import os,signal;os.kill(os.getpid(),signal.SIGKILL)")
        self.assertEqual(result["status"], "crashed")
        self.assertEqual(result["exit_code"], -signal.SIGKILL)


if __name__ == "__main__":
    unittest.main()
