# Darwin 21 spawn and task-token foundations

Source audit and implementation date: **2026-11-11**. The original checkpoint
recorded a source-derived ABI profile and build handoff. The later native Intel
fixture corrections and manifest-bound Monterey results are recorded below.
It applies only to native64 x86-64 code targeting macOS 12.7.6 / build 21H1320
/ Darwin 21.6.0. The owner's reported shipping kernel is
`xnu-8020.240.18.709.2`.

## Working record

| Item | Observed value |
| --- | --- |
| Starting Native-Kernel HEAD | `7ba36ef6d37f4d973816065994eef6099e336967` |
| Starting worktree | clean; no unrelated work was present |
| Initial Arena audit host | `Linux e2b.local 6.1.158+ #1 SMP PREEMPT_DYNAMIC ... x86_64 GNU/Linux` |
| Initial Arena language tools | Python 3.11.2 and GCC 12.2.0 (`cc`); Crystal and Clang were unavailable |
| Apple source checkout | external `/tmp/xnu-27b03b360a988dfd3dfdf34262bb0042026747cc`, never added to this repository |

The exact shipping `.240.18.709.2` source was not available during this audit.
The nearby official published source below is **not** asserted to be the
shipping kernel. That limitation blocks a matching-source claim but does not
block implementation of the independently audited Darwin 21 profile.

## Immutable source inventory

All consumed XNU bytes came from the official
[`xnu-8020.140.41` immutable revision `27b03b360a988dfd3dfdf34262bb0042026747cc`](https://github.com/apple-oss-distributions/xnu/tree/27b03b360a988dfd3dfdf34262bb0042026747cc).
The path links are immutable URLs at that revision. Byte counts and SHA-256
were measured from the external checkout.

| Consumed file | Revision | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| [`bsd/sys/spawn_internal.h`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/bsd/sys/spawn_internal.h) | `27b03b360a988dfd3dfdf34262bb0042026747cc` | 20,172 | `e9da073534f9d74d50636c47db12ff63172bf7851659f92fd32c7c75360cc5a2` |
| [`bsd/kern/kern_exec.c`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/bsd/kern/kern_exec.c) | same | 214,204 | `16c70a4bd0e86e187279a55bf9923342c8c1fdc403b5429bbe0386437d766bdf` |
| [`bsd/kern/syscalls.master`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/bsd/kern/syscalls.master) | same | 58,623 | `b216ba0bd79748f5299c2c02b40c0fc6793a6ae3e9d3df02209ac604797be2c4` |
| [`bsd/sys/spawn.h`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/bsd/sys/spawn.h) | same | 3,763 | `ec21960d173b9377c47c726b7b2f797042f4f079b5466238b39a88a0ca83d19e` |
| [`bsd/sys/signal.h`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/bsd/sys/signal.h) | same | 24,518 | `756fed2cab1ebcff529a90b6216629a4b14ebc58fda84acc314ecad458cd17b8` |
| [`bsd/kern/kern_sig.c`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/bsd/kern/kern_sig.c) | same | 93,805 | `300cbd63e2d8e23ba181adcda80e8c7d8c2766d537c7a80bb717dc8f94ef463b` |
| [`bsd/sys/_types.h`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/bsd/sys/_types.h) | same | 4,117 | `05c2492e48ffb3929b077b1d191b25495361c87773a761951f9b61b4602b2f3d` |
| [`bsd/sys/_types/_mode_t.h`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/bsd/sys/_types/_mode_t.h) | same | 1,465 | `7c4261bde41387fc23aefe5dee1e6298ae6b6f5592bca51947fdd9736e0640a6` |
| [`bsd/sys/_types/_sigset_t.h`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/bsd/sys/_types/_sigset_t.h) | same | 1,483 | `df99c73ecdbde1fcb3a4a22169871e036240452472b8ea70f287456d42593972` |
| [`osfmk/mach/machine.h`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/mach/machine.h) | same | 17,992 | `2c46b5dcef91a5948f7e398dd1dec48d59f28a1172c53356763627013a751dfa` |
| [`osfmk/mach/task_policy.h`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/mach/task_policy.h) | same | 19,532 | `c7eecf0838fdd5cd0f9c004e686cedbe4f242e21f550ddf104215cc693dc7529` |
| [`osfmk/kern/syscall_sw.c`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/kern/syscall_sw.c) | same | 15,487 | `7e629ccf329cff841ea40ebff9223e1c543eea4ac05b2374ef6dc9e70c92806d` |
| [`osfmk/mach/mach_traps.h`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/mach/mach_traps.h) | same | 25,150 | `d2be0e3e7643e8657b7531b396993076d6503ef30a8d74d84302f24d4ac73bc4` |
| [`osfmk/mach/message.h`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/mach/message.h) | same | 46,406 | `5bf2cb4a26867e171d91affca0cde68bbcaf33b491fb1ab3a6b722ece8c0059f` |
| [`osfmk/mach/port.h`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/mach/port.h) | same | 22,348 | `04f3aac22d1fb03f489d7a3fd4a2753db874f409d993158a2f2fadb60f165bf7` |
| [`osfmk/mach/mach_port.defs`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/mach/mach_port.defs) | same | 20,604 | `1c7cf75dc45d467ab26f68e15eab92dd481f798a09dba447686349d04e955ae8` |
| [`osfmk/mach/std_types.defs`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/mach/std_types.defs) | same | 4,991 | `d02b15a56b3c5adc9fe448f804a783a4cf8149bbf0f90727702f66c99731cb72` |
| [`osfmk/ipc/mach_msg.c`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/ipc/mach_msg.c) | same | 19,801 | `395690d8e1cd75a0ddea4cccd1a9c9bb1d05827f9823231b9fad72f1cb134727` |
| [`osfmk/ipc/ipc_kmsg.c`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/ipc/ipc_kmsg.c) | same | 163,347 | `7d0bd591f02fdfa8e7b266af97c1121f6a2ba1741645c4485d883bbd69324d07` |
| [`osfmk/ipc/ipc_mqueue.c`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/ipc/ipc_mqueue.c) | same | 41,257 | `89726fe30a36cf9e274f78a5472603dc4cd82c3c9b66090f945f77a1b11172a6` |
| [`osfmk/mach/task.defs`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/mach/task.defs) | same | 15,711 | `a2dfb70b77de48f1cf12156406afaeb6e86c840e590badd0bc46d39bddbfee94` |
| [`osfmk/kern/ipc_kobject.c`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/kern/ipc_kobject.c) | same | 47,192 | `a50d062ba2bd68ee70c628ad01c399c6b9497cf0d0a3718fb8256efe5212cc09` |
| [`osfmk/kern/task.c`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/kern/task.c) | same | 256,534 | `ac10eeb1868ce00433ee0f7ebcec0600b0ee6372ac301a4849665cb67747adc3` |
| [`osfmk/mach/task_info.h`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/mach/task_info.h) | same | 24,887 | `54f5264ac024346649c1b2617f83736ee60c7e3e67b96e9bce69e0a601371dfb` |
| [`bsd/sys/proc_info.h`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/bsd/sys/proc_info.h) | same | 39,941 | `d87f1a9dee8ad3312706b3e3e58aeb3e113e9a68ce4e45065b9fa0862eaf71dc` |
| [`bsd/kern/proc_info.c`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/bsd/kern/proc_info.c) | same | 93,104 | `ea8b44bee0404677b3e64acc81e2975cac5451b9f880f43da41d417a96e00612` |
| [`bsd/kern/kern_prot.c`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/bsd/kern/kern_prot.c) | same | 48,149 | `021c55783f2360ef859aa022b821562c357e0845b6416de27fe32a2c1a41bce6` |
| [`osfmk/mach/mig_errors.h`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/mach/mig_errors.h) | same | 4,614 | `5f9b82c31996cb2929d7bca5acb91ff5ffb1959e74da7e47deef1e25033a89c6` |
| [`osfmk/mach/ndr.h`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/mach/ndr.h) | same | 6,775 | `2fe22ecac00808ca9c927748c58f51844fdb3b70f4d0f95cebe1e7fe15ff400c` |
| [`osfmk/mach/mach_types.defs`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/mach/mach_types.defs) | same | 24,258 | `462f9361c39d6dc76a72e5e44cec092c3314f7e4149902502100848fbf5c8b0f` |
| [`bsd/bsm/audit.h`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/bsd/bsm/audit.h) | same | 12,119 | `27305a37bf8bf11c382391f776406078deef800e236625ba9ac3187d13933f79` |
| [`osfmk/mach/kern_return.h`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/mach/kern_return.h) | same | 10,008 | `4577d58f74dfbb8ef07ce460f82cb7a45999ad2a0479486df8d22658d4847f50` |
| [`libsyscall/mach/mach_msg.c`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/libsyscall/mach/mach_msg.c) | same | 24,305 | `9b50e291ef8c57490df393e453a52a390253136f1b0c3eeffd9737e32d4e0095` |
| [`bsd/vfs/vfs_lookup.c`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/bsd/vfs/vfs_lookup.c) | same | 59,606 | `8d87a17c29e2339fbc3cf968c21d1bea87286f9fcd2e6b0255e47bb4c04dff95` |

Loader validation separately uses published dyld 941.5
([`d0ad252a84bbbba1fd5937cd8b9a40d5bf08f719`](https://github.com/apple-oss-distributions/dyld/tree/d0ad252a84bbbba1fd5937cd8b9a40d5bf08f719)).
`common/MachOAnalyzer.cpp` has 296,375 bytes and SHA-256
`31270d7b507f93a88a68a0c4bd4d6d7163b21231b95bae50254359ff18de1ef8`. Its chained-fixup checks require supported
import/symbol formats, ordered/bounded starts and import regions, supported
page sizes and pointer formats. The builder restricts this Intel profile to
pointer formats 2 and 6. This reference is not an identity claim for the Mini's
shipping dyld; native loading still needs its own target receipt.

## A. Private spawn profile

`Spawn.profile(21)` now returns `Layout::Darwin21`; it is not a synonym for
the modern Darwin 24/25 profile. The immutable values are:

| Native64 item | Darwin 21 value | Evidence |
| --- | ---: | --- |
| BSD syscall | 244 | `syscalls.master`: `posix_spawn(pid_t *, const char *, const struct _posix_spawn_args_desc *, char **, char **)` |
| fixed copied attribute prefix | 152 | `offsetof(struct _posix_spawnattr, psa_ports)` in `kern_exec.c`; `attr_size != 0` only selects this fixed `copyin` length |
| complete attribute struct | 200 | pinned declaration; bytes after offset 152 are extension pointers and outside this profile |
| native64 descriptor | 128 | eight `user_size_t`/`user_addr_t` pairs in `user__posix_spawn_args_desc`; native64 branch copies `sizeof(px_args)` |
| descriptor offsets used | 0, 8, 16, 24 | `attr_size`, `attrp`, `file_actions_size`, `file_actions` |
| file-action header | 8 | two `int` fields (`alloc`, `count`) |
| action stride | 1040 | `_psfa_action_t`: type at 0, fd/fileport at 4, union at 8 |
| open payload | flags 8, UInt16 mode 12, path 14 | overlapping `psfaa_openargs` |
| chdir payload | path 8 | overlapping `psfaa_chdirargs` |
| path capacity | 1024 | `PATH_MAX` payload array |
| tested flags | `0x400c` | `SETSIGDEF=0x4`, `SETSIGMASK=0x8`, `CLOEXEC_DEFAULT=0x4000` from `spawn.h` |
| default signal set | `0xfffefeff` | all one-bit signal defaults except unresettable SIGKILL and SIGSTOP |

`kern_exec.c` verifies a nonzero action block has at least one action, is no
larger than the current FD limit permits, and has a size exactly equal to
`PSF_ACTIONS_SIZE(psfa_act_count)`. It applies actions in order. With
`CLOEXEC_DEFAULT`, it marks only explicit inheriting actions (including a DUP2
destination) for survival; the close operation itself occurs in `fdt_exec`.
Those facts justify the bounded fixture's three actions: duplicate pipe writer
to stdout, close pipe reader, then change directory to `/`.

The source does **not** use a smaller declared `attr_size` as a shorter-copy
negotiation. It only tests zero/nonzero then copies the fixed prefix. The
Darwin 21 profile therefore supplies 152 bytes, rather than reusing the
Darwin 24/25 192-byte prefix. It does not request extension fields or claim
that zeroing arbitrary future fields reproduces libc defaults.

### Independent layout assertion

`scripts/compat/darwin21_spawn_layout.c` independently transcribes only the
pinned native64 declarations and asserts the offsets, sizes and overlapping
payloads above. It does not include an Apple SDK header or downloaded Apple
source. The audit host actually compiled it successfully on 2026-11-11 with:

```sh
/usr/bin/cc -m64 -std=c11 -Wall -Werror -fsyntax-only scripts/compat/darwin21_spawn_layout.c
```

That was GCC 12.2.0 on Linux x86-64, so it demonstrates the self-contained C
layout model, not Xcode/SDK conformance. When the spawn lane is selected, the
handoff builder repeats the same assertion with Xcode's x86-64 C compiler and
records `compiled` only in its external build receipt. That Apple build had
**not** run at the original source-audit checkpoint. The native Intel correction
below records the later Xcode build and replay.

### Unmanaged spawn fixture

`spec/native/monterey_spawn.cr` is a fresh `-Dwithout_main` parent with one
`posix_spawn` child. It uses caller-owned fixed buffers and exact arrays:

| Check | Fixture evidence |
| --- | --- |
| descriptor/profile gate | refuses anything except the 152-byte / 128-byte Darwin 21 profile |
| argv/environment | target receives `nk-spawn-proof`, decimal source FD, and only `NK_SPAWN_PROOF=1` |
| stdio and output | pipe writer DUP2s to stdout; parent requires exactly `NK_SPAWN_OK\n` |
| terminal result | target returns 37; parent exclusively collects `37 << 8` |
| signal default/mask | parent installs ignored/blocked SIGUSR1; target observes default handler and unblocked bit |
| close-on-exec | target receives the original writer FD number and requires `F_GETFD` to return EBADF; stdout FD 1 remains through explicit DUP2 |
| working directory | CHDIR `/`; target opens relative `dev/null` and accepts any nonnegative descriptor, including reused stdin/stderr slots closed by `CLOEXEC_DEFAULT` |
| null path activation rejection | null syscall arguments return `EFAULT` with a positive PID copied out before the kernel's internal reap; this error-result PID grants no caller collection ownership |
| malformed descriptor action-size | the descriptor's 8-byte `file_actions_size` is below `PSF_ACTIONS_SIZE(1)`, returns `EINVAL` before fork, and preserves sentinel PID storage |
| malformed action count/size | a one-action byte length with count two fails the exact `PSF_ACTIONS_SIZE(count)` check before fork and preserves sentinel PID storage |
| invalid cwd | a CHDIR action through `/dev/null/...` fails activation; the audited kernel error path internally reaps rather than granting caller collection ownership |
| missing executable | a `/dev/null/...` executable path fails activation; no numeric PID from an error result is used as recovery input |
| cleanup | output polls total at most five seconds; every **confirmed successful** child PID has one bounded collector that signals SIGKILL on failure; setup/activation rejections never retry creation |

`kern_exec.c` validates the action minimum and exact `PSF_ACTIONS_SIZE(count)`
before it calls `fork1()`. Later activation/action failure reaches the
`spawn_no_exec` error path: the kernel copies the PID if requested and performs
its own internal reap. That is why the fixture treats only `error == 0` plus a
positive PID as caller collection ownership; it closes only its own descriptors
on a rejected activation and never retries an ambiguous create.

The fixture never changes a session or process group. It changes the signal
state only in its runner-owned probe process, which exits after the case. XNU
copies out a 16-byte `user64_sigaction` without `sa_tramp`, while a raw input is
the 24-byte `__user64_sigaction` that requires that trampoline. The fixture
therefore does not invent or reconstruct a previous trampoline; it is isolated
from the runner by process execution. Its outer runner has a 12-second
process-group bound, but the child has independent parent-side collection and
termination so runner cleanup is not its only containment.

## B. Darwin 21 `mach_msg_trap` task-token transport

`Mach.transport(21)` selects `MachMsgTrap`; `Mach.transport(22..25)` selects
the existing `MachMsg2` route. `Mach.read(current_task, name)` retains its
modern `MachMsg2` default for current callers. A Darwin 21 caller must select
its transport before the request is sent:

```crystal
transport = Native::Kernel::Darwin::Mach.transport(
  Native::Kernel::Darwin::Process.release
).not_nil!
words, count, code = Native::Kernel::Darwin::Mach.read(task, target, transport)
```

The selector returns nil for unreviewed majors. It makes no Process-Control
release-admission decision.

| Item | Audited Darwin 21 encoding/behavior |
| --- | --- |
| trap | `mach_msg_trap` is Mach trap 31 with seven arguments in `syscall_sw.c` and `mach_traps.h` |
| seven arguments | message pointer, option, send size, receive size, receive name, timeout, notify |
| initial raw trap request | `(-31, buffer, 0x003, 40, 512, reply, 0, 0)` (`SEND | RCV`) |
| receive-only retry | `(-31, buffer, 0x002, 0, 512, reply, 0, 0)` (`RCV`) |
| option widths | `mach_msg_option_t`, `mach_msg_size_t`, `mach_port_name_t`, and timeout are native 32-bit values; raw slots carry zero-extended values |
| library interruption options | `MACH_SEND_INTERRUPT=0x40` and `MACH_RCV_INTERRUPT=0x400` are **library-only** `MACH_MSG_OPTION_LIB` bits, not raw-trap controls. `mach_msg.c` masks them with `option &= MACH_MSG_OPTION_USER` before the kernel path, so this direct raw caller does not send either bit. |
| reported interruptions | if a raw exchange reports `MACH_SEND_INTERRUPTED`, no completed send is assumed and only that already-selected route can resend; if it reports `MACH_RCV_INTERRUPTED` after the combined call, the send completed and only receive is retried. A send interruption during receive-only ends the exchange. |
| request | 40 bytes: 24-byte header, NDR 8, flavor `TASK_AUDIT_TOKEN=15`, count 8; task subsystem starts at 3400 and task_info is ID 3405 |
| header rights | `0x1513`: target `COPY_SEND` (19), reply `MAKE_SEND_ONCE` (21); target send reference remains caller-owned |
| reply | task-info reply ID 3505; header + NDR + `kern_return_t` + count + up to eight UInt32 audit words |
| audit record | `mach_types.defs` transports `audit_token_t`; `bsd/bsm/audit.h` defines its eight UInt32 words; `task_info.h` makes its count `sizeof(audit_token_t)/sizeof(natural_t)`; `task.c` copies it for flavor 15 |
| receive buffer | exactly 512 bytes (`UInt32[128]`) |

`task.defs` declares the `task_info` CountInOut routine. `ipc_kobject.c`
registers `task_subsystem`; `task_info_from_user` converts the passed port to a
task-name port except the separately privileged DYLD flavor. The fixture only
uses flavor 15. `mach_msg.c`, `ipc_kmsg.c`, and `ipc_mqueue.c` establish the
send/receive route and the distinct interrupted cases. This is enough to
encode the message; it is not authority to inspect protected targets.

The raw trap result remains a Mach return code in `Result.primary` with
`error == 0`. A server/MIG result lives in reply `RetCode`; decoder failures
are native MIG-domain values: `MIG_TYPE_ERROR=-300`,
`MIG_REPLY_MISMATCH=-301`, and `MIG_ARRAY_TOO_LARGE=-307`. A successful
exchange releases its dedicated reply receive right using the caller-supplied
current task and `mach_port_mod_refs(..., MACH_PORT_RIGHT_RECEIVE, -1)`. That
cleanup is attempted after **every** exchange result. On an exchange failure,
that native exchange result wins; on exchange success, a cleanup failure is
returned. The caller still owns the task self and target send references.
Invalid current-task names can still prevent cleanup; the primitive has no
context owner able to repair them.

`Mach.retry_phase` is a pure three-state transition used by the exchange and
exposed for controlled interruption tests: only `MACH_RCV_INTERRUPTED` after a
completed send transitions to receive-only; a send interruption during
receive-only ends the exchange rather than resending. It does not claim that
`MACH_*_INTERRUPT` controls raw-trap restart behavior. `Mach.decode_task_audit_reply`
is a bounded pure decoder exposed specifically for controlled malformed-reply
tests. It reads no payload until it has rejected complex messages and checked:
reply ID 3505, declared size 36...512, NDR bytes, zero server code, count <= 8,
and exact `40 + count*4` length. It requires a caller buffer with at least 512
readable bytes and owns no port right. The ordinary read path uses it only after
exchange and reply-right cleanup.

`Mach.port_name_count` sends the unmanaged `mach_port_names` request used by
these acceptance workloads. It returns `{count, operation_code, cleanup_code}`;
a usable measurement requires both codes to be zero. `mach_port.defs` fixes
subsystem ID 3200 and two UInt32 out arrays. The native64 reply has a 24-byte
header, body, two 16-byte OOL descriptors, NDR and two counts: 76 bytes with
reply ID 3300. A generated MIG checker using the pinned definitions and the
review host's SDK agrees with those sizes/offsets; that mixed input is not a
complete Darwin 21 SDK closure or Mini execution result.

Ownership extraction precedes reply-ID, NDR and MIG count validation. It uses
received descriptor addresses and byte sizes, rather than malformed array
counts, and attempts every recognized mapping release. Success and
`MACH_RCV_BODY_ERROR` (including its `MACH_MSG_MASK` copyout bits) can transfer
mapping ownership; send and header failures never inspect the unreceived
buffer. The operation result remains separate from receive-right, VM or
structural cleanup diagnostics. A simple error envelope containing
`KERN_SUCCESS` is rejected. Nonempty data descriptors must match the audited
virtual-copy/deallocation contract.

This private cleanup is scoped to the kernel `mach_port_names` response, not
a general `mach_msg_destroy` implementation. Traversal is bounded by the
512-byte buffer and received message size. Duplicate/overlapping owned byte
ranges are coalesced without assuming page-aligned addresses. Unexpected
carried rights, OOL-port arrays, overflow or incomplete structural extraction
produce cleanup code 4 and cannot qualify a measurement. Known data mappings
are still released. Callers must not treat unsupported cleanup as reconciled
ownership or automatically retry disposal through the same numeric addresses.

`spec/mach_spec.cr` creates controlled good, complex, wrong-ID, wrong-NDR,
oversized-count, and inconsistent-size replies. Its managed Darwin fixture also
passes an unchecked enum value via `99_i32.unsafe_as(Transport)` and requires native code 4 without a
send, then performs 100 successful self reads and 100 invalid-destination reads
through the selected transport while checking Mach-name count before/after.
Those fixtures cover parser errors, exhaustive invalid-transport dispatch, and
reply-right growth checks without pretending a signal interruption can be
reliably induced on every kernel. The task-token raw fixture additionally has
an unreachable `argc == 99` compile-instantiation branch which references both
valid transports; each native bundle compiler must type-check the changed
private dispatch methods before link/audit.

`spec/native/monterey_task_token.cr` supplies the complementary unmanaged
workload. Each named task-token roster case obtains the Mach-name count before
and after 32 self successes plus 32 invalid-destination failures and requires
no growth. It then forks one gated owned child, obtains its task-name right, and
compares every returned audit PID/version pair with the live child's
`PROC_PIDT_BSDINFOWITHUNIQID` record: `kern_prot.c` sets audit words 5 and 7
from `proc_getpid` and `proc_pidversion`, while `proc_info.c` fills the same
`p_idversion` and enforces `PIF_COMPARE_IDVERSION` before copyout. The child
runs no session/group mutation.

The seventh spawn case deliberately creates a successful bounded exec target,
passes that confirmed success through the rejection path, and requires both
collection and a later `ECHILD`. Unexpected success still fails every actual
negative case. Bad executable/cwd cases require the audited `ENOTDIR` result
and post-fork PID copyout, without using an error-result PID for control.

The normal task-token path writes/closes the gate, collects status zero, asks the now-dead
destination to fail, and releases target/task rights. The separate
`task-token-gate-write-failure` and `task-token-gate-close-failure` cases
respectively write to an invalid descriptor or close the actual writer twice
to obtain `EBADF`, then use the same bounded collector. After every confirmed fork, collection is attempted even
when gate write/close reports failure; a distinct fixture return records a
cleanup/release failure rather than silently replacing the original gate
result. No path retries creation or treats a PID from a failed spawn-style
operation as collection authority.

## Native Intel fixture corrections on 2026-11-11

The returned fix report describes the initial bundle from
`9a11fc2e64c739000e9dc6aa4d33182ea700a7dd` on the native Intel Mini at
macOS 12.7.6 / 21H1320 / Darwin 21.6.0: all 16 task-token executions passed,
while spawn passed 20 of 28. Its success and null-arguments cases failed in
all four compiler/optimization builds. The report identifies two fixture
assumptions, consistent with the pinned XNU source:

- The success parent returned 33 after its target exited 15 without output.
  An instrumented unmanaged target established that CHDIR `/` succeeded and
  opening relative `dev/null` returned descriptor 0. `CLOEXEC_DEFAULT` closes
  stdin and stderr unless they are explicitly inherited, so a successful open
  can reuse those slots. The target now requires a successful, nonnegative
  descriptor and closes that exact descriptor. Its output, source-FD closure,
  signal, argument, environment and terminal-status checks remain in force.
- The null-arguments case returned the required `EFAULT`, with a positive PID
  copied out during activation. The Darwin 21 kernel internally reaps this
  failed spawn. The fixture now requires that exact error and positive copyout,
  using the existing activation-rejection path that never collects or signals
  an error-result PID. The returned managed spec supplied an unreadable
  descriptor for a pre-fork copyin failure; the integrated regression uses
  the structured pre-fork rejection described below.

These corrections affect the acceptance fixtures; the syscall entry, private
layout profiles and consumer release admission retain their existing contracts.

The returned build receipt binds all 12 executable components to the corrected
source and original Crystal 1.22.2 and 1.10.0 compiler binaries. The selected
SDK was 13.1; the report identifies Xcode 14. Independent archive inspection
reconciled every supplied executable hash, manifest payload, deployment-12.0
loader profile, empty import table and signature record. All 28 spawn and 16
task-token exact outcomes and bounded log bytes match the manifests on the
native Intel host above. The compiled source closure differs from the original
bundle only in `spec/native/exec.cr` and `spec/native/monterey_spawn.cr`; runtime
primitives and auditors are unchanged.

The build receipt records successful reachable-LLVM checks and IR/object hashes.
The returned archive omits those IR/object files and build logs, so their hashes
cannot be independently recomputed from this handoff. Its summary additionally
reports formatting, 38 specs and both unmanaged core modes on each compiler,
and 85 Python tests. The corresponding Mini logs, core manifests/artifacts,
initial failure traces and instrumented diagnosis are also absent. These are
reported auxiliary checks rather than independently reconciled evidence. The
report describes a local core-link wrapper selecting `-Wl,-fixup_chains`, the
same option used by the campaign builder, with the strict import auditor intact.

The integrated managed regression uses fully readable descriptor/action
buffers, but declares an eight-byte actions size below `PSF_ACTIONS_SIZE(1)`.
The pinned Darwin 21/24/25 sources reject this with `EINVAL` before fork. A
nonzero PID sentinel detects an erroneous overwrite. It selects the running
kernel's admitted profile and never invokes the private syscall on another
release. This replaces the returned unreadable-descriptor case. On macOS
15.4.1 / 24E263, the translated x86-64 Crystal 1.22.2 spec process stalled in
syscall handling and hit the runner's
300-second timeout. The retained sample locates it inside the new spawn call.
The structured case preserves pre-fork errno/output checks without requiring
an invalid memory dereference through translation. It is outside the replay
bundle's compiled closure; the Mini's activation `EFAULT` case is unchanged.
Process-Control Monterey admission remains a separate gate.

## Handoff and qualification gates

At Arena commit `8922b40`, only the source and C-model gates had run; that
cloud workspace lacked Crystal and an Apple compiler/SDK. The local corrective
checks below ran on macOS 15.4.1 / 24E263, Darwin 24.4.0, on an Apple M4 Max.
They preserve the source/target qualification boundary.

- Native-Kernel passes 38 Crystal specs on Crystal 1.22.2 and 1.10.0, both
  native ARM64 and translated x86-64. Each local qualification also passes the
  strict development/release core LLVM/import/runtime gates and all 24 behavior
  outcomes. The unmanaged core repeats 100 successful and 100 invalid-target
  exchanges and checks exact Mach-name counts without a managed observer.
- The final portable suite passes 85 Python contracts. The changes include
  malformed/partial received-reply disposal using real fixture-owned VM ranges,
  strict spawn rejection/cleanup, compiler launcher identity and loader checks.
- All 12 compatibility executable components build: spawn, its exec target and
  task-token, each for both compilers and optimization modes. Every artifact
  passes reachable LLVM, empty imports, ad hoc signature verification and the
  measured macOS 12.0.0 loader profile. These were translated x86-64 compiler
  component trials on ARM64, not execution of the compatibility cases or a run
  of the native-Intel-only packaging CLI.
- Process-Control retains its independently qualified Darwin 24/25 admission.
  Its companion fix explicitly refuses other majors before consulting layout
  availability. The new refusal regression also passes with the existing
  immutable dependency pin; source data availability does not grant launch
  authority. All four local consumer profiles pass 129 examples and helper
  artifact checks with the changed dependency bytes.

After the readable undersized-action regression was integrated, the complete
Native-Kernel qualification was rerun on this same macOS 15.4.1 host. All four
final receipts report 45 passing stages, 38 passing Crystal specs, 85 passing
Python tests, 24 exact behavior outcomes and an unchanged source tree: Crystal
1.22.2 and 1.10.0, each on native ARM64 and translated x86-64. The translated
verifier needed `PKG_CONFIG_PATH` directed to the installed Intel OpenSSL 3
metadata under `/usr/local`; without that selection, its managed verifier tried
to link the ARM64 Homebrew library under `/opt/homebrew`. This was a local
dependency-selection correction, not a source or auditor change.

Receipts, build logs and input hashes are external in the owner's
`arena-native-fixes-6zx6y1cp` test-cache directory. The full qualification
snapshots bind the runtime sources, managed specs and core fixture. Later
compatibility-fixture and Python-loader changes have their own portable and
compatibility-component evidence. Final corrected-fixture receipts are in the
owner's `monterey-commit-quality` test-cache directory under the `final2-*`
profiles. At this local correction checkpoint, hosted macOS 15/26 reruns and
forward replay had not run for these changes.

| Gate | State | Evidence required |
| --- | --- | --- |
| source layout audit | complete, nearby published source only | inventory and source rules above |
| independent C model | complete | GCC and selected Xcode syntax assertions |
| modern local runtime regression | complete on recorded host | both compilers, ARM64 and translated x86-64, strict artifact checks |
| compatibility component builds | complete locally | 12 x86-64 deployment-12.0 artifacts, both compilers/modes, loader/signature/import/LLVM proofs |
| native Intel packaging CLI | complete for corrected fixtures on 2026-11-11 | source-bound build receipt, both manifests and 12 audited executable components |
| manifest-bound Mini execution | complete for corrected fixtures on 2026-11-11 | all 28 spawn and 16 task-token executions passed across both compilers/modes |
| new hosted matrix / forward replay | unrun | changed-source macOS 15/26 native cells and kernel replay receipts |
| shipping-source match | unresolved | Apple publication of matching shipping source or equivalent official evidence |
| Process-Control Monterey integration | not started here | separate consumer admission, identity, ownership and lifecycle qualification |

On a native Intel Darwin build host with Xcode selected, both reviewed Crystal
compilers and this corrective checkout, run exactly:

```sh
python3 scripts/compat/build_monterey_foundations.py \
  --current /absolute/path/to/crystal-1.22.2/bin/crystal \
  --floor /absolute/path/to/crystal-1.10.0/bin/crystal \
  --output /external/new-monterey-foundations

# Build only the independent task-token lane when spawn tooling is unavailable.
python3 scripts/compat/build_monterey_foundations.py \
  --current /absolute/path/to/crystal-1.22.2/bin/crystal \
  --floor /absolute/path/to/crystal-1.10.0/bin/crystal \
  --campaign task-token \
  --output /external/new-monterey-task-token-foundations
```

The builder refuses Linux, Rosetta, non-x86-64 compiler targets or actual
compiler-binary slices, unexpected compiler versions, an existing output
directory, and output under a source checkout. It preserves the supplied
compiler invocation (including an official launcher and its environment) for
all build commands. It separately resolves the actual executable: direct
Mach-O is accepted, the one hash-pinned official `bin/crystal` launcher maps to
`embedded/bin/crystal`, and any other wrapper needs `--current-binary` and/or
`--floor-binary` naming a trusted actual Mach-O. `lipo` is run only on that
resolved binary, never on a launcher. The receipt hashes and records both
invocation and binary paths, versions/default targets, resolution reason, and
binary slices.

It sets `MACOSX_DEPLOYMENT_TARGET=12.0`; a selected spawn lane runs the Xcode
C assertion, then every selected fixture/compiler/optimization runs Crystal
cross compilation, reachable-LLVM audit, direct x86-64 link, executable `lipo -archs`
verification and `xcrun nm -u`. The link explicitly enables chained fixups to
avoid an unused `dyld_stub_binder` import at deployment target 12.0. Each final
binary is ad hoc signed and strictly verified before hashing. Measured loader
metadata must show a thin x86-64 executable, macOS minimum 12.0.0, and bounded
version-zero chained fixups with no imports. `--campaign` is repeatable; the two lanes have
separate manifests, rosters, artifacts and receipt entries. A failed spawn lane
does not suppress task-token preparation, but a failed or not-produced lane has
no qualifying manifest and remains explicit in `build-receipt.json`. No
invented binary, manifest hash or receipt is stored in Git.

Transfer each generated directory unchanged to the Mac Mini. On that exact
untranslated host, run the following separately (new output paths each time):

```sh
cd /path/to/spawn
/usr/bin/python3 -I monterey_foundations_runner.py --output /external/new-monterey-spawn-result

cd /path/to/task-token
/usr/bin/python3 -I monterey_foundations_runner.py --output /external/new-monterey-task-token-result
```

The runner requires Python isolated mode (`-I`), loads its sibling base runner
by exact path, verifies the manifest and every payload before each case and
after all cases, rejects payloads over 32 MiB, bounds each run and each stream,
records host/tool metadata and archives receipts. A preflight run on another Mac
must add `--preflight`; it is explicitly unqualified. Passing source review, C
compilation, preflight, or a cross-compile does not make a Monterey runtime
support claim.
