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

COMPILERS = (("current", "1.22.2"), ("floor", "1.10.0"))
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


def compiler_identity(path, expected):
    output = command_text([path, "--version"])
    if not re.match(r"^Crystal " + re.escape(expected) + r"(?:\s|$)", output):
        raise BuildError("Expected Crystal %s at %s" % (expected, path))
    if "Default target: x86_64-apple-" not in output:
        raise BuildError("Compiler does not report an x86-64 Apple default target: %s" % path)
    return output.strip()


def compiler_receipt(path, expected):
    architectures = command_text(["/usr/bin/xcrun", "lipo", "-archs", path]).split()
    if "x86_64" not in architectures:
        raise BuildError("Crystal compiler binary lacks x86-64 code: %s" % path)
    return {"path": path, "sha256": digest(Path(path)), "architectures": architectures,
            "description": compiler_identity(path, expected)}


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
        "cases": [
            {"id": kind, "exit_code": 0, "stdout": "NK_OK %s\n" % kind, "stderr": ""},
        ],
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


def build_campaign(kind, compilers, output, receipt):
    bundle = output / kind
    bundle.mkdir(mode=0o700)
    (bundle / "bin").mkdir(mode=0o700)
    copy_runner(bundle)
    write_bundle_readme(bundle, kind)
    builds = []
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
            receipt["artifacts"][kind + "/" + name] = hashes
    receipt["bundles"][kind] = {"manifest_sha256": make_manifest(bundle, kind, builds), "builds": builds}


def main(argv=None):
    output = None
    receipt = None
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current", required=True, help="Crystal 1.22.2 x86-64 compiler path")
    parser.add_argument("--floor", required=True, help="Crystal 1.10.0 x86-64 compiler path")
    parser.add_argument("--output", required=True, help="new external parent directory for both bundles and receipts")
    args = parser.parse_args(argv)
    try:
        require_build_host()
        output = base.safe_output(Path(args.output), ROOT)
        output.mkdir(parents=True, exist_ok=False, mode=0o700)
        compilers = {label: str(Path(getattr(args, label)).resolve()) for label, _ in COMPILERS}
        receipt = {
            "schema": 1,
            "status": "incomplete",
            "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "host": {"system": platform.system(), "architecture": platform.machine(), "deployment_target": "12.0"},
            "toolchain": {},
            "compilers": {},
            "sources": source_inventory(),
            "source_unchanged": False,
            "layout_assertion": {},
            "artifacts": {},
            "bundles": {},
        }
        receipt["toolchain"] = toolchain_receipt()
        for label, version in COMPILERS:
            receipt["compilers"][label] = compiler_receipt(compilers[label], version)
        (output / "logs").mkdir(mode=0o700)
        layout_log = output / "logs" / "darwin21-spawn-layout.log"
        with layout_log.open("w", encoding="utf-8") as log:
            environment = os.environ.copy()
            run(["/usr/bin/cc", "-arch", "x86_64", "-mmacosx-version-min=12.0", "-std=c11", "-Wall", "-Werror",
                 "-fsyntax-only", str(ROOT / "scripts/compat/darwin21_spawn_layout.c")], cwd=ROOT, environment=environment, log=log)
        receipt["layout_assertion"] = {"status": "compiled", "source_sha256": digest(ROOT / "scripts/compat/darwin21_spawn_layout.c"),
                                       "log": "logs/darwin21-spawn-layout.log"}
        for kind in ("spawn", "task-token"):
            build_campaign(kind, compilers, output, receipt)
        receipt["source_unchanged"] = receipt["sources"] == source_inventory()
        if not receipt["source_unchanged"]:
            raise BuildError("Source changed during bundle build")
        receipt["status"] = "built"
        receipt["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (output / "build-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("Built separate manifest-bound bundles:")
        print(output / "spawn")
        print(output / "task-token")
        return 0
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
