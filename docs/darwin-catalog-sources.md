# Darwin catalog source register

Reviewed 2026-11-12 with the repository's `github-search` helper and its
file-backed PAT pool. No Keychain or keysafe credential path was used. The
reference clones named below are disposable and sit outside every repository
at `/tmp/native-kernel-github-reference.T4BcoZ`.

This register answers which upstream repositories can strengthen the Darwin
operation inventory. It does not transfer their licenses to Native-Kernel and
does not make a third-party binding authoritative for Apple's ABI.

The evolving `syscall-advice` evidence corpus is tracked separately in
[Syscall Advice evidence intake](darwin-syscall-advice-intake.md). That corpus
adds consumer precedents and host-scoped C probes; every source-derived claim
must still be reproduced from this inventory's exact admitted XNU profile.

## Verified repositories

The core and follow-up repositories were verified individually through
GitHub's repository API.

| Repository | Evidence and intended use | License reported by GitHub | Verdict |
| ---------- | ------------------------- | -------------------------- | ------- |
| [apple-oss-distributions/xnu](https://github.com/apple-oss-distributions/xnu) | Primary source for BSD entries, Mach traps, `proc_info` selectors, MIG definitions, private headers and implementation semantics. The tracked catalog pins commit `ac9718fb1af618d5ce8678d0dc6e8a58f252216f`, tag `xnu-12377.121.6`. | `NOASSERTION`; source files carry APSL 2.0 notices | use |
| [apple-oss-distributions/Libc](https://github.com/apple-oss-distributions/Libc) | General C wrapper behavior, error translation, cancellation and compatibility fallbacks. XNU's in-tree `libsyscall`, not this separate repository, owns the reviewed `libproc` wrapper semantics. | `NOASSERTION` | use |
| [apple-oss-distributions/bootstrap_cmds](https://github.com/apple-oss-distributions/bootstrap_cmds) | MIG compiler and manuals. `migcom.tproj/routine.c`, `statement.c`, `type.c`, `user.c`, `server.c` and `mig.1` explain numbering, skips, implicit fields, dispositions and generated cleanup. Use for the deferred per-routine catalog, not to replace exact XNU build inputs. | `NOASSERTION`; inspected files carry APSL 2.0 and CMU notices | use |
| [apple-oss-distributions/AvailabilityVersions](https://github.com/apple-oss-distributions/AvailabilityVersions) | Version-name and availability mapping used to interpret SDK annotations. It can normalize release labels but cannot establish kernel behavior or private-interface support. | no SPDX value reported | use |
| [apple-oss-distributions/libpthread](https://github.com/apple-oss-distributions/libpthread) | Concrete `bsdthread`, workqueue and private synchronization operation values and wrapper behavior. Keep these outside the public surface until a consumer owns the runtime contract. | no SPDX value reported | use |
| [apple-oss-distributions/libdispatch](https://github.com/apple-oss-distributions/libdispatch) | Consumer evidence for workqueue, kevent and thread-pool contracts. It shows real call combinations but is not the kernel selector authority. | Apache-2.0 | use |
| [apple-oss-distributions/dyld](https://github.com/apple-oss-distributions/dyld) | Consumer and exported-symbol evidence around spawn, task/process image notification and private process controls. Use only when the corresponding XNU/SDK operation is under review. | `NOASSERTION` | use |
| [apple-oss-distributions/top](https://github.com/apple-oss-distributions/top) | Small concrete consumer of `proc_pidinfo`; useful for return-size and polling expectations. | no SPDX value reported | have |
| [apple-oss-distributions/adv_cmds](https://github.com/apple-oss-distributions/adv_cmds) | Additional process-inspection consumer evidence. It is an oracle for usage patterns, not ABI authority. | no SPDX value reported | have |
| [apple-oss-distributions/libplatform](https://github.com/apple-oss-distributions/libplatform) | Commpage entry points and library-mediated facilities that a syscall-only inventory cannot see. | Apache-2.0 | use |
| [apple-oss-distributions/IOKitUser](https://github.com/apple-oss-distributions/IOKitUser) | User-client call shapes and service-specific external method selectors. This supports provider catalogs, not a universal IOKit selector table. | `NOASSERTION` | use |
| [rust-lang/libc](https://github.com/rust-lang/libc) | Independent public-header cross-check for Darwin constants and record names, including `PROC_PIDTASKALLINFO`. Never use it to override exact Apple source. | Apache-2.0 | have |
| [golang/sys](https://github.com/golang/sys) | Generated Darwin syscall-number cross-checks for amd64 and arm64. It does not supply the secondary selector landscape. | BSD-3-Clause | have |
| [darlinghq/darling](https://github.com/darlinghq/darling) | Possible behavior and compatibility oracle when Apple source is unclear. Its GPL-3.0 code is not copied into this project, and the attempted `proc_info` code searches did not locate a useful catalog. | GPL-3.0 | have |
| [ziglang/zig](https://github.com/ziglang/zig) | The GitHub repository says development moved to Codeberg, and the targeted Darwin `proc_info` search returned no result. It adds no current catalog evidence here. | MIT | reject |

Repository verification recorded these GitHub facts on 2026-11-12: XNU had
3,880 stars; Libc 104; bootstrap_cmds 19; AvailabilityVersions 12;
libpthread 54; libdispatch 151; dyld 724; top 14; adv_cmds 16; libplatform 23;
IOKitUser 29; rust-lang/libc 2,647; golang/sys 1,362; Zig 43,279; and Darling
13,755. None was reported archived. These popularity values are discovery
context, not technical evidence, and will become stale.

## Exact reference revisions and roles

Disposable clones inspected on 2026-11-12 had these HEADs:

| Repository | Revision |
| ---------- | -------- |
| XNU | `ac9718fb1af618d5ce8678d0dc6e8a58f252216f` |
| bootstrap_cmds | `c71d2d72f48995baaea76148f61002e5299841de` |
| AvailabilityVersions | `149b1777f3e8c2133042d8e188f72e3adf6a7110` |
| libpthread | `42d026df5b07825070f60134b980a1ec2552dfee` |
| libdispatch | `2361ffb78a76f7ee488cd052eb0bc5c767118bf9` |
| dyld | `fd8d0c4d52320ebf64db34f3cb280310d905c5ae` |
| top | `1e3b6cace1cbca04536cf325da9adc7389a27e8f` |
| adv_cmds | `6bed8737a34dbb54782a18f47dccf933a9967a12` |
| libplatform | `2512ffd8bb5c6caff3c8ea83331ab8a0adc820c3` |
| IOKitUser | `323ead896d04424f87184d8f6ff0cce811aab106` |

The primary semantic sources missed by repository-name searches are inside
the pinned XNU tree:

- `libsyscall/wrappers/libproc/libproc.c`, `libproc.h` and
  `proc_listpidspath.c` define byte-count/PID-count translation, fixed-size
  usage calls, errors and concrete `proc_info` flavor combinations;
- `osfmk/mach/Makefile`, `makedefs/MakeInc.def` and `MakeInc.cmd` define the
  kernel MIG input sets, platform conditions and kernel user/server defines;
- `libsyscall/xcodescripts/mach_install_mig.sh` defines the public, private and
  internal SDK-facing Mach header sets, including the macOS/embedded
  `mach_vm.defs` split;
- `libsyscall/Libsyscall.xcodeproj/project.pbxproj` binds those generation
  steps into the product build;
- `bsd/sys/spawn_internal.h` carries private spawn records and extension
  fields that public function names alone cannot reveal;
- `bsd/pthread/workqueue_syscalls.h`, `bsd/sys/ulock.h` and libpthread call
  sites define packed private synchronization selectors;
- `bsd/kern/kern_newsysctl.c`, `bsd/sys/fsctl.h`, `bsd/sys/codesign.h` and
  `bsd/kern/kern_proc.c` supply registration, request encoding, authorization
  and returned-right semantics for later catalogs;
- `bsd/sys/coalition.h`, `bsd/sys/kern_memorystatus.h` and
  `bsd/sys/process_policy.h` define separate private policy domains; and
- `iokit/DriverKit/IOUserClient.iig` is an interface-generator space distinct
  from MIG `.defs` and from provider-specific external method selectors.

The generated MIG source map now records two independent roles from those XNU
build controls: kernel build membership and libsyscall header export. A source
file may be present in the tree without either role. Those columns still do not
resolve a preprocessor configuration into active per-routine message IDs.

The installed Xcode 15.4 SDK was also inspected as a versioned cross-check. It
contains public `libproc.h`, `sys/proc_info.h` and generated Mach interface
headers. Its `mig` and `migcom` identify themselves as `bootstrap_cmds-138`.
Those installed artifacts are not substituted for the pinned XNU source or
used to claim Monterey availability.

## Search receipts

Repository search totals are retained so a later reviewer can distinguish an
empty query from an omitted search.

| GitHub repository query | `total_count` |
| ----------------------- | ------------: |
| `org:apple-oss-distributions xnu` | 1 |
| `org:apple-oss-distributions Libsyscall` | 0 |
| `org:apple-oss-distributions Libc` | 7 |
| `darwin syscall macos xnu` | 1 |
| `macos syscall generator` | 0 |
| `org:apple-oss-distributions syscall` | 0 |
| `org:apple-oss-distributions mach` | 0 |
| `org:apple-oss-distributions IOKit` | 2 |
| `org:apple-oss-distributions pthread` | 0 |
| `darwin xnu syscall table` | 0 |
| `org:apple-oss-distributions bootstrap_cmds` | 1 |
| `org:apple-oss-distributions AvailabilityVersions` | 1 |
| `org:apple-oss-distributions libdispatch` | 1 |
| `org:apple-oss-distributions dyld` | 1 |
| `org:apple-oss-distributions top` | 1 |
| `org:apple-oss-distributions adv_cmds` | 1 |

The organization repository listing, rather than those name searches, found
the exact official repository names. Code searches then established:

- XNU has one `bsd/kern/syscalls.master` and 52 `.defs` files with a
  `subsystem` declaration across the pinned source tree. The generated MIG map
  separates 49 production sources from three test-only sources. use
- XNU's `proc_info_private.h` defines 20 outer `PROC_INFO_CALL_*` operations.
  The public and private headers together contribute 94 currently selected
  call, flavor, list, action and identity-flag rows to the generated process
  catalog. use
- Libc returned 20 code-search matches for `syscall`, including wrapper and
  fallback behavior. Its public `unistd.h` warning that generic `syscall(2)` is
  unsupported reinforces Native-Kernel's typed, admitted-entry approach. use
- libpthread returned one direct `__workq_kernreturn` match with its operation
  values. use
- bootstrap_cmds returned five focused `migcom`/routine matches. The compiler
  source and manuals show why `base + raw declaration ordinal` is not a sound
  message-ID derivation in the presence of skips, preprocessing and implicit
  fields. use
- libdispatch returned 20 `workq` and 11 `pthread_workqueue` matches. Those are
  consumer evidence only; an exact `__workq_kernreturn` query returned zero and
  is not treated as absence. use
- top and adv_cmds each returned one focused `proc_pidinfo` match. have
- AvailabilityVersions returned 11 `macOS` matches relevant to release-name
  normalization. use
- libplatform returned six commpage matches. use
- IOKitUser returned ten `IOConnectCallMethod` matches, showing why external
  method selectors must be catalogued per service. use
- rust-lang/libc returned two `PROC_PIDTASKALLINFO` search matches. Its Apple
  module's values for `PROC_PIDTASKALLINFO`, `PROC_PIDTBSDINFO` and
  `PROC_PIDTASKINFO` are 2, 3 and 4, matching the pinned XNU header and
  Native-Kernel records. have
- golang/sys returned two generated `SYS_PROC_INFO` matches. Its amd64 and
  arm64 number files both record 336, matching the pinned BSD table. have
- The targeted Zig and Darling searches produced no useful process selector
  table. reject

One Darling code-search request exhausted the active GitHub code-search token's
rate bucket. The search stopped until the reported reset time, then continued
through the PAT pool. No result was inferred while rate-limited.

## What these sources fill next

The exact XNU source already fills two durable artifacts:

- `darwin-proc-info-operations-xnu-12377.121.6.csv` is the bounded
  Process-Control secondary-operation queue. It records public versus private
  provenance, exact numeric values, size-macro expressions and current
  Native-Kernel coverage. use
- `darwin-mach-mig-subsystems-xnu-12377.121.6.csv` identifies every pinned
  MIG subsystem source, base message ID, declared routine/skip counts and
  kernel/libsyscall build roles. It is a source map, not yet a per-routine
  request/reply ABI catalog. use

The next extraction should parse every admitted MIG routine into its message
ID, request/reply fields, port dispositions and conditional availability. The
next semantic pass should reconcile public `proc_info` selectors with XNU's
in-tree `libsyscall/wrappers/libproc` implementation and retain private
selectors only when Process-Control has a concrete consumer and native
denial-path evidence.
