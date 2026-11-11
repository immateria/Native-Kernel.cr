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
                   "profile_definition": self.profile, "source": {"src/a.cr": "abc"},
                   "compiler": self.compiler_identity()}
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

    def compiler_identity(self):
        description = "Crystal 1.22.2 [fixture]\nDefault target: aarch64-apple-macosx11.0\n"
        return {"version": "1.22.2", "description": description,
                "default_target": "aarch64-apple-macosx11.0",
                "invocation": {"path": "/install/bin/crystal", "sha256": "1" * 64},
                "binary": {"path": "/install/embedded/bin/crystal", "sha256": "2" * 64,
                           "resolution": "official-launcher-layout", "architectures": ["x86_64", "arm64"],
                           "version": "1.22.2", "description": description,
                           "default_target": "aarch64-apple-macosx11.0"},
                "identity_scope": "compiler-binary-and-invocation-only"}

    def compiler_fixture(self, name, *, wrapper=True, content=b"\xcf\xfa\xed\xfecompiler-one"):
        install = self.directory / name
        binary = install / "embedded/bin/crystal"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(content)
        binary.chmod(0o700)
        invocation = install / "bin/crystal" if wrapper else binary
        if wrapper:
            invocation.parent.mkdir()
            invocation.write_bytes(b'#!/bin/sh\nexec "$(dirname "$0")/../embedded/bin/crystal" "$@"\n')
            invocation.chmod(0o700)
        return invocation.resolve(), binary.resolve()

    def identify_fixture_compiler(self, invocation, binary=None, *, description=None, binary_description=None,
                                  architectures="x86_64 arm64\n", translated=False):
        managed = self.make_runner()
        managed.args.compiler = str(invocation)
        managed.args.compiler_binary = str(binary) if binary else None
        managed.profile = dict(self.profile, architecture="x86_64") if translated else self.profile
        managed.receipt["translation_exception"] = translated
        managed.receipt["configuration"] = {"compilers": ["1.10.0", "1.22.2"]}
        description = description or self.compiler_identity()["description"]
        def observe(name, command, required=True):
            output = description
            if name == "compiler-binary-architectures":
                output = architectures
            elif name == "compiler-binary":
                output = binary_description or description
                if translated and command[:2] != ["/usr/bin/arch", "-x86_64"]:
                    output = self.compiler_identity()["description"]
            return {"status": "passed", "exit_code": 0, "stdout": output, "stderr": "", "output_truncated": False}
        stop = runner.QualificationError("Identity complete")
        with mock.patch.object(managed, "preflight"), mock.patch.object(managed, "observe", side_effect=observe), \
                mock.patch.object(managed, "stage", side_effect=stop), \
                mock.patch.object(runner, "OFFICIAL_LAUNCHER_SHA256", "0d4ea55c7304564eb4c9cb27650eefea6d37a911ce13f4b59d1a130c3a4b0377", create=True):
            try:
                managed.qualify()
            except runner.QualificationError as error:
                if error is not stop:
                    raise
        return managed.receipt.get("compiler", {})

    def test_official_launcher_and_actual_binary_have_separate_hashes(self):
        invocation, binary = self.compiler_fixture("official")
        identity = self.identify_fixture_compiler(invocation)
        self.assertEqual(identity.get("invocation"), {"path": str(invocation),
                         "sha256": "0d4ea55c7304564eb4c9cb27650eefea6d37a911ce13f4b59d1a130c3a4b0377"})
        self.assertEqual(identity.get("binary", {}).get("path"), str(binary))
        self.assertEqual(identity.get("binary", {}).get("sha256"), "b2e9fde807198bcde6df6dbde53f6d4576c198be2a237ae1333ae9b4c2fdc8af")
        self.assertEqual(identity["binary"]["resolution"], "official-launcher-layout")
        self.assertEqual(identity["binary"]["architectures"], ["x86_64", "arm64"])

    def test_direct_macho_compiler_is_its_own_binary(self):
        invocation, _ = self.compiler_fixture("direct", wrapper=False)
        identity = self.identify_fixture_compiler(invocation)
        self.assertEqual(identity.get("binary", {}).get("path"), str(invocation))
        self.assertEqual(identity["binary"]["resolution"], "direct-mach-o")
        self.assertEqual(identity["invocation"]["sha256"], identity["binary"]["sha256"])

    def test_unknown_wrapper_cannot_masquerade_as_the_compiler_binary(self):
        invocation, _ = self.compiler_fixture("unknown")
        invocation.write_text('#!/bin/sh\nexec /unresolved/crystal "$@"\n')
        with self.assertRaisesRegex(runner.QualificationError, "Cannot resolve actual compiler binary"):
            self.identify_fixture_compiler(invocation)

    def test_explicit_binary_path_resolves_a_local_wrapper(self):
        invocation, binary = self.compiler_fixture("explicit")
        invocation.write_text('#!/bin/sh\nexec /usr/bin/arch -x86_64 /unresolved/crystal "$@"\n')
        identity = self.identify_fixture_compiler(invocation, binary)
        self.assertEqual(identity.get("binary", {}).get("path"), str(binary))
        self.assertEqual(identity["binary"]["resolution"], "explicit-operator-path")

    def test_equal_launchers_do_not_hide_different_compiler_binaries(self):
        invocation, _ = self.compiler_fixture("first")
        first = self.identify_fixture_compiler(invocation)
        # The helper's output/root are per qualification, as in real cells.
        self.directory = self.directory / "second-cell"
        self.directory.mkdir()
        invocation, _ = self.compiler_fixture("second", content=b"\xcf\xfa\xed\xfecompiler-two")
        second = self.identify_fixture_compiler(invocation)
        self.assertEqual(first.get("invocation", {}).get("sha256"), second.get("invocation", {}).get("sha256"))
        self.assertNotEqual(first.get("binary", {}).get("sha256"), second.get("binary", {}).get("sha256"))

    def test_compiler_binary_must_contain_the_qualified_architecture(self):
        invocation, _ = self.compiler_fixture("wrong-arch")
        with self.assertRaisesRegex(runner.QualificationError, "Compiler binary lacks profile architecture"):
            self.identify_fixture_compiler(invocation, architectures="x86_64\n")

    def test_explicit_binary_must_report_the_invocation_version(self):
        invocation, binary = self.compiler_fixture("wrong-version")
        with self.assertRaisesRegex(runner.QualificationError, "Compiler invocation and binary versions differ"):
            self.identify_fixture_compiler(invocation, binary, binary_description="Crystal 1.10.0 [fixture]\nDefault target: aarch64-apple-darwin\n")

    def test_translated_binary_identity_uses_the_qualified_slice(self):
        invocation, binary = self.compiler_fixture("translated")
        description = "Crystal 1.22.2 [fixture]\nDefault target: x86_64-apple-macosx10.7\n"
        identity = self.identify_fixture_compiler(invocation, binary, description=description, translated=True)
        self.assertEqual(identity["binary"]["default_target"], "x86_64-apple-macosx10.7")

    def test_replay_rejects_launcher_only_or_inconsistent_compiler_identity(self):
        destination = dict(self.profile, os_major=26, darwin_major=25)
        receipt = {"status": "passed", "mode": "qualify", "profile_definition": self.profile,
                   "source": {"a": "b"}, "compiler": self.compiler_identity()}
        for binary in (None, {}, {**receipt["compiler"]["binary"], "sha256": "launcher"},
                       {**receipt["compiler"]["binary"], "version": "1.10.0"},
                       {**receipt["compiler"]["binary"], "architectures": ["x86_64"]}):
            with self.subTest(binary=binary):
                changed = dict(receipt, compiler=dict(receipt["compiler"], binary=binary))
                with self.assertRaises(runner.QualificationError):
                    runner.validate_replay_identity(changed, destination, {"a": "b"})

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
        managed.receipt["cases"] = [{"status": "passed"}] * (len(runner.CASE_IDS) * 2)
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
