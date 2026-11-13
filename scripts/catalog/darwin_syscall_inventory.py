#!/usr/bin/env python3
"""Build the reviewed Darwin syscall inventory from XNU source evidence.

The history archive and exact latest XNU source are deliberately external to
this repository. The generated files correct the latest Mach, ARM and
diagnostic rows, retain primary entries, add bounded secondary catalogs, and
record Native-Kernel coverage state. This script does not infer API
suitability.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[2]
LATEST_MEMBER_SUFFIX = "/output/latest_snapshot_entries.csv"
RAW_LITERAL_CALL = re.compile(r"\bRaw\.call\(\s*(-?\d+)(?![\w:])")
RAW_SYMBOL_CALL = re.compile(
    r"\bRaw\.call\(\s*(?:Native::Kernel::Darwin::)?"
    r"(Syscall::Number|Mach::Trap)::([A-Z][A-Z0-9_]*)"
)
CONSTANT = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*=\s*(-?\d+)_i32\b", re.MULTILINE)
FAMILY_ORDER = {"bsd": 0, "mach": 1, "machdep": 2, "diagnostic": 3}
EXACT_SNAPSHOT = "xnu-12377.121.6"
EXACT_COMMIT = "ac9718fb1af618d5ce8678d0dc6e8a58f252216f"
HISTORY_LATEST_INPUT_COMMIT = "f6217f891ac0bb64f3d375211650a4c1ff8ca1ea"
SOURCE_REPOSITORY = "https://github.com/apple-oss-distributions/xnu"
SOURCE_MANIFEST_NAME = "darwin-xnu-source-manifest-%s.json" % EXACT_SNAPSHOT
SOURCE_MANIFEST = ROOT / "docs/data" / SOURCE_MANIFEST_NAME
SOURCE_MANIFEST_ROLES = frozenset({
    "build_manifest",
    "generation_script",
    "mig_include",
    "mig_subsystem",
    "primary_implementation",
    "primary_table",
    "project_manifest",
    "selector_header",
    "test_source",
})
OWNED_OUTPUT_PATTERNS = (
    "darwin-active-syscalls-xnu-*.csv",
    "darwin-syscall-gaps-xnu-*.csv",
    "darwin-secondary-catalog-candidates-xnu-*.csv",
    "darwin-proc-info-operations-xnu-*.csv",
    "darwin-mach-mig-subsystems-xnu-*.csv",
    "darwin-syscall-inventory.json",
)
EXACT_SOURCE_SHA256 = {
    "bsd/kern/syscalls.master": "7e866891439ad5b3464777d2cacc3b82fc2e7f439fb5a8686c3e6f160d5aeab5",
    "osfmk/kern/syscall_sw.c": "9c84c9ea109067bbdac35c4ddcb3de872c228a7cfff51b72a6d5a109fc431820",
    "osfmk/arm64/proc_reg.h": "fcbead4162ad09d0f51be9ce88e5f2d6d89e89e58934975ee1aa23e506485055",
    "osfmk/arm64/machine_routines.c": "a1eb04ef6e17b597fbfedc41ff84558dcda18768fdb4f59f0dda242f9267800e",
    "osfmk/i386/machdep_call.c": "ca7fe53e0e7c6bc472340f787a0fba99a7733f24c4b130e57f42ed9b815540a6",
    "osfmk/i386/Diagnostics.h": "9d8ad11cabacf5af680150a35daf515446cf23350b85c36cc96c0c29698c0218",
    "osfmk/i386/Diagnostics.c": "e5c7bcad6f97f72d36d0b72bf17c0a9850aa972c37f31daaffc12506864c68d1",
    "bsd/sys/proc_info.h": "a4eb26cdfd3721b111f9979455d80a854625b0ef96ba4de1a4e7705f462e0f84",
    "bsd/sys/proc_info_private.h": "4f8a8290fb644349521befe852fbaebf1a2d3a9355b0937f45ce1d89a3906a73",
}
DIRECT_SOURCE_ROLES = {
    "bsd/kern/syscalls.master": "primary_table",
    "osfmk/kern/syscall_sw.c": "primary_table",
    "osfmk/arm64/proc_reg.h": "selector_header",
    "osfmk/arm64/machine_routines.c": "primary_implementation",
    "osfmk/i386/machdep_call.c": "primary_table",
    "osfmk/i386/Diagnostics.h": "selector_header",
    "osfmk/i386/Diagnostics.c": "primary_implementation",
    "bsd/sys/proc_info.h": "selector_header",
    "bsd/sys/proc_info_private.h": "selector_header",
    "osfmk/mach/Makefile": "build_manifest",
    "makedefs/MakeInc.def": "build_manifest",
    "makedefs/MakeInc.cmd": "build_manifest",
    "libsyscall/xcodescripts/mach_install_mig.sh": "generation_script",
    "libsyscall/Libsyscall.xcodeproj/project.pbxproj": "project_manifest",
}
SOURCE_COLUMNS = (
    "snapshot_id",
    "family",
    "architecture",
    "number",
    "selector",
    "logical_name",
    "handler",
    "status",
    "variant",
    "return_type",
    "arguments",
    "prototype",
    "condition",
    "audit",
    "file_flags",
    "no_syscall_stub",
    "arg_count",
    "arg_words",
    "munger",
    "extra",
    "comment",
    "x86_64_encoded",
    "arm64_encoded",
    "source_path",
    "source_line",
    "source_hash",
    "raw",
    "parse_warning",
)
IMPLEMENTATION_COLUMNS = (
    "implementation_source_path",
    "implementation_source_line",
    "implementation_source_hash",
)
OUTPUT_COLUMNS = SOURCE_COLUMNS + IMPLEMENTATION_COLUMNS + (
    "raw_selector",
    "native_kernel_state",
    "library_catalog_state",
    "implementation_decision",
    "native_kernel_files",
)
SECONDARY_COLUMNS = (
    "snapshot_id",
    "family",
    "architecture",
    "number",
    "logical_name",
    "selector_parameters",
    "arguments",
    "prototype",
    "native_kernel_state",
    "source_path",
    "source_line",
    "parse_warning",
    "candidate_basis",
)
PROC_INFO_COLUMNS = (
    "snapshot_id",
    "category",
    "symbol",
    "numeric_value",
    "value_expression",
    "size_symbol",
    "size_expression",
    "visibility",
    "native_kernel_state",
    "source_path",
    "source_line",
    "source_hash",
)
MIG_SUBSYSTEM_COLUMNS = (
    "snapshot_id",
    "source_scope",
    "kernel_build_roles",
    "libsyscall_export_roles",
    "subsystem_names",
    "base_message_id",
    "routine_declarations",
    "simpleroutine_declarations",
    "skip_declarations",
    "source_path",
    "source_line",
    "source_hash",
    "declaration",
    "parse_warning",
)
SELECTOR_PARAMETER_NAMES = frozenset({
    "action", "advice", "amode", "behav", "behavior", "call", "callnum",
    "class", "clock_id", "cmd", "com", "command", "control", "domain",
    "dpflags", "event", "events", "filter", "flag", "flags", "flavor",
    "graft_type", "guardflags", "how", "idtype", "infostyle", "inherit",
    "kind", "level", "mask", "mib", "mode", "op", "operation", "opt",
    "option", "options", "packed_selectors", "policy", "policy_subtype",
    "prot", "protocol", "reason_code", "reason_flags", "reason_namespace",
    "req", "request", "resource", "scope", "sfi_class", "sfi_flags", "sig",
    "signum", "style", "subsystem", "type", "whence", "which", "who",
})
SELECTOR_PARAMETER_SUFFIXES = (
    "_class", "_cmd", "_flag", "_flags", "_flavor", "_op", "_option",
    "_options", "_policy", "_type",
)
SPECIAL_NAME_PARAMETERS = frozenset({
    "crossarch_trap", "fpathconf", "getsockopt", "pathconf", "setsockopt",
    "sysctl",
})
PROC_LIST_TYPES = frozenset({
    "PROC_ALL_PIDS", "PROC_PGRP_ONLY", "PROC_TTY_ONLY", "PROC_UID_ONLY",
    "PROC_RUID_ONLY", "PROC_PPID_ONLY", "PROC_KDBG_ONLY",
})
IMPLEMENTED_PROC_INFO = frozenset({
    "PROC_INFO_CALL_LISTPIDS",
    "PROC_INFO_CALL_PIDINFO",
    "PROC_INFO_CALL_PIDRUSAGE",
    "PROC_INFO_CALL_SIGNAL_AUDITTOKEN",
    "PROC_ALL_PIDS",
    "PROC_PGRP_ONLY",
    "PROC_PPID_ONLY",
    "PROC_PIDTASKALLINFO",
    "PROC_PIDTBSDINFO",
    "PROC_PIDTASKINFO",
    "PROC_PIDT_SHORTBSDINFO",
    "PROC_PIDT_BSDINFOWITHUNIQID",
    "PIF_COMPARE_IDVERSION",
    "PIF_COMPARE_UNIQUEID",
})
PROC_INFO_WITNESSES = {
    "PROC_INFO_CALL_LISTPIDS": (
        "src/native-kernel/darwin/process.cr", "Raw.call(336, 1_u64",
    ),
    "PROC_INFO_CALL_PIDINFO": (
        "src/native-kernel/darwin/process.cr", "Raw.call(336, 2_u64",
    ),
    "PROC_INFO_CALL_PIDRUSAGE": (
        "src/native-kernel/darwin/process/inspection.cr", "Raw.call(336, 9_u64",
    ),
    "PROC_INFO_CALL_SIGNAL_AUDITTOKEN": (
        "src/native-kernel/darwin/process.cr", "Raw.call(336, 17_u64",
    ),
    "PROC_ALL_PIDS": (
        "src/native-kernel/darwin/process.cr", "Raw.call(336, 1_u64, 1_u64",
    ),
    "PROC_PGRP_ONLY": (
        "spec/native/behavior/inspection.cr", "Info::PGRP_ONLY",
    ),
    "PROC_PPID_ONLY": (
        "spec/native/behavior/inspection.cr", "Info::PPID_ONLY",
    ),
    "PROC_PIDTASKALLINFO": (
        "src/native-kernel/darwin/process/inspection.cr", "Info::PIDTASKALLINFO",
    ),
    "PROC_PIDTBSDINFO": (
        "src/native-kernel/darwin/process/inspection.cr", "Info::PIDTBSDINFO",
    ),
    "PROC_PIDTASKINFO": (
        "src/native-kernel/darwin/process/inspection.cr", "Info::PIDTASKINFO",
    ),
    "PROC_PIDT_SHORTBSDINFO": (
        "spec/typed_spec.cr", "Info::PIDT_SHORTBSDINFO",
    ),
    "PROC_PIDT_BSDINFOWITHUNIQID": (
        "spec/native/behavior/inspection.cr", "Info::PIDT_BSDINFOWITHUNIQID",
    ),
    "PIF_COMPARE_IDVERSION": (
        "spec/native/behavior/inspection.cr", "Info::PIF_COMPARE_IDVERSION",
    ),
    "PIF_COMPARE_UNIQUEID": (
        "spec/native/behavior/inspection.cr", "Info::PIF_COMPARE_UNIQUEID",
    ),
}


class CatalogError(RuntimeError):
    pass


class ConditionTracker:
    def __init__(self):
        self.frames = []

    def handle(self, line):
        match = re.match(r"^\s*#\s*(if|ifdef|ifndef|elif|else|endif)\b\s*(.*?)\s*$", line)
        if not match:
            return False
        kind, expression = match.groups()
        expression = re.sub(r"/\*.*?\*/", "", expression).strip()
        if kind in ("if", "ifdef", "ifndef", "elif") and not expression:
            raise CatalogError("Empty preprocessor #%s condition" % kind)
        if kind == "ifdef":
            kind, expression = "if", "defined(%s)" % expression
        elif kind == "ifndef":
            kind, expression = "if", "!defined(%s)" % expression
        if kind == "if":
            self.frames.append({
                "branches": [expression],
                "current": expression,
                "else_seen": False,
            })
        elif kind in ("elif", "else", "endif") and not self.frames:
            raise CatalogError("Unmatched preprocessor #%s" % kind)
        elif kind == "elif":
            frame = self.frames[-1]
            if frame["else_seen"]:
                raise CatalogError("Preprocessor #elif follows #else")
            prior = " || ".join("(%s)" % branch for branch in frame["branches"])
            frame["current"] = "(!(%s)) && (%s)" % (prior, expression)
            frame["branches"].append(expression)
        elif kind == "else":
            frame = self.frames[-1]
            if frame["else_seen"]:
                raise CatalogError("Duplicate preprocessor #else")
            frame["else_seen"] = True
            branches = frame["branches"]
            if len(branches) == 1 and "||" not in branches[0]:
                frame["current"] = "!(%s)" % branches[0]
            else:
                joined = " || ".join("(%s)" % branch for branch in branches)
                frame["current"] = "!(%s)" % joined
        elif kind == "endif":
            self.frames.pop()
        return True

    def finish(self):
        if self.frames:
            raise CatalogError("Unterminated preprocessor condition")

    @property
    def condition(self):
        parts = [frame["current"] for frame in self.frames if frame["current"] != "1"]
        if not parts:
            return "1"
        if len(parts) == 1:
            return parts[0]
        return " && ".join("(%s)" % part for part in parts)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def git_checkout_state(root):
    if not (root / ".git").exists():
        return None
    try:
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise CatalogError("Cannot inspect exact XNU Git checkout: %s" % error)
    return {"head": head, "head_matches": head == EXACT_COMMIT,
            "worktree_clean": not bool(status.strip())}


def manifest_role(relative, source):
    if relative in DIRECT_SOURCE_ROLES:
        return DIRECT_SOURCE_ROLES[relative]
    if not relative.endswith(".defs"):
        raise CatalogError("No manifest role is defined for %s" % relative)
    if relative.startswith("tests/"):
        return "test_source"
    if re.search(r"^[ \t]*subsystem\b", source, re.MULTILINE):
        return "mig_subsystem"
    return "mig_include"


def source_manifest_document(root):
    root = Path(root)
    state = git_checkout_state(root)
    if state is None:
        raise CatalogError("Source-manifest refresh requires an XNU Git checkout")
    if state["head"] != EXACT_COMMIT:
        raise CatalogError("Source-manifest checkout HEAD differs: %s" % state["head"])
    if not state["worktree_clean"]:
        raise CatalogError("Source-manifest checkout has uncommitted changes")

    paths = set(DIRECT_SOURCE_ROLES)
    paths.update(path.relative_to(root).as_posix()
                 for path in root.rglob("*.defs") if path.is_file())
    entries = []
    for relative in sorted(paths):
        source = root / relative
        if not source.is_file():
            raise CatalogError("Exact XNU source is missing %s" % source)
        actual = sha256(source)
        pinned = EXACT_SOURCE_SHA256.get(relative)
        if pinned is not None and actual != pinned:
            raise CatalogError("Pinned XNU source hash differs for %s: %s" %
                               (relative, actual))
        text = source.read_text(encoding="utf-8", errors="strict")
        entries.append({
            "path": relative,
            "sha256": actual,
            "role": manifest_role(relative, text),
        })
    return {
        "schema_version": 1,
        "snapshot_id": EXACT_SNAPSHOT,
        "source_repository": SOURCE_REPOSITORY,
        "commit": EXACT_COMMIT,
        "files": entries,
    }


def source_manifest_bytes(document):
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def json_object_without_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CatalogError("Exact XNU source manifest has duplicate key: %s" % key)
        result[key] = value
    return result


def load_source_manifest(path):
    manifest_path = Path(path)
    if not manifest_path.is_file():
        raise CatalogError("Exact XNU source manifest is missing: %s" % manifest_path)
    raw = manifest_path.read_bytes()
    try:
        document = json.loads(
            raw.decode("utf-8"), object_pairs_hook=json_object_without_duplicates
        )
    except (UnicodeDecodeError, ValueError) as error:
        raise CatalogError("Exact XNU source manifest is invalid: %s" % error)
    if not isinstance(document, dict):
        raise CatalogError("Exact XNU source manifest must be a JSON object")
    expected_keys = {"schema_version", "snapshot_id", "source_repository",
                     "commit", "files"}
    if set(document) != expected_keys:
        raise CatalogError("Exact XNU source manifest has unexpected top-level keys")
    if document.get("schema_version") != 1:
        raise CatalogError("Unsupported exact XNU source-manifest schema")
    if document.get("snapshot_id") != EXACT_SNAPSHOT:
        raise CatalogError("Exact XNU source-manifest snapshot differs")
    if document.get("source_repository") != SOURCE_REPOSITORY:
        raise CatalogError("Exact XNU source-manifest repository differs")
    if document.get("commit") != EXACT_COMMIT:
        raise CatalogError("Exact XNU source-manifest commit differs")
    entries = document.get("files")
    if not isinstance(entries, list) or not entries:
        raise CatalogError("Exact XNU source manifest has no files")
    return document, sha256_bytes(raw)


def exact_source_root(path, manifest_path=SOURCE_MANIFEST):
    root = Path(path)
    document, manifest_hash = load_source_manifest(manifest_path)
    entries = document["files"]
    observed = {}
    roles = {}
    prior = None
    root_resolved = root.resolve()
    for entry in entries:
        if not isinstance(entry, dict):
            raise CatalogError("Exact XNU source-manifest file entry is not an object")
        if set(entry) != {"path", "sha256", "role"}:
            raise CatalogError("Exact XNU source-manifest file entry has unexpected keys")
        relative = entry.get("path")
        expected = entry.get("sha256")
        role = entry.get("role")
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
            raise CatalogError("Exact XNU source manifest has an invalid path")
        if Path(relative).as_posix() != relative or ".." in Path(relative).parts:
            raise CatalogError("Exact XNU source manifest has an unsafe path: %s" % relative)
        if prior is not None and relative <= prior:
            detail = "duplicate" if relative == prior else "unsorted"
            raise CatalogError("Exact XNU source manifest has %s path: %s" %
                               (detail, relative))
        prior = relative
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise CatalogError("Exact XNU source manifest has invalid hash for %s" % relative)
        if role not in SOURCE_MANIFEST_ROLES:
            raise CatalogError("Exact XNU source manifest has unknown role for %s" % relative)
        source = root / relative
        try:
            source.resolve().relative_to(root_resolved)
        except ValueError:
            raise CatalogError("Exact XNU source escapes source root: %s" % relative)
        if not source.is_file():
            raise CatalogError("Exact XNU source is missing %s" % source)
        actual = sha256(source)
        if actual != expected:
            raise CatalogError("Exact XNU source hash differs for %s: %s" %
                               (relative, actual))
        observed[relative] = actual
        roles[relative] = role

    expected_paths = set(DIRECT_SOURCE_ROLES)
    observed_defs = {
        source.relative_to(root).as_posix()
        for source in root.rglob("*.defs") if source.is_file()
    }
    expected_paths.update(observed_defs)
    manifest_paths = set(observed)
    missing = sorted(expected_paths - manifest_paths)
    unexpected = sorted(manifest_paths - expected_paths)
    if missing or unexpected:
        parts = []
        if missing:
            parts.append("missing entries: %s" % ", ".join(missing))
        if unexpected:
            parts.append("unexpected entries: %s" % ", ".join(unexpected))
        raise CatalogError("Exact XNU source-manifest roster differs (%s)" %
                           "; ".join(parts))
    for relative, role in DIRECT_SOURCE_ROLES.items():
        if roles.get(relative) != role:
            raise CatalogError("Exact XNU source-manifest role differs for %s" % relative)
    for relative in observed_defs:
        source = (root / relative).read_text(encoding="utf-8", errors="strict")
        expected_role = manifest_role(relative, source)
        if roles.get(relative) != expected_role:
            raise CatalogError("Exact XNU source-manifest role differs for %s" % relative)

    state = git_checkout_state(root)
    if state is not None and not state["head_matches"]:
        raise CatalogError("Exact XNU Git checkout HEAD differs: %s" % state["head"])
    evidence = {
        "path": SOURCE_MANIFEST_NAME,
        "schema_version": document["schema_version"],
        "sha256": manifest_hash,
        "file_count": len(entries),
        "defs_file_count": len(observed_defs),
    }
    return root, observed, evidence


def extract_group(text, opener, closer, start=0):
    position = text.find(opener, start)
    if position < 0:
        raise CatalogError("Missing %s in XNU table row" % opener)
    depth = 0
    for index in range(position, len(text)):
        character = text[index]
        if character == opener:
            depth += 1
        elif character == closer:
            depth -= 1
            if depth == 0:
                return text[position + 1:index], index + 1
    raise CatalogError("Unclosed %s in XNU table row" % opener)


def split_top_level(text):
    parts = []
    start = 0
    depths = {"(": 0, "[": 0, "{": 0}
    pairs = {")": "(", "]": "[", "}": "{"}
    quoted = None
    escaped = False
    for index, character in enumerate(text):
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quoted:
                quoted = None
            continue
        if character in ('"', "'"):
            quoted = character
        elif character in depths:
            depths[character] += 1
        elif character in pairs:
            depths[pairs[character]] = max(0, depths[pairs[character]] - 1)
        elif character == "," and not any(depths.values()):
            parts.append(text[start:index].strip())
            start = index + 1
    parts.append(text[start:].strip())
    return parts


def source_row(**values):
    row = {name: "" for name in SOURCE_COLUMNS + IMPLEMENTATION_COLUMNS}
    row.update({name: str(value) for name, value in values.items() if value is not None})
    return row


def parse_exact_mach(source, source_hash):
    tracker = ConditionTracker()
    rows = []
    pattern = re.compile(r"/\*\s*(\d+)\s*\*/\s*MACH_TRAP\s*\(")
    offset = 0
    for line_number, line in enumerate(source.splitlines(keepends=True), 1):
        if tracker.handle(line):
            offset += len(line)
            continue
        match = pattern.search(line)
        if not match:
            offset += len(line)
            continue
        absolute = offset + match.start()
        body, end = extract_group(source, "(", ")", absolute)
        fields = split_top_level(body)
        if len(fields) < 2:
            raise CatalogError("Incomplete MACH_TRAP row at line %d" % line_number)
        number = int(match.group(1))
        handler = fields[0]
        count = int(fields[1], 0) if re.fullmatch(r"0[xX][0-9a-fA-F]+|\d+", fields[1]) else None
        words = None
        munger = ""
        extra = ""
        if len(fields) >= 4:
            words = int(fields[2], 0) if re.fullmatch(r"0[xX][0-9a-fA-F]+|\d+", fields[2]) else None
            munger = fields[3]
            extra = ", ".join(fields[4:])
        elif len(fields) == 3:
            munger = fields[2]
        rows.append(source_row(
            snapshot_id=EXACT_SNAPSHOT,
            family="mach",
            architecture="all",
            number=number,
            logical_name=handler[4:] if handler.startswith("sys_") else handler,
            handler=handler,
            status="inactive" if handler in ("kern_invalid", "nosys", "enosys") else "active",
            variant="mach_trap_table",
            condition=tracker.condition,
            no_syscall_stub=0,
            arg_count=count,
            arg_words=words,
            munger=munger,
            extra=extra,
            x86_64_encoded=0x01000000 | number,
            arm64_encoded=-number,
            source_path="osfmk/kern/syscall_sw.c",
            source_line=line_number,
            source_hash=source_hash,
            raw=source[absolute:end].replace("\n", " ").strip(),
        ))
        offset += len(line)
    tracker.finish()
    return rows


def named_function_body(source, name):
    match = re.search(
        r"\b%s\s*\([^;{}]*\)\s*\{" % re.escape(name), source,
        re.MULTILINE,
    )
    if not match:
        raise CatalogError("Exact XNU source lacks %s function body" % name)
    brace = source.find("{", match.start(), match.end())
    body, end = extract_group(source, "{", "}", brace)
    return body, brace + 1, end


def parse_exact_arm_platform(header, implementation, header_hash, implementation_hash):
    trap_match = re.search(
        r"^\s*#\s*define\s+PLATFORM_SYSCALL_TRAP_NO\s+(0[xX][0-9A-Fa-f]+|\d+)",
        header,
        re.MULTILINE,
    )
    if not trap_match:
        raise CatalogError("Exact XNU source lacks PLATFORM_SYSCALL_TRAP_NO")
    trap_number = int(trap_match.group(1), 0)
    body, body_start, _ = named_function_body(implementation, "platform_syscall")
    matches = list(re.finditer(r"\bcase\s+(\d+)\s*:\s*(?:/\*\s*(.*?)\s*\*/)?", body))
    rows = []
    for index, match in enumerate(matches):
        selector = int(match.group(1))
        end = (matches[index + 1].start() if index + 1 < len(matches) else
               body.find("default:", match.end()))
        if end < 0:
            end = len(body)
        segment = body[match.start():end]
        inline_comment = (match.group(2) or "").strip()
        call = re.search(r"\b(thread_(?:set|get)_cthread_self)\s*\(", segment)
        handler = call.group(1) if call else "platform_selector_%d" % selector
        removed = "removed" in (inline_comment + " " + segment).lower()
        rows.append(source_row(
            snapshot_id=EXACT_SNAPSHOT,
            family="machdep",
            architecture="arm64",
            number=trap_number,
            selector=selector,
            logical_name=handler,
            handler=handler,
            status="inactive" if removed or call is None else "active",
            variant="platform_syscall selector",
            condition="1",
            no_syscall_stub=0,
            extra="trap constant: osfmk/arm64/proc_reg.h; header_sha256=%s" % header_hash,
            comment=inline_comment,
            arm64_encoded=trap_number,
            source_path="osfmk/arm64/machine_routines.c",
            source_line=implementation.count("\n", 0, body_start + match.start()) + 1,
            source_hash=implementation_hash,
            raw=match.group(0).rstrip(),
        ))
    return rows


def parse_exact_diagnostics(header, implementation, header_hash,
                            implementation_hash):
    syscall = re.search(
        r"^[ \t]*#[ \t]*define[ \t]+diagSCnum[ \t]+"
        r"(0[xX][0-9A-Fa-f]+|\d+)",
        header,
        re.MULTILINE,
    )
    if not syscall:
        raise CatalogError("Exact XNU source lacks diagSCnum")
    encoded = 0x04000000 | int(syscall.group(1), 0)

    declarations = []
    declaration_pattern = re.compile(
        r"^[ \t]*#[ \t]*define[ \t]+(dg[A-Za-z0-9_]+)[ \t]+(\d+)"
        r"(?:[ \t]|$)",
        re.MULTILINE,
    )
    for match in declaration_pattern.finditer(header):
        declarations.append({
            "name": match.group(1),
            "selector": int(match.group(2)),
            "line": header.count("\n", 0, match.start()) + 1,
            "raw": header[match.start():header.find("\n", match.start())].strip(),
        })
    if not declarations:
        raise CatalogError("Exact XNU diagnostic header has no selectors")

    body, body_start, _ = named_function_body(implementation, "diagCall64")
    cases = {}
    tracker = ConditionTracker()
    offset = 0
    for line in body.splitlines(keepends=True):
        if tracker.handle(line):
            offset += len(line)
            continue
        match = re.search(r"\bcase[ \t]+(dg[A-Za-z0-9_]+)[ \t]*:", line)
        if match:
            name = match.group(1)
            if name in cases:
                raise CatalogError("Duplicate exact XNU diagnostic case: %s" % name)
            cases[name] = {
                "condition": tracker.condition,
                "line": implementation.count("\n", 0, body_start + offset + match.start()) + 1,
            }
        offset += len(line)
    tracker.finish()

    declaration_names = {entry["name"] for entry in declarations}
    unknown_cases = sorted(set(cases) - declaration_names)
    if unknown_cases:
        raise CatalogError("Exact XNU diagnostic cases lack declarations: %s" %
                           ", ".join(unknown_cases))
    rows = []
    for declaration in declarations:
        case = cases.get(declaration["name"])
        rows.append(source_row(
            snapshot_id=EXACT_SNAPSHOT,
            family="diagnostic",
            architecture="x86_64",
            number=encoded,
            selector=declaration["selector"],
            logical_name=declaration["name"],
            handler=declaration["name"],
            status="active" if case else "declared_only",
            variant="diagCall64 selector",
            condition=case["condition"] if case else "1",
            no_syscall_stub=0,
            x86_64_encoded=encoded,
            source_path="osfmk/i386/Diagnostics.h",
            source_line=declaration["line"],
            source_hash=header_hash,
            raw=declaration["raw"],
            implementation_source_path=("osfmk/i386/Diagnostics.c" if case else ""),
            implementation_source_line=(case["line"] if case else ""),
            implementation_source_hash=(implementation_hash if case else ""),
        ))
    return rows


def correct_latest_sources(rows, xnu_root, manifest_path=SOURCE_MANIFEST):
    snapshots = {row["snapshot_id"] for row in rows}
    if snapshots != {EXACT_SNAPSHOT}:
        return rows, None
    root, hashes, manifest_evidence = exact_source_root(xnu_root, manifest_path)
    original_hashes = {
        row["source_path"]: row["source_hash"]
        for row in rows
        if row["source_path"] in ("osfmk/kern/syscall_sw.c", "osfmk/arm64/machine_routines.c")
    }
    corrected = [
        row for row in rows
        if row["family"] not in ("mach", "diagnostic") and not
        (row["family"] == "machdep" and row["architecture"] == "arm64")
    ]
    corrected.extend(parse_exact_mach(
        (root / "osfmk/kern/syscall_sw.c").read_text(encoding="utf-8"),
        hashes["osfmk/kern/syscall_sw.c"],
    ))
    corrected.extend(parse_exact_arm_platform(
        (root / "osfmk/arm64/proc_reg.h").read_text(encoding="utf-8"),
        (root / "osfmk/arm64/machine_routines.c").read_text(encoding="utf-8"),
        hashes["osfmk/arm64/proc_reg.h"],
        hashes["osfmk/arm64/machine_routines.c"],
    ))
    corrected.extend(parse_exact_diagnostics(
        (root / "osfmk/i386/Diagnostics.h").read_text(encoding="utf-8"),
        (root / "osfmk/i386/Diagnostics.c").read_text(encoding="utf-8"),
        hashes["osfmk/i386/Diagnostics.h"],
        hashes["osfmk/i386/Diagnostics.c"],
    ))
    return corrected, {
        "snapshot_id": EXACT_SNAPSHOT,
        "commit": EXACT_COMMIT,
        "history_export_input_commit": HISTORY_LATEST_INPUT_COMMIT,
        "history_export_label_mismatch": True,
        "source_manifest": manifest_evidence,
        "verified_direct_file_sha256": {
            relative: hashes[relative] for relative in sorted(DIRECT_SOURCE_ROLES)
        },
        "replaced_families": ["mach", "machdep/arm64", "diagnostic"],
        "history_export_source_hashes_replaced": original_hashes,
    }


def macro_definitions(source):
    """Return object-like C macros without evaluating their expressions."""
    lines = source.splitlines()
    macros = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        match = re.match(r"^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(.*)$",
                         line)
        if not match:
            index += 1
            continue
        name, expression = match.groups()
        source_line = index + 1
        parts = [expression.rstrip()]
        while parts[-1].endswith("\\") and index + 1 < len(lines):
            parts[-1] = parts[-1][:-1].rstrip()
            index += 1
            parts.append(lines[index].strip())
        expression = " ".join(part for part in parts if part).strip()
        expression = re.sub(r"/\*.*?\*/", "", expression).strip()
        macros[name] = {"expression": expression, "line": source_line}
        index += 1
    return macros


def proc_info_category(name):
    if name.startswith("PROC_INFO_CALL_"):
        return "call"
    if name in PROC_LIST_TYPES:
        return "list_type"
    if name.startswith("PIF_COMPARE_"):
        return "identity_comparison_flag"
    if name.startswith("PROC_PIDFILEPORT"):
        return "pidfileportinfo_flavor"
    if name.startswith("PROC_PIDFD"):
        return "pidfdinfo_flavor"
    if name.startswith("PROC_PIDORIGINATOR_"):
        return "pidoriginatorinfo_flavor"
    if name.startswith("PROC_PIDDYNKQUEUE_"):
        return "piddynkqueueinfo_flavor"
    if name.startswith("PROC_PID"):
        return "pidinfo_flavor"
    if name.startswith("PROC_SELFSET_"):
        return "setcontrol_action"
    if name.startswith("PROC_DIRTYCONTROL_"):
        return "dirtycontrol_action"
    if name.startswith("PROC_UDATA_INFO_"):
        return "udata_action"
    if name.startswith("LISTCOALITIONS_"):
        return "listcoalitions_flavor"
    return None


def proc_info_rows(root, hashes):
    rows = []
    for relative, visibility in (
        ("bsd/sys/proc_info.h", "public"),
        ("bsd/sys/proc_info_private.h", "private"),
    ):
        macros = macro_definitions((root / relative).read_text(encoding="utf-8"))
        for name, definition in macros.items():
            category = proc_info_category(name)
            expression = definition["expression"]
            if category is None or name.endswith(("_SIZE", "_MAX")):
                continue
            if not re.fullmatch(r"0[xX][0-9A-Fa-f]+|\d+", expression):
                continue
            size_symbol = ""
            size_candidates = [name + "_SIZE", name + "SIZE"]
            if name.endswith("S"):
                size_candidates.append(name[:-1] + "_SIZE")
            for candidate in size_candidates:
                if candidate in macros:
                    size_symbol = candidate
                    break
            rows.append({
                "snapshot_id": EXACT_SNAPSHOT,
                "category": category,
                "symbol": name,
                "numeric_value": str(int(expression, 0)),
                "value_expression": expression,
                "size_symbol": size_symbol,
                "size_expression": macros.get(size_symbol, {}).get("expression", ""),
                "visibility": visibility,
                "native_kernel_state": ("implemented" if name in IMPLEMENTED_PROC_INFO
                                        else "unreviewed"),
                "source_path": relative,
                "source_line": str(definition["line"]),
                "source_hash": hashes[relative],
            })
    return sorted(rows, key=lambda row: (row["category"], int(row["numeric_value"]),
                                         row["symbol"]))


def mig_scope(relative):
    if relative.startswith("tests/"):
        return "test_only"
    if relative.startswith("osfmk/mach/"):
        return "mach_core"
    if relative.startswith("libsyscall/"):
        return "libsyscall_service"
    return "kernel_service"


def continued_make_values(source, variable):
    lines = source.splitlines()
    values = []
    index = 0
    pattern = re.compile(r"^[ \t]*%s[ \t]*=[ \t]*(.*)$" % re.escape(variable))
    while index < len(lines):
        match = pattern.match(lines[index])
        if not match:
            index += 1
            continue
        part = match.group(1)
        while True:
            continued = part.rstrip().endswith("\\")
            values.extend(re.findall(r"[A-Za-z0-9_./-]+\.defs\b", part))
            if not continued or index + 1 >= len(lines):
                break
            index += 1
            part = lines[index]
        index += 1
    return values


def quoted_shell_values(source, variable):
    match = re.search(
        r"^[ \t]*%s=\"(.*?)\"" % re.escape(variable),
        source,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        return []
    return re.findall(r"[A-Za-z0-9_./-]+\.defs\b", match.group(1))


def mig_build_roles(root):
    kernel = {}
    makefile = (root / "osfmk/mach/Makefile").read_text(encoding="utf-8")
    for variable, role in (
        ("MIG_TYPES", "kernel_type"),
        ("MIG_DEFS", "kernel_public"),
        ("MIG_PRIVATE_DEFS", "kernel_private"),
        ("MACH_PRIVATE_DEFS", "kernel_mach_private"),
    ):
        for name in continued_make_values(makefile, variable):
            relative = "osfmk/mach/%s" % name
            kernel.setdefault(relative, set()).add(role)

    exports = {}
    script = (root / "libsyscall/xcodescripts/mach_install_mig.sh").read_text(
        encoding="utf-8"
    )
    for name in quoted_shell_values(script, "MIGS"):
        exports.setdefault("osfmk/mach/%s" % name, set()).add("public_header")
    for name in quoted_shell_values(script, "MIGS_INTERNAL"):
        exports.setdefault("osfmk/mach/%s" % name, set()).add("internal_header")
    if re.search(r'MIGS="\$MIGS[ \t]+mach_vm\.defs"', script):
        roles = exports.setdefault("osfmk/mach/mach_vm.defs", set())
        roles.add("public_header_macos")
        roles.add("private_header_embedded")
    return kernel, exports


def mig_subsystem_rows(root):
    kernel_roles, export_roles = mig_build_roles(root)
    rows = []
    for path in sorted(root.rglob("*.defs")):
        source = path.read_text(encoding="utf-8")
        match = re.search(r"^[ \t]*subsystem\b", source, re.MULTILINE)
        if not match:
            continue
        end = source.find(";", match.end())
        if end < 0:
            raise CatalogError("MIG subsystem declaration has no terminator: %s" % path)
        declaration = source[match.start():end + 1]
        flattened = " ".join(declaration.split())
        base_match = re.search(r"(\d+)\s*;\s*$", flattened)
        warning = ""
        base = ""
        if base_match:
            base = base_match.group(1)
        else:
            warning = "subsystem base is not a decimal literal"
        clean_lines = []
        for line in re.sub(r"/\*.*?\*/", "", declaration,
                           flags=re.DOTALL).splitlines():
            if line.lstrip().startswith("#"):
                continue
            clean_lines.append(line)
        clean = " ".join(clean_lines)
        if base:
            clean = re.sub(r"\b%s\s*;\s*$" % re.escape(base), "", clean)
        tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", clean)
        ignored = {"subsystem", "KernelServer", "KernelUser", "KERNEL_USER"}
        names = []
        for token in tokens:
            if token not in ignored and token not in names:
                names.append(token)
        relative = path.relative_to(root).as_posix()
        rows.append({
            "snapshot_id": EXACT_SNAPSHOT,
            "source_scope": mig_scope(relative),
            "kernel_build_roles": ";".join(sorted(kernel_roles.get(relative, ()))),
            "libsyscall_export_roles": ";".join(
                sorted(export_roles.get(relative, ()))
            ),
            "subsystem_names": ";".join(names),
            "base_message_id": base,
            "routine_declarations": str(len(re.findall(
                r"^[ \t]*routine\b", source, re.MULTILINE | re.IGNORECASE))),
            "simpleroutine_declarations": str(len(re.findall(
                r"^[ \t]*simpleroutine\b", source,
                re.MULTILINE | re.IGNORECASE))),
            "skip_declarations": str(len(re.findall(
                r"^[ \t]*skip\s*;", source, re.MULTILINE))),
            "source_path": relative,
            "source_line": str(source.count("\n", 0, match.start()) + 1),
            "source_hash": sha256(path),
            "declaration": flattened,
            "parse_warning": warning,
        })
    return rows


def read_latest_rows(archive_path):
    try:
        with zipfile.ZipFile(archive_path) as archive:
            members = [name for name in archive.namelist()
                       if name.endswith(LATEST_MEMBER_SUFFIX)]
            if len(members) != 1:
                raise CatalogError("Expected one %s member; found %d" %
                                   (LATEST_MEMBER_SUFFIX, len(members)))
            member = members[0]
            with archive.open(member) as raw:
                text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
                reader = csv.DictReader(text)
                fieldnames = reader.fieldnames or ()
                if len(fieldnames) != len(set(fieldnames)):
                    raise CatalogError("Latest-snapshot CSV has duplicate columns")
                missing = set(SOURCE_COLUMNS) - set(fieldnames)
                if missing:
                    raise CatalogError("Latest-snapshot CSV lacks columns: %s" %
                                       ", ".join(sorted(missing)))
                rows = list(reader)
                if any(None in row for row in rows):
                    raise CatalogError("Latest-snapshot CSV has excess columns")
    except (UnicodeError, csv.Error) as error:
        raise CatalogError("Cannot read latest-snapshot CSV: %s" % error)
    if not rows:
        raise CatalogError("Latest-snapshot CSV is empty")
    snapshots = {row["snapshot_id"] for row in rows}
    if len(snapshots) != 1:
        raise CatalogError("Latest-snapshot CSV contains multiple snapshots: %s" %
                           ", ".join(sorted(snapshots)))
    snapshot = next(iter(snapshots))
    if not re.fullmatch(r"xnu-\d+(?:\.\d+){1,3}", snapshot):
        raise CatalogError("Latest-snapshot CSV has invalid snapshot ID: %s" % snapshot)
    return member, rows


def constant_values(path):
    if not path.is_file():
        return {}
    values = {}
    for name, number in CONSTANT.findall(path.read_text(encoding="utf-8")):
        values.setdefault(name, set()).add(int(number))
    return values


def resolve_symbol(name, family, definitions):
    values = definitions[family].get(name, set())
    if len(values) != 1:
        raise CatalogError("Cannot resolve %s constant %s uniquely: %s" %
                           (family, name, sorted(values)))
    selector = next(iter(values))
    if family == "bsd" and selector < 0:
        raise CatalogError("BSD constant %s has negative value %d" % (name, selector))
    if family == "mach" and selector >= 0:
        raise CatalogError("Mach trap constant %s has nonnegative value %d" % (name, selector))
    return selector


def discover_raw_coverage(root=ROOT):
    """Return primary entries reached by numeric or planned symbolic calls."""
    source_root = Path(root) / "src/native-kernel/darwin"
    if not source_root.is_dir():
        raise CatalogError("Darwin source directory is missing: %s" % source_root)
    definitions = {
        "bsd": constant_values(source_root.parent / "darwin/raw.cr"),
        "mach": constant_values(source_root.parent / "darwin/mach.cr"),
    }
    coverage = {}

    def record(key, relative, form):
        entry = coverage.setdefault(key, {"files": set(), "forms": set()})
        entry["files"].add(relative)
        entry["forms"].add(form)

    for path in sorted(source_root.rglob("*.cr")):
        relative = path.relative_to(root).as_posix()
        for line in path.read_text(encoding="utf-8").splitlines():
            code = line.split("#", 1)[0]
            for match in RAW_LITERAL_CALL.finditer(code):
                selector = int(match.group(1))
                family = "mach" if selector < 0 else "bsd"
                key = (family, abs(selector))
                record(key, relative, "literal")
            for match in RAW_SYMBOL_CALL.finditer(code):
                namespace, name = match.groups()
                family = "bsd" if namespace == "Syscall::Number" else "mach"
                selector = resolve_symbol(name, family, definitions)
                key = (family, abs(selector))
                record(key, relative, "symbolic")
    if not coverage:
        raise CatalogError("No numeric Darwin Raw.call sites were found")
    return coverage


def row_key(row):
    return row["family"], int(row["number"])


def sort_key(row):
    return (FAMILY_ORDER.get(row["family"], 99), int(row["number"]),
            row["architecture"], row["logical_name"])


def raw_selector(row):
    number = int(row["number"])
    if row["family"] == "bsd":
        return str(number)
    if row["family"] == "mach":
        return str(-number)
    return ""


def decorate_rows(source_rows, coverage):
    active = sorted((row for row in source_rows if row["status"] == "active"), key=sort_key)
    active_primary = {}
    for row in active:
        if row["family"] in ("bsd", "mach"):
            active_primary.setdefault(row_key(row), []).append(row)
    missing = sorted(key for key in coverage if key not in active_primary)
    ambiguous = sorted(key for key in coverage if len(active_primary.get(key, ())) != 1)
    if missing or ambiguous:
        parts = []
        if missing:
            parts.append("missing: %s" % missing)
        if ambiguous:
            parts.append("ambiguous: %s" % ambiguous)
        raise CatalogError("Current raw entries do not map one-to-one to active XNU rows (%s)" %
                           "; ".join(parts))

    decorated = []
    for source in active:
        key = row_key(source)
        coverage_entry = coverage.get(key)
        files = coverage_entry["files"] if coverage_entry else set()
        if coverage_entry:
            state = "typed_wrapper"
            forms = coverage_entry["forms"]
            catalog_state = ("named" if forms == {"symbolic"} else
                             "mixed" if "symbolic" in forms else "literal_only")
            decision = "implemented"
        elif source["family"] in ("bsd", "mach"):
            state = "raw_entry_only"
            catalog_state = "missing"
            decision = "unreviewed"
        else:
            state = "unsupported_entry_family"
            catalog_state = "missing"
            decision = "unsupported_family"
        row = {
            name: source.get(name, "")
            for name in SOURCE_COLUMNS + IMPLEMENTATION_COLUMNS
        }
        row.update({
            "raw_selector": raw_selector(source),
            "native_kernel_state": state,
            "library_catalog_state": catalog_state,
            "implementation_decision": decision,
            "native_kernel_files": ";".join(sorted(files)),
        })
        decorated.append(row)
    return decorated


def csv_bytes(rows):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=OUTPUT_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def argument_names(arguments):
    names = []
    for argument in arguments.split(","):
        identifiers = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", argument)
        if identifiers:
            names.append(identifiers[-1])
    return names


def selector_parameters(row):
    if row["family"] != "bsd":
        return []
    selected = []
    for name in argument_names(row["arguments"]):
        lower = name.lower()
        if lower == "name":
            candidate = row["logical_name"] in SPECIAL_NAME_PARAMETERS
        else:
            candidate = (lower in SELECTOR_PARAMETER_NAMES or
                         lower.endswith(SELECTOR_PARAMETER_SUFFIXES))
        if candidate and name not in selected:
            selected.append(name)
    return selected


def secondary_candidates(rows):
    candidates = []
    for row in rows:
        parameters = selector_parameters(row)
        if not parameters:
            continue
        candidate = {name: row.get(name, "") for name in SECONDARY_COLUMNS}
        candidate["selector_parameters"] = ";".join(parameters)
        candidate["candidate_basis"] = "selector-like scalar parameter name; heuristic audit queue"
        candidates.append(candidate)
    return candidates


def secondary_csv_bytes(rows):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=SECONDARY_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def catalog_csv_bytes(rows, columns):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def metadata(archive_path, member, history_rows, source_rows, rows, secondary,
             proc_info, mig_subsystems, correction):
    family_counts = {}
    for family in FAMILY_ORDER:
        family_rows = [row for row in rows if row["family"] == family]
        if not family_rows:
            continue
        family_counts[family] = {
            "active_logical_rows": len(family_rows),
            "active_numeric_slots": len({int(row["number"]) for row in family_rows}),
            "typed_wrapper_rows": sum(row["native_kernel_state"] == "typed_wrapper"
                                      for row in family_rows),
            "gap_rows": sum(row["native_kernel_state"] != "typed_wrapper"
                            for row in family_rows),
        }
    gaps = [row for row in rows if row["native_kernel_state"] != "typed_wrapper"]
    snapshot = rows[0]["snapshot_id"]
    return {
        "schema_version": 5,
        "snapshot_id": snapshot,
        "source_archive": Path(archive_path).name,
        "source_archive_sha256": sha256(archive_path),
        "source_member": member,
        "history_snapshot_rows_all_statuses": len(history_rows),
        "corrected_snapshot_rows_all_statuses": len(source_rows),
        "active_logical_rows": len(rows),
        "active_numeric_slots": len({(row["family"], int(row["number"])) for row in rows}),
        "active_parse_warning_rows": sum(bool(row["parse_warning"]) for row in rows),
        "typed_wrapper_rows": sum(row["native_kernel_state"] == "typed_wrapper" for row in rows),
        "gap_rows": len(gaps),
        "secondary_catalog_candidate_rows": len(secondary),
        "proc_info_catalog_rows": len(proc_info),
        "proc_info_implemented_rows": sum(
            row["native_kernel_state"] == "implemented" for row in proc_info
        ),
        "mig_subsystem_rows": len(mig_subsystems),
        "mig_production_subsystem_rows": sum(
            row["source_scope"] != "test_only" for row in mig_subsystems
        ),
        "mig_kernel_build_subsystem_rows": sum(
            bool(row["kernel_build_roles"]) for row in mig_subsystems
        ),
        "mig_libsyscall_export_subsystem_rows": sum(
            bool(row["libsyscall_export_roles"]) for row in mig_subsystems
        ),
        "family_counts": family_counts,
        "coverage_states": {
            state: sum(row["native_kernel_state"] == state for row in rows)
            for state in ("typed_wrapper", "raw_entry_only", "unsupported_entry_family")
        },
        "exact_source_correction": correction,
        "generation": {
            "script": "scripts/catalog/darwin_syscall_inventory.py",
            "source_admission_rule": (
                "tracked path/role/SHA-256 manifest plus exact .defs roster, "
                "validated before parsing"
            ),
            "active_rule": "status == active",
            "coverage_rule": (
                "numeric Raw.call literals or Syscall::Number/Mach::Trap calls "
                "in src/native-kernel/darwin"
            ),
            "policy_classification": "none; unimplemented primary entries remain unreviewed",
            "secondary_candidate_rule": (
                "BSD prototype parameters with selector-like names; heuristic "
                "and non-exhaustive"
            ),
            "proc_info_implemented_rule": (
                "issued through a shipped typed mechanism with a named source or "
                "positive-spec witness"
            ),
            "mig_role_rule": (
                "kernel build variables and libsyscall header-export lists; not "
                "configuration-resolved routine availability"
            ),
        },
    }


def build_outputs(archive_path, root=ROOT, latest_xnu_root=None,
                  source_manifest=SOURCE_MANIFEST):
    member, history_rows = read_latest_rows(archive_path)
    snapshot = history_rows[0]["snapshot_id"]
    if snapshot == EXACT_SNAPSHOT and latest_xnu_root is None:
        raise CatalogError(
            "%s requires --latest-xnu-root for exact Mach, ARM and diagnostic source" %
            EXACT_SNAPSHOT
        )
    source_rows, correction = correct_latest_sources(
        history_rows, latest_xnu_root, source_manifest
    )
    rows = decorate_rows(source_rows, discover_raw_coverage(root))
    gaps = [row for row in rows if row["native_kernel_state"] != "typed_wrapper"]
    secondary = secondary_candidates(rows)
    proc_info = []
    mig_subsystems = []
    if correction is not None:
        xnu_root = Path(latest_xnu_root)
        proc_info = proc_info_rows(
            xnu_root, correction["verified_direct_file_sha256"]
        )
        mig_subsystems = mig_subsystem_rows(xnu_root)
    meta = metadata(archive_path, member, history_rows, source_rows, rows,
                    secondary, proc_info, mig_subsystems, correction)
    outputs = {
        "darwin-active-syscalls-%s.csv" % snapshot: csv_bytes(rows),
        "darwin-syscall-gaps-%s.csv" % snapshot: csv_bytes(gaps),
        "darwin-secondary-catalog-candidates-%s.csv" % snapshot:
            secondary_csv_bytes(secondary),
        "darwin-syscall-inventory.json":
            (json.dumps(meta, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    }
    if correction is not None:
        outputs["darwin-proc-info-operations-%s.csv" % snapshot] = \
            catalog_csv_bytes(proc_info, PROC_INFO_COLUMNS)
        outputs["darwin-mach-mig-subsystems-%s.csv" % snapshot] = \
            catalog_csv_bytes(mig_subsystems, MIG_SUBSYSTEM_COLUMNS)
    return outputs


def find_stale_outputs(outputs, output_dir):
    output_dir = Path(output_dir)
    expected = set(outputs)
    owned = set()
    if output_dir.is_dir():
        for pattern in OWNED_OUTPUT_PATTERNS:
            owned.update(path.name for path in output_dir.glob(pattern) if path.is_file())
    return [output_dir / name for name in sorted(owned - expected)]


def update_outputs(outputs, output_dir, check=False):
    output_dir = Path(output_dir)
    changed = []
    for name, expected in outputs.items():
        path = output_dir / name
        actual = path.read_bytes() if path.is_file() else None
        if actual != expected:
            changed.append(path)
            if not check:
                output_dir.mkdir(parents=True, exist_ok=True)
                path.write_bytes(expected)
    stale = find_stale_outputs(outputs, output_dir)
    if check and (changed or stale):
        parts = []
        if changed:
            parts.append("differs: %s" % ", ".join(str(path) for path in changed))
        if stale:
            parts.append("has stale owned outputs: %s" %
                         ", ".join(str(path) for path in stale))
        raise CatalogError("Generated inventory %s" % "; ".join(parts))
    return changed, stale


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path,
                        help="darwin-xnu-syscall-history-first-pass ZIP")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/data")
    parser.add_argument("--root", type=Path, default=ROOT,
                        help="Native-Kernel checkout used for coverage discovery")
    parser.add_argument(
        "--latest-xnu-root",
        type=Path,
        help="exact xnu-12377.121.6 source checkout or extracted tree",
    )
    parser.add_argument(
        "--source-manifest",
        type=Path,
        default=SOURCE_MANIFEST,
        help="tracked exact-source manifest used for source admission",
    )
    parser.add_argument(
        "--write-source-manifest",
        action="store_true",
        help="explicitly refresh the manifest from a clean pinned Git checkout",
    )
    parser.add_argument("--check", action="store_true",
                        help="fail if tracked output differs; do not write")
    return parser.parse_args(argv)


def main(argv=None):
    arguments = parse_args(argv)
    try:
        if arguments.write_source_manifest:
            if arguments.check:
                raise CatalogError("--write-source-manifest cannot be combined with --check")
            if arguments.latest_xnu_root is None:
                raise CatalogError("--write-source-manifest requires --latest-xnu-root")
            document = source_manifest_document(arguments.latest_xnu_root)
            expected = source_manifest_bytes(document)
            path = arguments.source_manifest
            actual = path.read_bytes() if path.is_file() else None
            if actual != expected:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(expected)
                print("Updated %s" % path)
            else:
                print("Exact XNU source manifest already current")
            return 0
        if arguments.archive is None:
            raise CatalogError("normal generation requires --archive")
        outputs = build_outputs(arguments.archive, arguments.root,
                                arguments.latest_xnu_root,
                                arguments.source_manifest)
        changed, stale = update_outputs(outputs, arguments.output_dir,
                                        arguments.check)
    except (CatalogError, OSError, UnicodeError, zipfile.BadZipFile, csv.Error) as error:
        print("darwin syscall inventory: %s" % error, file=sys.stderr)
        return 1
    if arguments.check:
        print("Darwin syscall inventory matches %s" % arguments.archive)
    elif changed:
        print("Updated %s" % ", ".join(str(path) for path in changed))
    else:
        print("Darwin syscall inventory already current")
    if stale:
        print("Stale generator-owned outputs retained: %s" %
              ", ".join(str(path) for path in stale), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
