"""Portable contracts for the separate Darwin 21 handoff tooling."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
COMPAT = ROOT / "scripts" / "compat"
sys.path.insert(0, str(COMPAT))
SPEC = importlib.util.spec_from_file_location("monterey_foundations_runner", COMPAT / "monterey_foundations_runner.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
BUILDER_SPEC = importlib.util.spec_from_file_location("build_monterey_foundations", COMPAT / "build_monterey_foundations.py")
builder = importlib.util.module_from_spec(BUILDER_SPEC)
BUILDER_SPEC.loader.exec_module(builder)


class FoundationsRunnerContracts(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="monterey-foundations-tests-")
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name).resolve()
        self.bundle = self.base / "bundle"
        self.bundle.mkdir()
        self.output = self.base / "result"
        self.output.mkdir()
        self.kind = "spawn"
        (self.bundle / runner.RUNNER_FILE).write_text("# shipped foundations runner\n")
        (self.bundle / runner.BASE_RUNNER_FILE).write_text("# shipped base runner\n")
        (self.bundle / "README.txt").write_text("fixture\n")
        (self.bundle / "bin").mkdir()
        builds = []
        for name, (version, optimization) in runner.base.BUILD_ROSTER.items():
            build = {"name": name, "compiler_version": version, "optimization": optimization,
                     "path": "bin/spawn-" + name, "target_path": "bin/spawn-target-" + name}
            for key in ("path", "target_path"):
                path = self.bundle / build[key]
                path.write_text("#!/bin/sh\nexit 0\n")
                path.chmod(0o700)
            builds.append(build)
        files = {str(path.relative_to(self.bundle)): runner.base.digest(path)
                 for path in self.bundle.rglob("*") if path.is_file()}
        self.manifest = {"schema": 1, "kind": self.kind, "expected_host": runner.base.EXPECTED_HOST.copy(),
                         "files": files, "builds": builds, "cases": copy.deepcopy(runner.CAMPAIGNS[self.kind]["cases"])}
        self.save_manifest()
        self.host = dict(runner.base.EXPECTED_HOST, system="Darwin", hardware_arm64=False, translated=False)

    def save_manifest(self):
        (self.bundle / "manifest.json").write_text(json.dumps(self.manifest))

    def execute(self, command, cwd):
        expected = next(case for case in runner.CAMPAIGNS[self.kind]["cases"] if case["id"] == command[-1])
        return {"status": "completed", "exit_code": expected["exit_code"], "stdout": expected["stdout"],
                "stderr": expected["stderr"], "started": True, "completion_observed": True,
                "output_truncated": False, "timed_out": False, "cleanup": "already-absent"}

    def test_accepts_complete_spawn_manifest_and_runs_all_four_builds(self):
        with mock.patch.object(runner.base, "identify_host", return_value=self.host), \
                mock.patch.object(runner.base, "run_bounded", side_effect=self.execute), \
                contextlib.redirect_stdout(io.StringIO()):
            result = runner.run_bundle(self.bundle, self.output)
        self.assertEqual(result["status"], "passed")
        self.assertTrue(result["target_qualified"])
        self.assertEqual(len(result["cases"]), 4 * len(runner.CAMPAIGNS["spawn"]["cases"]))
        self.assertEqual(result["topology"], runner.CAMPAIGNS["spawn"]["topology"])
        self.assertTrue(result["source_unchanged"])

    def test_rejects_missing_spawn_target_or_wrong_case(self):
        self.manifest["builds"][0].pop("target_path")
        self.save_manifest()
        with self.assertRaisesRegex(runner.ProbeError, "Spawn target"):
            runner.load_manifest(self.bundle)
        self.manifest["builds"][0]["target_path"] = "bin/spawn-target-current-development"
        self.manifest["cases"][0]["stdout"] = "forged\n"
        self.save_manifest()
        with self.assertRaisesRegex(runner.ProbeError, "case contract"):
            runner.load_manifest(self.bundle)

    def test_task_token_manifest_forbids_an_unneeded_target(self):
        self.kind = "task-token"
        builds = []
        for name, (version, optimization) in runner.base.BUILD_ROSTER.items():
            path = self.bundle / "bin" / ("task-token-" + name)
            path.write_text("#!/bin/sh\nexit 0\n")
            path.chmod(0o700)
            builds.append({"name": name, "compiler_version": version, "optimization": optimization,
                           "path": "bin/task-token-" + name})
        self.manifest["kind"] = self.kind
        self.manifest["builds"] = builds
        self.manifest["cases"] = copy.deepcopy(runner.CAMPAIGNS[self.kind]["cases"])
        self.manifest["files"] = {str(path.relative_to(self.bundle)): runner.base.digest(path)
                                  for path in self.bundle.rglob("*") if path.is_file() and path.name != "manifest.json"}
        self.save_manifest()
        runner.load_manifest(self.bundle)
        self.manifest["builds"][0]["target_path"] = "bin/forged"
        self.save_manifest()
        with self.assertRaisesRegex(runner.ProbeError, "cannot name a target"):
            runner.load_manifest(self.bundle)

    def test_preflight_is_not_target_qualification(self):
        arm = dict(self.host, architecture="arm64", hardware_arm64=True, os_version="15.4.1")
        with mock.patch.object(runner.base, "identify_host", return_value=arm), \
                mock.patch.object(runner.base, "run_bounded", side_effect=self.execute), \
                contextlib.redirect_stdout(io.StringIO()):
            result = runner.run_bundle(self.bundle, self.output, preflight=True)
        self.assertEqual(result["status"], "preflight_passed")
        self.assertFalse(result["target_qualified"])
        self.assertFalse(result["target_runtime_observed"])

    def test_shipped_runner_refuses_nonisolated_python_before_creating_results(self):
        output = self.base / "nonisolated-result"
        result = subprocess.run(
            [sys.executable, str(COMPAT / "monterey_foundations_runner.py"), "--output", str(output)],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("python3 -I", result.stderr)
        self.assertFalse(output.exists())

    def test_builder_rejects_non_x86_darwin_ir_and_wrong_compiler_identity(self):
        valid = self.base / "valid.ll"
        valid.write_text('target triple = "x86_64-apple-macosx12.0.0"\n')
        self.assertEqual(builder.llvm_target(valid), "x86_64-apple-macosx12.0.0")
        invalid = self.base / "invalid.ll"
        invalid.write_text('target triple = "arm64-apple-macosx12.0.0"\n')
        with self.assertRaisesRegex(builder.BuildError, "not an x86-64 Darwin"):
            builder.llvm_target(invalid)
        identity = "Crystal 1.22.2 (2026-01-01)\nDefault target: x86_64-apple-macosx\n"
        with mock.patch.object(builder, "command_text", return_value=identity):
            self.assertEqual(builder.compiler_identity("/tmp/crystal", "1.22.2"), identity.strip())
        with mock.patch.object(builder, "command_text", return_value="Crystal 1.22.2\nDefault target: arm64-apple-macosx\n"):
            with self.assertRaisesRegex(builder.BuildError, "x86-64 Apple"):
                builder.compiler_identity("/tmp/crystal", "1.22.2")

    def test_builder_resolves_and_records_launcher_and_actual_macho_separately(self):
        launcher = self.base / "crystal-wrapper"
        launcher.write_text("#!/bin/sh\n")
        launcher.chmod(0o700)
        invocation = self.base / "crystal-invocation"
        invocation.symlink_to(launcher.name)
        binary = self.base / "crystal-bin"
        binary.write_bytes(b"\xcf\xfa\xed\xfeactual compiler")
        binary.chmod(0o700)
        with self.assertRaisesRegex(builder.BuildError, "Cannot resolve actual compiler binary"):
            builder.resolve_compiler_binary(launcher)
        resolved, mode = builder.resolve_compiler_binary(launcher, binary)
        self.assertEqual((resolved, mode), (binary.resolve(), "explicit-operator-path"))
        direct, mode = builder.resolve_compiler_binary(binary)
        self.assertEqual((direct, mode), (binary.resolve(), "direct-mach-o"))
        not_macho = self.base / "not-macho"
        not_macho.write_text("not a binary")
        not_macho.chmod(0o700)
        with self.assertRaisesRegex(builder.BuildError, "must be Mach-O"):
            builder.resolve_compiler_binary(launcher, not_macho)

        identity = "Crystal 1.22.2 (2026-01-01)\nDefault target: x86_64-apple-macosx\n"
        lipo_paths = []

        def commands(command):
            if command[1:] == ["--version"]:
                return identity
            self.assertEqual(command[:3], ["/usr/bin/xcrun", "lipo", "-archs"])
            lipo_paths.append(command[-1])
            return "x86_64\n"

        with mock.patch.object(builder, "command_text", side_effect=commands):
            receipt = builder.compiler_receipt(invocation, "1.22.2", binary)
        self.assertEqual(lipo_paths, [str(binary.resolve())])
        self.assertEqual(receipt["invocation"]["path"], str(invocation.absolute()))
        self.assertNotEqual(receipt["invocation"]["path"], str(launcher.resolve()))
        self.assertEqual(receipt["binary"]["path"], str(binary.resolve()))
        self.assertEqual(receipt["binary"]["resolution"], "explicit-operator-path")
        self.assertRegex(receipt["invocation"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(receipt["binary"]["sha256"], r"^[0-9a-f]{64}$")

    def test_campaign_selection_keeps_task_token_independent_of_spawn(self):
        calls = []

        def campaign(kind, compilers, output):
            calls.append(kind)
            if kind == "spawn":
                raise builder.BuildError("spawn compiler unavailable")
            return {"status": "built", "manifest_sha256": "a" * 64, "builds": [], "artifacts": {}}

        with mock.patch.object(builder, "build_campaign", side_effect=campaign):
            both = builder.build_campaigns(("spawn", "task-token"), {"current": "/current", "floor": "/floor"}, self.base)
        self.assertEqual(calls, ["spawn", "task-token"])
        self.assertEqual(both["spawn"]["status"], "failed")
        self.assertIn("unavailable", both["spawn"]["error"])
        self.assertEqual(both["task-token"]["status"], "built")

        calls.clear()
        with mock.patch.object(builder, "build_campaign", side_effect=campaign):
            task_only = builder.build_campaigns(("task-token",), {"current": "/current", "floor": "/floor"}, self.base)
        self.assertEqual(calls, ["task-token"])
        self.assertEqual(task_only["spawn"]["status"], "not_requested")
        self.assertEqual(task_only["task-token"]["status"], "built")

    def test_task_token_only_skips_spawn_layout_and_spawn_layout_failure_does_not_block_it(self):
        source = {"src/example.cr": "a" * 64}
        built = {"status": "built", "manifest_sha256": "b" * 64, "builds": [], "artifacts": {}}

        def campaign_results(campaigns, compilers, output):
            selected = set(campaigns)
            return {"spawn": {"status": "built"} if "spawn" in selected else {"status": "not_requested"},
                    "task-token": dict(built) if "task-token" in selected else {"status": "not_requested"}}

        common = [
            mock.patch.object(builder, "require_build_host"),
            mock.patch.object(builder.base, "safe_output", side_effect=lambda path, root: path),
            mock.patch.object(builder, "toolchain_receipt", return_value={}),
            mock.patch.object(builder, "compiler_receipt", return_value={}),
            mock.patch.object(builder, "source_inventory", return_value=source),
        ]
        task_only_output = self.base / "task-only-builder-output"
        with common[0], common[1], common[2], common[3], common[4], \
                mock.patch.object(builder, "run", side_effect=AssertionError("task-token-only must not run spawn layout")), \
                mock.patch.object(builder, "build_campaigns", side_effect=campaign_results), \
                contextlib.redirect_stdout(io.StringIO()):
            code = builder.main(["--current", "/tmp/current", "--floor", "/tmp/floor", "--campaign", "task-token",
                                 "--output", str(task_only_output)])
        self.assertEqual(code, 0)
        task_only_receipt = json.loads((task_only_output / "build-receipt.json").read_text())
        self.assertEqual(task_only_receipt["layout_assertion"]["status"], "not_requested")
        self.assertEqual(task_only_receipt["campaigns"]["task-token"]["status"], "built")

        failed_spawn_output = self.base / "failed-spawn-layout-output"
        calls = []

        def record_task_only(campaigns, compilers, output):
            calls.append(tuple(campaigns))
            return campaign_results(campaigns, compilers, output)

        with mock.patch.object(builder, "require_build_host"), \
                mock.patch.object(builder.base, "safe_output", side_effect=lambda path, root: path), \
                mock.patch.object(builder, "toolchain_receipt", return_value={}), \
                mock.patch.object(builder, "compiler_receipt", return_value={}), \
                mock.patch.object(builder, "source_inventory", return_value=source), \
                mock.patch.object(builder, "run", side_effect=builder.BuildError("spawn layout failed")), \
                mock.patch.object(builder, "build_campaigns", side_effect=record_task_only), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = builder.main(["--current", "/tmp/current", "--floor", "/tmp/floor", "--output", str(failed_spawn_output)])
        self.assertEqual(code, 1)
        self.assertEqual(calls, [("task-token",)])
        failed_spawn_receipt = json.loads((failed_spawn_output / "build-receipt.json").read_text())
        self.assertEqual(failed_spawn_receipt["layout_assertion"]["status"], "failed")
        self.assertEqual(failed_spawn_receipt["campaigns"]["spawn"]["status"], "failed")
        self.assertEqual(failed_spawn_receipt["campaigns"]["task-token"]["status"], "built")

    def test_runner_and_builder_parse_as_python_38(self):
        import ast
        for name in ("monterey_foundations_runner.py", "build_monterey_foundations.py"):
            source = (COMPAT / name).read_text()
            ast.parse(source, feature_version=(3, 8))


if __name__ == "__main__":
    unittest.main()
