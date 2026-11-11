# Supported ABI profiles

Initial source extraction: 2026-11-10, Process-Control `85b0103`.

The raw and typed entries compile only on Darwin ARM64 and x86-64. Other raw
profiles refuse explicitly. `source` and `audit` are portable managed metadata;
they do not require the Darwin entries. There is no native Linux or Windows
backend in this shard.

The BSD syscall and Mach trap numbers, register conventions and ABI records
were inherited from the original Darwin implementation. The modern task-info
request uses mach_msg2, introduced in Darwin 22; the separately selected Darwin
21 profile uses the seven-argument mach_msg_trap transport for the same audited
TASK_AUDIT_TOKEN request. Its source profile is not a Monterey runtime claim.
`Process.release` queries the kernel major without caching it. Callers admit the
releases their application has qualified. These availability floors are
source-derived and do not certify all permitted operating-system versions.
The process records follow SDK sys/proc_info.h and XNU sys/proc_info_private.h;
the event record follows Darwin kevent64 on both supported architectures.
The [accounting and inspection ABI](darwin-accounting.md) records the three
official Darwin 24/25 source pins for wait4, waitid, getrusage, BSD/task
information and PID usage v0/v1/v2. Checked PIDINFO uses slot 545; PID usage is
PID-keyed and does not inherit that operation's identity comparisons.
`Spawn.profile` supplies separately restricted private native64 spawn layouts for
Darwin 21, 24 and 25. It returns nil for other majors; Darwin 21 does not reuse
the later 192-byte prefix. The [process notes](darwin-process.md) and the dated
[Monterey foundations audit](darwin-monterey-foundations.md) record source pins,
fixed-copy rules, build handoff and the consumer qualification boundary.

`Mach.read` validates message ID, declared size, NDR, success code and word count
before reading payload. It rejects complex replies. An interrupted send retries
the send; an interrupted receive retries only receive. Every native exchange
return attempts release of its dedicated receive right in the explicit caller
current task. The supplied current-task name must designate that caller. Invalid
names can prevent cleanup; the shard has no context owner to repair them. Modern
calls default to mach_msg2; `Mach.transport(21)` selects the audited
seven-argument mach_msg_trap route and must be passed before the first send.

`Signal.action` accepts the exact native action including trampoline and flags.
It does not install a target-reset policy or add flags. `Signal.restore` returns
the native sigreturn result if the kernel rejects restoration; callers decide
how to terminate an invalid trampoline. Resource limits use UInt64 native fields.
`Process.exit` repeats the raw exit trap and does not enter the managed runtime.

The unmanaged probe covers raw pipe dual returns, BSD errno, seventh/eighth
arguments, raw fork discriminator and typed fork normalization with child-owned
exit and parent collection, task acquisition/token exchange and cleanup, and
stateless descriptor, event, resource, signal and process queries. The original
probe instantiated session/sigreturn bodies behind an unselected fixture branch;
the later runner fixtures execute session creation and native sigreturn
separately. Native specs count Mach names before and after repeated successful
and invalid-destination reads.

Both unoptimized and release reachable LLVM must reject managed runtime symbols,
mutable globals, unapproved assembly, indirect calls and external functions.
Both linked probe executables must have empty `nm -u` output. Apple's linker
still supplies a libSystem loader entry; that is distinct from undefined imports.
The copied verifier follows direct references and callback/global references;
it is a bounded compiler-artifact checker, not a general LLVM validator.
Compiler, stdlib and linker inputs are trusted and must stay stable while built.

Runtime qualification records are kept outside the repository. ARM64 execution
and Rosetta x86-64 execution establish only those environments. Additional Darwin
releases, foreign credentials, raw threads and application ownership integrations
need their own qualification. Native Windows execution is outside this profile.


## Qualification on 2026-11-10

On macOS 15.4.1, Crystal 1.22.2 and 1.10.0 each pass 14 specs on ARM64 and
x86-64 under Rosetta. All four profiles also pass both unmanaged LLVM audits,
empty-import checks and actual probe execution. Independent review recomputed
source and artifact hashes, checked both architecture engines against the
extracted implementation and found no remaining source or quality blocker.

Process-Control's integration passes 118 specs per macOS profile and repeats
actual Darwin PID reuse and signal-interruption qualification on both compilers.
Its helper receipts include the 15 dependency source digests. These are consumer
qualification results, separate from the standalone probe's scope above.

## Hosted qualification on 2026-11-11

The [runner suite](../ci/README.md) passed all eight native cells and four
macOS-15-to-26 forward replays in run `42979523044` at source `0db4c8b`.
Each native profile ran Crystal 1.10.0 and 1.22.2: ARM64 on macOS 15.8.2 and
26.7.2, and Intel x86-64 on macOS 15.7.9 and 26.6.1. All execution was
untranslated; ARM64 runners used virtual machines. Each native cell passed
19 Crystal specs, 35 Python contracts and ten behavior cases in both development
and release modes, with positive coverage mapped to 41 typed operations.
The [dated CI results](ci-results.md) give exact OS builds, source identity,
reviewed evidence and the first run's historical failures.

The four forward jobs executed macOS-15-built artifacts on macOS 26 of the
same architecture, for both compilers, without rebuilding. These results apply
to the recorded artifacts and hosts, not every release in either OS major.
Local Rosetta execution cannot establish native Intel behavior; source
inspection and cross-compilation cannot establish either host's runtime behavior.

The additional fixtures exercise successful descriptor, directory, socket,
resource, session, exec, signal, audit-token, event and process operations in
disposable processes. Their receipts report each run's actual coverage and
failure state. Process-Control's authenticated startup and lifecycle were
checked by its separate eight-cell consumer run at `d4fcf3f`, using dependency
`0db4c8b`. Each cell passed 122 Crystal examples and 11 Python contracts. See
[the consumer evidence and limits](ci-results.md#separate-consumer-qualification);
the primitive suite alone does not establish these consumer results.

## Process additions on 2026-11-11

The typed process surface adds `setpgid`, `getpgid` and `getsid`. The existing
unmanaged session case now executes owned-child group creation/joining, inherited
session queries, independent session creation and native leader refusals. The
process case also spawns an audited exec fixture through `Spawn.create`, captures
its exact output through a caller-owned pipe and collects exit 37 through its
exclusive collector. Both optimization modes retain the strict LLVM and empty
import gates. The coverage manifest names these positive paths explicitly.

These additions are included in the hosted source and separate consumer run
recorded above. Further source or host changes need their own qualification.
Source compatibility, an older receipt or a standalone spawn result does not
establish consumer startup, abort, target status or cleanup behavior on a new
release.


## Accounting and inspection on 2026-11-11

The local collection/inspection batch passes all four profiles on macOS 15.4.1
(Darwin 24.4.0): ARM64 and translated x86-64, each with Crystal 1.22.2 and
1.10.0. Each profile passes 24 Crystal specs, 35 Python contracts and twelve
behavior cases in both development and release modes. Positive coverage maps
to 45 typed operation names. Both modes also pass the core unmanaged probe,
reachable LLVM audits and empty undefined-import checks.

The [ABI notes](darwin-accounting.md) record the new wait4, waitid, getrusage,
typed PIDINFO, PID usage v0/v1/v2 and filtered-list contracts. Review corrected
the x86-64 flags clobber after optimized execution exposed a stale comparison
across a trap. The corrected entry and exact audit metadata are included in
all four final profiles. The auditor's other restrictions remain unchanged.

External receipts are under
`macos-accounting-20261111/parent-final-nk-{arm64,x86}-{current,floor}` in the
workspace test cache. Each binds 57 source/build inputs, with source and artifact
hashes independently recomputed after qualification. The subsequent
[hosted run 43051842375](https://github.com/immateria/Native-Kernel.cr/actions/runs/43051842375)
at source `1e8b43a` passes all eight native macOS 15/26 cells and four forward
replays. The separate
[consumer run 43051959509](https://github.com/immateria/Process-Control.cr/actions/runs/43051959509)
at source `f46af66`, pinned to that dependency, passes all eight native cells
with 128 examples each. Those runs qualify their recorded source and artifacts.
Foreign-credential and protected-target execution remain unrun.

## Selected Monterey primitives on 2026-11-11

The owner's Intel Mac Mini passes all 32 executions of the separate Monterey
probe: eight cases for prebuilt Crystal 1.22.2 and 1.10.0 binaries, each in
development and release modes. The host is macOS 12.7.6, build 21H1320,
Darwin 21.6.0, xnu-8020.240.18.709.2, without translation. These binaries were
built with minimum deployment version 12.0, strict reachable LLVM audits and
empty imports before transfer; the target runner does not invoke a compiler.

The selected cases cover descriptors, limits, numeric group/session operations,
exec, native signals/return, kqueue exit observation, wait4/waitid/getrusage and
typed process inspection. Their scope excludes the full core/audit/spawn cases.
The Monterey entry omits the later-kernel wait4(INT_MIN) EINVAL assertion,
following a source comparison with published xnu-8020.140.41. The exact shipping
kernel source was unavailable. No complete raw-surface or Process-Control
Darwin 21 launch/checked-control qualification follows from this subset.

The returned manifest matches the retained 71-file payload before and after
execution. All four build rosters, 32 exact results and 64 logs verify against
the delivery and build records. External evidence lives under
`monterey-probe-20261111/returned-x033pcte/` and
`monterey-probe-20261111/returned-x033pcte-verification.json` in the workspace
test cache. The workspace's dated Monterey probe review records provenance,
loader evidence, the original ZIP's absence at return review and remaining gates.
