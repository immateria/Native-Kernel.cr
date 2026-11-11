"""Exercise the workflow's dependency environment without installing packages."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]


def verification_script(profile, compiler):
    # Read only this known scalar/block shape; no YAML dependency is needed.
    workflow = (ROOT / ".github/workflows/macos.yml").read_text()
    step = workflow.split("      - name: Verify compiler and native architecture\n", 1)[1]
    run = step.split("      - ", 1)[0].split("        run: ", 1)[1]
    script = textwrap.dedent(run[2:]) if run.startswith("|\n") else run.splitlines()[0]
    return script.replace("${{ matrix.profile }}", profile).replace("${{ matrix.compiler }}", compiler)


@unittest.skipUnless(shutil.which("bash") and shutil.which("pkg-config"),
                     "setup contract needs bash and pkg-config, but installs no packages")
class SetupContractTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="nk-ci-setup-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.bin = self.directory / "bin"
        self.bin.mkdir()
        scripts = {
            "uname": 'case "$1" in -s) echo Darwin;; -m) echo "$TEST_ARCH";; *) exit 1;; esac',
            "sysctl": '[[ "$*" == "-in sysctl.proc_translated" ]] && echo 0',
            "brew": '''case "$*" in
              --prefix) echo "$TEST_BREW_ROOT";;
              "--prefix openssl@3") echo "$TEST_OPENSSL_PREFIX";;
              "--prefix libevent") echo "$TEST_LIBEVENT_PREFIX";;
              "install openssl@3 libevent pkg-config") :;;
              *) exit 1;;
            esac''',
            "crystal": '''[[ "$*" == --version ]] || exit 1
            printf 'Crystal %s [fixture]\nLLVM: 15.0.7\nDefault target: %s-apple-darwin\n' \
              "$TEST_COMPILER" "$TEST_TARGET"''',
        }
        for name, body in scripts.items():
            path = self.bin / name
            path.write_text("#!/bin/bash\nset -eu\n" + textwrap.dedent(body) + "\n")
            path.chmod(0o755)
        self.env_file = self.directory / "github-env"
        self.base_env = {key: value for key, value in os.environ.items()
                         if not key.startswith("PKG_CONFIG_")}
        self.base_env.update(PATH=f"{self.bin}:{os.environ['PATH']}",
                             GITHUB_ENV=str(self.env_file), RUNNER_TEMP=str(self.directory))

    def package(self, prefix, name, version):
        directory = prefix / "lib/pkgconfig"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{name}.pc").write_text(
            f"Name: {name}\nDescription: CI fixture\nVersion: {version}\nLibs:\nCflags:\n")
        return directory

    def shell(self, script, env):
        return subprocess.run(["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", script],
                              cwd=ROOT, env=env, text=True, capture_output=True)

    def exported_env(self, env):
        exported = dict(env)
        for line in self.env_file.read_text().splitlines():
            key, value = line.split("=", 1)
            exported[key] = value
        return exported

    def test_workflow_restores_openssl3_after_installer_and_for_next_step(self):
        for arch, target, brew_root in (("arm64", "aarch64", "/opt/homebrew"),
                                        ("x86_64", "x86_64", "/usr/local")):
            openssl = self.directory / brew_root.lstrip("/") / "opt/openssl@3"
            libevent = self.directory / brew_root.lstrip("/") / "opt/libevent"
            self.package(openssl, "openssl", "3.5.9")
            self.package(libevent, "libevent", "2.1.13-stable")
            for compiler in ("1.10.0", "1.22.2"):
                for foreign_version in ("1.1.1w", "4.0.0"):
                    with self.subTest(arch=arch, compiler=compiler, foreign=foreign_version):
                        env = dict(self.base_env, TEST_ARCH=arch, TEST_TARGET=target,
                                   TEST_BREW_ROOT=brew_root, TEST_COMPILER=compiler,
                                   TEST_OPENSSL_PREFIX=str(openssl), TEST_LIBEVENT_PREFIX=str(libevent))
                        profile = f"macos-15-{arch}"
                        self.env_file.write_text("")
                        setup = self.shell(f"bash scripts/ci/setup.sh dependencies '{profile}'", env)
                        self.assertEqual(setup.returncode, 0, setup.stdout + setup.stderr)
                        selected = self.exported_env(env)
                        foreign = self.package(self.directory / f"foreign-{foreign_version}",
                                               "openssl", foreign_version)
                        # The pinned install action prepends and persists this path.
                        with self.env_file.open("a") as stream:
                            stream.write(f"PKG_CONFIG_PATH={foreign}:{selected['PKG_CONFIG_PATH']}\n")
                        contaminated = self.exported_env(env)
                        query = self.shell("pkg-config --modversion openssl", contaminated)
                        self.assertEqual(query.stdout.strip(), foreign_version)
                        rejected = self.shell(
                            f"bash scripts/ci/setup.sh verify '{profile}' '{compiler}'", contaminated)
                        self.assertNotEqual(rejected.returncode, 0, rejected.stdout + rejected.stderr)

                        verified = self.shell(verification_script(profile, compiler), contaminated)
                        self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
                        # A new Actions step starts from persisted exports, not this shell.
                        next_step = self.shell("pkg-config --modversion openssl", self.exported_env(env))
                        self.assertEqual(next_step.returncode, 0, next_step.stderr)
                        self.assertEqual(next_step.stdout.strip(), "3.5.9")

    def test_workflow_requires_nonempty_selected_dependency_path(self):
        selected = self.package(self.directory / "selected", "openssl", "3.5.9")
        for value in (None, ""):
            with self.subTest(libdir=value):
                env = dict(self.base_env, TEST_ARCH="arm64", TEST_TARGET="aarch64",
                           TEST_BREW_ROOT="/opt/homebrew", TEST_COMPILER="1.10.0",
                           PKG_CONFIG_PATH=str(selected))
                if value is not None:
                    env["PKG_CONFIG_LIBDIR"] = value
                self.env_file.write_text("")
                verified = self.shell(verification_script("macos-15-arm64", "1.10.0"), env)
                self.assertNotEqual(verified.returncode, 0, verified.stdout + verified.stderr)
                self.assertEqual(self.env_file.read_text(), "")


if __name__ == "__main__":
    unittest.main()
