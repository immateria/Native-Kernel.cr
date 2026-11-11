# Darwin collection and process inspection

Source audit: 2026-11-11. This surface preserves the native64 ABI on Darwin
ARM64 and x86-64. It owns no child, process identity, buffer, retry policy or
release admission. All pointers and their complete writable storage belong to
the caller. BSD operations return `Result`: primary -1 plus positive errno on
failure. Output is usable only after the operation's success conditions below.

## Exact source inputs

The audit fetched each file separately from Apple's official XNU repository:

| Profile | Immutable revision |
| --- | --- |
| Darwin 24 | `e3723e1f17661b24996789d8afc084c0c3303b26` |
| Initial Darwin 25 | `f6217f891ac0bb64f3d375211650a4c1ff8ca1ea` |
| Published Darwin 25 update | `ac9718fb1af618d5ce8678d0dc6e8a58f252216f` |

These are source profiles, not identities for every shipping kernel of those
majors. The syscall-history ZIP's matching `syscalls.master` does not identify
its other uploaded files. This audit uses official per-file bytes throughout.
The external `macos-accounting-20261111/source-manifest.json` records revision,
path, byte count and SHA-256 for each retrieved input. Failed exploratory paths
are recorded as missing; they are not source evidence.

The [syscall table][syscalls] gives slots 7 (`wait4`), 117 (`getrusage`),
173 (`waitid`), 336 (`proc_info`) and 545 (`proc_info_extended_id`) with the
same selected signatures at all three pins. The [wait flags][wait],
[resource records][resource], [signal records][signal], [process records][proc]
and [private selectors][private] were compared at all three revisions.
The native64 rusage, siginfo, BSD/task and usage-v0/v1/v2 record definitions
are unchanged across those inputs, ignoring comments and whitespace.

The [collection and copyout bodies][exit], [resource implementation][resources]
and [process dispatch][inspection] establish the semantics below. The selected
wait, copyout, getrusage, PID usage, PID information and list functions have
equal normalized bodies across the pins. `calcru` changes from Mach task/thread
timevals in Darwin 24 to Recount conversion in Darwin 25. Task inspection and
usage gathering also change their ledger plumbing. No unchanged-implementation
claim applies to those functions. The exposed CPU units remain as listed below.

## Collection and accounting

| Operation | Native request | Successful result and valid output |
| --- | --- | --- |
| `Process.waitpid` | slot 7, null usage pointer | Positive child PID and native status; zero for no event |
| `Process.wait4` | slot 7, caller status and usage pointers | Positive child PID; status describes the event; usage is valid only for a terminal event |
| `Process.waitid` | slot 173, id type, UInt32 ID, siginfo pointer, options | Primary zero; nonzero `info.pid` after the caller clears it before the call indicates an event |
| `Resource.getrusage` | slot 117, `RUSAGE_SELF` (0) or `RUSAGE_CHILDREN` (-1) | Primary zero and a complete native usage record |

`waitpid` remains a useful status-only operation. `wait4` fills usage for a
successfully collected zombie; stopped and continued events leave it untouched.
`WNOHANG` with no event leaves both status and usage untouched. An error does
not guarantee untouched output: status copyout precedes usage copyout. A usage
copyout fault can return EFAULT after writing status, without reaping the child.
Do not treat that status as a successful collection. EINTR, ECHILD, EFAULT and
other native errors are preserved; callers choose retries and cleanup.
The terminal usage cache can be absent after a kernel allocation failure;
requesting it then returns ENOMEM and leaves collection pending. A caller that
needs status independently can choose a later status-only collection and
represent accounting as absent. The primitive does not substitute zero usage.

Terminal usage includes the target's own usage plus its already accumulated
child usage. The native exit path adds collected-descendant accounting before
the parent collects the target. `RUSAGE_CHILDREN` accumulates accounting already
collected by the current process, rather than querying all currently living
children. Times and additive counters accumulate; `max_rss` takes the maximum.
This is not a descendant-containment interface or a measurement of the helper
that performs collection.

`Resource::Time` is 16 bytes: signed Int64 seconds at 0, signed Int32
microseconds at 8 and four padding bytes. `Resource::Usage` is 144 bytes,
aligned to eight bytes on both architectures:

| Fields | Offset | Native meaning |
| --- | ---: | --- |
| `user`, `system` | 0, 16 | CPU seconds plus microseconds, each microsecond part in 0...1,000,000 |
| `max_rss` | 32 | Peak resident bytes in the audited kernels |
| `shared_memory`, `data_memory`, `stack_memory` | 40, 48, 56 | Native implementation-defined integral-memory counters |
| `reclaims`, `faults`, `swaps` | 64, 72, 80 | Native page reclaim, fault and swap counters |
| `input_blocks`, `output_blocks` | 88, 96 | Native block-operation counters; not bytes |
| `sent`, `received`, `signals` | 104, 112, 120 | Native message and signal counters |
| `voluntary_switches`, `involuntary_switches` | 128, 136 | Native context-switch counters |

All fourteen counters are signed Int64 native longs. Some are unused or
implementation-defined; zero does not establish that a kernel measured a
particular activity. The wrapper does not normalize them or relabel them as
portable metrics. The peak resident value comes directly from the Mach
`resident_size_max` byte count, rather than Linux's kilobyte convention.

`Process::Wait` defines `P_ALL=0`, `P_PID=1`, `P_PGID=2` and the native flags:
`WNOHANG=1`, `WUNTRACED=2`, `WEXITED=4`, `WSTOPPED=8`, `WCONTINUED=16`,
`WNOWAIT=32`. Use WUNTRACED with wait4 and WSTOPPED with waitid. The audited
waitid source rejects zero and options outside its mask. The wrappers leave
validation to the executing kernel: on the local Darwin 24.4.0 host, bit 0x40
alone returns ECHILD with no children, while zero, 0x80 and 0x40000000 return
EINVAL. That unexposed bit's semantics remain unresolved; source profiles do
not identify the executing kernel's complete behavior.

`WNOWAIT` leaves the event available for a later exclusive collector. It grants
no collection right. Native waitid leaves siginfo untouched on no event, so
clear `info.pid` before **every** call and inspect it only when error is zero.
Its `si_status` is an exit value or signal number, not wait4's encoded status.
The continued-event implementation returns saved `p_contproc` and `p_xstat`.
The [signal-delivery paths][delivery] determine their values: default SIGCONT
writes the target PID and SIGCONT; a synchronous signal wait writes the sender
PID; caught or held delivery can leave saved fields unchanged. Consequently a
continued event's PID need not identify the selected child, and its status can
retain a previous stop signal. Callers must preserve both fields and use
CLD_CONTINUED to identify the event. Early local probes returned a historical
PID and a previous stop signal under translated execution. Parent-side default
and mask changes did not settle the cause; those observations do not establish
a universal ARM64-versus-Rosetta distinction. The collection fixture configures
and reads back the child's own disposition and mask after fork, and waits for
its readiness acknowledgment before sending SIGSTOP.
Terminal observation also clears
the kernel's extra high exit-status bits even under WNOWAIT, so repeated
observation is not a promise to preserve every status extension.

`Signal::Info` preserves the 104-byte siginfo_t: six 32-bit fields through
status at offset 20, address at 24, the full eight-byte sigval union storage at
32, signed band at 40 and seven reserved UInt64 words at 48. `value` contains
the native union bits; an integer payload occupies its low 32 bits. The
`CLD_EXITED`, `CLD_KILLED`, `CLD_DUMPED`, `CLD_TRAPPED`, `CLD_STOPPED` and
`CLD_CONTINUED` constants retain native values 1 through 6.

## Live process inspection

`Process.info` keeps the generic PIDINFO entry and adds fixed-record overloads:

| Record | PIDINFO flavor | Size | Selected layout and units |
| --- | ---: | ---: | --- |
| `Process::Info::Bsd` | 3 | 136 | Existing BSD record; IDs, credentials, fixed name arrays and start seconds/microseconds |
| `Process::Info::Task` | 4 | 96 | Six UInt64 fields through offset 40; twelve signed Int32 fields from 48 through 92 |
| `Process::Info::All` | 2 | 232 | BSD at 0, task at 136 |

Success returns the actual number of copied bytes; require the expected size
before reading a record. Insufficient fixed-record capacity returns ENOMEM.
Invalid flavors return EINVAL. Absent targets return ESRCH; credential and MAC
checks can deny a present target. The wrapper preserves each native error.
Task virtual/resident sizes are bytes. Task total and existing-thread CPU
fields are Mach absolute-time ticks, as shown by [task filling][task] and
[Recount's timebase record][recount]; they are not nanoseconds or timevals.
Task counters retain native signed Int32 widths and kernel saturation behavior.

The overload with `flags` and `identity` uses slot 545 with **PIDINFO only**.
`PIF_COMPARE_IDVERSION=1` compares the located process's PID version;
`PIF_COMPARE_UNIQUEID=2` compares its unique ID. Both together return EINVAL;
a mismatch returns ESRCH before record copyout. Typed BSD/task/all overloads
also accept those arguments. The check and read concern the same located proc,
but produce no retained identity or future signaling authority.

`Process.usage` is a separate PIDRUSAGE operation (call 9 of slot 336), matching
the [libproc request][libproc]. It has pointer overloads for explicit versions
only; no current-version alias or caller-selected record length is supplied.
The kernel selects the copy length from the flavor and ignores buffersize.
Success returns zero, **not** the copied record size.

| Record | Flavor | Size | Version boundary |
| --- | ---: | ---: | --- |
| `Process::Usage::V0` | 0 | 96 | UUID then ten UInt64 fields; user time at 16, resident bytes at 64, start/exit at 80/88 |
| `Process::Usage::V1` | 1 | 144 | V0 prefix plus six collected-child fields at 96...143 |
| `Process::Usage::V2` | 2 | 160 | V1 prefix plus read/written byte counts at 144/152 |

CPU, process start/exit and child elapsed values retain Mach absolute-time
ticks. Memory and I/O fields are bytes; wakeups and pageins are counts. Live
process exit time is zero; zombie usage can come from cached terminal data.
The PID usage dispatcher receives neither comparison flags nor extended ID in
all three audited pins. This API therefore makes **no identity-checked usage
claim**, and exposes no misleading checked usage overload. Versions 3 through
6 and other process-info flavors remain future work.

`Process.list(type, filter, buffer, size)` adds native `PGRP_ONLY=2` and
`PPID_ONLY=6` filters alongside the existing all-PID call. The successful
primary value is bytes, not a PID count. A null buffer reports advisory
all-process capacity even for a filtered query. A full caller buffer can be
truncated as processes change; the caller must detect saturation and decide
whether to retry. Parent filtering also considers a traced process's original
parent. A list does not retain a process incarnation or freeze group membership.

## Verification boundary

The optimized translated fixture exposed a raw-entry defect during this batch.
With the old x86-64 `cc` clobber, LLVM 15 emitted a comparison before the inline
close trap and its conditional branch after the trap's flag-changing stack
adjustment. A successful child readiness write was then treated as failure.
Changing only that clobber to the x86 `flags` register made the same optimized
fixture report its intended exit 42 and complete collection. Both raw entry and
the exact assembly audit profile use the corrected name. The native fixture
keeps the write-result check across close to cover this regression.

LLVM inline assembly requires explicit register clobbers; its source IR is
not a GCC inline-assembly string passed through Clang's translation layer.
See [LLVM 15's clobber contract](https://releases.llvm.org/15.0.0/docs/LangRef.html#clobber-constraints).

The layout specs pin sizes and field offsets. Unmanaged `collection` and
`inspection` fixtures run in fresh disposable processes with bounded polls,
owned gated children and one collector. They cover normal/signal termination,
stop/continue, no-event sentinels, WNOWAIT then collection, repeated-collection
refusal, copyout failure, native CPU structure, self/child inspection, both
identity modes and mismatch, all exposed usage versions, list filters,
insufficient buffers, invalid requests and target disappearance.

The runner's coverage roster has twelve cases and maps the new operations to
positive cases in both optimization modes. The unmanaged LLVM and zero-import
gates apply to those fixtures. Earlier hosted results qualify their recorded
source/artifacts only; adding these cases does not rerun the macOS 15/26 hosted
matrix or establish consumer lifecycle qualification. See [support](support.md)
and the [runner guide](../ci/README.md).

[syscalls]: https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/bsd/kern/syscalls.master
[wait]: https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/bsd/sys/wait.h
[resource]: https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/bsd/sys/resource.h
[signal]: https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/bsd/sys/signal.h
[proc]: https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/bsd/sys/proc_info.h
[private]: https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/bsd/sys/proc_info_private.h
[exit]: https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/bsd/kern/kern_exit.c
[resources]: https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/bsd/kern/kern_resource.c
[inspection]: https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/bsd/kern/proc_info.c
[task]: https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/kern/bsd_kern.c
[recount]: https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/kern/recount.h
[libproc]: https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/libsyscall/wrappers/libproc/libproc.c

[delivery]: https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/bsd/kern/kern_sig.c
