# Linux process foundations

The two explicit entries are `native-kernel/linux/raw` and
`native-kernel/linux`. Only **non-Android LP64 GNU/musl Linux x86-64 and AArch64** are
admitted. Crystal's architecture-derived `bits64` flag alone is not LP64 proof;
GNU/musl environment selection also refuses x32 and AArch64 ILP32. Other 32-bit
Linux, Android, Windows and Darwin refuse these entries. `require "native-kernel"` remains the existing Darwin entry;
it does not silently select Linux. Source/audit metadata remains portable.

This is an implementation profile, **not a completed native qualification**.
See [the dated validation and blocks](linux-validation.md). No Process-Control
source, release admission or consumer backend is changed by this work.

```crystal
require "native-kernel/linux"
alias Linux = Native::Kernel::Linux

fds = StaticArray(Int32, 2).new(-1)
result = Linux::Descriptor.pipe2(fds.to_unsafe, Linux::Descriptor::O_CLOEXEC)
if result.error == 0
  # primary == 0; caller now owns fds[0] and fds[1], NOT Result registers.
  # Close both when finished. There is no automatic owner or cleanup policy.
  Linux::Descriptor.close(fds.to_unsafe[0])
  Linux::Descriptor.close(fds.to_unsafe[1])
end
```

## Raw entry and result

`Raw.call(number : Int32, a0..a5 : UInt64 = 0)` supplies zero through six
argument words. x86-64 uses `rax` for number/result and
`rdi,rsi,rdx,r10,r8,r9` for arguments, clobbering `rcx,r11,memory,flags`.
AArch64 uses `x8` for number, `x0..x5` for arguments and `x0` for the sole
result, with `memory,cc` clobbers. The instructions are `syscall` and `svc #0`.
There is no Darwin carry handling, stack argument area, x16 or Mach entry.
The flags clobbers are conservative; Linux's entry does not use flags to decode
errors. Crystal's fixed-register constraint syntax was checked against both
pinned compiler sources; **execution by either reviewed compiler is blocked in
the local validation**, so that inspection is not compiler/artifact proof.

Linux's own `Result` has `primary : Int64` and `error : Int32`. Primary keeps
all raw return bits, including negative errno words. Error is `-primary` only
for `-4095 <= primary <= -1`, otherwise zero. Thus an EBADF return is
`{primary: -9, error: 9}`, not Darwin's `{-1, secondary, 9}`. `-4096`, zero,
positive words and `Int64::MIN` are non-error words. No libc/TLS errno or
second result register is fabricated. The pure result decoder can be required
portably without admitting raw execution. Darwin's result and assembly keys
are unchanged.

The separate `Number` files contain 26 numbers, not a general syscall catalog.
`clone`, `execve`, `openat`, `mmap` and `munmap` are included only for unmanaged
fixtures. There is no managed fork/clone/exec/launch API.

## Mechanism surface and ownership

| Family | Public operations |
| --- | --- |
| `Descriptor` | `read`, `write`, `close`, `pipe2`, `dup3`, `fcntl` |
| `Process` | `pid`, `parent`, `getpgid`, `setpgid`, `getsid`, `setsid`, numeric `kill`, `exit_group`, `wait4`, raw `waitid` |
| `Pidfd` | `open`, `send_signal` |
| `Event` | raw `ppoll` |
| `Resource` | `getrusage`, `prlimit64` |

Buffers, byte capacities, paths, masks, records and descriptors are supplied
and owned by the caller. The shard does not allocate, retain a context, cache
features, call libc, initialize Crystal, install handlers, impose a public
signal policy, retry, reap implicitly or decide uncertain cleanup.

* `read`/`write` counts are **bytes**, not typed element counts. Only a successful
  returned count identifies transferred bytes; short/zero results are native.
* `pipe2` needs two writable `Int32` slots. A zero primary/error result acquires
  both output descriptors. Error outputs are not acquisitions or valid fd names.
* Successful `dup3` owns its destination, atomically replacing an open destination;
  equal source/destination is EINVAL, not dup2 behavior. `fcntl`'s third slot is
  a raw `UInt64`, including caller-owned pointer addresses. Successful
  `F_DUPFD[_CLOEXEC]` acquires the fd in primary; other commands have their native
  per-command output contract. A failed acquisition owns no new descriptor.
* `close` is not automatically retried: a Linux error can follow descriptor
  release. Retrying against a reused number is caller policy, not this layer.
* Numeric `kill` preserves positive PID, zero and negative group selectors and
  signal zero. These numbers do not establish identity or retained authority.
  `exit_group` normally terminates without managed Crystal shutdown. If a
  sandbox rejects exit and it returns, the raw `Result` is exposed; the library
  does not retry or choose a fallback. A disposable fixture-only termination
  loop is separately bounded by the external driver's deadline.
* Successful `Pidfd.open` owns a kernel-CLOEXEC descriptor. `NONBLOCK` is the
  v6.6 `PIDFD_NONBLOCK` flag (availability must be tested in the caller's kernel
  and sandbox). `send_signal` accepts a null or caller-owned native siginfo
  pointer and raw flags. Acquisition failures, denial, ENOSYS and other errors
  never fall back to numeric PID control. Signal zero is allowed by the raw
  mechanism; Process-Control's public policy remains its own.

Pidfd readiness is **observation**, not permission to reap an arbitrary retained
process. In particular `waitid(P_PIDFD, self_pidfd, ...)` is still ECHILD.
An authenticated helper's exclusive target collector is a separate consumer
ownership contract. Retained descriptors do not export a PID-generation token
or qualify numeric PID reuse.

## Collection, time, resources and output validity

`Process.wait4` exposes the native status word and optional `Resource::Usage*`.
A positive primary supplies that event's status and optional accounting.
Linux supplies usage for reported stop/continue events too. A zero WNOHANG
result supplies neither status nor usage. No output on error is a successful
result. **Linux may reap before a status or rusage copyout fails**; EFAULT does
not prove the child is still waitable. This deliberately does not inherit the
Darwin copyout/reaping ordering.

Raw `Process.waitid(type, id, info, options, usage)` has **five arguments**,
including the last rusage pointer (null is allowed). Clear `info.pid` before
each call, then require `error == 0 && info.pid != 0` for an event. For the
reviewed Linux source, WNOHANG/no-event clears the six SIGCHLD output fields;
the wrapper neither zeros nor promises initialization of the entire record.
No-event leaves usage untouched. WNOWAIT observes without consuming the event.
Copyout failure may follow consumption unless WNOWAIT was selected. Only the
exclusive child collector should consume statuses. `Info` reserves the full
128-byte, 8-aligned siginfo union but exposes only its SIGCHLD view. Raw waitid
writes number/error/code/pid/uid/status, **not si_utime/si_stime or its opaque
tail**. Rusage is the separate accounting output.

`Resource::Timeval` has two signed 64-bit words on both supported profiles;
its fractional unit is microseconds. `Usage` is 144 bytes. Linux `max_rss` is
**KiB (1024 bytes), not Darwin's bytes**. Other counters retain kernel meanings;
some are unused/zero. SELF queries the caller process, THREAD the calling
thread, and CHILDREN accounting accumulated from collected children, not a
live arbitrary-PID snapshot. Usage outputs are valid only on success.

`Resource::Limit` is two unsigned 64-bit words for `prlimit64`. Null new limit
queries; null old limit suppresses copyout. A set may take effect before an
old-limit copyout fault. Error does not imply rollback. The shard does not
restore limits or admit resource policy.

`Event.ppoll(fds, nfds : UInt32, timeout, mask, mask_bytes = 8)` exposes the
kernel's unsigned-int descriptor count, not libc's larger `nfds_t` binding.
Poll output is valid only on success. A nonnull timeout is **mutable caller
storage**: raw Linux may replace it with remaining seconds/nanoseconds,
including on interruption. Reinitialize it before reuse. Null waits
indefinitely. The temporary mask is the kernel's **8-byte/64-signal Set**, not
libc's 128-byte sigset_t. Wrong nonnull mask sizes preserve native EINVAL.
There is no copied timeout, retry or interpretation of unexpected event bits.

## Evidence, sources and licenses

[ci/linux-references.json](../ci/linux-references.json) records 120 file hashes
at eight immutable external source pins, including the floor compiler source,
overflow code generation, and require-path resolution reviews. Original snapshots
were external, shallow/sparse and detached; four additional Crystal compiler
files (two primitive/codegen sources and two source-path resolvers) were retrieved
through the GitHub content API at those exact compiler pins. Canonical Linux v6.6 is
`ffc253263a1375a65fa6c9f62a893e9767fbebfa`. Independent entries/error decoding
use jasonwhite/syscalls `fb4ebc28f8a4da147f03a856959306a082797a07`;
wrapper semantics use rustix `ffa6ee556f54ef646c5cfc67afc72703ae3a7382`.
The linux-raw-sys pin `3b15c17f2688445cd3e9ef2907113829837773dd` was generated
from **v6.17**, not v6.6. Its 26 used numbers agree with canonical v6.6 and
Go sys `6f4195bbcd27fffa838e6221a66c401d21944089`. No newer flags or semantics
were adopted. Go and Crystal libc signal sets are not the kernel signal set;
Go's padded Siginfo representation is not C alignment evidence. Kernel source
resolves ppoll's count width, timeout mutation, waitid's fifth slot/limited
copyouts, resource units and copyout-after-consumption semantics.

Crystal sources are pinned at 1.22.2
`1447d239ffd7b0456fcc183731c5e684b6b074f7` and 1.10.0
`9c011d77d660a5a7441370dce9e101b3ca094d8b`. No C declarations are added and
nothing from `lib_c` is imported by the Linux implementation. Inspection of
floor code also avoids the later `alignof` expression in specs; struct-offset
observations and independent C `_Alignof` assertions cover alignment.

Linux UAPI files declare GPL-2.0 WITH Linux-syscall-note. Nolibc architecture
examples declare LGPL-2.1 OR MIT; they establish registers/startup conventions,
not Crystal syntax. Linux implementation/selftests are GPL-2.0 or GPL-2.0-only
and were inspected, **not copied**. syscalls is BSD-2-Clause; Go is
BSD-3-Clause; Rust projects offer MIT/Apache alternatives; Crystal is
Apache-2.0. This implementation, startup and test fixtures are original MIT
code expressing ABI facts; no reference trees or third-party implementation
bodies are vendored. Per-file licensing, not a repository API license label,
controls any future reuse.

Process-Control `9bf6fc1a32f01238ebd47f2efc42604fb3e04605` (MIT) is a
**read-only requirements reference**. Pidfd observation, authenticated helper
startup, one target-status source and delegated-cgroup behavior remain its
policy. Full clone3/exec launch, cgroups, namespaces/credentials, signal
handlers/restorers, raw threads, PID-reuse qualification and consumer migration
are deferred. Fixture clone/exec is restricted to disposable unmanaged workers.
