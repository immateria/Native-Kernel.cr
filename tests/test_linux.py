"""Portable contracts for Linux inputs, strict ELF proof and bounded receipts.

Kernel execution belongs to linux_runner.py, never inferred from these tests.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import textwrap
from types import SimpleNamespace
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


def elf_object_bytes(*, architecture="x86_64", functions=2):
    labels = [b"", b".shstrtab"] + [(".text.nk." + str(index)).encode() for index in range(functions)]
    names = b"\0".join(labels) + b"\0"
    payload = 64 + 64 * len(labels)
    data = bytearray(payload + len(names) + functions)
    ident = b"\x7fELF\x02\x01\x01" + b"\0" * 9
    struct.pack_into("<16sHHIQQQIHHHHHH", data, 0, ident, 1, runner.ARCHITECTURES[architecture], 1,
                     0, 0, 64, 0, 64, 0, 0, 64, len(labels), 1)
    data[payload:payload + len(names)] = names
    struct.pack_into("<IIQQQQIIQQ", data, 128, 1, 3, 0, 0, payload, len(names), 0, 0, 1, 0)
    name_offset = len(b"\0.shstrtab\0")
    for index, label in enumerate(labels[2:]):
        struct.pack_into("<IIQQQQIIQQ", data, 192 + index * 64,
                         name_offset, 1, 6, 0, payload + len(names) + index, 1, 0, 0, 16, 0)
        name_offset += len(label) + 1
    return data


def proof_args(output, **overrides):
    return SimpleNamespace(**dict(dict(output=str(output), cross_target=None,
                           architecture="x86_64", cc="cc", expected_compiler="1.22.2",
                           record_failure=None, compiler="fixture-compiler"), **overrides))


def stage_result(*, exit_code=0, stdout="", stderr="", output_truncated=False, **fields):
    return dict(status="passed" if exit_code == 0 else "failed", exit_code=exit_code,
                stdout=stdout, stderr=stderr, output_truncated=output_truncated, **fields)


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


class LinuxObjectSectionsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nk-linux-object-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "fixture.o"

    def check(self, data, architecture="x86_64", functions=2):
        self.path.write_bytes(data)
        return runner.elf_object_sections(self.path, architecture, functions)

    def test_structurally_checks_large_transformed_objects_on_both_architectures(self):
        for architecture in runner.ARCHITECTURES:
            with self.subTest(architecture=architecture):
                record = self.check(elf_object_bytes(architecture=architecture, functions=5301), architecture, 5301)
                self.assertEqual(record["sections"], 5303)
                self.assertEqual(record["function_sections"], 5301)
                self.assertTrue(record["all_sections_validated"])
                self.assertLess(len(json.dumps(record)), 1024)
                self.assertEqual(runner.common.OUTPUT_LIMIT, 65536)

    def test_rejects_bad_identity_tables_names_and_payload_extents(self):
        for offset, fmt, value in ((16, "<H", 2), (18, "<H", 0), (40, "<Q", 65536),
                                   (58, "<H", 0), (60, "<H", 0), (62, "<H", 99),
                                   (128 + 4, "<I", 1), (128 + 24, "<Q", 65536),
                                   (192, "<I", 65536), (192 + 24, "<Q", 65536)):
            with self.subTest(offset=offset, value=value):
                data = elf_object_bytes()
                struct.pack_into(fmt, data, offset, value)
                with self.assertRaises(runner.ProofError):
                    self.check(data)
        data = elf_object_bytes()
        names_offset, names_size = struct.unpack_from("<QQ", data, 128 + 24)
        data[names_offset + names_size - 1] = ord("x")
        with self.assertRaisesRegex(runner.ProofError, "section name"):
            self.check(data)

    def test_rejects_changed_missing_duplicate_or_writable_function_sections(self):
        for functions in (0, 1, 3):
            with self.assertRaises(runner.ProofError):
                self.check(elf_object_bytes(), functions=functions)
        for offset, value in ((192 + 8, 7), (192 + 8, 2), (192 + 4, 8), (256, 11)):
            with self.subTest(offset=offset, value=value):
                data = elf_object_bytes()
                struct.pack_into("<I", data, offset, value)
                with self.assertRaises(runner.ProofError):
                    self.check(data)

    def test_rejects_initialization_arrays_by_name_or_section_type(self):
        for kind in (14, 15, 16):
            data = elf_object_bytes()
            struct.pack_into("<I", data, 192 + 4, kind)
            with self.assertRaisesRegex(runner.ProofError, "initialization/finalization"):
                self.check(data)
        for label in (b".ctors", b".dtors", b".init_array", b".fini_array"):
            data = elf_object_bytes()
            offset = data.index(b".text.nk.0\0")
            data[offset:offset + len(label) + 1] = label + b"\0"
            with self.assertRaisesRegex(runner.ProofError, "initialization/finalization"):
                self.check(data)

    def test_build_keeps_direct_object_validation_and_bounded_header_diagnostic(self):
        proof = runner.Runner(proof_args(Path(self.temp.name) / "proof"))
        proof.compiler, proof.version = "fixture-compiler", "1.22.2"
        commands = {}

        def stage(name, command, **options):
            commands[name] = command
            if name.startswith("compile-"):
                output = Path(command[-1])
                Path(str(output) + ".ll").write_text('target triple = "x86_64-unknown-linux-gnu"\n')
                Path(str(output) + ".s").write_text(".type main,@function\nmain:\nret\n.size main,.-main\n")
                Path(str(output) + ".o").write_bytes(elf_object_bytes(functions=1))
            if name.startswith("assemble-"):
                Path(command[-1]).write_bytes(elf_object_bytes(functions=1))
            return stage_result()

        def link(name, obj, program):
            program.write_bytes(elf_bytes())

        with mock.patch.object(proof, "stage", side_effect=stage), mock.patch.object(proof, "link", side_effect=link):
            with mock.patch.object(proof, "inspect", return_value={"type": 2}):
                _, record = proof.build_probe("raw", "development", "fixture-auditor")
        self.assertEqual(commands["object-raw-development"][:4], ["readelf", "-h", "-W", str(proof.build / "raw-development.sections.o")])
        self.assertTrue(record["object_sections"]["all_sections_validated"])
        self.assertTrue((proof.export / "raw-development.object-sections.json").is_file())
        with mock.patch.object(proof, "stage", side_effect=stage), mock.patch.object(runner, "elf_object_sections", side_effect=runner.ProofError("bad transformed object")):
            with mock.patch.object(proof, "link") as linker:
                with self.assertRaisesRegex(runner.ProofError, "bad transformed object"):
                    proof.build_probe("raw", "development", "fixture-auditor")
                linker.assert_not_called()


class CrystalEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nk-crystal-env-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def stdlib(self, version, prefix="compiler"):
        directory = self.root / prefix / ("crystal-" + version + "-1") / "share/crystal/src"
        directory.mkdir(parents=True)
        (directory / "prelude.cr").write_text('require "./object"\n')
        (directory / "object.cr").write_text("class Object; end\n")
        return directory

    def test_reviewed_compiler_env_outputs_support_unquoted_and_quoted_paths(self):
        # The real releases' `env` key sets/Process.quote format; only installation
        # prefixes are temporary. 1.22.2 adds EXEC_PATH and removes LIBRARY_RPATH.
        for version in ("1.10.0", "1.22.2"):
            directory = self.stdlib(version)
            extra = "CRYSTAL_LIBRARY_RPATH=''" if version == "1.10.0" else "CRYSTAL_EXEC_PATH=''"
            for value in ("lib:" + str(directory), '"lib:' + str(directory) + '"', "'lib:" + str(directory) + "'"):
                with self.subTest(version=version, path=value):
                    environment = ("CRYSTAL_CACHE_DIR=/home/runner/.cache/crystal\n"
                                   + extra + "\nCRYSTAL_PATH=" + value + "\nCRYSTAL_VERSION=" + version
                                   + "\nCRYSTAL_LIBRARY_PATH=/usr/bin/../lib/crystal\nCRYSTAL_OPTS=''\n")
                    hashes = runner.crystal_stdlib_sources(environment, self.root)
                    self.assertEqual(hashes, {str(path.resolve()): runner.common.sha256_file(path)
                                              for path in directory.glob("*.cr")})

    def test_shell_escaped_spaces_and_relative_search_sources_are_hashed_without_expansion(self):
        directory = self.stdlib("1.22.2", "compiler with spaces")
        library = self.root / "lib"
        library.mkdir()
        (library / "helper.cr").write_text("# relative Crystal search entry\n")
        value = "lib:" + str(directory)
        for escaped in ('"' + value + '"', value.replace(" ", "\\ ")):
            hashes = runner.crystal_stdlib_sources("CRYSTAL_PATH=" + escaped, self.root)
            self.assertIn(str((library / "helper.cr").resolve()), hashes)
            self.assertIn(str((directory / "prelude.cr").resolve()), hashes)
        with self.assertRaises(runner.ProofError):
            runner.crystal_stdlib_sources('CRYSTAL_PATH="$(touch forbidden)"', self.root)
        self.assertFalse((self.root / "forbidden").exists())

    def test_empty_duplicate_malformed_and_non_stdlib_values_fail_closed(self):
        directory = self.stdlib("1.22.2")
        for environment in ("", "CRYSTAL_PATH=", "CRYSTAL_PATH=''", "CRYSTAL_PATH=\"unfinished",
                            "CRYSTAL_PATH=lib other", "CRYSTAL_PATH=lib\nCRYSTAL_PATH=" + str(directory),
                            "CRYSTAL_PATH=:" + str(directory), "CRYSTAL_PATH=" + str(directory) + ":",
                            "CRYSTAL_PATH=lib::" + str(directory), "CRYSTAL_PATH=missing",
                            "CRYSTAL_PATH='bad\x00value'", "CRYSTAL_PATH='bad\rvalue'", "CRYSTAL_PATH=" + str(self.root)):
            with self.subTest(environment=environment), self.assertRaises(runner.ProofError):
                runner.crystal_stdlib_sources(environment, self.root)


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
        self.assertIn("S::CHLD.to_u64!", behavior)
        self.assertIn("D::FD_CLOEXEC.to_u64!", (ROOT / "spec/native/linux/behavior/descriptor.cr").read_text())
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
        self.assertIn('"--prelude", crystal_relative_path(prelude, self.root)', driver)
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


class LinuxRefusalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nk-refusal paths-")
        self.addCleanup(self.temp.cleanup)
        self.proof = runner.Runner(proof_args(Path(self.temp.name) / "proof"))
        self.proof.compiler = "fixture-compiler"

    def test_prelude_is_relative_to_cwd_and_require_to_external_source(self):
        commands = []

        def stage(name, command, **options):
            prelude = command[command.index("--prelude") + 1]
            source = Path(command[-1])
            entry = json.loads(source.read_text().removeprefix("require ").strip())
            self.assertTrue(prelude.startswith(("./", "../")))
            self.assertTrue(entry.startswith(("./", "../")))
            self.assertEqual((self.proof.root / prelude).resolve(), (self.proof.build / "refusal-prelude.cr").resolve())
            resolved = (source.parent / (entry + ".cr")).resolve()
            self.assertTrue(resolved.is_file(), resolved)
            self.assertTrue(resolved.is_relative_to(ROOT / "src"))
            self.assertFalse(options["require"])
            commands.append(command)
            message = "Linux kernel calls require non-Android LP64 GNU/musl Linux x86-64 or AArch64." if source.stem.startswith("linux-") else "Darwin kernel calls require ARM64 or x86-64."
            return stage_result(exit_code=1, stderr=message)

        with mock.patch.object(self.proof, "stage", side_effect=stage):
            self.proof.require_refusals()
        self.assertEqual(len(commands), 8)
        self.assertEqual(len({command[command.index("--target") + 1] for command in commands}), 7)
        self.assertEqual(runner.crystal_relative_path(self.proof.build / ".prelude.cr", self.proof.build), "./.prelude.cr")

    def test_arbitrary_compiler_failure_crash_or_truncation_does_not_count_as_refusal(self):
        results = [stage_result(exit_code=1, stderr=message) for message in
                   ("Linux kernel calls require", "Error: can't find file 'prelude'", "Error: can't find file 'native-kernel/linux/raw'",
                    "compiler crashed", "undefined reference to symbol", "Error in foreign standard library")]
        results += [stage_result(exit_code=code, stderr="Linux kernel calls require non-Android LP64 GNU/musl Linux x86-64 or AArch64.") for code in (0, -11, 2)]
        results.append(stage_result(exit_code=1, stderr="Linux kernel calls require non-Android LP64 GNU/musl Linux x86-64 or AArch64.", output_truncated=True))
        for result in results:
            with self.subTest(result=result), mock.patch.object(self.proof, "stage", return_value=result):
                with self.assertRaisesRegex(runner.ProofError, "did not refuse explicitly"):
                    self.proof.require_refusals()


class LinuxNativeAdmissionTests(unittest.TestCase):
    def test_current_virtualapple_cpu_blocks_rosetta_before_any_native_claim(self):
        with tempfile.TemporaryDirectory(prefix="nk-rosetta-") as temp:
            proof = runner.Runner(proof_args(Path(temp) / "proof"))
            with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(runner.platform, "system", return_value="Linux"):
                with mock.patch.object(runner.platform, "machine", return_value="x86_64"), mock.patch.object(runner.Path, "read_text", side_effect=["ordinary maps", "vendor_id : VirtualApple\nflags : sse2\n"]):
                    with mock.patch.object(proof, "oracles") as oracles, mock.patch.object(runner, "set_subreaper") as subreaper:
                        self.assertEqual(proof.run(), 1)
                        oracles.assert_not_called()
                        subreaper.assert_not_called()
            receipt = json.loads((proof.export / "receipt.json").read_text())
            self.assertEqual(receipt["status"], "blocked")
            self.assertEqual(receipt["qualification"], "incomplete")
            self.assertEqual(receipt["host"]["admission"], "unqualified")
            self.assertNotIn("execution", receipt["host"])
            self.assertIn("VirtualApple/Rosetta", receipt["reason"])
            self.assertEqual(receipt["stages"], [])
            self.assertEqual(len(receipt["unproduced_artifacts"]), 4)

    def test_native_cpu_admission_does_not_treat_binfmt_registration_as_translation(self):
        def proc(path):
            return {"/proc/self/maps": "ordinary mappings", "/proc/cpuinfo": "vendor_id : GenuineIntel\nflags : sse2\n",
                    "/proc/sys/fs/binfmt_misc/rosetta": "enabled\ninterpreter /media/rosetta/rosetta\n"}[str(path)]
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(runner.platform, "system", return_value="Linux"):
            with mock.patch.object(runner.platform, "machine", return_value="x86_64"), mock.patch.object(runner.Path, "read_text", autospec=True, side_effect=proc):
                runner.validate_native_host("x86_64")

    def test_linux_host_identity_failures_are_blocked_not_native_proof(self):
        with tempfile.TemporaryDirectory(prefix="nk-admission-") as temp:
            proof = runner.Runner(proof_args(Path(temp) / "proof"))
            with mock.patch.object(runner, "validate_native_host", side_effect=OSError("cannot read CPU identity")):
                with mock.patch.object(proof, "oracles") as oracles:
                    self.assertEqual(proof.run(), 1)
                    oracles.assert_not_called()
            self.assertEqual(proof.receipt["status"], "blocked")
            self.assertNotIn("execution", proof.receipt["host"])


class LinuxRuntimeOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nk-runtime-scope-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def test_scope_is_artifact_only_and_artifact_orphans_still_fail(self):
        for adopted in ([], [{"pid": 123, "status": 9}]):
            proof = runner.Runner(proof_args(self.directory / ("leak" if adopted else "clean")))
            events = []
            with mock.patch.object(runner, "set_subreaper", side_effect=lambda enabled: events.append(enabled)):
                with mock.patch.object(runner, "cleanup_adopted_children", side_effect=lambda: events.append("collect") or adopted):
                    with mock.patch.object(proof, "stage", side_effect=lambda *args, **kwargs: events.append("execute") or stage_result(stdout="NK linux raw passed\n")):
                        if adopted:
                            with self.assertRaisesRegex(runner.ProofError, "leaked a child"):
                                proof.runtime("fixture", "raw", "development", "mapping")
                        else:
                            proof.runtime("fixture", "raw", "development", "mapping")
            self.assertEqual(events, [True, "execute", "collect", False])
            self.assertEqual(proof.receipt["cases"][0]["completion_observed"], not adopted)
            self.assertEqual(proof.receipt["final_adopted_children"], adopted)

    def test_failed_execution_or_cleanup_always_releases_the_scope(self):
        for failure in ("execution", "cleanup"):
            proof = runner.Runner(proof_args(self.directory / failure))
            with mock.patch.object(runner, "set_subreaper") as subreaper:
                with mock.patch.object(runner, "cleanup_adopted_children", side_effect=runner.ProofError("cleanup failed") if failure == "cleanup" else None, return_value=[]):
                    with mock.patch.object(proof, "stage", side_effect=runner.ProofError("execution failed") if failure == "execution" else None, return_value=stage_result()):
                        with self.assertRaises(runner.ProofError):
                            proof.runtime("fixture", "raw", "development", "mapping")
                self.assertEqual(subreaper.call_args_list, [mock.call(True), mock.call(False)])

    def test_pidfd_enosys_or_inexact_output_cannot_complete_a_runtime_case(self):
        for index, result in enumerate((stage_result(exit_code=70), stage_result(stdout="NK_OK linux pidfd\n", exit_code=70),
                                        stage_result(stdout=""), stage_result(stdout="NK_OK linux pidfd\n", stderr="unexpected"),
                                        stage_result(stdout="NK_OK linux pidfd\n", output_truncated=True))):
            proof = runner.Runner(proof_args(self.directory / str(index)))
            with mock.patch.object(runner, "set_subreaper"), mock.patch.object(runner, "cleanup_adopted_children", return_value=[]):
                with mock.patch.object(proof, "stage", return_value=result), self.assertRaises(runner.ProofError):
                    proof.runtime("fixture", "pidfd", "development", "mapping")
            self.assertFalse(proof.receipt["cases"][0]["completion_observed"])
            self.assertEqual(proof.receipt["cases"][0]["status"], "failed")
        pidfd = (ROOT / "spec/native/linux/behavior/pidfd.cr").read_text()
        self.assertIn("return 70 unless own.error == 0", pidfd)

    @unittest.skipUnless(sys.platform == "linux", "native Linux subreaper regression")
    def test_real_preproof_orphan_is_separate_from_a_leaked_artifact_child(self):
        # A disposable outer supervisor owns the pre-proof orphan. The runner
        # process owns ONLY the artifact orphan and must kill/reap/fail it. No
        # subreaper setting or orphan is left in this unittest process.
        child = textwrap.dedent("""\
            import os, time
            read, write = os.pipe()
            if os.fork() == 0:
                os.close(read)
                os.setsid()
                os.close(1)
                os.close(2)
                os.write(write, b"ready")
                os.close(write)
                time.sleep(2)
                os._exit(0)
            os.close(write)
            assert os.read(read, 5) == b"ready"
            os.close(read)
            """)
        artifact = self.directory / "leaky-artifact"
        artifact.write_text("#!" + sys.executable + "\n" + child + 'print("NK linux raw passed", flush=True)\n')
        artifact.chmod(0o755)
        program = textwrap.dedent("""\
            import os, subprocess, sys, traceback
            from pathlib import Path
            sys.path.insert(0, sys.argv[1])
            from test_linux import runner, proof_args
            runner.set_subreaper(True)
            worker = os.fork()
            if worker == 0:
                try:
                    proof = runner.Runner(proof_args(Path(sys.argv[2]) / "proof"))
                    subprocess.run([sys.executable, "-c", sys.argv[4]], check=True, timeout=4)
                    assert runner.cleanup_adopted_children() == []
                    try:
                        proof.runtime(sys.argv[3], "raw", "development", "mapping")
                    except runner.ProofError as error:
                        assert "leaked a child" in str(error), str(error)
                    else:
                        raise AssertionError("artifact orphan incorrectly passed")
                    assert len(proof.receipt["cases"][0]["adopted_children"]) == 1
                    assert not proof.receipt["cases"][0]["completion_observed"]
                    assert runner.cleanup_adopted_children() == []
                except BaseException:
                    traceback.print_exc()
                    os._exit(1)
                os._exit(0)
            _, status = os.waitpid(worker, 0)
            adopted = runner.cleanup_adopted_children()
            runner.set_subreaper(False)
            assert status == 0, status
            assert len(adopted) == 1, adopted
            print("preproof and artifact children separately collected")
            """)
        result = subprocess.run([sys.executable, "-c", program, str(ROOT / "tests"), str(self.directory), str(artifact), child],
                                stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=12)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "preproof and artifact children separately collected\n")
        self.assertEqual(result.stderr, "")

    def test_tools_run_outside_ownership_and_cross_only_never_acquires_it(self):
        for cross in (False, True):
            proof = runner.Runner(proof_args(self.directory / str(cross), cross_target="aarch64" if cross else None))
            proof.host_arch = "x86_64"
            proof.compiler = "fixture-compiler"
            owned, collections = False, []

            def scope(enabled):
                nonlocal owned
                self.assertNotEqual(owned, enabled)
                owned = enabled

            def stage(name, command, **options):
                if name.startswith("execute-"):
                    self.assertTrue(owned)
                    case = command[1]
                    return stage_result(stdout="NK linux raw passed\n" if case == "raw" else "NK_OK linux " + case + "\n")
                self.assertFalse(owned, name)  # Includes the portable child-cleanup tests.
                return stage_result(stdout="23 examples, 0 failures\n" if name == "specs" else "11 examples, 0 failures\n")

            def build(fixture, optimization, auditor):
                self.assertFalse(owned, "compiler/auditor/linker")
                record = {"sha256": "fixture-only", "execution": "unrun"}
                proof.receipt["artifacts"][fixture + "-" + optimization] = record
                return "fixture-artifact", record

            def collect():
                self.assertTrue(owned)
                collections.append("artifact-only")
                return []

            with mock.patch.object(runner, "validate_native_host"), mock.patch.object(runner, "set_subreaper", side_effect=scope) as subreaper:
                with mock.patch.object(proof, "oracles"), mock.patch.object(proof, "identify_compiler"), mock.patch.object(proof, "stage", side_effect=stage):
                    with mock.patch.object(proof, "rejection_tests"), mock.patch.object(proof, "require_refusals"), mock.patch.object(proof, "build_probe", side_effect=build):
                        with mock.patch.object(runner, "cleanup_adopted_children", side_effect=collect):
                            self.assertEqual(proof.run(), 0, proof.receipt.get("reason"))
            self.assertFalse(owned)
            self.assertEqual(len(collections), 0 if cross else 22)
            self.assertEqual(proof.receipt["qualification"], "incomplete")
            if cross:
                subreaper.assert_not_called()
                self.assertNotIn("orphan_ownership", proof.receipt["host"])
                self.assertEqual(proof.receipt["status"], "cross-compile-only")
                self.assertEqual(proof.receipt["cases"], [])
            else:
                self.assertEqual(proof.receipt["status"], "mechanisms-passed")
                self.assertEqual(proof.receipt["final_adopted_children"], [])


class LinuxRunnerContracts(unittest.TestCase):
    def test_header_dependency_hashes_include_system_headers_and_spaces(self):
        with tempfile.TemporaryDirectory(prefix="nk-headers-") as temp:
            path = Path(temp)
            (path / "local.c").write_text("source")
            (path / "system header.h").write_text("header")
            (path / "deps").write_text("a: local.c \\\n system\\ header.h\n")
            hashes = runner.header_hashes(path / "deps", path)
            self.assertEqual(set(hashes), {str((path / "local.c").resolve()), str((path / "system header.h").resolve())})

    def test_native_host_rejects_wrong_os_architecture_and_emulation(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(runner.platform, "system", return_value="Darwin"):
            with self.assertRaises(runner.ProofError):
                runner.validate_native_host("x86_64")
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(runner.platform, "system", return_value="Linux"), mock.patch.object(runner.platform, "machine", return_value="aarch64"):
            with self.assertRaises(runner.ProofError):
                runner.validate_native_host("x86_64")
        with mock.patch.object(runner.platform, "system", return_value="Linux"), mock.patch.object(runner.platform, "machine", return_value="x86_64"), mock.patch.dict(os.environ, {"QEMU_CPU": "test"}, clear=True):
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
