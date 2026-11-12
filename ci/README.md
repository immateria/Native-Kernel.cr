# macOS runner qualification

Prepared on 2026-11-10; qualification updated on 2026-11-11. Run `42979523044`
at source `0db4c8b` passed all eight native cells and four forward replays. See
[the dated results](../docs/ci-results.md) for exact hosts, compilers, evidence
and limits. The profiles in [profiles.json](profiles.json) define the matrix;
qualification comes from each run's complete receipts. Preparing a workflow,
a skipped job, a cross-compile or a Rosetta run does not qualify a native runner.

The workflow has eight native cells: Crystal 1.10.0 and 1.22.2 on each of
`macos-15`, `macos-15-intel`, `macos-26` and `macos-26-intel`. Each cell checks
the actual OS release, Darwin major, CPU architecture and translation state;
the runner label alone is insufficient. Four additional jobs download only
the macOS 15 export for the same architecture and compiler, then execute its
already audited native binaries on macOS 26. Forward jobs do not install a
compiler or rebuild the fixtures. A build made on macOS 26 is a separate native
cell, not evidence of forward compatibility.

Both jobs have a public-repository guard before runner allocation. A private
repository or missing visibility skips every job and establishes no
qualification. Only standard GitHub-hosted runner labels are used; there are
no larger runners, schedules, release uploads, persistent caches or privileged
tokens. GitHub documents
[standard hosted runners and their labels](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
and [free standard runner use for public repositories](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
Recheck labels and billing before the owner enables this workflow in a new
repository. macOS 14 is not a substitute: its runner image was retired on
2026-11-02.

`push`, `pull_request` and manual dispatch are enabled. The owner authorized
publication to [immateria/Native-Kernel.cr](https://github.com/immateria/Native-Kernel.cr)
on 2026-11-10. The repository was confirmed public before the initial push.
The workflow requires no secret or local path configuration. Inspect each
run's 12 receipts before recording hosted qualification. A manual dispatch
requires the workflow on the default branch. Preparing or publishing this
workflow does not establish a hosted runtime result.

Every action is pinned to an immutable commit. The pins were resolved from
the upstream GitHub API on 2026-11-10: checkout v4
`11d5960a326750d5838078e36cf38b85af677262`, install-crystal v1
`36a22e9145188eec527c96e5a789ce4b832af587`, upload-artifact v4
`ea165f8d65b6e75b540449e92b4886f43607fa02`, and download-artifact v4
`d3f86a106a0bac45b974a628896c90dbdf5c8093`. `contents: read` is the only
token permission, and checkout does not persist credentials.

The native job first installs Homebrew `openssl@3`, `libevent` and `pkg-config`
with automatic updates disabled. It requires `/opt/homebrew` on ARM64 or
`/usr/local` on Intel. `PKG_CONFIG_LIBDIR` replaces the image's default search
paths, selecting OpenSSL 3 explicitly even on an image carrying OpenSSL 4.
The official `crystal-lang/install-crystal` action selects the exact matrix
version and native architecture. It can prepend a different Homebrew OpenSSL
directory to `PKG_CONFIG_PATH`. The verification step restores the selected
search path after installation and persists it through `GITHUB_ENV` for the
qualification step. Setup still requires OpenSSL 3, the exact compiler version
and the correct default target.

Native jobs have a 30-minute ceiling, forward jobs 15 minutes, and each matrix
runs at most four cells at a time. Matrix failures do not cancel other cells.
A newer run on the same ref cancels the older run. Cancellation or runner loss
can prevent cleanup steps; absent evidence is incomplete, never a pass.

The driver records passed, failed, unsupported, crashed, timed-out and incomplete
outcomes, source/configuration/executable hashes, actual host and compiler
identity, bounded outputs and completion evidence. Failed setup or a skipped
driver triggers an explicit incomplete receipt. The upload step runs after
failure and keeps only `OUTPUT/export`: receipts, bounded logs and audited
executables and compressed LLVM IR, including IR from failed audits. Object
files and compiler caches stay in external scratch space. Artifacts use unique
profile/compiler names, maximum compression and three-day retention. A failed
originating job can still upload diagnostics; its export cannot qualify forward
execution.

Compiler receipts retain the invocation or launcher identity separately from
the actual Mach-O compiler binary. The driver recognizes the reviewed official
launcher and its embedded compiler, or a direct Mach-O invocation. An unknown
wrapper requires `--compiler-binary PATH`; that path is the operator's explicit
assertion about the wrapper. Version and architecture checks still apply. These
hashes identify the selected compiler files, not every stdlib, SDK or linker input.

For local qualification, use an existing compiler and a new external output
directory. This does not run the Homebrew setup script:

```sh
python3 scripts/ci/runner.py qualify --compiler crystal \
  --profile macos-15-arm64 --output /external/new-native-result
python3 scripts/ci/runner.py replay --input /external/native15-result/export \
  --profile macos-26-arm64 --output /external/new-forward-result
python3 -m unittest discover -s tests -v
```

Use the profile matching the actual host. `--allow-translation` is an explicit
local-only option for a Rosetta x86-64 trial on Apple Silicon; select an x86-64
compiler invocation for that trial. CI never supplies this flag. Such a receipt
records translation and cannot substitute for the native Intel matrix cells.
For a custom Rosetta wrapper, also pass `--compiler-binary` with the underlying
compiler's Mach-O path, such as `INSTALL/embedded/bin/crystal` for the official
package. The wrapper file alone does not identify the compiler binary.

This suite concerns Native-Kernel primitives. Process-Control's launch,
identity, ownership and cleanup qualification comes from its separate consumer
run, recorded in [the dated results](../docs/ci-results.md#separate-consumer-qualification).
Native-Kernel receipts alone do not change a consumer's release admission.
See [the support boundaries](../docs/support.md).

The separate Darwin 21 private-spawn and task-token handoff is intentionally
outside this runner matrix and outside the existing eight-case Monterey
primitive bundle. On a native Intel Darwin build host, build its two
manifest-bound bundles with `scripts/compat/build_monterey_foundations.py`, then
run each bundle with `monterey_foundations_runner.py` on the exact Mini. The
[Monterey foundations audit](../docs/darwin-monterey-foundations.md) gives the
exact commands, source limitation and receipt gates. Neither a bundle build nor
a preflight execution qualifies Process-Control.

The collection/inspection batch adds two source-bound behavior cases, bringing
the required roster to twelve. `collection` exercises wait4, waitid and
getrusage with exclusive owned-child collection, observation and copyout-fault
checks. `inspection` exercises typed BSD/task records, both extended-ID
comparisons, usage versions 0/1/2 and parent/group list filters. These cases
require Darwin 24 in this suite. The coverage manifest maps 45 typed operation
names to positive cases; overloads and record versions are exercised within
their named case. The [ABI notes](../docs/darwin-accounting.md) describe native
units, output-validity and attribution limits. The earlier ten-case hosted
run does not qualify these additions.

The collection fixture also retains a successful write result across a close
trap before checking it. Its optimized x86-64 build exposed the former `cc`
clobber's failure to invalidate LLVM's flags register. The entry and exact audit
profile now name `flags`; the native case remains a regression for that failure.


# Separate Linux mechanisms path

The new [Linux workflow](../.github/workflows/linux.yml) does not modify the
macOS native/forward jobs. It has four native cells: exact Crystal 1.10.0 and
1.22.2 on standard public `ubuntu-24.04` x86-64 and `ubuntu-24.04-arm` AArch64.
All cells are **unrun here**, including the native ARM64 floor bootstrap.
No runner label, C oracle or cross build qualifies a native Crystal cell.
The [dated local blocks](../docs/linux-validation.md) and [ABI contracts](
../docs/linux-process.md) are part of the review boundary.

Actions reuse the immutable checkout/install/upload pins above, `contents: read`,
no persisted credentials, a public-repository guard, fail-fast false, no
translation/emulation and three-day retention. Native jobs have a 35-minute
ceiling. Build/cache/bootstrap paths are external. Failure uploads retain the
receipt, bounded logs, compressed LLVM and audited executables (not caches or
reference trees). Interrupted setup gets an explicit incomplete receipt.

Linux 1.10.0's official release has no ARM64 tarball. That cell installs the
native official 1.22.2 bootstrap, then builds/installs official source commit
`9c011d77d660a5a7441370dce9e101b3ca094d8b` with LLVM 14 outside the checkout.
The bootstrap script retains compiler/source hashes. It must actually produce
and run native 1.10.0 before the driver will accept the cell. A bootstrap error
is a failed/incomplete cell, not a substituted compiler or successful skip.
The 1.10.0 assembly printer emits escaped quoted local symbols rejected by
both GNU `as` and LLVM MC. Floor artifacts are therefore lowered directly from
the same audited, unmodified LLVM IR through matching LLVM 14 `llc`, which
writes an ELF object with per-function/data sections. Its version and binary
hash are recorded and rechecked. LLVM 14 is explicitly run with
`-opaque-pointers`, which this compiler's IR requires. The 1.22.2 path keeps the
system C driver's assembler and layout-only section insertion. The floor path
leaves emitted assembly, symbols, and LLVM IR unmodified and does not feed the
assembly to an assembler. The source-hashed startup object supplies a small
freestanding `memset` for backend-generated byte-fill libcalls; the startup-only
C oracle forces and checks its byte, return-pointer, and zero-length behavior.
Final executables still must have no undefined symbols.

For unmanaged 1.10.0 builds, the driver derives an external build-local prelude
from the first `prelude.cr` selected by that exact compiler's `CRYSTAL_PATH`.
It removes only the single standalone `require "crystal/main"` line: 1.10.0's
ordinary prelude defines managed C `main` even with `-Dwithout_main`. The
selected `crystal/main.cr` also supplies `Crystal.ignore_stdio_errors`, which
`kernel.cr` references. A second external adapter therefore defines only that
exact helper first, then requires the main-free prelude; it does not copy or
define managed `Crystal.main` or C `main`. Crystal resolves `--prelude` as a
require from the primary source file, so the driver passes a path relative to
the fixture source directory (not an assumed working or repository root).
Missing, duplicate or malformed main references or helper definitions fail
closed. The receipt binds and rechecks the selected prelude/main sources, their
hashes, the removed bytes/offset, extracted helper, both generated files and
each exact transformation before compilation and at exit. No stdlib is
vendored, no fixture entry ABI changes, and current compilers keep
`-Dwithout_main` without any prelude rewrite. LLVM audit, static no-import
linking and native execution remain mandatory on both releases.

Overflow-intrinsic admission is anchored to complete scalar symbols: `uadd`,
`usub`, `umul` and `smul` accept only i8/i16/i32/i64/i128; `sadd` and `ssub`
also accept the floor compiler's mixed-signedness i9/i17/i33/i65/i129
widenings. The widths are reviewed against both pinned `codegen/primitives.cr`
inputs. Suffixes, other widths, vectors and unrelated LLVM/runtime symbols are
rejected by executable regressions; no family-prefix admission remains.

`export/receipt-review.json` is a bounded view of the actual full receipt, bound
by its SHA-256. It retains all stage, artifact and runtime-case records needed for
roster/input checks; large source/function manifests are represented by counts
and canonical-JSON hashes, not truncated. CI also emits the complete view as
numbered, SHA-bound gzip/base64 Checks notices (at most ten, each below 4 KiB,
all below the unchanged 64-KiB capture bound) so it can be reconstructed and
inspected without downloading the artifact archive. The full receipt/manifests
remain in the unchanged three-day evidence upload. This
view adds no pass or qualification decision and never substitutes for native
execution. Missing, failed or incomplete evidence remains exactly that.

Local execution:

```sh
python3 scripts/ci/linux_runner.py --compiler /tools/crystal/bin/crystal   --expected-compiler 1.22.2 --architecture x86_64 --output /external/new-linux
# Explicit cross-only builds need a matching cross C assembler/linker:
python3 scripts/ci/linux_runner.py --compiler /tools/crystal/bin/crystal   --cross-target aarch64 --cc 'aarch64-linux-gnu-gcc' --output /external/new-cross
```

Both raw modes gate the typed fixtures. Ten typed cases plus the raw case run
in both modes; every public method is mapped in `ci/linux.json`. Static ELF
entry/import/dependency checks, independent installed-UAPI C assertions,
negative LLVM fixtures, unsupported direct requires, exact output markers and
source hashes before/after are mandatory. A separate Linux-spec example-count
gate prevents portable-only spec success. After auditing unmodified LLVM, the
runner requires one ELF text section per emitted function for O0 garbage
collection. The 1.22.2 path inserts only section/alignment directives into the
emitted assembly and preserves every original line; the 1.10.0 floor path avoids
its malformed escaped-symbol assembly printer and lowers the same audited IR
directly with hash-checked LLVM 14 `llc -function-sections -data-sections`.
That tool's binary/version, optimization level, exact command and one-function
ELF symbol/section roster are recorded and rechecked. Neither path removes
reachable IR or grants extra imports/assembly admission. Raw clone/exec occurs only in
unmanaged disposable fixtures. Exclusive child cleanup and driver subreaper
containment are bounded; any adopted child fails the case. `mechanisms-passed`
still leaves `qualification: incomplete`: genuinely delivered EINTR, consumer
migration/lifecycle, foreign credentials and PID reuse are not established.
Synthetic EINTR decoding is labeled separately, never promoted to native
interruption qualification. See the receipts, not the existence of this config.
