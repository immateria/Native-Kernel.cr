#!/usr/bin/env bash
# Native bootstrap only. There is no official Linux ARM64 tarball in 1.10.0.
# Build the exact official tag from source with the installed 1.22.2 bootstrap.
set -euo pipefail
[[ $(uname -s) == Linux && $(uname -m) == aarch64 ]]
[[ $# == 1 ]]
base=$(realpath -m "$1")
root=$(git rev-parse --show-toplevel)
[[ "$base" != "$root" && "$base" != "$root/"* && ! -e "$base" ]]
mkdir -p "$base"
bootstrap=$(command -v crystal)
"$bootstrap" --version
"$bootstrap" --version | grep -E '^Crystal 1\.22\.2( |$)'
"$bootstrap" --version | grep -E '^Default target: aarch64-.*linux-gnu$'
revision=9c011d77d660a5a7441370dce9e101b3ca094d8b
source="$base/source"
git init "$source"
git -C "$source" remote add origin https://github.com/crystal-lang/crystal.git
git -C "$source" fetch --depth=1 origin "$revision"
git -C "$source" checkout --detach "$revision"
[[ $(git -C "$source" rev-parse HEAD) == "$revision" ]]
export CRYSTAL_CACHE_DIR="$base/cache"
# The tagged source's bin/crystal explicitly selects its own stdlib; make uses
# the native bootstrap only as the compiler, never a translated x86 binary.
env -u CRYSTAL_PATH make -C "$source" crystal release=1 CRYSTAL="$bootstrap" LLVM_CONFIG=/usr/bin/llvm-config-15
make -C "$source" install PREFIX="$base/install" CRYSTAL="$bootstrap" LLVM_CONFIG=/usr/bin/llvm-config-15
"$base/install/bin/crystal" --version
"$base/install/bin/crystal" --version | grep -E '^Crystal 1\.10\.0( |$)'
"$base/install/bin/crystal" --version | grep -E '^Default target: aarch64-.*linux-gnu$'
python3 - "$base" "$bootstrap" "$revision" <<'PY'
import hashlib,json,pathlib,subprocess,sys
base,bootstrap,revision=pathlib.Path(sys.argv[1]),pathlib.Path(sys.argv[2]),sys.argv[3]
hashfile=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt={"mode":"native-source-bootstrap", "source_repository":"crystal-lang/crystal", "source_commit":revision,
         "bootstrap_binary":str(bootstrap),"bootstrap_sha256":hashfile(bootstrap),
         "compiler_sha256":hashfile(base/"install/bin/crystal"),
         "compiler_description":subprocess.check_output([str(base/"install/bin/crystal"),"--version"],text=True),
         "source_inputs":{str(p.relative_to(base/"source")):hashfile(p) for p in (base/"source/src").rglob("*.cr")}}
(base/"bootstrap.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
PY
printf '%s\n' "$base/install/bin" >> "${GITHUB_PATH:?}"
printf 'CRYSTAL_PATH=%s\n' "$base/install/share/crystal/src" >> "${GITHUB_ENV:?}"
