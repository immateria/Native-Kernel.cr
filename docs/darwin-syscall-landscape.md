# Darwin syscall and operation landscape

Inventory date: 2026-11-12. This is an implementation-decision aid, not a
claim that every kernel entry should become a public typed API.

## The missing 92 percent

The corrected latest snapshot contains 533 active logical rows for XNU
`xnu-12377.121.6`. Native-Kernel currently uses 44 of those primary entries
through typed wrappers. The remaining list therefore has 489 rows, or 91.7
percent of the active logical surface.

- [Complete active primary-table inventory](data/darwin-active-syscalls-xnu-12377.121.6.csv)
- [Gap-only inventory](data/darwin-syscall-gaps-xnu-12377.121.6.csv)
- [Selector-like BSD parameter candidates](data/darwin-secondary-catalog-candidates-xnu-12377.121.6.csv)
- [Exact `proc_info` operation catalog](data/darwin-proc-info-operations-xnu-12377.121.6.csv)
- [Exact Mach MIG subsystem source map](data/darwin-mach-mig-subsystems-xnu-12377.121.6.csv)
- [Machine-readable provenance and counts](data/darwin-syscall-inventory.json)
- [Exact XNU source manifest](data/darwin-xnu-source-manifest-xnu-12377.121.6.json)
- [Upstream data provenance and license](data/README.md)
- [GitHub catalog source register](darwin-catalog-sources.md)
- [Syscall Advice evidence generations and dispositions](darwin-syscall-advice-intake.md)

The CSVs retain XNU's logical name, handler, prototype, condition, audit class,
architecture, source path and source line. They add Native-Kernel's present
coverage state, catalog state and source files. `implementation_decision` is
`unreviewed` for an unimplemented BSD call or Mach trap. Generation does not
guess whether an entry is desirable.

| XNU family | Active logical rows | Numeric slots | Typed primary entries | Gap rows | Current raw route      |
| ---------- | ------------------: | ------------: | --------------------: | -------: | ---------------------- |
| BSD        |                 455 |           455 |                    36 |      419 | nonnegative `Raw.call` |
| Mach traps |                  62 |            62 |                     8 |       54 | negative `Raw.call`    |
| machdep    |                  11 |             7 |                     0 |       11 | unsupported            |
| diagnostic |                   5 |             1 |                     0 |        5 | unsupported            |
| **Total**  |             **533** |       **525** |                **44** |  **489** | —                      |

Logical rows, not distinct numbers, are the primary-entry review backlog. The
five x86-64 diagnostic operations share one encoded selector. Several machdep
slots also have architecture-specific meanings. Collapsing those rows would
discard the identity that an implementation must review.

The history archive is
`darwin-xnu-syscall-history-first-pass.zip`, SHA-256
`d6324bdc100c65f94396e2458b3f2dbe199d2fcc2e18d6c1cfd05f9fab94ee16`.
It contains four labelled source snapshots and 3,233 normalized historical rows.
Its latest export is labelled `xnu-12377.121.6`, but the ZIP comment on that
export's source input identifies earlier commit
`f6217f891ac0bb64f3d375211650a4c1ff8ca1ea`. Exactly three reviewed files match
the labelled tag byte for byte: the BSD table, x86 machdep table and x86
diagnostic header. The Mach table, ARM trap header and implementation, x86
diagnostic implementation and both `proc_info` headers differ.

The Native-Kernel generator therefore requires an exact source tree for commit
`ac9718fb1af618d5ce8678d0dc6e8a58f252216f`. Its tracked source manifest admits
99 files, including every one of the 85 `.defs` files, before parsing. The
generator replaces the Mach, ARM platform and x86 diagnostic rows from that
tree. This changes the all-status row count from 843 to 845: Mach slot 63 has
separate LP64 and non-LP64 variants, and the exact diagnostic header declares
`dg64`, which the history export omitted. The active LP64 Mach row has three
arguments, five argument words and `munge_wll`; the history export had recorded
an unconditional two-argument row. Active logical counts remain unchanged.
Inactive and declared-only rows remain history and compatibility evidence, not
the default implementation queue.

The five active x86-64 diagnostics now carry exact implementation lines and
hashes. `dgGzallocTest` and `dgPermCheck` exist only under
`DEVELOPMENT || DEBUG`; source catalog membership does not make them available
in a production kernel.

Two active rows retain upstream parser warnings: BSD 501 (`necp_open`) and BSD
522 (`necp_session_open`) each report an extra closing brace after the parsed
prototype. Their number and name remain useful inventory evidence, but the
prototype must be checked against the pinned source before either is
implemented.

## Completeness boundary

The primary CSV is complete only relative to the five dispatch source groups
used for `xnu-12377.121.6`: BSD `syscalls.master`, the exact Mach trap table,
x86 and exact ARM64 machdep/platform calls, and x86 diagnostics. The bundle's
shipped output verifier and all 16 of its tests passed locally on 2026-11-12,
but that verifier only established exact-tag identity for `syscalls.master`.
The Native-Kernel generator's admitted exact-source overlay reproduced all 533
active logical rows and the exact 489-row complement.

That evidence does **not** establish a complete Darwin operation landscape.
The following remain separate, unfinished inventories:

- secondary commands, flavors, flags and record-embedded selectors reached by
  BSD syscall handlers;
- Mach Interface Generator messages and their subsystem routine IDs;
- Mach task, thread, host, port, voucher, clock, semaphore and exception
  flavors carried by those messages;
- `sysctl` MIBs, including runtime-registered nodes;
- `ioctl`, `fsctl` and device-specific request codes and payload layouts;
- IOKit user-client external methods, which vary by service and hardware;
- commpage and library-mediated kernel facilities that are not dispatch-table
  entries;
- preprocessor configurations and XNU releases outside the four reviewed
  snapshots; and
- native availability, entitlement, sandbox and protected-target behavior.

Some of those spaces are not finite for “all macOS systems”: drivers and kernel
components can register host-specific control nodes or device operations. They
need a core-XNU catalog plus provider-specific extensions, not one universal
number table.

The generated selector-candidate CSV is an audit queue for the next layer. It
contains 218 active BSD rows whose prototypes have selector-like scalar
parameter names such as `cmd`, `operation`, `flavor`, `flags`, `which`, `how`,
`prot` or `com`. It is deliberately heuristic: it can include ordinary scalar
values, and it cannot see selectors hidden in pointed-to records or handler
bodies. The current XNU dataset does not provide Mach trap argument prototypes,
so that CSV makes no secondary-Mach completeness claim.

Regenerate or check the tracked inventory with:

```sh
python3 scripts/catalog/darwin_syscall_inventory.py \
  --archive /path/to/darwin-xnu-syscall-history-first-pass.zip \
  --latest-xnu-root /path/to/xnu-12377.121.6

python3 scripts/catalog/darwin_syscall_inventory.py \
  --archive /path/to/darwin-xnu-syscall-history-first-pass.zip \
  --latest-xnu-root /path/to/xnu-12377.121.6 \
  --check
```

## A syscall number is only the outer catalog

Many high-value entries are multiplexers. `proc_info` is one BSD syscall, but
its call numbers, flavors, filters, comparison flags and result records are
separate operation catalogs. The same is true of `fcntl`, `sysctl`, `ioctl`,
Mach messaging and several process-policy calls. Counting only primary entries
therefore understates both implemented behavior and remaining work.

The following table is the first prioritized catalog-unit register, not an
exhaustive universe. “Partial” means Native-Kernel has only the values needed
by its present wrappers. It does not mean that the upstream catalog has been
inventoried completely. The 218-row candidate CSV is the broader mechanical
queue from which this register must be expanded.

| Catalog unit                                                         | Current state                                                                              | Priority           | Required next result                                                                   |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ------------------ | -------------------------------------------------------------------------------------- |
| BSD syscall numbers                                                  | 36 typed entries use literals; all 455 active rows are now inventoried                     | now                | introduce symbols for implemented entries, then review gaps one operation at a time    |
| Mach trap selectors                                                  | 8 typed entries use literals; all 62 active rows are now inventoried                       | now                | introduce symbols for implemented traps; do not flatten Mach returns into BSD errno    |
| machdep calls                                                        | source inventory only; raw entry family unsupported                                        | defer              | add an architecture-specific raw contract before considering public names              |
| diagnostic operations                                                | source inventory only; raw entry family unsupported                                        | defer              | require a concrete debugging consumer and native safety model                          |
| `proc_info` call numbers                                             | all 20 exact call numbers catalogued; list, PID info, PID usage and audit-token signal implemented | process-next | review each remaining call's availability, authority and output contract               |
| process list types, PID flavors and comparison flags                 | 94 selected exact call/flavor/action/flag rows catalogued; 14 issued symbols have source/spec witnesses | process-next       | map every admitted flavor to an exact record prefix, size rule and identity guarantee  |
| wait ID types, wait options and status interpretation                | wrappers accept integers; terminal `CLD_*` codes are partial                               | process-next       | name supported selectors and record collection, stop/continue and retry semantics      |
| credential and group selectors                                       | primary entries are unimplemented                                                          | process-next       | start with read-only real/effective UID, GID and supplementary-group queries           |
| priority, rlimit and usage selectors                                 | `RUSAGE_SELF` and `RUSAGE_CHILDREN` only; limit kinds remain unnamed                       | process-next       | name queried resources before adding priority or cross-process limit controls          |
| signal numbers, mask operations and action flags                     | `CLD_*` result codes only                                                                  | process-next       | separate signal identity, mask operation, action flag and delivery policy catalogs     |
| `fcntl` commands and command argument shapes                         | generic integer command only                                                               | consumer-triggered | give each supported command a typed argument and ownership contract                    |
| kqueue filters, event flags and filter-specific `fflags`             | six process-exit values only                                                               | process-next       | catalog process filters separately from descriptor and timer filters                   |
| spawn flags, attribute fields and file-action tags                   | restricted Darwin 21/24/25 profile only                                                    | process-next       | keep each admitted layout and action subset versioned and natively qualified           |
| Mach message IDs, options, dispositions, rights and descriptor kinds | 52 subsystem sources mapped, including 49 production and three test-only sources; 37 have kernel-build roles and 17 have libsyscall export roles, but per-routine ABIs remain unparsed | process-next | split transport, MIG operation, right ownership and reply validation catalogs          |
| Mach task/port/host flavors and result codes                         | task audit and port names only                                                             | consumer-triggered | add a flavor only with its exact request/reply record and cleanup path                 |
| `sysctl` MIBs                                                        | release query uses literal `CTL_KERN/KERN_OSRELEASE` values                                | consumer-triggered | name only admitted MIB paths and distinguish read-only from mutating nodes             |
| socket domains, types, protocols, options and message flags          | generic integer parameters only                                                            | consumer-triggered | add by a concrete IPC/network consumer, not as one undifferentiated constant bag       |
| memory protection, mapping and advice flags                          | no typed Darwin VM/mmap surface beyond Mach deallocation                                   | consumer-triggered | decide BSD mapping versus Mach VM ownership before naming flags                        |
| `ioctl` request codes and payload records                            | absent                                                                                     | consumer-triggered | catalog per device family because request numbers alone do not define payload ABI      |
| `ptrace` requests                                                    | syscall absent                                                                             | defer              | require a debugger contract, privilege model and stopped-target state machine          |
| `csops` operations and code-signing flags                            | syscalls absent                                                                            | process-next       | begin with read-only audit-token-bound queries and exact output sizes                  |
| process-policy, I/O-policy and rlimit-control selectors              | syscalls absent                                                                            | consumer-triggered | require a policy owner and release-specific source/native evidence                     |
| audit-session operations                                             | syscalls absent                                                                            | consumer-triggered | keep audit session identity distinct from process identity and credentials             |
| coalition and memorystatus operations                                | private multiplexers absent                                                                | defer              | require an explicit containment/resource-policy design and release admission           |
| filesystem controls and attribute bitmaps                            | `ioctl`, `fsctl`, `ffsctl`, attrlist, xattr, pathconf, mount and quota catalogs unreviewed | consumer-triggered | separate global filesystem flags from command-specific payload ABIs                    |
| memory policy and mapping selectors                                  | protection, mapping, sync, inheritance and advice catalogs unreviewed                      | consumer-triggered | distinguish BSD VM calls, Mach VM calls and record-embedded flags                      |
| SysV IPC, POSIX AIO and timer selectors                              | command/mode catalogs unreviewed                                                           | defer              | require a concrete consumer and exact cancellation/ownership rules                     |
| pthread, workqueue, psynch and ulock operations                      | private synchronization selectors unreviewed                                               | defer              | keep Crystal runtime mechanisms outside the public surface without a consumer          |
| NECP, nexus and channel actions/options                              | private networking control catalogs unreviewed                                             | defer              | require provider-specific records and release admission                                |
| guarded descriptors and payload-reason namespaces                    | guard flags, reason namespaces/codes and payload formats unreviewed                        | consumer-triggered | model ownership and irreversible failure paths before constants                        |

The primary CSVs answer “what entries did the reviewed XNU dispatch-table
parser find?” This table answers “which named operation spaces have already
been recognized as decision units?” Neither proves that every operation space
has been found or promises to expose every upstream constant.

## Tranche-2 secondary-operation queue

The [tranche-2 evidence intake](darwin-syscall-advice-intake.md#evidence-generation-2--tranche-2)
adds bounded runtime observations to the following named-operation queues. It
does not change the 533 active primary rows, 44 typed primary entries or 489
gap rows, and it does not turn a successful C probe into a public support
guarantee.

- BSD 488 `renameatx_np`: `RENAME_SWAP`, `RENAME_EXCL` and their invalid
  combination;
- BSD 363 `kevent`: `EVFILT_VNODE` opened-object identity across replacement,
  with only source-corroborated relevance to BSD 369 `kevent64`;
- BSD 75 `madvise`: `MADV_FREE` mapping validity and discardable contents;
- BSD 92 `fcntl` and BSD 95 `fsync`: `F_BARRIERFSYNC` and `F_FULLFSYNC`
  availability/results, without a durability claim;
- BSD 92 `fcntl`: `F_OFD_SETLK` versus `F_SETLK` ownership lifetime;
- the composed `forkpty` path: session, process group, controlling terminal,
  foreground group and descriptor postconditions, without a synthetic syscall
  row;
- BSD 447 `connectx`: `CONNECT_RESUME_ON_READ_WRITE` on bounded loopback; and
- Mach message transport observed through libSystem `mach_msg`:
  `MACH_SEND_TIMED_OUT`, `MOVE_SEND` pseudo-receive and returned-header/right
  ownership. Raw trap slots `-31`/`-47` are source-mapped but were not both
  runtime-exercised by that probe.

These remain review queues. Exact-source reconstruction, Crystal artifact
auditing and source-bound native execution are separate gates before a row can
change Native-Kernel's typed or behavior-qualified surface.

## Gates for a stronger completeness claim

Do not describe the named-operation inventory as complete until all of these
have a pinned source, generated inventory and reviewed exceptions:

1. every relevant outer dispatch table in the admitted XNU source profile;
2. every active BSD handler's scalar selectors and selector-bearing records;
3. every admitted Mach `.defs` subsystem, routine ID and request/reply ABI;
4. SDK-visible constants reconciled with private XNU-only definitions;
5. core `sysctl`, `ioctl`, `fsctl` and IOKit registries separated from dynamic
   provider extensions;
6. commpage and library-mediated operations explicitly included or excluded;
7. architecture and release differences represented without collapsing
   conditional variants; and
8. a native evidence matrix that keeps “catalogued” separate from “callable,”
   “typed,” and “behavior-qualified.”

Even after those gates, the defensible claim is bounded: complete for named
sources, release profiles and providers. “Nothing is missing from Darwin” is
not a supportable claim.

## Process-Control order of work

The next process work should favor observation and identity before mutation.
The XNU names and slots below are from the complete active inventory.

### First: deepen the existing process multiplexer

Review the remaining `proc_info` call numbers and flavors before adding many new
top-level syscalls. The existing slots 336 (`proc_info`) and 545
(`proc_info_extended_id`) already support process listing, BSD/task records,
usage records and identity-checked reads. A full secondary catalog can expose
more observation while retaining one entry ABI and a consistent checked-PID
model.

The deliverable is not a list of constants alone. Every admitted combination
needs its input selector, exact output record and copied size, return-unit rule,
minimum Darwin profile, identity guarantee and native fixture.

### Second: read-only credentials and scheduling identity

Review this coherent query set together:

| BSD slot | XNU name      | Why it belongs together                                              |
| -------: | ------------- | -------------------------------------------------------------------- |
|       24 | `getuid`      | real user identity                                                   |
|       25 | `geteuid`     | effective user identity                                              |
|       43 | `getegid`     | effective group identity                                             |
|       47 | `getgid`      | real group identity                                                  |
|       79 | `getgroups`   | variable-length supplementary groups                                 |
|      100 | `getpriority` | scheduling observation with special return/error rules               |
|      327 | `issetugid`   | credential-transition state, not a replacement for credential values |

These are stateless Native-Kernel mechanisms. Process-Control decides when a
snapshot is meaningful and whether it is attached to the current process or a
retained target identity. Mutating companions such as `setuid`, `setgroups`
and `setpriority` should follow only when a consumer owns irreversible-change
and partial-failure policy.

### Third: authenticated or privilege-sensitive target observation

These candidates are valuable but need more design than a raw wrapper:

| Family/slot | XNU name                     | Required decision before implementation                                     |
| ----------- | ---------------------------- | --------------------------------------------------------------------------- |
| BSD 170     | `csops_audittoken`           | operation catalog, token binding, output size and protected-target behavior |
| BSD 538     | `task_inspect_for_pid`       | entitlement/privilege matrix and returned-right ownership                   |
| BSD 539     | `task_read_for_pid`          | entitlement/privilege matrix and returned-right ownership                   |
| Mach 45     | `task_for_pid`               | whether full task control is in scope at all                                |
| Mach 46     | `pid_for_task`               | identity strength and right validation                                      |
| Mach 96     | `debug_control_port_for_pid` | debug entitlement and caller-owned right cleanup                            |

Native compilation or same-user success is not enough evidence for these. Each
needs protected-target, foreign-credential and denial-path results on every
admitted release profile.

### Fourth: target mutation only behind identity policy

BSD slots 433 (`pid_suspend`), 434 (`pid_resume`) and 446
(`proc_rlimit_control`) are plausible Process-Control mechanisms. A bare PID is
reuse-prone, however. Native-Kernel may expose the stateless operation after its
ABI is audited; Process-Control should not offer a checked control method until
it can prove the target identity immediately before the mutation or explicitly
document the weaker contract.

`ptrace` (BSD 26), credential mutation, process-policy/I/O-policy operations,
coalitions and memorystatus belong after this boundary is settled. They carry
debugger state, privilege, irreversible credential change or private policy
semantics that a syscall number cannot express.

## Decision record for each implemented operation

Before moving a gap row from `unreviewed` to implemented, record all of:

1. the primary entry and every secondary selector the wrapper admits;
2. public SDK, public XNU, private XNU or architecture-private provenance;
3. architecture and Darwin-major availability, including changed signatures;
4. exact argument widths, copyin/copyout records, result registers and units;
5. ownership of descriptors, ports, VM, buffers and partial outputs;
6. PID/task/audit-token identity strength and PID-reuse exposure;
7. interruption, restart, cancellation and partial-success behavior;
8. credentials, entitlements, sandbox and protected-target behavior;
9. the Native-Kernel stateless boundary and the Process-Control policy owner;
10. source, compile, native success and native refusal evidence needed to ship.

A choice to defer is also a decision. Mark it with the missing consumer or
safety contract rather than leaving an attractive integer available through a
misleading typed name.

## Coverage meanings

- `typed_wrapper`: at least one typed Native-Kernel method reaches this primary
  entry. It does not imply every secondary operation or behavior is covered.
- `raw_entry_only`: the existing BSD/Mach assembly can mechanically issue the
  selector, but Native-Kernel has no typed method or symbolic primary constant.
- `unsupported_entry_family`: the latest XNU row belongs to machdep or the
  diagnostic gate, neither of which the current raw contract can dispatch.
- `literal_only`: an implemented primary selector is still written as a number
  in source. The namespace plan describes its future symbol but does not make
  that symbol present.
- `named`: every discovered call site for that implemented primary entry uses
  its `Syscall::Number` or `Mach::Trap` symbol. `mixed` marks a migration in
  which named and literal call sites coexist.
- `unreviewed`: no API, support or qualification decision has been made. It is
  not shorthand for safe, stable or useful.

Raw reachability, named catalog coverage, typed wrapper coverage and native
behavior qualification are four different measures. Report them separately.
