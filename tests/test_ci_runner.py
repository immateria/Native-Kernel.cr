"""Contract tests for the managed native qualifier; no Darwin compiler required."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("native_ci_runner", ROOT / "scripts/ci/runner.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class RunnerContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nk-ci-test-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.profile = {"os_major": 15, "darwin_major": 24, "architecture": "arm64"}
        self.host = {"system": "Darwin", "os_version": "15.4.1", "darwin_release": "24.4.0",
                     "architecture": "arm64", "hardware_arm64": True, "translated": False}

    def test_unknown_and_forged_profile_are_rejected(self):
        profiles, _ = runner.load_config(ROOT)
        with self.assertRaises(runner.QualificationError):
            runner.select_profile(profiles, "macos-16-arm64")
        profiles["profiles"]["macos-15-arm64"]["darwin_major"] = 25
        with self.assertRaises(runner.QualificationError):
            runner.select_profile(profiles, "macos-15-arm64")

    def test_host_os_kernel_arch_and_translation_must_match(self):
        runner.validate_host(self.host, self.profile)
        for field, value in (("system", "Linux"), ("os_version", "26.0"),
                             ("darwin_release", "25.0.0"), ("architecture", "x86_64"),
                             ("translated", True)):
            with self.subTest(field=field):
                changed = dict(self.host, **{field: value})
                with self.assertRaises(runner.QualificationError):
                    runner.validate_host(changed, self.profile)

    def test_translation_exception_is_local_and_explicit(self):
        profile = dict(self.profile, architecture="x86_64")
        runner.validate_host(self.host, profile, allow_translation=True, ci=False)
        with self.assertRaises(runner.QualificationError):
            runner.validate_host(self.host, profile, allow_translation=True, ci=True)

    def test_timeout_kills_process_group_and_bounds_output(self):
        result = runner.run_bounded([sys.executable, "-c", "import time; print('x'*10000, flush=True); time.sleep(5)"],
                                    self.directory / "timeout", timeout=0.15, output_limit=128)
        self.assertEqual(result["status"], "timed_out")
        self.assertLessEqual((self.directory / "timeout.stdout").stat().st_size, 128)
        self.assertTrue(result["output_truncated"])

    def test_crash_and_missing_completion_are_distinct(self):
        result = runner.run_bounded([sys.executable, "-c", "import os,signal; os.kill(os.getpid(),signal.SIGTERM)"],
                                    self.directory / "crash", timeout=2)
        self.assertEqual(result["status"], "crashed")
        expected = {"id": "resource", "minimum_darwin": 22, "exit_code": 0,
                    "stdout": "NK_OK resource\n", "stderr": ""}
        result = runner.run_bounded([sys.executable, "-c", "pass"], self.directory / "missing", timeout=2)
        self.assertEqual(runner.classify_case(result, expected, 24)["status"], "incomplete")

    def test_unsupported_is_only_a_declared_kernel_gap(self):
        expected = {"id": "audit", "minimum_darwin": 24, "exit_code": 0,
                    "stdout": "NK_OK audit\n", "stderr": ""}
        completed = {"status": "passed", "exit_code": 77, "stdout": "", "stderr": "", "output_truncated": False}
        self.assertEqual(runner.classify_case(completed, expected, 23)["status"], "unsupported")
        self.assertEqual(runner.classify_case(completed, expected, 24)["status"], "failed")

    def test_exact_completion_and_stderr_are_required(self):
        expected = {"id": "signal", "minimum_darwin": 22, "exit_code": 0,
                    "stdout": "NK_OK signal\n", "stderr": "S"}
        result = {"status": "passed", "exit_code": 0, "stdout": "NK_OK signal\n", "stderr": "S", "output_truncated": False}
        self.assertEqual(runner.classify_case(result, expected, 24)["status"], "passed")
        result["stderr"] = ""
        self.assertEqual(runner.classify_case(result, expected, 24)["status"], "failed")

    def test_only_all_required_successes_can_pass(self):
        for status in ("unsupported", "incomplete", "crashed", "timed_out", "failed"):
            self.assertFalse(runner.all_passed([{"status": "passed"}, {"status": status}]))
        self.assertFalse(runner.all_passed([]))
        self.assertTrue(runner.all_passed([{"status": "passed"}]))

    def test_replay_rejects_wrong_source_arch_or_origin(self):
        receipt = {"status": "passed", "mode": "qualify", "profile": "macos-15-arm64",
                   "profile_definition": self.profile, "source": {"src/a.cr": "abc"}}
        destination = dict(self.profile, os_major=26, darwin_major=25)
        runner.validate_replay_identity(receipt, destination, {"src/a.cr": "abc"})
        for source, profile in (({"src/a.cr": "changed"}, destination),
                                ({"src/a.cr": "abc"}, dict(destination, architecture="x86_64")),
                                ({"src/a.cr": "abc"}, self.profile)):
            with self.assertRaises(runner.QualificationError):
                runner.validate_replay_identity(receipt, profile, source)
        receipt["profile_definition"] = dict(self.profile, os_major=26)
        with self.assertRaises(runner.QualificationError):
            runner.validate_replay_identity(receipt, destination, {"src/a.cr": "abc"})

    def test_bundle_tamper_and_escaping_paths_are_rejected(self):
        executable = self.directory / "fixture"
        executable.write_bytes(b"original")
        manifest = {"fixture": runner.sha256_file(executable)}
        runner.verify_bundle_files(self.directory, manifest)
        executable.write_bytes(b"tampered")
        with self.assertRaises(runner.QualificationError):
            runner.verify_bundle_files(self.directory, manifest)
        with self.assertRaises(runner.QualificationError):
            runner.verify_bundle_files(self.directory, {"../outside": "a"})

    def test_source_identity_includes_nested_inputs_and_detects_additions(self):
        (self.directory / "src").mkdir()
        (self.directory / "src/a.cr").write_text("a")
        before = runner.source_identity(self.directory)
        (self.directory / "scripts/ci").mkdir(parents=True)
        (self.directory / "scripts/ci/new.py").write_text("b")
        self.assertNotEqual(before, runner.source_identity(self.directory))

    def make_runner(self, mode="qualify"):
        root = self.directory / "source"
        root.mkdir()
        (root / "src").mkdir()
        (root / "src/input.cr").write_text("original")
        return runner.Runner(SimpleNamespace(mode=mode, profile="macos-15-arm64",
                                            output=str(self.directory / "output"), allow_translation=False), root=root)

    def test_source_mutation_aborts_a_previously_successful_result(self):
        managed = self.make_runner()
        managed.receipt["stages"] = [{"name": "test", "status": "passed"}]
        managed.receipt["cases"] = [{"status": "passed"}] * 20
        (managed.root / "src/input.cr").write_text("changed")
        self.assertEqual(managed.finish(), 1)
        receipt = json.loads((managed.output / "export/receipt.json").read_text())
        self.assertFalse(receipt["source_unchanged"])
        self.assertEqual(receipt["status"], "failed")

    def test_export_failure_still_writes_failure_receipt(self):
        managed = self.make_runner()
        managed.receipt["artifacts"]["missing"] = {"path": str(self.directory / "missing"), "sha256": "a"}
        self.assertEqual(managed.finish("build failed"), 1)
        receipt = json.loads((managed.output / "export/receipt.json").read_text())
        self.assertEqual(receipt["status"], "failed")
        self.assertIn("export_error", receipt)

    def test_core_manifest_must_match_source_and_executable(self):
        managed = self.make_runner()
        receipt = {"source": {"src/input.cr": "abc"}, "core_manifest": {
            "sources": {"src/input.cr": "abc"}, "assembly": ["exact"],
            "artifacts": {"development.executable": "123"}},
            "artifacts": {"probe-development": {"sha256": "123"}}}
        managed.validate_core_manifest(receipt)
        receipt["artifacts"]["probe-development"]["sha256"] = "tampered"
        with self.assertRaises(runner.QualificationError):
            managed.validate_core_manifest(receipt)
        receipt["artifacts"] = {}
        receipt["source"]["src/input.cr"] = "new source"
        with self.assertRaises(runner.QualificationError):
            managed.validate_core_manifest(receipt)

    def test_incomplete_artifact_roster_cannot_execute(self):
        managed = self.make_runner()
        with self.assertRaises(runner.QualificationError):
            managed.execute_artifacts()

    def test_record_failure_needs_no_compiler_and_is_incomplete(self):
        output = self.directory / "fallback"
        result = runner.run_bounded([sys.executable, "-B", str(ROOT / "scripts/ci/runner.py"),
                                     "record-failure", "--profile", "macos-15-arm64", "--output", str(output),
                                     "--reason", "compiler setup failed", "--exit-code", "9"],
                                    self.directory / "fallback-command", timeout=10)
        self.assertEqual(result["exit_code"], 1)
        receipt = json.loads((output / "export/receipt.json").read_text())
        self.assertEqual(receipt["status"], "incomplete")
        self.assertEqual(receipt["stages"][-1]["exit_code"], 9)

    def test_closed_streams_do_not_kill_live_worker_early(self):
        result = runner.run_bounded([sys.executable, "-c", "import os,time; os.close(1); os.close(2); time.sleep(.15)"],
                                    self.directory / "closed-streams", timeout=2)
        self.assertEqual(result["status"], "passed")
        self.assertGreaterEqual(result["duration_seconds"], .15)

    def test_group_cleanup_precedes_leader_reaping(self):
        events, tracked = [], []
        original_spawn, original_killpg = subprocess.Popen, os.killpg
        def spawn(*args, **kwargs):
            process = original_spawn(*args, **kwargs)
            if not tracked:
                tracked.append(process.pid)
                original_wait = process.wait
                def wait(*args, **kwargs):
                    events.append("wait")
                    return original_wait(*args, **kwargs)
                process.wait = wait
            return process
        def killpg(pid, sig):
            if pid == tracked[0]:
                events.append("killpg")
            return original_killpg(pid, sig)
        with mock.patch.object(runner.subprocess, "Popen", spawn), mock.patch.object(runner.os, "killpg", killpg):
            result = runner.run_bounded([sys.executable, "-c", "pass"], self.directory / "ordered", timeout=2)
        self.assertEqual(result["status"], "passed")
        self.assertLess(events.index("killpg"), events.index("wait"))
        self.assertNotIn("killpg", events[events.index("wait"):])

    def test_exit_before_observer_registration_stays_unreaped(self):
        process = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
        observer = None
        try:
            time.sleep(.1)
            observer = runner.ExitObserver(process.pid)
            self.assertTrue(observer.exited())
            self.assertIsNone(process.returncode)
        finally:
            if observer is not None:
                observer.close()
            process.wait(timeout=2)

    def test_spec_roster_excludes_unmanaged_fixtures(self):
        (self.directory / "spec/native").mkdir(parents=True)
        (self.directory / "spec/b_spec.cr").write_text("b")
        (self.directory / "spec/a_spec.cr").write_text("a")
        (self.directory / "spec/native/behavior.cr").write_text("worker")
        source, files = runner.spec_runner_source(self.directory)
        self.assertEqual(files, ["spec/a_spec.cr", "spec/b_spec.cr"])
        self.assertEqual(source.count("require "), 2)
        self.assertNotIn("behavior.cr", source)

    def test_origin_proof_requires_full_stages_and_native_host(self):
        _, cases = runner.load_config(ROOT)
        origin = {"source": {"a": "b"}, "source_after": {"a": "b"}, "source_unchanged": True,
                  "host": self.host, "stages": [{"name": name, "status": "passed", "exit_code": 0}
                                                for name in runner.required_native_stages()],
                  "cases": [{"case": case["id"], "optimization": optimization,
                             "status": "passed", "completion_observed": True,
                             "exit_code": case["exit_code"], "stdout": case["stdout"], "stderr": case["stderr"]}
                            for optimization in ("development", "release") for case in cases]}
        runner.validate_origin_proof(origin, self.profile, cases)
        saved = origin["stages"]
        origin["stages"] = [{"name": "identity-compiler", "status": "passed", "exit_code": 0}]
        with self.assertRaises(runner.QualificationError):
            runner.validate_origin_proof(origin, self.profile, cases)
        origin["stages"] = saved
        origin["host"] = dict(self.host, translated=True)
        with self.assertRaises(runner.QualificationError):
            runner.validate_origin_proof(origin, self.profile, cases)
        origin["host"] = self.host
        origin["source_after"] = {"a": "changed"}
        with self.assertRaises(runner.QualificationError):
            runner.validate_origin_proof(origin, self.profile, cases)

    def test_unknown_profile_still_emits_a_failure_receipt(self):
        output = self.directory / "unknown"
        result = runner.run_bounded([sys.executable, "-B", str(ROOT / "scripts/ci/runner.py"), "qualify",
                                     "--compiler", "/no/compiler", "--profile", "forged", "--output", str(output)],
                                    self.directory / "unknown-command", timeout=10)
        self.assertEqual(result["exit_code"], 1)
        receipt = json.loads((output / "export/receipt.json").read_text())
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual(receipt["cases"], [])


if __name__ == "__main__":
    unittest.main()
