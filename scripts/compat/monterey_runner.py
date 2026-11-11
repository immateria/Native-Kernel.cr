#!/usr/bin/env python3
"""Run the shipped unmanaged Intel probes without building or installing anything."""
import argparse
import datetime
import errno
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import select
import selectors
import signal
import subprocess
import sys
import tempfile
import time
import zipfile

SCHEMA = 1
OUTPUT_LIMIT = 65536
CASE_TIMEOUT = 12.0
EXPECTED_HOST = {"os_version": "12.7.6", "os_build": "21H1320", "darwin_release": "21.6.0", "architecture": "x86_64"}
BUILD_ROSTER = {"current-development": ("1.22.2", "development"), "current-release": ("1.22.2", "release"),
                "floor-development": ("1.10.0", "development"), "floor-release": ("1.10.0", "release")}
CASE_ROSTER = {name: (0, "NK_OK " + name + "\n", "") for name in
               ("descriptor", "resource", "session", "event", "collection", "inspection")}
CASE_ROSTER.update({"exec": (37, "NK_EXEC_OK\n", ""), "signal": (0, "NK_OK signal\n", "S")})


class ProbeError(ValueError):
    pass


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def within(path, parent):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def payload_path(root, name):
    if not isinstance(name, str) or not name or "\\" in name:
        raise ProbeError("Invalid payload path")
    pure = PurePosixPath(name)
    if pure.is_absolute() or ".." in pure.parts or str(pure) != name:
        raise ProbeError("Payload paths must be normalized relative paths")
    path = root
    for part in pure.parts:
        path = path / part
        if path.is_symlink():
            raise ProbeError("Symlink payload path: " + name)
    if not path.is_file() or not within(path.resolve(), root):
        raise ProbeError("Missing regular payload: " + name)
    return path


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProbeError("Duplicate manifest key: " + key)
        result[key] = value
    return result


def load_manifest(root):
    path = payload_path(root, "manifest.json")
    if path.stat().st_size > 1024 * 1024:
        raise ProbeError("Manifest exceeds the size bound")
    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs)
    if not isinstance(data, dict) or type(data.get("schema")) is not int or data["schema"] != SCHEMA:
        raise ProbeError("Unsupported manifest schema")
    if data.get("expected_host") != EXPECTED_HOST:
        raise ProbeError("Manifest must name the reviewed Monterey target")
    files = data.get("files")
    if not isinstance(files, dict) or not files or len(files) > 1024:
        raise ProbeError("Manifest must declare the bounded payload inventory")
    if "monterey_runner.py" not in files or "manifest.json" in files:
        raise ProbeError("Inventory must include the runner and exclude the manifest")
    for name, value in files.items():
        payload_path(root, name)
        if not isinstance(value, str) or not re.fullmatch("[0-9a-f]{64}", value):
            raise ProbeError("Invalid SHA-256: " + name)
    builds = data.get("builds")
    if not isinstance(builds, list) or len(builds) != len(BUILD_ROSTER):
        raise ProbeError("Expected all four compiler/optimization builds")
    seen = set()
    for build in builds:
        if not isinstance(build, dict) or build.get("name") not in BUILD_ROSTER or build["name"] in seen:
            raise ProbeError("Invalid or duplicate build")
        seen.add(build["name"])
        if (build.get("compiler_version"), build.get("optimization")) != BUILD_ROSTER[build["name"]]:
            raise ProbeError("Incorrect compiler/optimization contract")
        for key, prefix in (("path", "probe-"), ("exec_path", "exec-")):
            wanted = "bin/" + prefix + build["name"]
            if build.get(key) != wanted or wanted not in files:
                raise ProbeError("Executable is not the reviewed payload path")
            if not os.access(payload_path(root, wanted), os.X_OK):
                raise ProbeError("Execute permission missing: " + wanted)
    cases = data.get("cases")
    if not isinstance(cases, list) or len(cases) != len(CASE_ROSTER):
        raise ProbeError("Expected all eight independent cases")
    seen = set()
    for case in cases:
        if not isinstance(case, dict) or case.get("id") not in CASE_ROSTER or case["id"] in seen:
            raise ProbeError("Invalid or duplicate case")
        seen.add(case["id"])
        actual = (case.get("exit_code"), case.get("stdout"), case.get("stderr"))
        if type(case.get("exit_code")) is not int or actual != CASE_ROSTER[case["id"]]:
            raise ProbeError("Incorrect native case contract")
    return data


def verify_payload(root, manifest, manifest_digest):
    if digest(payload_path(root, "manifest.json")) != manifest_digest:
        raise ProbeError("Manifest changed during execution")
    observed = {name: digest(payload_path(root, name)) for name in manifest["files"]}
    if observed != manifest["files"]:
        changed = sorted(name for name in observed if observed[name] != manifest["files"][name])
        raise ProbeError("Payload hash mismatch: " + ", ".join(changed))
    return observed


def safe_output(path, root):
    path = path.expanduser().resolve()
    if within(path, root) or within(root, path):
        raise ProbeError("Results must be outside the probe bundle")
    if any((parent / ".git").exists() for parent in (path,) + tuple(path.parents)):
        raise ProbeError("Results must be outside source repositories")
    return path


def create_output(requested, root):
    if requested:
        path = safe_output(Path(requested), root)
        path.mkdir(parents=True, exist_ok=False, mode=0o700)
        return path
    path = Path(tempfile.mkdtemp(prefix="native-kernel-monterey-results-")).resolve()
    try:
        return safe_output(path, root)
    except ProbeError:
        path.rmdir()  # Only the empty directory just created by this call.
        raise


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
                        raise ProbeError("Cannot confirm exited unreaped child after kqueue registration race")
                    self.already_exited = True
                except BaseException:
                    self.queue.close()
                    raise
            except BaseException:
                self.queue.close()
                raise
        elif not (hasattr(os, "waitid") and hasattr(os, "WNOWAIT")):
            raise ProbeError("Host cannot observe child exit without reaping")

    def exited(self):
        if self.already_exited:
            return True
        if self.queue is not None:
            self.already_exited = self.validate_events(self.queue.control(None, 1, 0))
            return self.already_exited
        result = os.waitid(os.P_PID, self.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        return result is not None

    def validate_events(self, events):
        for event in events:
            if event.flags & select.KQ_EV_ERROR:
                if event.data == errno.ESRCH:
                    raise ProcessLookupError(errno.ESRCH, "Child exited before registration")
                raise OSError(event.data, "Child exit observation failed")
            if event.ident != self.pid or event.filter != select.KQ_FILTER_PROC or not event.fflags & select.KQ_NOTE_EXIT:
                raise ProbeError("Unexpected child exit observation")
        return bool(events)

    def close(self):
        if self.queue is not None:
            self.queue.close()


def cleanup_group(process, observer=None):
    try:
        os.killpg(process.pid, signal.SIGKILL)
        return "signal-sent"
    except ProcessLookupError:
        return "already-absent"
    except PermissionError as error:
        # Darwin can return EPERM when only the reserved zombie remains.
        # Accept that only after unreaped exit observation has confirmed it.
        try:
            if observer is not None and observer.exited():
                return "exited-zombie"
        except (OSError, ValueError):
            pass
        return "failed: " + str(error)
    except OSError as error:
        return "failed: " + str(error)


def run_bounded(command, cwd, timeout=CASE_TIMEOUT, limit=OUTPUT_LIMIT):
    """Bound capture bytes and inherited pipe lifetime; clean the owned process group."""
    started = time.monotonic()
    result = {"command": [str(p) for p in command], "status": "incomplete", "exit_code": None,
              "stdout": "", "stderr": "", "output_truncated": False, "timed_out": False,
              "completion_observed": False, "started": False, "cleanup": "not-started"}
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    process, killed = None, False
    observer = None
    selector = selectors.DefaultSelector()
    try:
        environment = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "C", "LC_ALL": "C"}
        process = subprocess.Popen(command, cwd=str(cwd), env=environment, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        result["started"] = True
        observer = ExitObserver(process.pid)
        for name in buffers:
            pipe = getattr(process, name)
            os.set_blocking(pipe.fileno(), False)
            selector.register(pipe, selectors.EVENT_READ, name)
        deadline = started + timeout
        while selector.get_map():
            now = time.monotonic()
            if not killed and observer.exited():
                result["cleanup"] = cleanup_group(process, observer)
                killed = True
                deadline = min(deadline, now + 1.0)
            if now >= deadline:
                result["timed_out"] = True
                break
            for key, _ in selector.select(min(0.05, deadline - now)):
                try:
                    block = os.read(key.fileobj.fileno(), 8192)
                except BlockingIOError:
                    continue
                if not block:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                remaining = limit - len(buffers[key.data])
                buffers[key.data].extend(block[:remaining])
                if len(block) > remaining:
                    result["output_truncated"] = True
                    break
            if result["output_truncated"]:
                break
        # EOF can precede worker exit. Observe without reaping so its PID and
        # process-group number stay reserved until the group cleanup below.
        while not killed and not result["timed_out"] and not result["output_truncated"]:
            if observer.exited():
                result["cleanup"] = cleanup_group(process, observer)
                killed = True
                break
            if time.monotonic() >= deadline:
                result["timed_out"] = True
                break
            time.sleep(0.01)
    except (OSError, ValueError) as error:
        result["error"] = str(error)
    finally:
        if process is not None:
            if not killed:
                result["cleanup"] = cleanup_group(process, observer)
            try:
                process.wait(timeout=1.0)
                result["completion_observed"] = True
            except subprocess.TimeoutExpired:
                result["cleanup"] += "; leader-not-collected"
            result["exit_code"] = process.returncode
        if observer is not None:
            observer.close()
        for key in list(selector.get_map().values()):
            selector.unregister(key.fileobj)
            key.fileobj.close()
        if process is not None:
            for name in buffers:
                stream = getattr(process, name)
                if stream is not None and not stream.closed:
                    stream.close()
        selector.close()
        result["duration_seconds"] = round(time.monotonic() - started, 4)
        for name, value in buffers.items():
            rendered = bytes(value).decode("utf-8", errors="replace").encode("utf-8")
            if len(rendered) > limit:
                result["output_truncated"] = True
            result[name] = rendered[:limit].decode("utf-8", errors="ignore")
    if result.get("error") or result["cleanup"].startswith("failed") or not result["completion_observed"]:
        result["status"] = "incomplete"
    elif result["output_truncated"]:
        result["status"] = "output_limit"
    elif result["timed_out"]:
        result["status"] = "timed_out"
    elif result["exit_code"] is not None and result["exit_code"] < 0:
        result["status"] = "crashed"
    else:
        result["status"] = "completed"
    return result


def command_text(command, optional=False):
    try:
        result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        if optional:
            return {"value": None, "error": str(error)}
        raise ProbeError("Host identity command failed: " + str(error))
    if len(result.stdout) > OUTPUT_LIMIT or len(result.stderr) > OUTPUT_LIMIT:
        raise ProbeError("Host identity output exceeds its bound")
    value = result.stdout.decode("utf-8", errors="replace").strip()
    if result.returncode:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        if optional:
            return {"value": None, "exit_code": result.returncode, "error": error}
        raise ProbeError("Host identity command failed: " + error)
    return {"value": value}


def identify_host():
    commands = {"system": ["/usr/bin/uname", "-s"], "architecture": ["/usr/bin/uname", "-m"],
                "darwin_release": ["/usr/bin/uname", "-r"], "kernel": ["/usr/sbin/sysctl", "-n", "kern.version"],
                "os_version": ["/usr/bin/sw_vers", "-productVersion"], "os_build": ["/usr/bin/sw_vers", "-buildVersion"]}
    host = {name: command_text(command)["value"] for name, command in commands.items()}
    arm = command_text(["/usr/sbin/sysctl", "-n", "hw.optional.arm64"], optional=True)
    translated = command_text(["/usr/sbin/sysctl", "-n", "sysctl.proc_translated"], optional=True)
    host.update(hardware_arm64=arm["value"] == "1", translated=translated["value"] == "1",
                arm64_query=arm, translation_query=translated,
                developer_directory=command_text(["/usr/bin/xcode-select", "-p"], optional=True),
                sdk=command_text(["/usr/bin/xcrun", "--show-sdk-version"], optional=True), python=sys.version)
    return host


def require_host(host, preflight):
    if host.get("system") != "Darwin":
        raise ProbeError("The unmanaged probes require Darwin")
    if preflight:
        if host.get("architecture") not in ("x86_64", "arm64", "aarch64"):
            raise ProbeError("Preflight requires an Intel or Apple Silicon Mac")
        return
    if any(host.get(key) != value for key, value in EXPECTED_HOST.items()):
        raise ProbeError("Host does not match macOS 12.7.6 / 21H1320 / Darwin 21.6.0 / Intel")
    if host.get("hardware_arm64") or host.get("translated"):
        raise ProbeError("Target qualification requires native Intel execution")


def classify_case(result, expected):
    if result["status"] == "completed":
        result["status"] = "passed" if all(result[k] == expected[k] for k in ("exit_code", "stdout", "stderr")) else "wrong_result"
    return result


def write_receipt(output, receipt):
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def archive_results(output):
    destination = output.with_name(output.name + ".zip")
    with zipfile.ZipFile(str(destination), "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(output.rglob("*")):
            if path.is_file() and not path.is_symlink() and not within(path, output / "fixtures"):
                archive.write(str(path), str(Path(output.name) / path.relative_to(output)))
    return destination


def run_bundle(root, output, preflight=False):
    receipt = {"schema": SCHEMA, "mode": "preflight" if preflight else "monterey-intel", "status": "incomplete",
               "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "expected_host": EXPECTED_HOST,
               "scope": "selected Native-Kernel primitives; no Process-Control launch or checked-control qualification",
               "target_runtime_observed": False, "target_qualified": False,
               "cases": [], "stages": [], "source_unchanged": False}
    try:
        manifest = load_manifest(root)
        manifest_digest = digest(root / "manifest.json")
        receipt["manifest_sha256"] = manifest_digest
        receipt["sources_before"] = verify_payload(root, manifest, manifest_digest)
        receipt["stages"].append({"name": "payload-before", "status": "passed"})
        receipt["host"] = identify_host()
        require_host(receipt["host"], preflight)
        receipt["stages"].append({"name": "host", "status": "passed"})
        receipt["artifact_execution_translated"] = bool(receipt["host"]["hardware_arm64"] or receipt["host"]["translated"])
        receipt["builds"] = manifest["builds"]
        (output / "logs").mkdir()
        for build in manifest["builds"]:
            for expected in manifest["cases"]:
                verify_payload(root, manifest, manifest_digest)
                name = build["name"] + "-" + expected["id"]
                fixture = output / "fixtures" / name
                fixture.mkdir(parents=True)
                command = [str(payload_path(root, build["path"])), expected["id"], str(fixture / "fixture"),
                           str(payload_path(root, build["exec_path"]))]
                result = classify_case(run_bounded(command, fixture), expected)
                if not preflight and result.get("started"):
                    receipt["target_runtime_observed"] = True
                result.update(build=build["name"], case=expected["id"], expected=expected)
                for stream in ("stdout", "stderr"):
                    log = output / "logs" / (name + "." + stream)
                    log.write_text(result[stream], encoding="utf-8")
                    result[stream + "_log"] = str(log.relative_to(output))
                receipt["cases"].append(result)
                print(name + ": " + result["status"], flush=True)
                write_receipt(output, receipt)
        receipt["sources_after"] = verify_payload(root, manifest, manifest_digest)
        receipt["source_unchanged"] = receipt["sources_before"] == receipt["sources_after"]
        receipt["stages"].append({"name": "payload-after", "status": "passed"})
        passed = len(receipt["cases"]) == 32 and all(case["status"] == "passed" for case in receipt["cases"])
        receipt["status"] = ("preflight_passed" if preflight else "passed") if passed else ("preflight_failed" if preflight else "failed")
        receipt["target_qualified"] = passed and not preflight
    except (OSError, ValueError, KeyError, TypeError) as error:
        receipt["error"] = str(error)
        receipt["status"] = "preflight_failed" if preflight else "failed"
        receipt["stages"].append({"name": "runner", "status": "failed", "error": str(error)})
    receipt["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    write_receipt(output, receipt)
    return receipt


def main(argv=None, bundle_root=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="New external directory for receipts and bounded logs")
    parser.add_argument("--preflight", action="store_true", help="Test on another Mac; never qualifies Monterey")
    args = parser.parse_args(argv)
    root = (Path(bundle_root) if bundle_root else Path(__file__).parent).resolve()
    try:
        output = create_output(args.output, root)
    except (OSError, ValueError) as error:
        print("Cannot create results: " + str(error), file=sys.stderr)
        return 2
    receipt = run_bundle(root, output, args.preflight)
    try:
        archive = archive_results(output)
    except (OSError, ValueError) as error:
        receipt["status"] = "preflight_failed" if args.preflight else "failed"
        receipt["target_qualified"] = False
        receipt["error"] = "Cannot archive results: " + str(error)
        write_receipt(output, receipt)
        print(receipt["error"], file=sys.stderr)
        return 1
    print("Result: " + receipt["status"])
    print("Send this results ZIP: " + str(archive))
    return 0 if receipt["status"] in ("passed", "preflight_passed") else 1


if __name__ == "__main__":
    sys.exit(main())
