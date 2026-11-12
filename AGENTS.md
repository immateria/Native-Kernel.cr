# Working on Native-Kernel

This directory is an independent repository. The workspace root guide applies
when working in the Crystal-Shards workspace.
The compiler floor is Crystal 1.10.0. Keep this shard free of runtime shard
dependencies, compatibility aliases and Process-Control policy. The owner's
publication remote is https://github.com/immateria/Native-Kernel.cr.git.

Read [README.md](README.md) and [docs/support.md](docs/support.md) before changing
the ABI. `make check` checks formatting, runs specs and, on Darwin, builds and
runs the unmanaged native probe. Linux now dispatches to its separate ELF
runner; see docs/linux-process.md and docs/linux-validation.md before changing
that ABI or claiming native support. `make native RECEIPTS=/external/new-directory`
keeps source-bound receipts at a chosen location. Set `CRYSTAL` to the compiler
running each command and use a distinct external `CRYSTAL_CACHE_DIR` per run.
Scratch copies, receipts, object files and executables stay outside this tree.

`darwin/raw`, `darwin`, `linux/raw` and `linux` must work without Crystal managed
initialization, allocation, exceptions, runtime state or external function calls. Never require
`source` or `audit` from them. Those two managed build metadata entries remain
portable, including on platforms that refuse raw execution. Update the explicit
source list in `source.cr` whenever a shipped source is added or removed; its
coverage spec must still match every `src/**/*.cr` file.

Keep syscall result registers and BSD carry handling in one exact assembly
block. A BSD failure has primary -1 and positive `error`. Mach traps retain the
native result in primary and have error zero. Raw fork preserves the child
flag in secondary; only `Process.fork` changes child primary to zero.

The typed entry owns no descriptor, Mach right, context, cache or lifecycle.
Mach primitives accept the caller's explicit current-task name. They must not
consult Process-Control state. The task-info exchange owns its dedicated reply
receive right only for the exchange, releasing it on all native return paths.
Caller policy decides target identity, supported kernel releases, retries,
signal dispositions, collection and uncertain cleanup.

Before declaring an ABI change complete, run current and floor compiler specs
and unmanaged artifact verification on ARM64 and translated x86-64. The latter
checks reachable unoptimized and release LLVM using the exact assembly profile,
then requires an empty undefined-import table for each executable. Do not loosen
the auditor to mask a managed dependency. The auditor is an artifact check for
trusted compiler inputs, not a general LLVM validator or native OS proof.

For the runner suite, read [ci/README.md](ci/README.md). Keep the workflow's
public-repository guards, standard runner labels, exact compiler versions,
immutable action pins, read-only permission and three-day artifact retention.
Native cells and macOS-15-built forward replays are separate evidence. CI must
refuse translation; `--allow-translation` belongs only to local trials. An absent
or incomplete receipt cannot qualify a candidate profile. Keep setup/build
outputs external, preserve failure uploads and do not mask driver exit status.

Linux uses its own signed single-word result and exact per-architecture assembly
admission. Never union its templates with Darwin ASSEMBLY, change Darwin errno
normalization, use libc signal-set sizes for ppoll or omit raw waitid's fifth
rusage slot. Linux copyout faults may follow reaping. Keep caller ownership,
raw mutable timeouts and native resource units explicit. No managed launch,
signal-handler/restorer or consumer policy belongs in this layer. The Linux
runner's C oracles and cross-only output are not Crystal native proof; retain
blocked/unrun states and source-bound receipts rather than broad skips.
