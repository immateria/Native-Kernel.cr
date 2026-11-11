# Supported ABI profiles

Initial source extraction: 2026-11-10, Process-Control `85b0103`.

The raw and typed entries compile only on Darwin ARM64 and x86-64. Other raw
profiles refuse explicitly. `source` and `audit` are portable managed metadata;
they do not require the Darwin entries. There is no native Linux or Windows
backend in this shard.

The BSD syscall and Mach trap numbers, register conventions and ABI records
were inherited from the original Darwin implementation. The task-info request
uses the mach_msg2 protocol introduced in Darwin 22; audit-token signaling uses
Darwin 24. `Process.release` queries the kernel major without caching it. Callers
admit the releases their application has qualified. These availability floors
are source-derived and do not certify all permitted operating-system versions.
The process records follow SDK sys/proc_info.h and XNU sys/proc_info_private.h;
the event record follows Darwin kevent64 on both supported architectures.
`Spawn.profile` supplies the restricted private native64 spawn layout for Darwin
24 and 25. It returns nil for other majors. The [process notes](darwin-process.md)
record the source pins, fixed-copy rules and consumer qualification boundary.

`Mach.read` validates message ID, declared size, NDR, success code and word count
before reading payload. It rejects complex replies. An interrupted send retries
the send; an interrupted receive retries only receive. Every native exchange
return attempts release of its dedicated receive right in the explicit caller
current task. The supplied current-task name must designate that caller. Invalid
names can prevent cleanup; the shard has no context owner to repair them.

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
