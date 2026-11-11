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
                         "files": files, "builds": builds, "cases": [copy.deepcopy(runner.CAMPAIGNS[self.kind]["case"])]}
        self.save_manifest()
        self.host = dict(runner.base.EXPECTED_HOST, system="Darwin", hardware_arm64=False, translated=False)

    def save_manifest(self):
        (self.bundle / "manifest.json").write_text(json.dumps(self.manifest))

    def execute(self, command, cwd):
        expected = runner.CAMPAIGNS[self.kind]["case"]
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
        self.assertEqual(len(result["cases"]), 4)
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
        self.manifest["cases"] = [copy.deepcopy(runner.CAMPAIGNS[self.kind]["case"])]
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

    def test_runner_and_builder_parse_as_python_38(self):
        import ast
        for name in ("monterey_foundations_runner.py", "build_monterey_foundations.py"):
            source = (COMPAT / name).read_text()
            ast.parse(source, feature_version=(3, 8))


if __name__ == "__main__":
    unittest.main()
