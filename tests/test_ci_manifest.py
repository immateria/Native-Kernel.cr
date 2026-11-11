import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ManifestTests(unittest.TestCase):
    def test_every_public_typed_operation_has_a_positive_case(self):
        inventory = json.loads((ROOT / "ci/coverage.json").read_text())
        cases = json.loads((ROOT / "ci/cases.json").read_text())["cases"]
        case_ids = {case["id"] for case in cases} | {"core"}
        self.assertEqual(len(cases), len(case_ids) - 1)
        found = set()
        for family in ("Descriptor", "Process", "Resource", "Signal", "Event", "Mach"):
            path = ROOT / "src/native-kernel/darwin" / (family.lower() + ".cr")
            methods = re.findall(r"^\s*def self\.([a-z_]+)\b", path.read_text(), re.M)
            found.update(f"{family}.{method}" for method in methods)
        self.assertEqual(found, set(inventory["operations"]))
        for operation, evidence in inventory["operations"].items():
            self.assertIn(evidence["positive_case"], case_ids, operation)

    def test_candidate_matrix_is_explicit_and_uses_standard_runners(self):
        manifest = json.loads((ROOT / "ci/profiles.json").read_text())
        self.assertEqual(manifest["compilers"], ["1.10.0", "1.22.2"])
        expected = {
            "macos-15-arm64": ("macos-15", 15, 24, "arm64"),
            "macos-15-x86_64": ("macos-15-intel", 15, 24, "x86_64"),
            "macos-26-arm64": ("macos-26", 26, 25, "arm64"),
            "macos-26-x86_64": ("macos-26-intel", 26, 25, "x86_64"),
        }
        self.assertEqual(set(manifest["profiles"]), set(expected))
        for name, wanted in expected.items():
            row = manifest["profiles"][name]
            self.assertEqual(tuple(row[key] for key in
                                   ("runner", "os_major", "darwin_major", "architecture")), wanted)
            self.assertEqual(row["state"], "candidate")
        self.assertEqual(manifest["consumer_spawn"], "not_qualified_by_this_suite")


if __name__ == "__main__":
    unittest.main()
