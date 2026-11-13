# Darwin Syscall Advice tranche 2 intake plan

Plan date: 2026-11-12.

## Purpose

Use this plan to admit the second `syscall-advice` Darwin verification tranche
as bounded Native-Kernel evidence, map its named operations into the existing
Darwin audit queue, and add an unmanaged Mach send-timeout qualification case.
Execute the phases in order. A phase is complete only when its exit checks pass.

This plan does not authorize a new public Native-Kernel API, a support-floor
change, a commit, a push, or changes to Process-Control, PTY, Filesystem or
networking shards.

## Use this plan when

Use this plan when implementing the Native-Kernel intake for the exact tranche-2
artifacts listed below, or when resuming that implementation after a recorded
blocked/unrun result.

Do not use this plan to:

- ingest a different Skill bundle or probe manifest;
- design a general Mach message API;
- qualify Process-Control, PTY, File-Lock, Filesystem or networking behavior;
- lower a Darwin support floor; or
- regenerate the primary syscall inventory from a newer XNU snapshot.

For a different bundle or source revision, create a new dated intake plan and
preserve this plan's evidence identities as historical inputs.

## Completion definition

The plan is complete when all of the following are true:

1. Native-Kernel records the exact new Skill, probe manifest, report and
   verifier identities without erasing the predecessor evidence.
2. Each of the eight tranche-2 observations has an explicit primary-operation,
   secondary-operation and consumer disposition.
3. Generated syscall inventory rows remain source-derived; runtime observations
   do not change implementation coverage or primary-row counts.
4. A separate unmanaged Crystal case passes every required source, artifact and
   disposable-host runtime gate for each newly claimed native profile. If the
   fixture work is blocked, completed intake phases may be reported as partial
   results, but this plan is not complete.
5. Native-Kernel and Process-Control checks pass for the changed source, and
   every unrun host/profile remains named.

## Execution contract

Before editing:

1. Read the workspace and Native-Kernel `AGENTS.md` files, `README.md`,
   `docs/support.md`, `docs/darwin-syscall-advice-intake.md` and
   `docs/darwin-syscall-landscape.md`.
2. Record branch, HEAD and full working-tree status.
3. Treat all pre-existing changes as user work. Stop if they overlap an owned
   output and their relationship to this plan is unknown.
4. Verify every artifact in [Inputs](#inputs). Do not continue with an artifact
   whose bytes disagree with the recorded hash.

Tool rules:

- use the workspace code graph for code-symbol discovery and call/impact
  tracing;
- use `rg` for exact strings, JSON/configuration fields and documentation;
- use `apply_patch` for repository edits;
- use read-only Git commands until the user separately authorizes a commit; and
- use only external scratch directories and external `CRYSTAL_CACHE_DIR`
  values for builds and receipts; and
- invoke standalone Python checks with `-B` or
  `PYTHONDONTWRITEBYTECODE=1`; ignored repository-local bytecode is still an
  unintended output.

If a graph result is absent or stale, confirm the live file before acting. A
search hit, generated row or Skill statement is discovery evidence, not source
authority.

During execution:

- keep all Skill bundles, reports, XNU checkouts, compiler caches and runtime
  receipts outside the repository;
- do not copy implementation code from the Skill or XNU into shipped source;
- reproduce source claims from the exact Native-Kernel XNU profile before using
  them as source evidence;
- keep public contract, SDK/header evidence, exact-source behavior, runtime
  observation and probe-internal behavior as separate evidence classes;
- preserve every failure, skip, unsupported profile and unrun lane;
- do not weaken an expectation to make a probe pass;
- do not add a typed API solely because a C or fixture probe succeeds; and
- do not commit or push unless the user separately requests it.

When evidence conflicts, apply this precedence:

1. workspace and shard instructions;
2. admitted exact XNU and SDK/header bytes for the claimed source profile;
3. independently reproduced native runtime observations on exact probe bytes;
4. source-scoped Skill guidance and probe expectations;
5. third-party consumer precedents.

A higher-precedence disagreement does not erase lower-precedence evidence.
Record both scopes and stop before making a broader claim.

## Inputs

Required external deliverables directory:

`/Users/immateria/Downloads/syscall-advice-darwin-verification-tranche2-fixed`

| Artifact | SHA-256 |
| --- | --- |
| `skill.zip` | `107b21e8bc6e58572a7285f4d270fdb6f5f069ca6910b5ef597e907f55f5cb5f` |
| `macos-probes-final.json` | `281af17dc88c19200e466270801ddc7451cc6de79f71a6fbaaf8b16969063774` |
| `macos-probes-final-verifier.json` | `c54a47c65231b6c6475fbb61fca248390fa04f80e245fafa86f5001c0ec7162b` |
| `macos-probes-fixed.json` | `cde2365b0fa2a00fe38427bc4f91c0c4e5239b57cee81de4148cb385455ce89d` |
| `macos-probes-failures-unsandboxed.json` | `af9377d3d54a807b31832ca70f078adc60a0d9cb87466679c4e562811719db2e` |
| `macos-probes-mach-fixed.json` | `7b98c47f4d8c387c2346abcadf73358b7885786046a92606157b5935c8925a56` |
| `findings.md` | `d31567c312694f8f33b6eca65a0ff78bdf7c89d2f85c4cb5364e9a4759a7770d` |

Required identities inside `skill.zip`:

| Artifact | SHA-256 |
| --- | --- |
| `probes/manifest.json` | `c435944a868d13153e0ac29af92e2d27591145e2835f3027aba035322d77ccf3` |
| `evidence/probe-source-digests.json` | `1825caca94ff808f8521e71575239660b747261a8b77bfc17c24573dd1a35a8a` |
| `probes/darwin_mach_send_timeout_probe.c` | `1af775a0515a3f60784a17fc11de41602bd650d5f5c0a685bc36f97368bbb5f6` |

The final report records 33 passes, zero skips and zero failures on native arm64
macOS 15.4.1 build 24E263, Darwin 24.4.0, SDK 15.4, Apple Clang 17.0.0 and
Node 26.0.0, with `sysctl.proc_translated=0`. This is runtime observation for
that host and those bytes only.

Required exact XNU source profile:

- repository: `https://github.com/apple-oss-distributions/xnu`;
- tag: `xnu-12377.121.6`;
- commit: `ac9718fb1af618d5ce8678d0dc6e8a58f252216f`.

The plan-time Native-Kernel baseline is `470b02d0b18e9484e46bc6bf6a4078effe42c474`
on `main`. A moved HEAD is not automatically a blocker. Inspect all intervening
changes before execution.

Assumptions:

- the listed deliverables remain readable at their recorded paths;
- an external checkout or extraction of the exact XNU commit can be supplied;
- a disposable native arm64 macOS VM or hosted runner, plus a supervisor outside
  that guest/job, can be supplied for the first execution of the integrated raw
  Mach fixture; and
- commit, push and hosted-CI publication remain separate user decisions.

If an assumption is false, apply [Blocked behavior](#blocked-behavior) to the
affected phase. Do not substitute a newer artifact, moving source branch or
cross-compile result.

## Evidence boundaries

The final Skill report establishes only the observed C probe outcomes on the
recorded host. It does not establish:

- Native-Kernel Crystal ABI correctness;
- Intel, Rosetta or Darwin 21 behavior;
- public support for private/source-reviewed interfaces;
- power-loss durability;
- behavior under another sandbox, entitlement set, SDK or filesystem; or
- complete Mach descriptor/out-of-line pseudo-receive restoration.

The first sandboxed post-repair report remains evidence. Its five loopback,
notify and PTY failures were environmental because the exact focused probes
passed outside that sandbox. Its Mach failure was probe-internal: the cleanup
receive buffer omitted trailer space. Do not describe those reports as an
untouched baseline or an operating-system behavior change.

An adversarial feasibility trial also exposed a host-safety boundary. Its first
raw Mach prototype used invalid trap `-17` and packed the `mach_msg2` timeout in
the priority word. That process remained adopted by PID 1 in kernel state `UE`
after `SIGKILL`. A corrected scratch prototype subsequently passed, but it does
not qualify the future integrated fixture or erase the failed prototype. The
integrated fixture's first execution must therefore occur on a disposable
macOS host after source review, static artifact inspection and import auditing,
not on a long-lived workstation.

## Owned outputs

The implementation may change only these paths without a new scope decision:

- `docs/darwin-syscall-advice-intake.md`;
- `docs/darwin-syscall-advice-tranche2-plan.md`;
- `docs/darwin-syscall-landscape.md`;
- `docs/darwin-catalog-sources.md` when exact new source evidence is admitted;
- `spec/native/behavior.cr`;
- a focused new file under `spec/native/behavior/` for the Mach case;
- `ci/cases.json`;
- `scripts/ci/runner.py`;
- `tests/test_ci_runner.py`;
- `docs/support.md` and `docs/ci-results.md` only after corresponding native or
  hosted evidence exists; and
- `ci/coverage.json` only if an existing typed operation gains a truthful new
  positive case.

Do not edit generated `docs/data/darwin-*.csv` or
`docs/data/darwin-syscall-inventory.json` by hand. Do not mark a primary entry
implemented because a raw C or Crystal probe exercised it. Do not add a public
constant or method under `src/` in this work.

## Operation mapping

Use this mapping as the required tranche-2 disposition:

| Probe | Primary operation | Named/secondary operation | Native-Kernel disposition |
| --- | --- | --- | --- |
| `darwin-renameatx-contracts` | BSD 488 `renameatx_np` | `RENAME_SWAP`, `RENAME_EXCL` and their invalid combination | Record runtime evidence in the secondary flags queue; no wrapper. |
| `darwin-vnode-replacement` | BSD 363 `kevent` | `EVFILT_VNODE` opened-object identity across replacement | Record event-lifecycle evidence; do not claim pathname-watch semantics. Its relevance to BSD 369 `kevent64` is source corroboration, not direct runtime qualification. |
| `darwin-madv-free` | BSD 75 `madvise` | `MADV_FREE` mapping validity and discardable contents | Record VM selector evidence; no content-preservation claim. |
| `darwin-sync-commands` | BSD 92 `fcntl` plus BSD 95 `fsync` | `F_BARRIERFSYNC`, `F_FULLFSYNC` | Record command availability/results; no durability claim. |
| `darwin-lock-lifetime` | BSD 92 `fcntl` | `F_OFD_SETLK` versus `F_SETLK` ownership lifetime | Record command/lifetime evidence; leave lock policy to File-Lock/Filesystem consumers. |
| `darwin-pty-controlling-terminal` | composed library/kernel path | `forkpty`, session, group, `/dev/tty`, foreground group and descriptor postconditions | Record consumer evidence only; no synthetic `forkpty` syscall row. |
| `darwin-connectx-deferred` | BSD 447 `connectx` | `CONNECT_RESUME_ON_READ_WRITE` | Record loopback observation; no general network or early-data claim. |
| `darwin-mach-send-timeout` | libSystem `mach_msg` transport; raw trap slots `-31`/`-47` are source-mapped but were not both runtime-exercised | `MACH_SEND_TIMED_OUT`, `MOVE_SEND` pseudo-receive, returned header/right ownership | Add to the Mach ownership queue and qualify with a separate unmanaged Crystal case. |

## Delegable work packets

These packets may be assigned independently to a faster implementation agent.
They deliberately exclude Mach message construction, ownership-state design,
failure-path cleanup, raw fixture execution and native-result interpretation.
Packets A, C and D may run in parallel only when D uses an isolated worktree or
is the sole writer in this checkout. Packets B and E edit documentation and must
not run concurrently with another writer touching the same files.

Every delegated agent must:

1. read the workspace and Native-Kernel `AGENTS.md` files;
2. record branch, HEAD and full initial status before acting;
3. preserve all pre-existing modified, staged, untracked and ignored files;
4. change only the packet's owned paths;
5. keep caches, extracted archives, receipts and command logs outside the
   repository;
6. invoke standalone Python with `-B` or `PYTHONDONTWRITEBYTECODE=1`;
7. stop on an identity mismatch, unexplained overlapping edit or instruction
   ambiguity instead of widening scope;
8. not run `scripts/ci/runner.py qualify`, `replay`, the new Mach fixture or any
   ad hoc raw Mach experiment;
9. not edit generated `docs/data/` outputs, public `src/` files, workflows,
   Process-Control or another shard;
10. not commit, push, fetch, install dependencies or delete files; and
11. return changed paths, commands with exit status, external evidence paths,
    exact failures/unrun checks and final status relative to the initial status.

### Packet A: Authenticate artifacts and record the baseline

**Purpose:** Execute Phase 0 without editing repository files.

**Prerequisite:** Run this packet before any tranche-2 implementation edit. If
the new Mach behavior fixture already exists in the checkout, stop and request a
fresh baseline checkout rather than treating the changed tree as the baseline.

**Owned outputs:** A fresh external directory only. Create it with:

```sh
NK_T2_PHASE0="$(mktemp -d /private/tmp/native-kernel-tranche2-phase0.XXXXXX)"
print -r -- "$NK_T2_PHASE0"
```

Record the returned absolute path as `NK_T2_PHASE0`. Do not reuse a previous
directory.

**Required actions:**

1. Recompute every top-level hash in [Inputs](#inputs). Write the complete
   comparison, including expected and observed values, to
   `NK_T2_PHASE0/hashes.txt`.
2. Before extraction, inspect every ZIP entry. Reject duplicate names, absolute
   paths, any `..` path component, backslash-separated paths and Unix symlinks.
   Write the entry count and every rejection reason to
   `NK_T2_PHASE0/zip-safety.json`. Do not execute bundle contents during this
   check. Use Python's standard `zipfile` metadata and the Unix mode in
   `ZipInfo.external_attr`; a filename-only listing is insufficient for the
   symlink check.
3. Extract the accepted ZIP into `NK_T2_PHASE0/skill`, recompute every in-ZIP
   identity in [Inputs](#inputs), and append those comparisons to
   `NK_T2_PHASE0/hashes.txt`.
4. Run the packaged verifier against the original external
   `macos-probes-final.json`:

   ```sh
   node "$NK_T2_PHASE0/skill/syscall-advice/scripts/verify-macos-probe-report.mjs" \
     --report /Users/immateria/Downloads/syscall-advice-darwin-verification-tranche2-fixed/macos-probes-final.json \
     --require-all-darwin \
     --require-native-arm64
   ```

   Resolve the extracted top-level directory if the ZIP adds one enclosing
   folder; do not guess a different verifier. Preserve stdout, stderr and exit
   status separately.
5. Independently inspect the four retained reports and write their ordered
   `27/6 -> 5/1 -> 1/0 -> 33/0` counts, source digests and timestamps to
   `NK_T2_PHASE0/report-sequence.json`.
6. Run the existing Native-Kernel baseline only; the new Mach fixture must not
   exist or execute in this packet:

   ```sh
   PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
   CRYSTAL_CACHE_DIR="$NK_T2_PHASE0/crystal-cache" \
     make check RECEIPTS="$NK_T2_PHASE0/core-receipts"
   ```

   Preserve both command logs and exit statuses.
7. Confirm final repository status is byte-for-byte equivalent to initial
   status. Ignored bytecode or build output is a packet failure.

**Completion:** All identities match, ZIP safety passes, the verifier reports
exactly 33 passes/zero skips/zero failures, the report sequence matches, and
baseline commands reproduce. Otherwise return `Blocked: evidence identity` and
make no repository edit.

### Packet B: Append the tranche evidence documentation

**Prerequisite:** Packet A completed with no mismatch.

**Owned paths:**

- `docs/darwin-syscall-advice-intake.md`;
- `docs/darwin-syscall-landscape.md`.

**Required edits:**

1. Apply Phase 1 exactly. Preserve the predecessor evidence as its own dated
   generation.
2. Copy artifact hashes, host metadata and report counts only from Packet A's
   retained evidence. Do not recompute or normalize them while editing.
3. Add the eight rows in [Operation mapping](#operation-mapping) without
   changing their primary operation or disposition wording.
4. State the Skill and Native-Kernel XNU commit mismatch exactly as Phase 1
   requires.
5. Add only links and named secondary-queue entries to the landscape. Do not
   change the 533 active rows, 44 typed entries, 489 gaps or any generated file.

**Validation:**

```sh
git diff --check -- \
  docs/darwin-syscall-advice-intake.md \
  docs/darwin-syscall-landscape.md
git diff --name-only
git diff -- docs/data
```

The name-only output may contain pre-existing user paths plus the two owned
paths, but no new packet-owned path. The `docs/data` diff must be empty. Return
the two-file patch for review without committing it.

**Stop conditions:** Stop without editing if Packet A is incomplete, the
predecessor generation cannot be identified unambiguously, an owned file has an
unexplained overlapping edit or a requested statement would exceed the recorded
evidence.

### Packet C: Collect exact XNU byte receipts

**Purpose:** Perform the mechanical receipt portion of Phase 2. This packet does
not interpret source semantics.

**Owned outputs:** A fresh external directory only, created with:

```sh
NK_T2_XNU_RECEIPTS="$(mktemp -d /private/tmp/native-kernel-tranche2-xnu-receipts.XXXXXX)"
print -r -- "$NK_T2_XNU_RECEIPTS"
```

Use this exact existing checkout unless its identity check fails:

```sh
XNU_ROOT=/tmp/native-kernel-github-reference.T4BcoZ/xnu-12377.121.6
GIT_NO_LAZY_FETCH=1 git -C "$XNU_ROOT" remote get-url origin
GIT_NO_LAZY_FETCH=1 git -C "$XNU_ROOT" rev-parse HEAD
GIT_NO_LAZY_FETCH=1 git -C "$XNU_ROOT" rev-parse 'xnu-12377.121.6^{}'
GIT_NO_LAZY_FETCH=1 git -C "$XNU_ROOT" status --short
```

**Required actions:**

1. With lazy fetching disabled, record the checkout origin, HEAD, peeled
   `xnu-12377.121.6` tag and status. Require HEAD and the peeled tag to equal
   `ac9718fb1af618d5ce8678d0dc6e8a58f252216f`, the origin to equal the XNU URL
   in [Inputs](#inputs), and status to be empty.
2. Hash every file under [Phase 2's required exact-source
   files](#required-exact-source-files), preserving its repository-relative
   path. Write machine-readable JSON and a plain-text SHA-256 list.
3. Confirm every path with `git -C "$XNU_ROOT" ls-files --error-unmatch -- PATH`
   before hashing it. Record missing, unmaterialized or mismatched paths as
   failures; do not fetch or substitute a neighboring release.
4. Recheck HEAD and status after reading. They must match the initial receipt.

**Completion:** Return only source identity and byte receipts. Do not derive
constants, MIG layouts, call paths, ownership rules or API conclusions. Those
remain expert work in Phase 2.

### Packet D: Enforce ordered origin case rosters

**Purpose:** Fix the independent runner-contract defect without adding the new
Mach case.

**Owned paths:**

- `scripts/ci/runner.py`;
- `tests/test_ci_runner.py`.

**Exact change:** In `validate_origin_proof`, replace the set-only origin case
check with an ordered comparison for each optimization mode:

```python
observed_ids = [result.get("case") for result in observed]
if observed_ids != list(CASE_IDS):
    raise QualificationError("Origin case roster is incomplete, duplicated, or reordered")
```

Remove the old length/set conditional rather than retaining a redundant branch;
ordered equality rejects omissions, duplicates and extras. Leave the following
unchanged in this packet:

- `CASE_IDS`;
- `ci/cases.json`;
- behavior fixtures and case output contracts;
- receipt schema and profile definitions.

Extend `test_origin_proof_requires_full_stages_and_native_host`. Save a deep
copy of its valid `origin["cases"]`, then separately prove rejection when the
development slice is reversed, the release slice is reversed, one position is
replaced with a duplicate case and one case is omitted. Restore the saved list
between mutations and call `validate_origin_proof` once more at the end to prove
the restored origin still passes.

**Validation:**

```sh
python3 -B -m unittest \
  tests.test_ci_runner.RunnerContractTests.test_origin_proof_requires_full_stages_and_native_host \
  -v
python3 -B -m unittest discover -s tests -v
git diff --check -- scripts/ci/runner.py tests/test_ci_runner.py
```

If the focused dotted test name is changed while splitting the test, run every
new ordered-roster test explicitly before the full discovery suite. Do not run
native qualification. Return the two-file patch without committing it.

### Packet E: Transcribe completed qualification evidence

**Prerequisites:** Phases 3 and 4 completed outside this packet. Both compiler
receipts must pass, both external supervisor records must show normal driver
return and clean guest shutdown, and no deadline, forced teardown or ownership
uncertainty may remain.

**Owned paths:**

- `docs/darwin-syscall-advice-intake.md`;
- `docs/support.md` only for a passed existing profile;
- `docs/ci-results.md` only when the supplied receipt came from a real hosted
  run.

**Required edits:**

1. Transcribe exact receipt hashes, source hashes, host/build identity, compiler,
   optimization modes, ordered case results and supervisor-evidence hashes.
2. Label local disposable, hosted native, translated and unrun evidence
   separately.
3. Preserve every failed, incomplete, timed-out, forcibly torn down or missing
   result. Such a result cannot enter `docs/support.md` as qualification.
4. State that no public API or support floor changed.

**Validation:** Run `git diff --check` on the owned files, prove `docs/data` and
`src` have no packet diff, and compare final status with the recorded initial
status. Return the documentation patch and exact receipt paths for expert review
without committing it.

**Stop conditions:** Stop without editing if a receipt is incomplete, its source
identity differs from the implementation under review, a supervisor deadline or
forced teardown occurred, or the evidence class cannot be determined exactly.

Phase 2 semantic reconstruction, all of Phase 3, native/translated execution and
interpretation of failures remain non-delegable under this plan.

## Phase 0: Reproduce artifact identity and baseline

### Actions

1. Hash every file listed in [Inputs](#inputs).
2. Safely inspect `skill.zip`; reject absolute paths, `..` traversal and
   symlinks before extraction.
3. Extract to a fresh external directory.
4. Run the packaged macOS verifier against `macos-probes-final.json` with
   `--require-all-darwin --require-native-arm64`.
5. Confirm the report has exactly 33 current Darwin results and counts
   `pass=33`, `skip=0`, `fail=0`.
6. Inspect the four retained runtime reports. Record the five environmental
   failures and one corrected Mach probe defect without relabeling them.
7. Run Native-Kernel's current tests and record the baseline result before edits.

### Exit checks

- Every required hash matches.
- The packaged verifier passes against the final report.
- The historical failures have the classifications above.
- Native-Kernel's current tests reproduce their existing state.

If any check fails, stop and report `Blocked: evidence identity` with the
artifact, expected hash/result and observed hash/result.

## Phase 1: Append the evidence intake

### Actions

1. Keep the predecessor Skill/report table in
   `docs/darwin-syscall-advice-intake.md` as a dated evidence generation.
2. Add a separate tranche-2 table containing every identity in [Inputs](#inputs),
   the host/build/SDK/compiler metadata and the 33/0/0 result.
3. Record the sandboxed 27/6 run, unsandboxed focused 5/1 run, corrected Mach
   1/0 run and final 33/0 run as an ordered evidence sequence.
4. Add all eight rows from [Operation mapping](#operation-mapping) to the intake
   disposition table.
5. State that the Skill's XNU evidence at
   `f6217f891ac0bb64f3d375211650a4c1ff8ca1ea` is not the Native-Kernel exact
   inventory profile at `ac9718fb1af618d5ce8678d0dc6e8a58f252216f`.
6. Update `docs/darwin-syscall-landscape.md` only to link the new evidence and
   name the added secondary-operation queue items. Do not change primary counts,
   typed coverage or gap counts.

### Exit checks

- Both evidence generations remain identifiable.
- Every new claim names its evidence class and scope.
- The generated inventory is unchanged.
- No prose says that successful execution creates a public support guarantee.

## Phase 2: Reproduce the Mach ownership source contract

### Required exact-source files

Inspect these files at the exact XNU commit:

- `osfmk/mach/message.h`;
- `osfmk/mach/port.h`;
- `osfmk/mach/ndr.h`;
- `osfmk/mach/mig_errors.h`;
- `osfmk/mach/mach_port.defs`;
- `osfmk/kern/syscall_sw.c`;
- `osfmk/ipc/mach_msg.c`;
- `osfmk/ipc/ipc_kmsg.c`;
- `osfmk/ipc/mach_kernelrpc.c`;
- `osfmk/ipc/ipc_mqueue.c`;
- `osfmk/ipc/ipc_object.c`;
- `osfmk/ipc/ipc_right.c`; and
- `libsyscall/mach/mach_port.c`.

### Actions

1. Record external SHA-256 receipts for the exact bytes; do not add the checkout
   or full source files to the repository.
2. Reproduce the numeric values and message/header orientation for:
   `MACH_SEND_TIMED_OUT`, `MACH_SEND_TIMEOUT`, `MACH_MSG_TYPE_MOVE_SEND`,
   `MACH_MSG_TYPE_COPY_SEND`, `MACH_PORT_QLIMIT_DEFAULT`, send-right
   type/reference queries and receive trailer capacity.
3. Reproduce the raw entry and option contract before writing the fixture:
   task self `-28`, receive-right allocation `-16`, send-right release `-18`,
   right-reference modification `-19`, right insertion `-21`, reply-port
   allocation `-26`, legacy message trap `-31` and message2 trap `-47`. Confirm
   that trap `-17` is invalid in this profile and must not be used for cleanup.
   Record `MACH64_SEND_KOBJECT_CALL = 0x200000000` for the task RPC and
   `MACH64_SEND_MQ_CALL = 0x400000000` for the owned-queue send. Confirm that
   the `mach_msg2` timeout is a separate eighth argument, not the priority word.
4. Trace the pseudo-receive path that restores moved rights after the full-queue
   timeout. Keep the manual/public contract distinct from implementation detail.
5. Trace both failure classes for a `COPY_SEND` filler. A failure before
   successful copyin preserves only the original user reference. A failure
   after copyin can pseudo-receive the copied send right into the namespace and
   add a second user reference while the original remains owned. Record the
   exact source path and the evidence needed to distinguish those states.
6. Derive the fixture-local `mach_port_get_refs` request/reply layout from
   `mach_port.defs` and the exact generated/wrapper evidence. Do not guess a MIG
   message ID, request size, reply size, NDR field or count.
   Reproduce these audit baselines before admitting them:

   | Field | Expected value |
   | --- | --- |
   | Request ID | `3207` |
   | Reply ID | `3307` |
   | Request size | 40 bytes |
   | Success reply size | 40 bytes |
   | Ordinary MIG error reply size | 36 bytes |
   | NDR bytes | `00 00 00 00 01 00 00 00` |
   | Request payload | `UInt32 name`, `UInt32 right` |
   | Success payload | `Int32 return code`, `UInt32 refs` |

   The scalar result has no variable-array count field. Use a dedicated reply
   receive right and account for its ownership explicitly.
7. Derive the complete receive storage requirement. The bounded simple message
   is 28 bytes and the pinned native64 maximum trailer is 68 bytes, so declared
   capacity must be at least 96 bytes. Message size alone is insufficient.
8. Record the known unresolved path: descriptor/out-of-line pseudo-receive
   restoration can fail partially and may add `MACH_RCV_BODY_ERROR`. The bounded
   fixture does not qualify that path.

### Exit checks

- Every number and layout used by the proposed fixture has an exact-source or
  admitted SDK/header receipt.
- The source record distinguishes public contract, wrapper behavior and XNU
  implementation detail.
- No copied implementation body enters Native-Kernel.

If the exact `mach_port_get_refs` exchange cannot be independently reproduced,
stop before Phase 3 and report `Blocked: Mach reference accounting`. Do not
replace exact reference accounting with a weaker right-exists assertion.

## Phase 3: Add the unmanaged Mach timeout case

### Design

Add a dedicated behavior case named `mach-send-timeout`. Keep it separate from
the existing fixed task-info `Mach.read` exchange. The case must use
Native-Kernel raw/typed mechanisms only and must retain empty undefined-import
tables in development and release artifacts.

The case owns all resources. Represent task, destination receive, original
destination send, pseudo-received `COPY_SEND`, reply receive and `MOVE_SEND`
timeout ownership as separate explicit states. Preserve the primary result and
every cleanup result separately. A cleanup failure is a case failure, even when
the primary observation matched. Never release a name or reference whose
returned ownership has not been validated.

The case must:

1. acquire the caller task send reference through raw task-self trap `-28` and
   record that caller-owned reference for final release;
2. allocate one destination receive right through `-16` and insert exactly one
   send reference through `-21` with `MACH_MSG_TYPE_MAKE_SEND`;
3. allocate a dedicated reply receive right through `-26` for each bounded
   `mach_port_get_refs` exchange, validate its reply strictly and retire it
   through `-19` with receive-right delta `-1` on every applicable path;
4. record an exact initial destination send-right reference count of one;
5. fill the owned queue with exactly five, the reproduced
   `MACH_PORT_QLIMIT_DEFAULT`, zero-timeout `COPY_SEND` messages, requiring every
   filler send to succeed;
6. while the queue remains full, submit one controlled zero-timeout
   `COPY_SEND` message whose exact-source path reaches successful copyin before
   timing out, and require `MACH_SEND_TIMED_OUT`;
7. validate that the pseudo-received filler name equals the destination name and
   that its returned remote disposition is the received `PORT_SEND`/
   `MOVE_SEND` type, then require the send-right reference count to rise from
   one to two, tracking the second reference separately from the original
   reference;
8. release exactly that additional pseudo-received reference, require cleanup
   success and query the count back to one before continuing;
9. submit a 28-byte non-complex message with `MOVE_SEND` and zero send timeout;
10. require `MACH_SEND_TIMED_OUT` and distinguish this restoration path from an
   unexpectedly successful send, which consumes the send reference;
11. validate the returned remote name, require its send-right reference count
    to equal the pre-send count exactly and require its remote disposition to
    remain `MOVE_SEND` before treating that reference as restored;
12. receive one known filler message into at least 96 bytes of declared storage,
    covering the complete message and maximum trailer, then verify its ID/value;
13. release the validated restored destination send reference exactly once;
14. retire the destination receive right through `-19` with receive-right delta
    `-1`, causing the kernel to retire every still-queued filler message;
15. release every dedicated reply receive right and release the acquired task
    send reference last through raw send-right release `-18` or the existing
    source-equivalent `Mach.release` mechanism;
16. return a distinct bounded error code for each primary and cleanup
    postcondition; and
17. emit only the existing `NK_OK mach-send-timeout` success line through the
    behavior harness.

The failure-state contract is part of the design:

- every successful filler preserves the caller's original destination send
  reference and returns no additional user reference;
- a `COPY_SEND` failure before successful copyin leaves only the original user
  reference owned;
- a `COPY_SEND` failure after successful copyin can pseudo-receive an additional
  send reference while the original remains owned; the case must validate and
  track that returned reference separately before releasing it;
- if the filler failure stage or pseudo-receive result cannot be distinguished,
  preserve restoration uncertainty, do not guess a reference delta and fail the
  case so disposable-environment teardown contains any remaining ownership;
- an unexpectedly successful `MOVE_SEND` consumes that reference and must not
  enter timeout-restoration cleanup;
- a timed-out send authorizes restored-right cleanup only after the returned
  name, disposition and exact reference count are validated;
- a failed or malformed get-refs exchange does not authorize releasing an
  arbitrary returned name; and
- receive, RPC or teardown failure preserves its own result beside the primary
  result and fails the case.

Do not use raw trap `-17`; it is invalid in the admitted profile. Receive-right
reference removal through `-19` supplies queue teardown.

Do not add a generic public Mach send method. Do not call libSystem, allocate,
raise, use managed runtime state, or cache Mach names. Do not use an unbounded
queue-fill loop, infer the queue limit from timing, or use timing-only
synchronization. If the exact default-limit fill does not make the next send
time out, preserve the native result and fail the case; do not send additional
messages until a timeout appears.

### Files

1. Add a focused file under `spec/native/behavior/`.
2. Require and dispatch it from `spec/native/behavior.cr`.
3. Add `mach-send-timeout` to `scripts/ci/runner.py::CASE_IDS` and update the
   exact-roster error text.
4. Add its exact completion contract to `ci/cases.json` with
   `minimum_darwin: 24` until a separate native Darwin 21 result exists.
5. Extend `tests/test_ci_runner.py` so omitted, duplicated, reordered, skipped,
   timed-out or wrong-output results cannot qualify the expanded roster. Harden
   origin validation to compare the ordered case-ID sequence for each
   optimization mode against `CASE_IDS`; a set comparison is insufficient.
6. Change `ci/coverage.json` only if an existing typed operation is genuinely
   exercised more directly. Do not create a fictional typed operation merely
   to attach this case.

### Exit checks

- Both development and release behavior artifacts compile with the current and
  floor Crystal compilers.
- Reachable LLVM passes the existing exact assembly/import audit.
- Both linked artifacts have empty undefined-import tables.
- The case passes on native arm64 macOS 15.4.1 in both optimization modes on a
  disposable host.
- The controlled post-copyin `COPY_SEND` timeout proves the additional returned
  reference is observed, released exactly once and restored to the baseline
  count before the `MOVE_SEND` trial.
- Failure injection or focused mutants distinguish pre-copyin filler failure,
  post-copyin pseudo-receive and restoration uncertainty, and prove unexpected
  `MOVE_SEND` success, timeout restoration with failed reference query,
  malformed RPC reply, receive failure, cleanup failure and each ownership
  assertion can fail the case.
- Existing `Mach.read`, `Mach.port_name_count` and interruption cases remain
  unchanged and pass.

### First-execution safety gate

Before executing the newly integrated raw fixture:

1. complete the exact-source layout review in Phase 2;
2. use the source-bound qualification runner on a disposable native arm64
   macOS VM or separately authorized hosted runner;
3. require that runner to compile each development/release artifact, complete
   the reachable-LLVM audit and confirm an empty undefined-import table before
   invoking that artifact; and
4. refuse any path that executes an artifact before those checks pass.

An independent supervisor outside both the disposable guest and the
qualification-driver process is mandatory. For each `runner.py qualify`
command, it must:

1. create a fresh host-owned evidence directory containing
   `supervisor.jsonl`, `driver.stdout.log`, `driver.stderr.log`,
   `guest-console.log` and `provider-events.log`; record an unavailable stream
   explicitly rather than silently omitting it;
2. set and record a wall-clock deadline of no more than 45 minutes before
   launch; a stricter provider or workflow deadline is acceptable;
3. begin streaming driver stdout/stderr, guest console output and provider or VM
   lifecycle events to those paths before starting the guest command;
4. on normal driver return, record its status and independently confirm that no
   fixture process, descendant or adopted process remains;
5. on deadline expiry or lost guest control, record the supervisor-observable
   guest/VM state, mark qualification failed and forcibly stop and destroy the
   disposable environment; and
6. record completion and hash the retained supervisor evidence only after guest
   destruction or a separately evidenced clean guest shutdown.

The deadline handler, diagnostic capture and teardown path must remain runnable
without the guest's `qualify` process returning. After the deadline fires, they
must not call or join its Python `process.wait()`, depend on an in-guest cleanup
handler or await an in-guest log flush. Missing case logs after a forced teardown
are themselves preserved evidence, not permission to rerun on a long-lived
host. A hosted provider satisfies this rule only when its job timeout, log
capture and ephemeral-runner destruction are enforced outside the job. Adding
or changing a hosted workflow remains separately authorized work.

For this implementation, use the repository's existing `Native macOS
qualification` workflow for the first integrated execution. Its standard
GitHub-hosted runners are ephemeral, its native jobs have a provider-enforced
30-minute ceiling, its qualification step has a 20-minute ceiling, and its
read-only workflow retains bounded receipts and logs for three days. Push the
reviewed source commit, let the ordinary `push` trigger create the run, and do
not execute the new artifact locally first. Download every native and forward
receipt plus the complete GitHub job logs before classifying the result. A
cancelled, timed-out or runner-lost job is failed or incomplete evidence even
when another matrix cell passes. The GitHub run URL, run attempt, commit, job
IDs and downloaded artifact hashes form the external supervisor record; no file
written inside the runner may substitute for the provider's timeout and
teardown.

Preserve any hung or unkillable state as runtime evidence and destroy the
disposable environment rather than continuing on the host. Do not execute the
new fixture on a long-lived workstation until the supervised disposable run,
cleanup checks and failure mutants pass. The corrected scratch feasibility
prototype is design evidence only; it does not satisfy this gate for the
integrated source.

If no disposable environment or independent external supervisor is available,
report `Blocked: supervised disposable native execution`. Completed
documentation and source intake remain valid partial outputs, but Phase 3 and
this plan remain incomplete.

Do not lower `minimum_darwin` from 24 based on source age, cross-compilation or
Rosetta. Darwin 21 requires a separate Intel Mac Mini result using source-bound
transferred artifacts.

## Phase 4: Validate the repository and consumer

Resolve the current and floor compilers through the workspace toolchain and set
`NK_CURRENT_CRYSTAL` and `NK_FLOOR_CRYSTAL` to their executable paths. Use
fresh, external paths for every cache, receipt and qualification output.

First run the expanded behavior qualification on the disposable native arm64
host required by Phase 3, once per compiler. The following commands are guest
payloads; invoke each through the independent host supervisor with a deadline
of no more than 45 minutes rather than as an unsupervised interactive command:

```sh
CRYSTAL_CACHE_DIR="$NK_CURRENT_QUALIFY_CACHE" \
  python3 -B scripts/ci/runner.py qualify \
    --compiler "$NK_CURRENT_CRYSTAL" \
    --profile macos-15-arm64 \
    --output "$NK_CURRENT_QUALIFY_OUTPUT"

CRYSTAL_CACHE_DIR="$NK_FLOOR_QUALIFY_CACHE" \
  python3 -B scripts/ci/runner.py qualify \
    --compiler "$NK_FLOOR_CRYSTAL" \
    --profile macos-15-arm64 \
    --output "$NK_FLOOR_QUALIFY_OUTPUT"
```

The qualification receipt must contain the expanded ordered case roster in
both optimization modes, including `mach-send-timeout`. It must also retain the
exact source identities, successful reachable-LLVM audit and empty import
tables. A reordered case sequence is a validation failure even when its set of
case IDs is complete.

Then run the repository gates from Native-Kernel with separate external paths:

```sh
CRYSTAL_CACHE_DIR="$NK_CURRENT_CHECK_CACHE" \
  make check CRYSTAL="$NK_CURRENT_CRYSTAL" \
    RECEIPTS="$NK_CURRENT_CORE_RECEIPTS"

CRYSTAL_CACHE_DIR="$NK_FLOOR_CHECK_CACHE" \
  make check CRYSTAL="$NK_FLOOR_CRYSTAL" \
    RECEIPTS="$NK_FLOOR_CORE_RECEIPTS"

python3 -B -m unittest discover -s tests -v
git diff --check
```

`make check` and `make native` execute `spec/native/probe.cr`; they do not build
or execute `spec/native/behavior.cr` and cannot substitute for the two explicit
`runner.py qualify` commands.

Run Process-Control's documented consumer command, `make check`, against the
local override with a distinct external cache. Do not edit Process-Control in
this plan. Record its exact example count and the Native-Kernel dependency
source identity before and after the run.

When local arm64 checks pass, run translated x86-64 only as translated evidence.
Do not call it native Intel qualification. Hosted native ARM64/x86-64 CI and
forward replays require a separately authorized commit/push and remain unrun
until that happens.

### Exit checks

- Current and floor compilers pass the full Native-Kernel checks.
- The expanded ordered behavior roster passes development and release native
  execution on the disposable host with both compilers.
- Every behavior artifact passes reachable-LLVM audit and empty-import
  inspection before execution.
- Each host supervisor records its deadline, streamed evidence paths, normal
  driver exit and clean guest shutdown. Deadline expiry, lost control or forced
  teardown fails qualification.
- No fixture process, descendant or adopted process remains after either
  disposable-host run.
- Process-Control passes without source changes.
- Receipt source hashes match before and after each run.
- Relative to the recorded initial status, only intended owned outputs changed;
  all pre-existing unrelated changes remain preserved.

## Phase 5: Record results without broadening support

### Actions

1. Add the exact disposable-host result, qualification-receipt identities and
   independent supervisor evidence identities to
   `docs/darwin-syscall-advice-intake.md`.
2. Update `docs/support.md` only if the new case actually passed an existing
   profile. Name the host, architecture, translation state, compiler and modes.
3. Update `docs/ci-results.md` only after a real hosted run. Do not predict it.
4. Leave Darwin 21, descriptor/OOL partial restoration and other unrun lanes
   explicitly unqualified.
5. Report whether the result changes any public API. The expected answer for
   this plan is `no`.

### Exit checks

- Documentation distinguishes source review, disposable native execution,
  long-lived-host native execution, translated execution, hosted execution and
  unrun work.
- No support statement exceeds its receipt.
- The predecessor and tranche-2 evidence remain independently traceable.

## Blocked behavior

Return `Blocked` and stop the affected phase when:

- an input artifact or exact source byte fails identity verification;
- the working tree contains an unexplained overlapping change;
- a MIG layout or numeric constant cannot be reproduced from admitted evidence;
- the unmanaged fixture requires an external import, managed runtime state or an
  unbounded wait;
- exact right-reference accounting cannot be observed;
- no disposable native macOS environment is available for the integrated
  fixture's first execution;
- no supervisor outside the guest can enforce the wall-clock deadline, preserve
  independent diagnostics and destroy a non-returning environment;
- a fixture process or descendant cannot be proved exited after execution;
- a native result contradicts the expected ownership transition; or
- a required check fails for a reason unrelated to the intended change.

A blocked report must include:

1. the phase and command/probe;
2. the expected result;
3. the observed result;
4. preserved artifact/log paths;
5. the narrowest evidence-supported conclusion; and
6. the smallest user decision or new evidence required to continue.

Hosted CI is optional only when another independently supervised disposable
native environment has completed the first-execution gate. If no supervised
disposable environment is available, Phase 3 and this plan are blocked. Once
that gate passes, do not mark the plan blocked merely because the Intel Mac
Mini, hosted matrix or a different macOS release has not yet run. Mark those
lanes `Unrun` and keep the claim scoped to completed evidence.

If only a later phase is blocked, preserve all completed earlier-phase outputs
and report their checks separately. Do not describe the whole plan as complete.

## Completion report

Return exactly these sections after execution:

1. `Changed files` — paths and their purpose.
2. `Evidence admitted` — artifact/source identities and evidence classes.
3. `Native qualification` — host, architecture, compiler, optimization modes
   and exact case results.
4. `Consumer result` — Process-Control command and outcome.
5. `Unrun or blocked` — every unsupported, skipped, unavailable or failed lane.
6. `API effect` — state whether any public API or support floor changed.

Before returning, verify that no failure was converted into a pass, no generated
inventory was edited by hand, no public API was added, no receipt entered the
repository, and no commit or push occurred without separate authorization.
