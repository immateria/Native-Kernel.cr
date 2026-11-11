# macOS runner qualification

Prepared on 2026-11-10. The profiles in [profiles.json](profiles.json) are
candidates. Preparing the workflow, a skipped job, a cross-compile or a Rosetta
run does not qualify a native runner. Hosted macOS 26 and native Intel results
have not been collected in this preparation pass.

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
The workflow requires no secret or local path configuration. Inspect the first
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
version and native architecture. Setup checks `crystal --version`, its default
target and the selected OpenSSL major before qualification.

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
files and compiler caches stay in external scratch space. Artifacts use unique profile/compiler names, maximum compression and
three-day retention. A failed originating job can still upload diagnostics;
its export cannot qualify forward execution.

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

This suite concerns Native-Kernel primitives. It does not admit macOS 26 in
Process-Control or qualify that consumer's private spawn ABI, process identity,
ownership policy or cleanup integrations. See [the support boundaries](../docs/support.md).
