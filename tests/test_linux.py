"""Portable contracts for Linux inputs, strict ELF proof and bounded receipts.

Kernel execution belongs to linux_runner.py, never inferred from these tests.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import struct
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("linux_proof_runner", ROOT / "scripts/ci/linux_runner.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def elf_bytes(*, architecture="x86_64", section=".text", segment=0x6474e551):
    data = bytearray(1024)
    ident = b"\x7fELF\x02\x01\x01" + b"\0" * 9
    struct.pack_into("<16sHHIQQQIHHHHHH", data, 0, ident, 2, runner.ARCHITECTURES[architecture], 1,
                     0x401000, 64, 192, 0, 64, 56, 2, 64, 3, 1)
    struct.pack_into("<IIQQQQQQ", data, 64, 1, 5, 640, 0x401000, 0, 1, 1, 4096)
    struct.pack_into("<IIQQQQQQ", data, 120, segment, 6, 0, 0, 0, 0, 0, 16)
    names = b"\0.shstrtab\0" + section.encode() + b"\0"
    data[512:512 + len(names)] = names
    struct.pack_into("<IIQQQQIIQQ", data, 256, 1, 3, 0, 0, 512, len(names), 0, 0, 1, 0)
    struct.pack_into("<IIQQQQIIQQ", data, 320, 11, 1, 6, 0x401000, 640, 1, 0, 0, 1, 0)
    data[640] = 0xc3
    return data


class LinuxElfTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nk-linux-elf-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "fixture"

    def check(self, data, architecture="x86_64"):
        self.path.write_bytes(data)
        return runner.elf_identity(self.path, architecture)

    def test_identifies_both_elf64_machines_without_execution_claim(self):
        for architecture in runner.ARCHITECTURES:
            self.assertEqual(self.check(elf_bytes(architecture=architecture), architecture)["machine"], runner.ARCHITECTURES[architecture])

    def test_rejects_wrong_endianness_word_size_and_architecture(self):
        for byte, value in ((4, 1), (5, 2), (18, 0)):
            data = elf_bytes()
            data[byte] = value
            with self.assertRaises(runner.ProofError):
                self.check(data)

    def test_refuses_interpreter_dynamic_and_runtime_initializers(self):
        for segment in (2, 3):
            with self.assertRaisesRegex(runner.ProofError, "dynamic segment or interpreter"):
                self.check(elf_bytes(segment=segment))
        for section in (".init_array", ".fini_array", ".preinit_array", ".ctors", ".dtors"):
            with self.assertRaisesRegex(runner.ProofError, "initialization/finalization"):
                self.check(elf_bytes(section=section))

    def test_rejects_writable_code_or_executable_stack(self):
        for offset in (68, 124):
            data = elf_bytes()
            struct.pack_into("<I", data, offset, 7)
            with self.assertRaisesRegex(runner.ProofError, "Writable executable"):
                self.check(data)

    def test_requires_entry_in_executable_load_and_bounded_tables(self):
        data = elf_bytes()
        struct.pack_into("<Q", data, 24, 0x42)
        with self.assertRaisesRegex(runner.ProofError, "entry"):
            self.check(data)
        data = elf_bytes()
        struct.pack_into("<Q", data, 32, len(data))
        with self.assertRaisesRegex(runner.ProofError, "program table"):
            self.check(data)
        data = elf_bytes()
        struct.pack_into("<Q", data, 40, len(data))
        with self.assertRaisesRegex(runner.ProofError, "section table"):
            self.check(data)


class LinuxFunctionSectionsTests(unittest.TestCase):
    def test_preserves_every_original_assembly_line_and_instruction(self):
        for architecture, marker in (("x86_64", "@"), ("aarch64", "%")):
            assembly = ('\t.text\n\t.type main,' + marker + 'function\nmain: # @main\n'
                        '  instruction is never rewritten\n.Lend0:\n\t.size main, .Lend0-main\n'
                        '\t.cfi_endproc\n\t.type "unused helper",' + marker + 'function\n'
                        '"unused helper": // @unused helper\n  external reference is NOT suppressed\n'
                        '.Lend1:\n\t.size "unused helper", .Lend1-"unused helper"\n')
            sectioned, functions = runner.function_sections(assembly, architecture)
            self.assertEqual(functions, ["main", '"unused helper"'])
            for index in range(2):
                addition = '.section .text.nk.' + str(index) + ',"ax",' + marker + 'progbits\n.p2align 4\n'
                self.assertEqual(sectioned.count(addition), 1)
                sectioned = sectioned.replace(addition, "")
            self.assertEqual(sectioned, assembly)

    def test_refuses_incomplete_duplicate_unlabeled_and_section_switches(self):
        for assembly in ("", ".type foo,@function\nfoo:\n", ".type foo,@function\n.size foo,0\n",
                         ".type foo,@function\nfoo:\n.section .text\n.size foo,0\n",
                         ".type foo,@function\nfoo:\n.size foo,0\n.type foo,@function\n",
                         ".type foo,@function\nfoo:\n.size foo,0\n.section .debug_info\n"):
            with self.assertRaises(runner.ProofError):
                runner.function_sections(assembly, "x86_64")


class LinuxInputContracts(unittest.TestCase):
    def test_explicit_source_inventory_covers_both_platforms_and_portable_metadata(self):
        paths = set(re.findall(r'"(src/[^\"]+\.cr)"', (ROOT / "src/native-kernel/source.cr").read_text()))
        self.assertEqual(paths, {p.relative_to(ROOT).as_posix() for p in (ROOT / "src").rglob("*.cr")})
        for entry in ("linux/raw.cr", "linux.cr"):
            self.assertIn("src/native-kernel/" + entry, paths)
        self.assertEqual((ROOT / "src/native-kernel.cr").read_text(), 'require "./native-kernel/darwin"\n')

    def test_raw_require_graph_has_no_libc_metadata_or_managed_dependency(self):
        for source in (ROOT / "src/native-kernel/linux").rglob("*.cr"):
            text = source.read_text()
            self.assertNotRegex(text, r"\bLibC\b|^\s*lib \w+|require .*\b(?:source|audit|c/)", source)
            for path in re.findall(r'^require "([^"]+)"', text, re.M):
                self.assertTrue(path.startswith("./"))
        raw = (ROOT / "src/native-kernel/linux/raw.cr").read_text()
        for guard in ("flag?(:linux)", "!flag?(:android)", "flag?(:bits64)", "flag?(:gnu)", "flag?(:musl)", "flag?(:x86_64)", "flag?(:aarch64)"):
            self.assertIn(guard, raw)

    def test_fixture_only_entries_do_not_grow_into_a_managed_launch_api(self):
        process = (ROOT / "src/native-kernel/linux/process.cr").read_text()
        self.assertNotRegex(process, r"def self\.(?:fork|clone|execve|spawn)\b")
        self.assertNotIn("loop do", process) # No automatic retry, including denied exit_group.
        for method in ("wait4", "waitid"):
            self.assertIn("def self." + method, process)
        self.assertRegex(process, r"options : Int32,\s*usage : Resource::Usage\*")
        behavior = (ROOT / "spec/native/linux/behavior/common.cr").read_text()
        self.assertIn("Number::CLONE", behavior)
        self.assertIn("result.error == 10", behavior) # No kill after possibly completed collection.

    def test_all_public_methods_have_named_executed_cases(self):
        manifest = json.loads((ROOT / "ci/linux.json").read_text())
        found = set()
        for family in ("Descriptor", "Process", "Pidfd", "Event", "Resource", "Raw"):
            text = (ROOT / "src/native-kernel/linux" / (family.lower() + ".cr")).read_text()
            found.update(family + "." + method for method in re.findall(r"^  def self\.([a-z][a-z0-9_]*)\b", text, re.M))
        self.assertEqual(found, set(manifest["operations"]))
        self.assertEqual(len(found), 22)
        self.assertEqual(tuple(manifest["cases"]), runner.CASES)
        for case in manifest["operations"].values():
            self.assertIn(case, ("raw",) + runner.CASES)

    def test_every_number_has_an_independent_c_assertion(self):
        oracle = (ROOT / "scripts/ci/linux-layout.c").read_text()
        numbers = {name.upper(): (int(x86), int(arm)) for name, x86, arm in re.findall(r"NUMBER\((\w+),(\d+),(\d+)\)", oracle)}
        self.assertEqual(len(numbers), 26)
        for index, architecture in enumerate(("x86_64", "aarch64")):
            text = (ROOT / "src/native-kernel/linux/syscall" / (architecture + ".cr")).read_text()
            table = {name: int(value) for name, value in re.findall(r"^  (\w+)\s*=\s*(\d+)$", text, re.M)}
            self.assertEqual(table, {name: pair[index] for name, pair in numbers.items()})

    def test_separate_asm_profiles_and_fail_closed_negative_roster(self):
        metadata = (ROOT / "src/native-kernel/audit.cr").read_text()
        self.assertEqual(metadata.count("ASSEMBLY = ["), 3)
        self.assertIn('~{r11},~{memory},~{flags}', metadata)
        self.assertIn('svc #0\\0={x0},{x8}', metadata)
        fixtures = {path.stem for path in (ROOT / "spec/native/linux/rejections").glob("*.ll")}
        self.assertEqual(fixtures, {"external", "mutable", "incorrect", "darwin"})
        auditor = (ROOT / "scripts/ci/audit.cr").read_text()
        self.assertIn('when nil', auditor)
        self.assertIn('linux-x86_64', auditor)
        self.assertIn('linux-aarch64', auditor)
        self.assertNotIn(".concat", auditor)

    def test_native_elf_start_never_uses_a_crt_or_crystal_main(self):
        for architecture in runner.ARCHITECTURES:
            source = (ROOT / ("spec/native/linux/start-" + architecture + ".S")).read_text()
            self.assertIn("_start:", source)
            self.assertRegex(source, r"\b(?:call|bl) main")
            self.assertNotIn("__crystal_main", source)
            self.assertIn("GNU-stack", source)
        driver = (ROOT / "scripts/ci/linux_runner.py").read_text()
        self.assertIn('"-nostdlib", "-static", "-no-pie"', driver)
        self.assertIn('for fixture in ("raw", "behavior")', driver)
        self.assertIn('for optimization in ("development", "release")', driver)
        self.assertIn('self.rejection_tests(auditor)', driver)
        self.assertIn('self.require_refusals()', driver)

    def test_linux_specs_have_their_own_non_skip_gate_and_ilp32_refusals(self):
        driver = (ROOT / "scripts/ci/linux_runner.py").read_text()
        self.assertIn('"linux-specs"', driver)
        self.assertIn('int(count[1]) < 11', driver)
        self.assertIn('"--prelude", str(prelude)', driver)
        for target in ("x86_64-unknown-linux-gnux32", "aarch64-unknown-linux-gnu_ilp32"):
            self.assertIn(target, driver)

    def test_floor_does_not_use_new_alignof_expression(self):
        source = (ROOT / "spec/linux_abi_spec.cr").read_text()
        self.assertNotRegex(source, r"\balignof\(")
        self.assertIn("offsetof(LinuxAlignment", source)
        self.assertIn("_Alignof", (ROOT / "scripts/ci/linux-layout.c").read_text())

    def test_linux_is_selected_by_make_without_weakening_darwin(self):
        self.assertIn("filter Darwin Linux", (ROOT / "Makefile").read_text())
        check = (ROOT / "scripts/check-native.cr").read_text()
        self.assertIn('"scripts/ci/linux_runner.py"', check)
        self.assertIn("Native::Kernel::Audit::ASSEMBLY.to_set", check)
        self.assertIn('"xcrun", ["nm", "-u"', check)

    def test_public_native_ci_is_pinned_bounded_and_has_no_emulation(self):
        config = json.loads((ROOT / "ci/linux.json").read_text())
        self.assertEqual(config["compilers"], ["1.10.0", "1.22.2"])
        self.assertEqual(config["profiles"]["x86_64"]["runner"], "ubuntu-24.04")
        self.assertEqual(config["profiles"]["aarch64"]["runner"], "ubuntu-24.04-arm")
        workflow = (ROOT / ".github/workflows/linux.yml").read_text()
        self.assertIn("contents: read", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("repository.visibility == 'public'", workflow)
        self.assertIn("retention-days: 3", workflow)
        self.assertIn("if: always()", workflow)
        self.assertIn("--expected-compiler", workflow)
        self.assertIn("linux-floor-arm64.sh", workflow)
        self.assertNotRegex(workflow, r"qemu|--allow-translation|pull_request_target|secrets\.")
        uses = re.findall(r"uses: ([^\s]+)", workflow)
        self.assertTrue(uses)
        self.assertTrue(all(re.fullmatch(r"[\w/-]+@[0-9a-f]{40}", value) for value in uses))

    def test_source_pins_and_versions_remain_explicit(self):
        references = json.loads((ROOT / "ci/linux-references.json").read_text())
        pins = {item["repository"]: item for item in references["references"]}
        self.assertEqual(pins["torvalds/linux"]["revision"], "ffc253263a1375a65fa6c9f62a893e9767fbebfa")
        self.assertEqual(pins["sunfishcode/linux-raw-sys"]["source_version"], "v6.17")
        self.assertEqual(pins["immateria/Process-Control.cr"]["revision"], "9bf6fc1a32f01238ebd47f2efc42604fb3e04605")
        for item in references["references"]:
            self.assertTrue(item["files"])
            self.assertTrue(all(re.fullmatch(r"[0-9a-f]{64}", digest) for digest in item["files"].values()))


class LinuxRunnerContracts(unittest.TestCase):
    def test_header_dependency_hashes_include_system_headers_and_spaces(self):
        with tempfile.TemporaryDirectory(prefix="nk-headers-") as temp:
            path = Path(temp)
            (path / "local.c").write_text("source")
            (path / "system header.h").write_text("header")
            (path / "deps").write_text("a: local.c \\\n system\\ header.h\n")
            hashes = runner.header_hashes(path / "deps", path)
            self.assertEqual(set(hashes), {str(path / "local.c"), str(path / "system header.h")})

    def test_native_host_rejects_wrong_os_architecture_and_emulation(self):
        with mock.patch.object(runner.platform, "system", return_value="Darwin"):
            with self.assertRaises(runner.ProofError):
                runner.validate_native_host("x86_64")
        with mock.patch.object(runner.platform, "system", return_value="Linux"), mock.patch.object(runner.platform, "machine", return_value="aarch64"):
            with self.assertRaises(runner.ProofError):
                runner.validate_native_host("x86_64")
        with mock.patch.object(runner.platform, "system", return_value="Linux"), mock.patch.object(runner.platform, "machine", return_value="x86_64"), mock.patch.dict(os.environ, {"QEMU_CPU": "test"}):
            with self.assertRaisesRegex(runner.ProofError, "Emulated"):
                runner.validate_native_host("x86_64")

    def test_incomplete_setup_records_blocked_source_bound_receipt_without_running(self):
        with tempfile.TemporaryDirectory(prefix="nk-linux-failure-") as temp:
            args = type("Args", (), dict(output=str(Path(temp)/"new"), cross_target=None,
                        architecture="x86_64", cc="cc", expected_compiler="1.10.0",
                        record_failure="compiler setup failed", compiler="missing"))()
            proof = runner.Runner(args)
            proof.receipt["artifacts"]["raw-development"] = {"status": "building", "execution": "unrun"}
            with mock.patch.object(proof, "oracles") as oracles:
                self.assertEqual(proof.run(), 1)
                oracles.assert_not_called()
            receipt = json.loads((proof.export / "receipt.json").read_text())
            self.assertEqual(receipt["status"], "blocked")
            self.assertEqual(receipt["qualification"], "incomplete")
            self.assertTrue(receipt["source_unchanged"])
            self.assertEqual(receipt["stages"], [])
            self.assertEqual(len(receipt["unproduced_artifacts"]), 4)

    def test_source_identity_covers_every_native_linux_input(self):
        identity = runner.source_identity(ROOT)
        for directory in ("src/native-kernel/linux", "spec/native/linux"):
            for path in (ROOT / directory).rglob("*"):
                if path.is_file():
                    self.assertIn(path.relative_to(ROOT).as_posix(), identity)
        for name in (".github/workflows/linux.yml", "ci/linux.json", "docs/linux-process.md", "scripts/ci/linux-layout.c"):
            self.assertIn(name, identity)


if __name__ == "__main__":
    unittest.main()
