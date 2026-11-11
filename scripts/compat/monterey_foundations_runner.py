#!/usr/bin/env python3
"""Run a shipped Darwin 21 spawn or task-token bundle without building it.

This deliberately uses the established Monterey runner's bounded executor,
host gate, inventory hashing and archive conventions. It is a separate profile:
the original eight BSD primitive cases remain unchanged.
"""
import argparse
import datetime
import importlib.util
import json
from pathlib import Path
import re
import sys

BASE_RUNNER_FILE = "monterey_runner.py"
BASE_RUNNER_PATH = Path(__file__).with_name(BASE_RUNNER_FILE)
BASE_SPEC = importlib.util.spec_from_file_location("native_kernel_monterey_runner", BASE_RUNNER_PATH)
if BASE_SPEC is None or BASE_SPEC.loader is None:
    raise RuntimeError("Cannot load the bundled Monterey runner")
base = importlib.util.module_from_spec(BASE_SPEC)
BASE_SPEC.loader.exec_module(base)

SCHEMA = 1
MAX_PAYLOAD_BYTES = 32 * 1024 * 1024
RUNNER_FILE = "monterey_foundations_runner.py"
CAMPAIGNS = {
    "spawn": {
        "cases": [
            {"id": "spawn-success", "exit_code": 0, "stdout": "NK_OK spawn-success\n", "stderr": ""},
            {"id": "spawn-null-arguments", "exit_code": 0, "stdout": "NK_OK spawn-null-arguments\n", "stderr": ""},
            {"id": "spawn-malformed-descriptor-size", "exit_code": 0, "stdout": "NK_OK spawn-malformed-descriptor-size\n", "stderr": ""},
            {"id": "spawn-malformed-action-size", "exit_code": 0, "stdout": "NK_OK spawn-malformed-action-size\n", "stderr": ""},
            {"id": "spawn-invalid-cwd", "exit_code": 0, "stdout": "NK_OK spawn-invalid-cwd\n", "stderr": ""},
            {"id": "spawn-missing-executable", "exit_code": 0, "stdout": "NK_OK spawn-missing-executable\n", "stderr": ""},
        ],
        "topology": "runner -> spawn probe -> one posix_spawn target when creation succeeds; probe exclusively collects confirmed targets",
    },
    "task-token": {
        "cases": [
            {"id": "task-token-exchange-growth", "exit_code": 0, "stdout": "NK_OK task-token-exchange-growth\n", "stderr": ""},
            {"id": "task-token-attribution", "exit_code": 0, "stdout": "NK_OK task-token-attribution\n", "stderr": ""},
            {"id": "task-token-gate-write-failure", "exit_code": 0, "stdout": "NK_OK task-token-gate-write-failure\n", "stderr": ""},
            {"id": "task-token-gate-close-failure", "exit_code": 0, "stdout": "NK_OK task-token-gate-close-failure\n", "stderr": ""},
        ],
        "topology": "runner -> task-token probe -> one gated fork child; probe exclusively collects each confirmed child",
    },
}


class ProbeError(ValueError):
    pass


def require_file(root, name):
    try:
        return base.payload_path(root, name)
    except base.ProbeError as error:
        raise ProbeError(str(error))


def load_manifest(root):
    path = require_file(root, "manifest.json")
    if path.stat().st_size > 1024 * 1024:
        raise ProbeError("Manifest exceeds the size bound")
    try:
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=base.unique_pairs)
    except (ValueError, TypeError) as error:
        raise ProbeError(str(error))
    if not isinstance(data, dict) or type(data.get("schema")) is not int or data["schema"] != SCHEMA:
        raise ProbeError("Unsupported manifest schema")
    kind = data.get("kind")
    if kind not in CAMPAIGNS:
        raise ProbeError("Unknown foundations campaign")
    if data.get("expected_host") != base.EXPECTED_HOST:
        raise ProbeError("Manifest must name the reviewed Monterey target")
    files = data.get("files")
    if not isinstance(files, dict) or not files or len(files) > 128:
        raise ProbeError("Manifest must declare the bounded payload inventory")
    if "manifest.json" in files or RUNNER_FILE not in files or BASE_RUNNER_FILE not in files:
        raise ProbeError("Inventory must include both runners and exclude the manifest")
    total = 0
    for name, value in files.items():
        payload = require_file(root, name)
        if not isinstance(value, str) or not re.fullmatch("[0-9a-f]{64}", value):
            raise ProbeError("Invalid SHA-256: " + name)
        total += payload.stat().st_size
        if total > MAX_PAYLOAD_BYTES:
            raise ProbeError("Bundle payload exceeds the 32 MiB bound")

    builds = data.get("builds")
    if not isinstance(builds, list) or len(builds) != len(base.BUILD_ROSTER):
        raise ProbeError("Expected all four compiler/optimization builds")
    seen = set()
    for build in builds:
        if not isinstance(build, dict) or build.get("name") not in base.BUILD_ROSTER or build["name"] in seen:
            raise ProbeError("Invalid or duplicate build")
        seen.add(build["name"])
        if (build.get("compiler_version"), build.get("optimization")) != base.BUILD_ROSTER[build["name"]]:
            raise ProbeError("Incorrect compiler/optimization contract")
        expected = "bin/" + kind + "-" + build["name"]
        if build.get("path") != expected or expected not in files:
            raise ProbeError("Probe is not the reviewed payload path")
        if not require_file(root, expected).stat().st_mode & 0o111:
            raise ProbeError("Execute permission missing: " + expected)
        if kind == "spawn":
            target = "bin/spawn-target-" + build["name"]
            if build.get("target_path") != target or target not in files:
                raise ProbeError("Spawn target is not the reviewed payload path")
            if not require_file(root, target).stat().st_mode & 0o111:
                raise ProbeError("Execute permission missing: " + target)
        elif "target_path" in build:
            raise ProbeError("Task-token build cannot name a target")

    cases = data.get("cases")
    expected_cases = CAMPAIGNS[kind]["cases"]
    if not isinstance(cases, list) or cases != expected_cases:
        raise ProbeError("Incorrect foundations case contract")
    return data


def verify_payload(root, manifest, manifest_digest):
    if base.digest(require_file(root, "manifest.json")) != manifest_digest:
        raise ProbeError("Manifest changed during execution")
    observed = {name: base.digest(require_file(root, name)) for name in manifest["files"]}
    if observed != manifest["files"]:
        changed = sorted(name for name in observed if observed[name] != manifest["files"][name])
        raise ProbeError("Payload hash mismatch: " + ", ".join(changed))
    return observed


def write_receipt(output, receipt):
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_bundle(root, output, preflight=False):
    receipt = {
        "schema": SCHEMA,
        "mode": "preflight" if preflight else "monterey-intel",
        "status": "incomplete",
        "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "expected_host": base.EXPECTED_HOST,
        "scope": "Darwin 21 private spawn or mach_msg_trap task-token primitive; no Process-Control qualification",
        "target_runtime_observed": False,
        "target_qualified": False,
        "cases": [],
        "stages": [],
        "source_unchanged": False,
    }
    try:
        manifest = load_manifest(root)
        kind = manifest["kind"]
        receipt["campaign"] = kind
        receipt["topology"] = CAMPAIGNS[kind]["topology"]
        manifest_digest = base.digest(require_file(root, "manifest.json"))
        receipt["manifest_sha256"] = manifest_digest
        receipt["sources_before"] = verify_payload(root, manifest, manifest_digest)
        receipt["stages"].append({"name": "payload-before", "status": "passed"})
        receipt["host"] = base.identify_host()
        base.require_host(receipt["host"], preflight)
        receipt["stages"].append({"name": "host", "status": "passed"})
        receipt["artifact_execution_translated"] = bool(receipt["host"]["hardware_arm64"] or receipt["host"]["translated"])
        receipt["builds"] = manifest["builds"]
        (output / "logs").mkdir()
        for build in manifest["builds"]:
            for expected in CAMPAIGNS[kind]["cases"]:
                verify_payload(root, manifest, manifest_digest)
                name = build["name"] + "-" + expected["id"]
                fixture = output / "fixtures" / name
                fixture.mkdir(parents=True)
                command = [str(require_file(root, build["path"]))]
                if kind == "spawn":
                    command.append(str(require_file(root, build["target_path"])))
                command.append(expected["id"])
                result = base.classify_case(base.run_bounded(command, fixture), expected)
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
        expected_case_count = len(base.BUILD_ROSTER) * len(CAMPAIGNS[kind]["cases"])
        passed = len(receipt["cases"]) == expected_case_count and all(case["status"] == "passed" for case in receipt["cases"])
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
    if not sys.flags.isolated:
        print("Run the shipped runner with /usr/bin/python3 -I to prevent bundle-local module shadowing", file=sys.stderr)
        return 2
    root = (Path(bundle_root) if bundle_root else Path(__file__).parent).resolve()
    try:
        output = base.create_output(args.output, root)
    except (OSError, ValueError) as error:
        print("Cannot create results: " + str(error), file=sys.stderr)
        return 2
    receipt = run_bundle(root, output, args.preflight)
    try:
        archive = base.archive_results(output)
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
