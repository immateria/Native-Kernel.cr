# Darwin 21 spawn and task-token foundations

Source audit and implementation date: **2026-11-11**. This document records a
source-derived ABI profile and build handoff, not Monterey runtime qualification.
It applies only to native64 x86-64 code targeting macOS 12.7.6 / build 21H1320
/ Darwin 21.6.0. The owner's reported shipping kernel is
`xnu-8020.240.18.709.2`.

## Working record

| Item | Observed value |
| --- | --- |
| Starting Native-Kernel HEAD | `7ba36ef6d37f4d973816065994eef6099e336967` |
| Starting worktree | clean; no unrelated work was present |
| Audit host | `Linux e2b.local 6.1.158+ #1 SMP PREEMPT_DYNAMIC ... x86_64 GNU/Linux` |
| Available language tools | Python 3.11.2 and GCC 12.2.0 (`cc`); Crystal and Clang were unavailable |
| Apple source checkout | external `/tmp/xnu-27b03b360a988dfd3dfdf34262bb0042026747cc`, never added to this repository |

The exact shipping `.240.18.709.2` source was not available during this audit.
The nearby official published source below is **not** asserted to be the
shipping kernel. That limitation blocks a matching-source claim but does not
block implementation of the independently audited Darwin 21 profile.

## Immutable source inventory

All consumed Apple bytes came from the official
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
| [`osfmk/ipc/mach_msg.c`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/ipc/mach_msg.c) | same | 19,801 | `395690d8e1cd75a0ddea4cccd1a9c9bb1d05827f9823231b9fad72f1cb134727` |
| [`osfmk/ipc/ipc_kmsg.c`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/ipc/ipc_kmsg.c) | same | 163,347 | `7d0bd591f02fdfa8e7b266af97c1121f6a2ba1741645c4485d883bbd69324d07` |
| [`osfmk/ipc/ipc_mqueue.c`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/ipc/ipc_mqueue.c) | same | 41,257 | `89726fe30a36cf9e274f78a5472603dc4cd82c3c9b66090f945f77a1b11172a6` |
| [`osfmk/mach/task.defs`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/mach/task.defs) | same | 15,711 | `a2dfb70b77de48f1cf12156406afaeb6e86c840e590badd0bc46d39bddbfee94` |
| [`osfmk/kern/ipc_kobject.c`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/kern/ipc_kobject.c) | same | 47,192 | `a50d062ba2bd68ee70c628ad01c399c6b9497cf0d0a3718fb8256efe5212cc09` |
| [`osfmk/kern/task.c`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/kern/task.c) | same | 256,534 | `ac10eeb1868ce00433ee0f7ebcec0600b0ee6372ac301a4849665cb67747adc3` |
| [`osfmk/mach/task_info.h`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/mach/task_info.h) | same | 24,887 | `54f5264ac024346649c1b2617f83736ee60c7e3e67b96e9bce69e0a601371dfb` |
| [`osfmk/mach/mig_errors.h`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/mach/mig_errors.h) | same | 4,614 | `5f9b82c31996cb2929d7bca5acb91ff5ffb1959e74da7e47deef1e25033a89c6` |
| [`osfmk/mach/ndr.h`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/mach/ndr.h) | same | 6,775 | `2fe22ecac00808ca9c927748c58f51844fdb3b70f4d0f95cebe1e7fe15ff400c` |
| [`osfmk/mach/mach_types.defs`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/mach/mach_types.defs) | same | 24,258 | `462f9361c39d6dc76a72e5e44cec092c3314f7e4149902502100848fbf5c8b0f` |
| [`bsd/bsm/audit.h`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/bsd/bsm/audit.h) | same | 12,119 | `27305a37bf8bf11c382391f776406078deef800e236625ba9ac3187d13933f79` |
| [`osfmk/mach/kern_return.h`](https://github.com/apple-oss-distributions/xnu/blob/27b03b360a988dfd3dfdf34262bb0042026747cc/osfmk/mach/kern_return.h) | same | 10,008 | `4577d58f74dfbb8ef07ce460f82cb7a45999ad2a0479486df8d22658d4847f50` |

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
layout model, not Xcode/SDK conformance. The handoff builder repeats the same
assertion with Xcode's x86-64 C compiler and records `compiled` only in its
external build receipt. That Apple build has **not** run here.

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
| working directory | CHDIR `/`; target opens relative `dev/null` |
| rejection | null syscall arguments must return `EFAULT` and leave caller's PID output zero |
| cleanup | output polls total at most five seconds; every confirmed PID has one bounded collector that signals SIGKILL on failure |

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
| initial trap request | `(-31, buffer, 0x443, 40, 512, reply, 0, 0)` |
| receive-only retry | `(-31, buffer, 0x402, 0, 512, reply, 0, 0)` |
| option widths | `mach_msg_option_t`, `mach_msg_size_t`, `mach_port_name_t`, and timeout are native 32-bit values; raw slots carry zero-extended values |
| interruptions | `MACH_SEND_INTERRUPT=0x40` and `MACH_RCV_INTERRUPT=0x400` request observable interruption; send interruption resends only the same route because XNU says caller still has the message; receive interruption has no message and retries receive only |
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
send transitions to receive-only; a send interruption during receive-only ends
the exchange rather than resending. `Mach.decode_task_audit_reply` is a bounded
pure decoder exposed specifically for controlled malformed-reply tests. It reads no payload until it has rejected
complex messages and checked: reply ID 3505, declared size 36...512, NDR bytes,
zero server code, count <= 8, and exact `40 + count*4` length. It requires a
caller buffer with at least 512 readable bytes and owns no port right. The
ordinary read path uses it only after exchange and reply-right cleanup.

`spec/mach_spec.cr` creates controlled good, complex, wrong-ID, wrong-NDR,
oversized-count, and inconsistent-size replies. Its managed Darwin fixture
also performs 100 successful self reads and 100 invalid-destination reads
through the selected transport while checking Mach-name count before/after.
Those fixtures cover parser errors and reply-right growth checks without
pretending a signal interruption can be reliably induced on every kernel.

`spec/native/monterey_task_token.cr` supplies the complementary unmanaged
workload. It does 32 self successes and 32 invalid-destination failures, then
forks one gated owned child, obtains its task-name right, verifies 32 reads
have that child's PID in audit word 5 and a nonzero PID-version in word 7,
kills/collects it, and requires the dead destination to fail. It releases both
the target and task rights on its normal path. It creates no new session or
process group; the parent is the exclusive bounded collector.

## Handoff and qualification gates

The source and C-model gates have run. Crystal compilation, LLVM audit,
linking, undefined-import inspection, bundle manifest generation, and native
execution have not run because this workspace has neither Crystal nor an Apple
compiler/SDK. The native gates below are **blocked by the missing x86-64
prebuilt build/bundle prerequisite**, not labelled “Awaiting target”.

| Gate | State | Evidence required |
| --- | --- | --- |
| source layout audit | complete, nearby published source only | inventory and source rules above |
| Linux independent C model | complete | successful GCC syntax-only assertion |
| Xcode C assertion | blocked: build prerequisite | external builder receipt marks `layout_assertion.status=compiled` |
| four development/release builds | blocked: build prerequisite | two Crystal versions, x86-64 target, deployment target 12.0 |
| reachable LLVM / empty imports | blocked: build prerequisite | per-artifact builder logs and hashes |
| manifest-bound Mini execution | blocked: no bundles to transfer | four exact spawn and four exact task-token results plus receipts |
| shipping-source match | unresolved | Apple publication of `.240.18.709.2` source or equivalent official source evidence |
| Process-Control integration | not started here | separate consumer release admission, identity, ownership and cleanup qualification |

On a native Intel Darwin build host with Xcode selected, both reviewed Crystal
compilers and this checkout at the reviewed commit, run exactly:

```sh
python3 scripts/compat/build_monterey_foundations.py \
  --current /absolute/path/to/crystal-1.22.2/bin/crystal \
  --floor /absolute/path/to/crystal-1.10.0/bin/crystal \
  --output /external/new-monterey-foundations
```

The builder refuses Linux, Rosetta, non-x86-64 compiler targets or compiler
binary slices, unexpected compiler versions, an existing output directory, and
output under a source checkout. It sets `MACOSX_DEPLOYMENT_TARGET=12.0`, runs
the Xcode C assertion,
then for every fixture/compiler/optimization runs Crystal cross compilation,
reachable-LLVM audit, direct x86-64 link, `lipo -archs` verification and
`xcrun nm -u`. The external receipt binds the SDK/CC identity plus the exact
Crystal binary paths, versions and SHA-256 digests. It writes external logs,
digests and separate `spawn/` and `task-token/` bundles. No invented binary,
manifest hash or receipt is stored in Git.

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
