#!/usr/bin/env python3
"""Bounded source-bound Darwin qualification; Python standard library only."""
import argparse
from datetime import datetime, timezone
import gzip
import errno
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import select
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 1
OUTPUT_LIMIT = 65536
CASE_TIMEOUT = 12
BUILD_TIMEOUT = 300
CASE_IDS = ("descriptor", "directory", "socket", "resource", "session", "exec", "signal", "audit", "event", "process")
PROFILE_IDENTITIES = {
    "macos-15-arm64": (15, 24, "arm64"), "macos-15-x86_64": (15, 24, "x86_64"),
    "macos-26-arm64": (26, 25, "arm64"), "macos-26-x86_64": (26, 25, "x86_64"),
}
# Official macOS 1.10.0/1.22.2 launchers, read on 2026-11-10. Only this exact
# script is mapped to its package's embedded compiler; arbitrary shell is not parsed.
OFFICIAL_LAUNCHER_SHA256 = "541fa514cc2207fd3168d44e8a5aa13d65a1e3b2258b1636056631e45b61635d"
MACH_O_MAGICS = (b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe",
                 b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca", b"\xca\xfe\xba\xbf", b"\xbf\xba\xfe\xca")


class QualificationError(Exception):
    pass


class ExitObserver:
    """Observe child exit while preserving its unreaped PID/PGID reservation."""
    def __init__(self, pid):
        self.pid = pid
        self.queue = None
        self.already_exited = False
        if hasattr(select, "kqueue"):
            self.queue = select.kqueue()
            event = select.kevent(pid, filter=select.KQ_FILTER_PROC,
                                  flags=select.KQ_EV_ADD | select.KQ_EV_ONESHOT,
                                  fflags=select.KQ_NOTE_EXIT)
            try:
                events = self.queue.control([event], 1, 0)
                self.already_exited = self.validate_events(events)
            except ProcessLookupError:
                # Confirm the registration race against this own unreaped PID.
                # No other waiter exists; its zombie still reserves the PGID.
                try:
                    result = subprocess.run(["/bin/ps", "-o", "pid=,stat=", "-p", str(pid)],
                                            capture_output=True, text=True, timeout=2, check=False)
                    fields = result.stdout.split()
                    if result.returncode != 0 or len(fields) != 2 or fields[0] != str(pid) or not fields[1].startswith("Z"):
                        raise QualificationError("Cannot confirm exited unreaped child after kqueue registration race")
                    self.already_exited = True
                except BaseException:
                    self.queue.close()
                    raise
            except BaseException:
                self.queue.close()
                raise
        elif not (hasattr(os, "waitid") and hasattr(os, "WNOWAIT")):
            raise QualificationError("Host cannot observe child exit without reaping")

    def exited(self):
        if self.already_exited:
            return True
        if self.queue is not None:
            return self.validate_events(self.queue.control(None, 1, 0))
        result = os.waitid(os.P_PID, self.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        return result is not None

    def validate_events(self, events):
        for event in events:
            if event.flags & select.KQ_EV_ERROR:
                if event.data == errno.ESRCH:
                    raise ProcessLookupError(errno.ESRCH, "Child exited before registration")
                raise OSError(event.data, "Child exit observation failed")
            if event.ident != self.pid or event.filter != select.KQ_FILTER_PROC or not event.fflags & select.KQ_NOTE_EXIT:
                raise QualificationError("Unexpected child exit observation")
        return bool(events)

    def close(self):
        if self.queue is not None:
            self.queue.close()


def spec_runner_source(root, entry_directory=None):
    root = Path(root)
    files = sorted(path.relative_to(root).as_posix() for path in (root / "spec").rglob("*_spec.cr"))
    if not files:
        raise QualificationError("No Crystal spec files found")
    entry_directory = Path(entry_directory) if entry_directory is not None else root
    return "".join("require " + json.dumps("./" + Path(os.path.relpath(root / name, entry_directory)).as_posix()) + "\n" for name in files), files


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def compiler_version(description):
    match = re.search(r"\bCrystal (\d+\.\d+\.\d+)(?:\s|$)", description)
    target = re.search(r"^Default target: (.+)$", description, re.M)
    if not match or not target:
        raise QualificationError("Compiler version output lacks version or default target")
    return match[1], target[1].strip()


def resolve_compiler_binary(invocation, explicit=None):
    invocation = Path(invocation)
    with invocation.open("rb") as stream:
        direct = stream.read(4) in MACH_O_MAGICS
    if explicit:
        binary, resolution = Path(explicit).expanduser().resolve(), "explicit-operator-path"
    elif direct:
        binary, resolution = invocation, "direct-mach-o"
    elif sha256_file(invocation) == OFFICIAL_LAUNCHER_SHA256 and invocation.name == "crystal" and invocation.parent.name == "bin":
        binary, resolution = (invocation.parent.parent / "embedded/bin/crystal").resolve(), "official-launcher-layout"
    else:
        raise QualificationError("Cannot resolve actual compiler binary; supply --compiler-binary for a trusted local wrapper")
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise QualificationError("Compiler binary is missing or not executable")
    with binary.open("rb") as stream:
        if stream.read(4) not in MACH_O_MAGICS:
            raise QualificationError("Actual compiler binary must be Mach-O, not a launcher")
    return binary, resolution


def validate_compiler_identity(compiler, profile):
    try:
        invocation, binary = compiler["invocation"], compiler["binary"]
        if compiler["identity_scope"] != "compiler-binary-and-invocation-only":
            raise QualificationError("Origin compiler identity scope is incomplete")
        for identity in (invocation, binary):
            if not isinstance(identity["path"], str) or not Path(identity["path"]).is_absolute() or not re.fullmatch(r"[0-9a-f]{64}", identity["sha256"]):
                raise QualificationError("Origin compiler path/hash identity is incomplete")
        if binary["resolution"] not in ("direct-mach-o", "official-launcher-layout", "explicit-operator-path"):
            raise QualificationError("Origin compiler binary resolution is unknown")
        if binary["resolution"] == "direct-mach-o" and (invocation["path"] != binary["path"] or invocation["sha256"] != binary["sha256"]):
            raise QualificationError("Origin direct compiler binary differs from invocation")
        architectures = binary["architectures"]
        if not isinstance(architectures, list) or not architectures or len(architectures) != len(set(architectures)) or not set(architectures).issubset({"arm64", "x86_64"}) or profile["architecture"] not in architectures:
            raise QualificationError("Compiler binary lacks profile architecture")
        version, target = compiler_version(compiler["description"])
        binary_version, binary_target = compiler_version(binary["description"])
        if version not in ("1.10.0", "1.22.2") or version != compiler["version"] or binary_version != version or binary["version"] != version:
            raise QualificationError("Compiler invocation and binary versions differ")
        architecture = "arm64" if target.startswith(("aarch64-", "arm64-")) else "x86_64" if target.startswith("x86_64-") else None
        if architecture != profile["architecture"] or not re.search(r"apple-(?:macosx|darwin)", target) or target != compiler["default_target"] or target != binary_target or target != binary["default_target"]:
            raise QualificationError("Compiler invocation and binary targets differ from profile")
    except (KeyError, TypeError, AttributeError) as error:
        raise QualificationError("Origin compiler binary identity is incomplete") from error


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def source_identity(root):
    root = Path(root)
    files = set()
    for directory in ("src", "scripts", "spec", "ci", "tests", ".github/workflows"):
        folder = root / directory
        if folder.exists():
            files.update(p for p in folder.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    for name in ("shard.yml", "Makefile", "AGENTS.md"):
        if (root / name).is_file():
            files.add(root / name)
    return {p.relative_to(root).as_posix(): sha256_file(p) for p in sorted(files)}


def load_config(root):
    try:
        profiles = json.loads((Path(root) / "ci/profiles.json").read_text())
        cases = json.loads((Path(root) / "ci/cases.json").read_text())
        if profiles["schema"] != SCHEMA or cases["schema"] != SCHEMA:
            raise QualificationError("Unsupported configuration schema")
        if profiles["compilers"] != ["1.10.0", "1.22.2"]:
            raise QualificationError("Compiler matrix must be exactly 1.10.0 and 1.22.2")
        definitions = cases["cases"]
        if [c["id"] for c in definitions] != list(CASE_IDS):
            raise QualificationError("Case roster must contain all ten required cases in order")
        for case in definitions:
            if not isinstance(case["minimum_darwin"], int) or not isinstance(case["exit_code"], int):
                raise QualificationError("Invalid numeric case contract")
            if not isinstance(case["stdout"], str) or not isinstance(case["stderr"], str):
                raise QualificationError("Invalid completion contract")
        return profiles, definitions
    except (KeyError, TypeError, ValueError, OSError) as error:
        raise QualificationError("Invalid qualification configuration: " + str(error)) from error


def select_profile(profiles, identifier):
    if identifier not in PROFILE_IDENTITIES:
        raise QualificationError("Unknown profile: " + str(identifier))
    try:
        profile = profiles["profiles"][identifier]
        actual = (profile["os_major"], profile["darwin_major"], profile["architecture"])
    except (KeyError, TypeError) as error:
        raise QualificationError("Missing profile definition") from error
    if actual != PROFILE_IDENTITIES[identifier]:
        raise QualificationError("Profile identity differs from declared OS/kernel/architecture")
    return profile


def major(value):
    try:
        return int(value.split(".")[0])
    except (ValueError, AttributeError):
        raise QualificationError("Missing or invalid host version")


def validate_host(host, profile, allow_translation=False, ci=False):
    if allow_translation and ci:
        raise QualificationError("Translation exception is forbidden in CI")
    if host.get("system") != "Darwin":
        raise QualificationError("Native qualification requires Darwin")
    if major(host.get("os_version")) != profile["os_major"]:
        raise QualificationError("Actual macOS major does not match profile")
    if major(host.get("darwin_release")) != profile["darwin_major"]:
        raise QualificationError("Actual Darwin major does not match profile")
    if host.get("translated") not in (True, False) or host.get("hardware_arm64") not in (True, False):
        raise QualificationError("Host translation/hardware identity is unknown")
    exception = allow_translation and host["hardware_arm64"] and profile["architecture"] == "x86_64"
    if host["translated"] and not exception:
        raise QualificationError("Translated execution cannot qualify a native runner profile")
    if host.get("architecture") != profile["architecture"] and not exception:
        raise QualificationError("Actual process architecture does not match profile")
    if profile["architecture"] == "arm64" and not host["hardware_arm64"]:
        raise QualificationError("ARM64 profile requires ARM64 hardware")
    if profile["architecture"] == "x86_64" and host["hardware_arm64"] and not exception:
        raise QualificationError("Intel native profile requires Intel hardware")


def run_bounded(command, log_prefix, *, timeout, output_limit=OUTPUT_LIMIT, cwd=None, env=None):
    """Drain both streams with bounded RAM/disk, then kill/reap the process group."""
    prefix = Path(log_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    captured = {"stdout": bytearray(), "stderr": bytearray()}
    truncated, timed_out, spawn_error, code, process = False, False, None, None, None
    observer, selector, exited, group_cleaned = None, None, False, False
    try:
        process = subprocess.Popen([str(x) for x in command], cwd=cwd, env=env,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True)
        observer = ExitObserver(process.pid)
        selector = selectors.DefaultSelector()
        for name in captured:
            stream = getattr(process, name)
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        deadline = started + timeout
        while selector.get_map() or not exited:
            exited = exited or observer.exited()
            if exited and not group_cleaned:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                except PermissionError:
                    # Darwin returns EPERM when only the exited zombie remains.
                    # NOTE_EXIT already proved that the reserved leader exited.
                    pass
                group_cleaned = True
            if time.monotonic() >= deadline:
                timed_out = True
                break
            for key, _ in selector.select(min(0.1, max(0, deadline - time.monotonic()))):
                block = os.read(key.fileobj.fileno(), 16384)
                if not block:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                available = output_limit - len(captured[key.data])
                captured[key.data].extend(block[:max(available, 0)])
                truncated = truncated or len(block) > available
    except OSError as error:
        spawn_error = str(error)
    finally:
        if process is not None:
            # The leader remains unreaped through the final group operation, so
            # no reused numeric PGID can target another process group.
            if not group_cleaned:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                except PermissionError:
                    if not exited and not (observer is not None and observer.exited()):
                        spawn_error = "Process group cleanup could not confirm exited leader"
                        process.kill()
            code = process.wait()
            for name in captured:
                stream = getattr(process, name)
                if stream is not None and not stream.closed:
                    stream.close()
        if observer is not None:
            observer.close()
        if selector is not None:
            selector.close()
    if spawn_error:
        captured["stderr"].extend(spawn_error.encode()[:output_limit])
    for name, data in captured.items():
        Path(str(prefix) + "." + name).write_bytes(data)
    status = "timed_out" if timed_out else "incomplete" if spawn_error else "crashed" if code < 0 else "passed" if code == 0 else "failed"
    return {"status": status, "exit_code": code, "duration_seconds": round(time.monotonic() - started, 4),
            "stdout": captured["stdout"].decode("utf-8", errors="replace"),
            "stderr": captured["stderr"].decode("utf-8", errors="replace"),
            "output_truncated": truncated, "command": [str(x) for x in command],
            "stdout_log": str(prefix) + ".stdout", "stderr_log": str(prefix) + ".stderr"}


def classify_case(result, expected, darwin_major):
    result = dict(result, case=expected["id"], expected=expected, completion_observed=False)
    if darwin_major < expected["minimum_darwin"]:
        result["status"] = "unsupported"
        result["reason"] = "Declared minimum Darwin is " + str(expected["minimum_darwin"])
    elif result["status"] in ("crashed", "timed_out", "incomplete"):
        pass
    elif result["output_truncated"]:
        result["status"] = "failed"
        result["reason"] = "Worker output exceeded bound"
    elif result["exit_code"] != expected["exit_code"]:
        result["status"] = "failed"
        result["reason"] = "Unexpected exit code"
    elif result["stdout"] != expected["stdout"]:
        result["status"] = "incomplete" if not result["stdout"] else "failed"
        result["reason"] = "Missing or incorrect completion marker"
    elif result["stderr"] != expected["stderr"]:
        result["status"] = "failed"
        result["reason"] = "Unexpected worker stderr"
    else:
        result["status"] = "passed"
        result["completion_observed"] = True
    return result


def all_passed(results):
    return bool(results) and all(result.get("status") == "passed" for result in results)


def verify_bundle_files(bundle, manifest):
    bundle = Path(bundle).resolve()
    if not isinstance(manifest, dict) or not manifest:
        raise QualificationError("Bundle has no file hashes")
    if len(manifest) > 256:
        raise QualificationError("Bundle exceeds file count bound")
    total = 0
    for name, digest in manifest.items():
        if not isinstance(name, str) or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise QualificationError("Malformed bundle file digest")
        path = bundle / name
        if Path(name).is_absolute() or ".." in Path(name).parts or not path.resolve().is_relative_to(bundle):
            raise QualificationError("Bundle file escapes bundle root")
        if path.is_symlink() or not path.is_file():
            raise QualificationError("Missing or altered bundle file: " + name)
        total += path.stat().st_size
        if total > 32 * 1024 * 1024:
            raise QualificationError("Bundle exceeds 32 MiB bound")
        if sha256_file(path) != digest:
            raise QualificationError("Missing or altered bundle file: " + name)


def validate_replay_identity(origin, destination, source):
    if origin.get("status") != "passed" or origin.get("mode") != "qualify":
        raise QualificationError("Replay requires a passed original qualification")
    original = origin.get("profile_definition", {})
    if original.get("os_major") != 15 or original.get("darwin_major") != 24:
        raise QualificationError("Replay origin must be macOS 15 / Darwin 24")
    if destination.get("os_major") != 26 or destination.get("darwin_major") != 25:
        raise QualificationError("Replay destination must be macOS 26 / Darwin 25")
    if original.get("architecture") != destination.get("architecture"):
        raise QualificationError("Replay architecture differs from origin")
    if origin.get("source") != source:
        raise QualificationError("Replay source/config identity differs from current checkout")
    if origin.get("translation_exception"):
        raise QualificationError("Local translated qualification cannot supply native forward proof")
    validate_compiler_identity(origin.get("compiler"), original)


def required_native_stages():
    stages = {"identity-" + name for name in ("os-version", "os-build", "hardware-arm64", "translation",
                                             "cpu", "sdk-path", "sdk-version", "cc", "cc-version", "linker", "compiler")}
    stages.update(("identity-compiler-binary", "identity-compiler-binary-architectures"))
    stages.update(("python-tests", "format", "build-spec", "spec", "core-native", "build-auditor"))
    for optimization in ("development", "release"):
        stages.add("execute-probe-" + optimization)
        for fixture in ("probe", "behavior", "exec"):
            name = fixture + "-" + optimization
            stages.update(("architecture-" + name, "imports-" + name))
            if fixture != "probe":
                stages.update(prefix + name for prefix in ("compile-", "audit-ir-", "link-"))
    return stages


def validate_origin_proof(origin, profile, cases):
    validate_host(origin.get("host", {}), profile, ci=True)
    if origin.get("artifact_execution_translated"):
        raise QualificationError("Origin artifact execution was translated")
    if origin.get("source_unchanged") is not True or origin.get("source_after") != origin.get("source"):
        raise QualificationError("Origin source/config tree changed during qualification")
    stages = origin.get("stages", [])
    names = [stage.get("name") for stage in stages]
    if len(names) != len(set(names)) or not required_native_stages().issubset(names):
        raise QualificationError("Origin qualification stage roster is incomplete or duplicated")
    if not all_passed(stages):
        raise QualificationError("Origin has failed or incomplete stages")
    for stage in stages:
        optional = stage["name"] in ("identity-hardware-arm64", "identity-translation")
        if stage.get("output_truncated") or (stage.get("exit_code") != 0 and not optional):
            raise QualificationError("Origin stage lacks successful bounded completion")
    for optimization in ("development", "release"):
        observed = [c for c in origin.get("cases", []) if c.get("optimization") == optimization]
        if len(observed) != 10 or {c.get("case") for c in observed} != set(CASE_IDS):
            raise QualificationError("Origin case roster is incomplete")
        for expected in cases:
            result = next(c for c in observed if c["case"] == expected["id"])
            if not result.get("completion_observed") or classify_case(dict(result, output_truncated=result.get("output_truncated", False)), expected, profile["darwin_major"])["status"] != "passed":
                raise QualificationError("Origin lacks exact observed case completion")


class Runner:
    def __init__(self, args, root=ROOT):
        self.args = args
        self.root = Path(root).resolve()
        self.output = Path(args.output).expanduser().resolve()
        if self.output == self.root or self.output.is_relative_to(self.root):
            raise QualificationError("Output must be outside the repository")
        self.output.mkdir(parents=True, exist_ok=True)
        if (self.output / "receipt.json").exists() and args.mode != "record-failure":
            raise QualificationError("Output already contains a receipt")
        self.logs = self.output / "logs"
        self.logs.mkdir(exist_ok=True)
        self.receipt = {"schema": SCHEMA, "mode": args.mode, "profile": args.profile,
                        "started_at": datetime.now(timezone.utc).isoformat(), "status": "incomplete",
                        "consumer_spawn": "not_qualified_by_this_suite", "stages": [], "cases": [],
                        "artifacts": {}, "source": source_identity(self.root),
                        "translation_exception": bool(getattr(args, "allow_translation", False))}
        self.receipt["host"] = {"system": platform.system(), "architecture": platform.machine(),
                                "darwin_release": platform.release(), "kernel": platform.version(),
                                "os_version": platform.mac_ver()[0]}
        workflow_fields = ("GITHUB_REPOSITORY", "GITHUB_SHA", "GITHUB_WORKFLOW_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT",
                           "GITHUB_WORKFLOW", "GITHUB_JOB", "GITHUB_REF", "RUNNER_OS", "RUNNER_ARCH", "ImageVersion")
        self.receipt["workflow"] = {name: os.environ[name] for name in workflow_fields if name in os.environ}
        if os.environ.get("GITHUB_REPOSITORY") and os.environ.get("GITHUB_RUN_ID"):
            self.receipt["workflow"]["run_url"] = "https://github.com/" + os.environ["GITHUB_REPOSITORY"] + "/actions/runs/" + os.environ["GITHUB_RUN_ID"]
        self.environment = dict(os.environ, CRYSTAL_CACHE_DIR=str(self.output / "compiler-cache"),
                                MACOSX_DEPLOYMENT_TARGET="15.0", PYTHONDONTWRITEBYTECODE="1")
        self.profile = None
        self.cases = None

    def stage(self, name, command, timeout=BUILD_TIMEOUT, require=True, env=None):
        result = run_bounded(command, self.logs / name, timeout=timeout, cwd=self.root,
                             env=env or self.environment)
        result["name"] = name
        if result["output_truncated"]:
            result["status"] = "failed"
            result["reason"] = "Stage output exceeded bound"
        self.receipt["stages"].append(result)
        if require and result["status"] != "passed":
            raise QualificationError("Stage failed: " + name + " (" + result["status"] + ")")
        return result

    def observe(self, name, command, required=True):
        return self.stage("identity-" + name, command, timeout=20, require=required)

    def preflight(self):
        profiles, self.cases = load_config(self.root)
        self.profile = select_profile(profiles, self.args.profile)
        self.receipt["profile_definition"] = self.profile
        self.receipt["configuration"] = {"compilers": profiles["compilers"], "cases": self.cases}
        self.receipt["configuration"]["manifests"] = {
            path.name: json.loads(path.read_text()) for path in sorted((self.root / "ci").glob("*.json"))
        }
        host = {"system": platform.system(), "architecture": platform.machine(),
                "darwin_release": platform.release(), "kernel": platform.version(),
                "os_version": platform.mac_ver()[0], "python": platform.python_version(),
                "translated": None, "hardware_arm64": None}
        self.receipt["host"] = host
        if host["system"] != "Darwin":
            validate_host(host, self.profile)
        host["os_version"] = self.observe("os-version", ["/usr/bin/sw_vers", "-productVersion"])["stdout"].strip()
        host["os_build"] = self.observe("os-build", ["/usr/bin/sw_vers", "-buildVersion"])["stdout"].strip()
        hardware = self.observe("hardware-arm64", ["/usr/sbin/sysctl", "-n", "hw.optional.arm64"], required=False)
        if hardware["exit_code"] == 0 and hardware["stdout"].strip() in ("0", "1"):
            host["hardware_arm64"] = hardware["stdout"].strip() == "1"
        elif host["architecture"] == "x86_64":
            cpu = self.observe("hardware-machine", ["/usr/sbin/sysctl", "-n", "hw.machine"])
            if cpu["stdout"].strip() == "x86_64":
                host["hardware_arm64"] = False
        translated = self.observe("translation", ["/usr/sbin/sysctl", "-in", "sysctl.proc_translated"], required=False)
        if translated["exit_code"] == 0 and translated["stdout"].strip() in ("0", "1"):
            host["translated"] = translated["stdout"].strip() == "1"
        elif host["hardware_arm64"] is False or host["architecture"] == "arm64":
            host["translated"] = False
        host["cpu"] = self.observe("cpu", ["/usr/sbin/sysctl", "-n", "machdep.cpu.brand_string"])["stdout"].strip()
        validate_host(host, self.profile, self.receipt["translation_exception"],
                      bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS")))
        self.receipt["artifact_execution_translated"] = host["hardware_arm64"] and self.profile["architecture"] == "x86_64"
        # Darwin's optional sysctl key absence is recorded, with resolved identity.
        for stage in self.receipt["stages"]:
            if stage["name"] in ("identity-translation", "identity-hardware-arm64") and stage["status"] == "failed":
                stage["status"] = "passed"
                stage["reason"] = "Absent optional sysctl key; identity resolved by architecture/hardware evidence"
        toolchain = {}
        for name, command in (
                ("sdk-path", ["xcrun", "--show-sdk-path"]), ("sdk-version", ["xcrun", "--show-sdk-version"]),
                ("cc", ["xcrun", "--find", "clang"]), ("cc-version", ["cc", "--version"]),
                ("linker", ["xcrun", "ld", "-v"])):
            result = self.observe(name, command)
            toolchain[name] = (result["stdout"] + result["stderr"]).strip()
        self.receipt["toolchain"] = toolchain
        self.receipt["build_environment"] = {"MACOSX_DEPLOYMENT_TARGET": "15.0", "persistent_cache": False}

    def qualify(self):
        self.preflight()
        compiler = self.identify_compiler()
        self.stage("python-tests", [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests"])
        self.stage("format", [compiler, "tool", "format", "--check", "src", "spec", "scripts"])
        # Crystal 1.10's spec command cannot select single-module output.
        source, spec_files = spec_runner_source(self.root, self.output)
        spec_entry = self.output / "spec-runner.cr"
        spec_entry.write_text(source)
        self.receipt["spec_entry"] = {"sha256": sha256_file(spec_entry), "files": spec_files,
                                       "sources": {name: self.receipt["source"][name] for name in spec_files}}
        spec_executable = self.output / "spec-runner"
        self.environment["CRYSTAL_SPEC_COMPILER_BIN"] = compiler
        self.stage("build-spec", [compiler, "build", "--single-module", "--error-on-warnings",
                                  str(spec_entry), "-o", str(spec_executable)])
        self.stage("spec", [str(spec_executable), "--no-color"])
        original = self.output / "core"
        self.stage("core-native", [compiler, "run", "--single-module", "scripts/check-native.cr", "--", str(original)])
        manifest_path = original / "manifest.json"
        if not manifest_path.is_file():
            raise QualificationError("Existing native verifier did not produce its manifest")
        self.receipt["core_manifest_sha256"] = sha256_file(manifest_path)
        self.receipt["core_manifest"] = json.loads(manifest_path.read_text())
        self.validate_core_manifest(self.receipt)
        artifact_dir = self.output / "artifacts"
        artifact_dir.mkdir()
        audit = self.output / "audit"
        self.stage("build-auditor", [compiler, "build", "--single-module", "scripts/ci/audit.cr", "-o", str(audit), "--error-on-warnings"])
        for optimization in ("development", "release"):
            self.add_artifact("probe-" + optimization, original / ("probe-" + optimization))
            for fixture in ("behavior", "exec"):
                artifact = artifact_dir / (fixture + "-" + optimization)
                flags = [compiler, "build", "--cross-compile", "--single-module", "--no-debug", "--error-on-warnings",
                         "-Dwithout_main", "--emit", "llvm-ir"]
                if optimization == "release":
                    flags.append("--release")
                elif self.receipt["compiler"]["version"] != "1.10.0":
                    flags.append("-O0")
                flags += [str(self.root / ("spec/native/" + fixture + ".cr")), "-o", str(artifact)]
                name = fixture + "-" + optimization
                self.stage("compile-" + name, flags)
                ir_path = Path(str(artifact) + ".ll")
                ir = ir_path.read_text()
                match = re.search(r'^target triple = "([^"]+)"', ir, re.M)
                if not match:
                    raise QualificationError("Emitted IR has no compiled target triple")
                self.validate_target(match[1])
                self.stage("audit-ir-" + name, [str(audit), str(ir_path)])
                self.stage("link-" + name, ["cc", "-arch", self.profile["architecture"], str(artifact) + ".o",
                                            "-o", str(artifact), "-Wl,-dead_strip"])
                self.add_artifact(name, artifact, ir_sha256=sha256_file(ir_path), target=match[1],
                                  object_sha256=sha256_file(str(artifact) + ".o"))
        self.execute_artifacts()

    def identify_compiler(self):
        compiler = str(Path(self.args.compiler).expanduser().resolve()) if "/" in self.args.compiler else shutil.which(self.args.compiler)
        if not compiler:
            raise QualificationError("Compiler executable not found")
        compiler = str(Path(compiler).resolve())
        self.environment["CRYSTAL"] = compiler
        result = self.observe("compiler", [compiler, "--version"])
        version, target = compiler_version(result["stdout"])
        if version not in self.receipt["configuration"]["compilers"]:
            raise QualificationError("Compiler is outside the exact 1.10.0 / 1.22.2 matrix")
        self.validate_target(target)
        self.receipt["compiler"] = {"version": version, "description": result["stdout"], "default_target": target,
                                    "invocation": {"path": compiler, "sha256": sha256_file(compiler)},
                                    "identity_scope": "compiler-binary-and-invocation-only"}
        binary, resolution = resolve_compiler_binary(compiler, getattr(self.args, "compiler_binary", None))
        identity = {"path": str(binary), "sha256": sha256_file(binary), "resolution": resolution}
        self.receipt["compiler"]["binary"] = identity
        result = self.observe("compiler-binary-architectures", ["xcrun", "lipo", "-archs", str(binary)])
        identity["architectures"] = result["stdout"].strip().split()
        if self.profile["architecture"] not in identity["architectures"]:
            raise QualificationError("Compiler binary lacks profile architecture")
        command = [str(binary), "--version"]
        if self.receipt["translation_exception"] and self.profile["architecture"] == "x86_64":
            command = ["/usr/bin/arch", "-x86_64"] + command
        result = self.observe("compiler-binary", command)
        identity["version"], identity["default_target"] = compiler_version(result["stdout"])
        identity["description"] = result["stdout"]
        validate_compiler_identity(self.receipt["compiler"], self.profile)
        return compiler

    def validate_target(self, target):
        architecture = "arm64" if target.startswith(("aarch64-", "arm64-")) else "x86_64" if target.startswith("x86_64-") else None
        if architecture != self.profile["architecture"] or not re.search(r"apple-(?:macosx|darwin)", target):
            raise QualificationError("Actual compiler target does not match Darwin profile: " + target)

    def audit_executable(self, name, path):
        result = self.stage("architecture-" + name, ["xcrun", "lipo", "-archs", str(path)], timeout=20)
        if result["stdout"].strip().split() != [self.profile["architecture"]]:
            raise QualificationError("Linked executable architecture differs from profile: " + name)
        result = self.stage("imports-" + name, ["xcrun", "nm", "-u", str(path)], timeout=20)
        if result["stdout"].strip() or result["stderr"].strip():
            raise QualificationError("Native executable has imports or nm diagnostics: " + name)

    def add_artifact(self, name, path, **metadata):
        self.audit_executable(name, path)
        self.receipt["artifacts"][name] = {"path": str(path), "sha256": sha256_file(path),
                                             "architecture": self.profile["architecture"], **metadata}

    def execute_artifacts(self):
        expected = {name + "-" + mode for name in ("probe", "behavior", "exec") for mode in ("development", "release")}
        if set(self.receipt["artifacts"]) != expected:
            raise QualificationError("Audited artifact roster is incomplete")
        for name, artifact in self.receipt["artifacts"].items():
            if sha256_file(artifact["path"]) != artifact["sha256"]:
                raise QualificationError("Audited executable changed before execution: " + name)
        self.validate_core_manifest(self.receipt)
        darwin = self.profile["darwin_major"]
        for optimization in ("development", "release"):
            probe = self.receipt["artifacts"]["probe-" + optimization]
            result = self.stage("execute-probe-" + optimization, [probe["path"]], timeout=CASE_TIMEOUT)
            if result["stdout"] or result["stderr"]:
                raise QualificationError("Existing native probe produced unexpected output")
            worker = self.receipt["artifacts"]["behavior-" + optimization]
            executable = self.receipt["artifacts"]["exec-" + optimization]
            for case in self.cases:
                if darwin < case["minimum_darwin"]:
                    result = {"status": "unsupported", "case": case["id"], "optimization": optimization,
                              "reason": "Declared minimum Darwin is " + str(case["minimum_darwin"]), "completion_observed": False}
                else:
                    with tempfile.TemporaryDirectory(prefix="nki-", dir="/tmp") as directory:
                        fixture = Path(directory) / "fixture"
                        if case["id"] == "directory":
                            fixture.mkdir()
                            (fixture / "nk-entry").write_bytes(b"entry")
                        result = run_bounded([worker["path"], case["id"], str(fixture), executable["path"]],
                                             self.logs / ("case-" + optimization + "-" + case["id"]),
                                             timeout=CASE_TIMEOUT, output_limit=4096, cwd=self.root, env=self.environment)
                        result = classify_case(result, case, darwin)
                        result["optimization"] = optimization
                self.receipt["cases"].append(result)
        if len(self.receipt["cases"]) != 20 or not all_passed(self.receipt["cases"]):
            raise QualificationError("One or more required behavior cases did not pass")

    def replay(self):
        self.preflight()
        bundle = Path(self.args.input).expanduser().resolve()
        origin_path = bundle / "receipt.json"
        if origin_path.stat().st_size > 8 * 1024 * 1024:
            raise QualificationError("Origin receipt exceeds size limit")
        origin = json.loads(origin_path.read_text())
        if origin.get("schema") != SCHEMA:
            raise QualificationError("Unsupported origin receipt schema")
        profiles, _ = load_config(self.root)
        original_profile = select_profile(profiles, origin.get("profile"))
        if origin.get("profile_definition") != original_profile:
            raise QualificationError("Origin profile definition is forged or stale")
        validate_replay_identity(origin, self.profile, self.receipt["source"])
        verify_bundle_files(bundle, origin.get("bundle_files"))
        if origin.get("configuration") != self.receipt["configuration"]:
            raise QualificationError("Origin configuration differs from destination")
        if origin.get("compiler", {}).get("version") not in profiles["compilers"]:
            raise QualificationError("Origin compiler is outside qualification matrix")
        validate_origin_proof(origin, original_profile, self.cases)
        entry = origin.get("spec_entry", {})
        _, spec_files = spec_runner_source(self.root)
        if entry.get("files") != spec_files or entry.get("sources") != {name: self.receipt["source"][name] for name in spec_files}:
            raise QualificationError("Origin spec entry does not cover the current complete spec roster")
        if origin["bundle_files"].get("spec-runner.cr") != entry.get("sha256"):
            raise QualificationError("Origin generated spec entry is not bound to bundle")
        if origin["bundle_files"].get("core-manifest.json") != origin["core_manifest_sha256"]:
            raise QualificationError("Original core manifest is not bound to bundle")
        if json.loads((bundle / "core-manifest.json").read_text()) != origin["core_manifest"]:
            raise QualificationError("Original core manifest differs from receipt")
        self.validate_core_manifest(origin)
        self.receipt["origin"] = {"receipt_sha256": sha256_file(origin_path), "profile": origin["profile"],
                                   "compiler": origin["compiler"], "core_manifest_sha256": origin["core_manifest_sha256"]}
        self.receipt["core_manifest"] = origin["core_manifest"]
        self.receipt["core_manifest_sha256"] = origin["core_manifest_sha256"]
        self.receipt["compiler"] = origin["compiler"]
        artifact_dir = self.output / "artifacts"
        artifact_dir.mkdir()
        for name, artifact in origin["artifacts"].items():
            if name not in {n + "-" + mode for n in ("probe", "behavior", "exec") for mode in ("development", "release")}:
                raise QualificationError("Unknown origin artifact")
            relative = "executables/" + name
            if origin["bundle_files"].get(relative) != artifact["sha256"]:
                raise QualificationError("Artifact digest is not bound to bundle manifest")
            path = artifact_dir / name
            shutil.copyfile(bundle / relative, path)
            path.chmod(0o700)
            self.add_artifact(name, path, **{k: v for k, v in artifact.items() if k not in ("path", "sha256", "architecture")})
        self.execute_artifacts()

    def validate_core_manifest(self, receipt):
        core = receipt["core_manifest"]
        if not core.get("sources") or any(receipt["source"].get(name) != digest for name, digest in core["sources"].items()):
            raise QualificationError("Core native proof is not bound to current source")
        if not core.get("assembly"):
            raise QualificationError("Core native proof lacks exact assembly profile")
        for optimization in ("development", "release"):
            artifact = receipt["artifacts"].get("probe-" + optimization)
            if artifact and core["artifacts"].get(optimization + ".executable") != artifact["sha256"]:
                raise QualificationError("Core executable differs from original core proof")

    def finish(self, error=None):
        after = source_identity(self.root)
        self.receipt["source_after"] = after
        self.receipt["source_unchanged"] = after == self.receipt["source"]
        if not self.receipt["source_unchanged"]:
            error = "Source/config tree changed during qualification"
        if error:
            self.receipt["error"] = str(error)
            self.receipt["status"] = "incomplete" if self.args.mode == "record-failure" else "failed"
        elif self.args.mode in ("qualify", "replay") and all_passed(self.receipt["stages"]) and len(self.receipt["cases"]) == 20 and all_passed(self.receipt["cases"]):
            self.receipt["status"] = "passed"
        else:
            self.receipt["status"] = "incomplete"
        self.receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        try:
            self.coverage()
            self.export()
        except Exception as export_error:
            self.receipt["status"] = "failed"
            self.receipt["export_error"] = str(export_error)
            write_json(self.output / "export/receipt.json", self.receipt)
        write_json(self.output / "receipt.json", self.receipt)
        return 0 if self.receipt["status"] == "passed" else 1

    def coverage(self):
        path = self.root / "ci/coverage.json"
        if not path.is_file():
            return
        mapping = json.loads(path.read_text())
        observed = {}
        for operation, definition in mapping["operations"].items():
            case = definition["positive_case"]
            passed = []
            for optimization in ("development", "release"):
                if case == "core":
                    success = any(s["name"] == "execute-probe-" + optimization and s["status"] == "passed" for s in self.receipt["stages"])
                else:
                    success = any(c["case"] == case and c.get("optimization") == optimization and c["status"] == "passed" and c.get("completion_observed") for c in self.receipt["cases"])
                if success:
                    passed.append(optimization)
            observed[operation] = {"positive_case": case, "passed_optimizations": passed}
        self.receipt["positive_coverage"] = observed

    def export(self):
        bundle = self.output / "export"
        bundle.mkdir(exist_ok=True)
        files = {}
        total = 0

        def include(path, relative, compressed=False):
            nonlocal total
            target = bundle / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if compressed:
                with path.open("rb") as source, gzip.open(target, "wb", compresslevel=9) as destination:
                    shutil.copyfileobj(source, destination)
            else:
                shutil.copyfile(path, target)
            total += target.stat().st_size
            if total > 32 * 1024 * 1024:
                target.unlink()
                raise QualificationError("Export exceeds 32 MiB bound")
            files[relative] = sha256_file(target)
            return target

        for path in sorted(self.logs.glob("*")):
            if path.is_file() and not path.is_symlink():
                include(path, "logs/" + path.name)
        if (self.output / "spec-runner.cr").is_file():
            include(self.output / "spec-runner.cr", "spec-runner.cr")
        for name, artifact in self.receipt["artifacts"].items():
            path = Path(artifact["path"])
            if sha256_file(path) != artifact["sha256"]:
                self.receipt["status"] = "failed"
                self.receipt["error"] = "Audited artifact changed before export: " + name
                continue
            include(path, "executables/" + name).chmod(0o700)
        # Compressed IR is retained even if its audit failed; objects/caches stay local.
        for folder in (self.output / "core", self.output / "artifacts"):
            if folder.is_dir():
                for path in sorted(folder.glob("*.ll")):
                    include(path, "ir/" + folder.name + "-" + path.name + ".gz", compressed=True)
        if "core_manifest" in self.receipt:
            original = self.output / "core/manifest.json"
            if not original.is_file():
                original = Path(self.args.input) / "core-manifest.json"
            target = include(original, "core-manifest.json")
            if sha256_file(target) != self.receipt["core_manifest_sha256"]:
                self.receipt["status"] = "failed"
                self.receipt["error"] = "Original core manifest digest mismatch"
        self.receipt["bundle_files"] = files
        self.receipt["bundle_bytes_without_receipt"] = total
        write_json(bundle / "receipt.json", self.receipt)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)
    for mode in ("qualify", "replay", "record-failure"):
        sub = subparsers.add_parser(mode)
        sub.add_argument("--profile", required=True)
        sub.add_argument("--output", required=True)
        if mode != "record-failure":
            sub.add_argument("--allow-translation", action="store_true", help="local diagnostic only; forbidden in CI")
        if mode == "qualify":
            sub.add_argument("--compiler", required=True)
            sub.add_argument("--compiler-binary", help="actual Mach-O compiler behind a trusted local wrapper; explicit operator assertion")
        elif mode == "replay":
            sub.add_argument("--input", required=True)
        else:
            sub.add_argument("--reason", required=True)
            sub.add_argument("--exit-code", type=int, default=1)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    runner = None
    try:
        runner = Runner(args)
        if args.mode == "record-failure":
            existing = runner.output / "receipt.json"
            if existing.exists():
                runner.receipt = json.loads(existing.read_text())
            runner.receipt["stages"].append({"name": "workflow-fallback", "status": "incomplete",
                                             "exit_code": args.exit_code, "reason": args.reason})
            return runner.finish(args.reason)
        getattr(runner, args.mode)()
        return runner.finish()
    except Exception as error:
        print("Qualification failed: " + str(error), file=sys.stderr)
        if runner:
            return runner.finish(error)
        return 1
    except KeyboardInterrupt:
        if runner:
            runner.finish("Runner interrupted before completion")
        return 130


if __name__ == "__main__":
    sys.exit(main())
