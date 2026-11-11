"""Portable contracts for the separate Darwin 21 handoff tooling."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import struct
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
        self.assertEqual(len(result["cases"]), 28)
        cleanup_builds = {case["build"] for case in result["cases"] if case["case"] == "spawn-rejection-cleanup"}
        self.assertEqual(cleanup_builds, set(runner.base.BUILD_ROSTER))
        self.assertEqual(result["topology"], runner.CAMPAIGNS["spawn"]["topology"])
        self.assertTrue(result["source_unchanged"])

    def test_manifest_cannot_omit_rejection_cleanup(self):
        self.manifest["cases"] = [case for case in self.manifest["cases"] if case["id"] != "spawn-rejection-cleanup"]
        self.save_manifest()
        with self.assertRaisesRegex(runner.ProbeError, "case contract"):
            runner.load_manifest(self.bundle)

    def test_one_failed_rejection_cleanup_case_prevents_qualification(self):
        def execute(command, cwd):
            result = self.execute(command, cwd)
            if command[-1] == "spawn-rejection-cleanup" and command[0].endswith("spawn-floor-release"):
                result["exit_code"] = 17
            return result

        with mock.patch.object(runner.base, "identify_host", return_value=self.host), \
                mock.patch.object(runner.base, "run_bounded", side_effect=execute), \
                contextlib.redirect_stdout(io.StringIO()):
            result = runner.run_bundle(self.bundle, self.output)
        self.assertEqual(len(result["cases"]), 28)
        failures = [case for case in result["cases"] if case["status"] != "passed"]
        self.assertEqual(len(failures), 1)
        self.assertEqual((failures[0]["build"], failures[0]["case"], failures[0]["status"]),
                         ("floor-release", "spawn-rejection-cleanup", "wrong_result"))
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["target_runtime_observed"])
        self.assertFalse(result["target_qualified"])
        self.assertTrue(result["source_unchanged"])
        saved = json.loads((self.output / "receipt.json").read_text())
        self.assertEqual(saved["status"], "failed")
        self.assertFalse(saved["target_qualified"])

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

    def test_official_launcher_symlink_keeps_invocation_and_resolves_installed_binary(self):
        installation = self.base / "installation"
        launcher = installation / "bin" / "crystal"
        launcher.parent.mkdir(parents=True)
        launcher.write_text("#!/bin/sh\n# reviewed fixture launcher\n")
        launcher.chmod(0o700)
        binary = installation / "embedded" / "bin" / "crystal"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"\xcf\xfa\xed\xfeactual compiler")
        binary.chmod(0o700)
        invocation = self.base / "aliases" / "bin" / "crystal"
        invocation.parent.mkdir(parents=True)
        invocation.symlink_to(launcher)
        identity = "Crystal 1.22.2\nDefault target: x86_64-apple-macosx\n"
        commands = []

        def command_text(command):
            commands.append(command)
            return "x86_64\n" if command[1:3] == ["lipo", "-archs"] else identity

        with mock.patch.object(builder, "OFFICIAL_LAUNCHER_SHA256", builder.digest(launcher)), \
                mock.patch.object(builder, "command_text", side_effect=command_text):
            receipt = builder.compiler_receipt(invocation, "1.22.2")
        self.assertEqual(commands, [[str(invocation), "--version"], [str(binary), "--version"],
                                    ["/usr/bin/xcrun", "lipo", "-archs", str(binary)]])
        self.assertEqual(receipt["invocation"]["path"], str(invocation))
        self.assertEqual(receipt["invocation"]["sha256"], builder.digest(launcher))
        self.assertEqual(receipt["binary"]["path"], str(binary))
        self.assertEqual(receipt["binary"]["resolution"], "official-launcher-layout")

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


class MachOLoaderContracts(unittest.TestCase):
    def artifact(self, legacy=False, duplicate=False, segments=False):
        if legacy:
            deployment = struct.pack("<4I", 0x24, 16, 12 << 16, 13 << 16)
        else:
            deployment = struct.pack("<6I", 0x32, 24, 1, 12 << 16, 13 << 16, 0)
        deployments = deployment * (2 if duplicate else 1)
        starts = struct.pack("<2I", 1, 8) if segments else struct.pack("<I", 0)
        record = struct.pack("<IHHQIHH", 24, 4096, 6, 4096, 0, 1, 0xffff) if segments else b""
        payload_size = 28 + len(starts) + len(record)
        payload = struct.pack("<7I", 0, 28, payload_size, payload_size, 0, 1, 0) + starts + record
        fixups_command = 32 + len(deployments)
        fixups_data = fixups_command + 16
        header = struct.pack("<8I", 0xfeedfacf, 0x01000007, 3, 2, 3 if duplicate else 2,
                             len(deployments) + 16, 0, 0)
        command = struct.pack("<4I", 0x80000034, 16, fixups_data, len(payload))
        return bytearray(header + deployments + command + payload), fixups_command, fixups_data

    def test_reads_both_macos_deployment_commands_and_rebase_metadata(self):
        for legacy in (False, True):
            with self.subTest(legacy=legacy):
                data, _, _ = self.artifact(legacy=legacy, segments=True)
                result = builder.macho_identity(data)
                self.assertEqual(result["architecture"], "x86_64")
                self.assertEqual(result["deployment"], {
                    "command": "LC_VERSION_MIN_MACOSX" if legacy else "LC_BUILD_VERSION",
                    "platform": "macOS", "minimum": "12.0.0", "sdk": "13.0.0",
                })
                self.assertEqual(result["chained_fixups"]["version"], 0)
                self.assertEqual(result["chained_fixups"]["imports_count"], 0)
                self.assertEqual(result["chained_fixups"]["segments"],
                                 [{"index": 0, "pointer_format": 6, "page_count": 1}])

    def test_rejects_foreign_architecture_file_type_and_incomplete_commands(self):
        for offset, value in ((0, 0xcafebabe), (4, 0x0100000c), (12, 6), (16, 3), (20, 0xffffffff)):
            with self.subTest(offset=offset):
                data, _, _ = self.artifact()
                struct.pack_into("<I", data, offset, value)
                with self.assertRaises(builder.BuildError):
                    builder.macho_identity(data)
        data, _, _ = self.artifact()
        with self.assertRaises(builder.BuildError):
            builder.macho_identity(data[:31])

    def test_rejects_wrong_platform_deployment_and_duplicate_deployment(self):
        for offset, value in ((40, 2), (44, 13 << 16), (36, 8)):
            with self.subTest(offset=offset):
                data, _, _ = self.artifact()
                struct.pack_into("<I", data, offset, value)
                with self.assertRaises(builder.BuildError):
                    builder.macho_identity(data)
        data, _, _ = self.artifact(duplicate=True)
        with self.assertRaisesRegex(builder.BuildError, "Duplicate.*deployment"):
            builder.macho_identity(data)

    def test_rejects_new_fixup_version_imports_and_out_of_bounds_offsets(self):
        for field, value in ((0, 1), (16, 1), (4, 31), (8, 33), (12, 33), (28, 4)):
            with self.subTest(field=field):
                data, _, fixups_data = self.artifact()
                struct.pack_into("<I", data, fixups_data + field, value)
                with self.assertRaises(builder.BuildError):
                    builder.macho_identity(data)
        data, command, _ = self.artifact()
        struct.pack_into("<I", data, command + 8, len(data))
        with self.assertRaisesRegex(builder.BuildError, "artifact bounds"):
            builder.macho_identity(data)

    def test_rejects_segment_records_and_page_tables_outside_fixups(self):
        for offset, value in ((32, 4), (36, 0xffffffff)):
            with self.subTest(offset=offset):
                data, _, fixups_data = self.artifact(segments=True)
                struct.pack_into("<I", data, fixups_data + offset, value)
                with self.assertRaisesRegex(builder.BuildError, "payload bounds"):
                    builder.macho_identity(data)

    def test_accepts_audited_import_formats_page_sizes_and_intel_pointer_formats(self):
        for imports_format in (1, 2, 3):
            for page_size in (4096, 16384):
                for pointer_format in (2, 6):
                    with self.subTest(imports_format=imports_format, page_size=page_size, pointer_format=pointer_format):
                        data, _, fixups_data = self.artifact(segments=True)
                        struct.pack_into("<I", data, fixups_data + 20, imports_format)
                        struct.pack_into("<2H", data, fixups_data + 40, page_size, pointer_format)
                        result = builder.macho_identity(data)
                        self.assertEqual(result["chained_fixups"]["imports_format"], imports_format)
                        self.assertEqual(result["chained_fixups"]["segments"][0]["pointer_format"], pointer_format)

    def test_rejects_unknown_header_formats_even_without_imports(self):
        for offset, value in ((20, 0), (20, 4), (24, 1)):
            with self.subTest(offset=offset, value=value):
                data, _, fixups_data = self.artifact()
                struct.pack_into("<I", data, fixups_data + offset, value)
                with self.assertRaises(builder.BuildError):
                    builder.macho_identity(data)

    def test_rejects_import_symbol_order_and_starts_overlapping_imports(self):
        data, _, fixups_data = self.artifact()
        struct.pack_into("<I", data, fixups_data + 12, 28)
        with self.assertRaises(builder.BuildError):
            builder.macho_identity(data)
        for imports_offset in (32, 59):
            with self.subTest(imports_offset=imports_offset):
                data, _, fixups_data = self.artifact(segments=True)
                struct.pack_into("<I", data, fixups_data + 8, imports_offset)
                with self.assertRaises(builder.BuildError):
                    builder.macho_identity(data)

    def test_rejects_unaudited_page_sizes_and_pointer_formats(self):
        for offset, value in ((40, 0), (40, 8192), (42, 1), (42, 7), (42, 13)):
            with self.subTest(offset=offset, value=value):
                data, _, fixups_data = self.artifact(segments=True)
                struct.pack_into("<H", data, fixups_data + offset, value)
                with self.assertRaises(builder.BuildError):
                    builder.macho_identity(data)


if __name__ == "__main__":
    unittest.main()
