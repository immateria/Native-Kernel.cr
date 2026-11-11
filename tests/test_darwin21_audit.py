"""Portable source-layout gates for the Darwin 21 foundation audit."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Darwin21Audit(unittest.TestCase):
    def test_independent_native64_spawn_assertions_compile(self):
        compiler = shutil.which("cc")
        if compiler is None:
            self.skipTest("C compiler unavailable")
        result = subprocess.run(
            [compiler, "-m64", "-std=c11", "-Wall", "-Werror", "-fsyntax-only",
             str(ROOT / "scripts/compat/darwin21_spawn_layout.c")],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_audit_records_the_published_source_limit_and_handoff_gate(self):
        document = (ROOT / "docs/darwin-monterey-foundations.md").read_text(encoding="utf-8")
        self.assertIn("27b03b360a988dfd3dfdf34262bb0042026747cc", document)
        self.assertIn("xnu-8020.240.18.709.2", document)
        self.assertIn("not** asserted to be the\nshipping kernel", document)
        self.assertIn("blocked by the missing x86-64", document)
        self.assertIn("build_monterey_foundations.py", document)

    def test_private_profile_and_transport_remain_explicitly_separate(self):
        spawn = (ROOT / "src/native-kernel/darwin/spawn.cr").read_text(encoding="utf-8")
        mach = (ROOT / "src/native-kernel/darwin/mach.cr").read_text(encoding="utf-8")
        self.assertIn("when 21     then Profile.new(21, Layout::Darwin21)", spawn)
        self.assertIn("when Layout::Darwin21 then 152", spawn)
        self.assertIn("when Layout::Darwin21 then 128", spawn)
        self.assertIn("MachMsgTrap", mach)
        self.assertIn("Raw.call(-31", mach)
        self.assertIn("TRAP_RECEIVE_OPTIONS", mach)
        self.assertIn("retry_phase", mach)
        self.assertIn("decode_task_audit_reply", mach)

    def test_native_fixture_completion_markers_match_the_separate_runner(self):
        runner = (ROOT / "scripts/compat/monterey_foundations_runner.py").read_text(encoding="utf-8")
        spawn = (ROOT / "spec/native/monterey_spawn.cr").read_text(encoding="utf-8")
        task_token = (ROOT / "spec/native/monterey_task_token.cr").read_text(encoding="utf-8")
        self.assertIn('"NK_OK spawn\\n"', runner)
        self.assertIn('"NK_OK task-token\\n"', runner)
        self.assertIn('"NK_OK spawn\\n"', spawn)
        self.assertIn('"NK_OK task-token\\n"', task_token)
        self.assertIn("collect(pid, 0, false)", task_token)


if __name__ == "__main__":
    unittest.main()
