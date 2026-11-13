# Syscall Advice evidence intake

Reviewed 2026-11-12. This document maps the evolving `syscall-advice` Agent
Skill into Native-Kernel work without making the Skill an ABI authority or a
runtime dependency.

## Evidence boundary

The reviewed Skill bundle and macOS report have these identities:

| Artifact | SHA-256 |
| -------- | ------- |
| `skill.zip` | `1af22af613ddbe6d9eff04124d00a4adbc2c7198df1d09aac6d4006cac015a8a` |
| `macos-probes-final.json` | `49f9af0cb360be7052d7f9e3a610ed32578f8f1e72cc00ba08952ba66a87efb1` |
| primary Darwin source audit | `a69347ae10fd62516074ec0f23469e989df6421513c0cfa13b60cb8d4128160e` |
| supplemental Darwin source audit | `59bb0204397d684210c37ebdb37db4d27bff725b81b7cc59051ab60b50dcec9f` |
| probe manifest | `ddcbfe1392250afc5c5d89f0d600bd32917feb45fc60d97b6821dccbdfb7c76f` |

The report records 25 passes, no skips and no failures on native arm64 macOS
15.4.1 build 24E263, Darwin 24.4.0, SDK 15.4 and Apple Clang 17.0.0. It is C
probe evidence for those exact bytes and that host. It is not Crystal native
artifact qualification, an Intel or Monterey result, a support guarantee, or
proof for a different SDK.

The Skill's primary XNU archive is pinned to
`f6217f891ac0bb64f3d375211650a4c1ff8ca1ea`. Native-Kernel's current exact
inventory profile is `ac9718fb1af618d5ce8678d0dc6e8a58f252216f`. A source
claim discovered in the Skill must therefore be reproduced from
Native-Kernel's admitted exact source before it changes a generated inventory.
The Skill's source audits remain useful consumer and earlier-source evidence.

Keep the Skill and its reports outside this repository. Record immutable
artifact identities and bounded conclusions here; do not add a runtime or
build dependency on the Skill.

## Current mapping

| Skill surface | Native-Kernel disposition | Consumer boundary |
| ------------- | ------------------------- | ----------------- |
| `waitid(WNOWAIT)` observation, one later reap and `ECHILD` after collection | Corroborates the existing typed wrapper, no-event rules and native collection fixtures. No API change. | Process-Control retains designated-reaper and collection policy. |
| `POSIX_SPAWN_CLOEXEC_DEFAULT` with explicit same-number inheritance | Corroborates close-by-default behavior already exercised by the restricted spawn fixtures. It does not validate Native-Kernel's private descriptor layouts. | Process-Control owns the allowed-descriptor set and launch discipline. |
| `EVFILT_SIGNAL` while `SIGUSR1` is ignored | Add the filter constant and a native behavior case proving observation remains distinct from disposition. | A consumer decides whether an observed generation has any policy meaning. |
| `MACH_RCV_LARGE` oversized receive retry | Add to the Mach operation/ownership queue. Do not generalize the fixed task-info reply exchange merely to expose it. | A future generic Mach or MIG consumer must own buffer growth and received-right cleanup. |
| `MACH_RCV_BODY_ERROR` and partial ownership | Reinforces the existing partial-reply cleanup path and the future per-routine MIG catalog. | Caller policy handles cleanup uncertainty; operation and cleanup codes stay separate. |
| `EV_DISPATCH2` deferred deletion and `EV_UDATA_SPECIFIC` identity | Add to the named kqueue operation queue. Defer typed constants/recipes until a consumer needs this lifecycle. | Event-owner policy must retain registration identity through terminal deletion. |
| SCM_RIGHTS installation without `MSG_CTRUNC` | Record under `sendmsg`/`recvmsg`, ancillary-layout and descriptor-ownership work. Do not treat the flag as proof that no descriptor was installed. | A future IPC consumer sizes control storage before consumption and owns admission/cleanup. |
| `sendfile`, `fcopyfile`, `SO_ERROR`, `F_PREALLOCATE`, `dispatch_io`, `dlerror` and notify behavior | Retain as discovery evidence for later networking, filesystem, loader and notification consumers. Do not broaden the Process-Control surface. | The first concrete consumer supplies the contract and native qualification. |

## Applied intake

The 2026-11-12 intake added `EVFILT_SIGNAL` and extended the unmanaged event
fixture. The fixture owns its kqueue, temporarily installs `SIG_IGN` for
`SIGUSR1`, sends that signal to itself, observes one `EVFILT_SIGNAL` event with
a positive generation count, confirms that observation did not change the
signal disposition, restores the exact prior default mask and flags, and closes
the queue on every registered path.

The final fixture passed development and release artifact audits and native
execution with Crystal 1.22.2 and the 1.10.0 floor on ARM64. Both compiler
levels also passed the source-bound x86-64 local qualification under Rosetta,
including the event case in both artifact modes. Translation is recorded in
those receipts and is not native Intel qualification. The complete Python
contract suite passed 176 tests with one Linux-only skip, and Process-Control's
consumer check passed 130 examples. A runner contract also gained enough time
for a translated Python child to emit its bounded-output fixture before the
intentional timeout; the timeout, process-group cleanup and truncation
expectations did not change.

## Useful source expansion

The Skill's source registry adds consumer evidence that complements the current
catalog register:

- `launchd`, `system_cmds`, `Libnotify` and `dyld` for process, Mach and
  notification call combinations;
- `file_cmds`, `network_cmds`, `lsof` and `dtrace` for concrete selector and
  observation use;
- `libuv`, `Mio`, SwiftNIO, `node-pty` and OpenSSH for mature-runtime process,
  event, PTY and descriptor-lifecycle precedents; and
- `copyfile`, `libmalloc` and `libplatform` for named operation spaces that are
  not reducible to the primary syscall table.

These repositories are oracles for discovery and usage. XNU exact source,
admitted SDK/header bytes and native target observations retain their separate
roles. A third-party call site never overrides an Apple ABI definition.

## Intake procedure for a later Skill bundle

For each new bundle or macOS report:

1. Record the bundle, probe manifest and report SHA-256 values, host/build,
   architecture, translation state, SDK and compiler.
2. Compare probe IDs and claims with this mapping. Preserve removals, changed
   expectations, skips and failures; a greener report is not automatically a
   stronger contract.
3. Classify each new fact as public contract, SDK/header evidence, admitted
   source behavior, runtime observation, probe-internal behavior or inference.
4. Reproduce source-derived claims against the exact source manifest used by
   the Native-Kernel inventory. Record revision disagreements rather than
   choosing whichever copy is newer.
5. Search the existing typed surface and native fixtures before proposing an
   API. Mark corroborated behavior without adding a duplicate wrapper.
6. Add a typed primitive only when the operation is stateless, its ABI and
   ownership are explicit, and a real consumer needs it. Keep retry, identity,
   admission and cleanup policy in that consumer.
7. Port a consequential C observation into an unmanaged Crystal fixture when
   it is meant to qualify Native-Kernel. The Skill report remains independent
   corroboration, not a substitute for that run.
8. Run Native-Kernel's affected native/compiler matrix and Process-Control's
   consumer checks. Keep all reports and scratch artifacts outside both
   repositories.

The expected result of an intake can legitimately be documentation only. A
new probe does not require a new public constant, wrapper or support claim.
