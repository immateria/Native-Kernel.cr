# Syscall Advice evidence intake

Reviewed 2026-11-12. This document maps the evolving `syscall-advice` Agent
Skill into Native-Kernel work without making the Skill an ABI authority or a
runtime dependency.

## Evidence generation 1 — predecessor

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

## Evidence generation 2 — tranche 2

The bounded evidence intake authenticated this generation on 2026-11-12. The hashes below are
the exact external artifact and packaged-source identities it reproduced; they
are not identities inferred from filenames or a later Skill bundle.

| Artifact | SHA-256 |
| -------- | ------- |
| `skill.zip` | `107b21e8bc6e58572a7285f4d270fdb6f5f069ca6910b5ef597e907f55f5cb5f` |
| `macos-probes-final.json` | `281af17dc88c19200e466270801ddc7451cc6de79f71a6fbaaf8b16969063774` |
| `macos-probes-final-verifier.json` | `c54a47c65231b6c6475fbb61fca248390fa04f80e245fafa86f5001c0ec7162b` |
| `macos-probes-fixed.json` | `cde2365b0fa2a00fe38427bc4f91c0c4e5239b57cee81de4148cb385455ce89d` |
| `macos-probes-failures-unsandboxed.json` | `af9377d3d54a807b31832ca70f078adc60a0d9cb87466679c4e562811719db2e` |
| `macos-probes-mach-fixed.json` | `7b98c47f4d8c387c2346abcadf73358b7885786046a92606157b5935c8925a56` |
| `findings.md` | `d31567c312694f8f33b6eca65a0ff78bdf7c89d2f85c4cb5364e9a4759a7770d` |
| packaged `probes/manifest.json` | `c435944a868d13153e0ac29af92e2d27591145e2835f3027aba035322d77ccf3` |
| packaged `evidence/probe-source-digests.json` | `1825caca94ff808f8521e71575239660b747261a8b77bfc17c24573dd1a35a8a` |
| packaged `probes/darwin_mach_send_timeout_probe.c` | `1af775a0515a3f60784a17fc11de41602bd650d5f5c0a685bc36f97368bbb5f6` |

The final report is runtime-observed C-probe evidence for native arm64 macOS
15.4.1 build 24E263, Darwin 24.4.0, SDK 15.4, Apple Clang 17.0.0
(`clang-1700.0.13.3`) and Node 26.0.0, with
`sysctl.proc_translated=0`. Its exact manifest has 33 current Darwin results:
33 passes, zero skips and zero failures. The packaged identity verifier passed
with both `--require-all-darwin` and `--require-native-arm64`.
The recorded SDK path was
`/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk`;
the compiler path was
`/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang`.

The retained reports form this ordered evidence sequence:

| Report | UTC interval | Result | Evidence classification |
| ------ | ------------ | ------ | ----------------------- |
| `macos-probes-fixed.json` | 2026-11-13 01:06:35.157–01:06:41.948 | 27 pass, 6 fail | Sandboxed runtime observation. Five loopback, notify and PTY failures were environmental; the Mach failure was probe-internal. |
| `macos-probes-failures-unsandboxed.json` | 2026-11-13 01:07:04.153–01:07:05.747 | 5 pass, 1 fail | Focused unsandboxed runtime observation. The five environmental cases passed; the original Mach probe still failed. |
| `macos-probes-mach-fixed.json` | 2026-11-13 01:07:43.958–01:07:44.242 | 1 pass, 0 fail | Focused runtime observation after correcting the Mach probe's undersized cleanup receive buffer. |
| `macos-probes-final.json` | 2026-11-13 01:07:53.488–01:07:59.790 | 33 pass, 0 fail | Final runtime observation for the exact host, toolchain, manifest and probe-source digests above. |

The five environmentally constrained cases were `darwin-sendfile-hdtr`,
`darwin-so-error-clear`, `darwin-notify-suspend`,
`darwin-pty-controlling-terminal` and `darwin-connectx-deferred`. The original
`darwin-mach-send-timeout` failure was not an operating-system contradiction:
its cleanup receive storage omitted trailer capacity. The original failures
remain evidence and are not relabelled as passes.

The Skill's source evidence remains scoped to XNU commit
`f6217f891ac0bb64f3d375211650a4c1ff8ca1ea`. That is not Native-Kernel's exact
inventory profile, XNU commit
`ac9718fb1af618d5ce8678d0dc6e8a58f252216f`. A tranche-2 runtime result does
not reconcile that source difference, qualify Crystal code, establish Intel or
Monterey behavior, or create a public support guarantee.

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

### Tranche-2 operation disposition

Each row below records runtime-observed C-probe evidence on the exact tranche-2
host and bytes above. Source interpretations remain scoped to their recorded
source revision and must be reproduced from Native-Kernel's admitted exact XNU
profile before implementation.

| Probe | Primary operation | Named or secondary operation | Native-Kernel disposition |
| ----- | ----------------- | ---------------------------- | ------------------------- |
| `darwin-renameatx-contracts` | BSD 488 `renameatx_np` | `RENAME_SWAP`, `RENAME_EXCL` and their invalid combination | Record runtime evidence in the secondary flags queue; no wrapper. |
| `darwin-vnode-replacement` | BSD 363 `kevent` | `EVFILT_VNODE` opened-object identity across replacement | Record event-lifecycle evidence; do not claim pathname-watch semantics. Its relevance to BSD 369 `kevent64` is source corroboration, not direct runtime qualification. |
| `darwin-madv-free` | BSD 75 `madvise` | `MADV_FREE` mapping validity and discardable contents | Record VM selector evidence; no content-preservation claim. |
| `darwin-sync-commands` | BSD 92 `fcntl` plus BSD 95 `fsync` | `F_BARRIERFSYNC`, `F_FULLFSYNC` | Record command availability/results; no durability claim. |
| `darwin-lock-lifetime` | BSD 92 `fcntl` | `F_OFD_SETLK` versus `F_SETLK` ownership lifetime | Record command/lifetime evidence; leave lock policy to File-Lock/Filesystem consumers. |
| `darwin-pty-controlling-terminal` | composed library/kernel path | `forkpty`, session, group, `/dev/tty`, foreground group and descriptor postconditions | Record consumer evidence only; no synthetic `forkpty` syscall row. |
| `darwin-connectx-deferred` | BSD 447 `connectx` | `CONNECT_RESUME_ON_READ_WRITE` | Record loopback observation; no general network or early-data claim. |
| `darwin-mach-send-timeout` | libSystem `mach_msg` transport; raw trap slots `-31`/`-47` are source-mapped but were not both runtime-exercised | `MACH_SEND_TIMED_OUT`, `MOVE_SEND` pseudo-receive, returned header/right ownership | Add to the Mach ownership queue and qualify with a separate unmanaged Crystal case. |

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
