#!/usr/bin/env python3
"""Source-bound Linux mechanisms proof. Standard library only; no consumer policy.

No C oracle, cross build or kernel version substitutes for executing the audited
Crystal artifacts. A passed mechanisms run still leaves the listed qualification
limits (notably genuinely delivered EINTR) explicit in its receipt.
"""
import argparse
import base64
import ctypes
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import signal
import struct
import sys
import time

# Reuse the reviewed bounded capture/leader reservation, not Darwin admission.
_COMMON_SPEC = importlib.util.spec_from_file_location("nk_bounded_runner", Path(__file__).with_name("runner.py"))
common = importlib.util.module_from_spec(_COMMON_SPEC)
_COMMON_SPEC.loader.exec_module(common)
ROOT = Path(__file__).resolve().parents[2]
ARCHITECTURES = {"x86_64": 62, "aarch64": 183}
CASES = ("descriptor", "exec", "process", "pidfd", "poll", "collection", "signal-status", "copyout", "resource", "leaks")


class ProofError(Exception):
    pass


def source_identity(root):
    sources = common.source_identity(root)
    for path in (Path(root) / "docs").glob("linux*.md"):
        sources[path.relative_to(root).as_posix()] = common.sha256_file(path)
    for name in ("README.md", "docs/support.md", "ci/README.md"):
        sources[name] = common.sha256_file(Path(root) / name)
    return dict(sorted(sources.items()))


def elf_identity(path, architecture, *, executable=True):
    """Read ELF identity/segments directly; readelf/nm evidence is also retained."""
    data = Path(path).read_bytes()
    if len(data) < 64 or data[:7] != b"\x7fELF\x02\x01\x01":
        raise ProofError("Expected little-endian ELF64")
    kind, machine = struct.unpack_from("<HH", data, 16)
    if machine != ARCHITECTURES[architecture] or kind != (2 if executable else 1):
        raise ProofError("ELF machine/type differs from selected profile")
    entry, phoff, shoff = struct.unpack_from("<QQQ", data, 24)
    phsize, phnum, shsize, shnum, names_index = struct.unpack_from("<HHHHH", data, 54)
    if not executable:
        return {"architecture": architecture, "machine": machine, "type": kind}
    if phnum == 0 or phsize != 56 or phnum > 128 or phoff + phnum * phsize > len(data):
        raise ProofError("Invalid ELF program table")
    entry_in_code = False
    for index in range(phnum):
        start = phoff + index * phsize
        segment, flags, offset, address, physical, filesz, memsz, alignment = struct.unpack_from("<IIQQQQQQ", data, start)
        if segment in (2, 3):
            raise ProofError("Standalone ELF has a dynamic segment or interpreter")
        if offset + filesz > len(data) or filesz > memsz:
            raise ProofError("Invalid ELF segment extent")
        if segment == 1 and flags & 1 and address <= entry < address + memsz:
            entry_in_code = True
        if segment in (1, 0x6474e551) and flags & 1 and flags & 2:
            raise ProofError("Writable executable segment/stack")
    if not entry_in_code:
        raise ProofError("ELF entry is not in an executable load segment")
    if shsize != 64 or not (0 < names_index < shnum < 65535) or shoff + shnum * shsize > len(data):
        raise ProofError("Invalid ELF section table")
    name_offset, name_size = struct.unpack_from("<QQ", data, shoff + names_index * shsize + 24)
    if name_offset + name_size > len(data):
        raise ProofError("Invalid ELF section names")
    names = data[name_offset:name_offset + name_size]
    for index in range(shnum):
        section = shoff + index * shsize
        name = struct.unpack_from("<I", data, section)[0]
        size = struct.unpack_from("<Q", data, section + 32)[0]
        label = names[name:].split(b"\0", 1)[0]
        if size and label in (b".init_array", b".fini_array", b".preinit_array", b".ctors", b".dtors"):
            raise ProofError("ELF contains initialization/finalization arrays")
    return {"architecture": architecture, "machine": machine, "type": kind, "entry": entry,
            "interpreter": False, "dynamic_segment": False, "initializers": False}


def elf_object_sections(path, architecture, function_count, *, llvm_function_sections=False):
    """Validate every object section and, for llc output, its one-function mapping."""
    identity = elf_identity(path, architecture, executable=False)
    data = Path(path).read_bytes()
    shoff = struct.unpack_from("<Q", data, 40)[0]
    shsize, shnum, names_index = struct.unpack_from("<HHH", data, 58)
    if function_count < 1 or shsize != 64 or not (0 < names_index < shnum < 65535) or shoff + shnum * shsize > len(data):
        raise ProofError("Invalid ELF object section table")
    names_header = struct.unpack_from("<IIQQQQIIQQ", data, shoff + names_index * shsize)
    name_offset, name_size = names_header[4:6]
    if names_header[1] != 3 or not name_size or name_offset + name_size > len(data):
        raise ProofError("Invalid ELF object section names")
    names = data[name_offset:name_offset + name_size]
    sections, function_sections, executable_sections = [], {}, []
    for index in range(shnum):
        fields = struct.unpack_from("<IIQQQQIIQQ", data, shoff + index * shsize)
        name, kind, flags, address, offset, size, link, info, alignment, entry_size = fields
        end = names.find(b"\0", name)
        if name >= len(names) or end == -1:
            raise ProofError("Invalid ELF object section name")
        label = names[name:end]
        if kind != 8 and offset + size > len(data):  # SHT_NOBITS has no file payload.
            raise ProofError("Invalid ELF object section extent")
        if flags & 1 and flags & 4:
            raise ProofError("Writable executable ELF object section")
        if size and (kind in (14, 15, 16) or label in (b".init_array", b".fini_array", b".preinit_array", b".ctors", b".dtors")):
            raise ProofError("ELF object contains initialization/finalization arrays")
        section = {"index": index, "name": label, "kind": kind, "flags": flags, "address": address,
                   "offset": offset, "size": size, "link": link, "info": info, "entry_size": entry_size}
        sections.append(section)
        if flags & 4 and size:
            executable_sections.append(section)
        if llvm_function_sections and label.startswith(b".text."):
            if label in function_sections or kind != 1 or flags & 7 != 6 or size == 0:
                raise ProofError("Invalid or duplicate LLVM per-function text section")
            function_sections[label] = section
        elif not llvm_function_sections and label.startswith(b".text.nk."):
            if label in function_sections or kind != 1 or flags & 7 != 6:
                raise ProofError("Invalid or duplicate transformed function section")
            function_sections[label] = section
    if not llvm_function_sections:
        expected = {(".text.nk." + str(index)).encode() for index in range(function_count)}
        if set(function_sections) != expected:
            raise ProofError("Transformed ELF function-section roster differs from emitted assembly")
        return dict(identity, sections=shnum, function_sections=len(function_sections),
                    all_sections_validated=True, initializers=False, writable_executable_sections=False)

    # Direct LLVM IR-to-object lowering avoids the floor assembly printer's
    # malformed escaped quoted local symbols. Require the output's complete
    # STT_FUNC roster to correspond one-for-one with executable .text.<symbol>
    # sections, as requested with -function-sections. No instruction text or IR
    # is repaired or filtered, and no permissive assembler parser is involved.
    if len(function_sections) != function_count or any(not section["name"].startswith(b".text.") for section in executable_sections):
        raise ProofError("LLVM object does not have the complete per-function text-section roster")
    symtabs = [section for section in sections if section["kind"] == 2]
    if len(symtabs) != 1:
        raise ProofError("LLVM object must have exactly one ELF symbol table")
    symtab = symtabs[0]
    symbol_count = symtab["size"] // 24
    if (symtab["entry_size"] != 24 or symtab["size"] % 24 or symtab["link"] >= len(sections) or
            sections[symtab["link"]]["kind"] != 3 or not 1 <= symtab["info"] <= symbol_count):
        raise ProofError("Malformed LLVM object symbol table/string table")
    string_section = sections[symtab["link"]]
    strings = data[string_section["offset"]:string_section["offset"] + string_section["size"]]
    symbols_by_section, function_symbols = {}, []
    for offset in range(symtab["offset"], symtab["offset"] + symtab["size"], 24):
        name_offset, info, other, section_index, value, size = struct.unpack_from("<IBBHQQ", data, offset)
        if info & 0xF != 2 or section_index == 0:  # STT_FUNC, defined in this object.
            continue
        end = strings.find(b"\0", name_offset)
        if name_offset >= len(strings) or end == -1 or end == name_offset:
            raise ProofError("Malformed or unnamed defined LLVM function symbol")
        symbol = strings[name_offset:end]
        if section_index >= len(sections):
            raise ProofError("LLVM function symbol has an invalid section index")
        section = sections[section_index]
        if section["name"] not in function_sections or not section["flags"] & 4:
            raise ProofError("Defined LLVM function is outside a dedicated executable text section")
        if size == 0 or value > section["size"] or size > section["size"] - value:
            raise ProofError("LLVM function symbol has an invalid extent in its text section")
        function_symbols.append(symbol)
        symbols_by_section.setdefault(section_index, []).append(symbol)
    if (len(function_symbols) != function_count or len(set(function_symbols)) != function_count or
            set(symbols_by_section) != {section["index"] for section in function_sections.values()} or
            any(len(symbols) != 1 for symbols in symbols_by_section.values())):
        raise ProofError("LLVM function symbols do not map one-to-one to emitted function sections")
    digest = lambda values: hashlib.sha256(b"\0".join(sorted(values))).hexdigest()
    return dict(identity, sections=shnum, function_sections=len(function_sections),
                function_symbols=len(function_symbols), function_symbols_sha256=digest(function_symbols),
                function_sections_sha256=digest(list(function_sections)), all_sections_validated=True,
                initializers=False, writable_executable_sections=False)


def crystal_search_directories(environment, root):
    """Parse Crystal's shell-escaped search list in the compiler's lookup order."""
    assignments = [line.partition("=")[2] for line in environment.splitlines() if line.startswith("CRYSTAL_PATH=")]
    if len(assignments) != 1:
        raise ProofError("Expected one CRYSTAL_PATH in crystal env")
    try:
        values = shlex.split(assignments[0], comments=False, posix=True)
    except ValueError as error:
        raise ProofError("Malformed CRYSTAL_PATH in crystal env: " + str(error)) from error
    if len(values) != 1 or not values[0] or any(char in values[0] for char in "\0\n\r"):
        raise ProofError("Expected one nonempty CRYSTAL_PATH value")
    paths = values[0].split(":")  # The reviewed Linux compilers use POSIX path lists.
    if any(not path for path in paths):
        raise ProofError("Empty CRYSTAL_PATH search entry")
    directories = [(Path(root) / path).resolve() for path in paths if (Path(root) / path).is_dir()]
    if not directories or crystal_require_source("prelude", directories) is None:
        raise ProofError("Cannot locate the selected Crystal standard-library directory")
    return directories


def crystal_require_source(filename, directories):
    """Mirror Crystal 1.10/1.22's first-file require expansion for a logical name."""
    relative = Path(filename)
    if relative.is_absolute() or "\0" in filename or "\n" in filename or "\r" in filename:
        raise ProofError("Unexpected absolute or malformed compiler require name")
    for directory in directories:
        base = directory / relative
        candidates = [base if filename.endswith(".cr") else Path(str(base) + ".cr")]
        filename_is_relative = filename.startswith(".")
        parts = filename.partition("/")
        shard_name, has_separator, shard_path = parts
        if not filename_is_relative and has_separator:
            shard_source = directory / shard_name / "src"
            shard_path_stem = shard_path[:-3] if shard_path.endswith(".cr") else shard_path
            candidates.extend((shard_source / (shard_path_stem + ".cr"),
                               shard_source / shard_name / (shard_path_stem + ".cr"),
                               base / (base.name.removesuffix(".cr") + ".cr"),
                               shard_source / shard_path / (shard_path_stem + ".cr"),
                               shard_source / shard_name / shard_path / (shard_path_stem + ".cr")))
        else:
            basename = base.name.removesuffix(".cr")
            candidates.append(base / (basename + ".cr"))
            if not filename_is_relative:
                candidates.append(base / "src" / (basename + ".cr"))
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()
    return None


def crystal_stdlib_sources(environment, root):
    """Bind every selected search-source tree, including the actual stdlib."""
    sources = {str(path): common.sha256_file(path) for directory in crystal_search_directories(environment, root)
               for path in sorted(directory.rglob("*.cr"))}
    if not sources:
        raise ProofError("Cannot identify the selected Crystal standard-library sources")
    return sources


def crystal_relative_path(path, directory):
    """Make an explicit relative require path from the file's source directory."""
    relative = Path(os.path.relpath(path, directory)).as_posix()
    return relative if relative.startswith(("./", "../")) else "./" + relative


def floor_prelude_bytes(original):
    """Remove only 1.10's exact standalone managed-main require, byte for byte.

    The selected compiler's prelude is the input, not a vendored stdlib. Refuse
    absent, duplicate or malformed active main references instead of guessing at
    other prelude shapes. Comments are inert and remain completely unchanged.
    """
    lines = original.splitlines(keepends=True)
    mentions = [index for index, line in enumerate(lines)
                if b"crystal/main" in line and not line.lstrip().startswith(b"#")]
    expected = b'require "crystal/main"'
    if len(mentions) != 1 or lines[mentions[0]] not in (expected, expected + b"\n", expected + b"\r\n"):
        raise ProofError('Floor prelude must contain exactly one standalone require "crystal/main"')
    index = mentions[0]
    offset, removed = sum(map(len, lines[:index])), lines[index]
    generated = original[:offset] + original[offset + len(removed):]
    if generated[:offset] + removed + generated[offset:] != original:
        raise ProofError("Floor prelude transformation changed other bytes")
    return generated, {"operation": 'Remove exactly the single standalone require "crystal/main" line; no other bytes changed',
                       "removed_line": removed.decode("ascii"), "line_number": index + 1,
                       "byte_offset": offset, "original_size": len(original), "generated_size": len(generated),
                       "all_other_bytes_preserved": True}


def floor_stdio_helper_bytes(original):
    """Extract only the exact 1.10 stdio helper needed by kernel.cr's exit definitions."""
    lines = original.splitlines(keepends=True)
    definitions = [index for index, line in enumerate(lines)
                   if b"def self.ignore_stdio_errors" in line and not line.lstrip().startswith(b"#")]
    expected = (b"  def self.ignore_stdio_errors(&)\n", b"    yield\n", b"  rescue IO::Error\n", b"  end\n")
    if len(definitions) != 1 or tuple(lines[definitions[0]:definitions[0] + len(expected)]) != expected:
        raise ProofError("Selected floor main source must contain exactly the expected ignore_stdio_errors helper")
    index = definitions[0]
    offset = sum(map(len, lines[:index]))
    helper = b"".join(lines[index:index + len(expected)])
    return helper, {"operation": "Select only the exact Crystal.ignore_stdio_errors method; no other main.cr bytes are copied",
                    "line_number": index + 1, "byte_offset": offset, "method_size": len(helper),
                    "method_sha256": hashlib.sha256(helper).hexdigest(), "all_other_main_bytes_omitted": True}


FLOOR_UNMANAGED_ADAPTER_OPERATION = "Expose only the selected Crystal.ignore_stdio_errors helper before requiring the exact main-free prelude"


def floor_unmanaged_adapter_bytes(prelude_path, adapter_path, helper):
    """Expose the exact floor helper before loading the unchanged derived prelude."""
    relative = crystal_relative_path(prelude_path, Path(adapter_path).parent)
    return b"module Crystal\n" + helper + b"end\nrequire " + json.dumps(relative).encode("ascii") + b"\n"


def check_floor_prelude(record):
    """Recheck selected/generated prelude and helper adapter before builds and at exit."""
    try:
        original = Path(record["original_path"]).read_bytes()
        generated = Path(record["generated_path"]).read_bytes()
        adapter = record["adapter"]
        helper_source = Path(adapter["source_path"]).read_bytes()
        adapter_bytes = Path(adapter["generated_path"]).read_bytes()
        expected, transformation = floor_prelude_bytes(original)
        helper, helper_transformation = floor_stdio_helper_bytes(helper_source)
        expected_adapter = floor_unmanaged_adapter_bytes(record["generated_path"], adapter["generated_path"], helper)
    except (KeyError, TypeError) as error:
        raise ProofError("Floor prelude/adapter receipt is incomplete") from error
    if (hashlib.sha256(original).hexdigest() != record["original_sha256"] or
            hashlib.sha256(generated).hexdigest() != record["generated_sha256"] or
            generated != expected or transformation != record["transformation"] or
            hashlib.sha256(helper_source).hexdigest() != adapter["source_sha256"] or
            hashlib.sha256(helper).hexdigest() != adapter["method_sha256"] or
            helper_transformation != adapter["transformation"] or
            adapter.get("operation") != FLOOR_UNMANAGED_ADAPTER_OPERATION or
            hashlib.sha256(adapter_bytes).hexdigest() != adapter["generated_sha256"] or
            adapter_bytes != expected_adapter):
        raise ProofError("Selected/generated floor prelude, helper source or exact adapter transformation changed")


def function_sections(assembly, architecture):
    """Give each compiler-emitted ELF function its own GC section.

    Crystal's O0 single-module object otherwise shares .text with unused runtime
    helpers. Preserve EVERY original assembly line/instruction and add only a
    section switch/alignment before a complete .type ... function / .size pair.
    Audit the unmodified emitted LLVM first; never prune functions or imports to
    make that audit pass. This is a layout-only, source-bound build step, not a
    second compiler, IR filter, unmanaged API dependency or audit exemption.
    """
    marker = "@" if architecture == "x86_64" else "%"
    result, functions, active, labeled = [], [], None, False
    for line in assembly.splitlines(keepends=True):
        if re.match(r'^\s*\.section\s+\.debug_', line):
            raise ProofError("Function-section assembly requires the --no-debug build")
        match = re.match(r'^\s*\.type\s+(.+?),\s*[@%]function\s*(?:[#/].*)?$', line)
        if match:
            symbol = match[1].strip()
            if active or symbol in functions:
                raise ProofError("Incomplete/duplicate emitted assembly function")
            active, labeled = symbol, False
            result.append('.section .text.nk.' + str(len(functions)) + ',"ax",' + marker + 'progbits\n.p2align 4\n')
            functions.append(symbol)
        elif active:
            if re.match(r'^\s*\.(?:section|text|pushsection|popsection)\b', line):
                raise ProofError("Unexpected emitted section switch inside a function")
            if re.match(r'^\s*' + re.escape(active) + r':\s*(?:(?:#|//).*)?$', line):
                labeled = True
            if re.match(r'^\s*\.size\s+' + re.escape(active) + r'\s*,', line):
                if not labeled:
                    raise ProofError("Emitted assembly function lacks its label")
                active = None
        result.append(line)
    if active or not functions:
        raise ProofError("Emitted assembly lacks complete ELF functions")
    return "".join(result), functions


def validate_native_host(architecture):
    actual = platform.machine()
    if platform.system() != "Linux" or actual != architecture or struct.calcsize("P") != 8:
        raise ProofError("Native execution requires matching non-Android Linux LP64")
    if hasattr(sys, "getandroidapilevel") or os.environ.get("ANDROID_ROOT"):
        raise ProofError("Android is not admitted")
    expected_runner = "X64" if architecture == "x86_64" else "ARM64"
    if os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("RUNNER_ARCH") != expected_runner:
        raise ProofError("Runner architecture differs from the native profile")
    if any(name.startswith("QEMU_") for name in os.environ):
        raise ProofError("Emulated execution cannot qualify a native profile")
    maps = Path("/proc/self/maps").read_text()
    if re.search(r"qemu|box64|FEXInterpreter", maps, re.I):
        raise ProofError("Translated execution cannot qualify a native profile")
    cpu = Path("/proc/cpuinfo").read_text()
    # VirtualApple is positive evidence about this x86 process/CPU (Rosetta),
    # unlike a globally registered binfmt handler which might not be in use.
    if architecture == "x86_64" and re.search(r"^vendor_id\s*:\s*VirtualApple\s*$", cpu, re.M | re.I):
        raise ProofError("Translated VirtualApple/Rosetta x86-64 CPU cannot qualify native execution")
    # Distinguish a native hosted architecture from a user-mode emulator's uname.
    if architecture == "x86_64" and not re.search(r"^flags\s*:", cpu, re.M):
        raise ProofError("Cannot establish x86-64 CPU profile")
    if architecture == "aarch64" and not re.search(r"^CPU implementer\s*:", cpu, re.M):
        raise ProofError("Cannot establish AArch64 CPU profile")


def header_hashes(dependency_file, root=ROOT):
    content = Path(dependency_file).read_text().replace("\\\n", " ")
    dependencies = shlex.split(content.split(":", 1)[1])
    paths = [Path(name) if Path(name).is_absolute() else Path(root) / name for name in dependencies]
    return {str(path.resolve()): common.sha256_file(path) for path in paths}


def set_subreaper(enabled):
    # Driver-only failure containment, scoped to native artifact execution.
    # Never adopt the portable tests' or compiler tools' grandchildren.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, int(enabled), 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise ProofError("Cannot set artifact orphan ownership: errno " + str(ctypes.get_errno()))


def cleanup_adopted_children():
    """The driver exclusively collects fixture orphans, never arbitrary PIDs."""
    path = Path(f"/proc/self/task/{os.getpid()}/children")
    adopted, deadline = [], time.monotonic() + 3
    while True:
        children = [int(pid) for pid in path.read_text().split()]
        if not children:
            return adopted
        for pid in children:
            # Still our unreaped child; no competing waiter or failed-creation PID.
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            got, status = os.waitpid(pid, os.WNOHANG)
            if got:
                adopted.append({"pid": pid, "status": status})
        if time.monotonic() >= deadline:
            raise ProofError("Fixture child cleanup exceeded its deadline")
        time.sleep(0.001)


class Runner:
    def __init__(self, args, root=ROOT):
        self.args, self.root = args, Path(root).resolve()
        self.output = Path(args.output).expanduser().resolve()
        if self.output == self.root or self.output.is_relative_to(self.root):
            raise ProofError("Evidence/cache/build directory must be outside the repository")
        if self.output.exists():
            raise ProofError("Choose a new evidence directory")
        self.export = self.output / "export"
        self.export.mkdir(parents=True)
        self.logs = self.export / "logs"
        self.logs.mkdir()
        self.build = self.output / "build"
        self.build.mkdir()
        self.host_arch = platform.machine()
        self.architecture = args.cross_target or args.architecture or self.host_arch
        self.cross = bool(args.cross_target)
        self.config = json.loads((self.root / "ci/linux.json").read_text())
        if tuple(self.config["cases"]) != CASES or self.architecture not in ARCHITECTURES:
            raise ProofError("Invalid Linux case/architecture selection")
        self.env = dict(os.environ, CRYSTAL_CACHE_DIR=str(self.output / "cache"),
                        PYTHONDONTWRITEBYTECODE="1", NK_ELF_PROOF="stack-arguments")
        self.cc = shlex.split(args.cc)
        if not self.cc:
            raise ProofError("Select a nonempty C compiler command")
        self.compiler_llvm_version = None
        self.llvm_llc = None
        self.llvm_llc_version = None
        self.receipt = {
            "schema": 1, "status": "incomplete", "qualification": "incomplete",
            "mode": "cross-compile-only" if self.cross else "native",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "source_before": source_identity(self.root), "stages": [], "cases": [], "artifacts": {},
            "host": {"system": platform.system(), "architecture": self.host_arch,
                     "kernel": platform.release(), "version": platform.version(),
                     "os_release": Path("/etc/os-release").read_text() if Path("/etc/os-release").exists() else None,
                     "proc_status": Path("/proc/self/status").read_text() if Path("/proc/self/status").exists() else None},
            "architecture": self.architecture, "limits": self.config["limits"],
            "expected_compiler": args.expected_compiler,
            "configuration": self.config,
            "workflow": {key: value for key, value in os.environ.items() if key in
                         ("GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_REPOSITORY", "RUNNER_ARCH", "RUNNER_OS", "ImageOS", "ImageVersion")}}
        self.write()

    def write(self):
        common.write_json(self.export / "receipt.json", self.receipt)

    def stage(self, name, command, *, timeout=300, require=True):
        result = common.run_bounded(command, self.logs / name, timeout=timeout, cwd=self.root, env=self.env)
        result["name"] = name
        if result["output_truncated"]:
            result["status"] = "failed"
            result["reason"] = "Output exceeded the 64-KiB per-stream capture bound"
        self.receipt["stages"].append(result)
        self.write()
        if require and result["status"] != "passed":
            raise ProofError("Stage failed: " + name)
        return result

    def artifact(self, name, path, *, ir=None, obj=None):
        record = {"sha256": common.sha256_file(path), "path": str(path),
                  "execution": "unrun"}
        if ir:
            record["llvm_sha256"] = common.sha256_file(ir)
            with gzip.open(self.export / (name + ".ll.gz"), "wb") as stream:
                stream.write(Path(ir).read_bytes())
        if obj:
            record["object_sha256"] = common.sha256_file(obj)
        self.receipt["artifacts"][name] = record
        shutil.copy2(path, self.export / name)
        self.write()
        return record

    def inspect(self, name, path):
        identity = elf_identity(path, self.architecture)
        self.stage("readelf-" + name, ["readelf", "-h", "-l", "-d", "-S", "-W", str(path)])
        imports = self.stage("imports-" + name, ["nm", "-u", str(path)])
        if imports["stdout"].strip() or imports["stderr"].strip():
            raise ProofError("Standalone executable has undefined imports")
        symbols = self.stage("symbols-" + name, ["nm", "--defined-only", str(path)])
        start = re.search(r"^([0-9a-f]+) T _start$", symbols["stdout"], re.M)
        if not start or int(start[1], 16) != identity["entry"]:
            raise ProofError("ELF e_entry does not designate the original _start")
        if re.search(r"\b(?:__crystal_|GC_|__cxa|__gxx|_Unwind|__libc)", symbols["stdout"]):
            raise ProofError("Standalone executable retains Crystal/managed initialization or runtime")
        if not self.cross:
            self.stage("disassemble-entry-" + name, ["objdump", "--disassemble=_start", str(path)])
        return identity

    def oracles(self):
        self.stage("identity-uname", ["uname", "-a"], timeout=20)
        self.receipt["git_head"] = self.stage("identity-git-head", ["git", "rev-parse", "HEAD"], timeout=20)["stdout"].strip()
        self.receipt["git_branch"] = self.stage("identity-git-branch", ["git", "branch", "--show-current"], timeout=20)["stdout"].strip()
        self.stage("identity-cc", self.cc + ["--version"], timeout=20)
        self.stage("identity-ld", ["ld", "--version"], timeout=20)
        self.stage("identity-readelf", ["readelf", "--version"], timeout=20)
        self.stage("identity-nm", ["nm", "--version"], timeout=20)
        tools = {"cc_driver": self.cc[0], "ld": "ld", "readelf": "readelf", "nm": "nm"}
        if not self.cross:
            tools["objdump"] = "objdump"
        self.receipt["tools"] = {}
        for name, command in tools.items():
            path = Path(shutil.which(command) or command).resolve()
            self.receipt["tools"][name] = {"path": str(path), "sha256": common.sha256_file(path)}
        self.receipt["tools_scope"] = "selected driver/tool binaries, not every SDK/shared-library/linker input"
        dependency = self.build / "layout.d"
        oracle = self.build / ("layout.o" if self.cross else "layout")
        flags = ["-std=c11", "-Wall", "-Wextra", "-Werror", "-MD", "-MF", str(dependency)]
        if self.cross:
            flags += ["-DNK_LAYOUT_ONLY", "-c"]
        self.stage("compile-layout", self.cc + flags + ["scripts/ci/linux-layout.c", "-o", str(oracle)])
        self.receipt["layout_oracle"] = {"headers": "installed UAPI, not pinned Linux v6.6 headers",
                                         "header_sha256": header_hashes(dependency, self.root), "object_or_executable_sha256": common.sha256_file(oracle)}
        if not self.cross:
            self.stage("execute-layout", [str(oracle)], timeout=10)
            capabilities = self.build / "capabilities"
            self.stage("compile-capabilities", self.cc + ["-std=c11", "-Wall", "-Wextra", "-Werror", "scripts/ci/linux-capabilities.c", "-o", str(capabilities)])
            result = self.stage("execute-capabilities", [str(capabilities)], timeout=10)
            self.receipt["capabilities"] = {"scope": "libc C diagnostic, not Crystal native proof", "observed": json.loads(result["stdout"])}
        startup = self.root / ("spec/native/linux/start-" + self.architecture + ".S")
        self.receipt["startup"] = {"source_path": startup.relative_to(self.root).as_posix(),
                                   "source_bytes": startup.read_text(), "sha256": common.sha256_file(startup)}
        start = self.build / "start.o"
        self.stage("assemble-start", self.cc + ["-c", str(startup), "-o", str(start)])
        elf_identity(start, self.architecture, executable=False)
        self.receipt["startup"]["object_sha256"] = common.sha256_file(start)
        c_object, c_program = self.build / "start-check.o", self.build / "start-check"
        self.stage("compile-startup-oracle", self.cc + ["-c", "-ffreestanding", "-fno-builtin", "-fno-stack-protector", "-fno-pie", "-ffunction-sections", "-fdata-sections", "-Wall", "-Wextra", "-Werror", "spec/native/linux/start_check.c", "-o", str(c_object)])
        self.link("startup-oracle", c_object, c_program)
        c_elf = self.inspect("startup-oracle", c_program)
        artifact = self.artifact("startup-oracle", c_program, obj=c_object)
        artifact["identity"] = c_elf
        artifact["scope"] = "C startup-only; NOT Crystal unmanaged proof"
        if not self.cross:
            self.stage("execute-startup-oracle", [str(c_program), "startup", "ELF-argument", "ignored"], timeout=10)
            artifact["execution"] = "native-startup-only-passed"
        self.write()

    def link(self, name, obj, program):
        self.stage("link-" + name, self.cc + ["-nostdlib", "-static", "-no-pie", "-Wl,--gc-sections,--build-id=none,-e,_start",
                                            str(self.build / "start.o"), str(obj), "-o", str(program)])

    def identify_compiler(self):
        compiler = shutil.which(self.args.compiler) if "/" not in self.args.compiler else self.args.compiler
        if not compiler or not Path(compiler).is_file():
            self.receipt["status"] = "blocked"
            raise ProofError("Exact Crystal compiler unavailable: " + self.args.compiler)
        compiler = str(Path(compiler).resolve())
        result = self.stage("identity-compiler", [compiler, "--version"], timeout=20)
        version, target = common.compiler_version(result["stdout"])
        if version not in self.config["compilers"] or (self.args.expected_compiler and self.args.expected_compiler != version):
            raise ProofError("Compiler must match the exact reviewed release")
        llvm_version = re.search(r"^LLVM:\s*(\d+(?:\.\d+)+)\s*$", result["stdout"], re.M)
        if not llvm_version:
            raise ProofError("Compiler identity does not report its LLVM major/minor version")
        self.compiler_llvm_version = llvm_version[1]
        if version == "1.10.0" and self.compiler_llvm_version.split(".", 1)[0] != "15":
            raise ProofError("Crystal 1.10.0 floor codegen requires the reviewed LLVM 15 compiler backend")
        if not target.startswith(self.host_arch + "-") or not re.search(r"linux-(?:gnu|musl)$", target):
            raise ProofError("Compiler default target must be native non-Android LP64 Linux")
        # Official Linux archives contain a direct ELF executable. An arbitrary
        # launcher is not identified merely by trusting its --version output.
        binary = Path(compiler).read_bytes()
        if len(binary) < 64 or binary[:7] != b"\x7fELF\x02\x01\x01" or struct.unpack_from("<H", binary, 18)[0] != ARCHITECTURES[self.host_arch]:
            raise ProofError("Select the actual native ELF Crystal binary, not a wrapper")
        self.receipt["compiler"] = {"path": compiler, "sha256": common.sha256_file(compiler), "version": version,
                                    "llvm_version": self.compiler_llvm_version, "default_target": target, "description": result["stdout"],
                                    "identity_scope": "compiler ELF and selected stdlib (not all SDK/linker inputs)"}
        self.env["CRYSTAL"] = compiler
        environment = self.stage("compiler-env", [compiler, "env"], timeout=20)
        self.receipt["compiler"]["environment"] = environment["stdout"]
        self.receipt["compiler"]["stdlib_sha256"] = crystal_stdlib_sources(environment["stdout"], self.root)
        self.compiler, self.version = compiler, version
        self.prepare_unmanaged_entry(environment["stdout"])

    def prepare_unmanaged_entry(self, environment):
        entry = self.receipt["unmanaged_entry"] = {"strategy": "compiler-without-main-flag", "flags": ["-Dwithout_main"]}
        if self.version == "1.10.0":
            # This release ignores without_main and always requires crystal/main.
            # Use its actual first-selected prelude, changing no other stdlib input.
            directories = crystal_search_directories(environment, self.root)
            original = crystal_require_source("prelude", directories)
            main_source = crystal_require_source("crystal/main", directories)
            if original is None or main_source is None:
                raise ProofError("Cannot locate the selected floor prelude and main source")
            data, main_data = original.read_bytes(), main_source.read_bytes()
            digest, main_digest = hashlib.sha256(data).hexdigest(), hashlib.sha256(main_data).hexdigest()
            selected_sources = self.receipt["compiler"]["stdlib_sha256"]
            if selected_sources.get(str(original)) != digest:
                raise ProofError("Selected floor prelude differs from the hashed compiler inputs")
            if selected_sources.get(str(main_source)) != main_digest:
                raise ProofError("Selected floor main source differs from the hashed compiler inputs")
            generated, transformation = floor_prelude_bytes(data)
            helper, helper_transformation = floor_stdio_helper_bytes(main_data)
            path = self.build / "prelude-without-main-1.10.0.cr"
            path.write_bytes(generated)
            adapter_path = self.build / "unmanaged-prelude-1.10.0.cr"
            adapter_bytes = floor_unmanaged_adapter_bytes(path, adapter_path, helper)
            adapter_path.write_bytes(adapter_bytes)
            adapter = {"source_path": str(main_source), "source_sha256": main_digest,
                       "method_sha256": hashlib.sha256(helper).hexdigest(), "transformation": helper_transformation,
                       "generated_path": str(adapter_path), "generated_sha256": common.sha256_file(adapter_path),
                       "operation": FLOOR_UNMANAGED_ADAPTER_OPERATION}
            prelude = {"original_path": str(original), "original_sha256": digest,
                       "generated_path": str(path), "generated_sha256": common.sha256_file(path),
                       "transformation": transformation, "adapter": adapter}
            check_floor_prelude(prelude)
            source_directory = self.root / "spec/native/linux"
            entry.update(strategy="selected-floor-prelude-minus-main-with-stdio-helper", prelude=prelude,
                         flags=["-Dwithout_main", "--prelude", crystal_relative_path(adapter_path, source_directory)])
            # Retain the exact generated prelude and minimal adapter as evidence.
            shutil.copy2(path, self.export / path.name)
            shutil.copy2(adapter_path, self.export / adapter_path.name)
        self.write()

    def unmanaged_flags(self, source):
        if self.version != "1.10.0":
            return ["-Dwithout_main"]
        entry = self.receipt.get("unmanaged_entry", {})
        prelude = entry.get("prelude")
        if not prelude:
            raise ProofError("Floor unmanaged build requires the source-bound generated prelude")
        check_floor_prelude(prelude)
        adapter = prelude.get("adapter")
        if not adapter:
            raise ProofError("Floor unmanaged build requires the source-bound no-main adapter")
        return ["-Dwithout_main", "--prelude", crystal_relative_path(adapter["generated_path"], Path(source).parent)]

    def rejection_tests(self, auditor):
        reasons = {"external": "unapproved symbol write", "mutable": "mutable global", "incorrect": "indirect or unrecognized", "darwin": "indirect or unrecognized"}
        for architecture in ARCHITECTURES:
            for fixture, reason in reasons.items():
                result = self.stage("reject-" + architecture + "-" + fixture,
                                    [str(auditor), str(self.root / ("spec/native/linux/rejections/" + fixture + ".ll")), "linux-" + architecture], require=False)
                if result["exit_code"] != 1 or reason not in result["stdout"] + result["stderr"] or result["output_truncated"]:
                    raise ProofError("Negative auditor fixture did not reject for its intended reason")
                result["expected_rejection"] = True
                result["status"] = "passed"
        # Actual opposite-architecture Linux keys must not enter either profile.
        for architecture, other in (("x86_64", "aarch64"), ("aarch64", "x86_64")):
            key = ("svc #0", "={x0},{x8},{x0},{x1},{x2},{x3},{x4},{x5},~{memory},~{cc}") if other == "aarch64" else ("syscall", "={rax},{rax},{rdi},{rsi},{rdx},{r10},{r8},{r9},~{rcx},~{r11},~{memory},~{flags}")
            path = self.build / ("opposite-" + architecture + ".ll")
            path.write_text('define i32 @main() {\n  %r = call i64 asm sideeffect "' + key[0] + '", "' + key[1] + '"()\n  ret i32 0\n}\n')
            result = self.stage("reject-opposite-" + architecture, [str(auditor), str(path), "linux-" + architecture], require=False)
            if result["exit_code"] != 1 or "indirect or unrecognized" not in result["stderr"] + result["stdout"]:
                raise ProofError("Auditor admitted opposite-platform assembly")
            result.update(status="passed", expected_rejection=True)

    def require_refusals(self):
        # Use a tiny external source, and require a specific refusal diagnostic;
        # compiler/linker/stdlib crashes cannot count as a successful negative.
        prelude = self.build / "refusal-prelude.cr"
        prelude.write_text("# Isolate the entry guard from unsupported target stdlibs.\n")
        linux_message = "Linux kernel calls require non-Android LP64 GNU/musl Linux x86-64 or AArch64."
        darwin_message = "Darwin kernel calls require ARM64 or x86-64."
        cases = [
            ("linux-on-darwin", "aarch64-apple-darwin", "native-kernel/linux/raw", linux_message),
            ("linux-on-windows", "x86_64-pc-windows-msvc", "native-kernel/linux", linux_message),
            ("linux-on-i386", "i386-unknown-linux-gnu", "native-kernel/linux/raw", linux_message),
            ("linux-on-android", "aarch64-unknown-linux-android", "native-kernel/linux/raw", linux_message),
            ("linux-on-x32", "x86_64-unknown-linux-gnux32", "native-kernel/linux/raw", linux_message),
            ("linux-on-arm-ilp32", "aarch64-unknown-linux-gnu_ilp32", "native-kernel/linux/raw", linux_message),
            ("darwin-on-linux", "x86_64-unknown-linux-gnu", "native-kernel/darwin/raw", darwin_message),
            ("root-still-darwin", "x86_64-unknown-linux-gnu", "native-kernel", darwin_message),
        ]
        for name, target, entry, message in cases:
            source = self.build / (name + ".cr")
            source.write_text('require ' + json.dumps(crystal_relative_path(self.root / "src" / entry, source.parent)) + '\n')
            result = self.stage("refuse-" + name, [self.compiler, "build", "--no-codegen", "--prelude", crystal_relative_path(prelude, source.parent), "--target", target, str(source)], require=False)
            if result["exit_code"] != 1 or result["output_truncated"] or message not in result["stderr"] + result["stdout"]:
                raise ProofError("Unsupported direct require did not refuse explicitly: " + name)
            result.update(status="passed", expected_rejection=True)

    def llvm_codegen_command(self, ir, obj, triple, optimization):
        if self.version != "1.10.0":
            return None
        if optimization not in ("development", "release"):
            raise ProofError("Unknown LLVM optimization profile")
        if not self.llvm_llc:
            if not self.compiler_llvm_version:
                raise ProofError("The exact Crystal compiler's LLVM version was not identified")
            major = self.compiler_llvm_version.split(".", 1)[0]
            tool_name = "llc-" + major
            candidate = shutil.which(tool_name)
            if not candidate or not Path(candidate).is_file():
                raise ProofError("Crystal 1.10.0 codegen requires " + tool_name + " matching its LLVM IR producer")
            path = str(Path(candidate).resolve())
            result = self.stage("identity-" + tool_name, [path, "--version"], timeout=20)
            match = re.search(r"LLVM version ([0-9]+(?:\.[0-9]+)*)", result["stdout"])
            if not match or match[1].split(".", 1)[0] != major:
                raise ProofError("The floor LLVM codegen tool must match compiler LLVM major " + major)
            self.llvm_llc, self.llvm_llc_version = path, match[1]
            tool_key = "llc_" + major
            self.receipt.setdefault("tools", {})[tool_key] = {"path": path, "sha256": common.sha256_file(path)}
            self.receipt["floor_codegen_tool"] = {
                "name": tool_name, "path": path, "sha256": common.sha256_file(path), "version": match[1],
                "compiler_llvm_version": self.compiler_llvm_version,
                "operation": "Lower the exact audited compiler LLVM IR with the matching LLVM major to ELF object sections",
                "options": ["-opaque-pointers", "-function-sections", "-data-sections"],
                "optimization_mapping": {"development": "-O=0 (Crystal CodeGenOptLevel::None)",
                                          "release": "-O=3 (Crystal CodeGenOptLevel::Aggressive)"}}
            self.write()
        return [self.llvm_llc, "-opaque-pointers", "-filetype=obj", "-function-sections", "-data-sections",
                "-O=0" if optimization == "development" else "-O=3", "-mtriple=" + triple,
                str(ir), "-o", str(obj)]

    def build_probe(self, fixture, optimization, auditor):
        name = fixture + "-" + optimization
        artifact = self.build / name
        record = self.receipt["artifacts"][name] = {"status": "building", "execution": "unrun"}
        source = self.root / ("spec/native/linux/" + ("raw_probe" if fixture == "raw" else "behavior") + ".cr")
        flags = [self.compiler, "build", "--cross-compile", "--single-module", "--no-debug", "--error-on-warnings"]
        flags += self.unmanaged_flags(source) + ["--emit", "llvm-ir,asm"]
        if self.cross:
            flags += ["--target", self.config["profiles"][self.architecture]["target"]]
        if optimization == "release":
            flags += ["--release"]
        elif self.version != "1.10.0":
            flags += ["-O0"]
        self.stage("compile-" + name, flags + [str(source), "-o", str(artifact)])
        ir, emitted_obj = Path(str(artifact) + ".ll"), Path(str(artifact) + ".o")
        assembly = Path(str(artifact) + ".s")
        record.update(llvm_sha256=common.sha256_file(ir), compiler_object_sha256=common.sha256_file(emitted_obj),
                      emitted_assembly_sha256=common.sha256_file(assembly), optimization=optimization)
        self.write()
        # Retain even rejected IR, not just successful builds.
        with gzip.open(self.export / (name + ".ll.gz"), "wb") as stream:
            stream.write(ir.read_bytes())
        triple = re.search(r'^target triple = "([^"]+)"', ir.read_text(), re.M)
        if not triple or not triple[1].startswith(self.architecture + "-") or "linux" not in triple[1] or "android" in triple[1]:
            raise ProofError("Emitted LLVM target differs from the selected Linux architecture")
        self.stage("audit-" + name, [str(auditor), str(ir), "linux-" + self.architecture])
        if common.sha256_file(ir) != record["llvm_sha256"]:
            raise ProofError("Compiler LLVM IR changed during its source-bound audit")
        elf_identity(emitted_obj, self.architecture, executable=False)
        sectioned = Path(str(artifact) + ".sections.s")
        text, functions = function_sections(assembly.read_text(), self.architecture)
        obj = Path(str(artifact) + ".sections.o")
        if self.version == "1.10.0":
            # GNU as and LLVM MC both reject escaped quoted local symbols in
            # Crystal 1.10's printer output. Lower the audited, unmodified IR
            # directly with the compiler-matching LLVM 15 object writer instead.
            section_record = {"emitted_assembly_sha256": common.sha256_file(assembly), "functions": functions,
                              "llvm_ir_sha256": common.sha256_file(ir), "optimization": optimization,
                              "operation": "Lower the exact audited LLVM IR with matching LLVM 15 llc -opaque-pointers -function-sections -data-sections; retain emitted assembly as evidence without rewriting it or passing it to an assembler"}
            record["function_sections"] = section_record
            self.write()
            command = self.llvm_codegen_command(ir, obj, triple[1], optimization)
            if common.sha256_file(ir) != record["llvm_sha256"]:
                raise ProofError("Compiler LLVM IR changed after audit and before object lowering")
            self.stage("lower-" + name, command)
            if common.sha256_file(ir) != record["llvm_sha256"]:
                raise ProofError("Compiler LLVM IR changed during direct object lowering")
            object_sections = elf_object_sections(obj, self.architecture, len(functions), llvm_function_sections=True)
            section_record["lowering_command"] = command
            section_record["codegen_object_sha256"] = common.sha256_file(obj)
            with gzip.open(self.export / (name + ".s.gz"), "wb") as stream:
                stream.write(assembly.read_bytes())
        else:
            sectioned.write_text(text)
            section_record = {"emitted_assembly_sha256": common.sha256_file(assembly),
                              "sectioned_assembly_sha256": common.sha256_file(sectioned), "functions": functions,
                              "operation": "Insert only per-function ELF section/alignment directives; no original lines removed or changed"}
            record["function_sections"] = section_record
            self.write()
            for suffix, path in ((".s.gz", assembly), (".sections.s.gz", sectioned)):
                with gzip.open(self.export / (name + suffix), "wb") as stream:
                    stream.write(path.read_bytes())
            self.stage("assemble-" + name, self.cc + ["-c", "-x", "assembler", str(sectioned), "-o", str(obj)])
            object_sections = elf_object_sections(obj, self.architecture, len(functions))
        common.write_json(self.export / (name + ".object-sections.json"), object_sections)
        record["object_sections"] = object_sections
        self.write()
        self.stage("object-" + name, ["readelf", "-h", "-W", str(obj)])
        self.link(name, obj, artifact)
        identity = self.inspect(name, artifact)
        emitted_hash, object_sections = record["compiler_object_sha256"], record["object_sections"]
        record = self.artifact(name, artifact, ir=ir, obj=obj)
        record.update(identity=identity, target=triple[1], optimization=optimization, status="audited-and-linked",
                      compiler_object_sha256=emitted_hash, function_sections=section_record, object_sections=object_sections)
        return artifact, record

    def runtime(self, artifact, name, optimization, mapping):
        expected = "NK linux raw passed\n" if name == "raw" else "NK_OK linux " + name + "\n"
        # This artifact's build/audit/link stages are complete. Own descendants
        # only during its execution; release the scope before running tools again.
        set_subreaper(True)
        self.receipt["host"]["orphan_ownership"] = "native artifact execution only"
        try:
            result = self.stage("execute-" + name + "-" + optimization,
                                [str(artifact), name, "ELF-argument", str(mapping)], timeout=45 if name == "leaks" else 12, require=False)
        finally:
            try:
                adopted = cleanup_adopted_children()
                self.receipt.setdefault("final_adopted_children", []).extend(adopted)
            finally:
                set_subreaper(False)
            self.write()
        result["adopted_children"] = adopted
        complete = result["exit_code"] == 0 and result["stdout"] == expected and result["stderr"] == "" and not result["output_truncated"] and not adopted
        if not complete:
            result["status"] = "failed" if result["status"] == "passed" else result["status"]
        self.receipt["cases"].append({"name": name, "optimization": optimization, "status": result["status"],
                                      "completion_observed": complete, "adopted_children": adopted})
        self.write()
        if not complete:
            raise ProofError("Native case failed, lacked exact completion, or leaked a child: " + name)

    def run(self):
        try:
            if self.args.record_failure:
                self.receipt["status"] = "blocked"
                raise ProofError(self.args.record_failure)
            self.receipt["host"]["admission"] = "unqualified"
            try:
                validate_native_host(self.host_arch if self.cross else self.architecture)
            except (ProofError, OSError):
                self.receipt["status"] = "blocked"
                raise
            self.receipt["host"]["admission"] = "passed"
            if self.cross and self.architecture == self.host_arch:
                raise ProofError("Cross-only mode must select a different architecture")
            self.receipt["host"]["execution"] = "native Linux caller; no translation admitted"
            self.oracles()
            self.identify_compiler()
            self.stage("python-tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
            self.stage("format", [self.compiler, "tool", "format", "--check", "src", "spec", "scripts"])
            if not self.cross:
                result = self.stage("specs", [self.compiler, "spec", "--error-on-warnings", "--no-color"])
                examples = re.search(r"(\d+) examples?,", result["stdout"])
                if not examples or int(examples[1]) < 20:
                    raise ProofError("Specs did not execute the Linux/portable roster")
                self.receipt["spec_examples"] = int(examples[1])
                selected = self.stage("linux-specs", [self.compiler, "spec", "spec/linux_raw_spec.cr", "spec/linux_abi_spec.cr", "--error-on-warnings", "--no-color"])
                count = re.search(r"(\d+) examples?,", selected["stdout"])
                if not count or int(count[1]) < 11:
                    raise ProofError("Linux-specific specs were skipped or did not execute their roster")
                self.receipt["linux_spec_examples"] = int(count[1])
            auditor = self.build / "audit"
            self.stage("build-auditor", [self.compiler, "build", "--single-module", "--error-on-warnings", "scripts/ci/audit.cr", "-o", str(auditor)])
            self.rejection_tests(auditor)
            self.require_refusals()
            mapping = self.build / "mapping-input"
            mapping.write_bytes(b"\0" * 65536 + b"sixth-slot-nonzero-offset\0" + b"\0" * 4096)
            self.receipt["mapping_input_sha256"] = common.sha256_file(mapping)
            # Do not build on a failed raw layer. Both raw optimization gates
            # complete before instantiating/building the typed behavior layer.
            for fixture in ("raw", "behavior"):
                for optimization in ("development", "release"):
                    artifact, record = self.build_probe(fixture, optimization, auditor)
                    if not self.cross:
                        for case in (("raw",) if fixture == "raw" else CASES):
                            self.runtime(artifact, case, optimization, mapping)
                        record["execution"] = "native-passed"
                        record["status"] = "passed"
            if self.cross:
                self.receipt["status"] = "cross-compile-only"
            else:
                expected = {(case, mode) for case in ("raw",) + CASES for mode in ("development", "release")}
                observed = {(case["name"], case["optimization"]) for case in self.receipt["cases"] if case["completion_observed"]}
                if observed != expected:
                    raise ProofError("Native runtime roster is incomplete")
                self.receipt["status"] = "mechanisms-passed"
            # Intentionally NOT "qualified": no genuine EINTR/consumer/PID reuse
            # claim follows from this roster. Missing compilers never get here.
        except (ProofError, OSError, ValueError) as error:
            self.receipt["reason"] = str(error)
            if self.receipt["status"] != "blocked":
                self.receipt["status"] = "failed"
        finally:
            self.receipt["source_after"] = source_identity(self.root)
            self.receipt["source_unchanged"] = self.receipt["source_before"] == self.receipt["source_after"]
            if not self.receipt["source_unchanged"]:
                self.receipt.update(status="failed", reason="Source/build inputs changed during proof")
            for name, digest in self.receipt.get("layout_oracle", {}).get("header_sha256", {}).items():
                if not Path(name).is_file() or common.sha256_file(name) != digest:
                    self.receipt.update(status="failed", reason="C oracle input changed during proof: " + name)
            tools = self.receipt.get("tools", {})
            self.receipt["tool_inputs_unchanged"] = all(Path(item["path"]).is_file() and common.sha256_file(item["path"]) == item["sha256"] for item in tools.values()) if tools else None
            if tools and not self.receipt["tool_inputs_unchanged"]:
                self.receipt.update(status="failed", reason="Selected build/inspection tool changed during proof")
            compiler = self.receipt.get("compiler", {})
            selected = dict(compiler.get("stdlib_sha256", {}))
            if compiler.get("sha256"):
                selected[compiler["path"]] = compiler["sha256"]
            prelude = self.receipt.get("unmanaged_entry", {}).get("prelude")
            if prelude:
                selected[prelude["generated_path"]] = prelude["generated_sha256"]
                adapter = prelude.get("adapter", {})
                if adapter.get("generated_path") and adapter.get("generated_sha256"):
                    selected[adapter["generated_path"]] = adapter["generated_sha256"]
                if adapter.get("source_path") and adapter.get("source_sha256"):
                    selected[adapter["source_path"]] = adapter["source_sha256"]
                try:
                    check_floor_prelude(prelude)
                except (ProofError, OSError) as error:
                    self.receipt.update(status="failed", reason="Floor prelude input changed: " + str(error))
            self.receipt["compiler_inputs_unchanged"] = all(Path(path).is_file() and common.sha256_file(path) == digest for path, digest in selected.items()) if selected else None
            if selected and not self.receipt["compiler_inputs_unchanged"]:
                self.receipt.update(status="failed", reason="Compiler/stdlib inputs changed during proof")
            self.receipt["unproduced_artifacts"] = [name + "-" + mode for name in ("raw", "behavior") for mode in ("development", "release") if not self.receipt["artifacts"].get(name + "-" + mode, {}).get("sha256")]
            self.receipt["completed_at"] = datetime.now(timezone.utc).isoformat()
            self.write()
        return 0 if self.receipt["status"] in ("mechanisms-passed", "cross-compile-only") else 1


def manifest_sha256(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def receipt_review(path):
    """A bounded, SHA-bound view of the actual receipt, not a second proof.

    Keep the complete artifact/case/stage rosters and input-integrity results
    inspectable through the Checks API when artifact downloads are unavailable.
    Large source/function manifests stay in receipt.json; bind their exact
    content by count and canonical-JSON hash, never by truncation or a fake pass.
    """
    serialized = Path(path).read_bytes()
    receipt = json.loads(serialized)
    fields = ("status", "qualification", "mode", "architecture", "expected_compiler", "git_head", "git_branch",
              "host", "source_unchanged", "tool_inputs_unchanged", "compiler_inputs_unchanged", "tools", "tools_scope",
              "floor_codegen_tool", "spec_examples", "linux_spec_examples", "cases", "unproduced_artifacts", "final_adopted_children",
              "unmanaged_entry", "limits", "reason", "workflow")
    review = {key: receipt.get(key) for key in fields}
    review.update(review_schema=1, receipt_sha256=hashlib.sha256(serialized).hexdigest(),
                  scope="Bounded review of receipt.json; full source/function manifests remain in the SHA-bound receipt")
    review["source_manifests"] = {key: {"count": len(receipt.get(key, {})), "sha256": manifest_sha256(receipt.get(key, {}))}
                                  for key in ("source_before", "source_after")}
    compiler = dict(receipt.get("compiler", {}))
    stdlib = compiler.pop("stdlib_sha256", {})
    compiler["stdlib_sources"] = {"count": len(stdlib), "sha256": manifest_sha256(stdlib)}
    # The parsed environment/path selection and identity remain in the full receipt.
    compiler.pop("environment", None)
    review["compiler"] = compiler
    review["stages"] = []
    diagnostic_stage_emitted = False
    for stage in receipt["stages"]:
        record = {key: stage.get(key) for key in ("name", "status", "exit_code", "output_truncated", "expected_rejection")}
        if stage["name"].startswith(("compile-", "lower-", "identity-llc-")) or stage["name"] == "format":
            record["command"] = stage["command"]
        if stage["name"].startswith("imports-"):
            record.update(stdout=stage["stdout"], stderr=stage["stderr"])
        if stage["status"] != "passed":
            record.update(stdout_tail=stage["stdout"][-1024:], stderr_tail=stage["stderr"][-1024:])
            if not diagnostic_stage_emitted:
                if "command" in stage:
                    record["command"] = stage["command"]
                record.update(stdout_head=stage["stdout"][:1024], stderr_head=stage["stderr"][:1024],
                              stdout_error_lines=[line[:256] for line in stage["stdout"].splitlines()
                                                  if re.search(r"(?:error|fatal|undefined reference|cannot|failed)", line, re.I)][-4:],
                              stderr_error_lines=[line[:256] for line in stage["stderr"].splitlines()
                                                  if re.search(r"(?:error|fatal|undefined reference|cannot|failed)", line, re.I)][-4:])
                if len(json.dumps(stage["stderr"], ensure_ascii=True)) <= 8192:
                    record["stderr_full"] = stage["stderr"]
                diagnostic_stage_emitted = True
        review["stages"].append(record)
    review["artifacts"] = {}
    for name, artifact in receipt["artifacts"].items():
        record = dict(artifact)
        if "function_sections" in record:
            section = dict(record["function_sections"])
            functions = section.pop("functions")
            section.update(function_count=len(functions), functions_sha256=manifest_sha256(functions))
            record["function_sections"] = section
        review["artifacts"][name] = record
    return review


def write_receipt_review(path, *, ci=False):
    review = receipt_review(path)
    payload = json.dumps(review, sort_keys=True, separators=(",", ":")).encode()
    if len(payload) > common.OUTPUT_LIMIT - 512:
        raise ProofError("Receipt review exceeds the unchanged 64-KiB output bound")
    encoded = base64.b64encode(gzip.compress(payload, mtime=0)).decode("ascii")
    parts = [encoded[start:start + 3600] for start in range(0, len(encoded), 3600)]
    # The hosted runner truncates issue messages at 4096 characters and records
    # at most ten notices per step. Compress, number and hash the complete view;
    # never publish a truncated JSON fragment as if it were a complete receipt.
    digest = hashlib.sha256(payload).hexdigest()
    notices = ["::notice title=Native Linux receipt review " + str(index) + "/" + str(len(parts)) +
               "::NK_LINUX_RECEIPT_REVIEW " + digest + " " + str(index) + "/" + str(len(parts)) + " " + part
               for index, part in enumerate(parts, 1)]
    if len(parts) > 10 or len(("\n".join(notices) + "\n").encode()) > common.OUTPUT_LIMIT - 512:
        raise ProofError("Receipt review exceeds the bounded Checks-notice budget")
    common.write_json(Path(path).with_name("receipt-review.json"), review)
    if ci:
        print("\n".join(notices))
    return review


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default=os.environ.get("CRYSTAL", "crystal"))
    parser.add_argument("--expected-compiler", choices=("1.10.0", "1.22.2"))
    parser.add_argument("--architecture", choices=tuple(ARCHITECTURES))
    parser.add_argument("--cross-target", choices=tuple(ARCHITECTURES))
    parser.add_argument("--cc", default=os.environ.get("CC", "cc"))
    parser.add_argument("--output", required=True)
    parser.add_argument("--record-failure")
    args = parser.parse_args(argv)
    try:
        runner = Runner(args)
        code = runner.run()
        write_receipt_review(runner.export / "receipt.json", ci=os.environ.get("GITHUB_ACTIONS") == "true")
        print(runner.receipt["status"] + ": " + str(runner.export / "receipt.json"))
        return code
    except (ProofError, OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
