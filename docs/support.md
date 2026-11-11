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
stateless descriptor, event, resource, signal and process queries. Remaining
session/sigreturn bodies are instantiated and reachable in LLVM behind an
unselected fixture branch; that proves their generated dependency closure, not
successful sigreturn or session creation. Native specs count Mach names before
and after repeated successful and invalid-destination reads.

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

## Candidate hosted profiles

The [runner suite](../ci/README.md), prepared on 2026-11-10, names macOS 15 and
26 on native ARM64 and x86-64 with Crystal 1.10.0 and 1.22.2. These profile
records describe the candidate job matrix. The first hosted run passed all four
macOS 26 native cells at source `1312007`; exact hosts and evidence are recorded
in [the dated CI results](ci-results.md). Its macOS 15 setup failures leave the
forward jobs unqualified. Those jobs must execute macOS-15-built artifacts on
macOS 26 of the same architecture. Local Rosetta execution cannot establish
native Intel behavior; source inspection and cross-compilation cannot establish
either host's runtime behavior.

The additional fixtures exercise successful descriptor, directory, socket,
resource, session, exec, signal, audit-token, event and process operations in
disposable processes. Their receipts report each run's actual coverage and
failure state. Even a passing primitive suite does not qualify Process-Control's
private spawn ABI or change that consumer's supported-release admission.
