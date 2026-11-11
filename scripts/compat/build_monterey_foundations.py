#!/usr/bin/env python3
"""Build auditable x86-64 Darwin 21 spawn and task-token handoff bundles.

Run this only on a native Intel Darwin build host with the two reviewed Crystal
compilers. It emits separate, manifest-bound bundles; the Mini executes them
with monterey_foundations_runner.py and never invokes this builder or Crystal.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import monterey_runner as base
import monterey_foundations_runner as foundations_runner

COMPILERS = (("current", "1.22.2"), ("floor", "1.10.0"))
CAMPAIGNS = ("spawn", "task-token")
# The official macOS launcher is a shell script, not a Mach-O. Only this exact
# reviewed launcher has a known embedded compiler layout; a local wrapper must
# name its actual executable with the matching --*-binary option.
OFFICIAL_LAUNCHER_SHA256 = "541fa514cc2207fd3168d44e8a5aa13d65a1e3b2258b1636056631e45b61635d"
MACH_O_MAGICS = (b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe",
                 b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca", b"\xca\xfe\xba\xbf", b"\xbf\xba\xfe\xca")
KIND_SOURCES = {
    "spawn": ("spec/native/monterey_spawn.cr", "spec/native/exec.cr"),
    "task-token": ("spec/native/monterey_task_token.cr",),
}


class BuildError(RuntimeError):
    pass


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def run(command, *, cwd, environment, log):
    log.write("$ " + " ".join(command) + "\n")
    log.flush()
    result = subprocess.run(command, cwd=str(cwd), env=environment, stdin=subprocess.DEVNULL,
                            stdout=log, stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        raise BuildError("Command failed (%d): %s" % (result.returncode, " ".join(command)))


def command_text(command):
    try:
        result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise BuildError("Cannot run %s: %s" % (command[0], error))
    if result.returncode:
        raise BuildError("Command failed: %s\n%s" % (" ".join(command), result.stderr.strip()))
    return result.stdout


def require_build_host():
    if platform.system() != "Darwin" or platform.machine() != "x86_64":
        raise BuildError("Build requires a native Intel Darwin host; it does not cross-build from Linux or Rosetta")
    # Native Intel macOS commonly has no sysctl.proc_translated OID. A missing
    # optional query is not translation; a successful nonzero result is.
    try:
        result = subprocess.run(["/usr/sbin/sysctl", "-n", "sysctl.proc_translated"], stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise BuildError("Cannot query translation state: %s" % error)
    if result.returncode == 0 and result.stdout.strip() not in ("", "0"):
        raise BuildError("Build requires untranslated native Intel execution")


def is_mach_o(path):
    try:
        with Path(path).open("rb") as stream:
            return stream.read(4) in MACH_O_MAGICS
    except OSError as error:
        raise BuildError("Cannot inspect compiler path %s: %s" % (path, error))


def compiler_version_target(description):
    version = re.search(r"^Crystal (\d+\.\d+\.\d+)(?:\s|$)", description, re.MULTILINE)
    target = re.search(r"^Default target: (.+)$", description, re.MULTILINE)
    if not version or not target:
        raise BuildError("Compiler version output lacks version or default target")
    return version.group(1), target.group(1).strip()


def compiler_identity(path, expected):
    output = command_text([str(path), "--version"])
    version, target = compiler_version_target(output)
    if version != expected:
        raise BuildError("Expected Crystal %s at %s" % (expected, path))
    if not target.startswith("x86_64-apple-"):
        raise BuildError("Compiler does not report an x86-64 Apple default target: %s" % path)
    return output.strip()


def invocation_path(value):
    # Do not resolve symlinks here: the supplied launcher is the command whose
    # environment and wrapper behavior the build must retain and record.
    return Path(value).expanduser().absolute()


def resolve_compiler_binary(invocation, explicit=None):
    invocation = invocation_path(invocation)
    if explicit:
        binary, resolution = Path(explicit).expanduser().resolve(), "explicit-operator-path"
    elif is_mach_o(invocation):
        binary, resolution = invocation.resolve(), "direct-mach-o"
    elif digest(invocation) == OFFICIAL_LAUNCHER_SHA256 and invocation.name == "crystal" and invocation.parent.name == "bin":
        binary, resolution = (invocation.parent.parent / "embedded/bin/crystal").resolve(), "official-launcher-layout"
    else:
        raise BuildError("Cannot resolve actual compiler binary; supply --current-binary or --floor-binary for a trusted local wrapper")
    if not binary.is_file() or not os.access(str(binary), os.X_OK):
        raise BuildError("Compiler binary is missing or not executable: %s" % binary)
    if not is_mach_o(binary):
        raise BuildError("Actual compiler binary must be Mach-O, not a launcher: %s" % binary)
    return binary, resolution


def compiler_receipt(invocation, expected, explicit=None):
    invocation = invocation_path(invocation)
    invocation_description = compiler_identity(invocation, expected)
    invocation_version, invocation_target = compiler_version_target(invocation_description)
    binary, resolution = resolve_compiler_binary(invocation, explicit)
    binary_description = compiler_identity(binary, expected)
    binary_version, binary_target = compiler_version_target(binary_description)
    if (invocation_version, invocation_target) != (binary_version, binary_target):
        raise BuildError("Compiler invocation and actual binary identities differ: %s" % invocation)
    architectures = command_text(["/usr/bin/xcrun", "lipo", "-archs", str(binary)]).split()
    if "x86_64" not in architectures:
        raise BuildError("Crystal compiler binary lacks x86-64 code: %s" % binary)
    return {
        "identity_scope": "compiler-binary-and-invocation-only",
        "invocation": {"path": str(invocation), "sha256": digest(invocation),
                       "version": invocation_version, "default_target": invocation_target,
                       "description": invocation_description},
        "binary": {"path": str(binary), "sha256": digest(binary), "resolution": resolution,
                   "architectures": architectures, "version": binary_version,
                   "default_target": binary_target, "description": binary_description},
    }


def toolchain_receipt():
    return {
        "sdk_path": command_text(["/usr/bin/xcrun", "--show-sdk-path"]).strip(),
        "sdk_version": command_text(["/usr/bin/xcrun", "--show-sdk-version"]).strip(),
        "cc": command_text(["/usr/bin/xcrun", "--find", "clang"]).strip(),
        "cc_version": command_text(["/usr/bin/cc", "--version"]).strip(),
    }


def llvm_target(path):
    match = re.search(r'^target triple = "([^"]+)"', path.read_text(encoding="utf-8"), re.MULTILINE)
    if not match or not re.match(r"^x86_64-apple-(?:macosx|darwin)", match.group(1)):
        raise BuildError("LLVM artifact is not an x86-64 Darwin target: %s" % path)
    return match.group(1)


def source_inventory():
    wanted = sorted((ROOT / "src").rglob("*.cr"))
    wanted += [ROOT / relative for relative in (
        "spec/native/monterey_spawn.cr", "spec/native/monterey_task_token.cr", "spec/native/exec.cr",
        "scripts/verification.cr", "scripts/ci/audit.cr", "scripts/compat/darwin21_spawn_layout.c",
        "scripts/compat/monterey_runner.py", "scripts/compat/monterey_foundations_runner.py",
        "scripts/compat/build_monterey_foundations.py",
    )]
    return {str(path.relative_to(ROOT)): digest(path) for path in sorted(wanted)}


def copy_runner(bundle):
    for name in ("monterey_runner.py", "monterey_foundations_runner.py"):
        source = ROOT / "scripts/compat" / name
        destination = bundle / name
        shutil.copy2(source, destination)
        destination.chmod(0o700)


def write_bundle_readme(bundle, kind):
    text = (
        "Native-Kernel Darwin 21 %s bundle\n\n" % kind +
        "Run only on macOS 12.7.6 build 21H1320, Darwin 21.6.0, native Intel:\n"
        "  /usr/bin/python3 -I monterey_foundations_runner.py --output /external/new-%s-result\n\n" % kind +
        "This bundle is prebuilt. The runner verifies every payload hash before and after\n"
        "each bounded case, captures at most 65536 bytes per stream, and archives receipts.\n"
        "It does not qualify Process-Control or any other release/host.\n"
    )
    (bundle / "README.txt").write_text(text, encoding="utf-8")


def make_manifest(bundle, kind, builds):
    files = {str(path.relative_to(bundle)): digest(path) for path in sorted(bundle.rglob("*")) if path.is_file()}
    manifest = {
        "schema": 1,
        "kind": kind,
        "expected_host": base.EXPECTED_HOST,
        "files": files,
        "builds": builds,
        "cases": foundations_runner.CAMPAIGNS[kind]["cases"],
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return digest(bundle / "manifest.json")


def build_one(compiler, version, optimization, source, artifact, work, log):
    environment = os.environ.copy()
    environment.update({"MACOSX_DEPLOYMENT_TARGET": "12.0", "CRYSTAL_CACHE_DIR": str(work / "cache")})
    command = [compiler, "build", "--cross-compile", "--single-module", "--no-debug", "--error-on-warnings",
               "-Dwithout_main", "--emit", "llvm-ir"]
    if optimization == "release":
        command.append("--release")
    elif version != "1.10.0":
        command.append("-O0")
    command += [str(ROOT / source), "-o", str(artifact)]
    run(command, cwd=ROOT, environment=environment, log=log)
    ir_path = Path(str(artifact) + ".ll")
    object_path = Path(str(artifact) + ".o")
    target = llvm_target(ir_path)
    run([compiler, "run", "scripts/ci/audit.cr", "--", str(ir_path)], cwd=ROOT, environment=environment, log=log)
    executable = artifact.with_suffix("")
    run(["/usr/bin/cc", "-arch", "x86_64", "-mmacosx-version-min=12.0", str(artifact) + ".o",
         "-o", str(executable), "-Wl,-dead_strip"], cwd=ROOT, environment=environment, log=log)
    architectures = command_text(["/usr/bin/xcrun", "lipo", "-archs", str(executable)]).split()
    if architectures != ["x86_64"]:
        raise BuildError("Linked executable is not a sole x86-64 Mach-O: %s" % executable)
    imports = command_text(["/usr/bin/xcrun", "nm", "-u", str(executable)]).strip()
    if imports:
        raise BuildError("Executable imports external symbols: %s" % executable)
    return executable, {"target": target, "architectures": architectures, "ir_sha256": digest(ir_path),
                        "object_sha256": digest(object_path), "executable_sha256": digest(executable)}


def build_campaign(kind, compilers, output):
    # A campaign writes only its own bundle and manifest. The caller records a
    # failure instead of letting a spawn error suppress task-token preparation.
    bundle = output / kind
    bundle.mkdir(mode=0o700)
    (bundle / "bin").mkdir(mode=0o700)
    copy_runner(bundle)
    write_bundle_readme(bundle, kind)
    builds = []
    artifacts = {}
    for label, version in COMPILERS:
        compiler = compilers[label]
        for optimization in ("development", "release"):
            name = label + "-" + optimization
            work = output / "work" / kind / name
            work.mkdir(parents=True, mode=0o700)
            log_path = output / "logs" / (kind + "-" + name + ".log")
            with log_path.open("w", encoding="utf-8") as log:
                probe_artifact = work / kind
                probe, hashes = build_one(compiler, version, optimization, KIND_SOURCES[kind][0], probe_artifact, work, log)
                probe_destination = bundle / "bin" / (kind + "-" + name)
                shutil.copy2(probe, probe_destination)
                probe_destination.chmod(0o700)
                build = {"name": name, "compiler_version": version, "optimization": optimization,
                         "path": "bin/" + kind + "-" + name}
                if kind == "spawn":
                    target_artifact = work / "spawn-target"
                    target, target_hashes = build_one(compiler, version, optimization, KIND_SOURCES[kind][1], target_artifact, work, log)
                    target_destination = bundle / "bin" / ("spawn-target-" + name)
                    shutil.copy2(target, target_destination)
                    target_destination.chmod(0o700)
                    build["target_path"] = "bin/spawn-target-" + name
                    for field, value in target_hashes.items():
                        hashes["target_" + field] = value
            builds.append(build)
            artifacts[name] = hashes
    return {"status": "built", "manifest_sha256": make_manifest(bundle, kind, builds),
            "builds": builds, "artifacts": artifacts}


def build_campaigns(campaigns, compilers, output):
    selected = set(campaigns)
    results = {kind: {"status": "not_requested"} for kind in CAMPAIGNS}
    for kind in CAMPAIGNS:
        if kind not in selected:
            continue
        try:
            results[kind] = build_campaign(kind, compilers, output)
        except (BuildError, OSError, ValueError) as error:
            # Do not present a partial directory as a qualifying lane: it has
            # no manifest, and its failure remains explicit in the parent
            # receipt while later selected campaigns continue.
            results[kind] = {"status": "failed", "error": str(error)}
    return results


def main(argv=None):
    output = None
    receipt = None
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current", required=True, help="Crystal 1.22.2 invocation path; a reviewed launcher is retained for builds")
    parser.add_argument("--current-binary", help="actual Mach-O behind an unrecognized current compiler wrapper")
    parser.add_argument("--floor", required=True, help="Crystal 1.10.0 invocation path; a reviewed launcher is retained for builds")
    parser.add_argument("--floor-binary", help="actual Mach-O behind an unrecognized floor compiler wrapper")
    parser.add_argument("--campaign", action="append", choices=CAMPAIGNS,
                        help="build only this independent campaign; repeat to build both (default: both)")
    parser.add_argument("--output", required=True, help="new external parent directory for selected bundles and receipts")
    args = parser.parse_args(argv)
    try:
        require_build_host()
        output = base.safe_output(Path(args.output), ROOT)
        output.mkdir(parents=True, exist_ok=False, mode=0o700)
        compilers = {label: str(invocation_path(getattr(args, label))) for label, _ in COMPILERS}
        campaigns = tuple(dict.fromkeys(args.campaign or CAMPAIGNS))
        receipt = {
            "schema": 1,
            "status": "incomplete",
            "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "host": {"system": platform.system(), "architecture": platform.machine(), "deployment_target": "12.0"},
            "toolchain": {},
            "compilers": {},
            "selected_campaigns": list(campaigns),
            "campaigns": {kind: {"status": "not_requested"} for kind in CAMPAIGNS},
            "sources": source_inventory(),
            "source_unchanged": False,
            "layout_assertion": {"status": "not_requested"},
        }
        receipt["toolchain"] = toolchain_receipt()
        for label, version in COMPILERS:
            receipt["compilers"][label] = compiler_receipt(compilers[label], version, getattr(args, label + "_binary"))
        (output / "logs").mkdir(mode=0o700)
        buildable_campaigns = campaigns
        # This assertion proves the private spawn profile only. Keep it in the
        # spawn lane so a task-token-only request does not acquire a spawn
        # prerequisite, and a spawn-layout failure still leaves task-token able
        # to prepare its own independent bundle.
        if "spawn" in campaigns:
            layout_log = output / "logs" / "darwin21-spawn-layout.log"
            layout = {"source_sha256": digest(ROOT / "scripts/compat/darwin21_spawn_layout.c"),
                      "log": "logs/darwin21-spawn-layout.log"}
            try:
                with layout_log.open("w", encoding="utf-8") as log:
                    environment = os.environ.copy()
                    run(["/usr/bin/cc", "-arch", "x86_64", "-mmacosx-version-min=12.0", "-std=c11", "-Wall", "-Werror",
                         "-fsyntax-only", str(ROOT / "scripts/compat/darwin21_spawn_layout.c")], cwd=ROOT, environment=environment, log=log)
                layout["status"] = "compiled"
            except BuildError as error:
                layout["status"] = "failed"
                layout["error"] = str(error)
                receipt["campaigns"]["spawn"] = {"status": "failed", "error": str(error)}
                buildable_campaigns = tuple(kind for kind in campaigns if kind != "spawn")
            receipt["layout_assertion"] = layout
        built_campaigns = build_campaigns(buildable_campaigns, compilers, output)
        for kind in buildable_campaigns:
            receipt["campaigns"][kind] = built_campaigns[kind]
        receipt["source_unchanged"] = receipt["sources"] == source_inventory()
        if not receipt["source_unchanged"]:
            raise BuildError("Source changed during bundle build")
        failed = [kind for kind in campaigns if receipt["campaigns"][kind]["status"] != "built"]
        receipt["status"] = "built" if not failed else "failed"
        receipt["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (output / "build-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        for kind in campaigns:
            campaign = receipt["campaigns"][kind]
            if campaign["status"] == "built":
                print("Built manifest-bound %s bundle:" % kind)
                print(output / kind)
            else:
                print("%s campaign failed: %s" % (kind, campaign["error"]), file=sys.stderr)
        return 0 if not failed else 1
    except (BuildError, OSError, ValueError) as error:
        if output is not None and receipt is not None:
            receipt["status"] = "failed"
            receipt["error"] = str(error)
            receipt["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            try:
                (output / "build-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            except OSError:
                pass
        print("Build failed: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
