# Native-Kernel namespace implementation runbook

Status: proposed on 2026-11-12. This file instructs an implementation agent; it
does not claim that the changes are implemented, committed, published or
qualified.

## Purpose

Reshape Native-Kernel's public surface so later Darwin, Linux and Windows kernel
catalogs can use precise owners without preserving misleading names or
unpublished compatibility aliases. Update Process-Control, the first consumer,
without changing native ABI, arguments, results, error provenance, resource
ownership or fallback behavior.

This runbook covers four change classes:

1. namespace and method ownership;
2. generic-entry target selection;
3. removal of unpublished spawn-profile defaults; and
4. isolated-spec repair.

## Use this runbook when

- implementing the namespace audit recorded on 2026-11-12;
- updating Native-Kernel and Process-Control together for the names in this
  file; or
- qualifying the resulting local or committed source.

## Do not use this runbook for

- importing the complete Darwin, Linux or Windows syscall catalog;
- adding an empty or unqualified Windows backend;
- replacing Mach return tuples with named records;
- changing native mechanism behavior or Process-Control policy;
- publishing, pushing, tagging, changing remotes or deleting CI artifacts; or
- committing unrelated Process-Control time-taxonomy work.

If work crosses one of these boundaries, stop and request a separate decision.

## Authority and precedence

Apply rules in this order:

1. explicit user instructions for the current turn;
2. the exact owner-approved surface decisions in **Required public contract**;
3. the workspace and shard `AGENTS.md` files; and
4. the remaining workflow in this runbook.

The method map below is a specific rename exception to the namespacing guide's
general rule that methods keep their names. The audit-token signal row also
authorizes the single argument rename `words` to `token`; no other getter or
argument is renamed. The separately listed Spawn constructor requirement and
removal of `attributes_size` are API removals for unpublished behavior, not
rename exceptions.

When naming clarity conflicts with native compatibility, preserve the native
contract and stop. Do not keep an old name merely because it exists: these APIs
are unpublished and compatibility aliases are forbidden.

Do not commit unless the user explicitly authorizes commits. Without that
authorization, treat Phases A, B and C as review checkpoints and continue in
disposable proof trees.

## Required inputs

### Repository baseline

Recheck these values before editing; they are planning evidence, not permanent
truth:

| Repository               | Observed state on 2026-11-12                                                                 |
| ------------------------ | -------------------------------------------------------------------------------------------- |
| Native-Kernel            | `main` at `1bf920b`, one commit ahead of `origin/main`; this plan is the only untracked path |
| Process-Control          | `main` at `9bf6fc1`, with the four user edits listed below                                   |
| Crystal Semantic Toolkit | `codex/editor-navigation`, clean; CST 2.57.0                                                 |

Known audit baseline:

- CST all-role audit: 70 files, 621 declarations, no parse error, seven
  advisories;
- Darwin semantic graph: 7,459 typed method instances, no normalization
  collision or unmapped caller, but incomplete because of unsupported macro
  inputs; and
- Linux cross-target graph: `stale-input` on two attempts, therefore not
  qualification.

The existing Process-Control edits are outside this runbook:

- `docs/contracts.md`;
- `spec/accounting_spec.cr`;
- `src/process-control/internal/unix/protocol.cr`; and
- `src/process-control/resource/usage.cr`.

Leave those hunks unstaged and uncommitted. If a required namespace edit
overlaps one, stop. Final qualification must use disposable proof trees that do
not contain these four edits.

### Source authorities

Record the SHA-256 or commit of every source used:

- `/Users/immateria/Downloads/darwin-xnu-syscall-history-first-pass.zip`;
- Darwin 21 `xnu-8020.140.41`, commit
  `27b03b360a988dfd3dfdf34262bb0042026747cc`;
- Darwin 24 `xnu-11417.101.15`, commit
  `e3723e1f17661b24996789d8afc084c0c3303b26`;
- Darwin 25 `xnu-12377.121.6`, commit
  `ac9718fb1af618d5ce8678d0dc6e8a58f252216f`; and
- the Linux v6.6 tables named in `docs/linux-process.md` and the two shipped
  Linux architecture-number files.

Darwin 21 is a nearby published source, not the exact shipping
`xnu-8020.240.18.709.2` source. Preserve that limit in all reports.

If a source authority disagrees with Appendix A, stop and report the exact
source, revision, field and value before changing code.

### Terms

- **raw entry**: direct `Raw.call` engine and architecture assembly;
- **typed entry**: platform ABI records and thin wrappers built on the raw entry;
- **unmanaged artifact**: custom-entry executable built with `-Dwithout_main`
  without starting Crystal's managed runtime;
- **metadata entry**: managed build-tool input describing shipped source or
  permitted assembly; the audited unmanaged artifact must not require it;
- **Implemented locally**: all mandatory local, floor-compiler and cross-target
  gates pass, every native gate admitted by an available host passes, and every
  unavailable native cell is named as a limit;
- **Committed**: the authorized paired checkpoint commits exist with correct
  staged scope; and
- **Release qualified**: committed final source also has the required hosted
  evidence and macOS 12 Intel receipt.

Never use `Complete`; it is not a status in this runbook.

## Required public contract

### Generic and explicit entries

`require "native-kernel"` must dispatch at compile time:

- 64-bit Darwin ARM64 or x86-64 loads `native-kernel/darwin`;
- non-Android 64-bit GNU or musl Linux on AArch64 or x86-64 loads
  `native-kernel/linux`; and
- every other target refuses with a message naming the target and supported
  profiles.

The refusal must contain this exact stable text after any compiler target
prefix: `Native-Kernel supports only 64-bit Darwin ARM64/x86-64 and non-Android
64-bit GNU/musl Linux AArch64/x86-64.`

Retain these explicit entries:

- `native-kernel/darwin`;
- `native-kernel/darwin/raw`;
- `native-kernel/linux`; and
- `native-kernel/linux/raw`.

Metadata remains explicit and must not enter a raw or typed require graph.

### Namespace and method map

Apply these changes directly. Do not add aliases or forwarding methods.

| Kind      | Current surface                         | Target surface                                           |
| --------- | --------------------------------------- | -------------------------------------------------------- |
| namespace | `Linux::Number`                         | `Linux::Syscall::Number`                                 |
| type      | `Darwin::Resource::Time`                | `Darwin::Resource::Timeval`                              |
| module    | `Darwin::ABI`                           | `Darwin::Mach::ABI`                                      |
| enum      | `Darwin::Mach::ExchangePhase`           | `Darwin::Mach::Exchange::Phase`                          |
| method    | `Darwin::Process.release`               | `Darwin::Release.major`                                  |
| method    | `Darwin::Signal.kill(pid, number)`      | `Darwin::Process.kill(pid, number)`                      |
| method    | `Darwin::Process.signal(words, number)` | `Darwin::Process.signal_with_audit_token(token, number)` |
| method    | `Darwin::Mach.task`                     | `Darwin::Mach.task_self`                                 |
| method    | `Darwin::Mach.open`                     | `Darwin::Mach.task_name_for_pid`                         |
| method    | `Darwin::Mach.retain`                   | `Darwin::Mach.retain_send_right`                         |
| method    | `Darwin::Mach.release`                  | `Darwin::Mach.release_send_right`                        |
| method    | `Darwin::Mach.read`                     | `Darwin::Mach.read_audit_token`                          |

`Darwin::Release.major` reads `KERN_OSRELEASE`. `Spawn.profile(major)` and
`Mach.transport(major)` remain explicit selectors; callers pass
`Release.major` where they currently pass `Process.release`.

Ordinary PID signaling, audit-token signaling and pidfd signaling remain three
separate authority routes. Audit-token and pidfd routes must never fall back to
PID `kill`.

### Internal and fixture names

Apply this exact map to the remaining compound Crystal declarations. These
fixture namespaces are program-local and do not enter the library API.

| Path                                                                  | Current declaration    | Target declaration                  |
| --------------------------------------------------------------------- | ---------------------- | ----------------------------------- |
| `spec/linux_abi_spec.cr`                                              | `LinuxKernel`          | `Linux::ABI::Fixture::Kernel`       |
| `spec/linux_abi_spec.cr`                                              | `LinuxAlignment(T)`    | `Linux::ABI::Fixture::Alignment(T)` |
| `spec/native/monterey_spawn.cr`                                       | `MontereySpawn`        | `Spawn::Monterey`                   |
| `spec/native/monterey_task_token.cr`                                  | `MontereyTaskToken`    | `Task::Token::Monterey`             |
| `spec/native/exec.cr`                                                 | `ExecProof`            | `Exec::Proof`                       |
| `spec/native/linux/raw_probe.cr`                                      | `LinuxRawProbe`        | `Linux::Raw::Probe`                 |
| `spec/native/linux/raw_probe.cr`                                      | `LinuxRawProbe::Linux` | `Linux::Raw::Probe::Kernel`         |
| `spec/native/linux/behavior.cr` and `spec/native/linux/behavior/*.cr` | `LinuxBehavior`        | `Linux::Behavior`                   |
| `spec/native/linux/behavior/common.cr`                                | `LinuxBehavior::Linux` | `Linux::Behavior::Kernel`           |

Retain the short fixture aliases `D`, `P`, `E`, `S`, `R` and `W`. Search all
Crystal sources, specs, fixtures, examples and scripts again at kickoff. Stop
for an owner decision if another compound declaration lacks either a target in
this file or an exception in **Names that remain**.

### Process information records

`Process::Info` becomes a module containing the existing selector, flavor and
comparison constants. Its `BSD`, `Identifier` and `Task` children are `lib`
namespaces for C records.

| Native record             | Current type            | Target type                         |
| ------------------------- | ----------------------- | ----------------------------------- |
| `proc_bsdshortinfo`       | `Process::Info::Short`  | `Process::Info::BSD::Short`         |
| `proc_bsdinfo`            | `Process::Info::Bsd`    | `Process::Info::BSD::Record`        |
| `proc_uniqidentifierinfo` | `Process::Info::Unique` | `Process::Info::Identifier::Unique` |
| `proc_bsdinfowithuniqid`  | `Process::Info::Record` | `Process::Info::BSD::Identified`    |
| `proc_taskinfo`           | `Process::Info::Task`   | `Process::Info::Task::Record`       |
| `proc_taskallinfo`        | `Process::Info::All`    | `Process::Info::Task::All`          |

Retain the constant names and values listed in Appendix A.4.

Retain `Process::Usage::V0`, `V1` and `V2`. Do not merge
`Process::Usage` with `Resource::Usage`; live PID snapshots and terminal
`rusage` accounting have different attribution and output contracts.

### Portable metadata

Apply this exact map:

| Current surface                                 | Target surface                                      |
| ----------------------------------------------- | --------------------------------------------------- |
| `require "native-kernel/source"`                | `require "native-kernel/metadata/source"`           |
| `Native::Kernel::Source`                        | `Native::Kernel::Metadata::Source`                  |
| `require "native-kernel/audit"`                 | `require "native-kernel/metadata/assembly"`         |
| `Native::Kernel::Audit::ASSEMBLY`               | `Native::Kernel::Metadata::Assembly::DARWIN`        |
| `Native::Kernel::Audit::LINUX_X86_64_ASSEMBLY`  | `Native::Kernel::Metadata::Assembly::LINUX_X86_64`  |
| `Native::Kernel::Audit::LINUX_AARCH64_ASSEMBLY` | `Native::Kernel::Metadata::Assembly::LINUX_AARCH64` |

`Metadata::Source::FILES` and `.root` retain their meanings. Metadata must
compile on Darwin, Linux and Windows even when the target has no raw profile.

### Spawn profile

- Require `major` and `layout` when constructing `Spawn::Profile` directly.
- Keep `Spawn.profile(major)` as the normal selection path.
- Remove `attributes_size`.
- Keep `fixed_attribute_copy_size` as the only public spelling.
- Preserve the audited Darwin 21, 24 and 25 values.

### Names that remain

Do not rename:

- `Linux::Pidfd`: `pidfd` is one established Linux kernel term;
- `Darwin::Event::Kevent64`: this follows the native API term;
- either platform `Process` module;
- `Linux::Signal::Set`;
- platform-local `Result` types; or
- `Process::Usage::V0`, `V1` and `V2`.

The accepted CST advisory set is limited to the qualified platform `Process`
modules, `Linux::Signal::Set` and deliberate `Syscall::Number` leaves. Fix or
obtain explicit owner acceptance for every other finding.

### Target ownership tree

This tree is an ownership checklist, not an exhaustive declaration listing:

```text
Native::Kernel
├── Metadata
│   ├── Assembly
│   └── Source
├── Darwin
│   ├── Release
│   ├── Syscall::Number
│   ├── Descriptor
│   ├── Event
│   ├── Mach
│   │   ├── ABI
│   │   ├── Trap
│   │   ├── Exchange::Phase
│   │   └── Transport
│   ├── Process
│   │   ├── Info
│   │   │   ├── BSD
│   │   │   ├── Identifier
│   │   │   ├── Task
│   │   │   └── Call
│   │   ├── Usage
│   │   └── Wait
│   ├── Resource
│   │   ├── Limit
│   │   ├── Timeval
│   │   └── Usage
│   ├── Signal
│   └── Spawn
└── Linux
    ├── Syscall::Number
    ├── Descriptor
    ├── Event
    ├── Pidfd
    ├── Process::Wait
    ├── Resource
    │   ├── Limit
    │   ├── Timeval
    │   └── Usage
    └── Signal
```

Do not add a Windows namespace until it has implementation and qualification.
Linux keeps architecture-specific files beneath one `Syscall::Number`
namespace because its number values differ by architecture.

## Execution workflow

Run phases in order. Do not start the next phase until the current phase's
validation passes or the user explicitly accepts a named open gate.

Run the workflow in one dedicated `zsh -f` session so the recorded variables and
helper functions persist. Begin it with `set -e` and `setopt no_unset pipe_fail`.
If the shell is restarted, re-establish every recorded path and redeclare the
helper functions before continuing. Commands that intentionally inspect a
nonzero status must capture it explicitly. A block succeeds only when every
mandatory command in it succeeds and its final assertion passes.

The proof trees are the implementation and qualification source of truth. Make
each phase there first. When commits are authorized, transfer only that phase's
patch into the two live `namespaces` branches after its proof gates pass, inspect
an explicit staged path and hunk allowlist, run the paired live checks, and
create the named commits. Never rebuild a proof tree from the dirty live
Process-Control checkout.

### Phase 0: establish baseline and proof scope

1. Re-read the workspace, Native-Kernel and Process-Control guides.
2. Run the workspace dirty-status inventory. Record every pre-existing change.
3. Take the Native-Kernel, Process-Control and workspace namespacing locks. Take
   the heavy-run lock only during heavy gates. Record each lock owner.
4. If live repository edits or commits are authorized, create or switch both
   shard repositories to `namespaces` from the recorded baseline. Create or
   update `docs/design/namespacing/Native-Kernel.md` in the workspace repository
   with the exact maps in this file, mark Native-Kernel as owner-approved in the
   workspace namespacing ledger and link this runbook. Keep those workspace
   changes separate from both shard repositories.
5. Record repository revisions, compiler descriptions and paths, host OS and
   architecture. Set `NK_BASELINE_COMMIT` and `PC_BASELINE_COMMIT` to the exact
   respective live `HEAD` values before snapshotting. Set `CURRENT_CRYSTAL` and
   `FLOOR_CRYSTAL` to the absolute selected compiler executables and verify their
   reported releases before use.
6. Create an external scratch root:

   ```zsh
   NK_PLAN_SCRATCH=$(mktemp -d /private/tmp/native-kernel-namespace.XXXXXX)
   ```

7. Snapshot committed and working trees:

   ```zsh
   cd /Users/immateria/Crystal-Shards
   zsh docs/design/namespacing/snapshot.zsh \
     "$NK_PLAN_SCRATCH/committed" shards/Native-Kernel shards/Process-Control
   zsh docs/design/namespacing/snapshot.zsh --worktree \
     "$NK_PLAN_SCRATCH/working" shards/Native-Kernel shards/Process-Control
   ```

8. Build a minimal disposable workspace from the committed snapshots:

   ```zsh
   PROOF_WORKSPACE="$NK_PLAN_SCRATCH/proof-workspace"
   mkdir -p "$PROOF_WORKSPACE/shards"
   cp -R "$NK_PLAN_SCRATCH/committed/Native-Kernel" \
     "$PROOF_WORKSPACE/shards/Native-Kernel"
   cp -R "$NK_PLAN_SCRATCH/committed/Process-Control" \
     "$PROOF_WORKSPACE/shards/Process-Control"
   cp -p /Users/immateria/Crystal-Shards/check.zsh "$PROOF_WORKSPACE/check.zsh"
   cp -p /Users/immateria/Crystal-Shards/cross.zsh "$PROOF_WORKSPACE/cross.zsh"
   cp -p /Users/immateria/Crystal-Shards/link.zsh "$PROOF_WORKSPACE/link.zsh"

   NK_PROOF="$PROOF_WORKSPACE/shards/Native-Kernel"
   PC_PROOF="$PROOF_WORKSPACE/shards/Process-Control"
   cp /Users/immateria/Crystal-Shards/shards/Native-Kernel/docs/namespace-plan.md \
     "$NK_PROOF/docs/namespace-plan.md"
   git -C "$NK_PROOF" init -q
   git -C "$PC_PROOF" init -q
   zsh "$PROOF_WORKSPACE/link.zsh" --quiet
   ```

   The scratch Git directories exist only so the copied `cross.zsh` discovers
   both shards. Do not use their untracked status as source evidence. Apply only
   this runbook's patches to these proof trees; never copy the four unrelated
   Process-Control edits.
9. Bind the copied workspace tools and the generated override before any source
   snapshot or gate. The runtime manifest includes the operational Git excludes
   because `link.zsh` owns them, but repository-content snapshots exclude all
   `.git` state:

   ```zsh
   PROOF_OVERRIDE="$PROOF_WORKSPACE/shard.override.yml"
   [[ -f "$PROOF_OVERRIDE" ]]
   [[ -L "$PC_PROOF/shard.override.yml" ]]
   PC_OVERRIDE_LINK="$PC_PROOF/shard.override.yml"
   [[ "${PC_OVERRIDE_LINK:A}" == "${PROOF_OVERRIDE:A}" ]]

   PROOF_TOOL_SOURCE_RECEIPT="$NK_PLAN_SCRATCH/proof-tool-sources.tsv"
   print -r -- $'tool\toriginal_sha256\tcopy_sha256' \
     > "$PROOF_TOOL_SOURCE_RECEIPT"
   for tool in check.zsh cross.zsh link.zsh; do
     original_sha=$(shasum -a 256 \
       "/Users/immateria/Crystal-Shards/$tool" | awk '{print $1}')
     copy_sha=$(shasum -a 256 \
       "$PROOF_WORKSPACE/$tool" | awk '{print $1}')
     [[ "$original_sha" == "$copy_sha" ]]
     print -r -- "$tool"$'\t'"$original_sha"$'\t'"$copy_sha" \
       >> "$PROOF_TOOL_SOURCE_RECEIPT"
   done

   proof_tool_manifest() {
     local tool digest target repository
     for tool in check.zsh cross.zsh link.zsh; do
       digest=$(shasum -a 256 \
         "$PROOF_WORKSPACE/$tool" | awk '{print $1}') || return 1
       print -r -- $'tool\t'"$digest"$'\t'"$tool" || return 1
     done
     digest=$(shasum -a 256 "$PROOF_OVERRIDE" | awk '{print $1}') || return 1
     print -r -- $'override\t'"$digest"$'\tshard.override.yml' || return 1
     target=$(readlink "$PC_PROOF/shard.override.yml") || return 1
     [[ "$target" == "$PROOF_OVERRIDE" ]] || return 1
     print -r -- $'symlink\t'"$target"$'\tshards/Process-Control/shard.override.yml' || return 1
     for repository in "$NK_PROOF" "$PC_PROOF"; do
       digest=$(shasum -a 256 \
         "$repository/.git/info/exclude" | awk '{print $1}') || return 1
       print -r -- $'git-exclude\t'"$digest"$'\t'"${repository#$PROOF_WORKSPACE/}" || return 1
     done
     digest=$(shasum -a 256 \
       "$PROOF_TOOL_SOURCE_RECEIPT" | awk '{print $1}') || return 1
     print -r -- $'source-receipt\t'"$digest" || return 1
   }
   PROOF_TOOL_MANIFEST="$NK_PLAN_SCRATCH/proof-tools.sha256"
   proof_tool_manifest > "$PROOF_TOOL_MANIFEST"
   verify_proof_tools() {
     proof_tool_manifest | cmp -s "$PROOF_TOOL_MANIFEST" -
   }
   verify_proof_tools

   CRYSTAL_BIN=${CURRENT_CRYSTAL:A}
   CRYSTAL_ROOT=${CRYSTAL_BIN:h:h}
   SHARDS_BIN="$CRYSTAL_ROOT/embedded/bin/shards"
   [[ -x "$SHARDS_BIN" ]]
   (
     cd "$PC_PROOF"
     SHARDS_OVERRIDE="$PROOF_OVERRIDE" \
       "$SHARDS_BIN" install
   )
   PC_NATIVE_KERNEL=$(cd "$PC_PROOF/lib/native-kernel" && pwd -P)
   [[ "$PC_NATIVE_KERNEL" == "$NK_PROOF" ]]
   verify_proof_tools
   ```

   Repeat the resolved-path assertion immediately before every Process-Control
   gate. Run `verify_proof_tools` immediately before and after every copied
   workspace command. A proof command must not resolve any Native-Kernel source
   from the live workspace or a downloaded package.
10. Define repository-content phase snapshots and binary phase diffs:

   ```zsh
   PHASE_SNAPSHOTS="$NK_PLAN_SCRATCH/phase-snapshots"
   mkdir -p "$PHASE_SNAPSHOTS"
   discard_scratch() {
     local target=$1
     [[ -n "$target" && "$target" == "$NK_PLAN_SCRATCH"/* ]] || return 1
     [[ ! -e "$target" ]] || find "$target" -depth -delete
   }
   repository_content_copy() {
     local source=$1 destination=$2
     [[ -d "$source" && ! -e "$destination" ]] || return 1
     rsync -a \
       --exclude '/.git/' --exclude '/lib/' --exclude '/bin/' \
       --exclude '/.crystal/' --exclude '/shard.lock' \
       --exclude '/shard.override.yml' \
       "$source/" "$destination/"
   }
   repository_content_manifest() {
     setopt local_options extended_glob null_glob pipe_fail
     local root=$1 file link digest target
     [[ -d "$root" ]] || return 1
     (
       cd "$root" || exit 1
       for file in **/*(.DN); do
         [[ "$file" == .git/* || "$file" == lib/* || \
            "$file" == bin/* || "$file" == .crystal/* || \
            "$file" == shard.lock || "$file" == shard.override.yml ]] && continue
         digest=$(shasum -a 256 -- "$file" | awk '{print $1}') || exit 1
         print -r -- $'file\t'"$digest"$'\t'"$file" || exit 1
       done
       for link in **/*(@DN); do
         [[ "$link" == .git/* || "$link" == lib/* || \
            "$link" == bin/* || "$link" == .crystal/* || \
            "$link" == shard.override.yml ]] && continue
         target=$(readlink "./$link") || exit 1
         digest=$(print -rn -- "$target" | shasum -a 256 | awk '{print $1}') || exit 1
         print -r -- $'link\t'"$digest"$'\t'"$link"$'\t'"$target" || exit 1
       done
     ) | LC_ALL=C sort
   }
   run_proof_workspace_gate() {
     local label=$1 result temporary failure gate_path
     local command_code=0 evidence_code=0
     shift
     result="$NK_PLAN_SCRATCH/workspace-gates/$label"
     [[ ! -e "$result" ]] || return 1
     mkdir -p "$NK_PLAN_SCRATCH/workspace-gates" || return 1
     temporary=$(mktemp -d \
       "$NK_PLAN_SCRATCH/workspace-gates/.${label}.XXXXXX") || return 1
     verify_proof_tools || evidence_code=1
     repository_content_manifest "$NK_PROOF" \
       > "$temporary/native-kernel.before" || evidence_code=1
     repository_content_manifest "$PC_PROOF" \
       > "$temporary/process-control.before" || evidence_code=1
     if (( evidence_code == 0 )); then
       gate_path="${CURRENT_CRYSTAL:h}:${SHARDS_BIN:h}:/usr/bin:/bin:/usr/sbin:/sbin"
       env PATH="$gate_path" \
         CRYSTAL="$CURRENT_CRYSTAL" \
         CRYSTAL_SPEC_COMPILER_BIN="$CURRENT_CRYSTAL" \
         CHECK_LOGS="$temporary/check-logs" \
         CROSS_LOGS="$temporary/cross-logs" \
         "$@" > "$temporary/stdout" 2> "$temporary/stderr" || command_code=$?
     fi
     print -r -- "$command_code" > "$temporary/status"
     repository_content_manifest "$NK_PROOF" \
       > "$temporary/native-kernel.after" || evidence_code=1
     repository_content_manifest "$PC_PROOF" \
       > "$temporary/process-control.after" || evidence_code=1
     verify_proof_tools || evidence_code=1
     cmp -s "$temporary/native-kernel.before" \
       "$temporary/native-kernel.after" || evidence_code=1
     cmp -s "$temporary/process-control.before" \
       "$temporary/process-control.after" || evidence_code=1
     if (( command_code != 0 || evidence_code != 0 )); then
       failure="$NK_PLAN_SCRATCH/workspace-gates/failed-${temporary:t}"
       mv "$temporary" "$failure" || discard_scratch "$temporary"
       return 1
     fi
     mv "$temporary" "$result" || {
       discard_scratch "$temporary"
       return 1
     }
   }
   phase_snapshot() {
     local label=$1 destination="$PHASE_SNAPSHOTS/$1" temporary
     if [[ -e "$destination" ]]; then
       print -u2 -r -- "phase snapshot already exists: $destination"
       return 1
     fi
     temporary=$(mktemp -d "$PHASE_SNAPSHOTS/.${label}.XXXXXX") || return 1
     if ! repository_content_copy "$NK_PROOF" "$temporary/Native-Kernel" || \
        ! repository_content_copy "$PC_PROOF" "$temporary/Process-Control"; then
       discard_scratch "$temporary"
       return 1
     fi
     mv "$temporary" "$destination" || {
       discard_scratch "$temporary"
       return 1
     }
   }
   phase_patch() {
     local previous=$1 current=$2 repository=$3 diff_code=0
     local before="$PHASE_SNAPSHOTS/$previous/$repository"
     local after="$PHASE_SNAPSHOTS/$current/$repository"
     local result="$NK_PLAN_SCRATCH/phase-$current-$repository" temporary
     if [[ ! -d "$before" || ! -d "$after" || -e "$result" ]]; then
       print -u2 -r -- "invalid phase diff inputs: $previous $current $repository"
       return 1
     fi
     temporary=$(mktemp -d "$NK_PLAN_SCRATCH/.phase-$current-$repository.XXXXXX") || return 1
     git diff --no-index --binary -- \
       "$before" "$after" > "$temporary/patch" 2> "$temporary/stderr" || diff_code=$?
     if (( diff_code != 1 )) || [[ ! -s "$temporary/patch" || -s "$temporary/stderr" ]]; then
       [[ -s "$temporary/stderr" ]] && command cat -- "$temporary/stderr" >&2
       discard_scratch "$temporary"
       return 1
     fi
     shasum -a 256 -- "$temporary/patch" > "$temporary/SHA256" || {
       discard_scratch "$temporary"
       return 1
     }
     mv "$temporary" "$result" || {
       discard_scratch "$temporary"
       return 1
     }
   }
   verify_staged_phase() {
     local phase=$1 repository=$2 live=$3 diff_code=0
     local proof="$PHASE_SNAPSHOTS/$phase/$repository"
     local result="$NK_PLAN_SCRATCH/staged-$phase-$repository" temporary failure
     [[ -d "$proof" && -d "$live/.git" && ! -e "$result" ]] || return 1
     temporary=$(mktemp -d "$NK_PLAN_SCRATCH/.staged-$phase-$repository.XXXXXX") || return 1
     mkdir -p "$temporary/content" "$temporary/compare" || {
       discard_scratch "$temporary"
       return 1
     }
     git -C "$live" checkout-index --all --prefix="$temporary/content/" || {
       discard_scratch "$temporary"
       return 1
     }
     git diff --no-index --exit-code -- "$proof" "$temporary/content" \
       > "$temporary/compare/stdout" 2> "$temporary/compare/stderr" || diff_code=$?
     if (( diff_code != 0 )) || \
        [[ -s "$temporary/compare/stdout" || -s "$temporary/compare/stderr" ]]; then
       [[ -s "$temporary/compare/stdout" ]] && command cat -- "$temporary/compare/stdout" >&2
       [[ -s "$temporary/compare/stderr" ]] && command cat -- "$temporary/compare/stderr" >&2
       failure="$NK_PLAN_SCRATCH/failed-staged-${temporary:t}"
       mv "$temporary" "$failure" || discard_scratch "$temporary"
       return 1
     fi
     shasum -a 256 -- "$temporary"/content/**/*(.DN) \
       > "$temporary/compare/SHA256" || {
       discard_scratch "$temporary"
       return 1
     }
     mv "$temporary" "$result" || {
       discard_scratch "$temporary"
       return 1
     }
   }
   phase_snapshot 0
   ```

   Each destination is new and external. These snapshots, not a diff from the
   intentionally untracked scratch repositories, define the A, B and C patch
   boundaries. Every phase must change both repositories; an empty phase patch
   is a failure of the paired-checkpoint contract. `shard.override.yml` is
   operational proof-workspace state: `repository_content_copy` excludes it from
   phase and native-host source copies, while `proof_tool_manifest` binds the
   proof-workspace link and target separately.

   Before each live checkpoint, transfer only the corresponding recorded phase
   patch, stage an explicit path/hunk allowlist, and run `git diff --cached
   --check`. Checkpoint A also stages the runbook byte-for-byte from
   `$PHASE_SNAPSHOTS/A/Native-Kernel/docs/namespace-plan.md`, because it was
   deliberately present in proof snapshot 0 rather than in the A diff. Then
   export and compare the complete staged index:

   ```zsh
   NK_LIVE=/Users/immateria/Crystal-Shards/shards/Native-Kernel
   PC_LIVE=/Users/immateria/Crystal-Shards/shards/Process-Control
   verify_staged_phase PHASE Native-Kernel "$NK_LIVE" &&
     verify_staged_phase PHASE Process-Control "$PC_LIVE"
   ```

   Replace `PHASE` with `A`, `B` or `C`. Do not commit unless both comparisons
   are byte-identical. The proof trees and verified staged indexes now contain
   identical repository bytes. Under the workspace heavy-run lock, run the
   mandatory targeted workspace scripts from the disposable proof workspace
   before each paired checkpoint:

   ```zsh
   run_proof_workspace_gate "checkpoint-PHASE-check" \
     zsh "$PROOF_WORKSPACE/check.zsh" native-kernel process-control &&
     run_proof_workspace_gate "checkpoint-PHASE-cross" \
       zsh "$PROOF_WORKSPACE/cross.zsh" native-kernel process-control
   ```

   Replace `PHASE` with `A`, `B` or `C`. These are byte-bound copies of the
   governing workspace commands, discovered against only the source-bound proof
   repositories. The wrapper rejects any tool, override, operational-link or
   repository-content change. A run from the dirty live workspace is optional
   integration evidence and never qualification. The subsequent commit consumes
   the verified index and is chained as described below.

   Immediately after staged verification and immediately before each named
   commit, record the index tree and parent. Substitute the repository and exact
   checkpoint subject, then assert the new commit:

   ```zsh
   EXPECTED_PARENT=$(git -C "$LIVE_REPOSITORY" rev-parse HEAD) &&
     EXPECTED_TREE=$(git -C "$LIVE_REPOSITORY" write-tree) &&
     git -C "$LIVE_REPOSITORY" commit -m "$CHECKPOINT_SUBJECT" &&
     [[ "$(git -C "$LIVE_REPOSITORY" rev-parse HEAD^)" == "$EXPECTED_PARENT" ]] &&
     [[ "$(git -C "$LIVE_REPOSITORY" rev-parse 'HEAD^{tree}')" == "$EXPECTED_TREE" ]]
   ```

   Do not stage, unstage or run a mutating hook between `write-tree` and commit.
   A parent or tree mismatch invalidates the checkpoint.
11. Save these baseline artifacts under `$NK_PLAN_SCRATCH/baseline`:
   - revisions, status and complete diffs;
   - toolchain and host descriptions;
   - source-authority hashes;
   - CST all-role audit, namespace advice, source outline and semantic-graph
     JSON;
   - discovered spec files and complete output/example counts;
   - the full stale-name search scope and results for both committed snapshots;
   - an ABI manifest with each affected field's name, Crystal type, size,
     alignment and offset;
   - Appendix A's constants and values;
   - `make native` receipts, reachable-IR output, executable/IR hashes and
     undefined-import reports; and
   - Native-Kernel's source manifest plus Process-Control's dependency-source
     and assembly-profile manifests.
   Record the absolute current/floor receipt paths for each native profile as
   `BASELINE_{DARWIN,LINUX_ARM,LINUX_X86}_{CURRENT,FLOOR}_RECEIPT`. After the
   final native runs, record the matching `FINAL_*_RECEIPT` variables. A missing
   current or floor receipt leaves the comparator gate unrun, never passed.
12. Retain the exact ABI probe source in the receipt. After renaming, change only
   its qualified type names.
13. Run the current focused specs and native gates once. Record the known
    baseline failures: `spec/typed_spec.cr` and `spec/mach_spec.cr` fail alone
    because they borrow the alias from `spec/raw_spec.cr`;
    `spec/spawn_spec.cr` passes alone with five examples.

Stop Phase 0 if another active session owns a required repository, a required
source is missing, or an existing user edit overlaps a required hunk.

### Phase A: semantic names in existing files

Do not move or forward a source file in this phase.

In Native-Kernel:

1. Make the generic entry dispatch only to the supported profiles above.
2. Rename `Linux::Number` to `Linux::Syscall::Number` in its existing files.
3. Add Appendix A's Darwin constants without moving files:
   - declare `Darwin::Syscall::Number` in `darwin/raw.cr`;
   - declare `Darwin::Mach::Trap` in `darwin/mach.cr`; and
   - declare `Darwin::Process::Info::Call` in
     `darwin/process/inspection.cr`.
4. Replace every unexplained syscall, trap and `proc_info` operation literal in
   typed wrappers. Retain documented flags, flavors and Mach message IDs.
5. Declare `Darwin::Release` temporarily in `darwin/process.cr` and apply the
   release and signaling method map.
6. Apply the process-information, `Timeval`, Mach method, `Mach::ABI` and
   `Mach::Exchange::Phase` maps while declarations remain in their existing
   physical files.
7. Rename metadata modules and constants inside existing `source.cr` and
   `audit.cr`. Keep the old physical require paths until Phase C.
8. Apply the exact internal and fixture map. Make each spec self-contained. Put
   every remaining helper in its file-specific fixture namespace; do not use a
   suite-global alias supplied by another spec file.
9. Add `scripts/ci/generic_entry.cr` as a minimal fixture that requires
   `../../src/native-kernel` and makes no platform-specific call.
10. Add `scripts/ci/target_smoke.cr` as a dependency-free `nil` program used
   only to distinguish a compiler-incapable target from Native-Kernel refusal.
11. Add `scripts/ci/route_closure.cr` and one minimal custom-entry fixture for
   PID, audit-token and pidfd signaling.
12. Add `scripts/ci/namespace_evidence.cr`. The same file compiles against the
   committed and final require graphs; `-Dnamespace_after` selects final names.
   It emits canonical JSON with schema `namespace-evidence/1`, logical ABI type
   names, sizes, alignments, ordered fields with Crystal types and offsets, and
   every Appendix A constant with its exact Crystal type and value.
13. Add `scripts/ci/namespace_compare.py`. Its `compare` command consumes the
   before/after namespace evidence, native receipts, reachable LLVM, route
   closure and TAP inventories; emits schema `namespace-comparison/1`; and exits
   nonzero on any difference outside Appendix B's names and Phase C's paths. Its
   `seal` command emits a sorted path/SHA-256 manifest for a bounded transfer
   directory, and `verify-seal` recomputes and compares that manifest. These
   commands use only Python's standard library. Its `verify-source` command
   compares every source path/hash in a build receipt with the named Git commit
   in an explicit `--repository` checkout;
   `chain` validates and records the final commit/tree, build receipt and both
   campaign manifests; and `verify-chain` independently recomputes and verifies
   every relationship recorded by `chain` against an expected commit and tree.
   Its `native-receipt` command validates the exact host evidence layout in
   Phase D and writes one `native-copy/1` JSON document; `verify-native-receipt`
   recomputes every indexed hash and invariant from that document and host root.
   Add this script to `build_monterey_foundations.py`'s fixed source inventory so
   the build receipt binds the verifier later copied into the handoff.
14. Add `scripts/ci/namespace_removed_patterns.tsv` and
   `scripts/ci/stale_name_allowlist.tsv`. The pattern file's exact header is
   `kind<TAB>pattern`; `kind` is `symbol` for a Crystal-identifier-boundary
   match, `fixed` for an exact substring or `path` for an exact slash-normalized
   path. Tabs and newlines are forbidden in patterns. It contains every current
   surface in the namespace and method map, process-record map, metadata map and
   fixture map, plus `attributes_size` and every old require and source path.
   The allowlist's exact header is
   `kind<TAB>pattern<TAB>repository<TAB>path<TAB>line_sha256<TAB>reason`.
   `repository` is `Native-Kernel` or `Process-Control`; `path` is relative and
   slash-normalized; and `line_sha256` hashes the exact UTF-8 line without its
   line ending. `kind` and `pattern` together identify the pattern; duplicate
   pattern text across different kinds is allowed and never shares an allowance.
   Every field is required, and paths may not escape their repository root. Do
   not put a commit, tree or containing-repository manifest digest in this
   tracked file; that would make its identity self-referential.
15. Add `scripts/ci/stale_names.zsh`. It accepts the exact flagged interface
   used in Phase D; searches `.cr`, `.md`, `.yml`, `.yaml`, `.zsh`, `.sh` and
   extensionless files; excludes `.git`, `lib`, `bin`, `.crystal` and its two
   input TSV files; and emits sorted rows. Its exact tab-separated header fields,
   in order, are `kind`, `pattern`, `repository`, `source_revision`, `path`,
   `line`, `line_sha256`, `text`, `status` and `reason`.
   A `path` match has `line` equal to `0`, `line_sha256` equal to the SHA-256 of
   empty bytes
   (`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`), and
   `text` equal to the slash-normalized repository-relative path. Symbol and
   fixed matches use the one-based line number, exact line hash and exact line
   text.
   It validates both TSV schemas, rejects duplicate rows and unsafe paths, and
   exits nonzero for a match absent from the allowlist. `--report-only` records
   baseline matches without applying the allowlist; it does not make a baseline
   match acceptable in final source. Each required `--revision
   REPOSITORY=IDENTITY` value is supplied externally at scan time and copied into
   every output row; the output receipt, rather than the tracked allowlist, binds
   matches to source identity.
16. Add `scripts/ci/test_namespace_evidence.py`. Its disposable fixtures plant
   and require rejection of: an ABI field/type change, raw constant change,
   assembly multiplicity change, opcode/call-target change, new import, missing
   TAP case, wrong route, stale name, source-fingerprint mismatch, sealed-payload
   tamper, chain mismatch and native-receipt evidence mismatch. It also checks
   one valid fixture for every tool.
17. Update current Native-Kernel docs. Preserve historical quotations only when
    the stale-name report records path, line, historical revision and reason.

In Process-Control, update the known consumers in Appendix C and search the
live tree for additional users. Keep old metadata require paths in this phase.

Phase A validation:

- all affected ABI fields retain type, signedness, size, alignment and offset;
- Appendix A's values are unchanged;
- `raw_spec.cr`, `typed_spec.cr`, `mach_spec.cr` and `spawn_spec.cr` pass alone;
- the generic-entry fixture and standalone Linux ABI/raw specs type-check for
  x86-64 GNU, x86-64 musl, AArch64 GNU and AArch64 musl;
- the route-closure fixtures build; and
- Native-Kernel and Process-Control `make check` pass against the local
  override at the current compiler and Crystal 1.10.0 floor.

Record the phase boundary:

```zsh
phase_snapshot A &&
  phase_patch 0 A Native-Kernel &&
  phase_patch 0 A Process-Control
```

If commits are authorized, create paired Checkpoint A commits:

- Native-Kernel: `Name the kernel mechanisms by their owners`
- Process-Control: `Use the precise Native-Kernel mechanism names`

Checkpoint A must contain no source-file or require-path move.
The Native-Kernel Checkpoint A commit includes `docs/namespace-plan.md`; the
controlling runbook must not remain untracked after that checkpoint.

### Phase B: remove spawn compatibility

1. Require explicit `major` and `layout` in `Spawn::Profile.new`.
2. Remove `attributes_size` and migrate all consumers to
   `fixed_attribute_copy_size`.
3. Replace the historical zero-argument-construction spec with explicit profile
   assertions.
4. Recheck Darwin 21, 24 and 25 values and Process-Control allocation behavior.

Run Native-Kernel and Process-Control `make check`, then record the phase
boundary:

```zsh
phase_snapshot B &&
  phase_patch A B Native-Kernel &&
  phase_patch A B Process-Control
```

If commits are authorized, create paired Checkpoint B commits:

- Native-Kernel: `Require an explicit spawn profile`
- Process-Control: `Use the explicit spawn copy size`

### Phase C: move files and require paths

Move only declarations already validated in Phases A and B:

```text
src/native-kernel/metadata/source.cr
src/native-kernel/metadata/assembly.cr
src/native-kernel/darwin/release.cr
src/native-kernel/darwin/syscall/number.cr
src/native-kernel/darwin/mach/abi.cr
src/native-kernel/darwin/mach/trap.cr
src/native-kernel/darwin/process/info.cr
src/native-kernel/darwin/process/info/call.cr
src/native-kernel/darwin/process/info/bsd.cr
src/native-kernel/darwin/process/info/identifier.cr
src/native-kernel/darwin/process/info/task.cr
src/native-kernel/linux/syscall/number/{aarch64,x86_64}.cr
```

Then:

1. update all require edges;
2. move `Event::Kevent64` and its constants into the existing
   `darwin/event.cr`, then remove `darwin/abi.cr` after every declaration in it
   has an explicit destination;
3. update `Metadata::Source::FILES` so each shipped source appears exactly once;
4. update Process-Control to the new metadata require paths;
5. update helper fingerprints, fixtures and current docs; and
6. verify that no old file or forwarding require remains.

Compile metadata through the new paths for Darwin, Linux and Windows.

Record the phase boundary:

```zsh
phase_snapshot C &&
  phase_patch B C Native-Kernel &&
  phase_patch B C Process-Control &&
  repository_content_manifest "$PHASE_SNAPSHOTS/C/Native-Kernel" \
    > "$NK_PLAN_SCRATCH/phase-c-native-kernel.sha256" &&
  repository_content_manifest "$PHASE_SNAPSHOTS/C/Process-Control" \
    > "$NK_PLAN_SCRATCH/phase-c-process-control.sha256"
```

The two manifest files are canonical, sorted repository-content inventories.
Record each manifest file's own SHA-256 with the Phase C evidence. A later
native receipt must name both manifest SHA-256 values and prove its host copies
against the inventories, not merely repeat their values.

If commits are authorized, create paired Checkpoint C commits:

- Native-Kernel: `Move the kernel sources under their namespaces`
- Process-Control: `Follow the Native-Kernel metadata paths`

Immediately record both resulting commit and tree identities as
`NK_CHECKPOINT_C_COMMIT`, `NK_CHECKPOINT_C_TREE`, `PC_CHECKPOINT_C_COMMIT` and
`PC_CHECKPOINT_C_TREE`. These four recorded values, together with the Phase C
manifest hashes, identify the paired final implementation source.

### Phase D: resolve names and qualify final source

#### Compare name resolution

Write Appendix B.1 byte-for-byte to `$NK_PLAN_SCRATCH/renames.tsv` and Appendix
B.2 to `$NK_PLAN_SCRATCH/method-renames.tsv`, then run:

```zsh
CRYSTAL_CACHE_DIR="$NK_PLAN_SCRATCH/cache-resolve-paths" \
  "$CURRENT_CRYSTAL" build \
  /Users/immateria/Crystal-Shards/docs/design/namespacing/resolve_paths.cr \
  -o "$NK_PLAN_SCRATCH/resolve_paths"
"$NK_PLAN_SCRATCH/resolve_paths" compare \
  --renames "$NK_PLAN_SCRATCH/renames.tsv" \
  --old "$NK_PLAN_SCRATCH/committed/Native-Kernel" \
        "$NK_PLAN_SCRATCH/committed/Process-Control" \
  --new "$NK_PROOF" "$PC_PROOF"
```

The paired old and new trees supply one another's declarations. Do not also
pass any compared tree through `--decl`. If a newly discovered reference needs
an unchanged external shard, repeat `--decl DIR` once for each such dependency
and record the identical directory used for both indexes.

Confirm the snapshot tool's emitted directory names and substitute their exact
paths if they differ. Read every `NEW SILENT` row. Fix every unexplained path
change in the checkpoint that introduced it; do not create an unassigned fourth
source checkpoint.

#### Run CST from stable inputs

Define and validate the source-bound manifest before running CST:

```zsh
proof_manifest() {
  setopt local_options extended_glob null_glob
  local root label file pc_native_kernel
  for root label in \
    "$NK_PROOF" native-kernel \
    "$PC_PROOF" process-control \
    "$NK_PLAN_SCRATCH/committed/Native-Kernel" baseline-native-kernel \
    "$NK_PLAN_SCRATCH/committed/Process-Control" baseline-process-control
  do
    [[ -d "$root" ]] || return 1
    print -r -- "repository $label" || return 1
    (
      cd "$root" || exit 1
      for file in **/*(.DN); do
        [[ "$file" == .git/* || "$file" == lib/* || \
           "$file" == bin/* || "$file" == .crystal/* ]] && continue
        shasum -a 256 -- "$file" || exit 1
      done
    ) || return 1
  done
  pc_native_kernel=$(cd "$PC_PROOF/lib/native-kernel" && pwd -P) || return 1
  [[ "$pc_native_kernel" == "$NK_PROOF" ]] || return 1
  print -r -- "process-control native-kernel $pc_native_kernel" || return 1
  verify_proof_tools || return 1
  shasum -a 256 -- "$PROOF_TOOL_MANIFEST" || return 1
}
run_cst() {
  local label=$1 code=0 result temporary failure
  result="$NK_PLAN_SCRATCH/cst/$label"
  shift
  mkdir -p "$NK_PLAN_SCRATCH/cst" || return 1
  [[ ! -e "$result" ]] || return 1
  temporary=$(mktemp -d "$NK_PLAN_SCRATCH/cst/.${label}.XXXXXX") || return 1
  proof_manifest > "$temporary/before.sha256" || code=$?
  if (( code == 0 )); then
    "$@" > "$temporary/output.json" 2> "$temporary/stderr.log" || code=$?
  fi
  if (( code == 0 )); then
    python3 -m json.tool "$temporary/output.json" > /dev/null || code=$?
  fi
  if (( code == 0 )); then
    proof_manifest > "$temporary/after.sha256" || code=$?
  fi
  if (( code == 0 )); then
    cmp -s "$temporary/before.sha256" "$temporary/after.sha256" || code=$?
  fi
  if (( code != 0 )); then
    failure="$NK_PLAN_SCRATCH/cst/failure-${temporary:t}"
    mv "$temporary" "$failure" || discard_scratch "$temporary"
    return 1
  fi
  mv "$temporary" "$result" || {
    discard_scratch "$temporary"
    return 1
  }
}
```

Run one wrapped command at a time from the final source-stable, manifest-bound
proof trees:

```zsh
CST=/Users/immateria/src/Crystal-Semantic-Toolkit/bin/cst-host
run_cst audit env CST_NO_FACT_CACHE=1 "$CST" \
  audit --repo "$NK_PROOF" --all-roles --json &&
run_cst namespace env CST_NO_FACT_CACHE=1 "$CST" \
  namespace advise --repo "$NK_PROOF" --json &&
run_cst outline env CST_NO_FACT_CACHE=1 "$CST" \
  ast outline --json "$NK_PROOF/src" &&
run_cst raw-graph env CST_NO_FACT_CACHE=1 "$CST" \
  semantic graph --repo "$NK_PROOF" --entry spec/raw_spec.cr --json &&
run_cst linux-x86-gnu env CST_NO_FACT_CACHE=1 "$CST" \
  semantic graph --repo "$NK_PROOF" --entry spec/linux_abi_spec.cr \
  --target x86_64-unknown-linux-gnu --json &&
run_cst linux-arm-gnu env CST_NO_FACT_CACHE=1 "$CST" \
  semantic graph --repo "$NK_PROOF" --entry spec/linux_abi_spec.cr \
  --target aarch64-unknown-linux-gnu --json &&
run_cst linux-x86-musl env CST_NO_FACT_CACHE=1 "$CST" \
  semantic graph --repo "$NK_PROOF" --entry spec/linux_abi_spec.cr \
  --target x86_64-unknown-linux-musl --json &&
run_cst linux-arm-musl env CST_NO_FACT_CACHE=1 "$CST" \
  semantic graph --repo "$NK_PROOF" --entry spec/linux_abi_spec.cr \
  --target aarch64-unknown-linux-musl --json
```

Use the same before/output-or-log/after pattern for every later build, spec,
matrix and native command. This replaces Git status as stability evidence for
the disposable trees. The dependency assertion inside `proof_manifest` must
pass every time.

If a graph returns `stale-input`, create a second proof workspace from the same
committed snapshots, apply the same patches and retry once. After a second stale
result, stop unless the owner explicitly accepts this alternate proof:

- both Linux cross-target builds;
- native execution on both Linux architectures;
- clean stale-name and namespace audits; and
- the raw constant and route-closure IR proofs below.

#### Run final validation

Use a distinct external `CRYSTAL_CACHE_DIR` for every concurrent Crystal run.
Hold the workspace heavy-run lock around workspace matrices and native audits.
Run Native-Kernel commands from `NK_PROOF`. Run Process-Control commands from
`PC_PROOF` with `SHARDS_OVERRIDE=$PROOF_OVERRIDE`, after the
resolved-path assertion and manifest-before step. Store every log, cache,
receipt and matrix output outside both proof trees.

Run this explicit Linux profile matrix with both selected compilers; do not
infer musl support from the copied workspace matrix:

```zsh
LINUX_PROFILES=(
  x86_64-linux-gnu
  x86_64-linux-musl
  aarch64-linux-gnu
  aarch64-linux-musl
)
LINUX_MATRIX="$NK_PLAN_SCRATCH/linux-profile-matrix"
[[ ! -e "$LINUX_MATRIX" ]]
mkdir -p "$LINUX_MATRIX/logs" "$LINUX_MATRIX/manifests"
print -r -- $'compiler\ttarget\tentry\tstatus\tlog' > "$LINUX_MATRIX/receipt.tsv"
linux_failures=0
for label compiler in current "$CURRENT_CRYSTAL" floor "$FLOOR_CRYSTAL"; do
  for target in "${LINUX_PROFILES[@]}"; do
    for entry in \
      scripts/ci/generic_entry.cr \
      spec/linux_abi_spec.cr \
      spec/linux_raw_spec.cr
    do
      entry_label=${${entry:t}:r}
      cell="$label-$target-$entry_label"
      code=0
      proof_manifest > "$LINUX_MATRIX/manifests/$cell.before" || code=$?
      if (( code == 0 )); then
        CRYSTAL_CACHE_DIR="$NK_PLAN_SCRATCH/cache-$cell" \
        "$compiler" build --no-codegen --cross-compile --target "$target" \
          "$NK_PROOF/$entry" > "$LINUX_MATRIX/logs/$cell.log" 2>&1 || code=$?
      fi
      if (( code == 0 )); then
        proof_manifest > "$LINUX_MATRIX/manifests/$cell.after" || code=$?
      fi
      if (( code == 0 )); then
        cmp -s "$LINUX_MATRIX/manifests/$cell.before" \
          "$LINUX_MATRIX/manifests/$cell.after" || code=$?
      fi
      if (( code == 0 )); then
        cell_status=passed
      else
        cell_status=failed
        (( linux_failures += 1 ))
      fi
      print -r -- "$label"$'\t'"$target"$'\t'"$entry_label"$'\t'"$cell_status"$'\t'"logs/$cell.log" \
        >> "$LINUX_MATRIX/receipt.tsv"
    done
  done
done
[[ $(wc -l < "$LINUX_MATRIX/receipt.tsv") -eq 25 ]]
(( linux_failures == 0 ))
```

All 24 cells must type-check. Linux native runtime evidence remains the two GNU
hosts; the musl cells are compile-time profile evidence.

Native-Kernel:

1. Crystal formatting check for every changed Crystal file.
2. Every focused spec above, alone.
3. Full `make check`.
4. Full `make native` with separate current and Crystal 1.10.0 floor compilers,
   distinct external caches and receipts.
5. Crystal 1.10.0 floor build and specs.
6. Proof-workspace cross-target matrix through this source-bound wrapper:

   ```zsh
   run_proof_workspace_gate phase-d-native-kernel-cross \
     zsh "$PROOF_WORKSPACE/cross.zsh" native-kernel
   ```
7. Native Linux x86-64 and AArch64 checks in disposable OrbStack copies with
   both current and floor compilers.
8. Native macOS ARM64 and Rosetta x86-64 unmanaged artifact checks with both
   current and floor compilers.

Process-Control:

1. Run the complete check and Darwin qualification under both selected
   compilers. This wrapper binds the dependency, compiler, cache, logs and source
   manifests into a distinct external receipt for every command:

   ```zsh
   PC_GATE_ROOT="$NK_PLAN_SCRATCH/process-control-gates"
   [[ ! -e "$PC_GATE_ROOT" ]]
   mkdir -p "$PC_GATE_ROOT"
   PC_MAKE=$(command -v make)
   [[ -x "$PC_MAKE" ]]
   run_process_control_gate() {
     local gate=$1 compiler=$2 receipt="$PC_GATE_ROOT/$1"
     local command_code=0 evidence_code=0 resolved
     shift 2
     [[ ! -e "$receipt" ]] || return 1
     mkdir -p "$receipt"
     resolved=$(cd "$PC_PROOF/lib/native-kernel" && pwd -P) || return 1
     [[ "$resolved" == "$NK_PROOF" ]] || return 1
     print -r -- "$compiler" > "$receipt/compiler.path"
     shasum -a 256 "$compiler" > "$receipt/compiler.sha256"
     "$compiler" --version > "$receipt/compiler.txt" 2>&1 || return 1
     print -r -- "${(q)@}" > "$receipt/command.zsh"
     proof_manifest > "$receipt/sources.before.sha256" || return 1
     (
       cd "$PC_PROOF"
       env SHARDS_OVERRIDE="$PROOF_OVERRIDE" \
         CRYSTAL_CACHE_DIR="$NK_PLAN_SCRATCH/cache-process-control-$gate" \
         CRYSTAL="$compiler" CRYSTAL_SPEC_COMPILER_BIN="$compiler" \
         "$@"
     ) > "$receipt/stdout" 2> "$receipt/stderr" || command_code=$?
     print -r -- "$command_code" > "$receipt/status"
     proof_manifest > "$receipt/sources.after.sha256" || evidence_code=1
     cmp -s "$receipt/sources.before.sha256" \
       "$receipt/sources.after.sha256" || evidence_code=1
     (( command_code == 0 && evidence_code == 0 ))
   }

   run_process_control_gate check-current "$CURRENT_CRYSTAL" "$PC_MAKE" check
   run_process_control_gate check-floor "$FLOOR_CRYSTAL" "$PC_MAKE" check
   run_process_control_gate darwin-current "$CURRENT_CRYSTAL" \
     "$CURRENT_CRYSTAL" run scripts/check-darwin.cr -- \
     "$PC_GATE_ROOT/darwin-current-artifacts"
   run_process_control_gate darwin-floor "$FLOOR_CRYSTAL" \
     "$FLOOR_CRYSTAL" run scripts/check-darwin.cr -- \
     "$PC_GATE_ROOT/darwin-floor-artifacts"
   ```

   The four required local receipt paths are
   `$PC_GATE_ROOT/{check-current,check-floor,darwin-current,darwin-floor}`; the
   two Darwin artifact receipts are the adjacent `*-artifacts` directories. A
   bare `crystal`, shared cache or one-compiler substitution is not evidence.
2. Run the proof-workspace cross-target matrix through this source-bound wrapper:

   ```zsh
   run_proof_workspace_gate phase-d-process-control-cross \
     zsh "$PROOF_WORKSPACE/cross.zsh" process-control
   ```
3. On native Linux AArch64 and untranslated x86-64 hosts, run the complete check
   under both selected compilers with `PROCESS_CONTROL_REQUIRE_PIDFD=1`. If the
   cgroup capability probe admits a delegated root, also set
   `PROCESS_CONTROL_CGROUP_SPEC_ROOT` to that root and
   `PROCESS_CONTROL_REQUIRE_CGROUP_BIRTH=1`. Require separate source-bound
   receipts for current and floor. A failed pidfd requirement is a failed
   admitted gate; an incapable host is an unavailable cell named under `Limits`.

#### Bind native copies to Phase C

For each Linux ARM64, Linux x86-64, macOS ARM64 and Rosetta x86-64 run, create a
new external host directory. Copy both repositories only from the Phase C
snapshots with `repository_content_copy`; never copy a live checkout. Create a
host-local override whose `native-kernel.path` names that host copy, install it
with the current compiler's embedded `shards`, and assert the resolved
Process-Control dependency root before execution. Run the unmanaged artifact
builder/verifier separately with `CURRENT_CRYSTAL` and `FLOOR_CRYSTAL`; neither
receipt may stand in for the other. Store their complete gate evidence at
`$NATIVE_ROOT/receipts/native-kernel-current` and
`$NATIVE_ROOT/receipts/native-kernel-floor`, respectively; each directory has
the same compiler path, compiler SHA-256, version, quoted command, environment,
stdout, stderr, status and source-manifest fields required of the
Process-Control gate evidence below.

Create the parents before calling `repository_content_copy`; each repository
destination itself must remain absent because the helper rejects replacement.
Before the first build or test command, bind the source and `before` copy to the
canonical Phase C inventories:

```zsh
NATIVE_ROOT=/external/unique-native-host-directory
[[ ! -e "$NATIVE_ROOT" ]]
mkdir -p "$NATIVE_ROOT"/{source,before,after,manifests,compare}
repository_content_copy "$PHASE_SNAPSHOTS/C/Native-Kernel" \
  "$NATIVE_ROOT/source/Native-Kernel"
repository_content_copy "$PHASE_SNAPSHOTS/C/Process-Control" \
  "$NATIVE_ROOT/source/Process-Control"
repository_content_copy "$NATIVE_ROOT/source/Native-Kernel" \
  "$NATIVE_ROOT/before/Native-Kernel"
repository_content_copy "$NATIVE_ROOT/source/Process-Control" \
  "$NATIVE_ROOT/before/Process-Control"

compare_native_copy() {
  local label=$1 expected=$2 actual=$3 code=0
  git diff --no-index --exit-code -- "$expected" "$actual" \
    > "$NATIVE_ROOT/compare/$label.stdout" \
    2> "$NATIVE_ROOT/compare/$label.stderr" || code=$?
  print -r -- "$code" > "$NATIVE_ROOT/compare/$label.status"
  (( code == 0 )) &&
    [[ ! -s "$NATIVE_ROOT/compare/$label.stdout" ]] &&
    [[ ! -s "$NATIVE_ROOT/compare/$label.stderr" ]]
}

repository_content_manifest "$NATIVE_ROOT/source/Native-Kernel" \
  > "$NATIVE_ROOT/manifests/source-native-kernel.sha256"
repository_content_manifest "$NATIVE_ROOT/source/Process-Control" \
  > "$NATIVE_ROOT/manifests/source-process-control.sha256"
repository_content_manifest "$NATIVE_ROOT/before/Native-Kernel" \
  > "$NATIVE_ROOT/manifests/before-native-kernel.sha256"
repository_content_manifest "$NATIVE_ROOT/before/Process-Control" \
  > "$NATIVE_ROOT/manifests/before-process-control.sha256"
cmp -s "$NK_PLAN_SCRATCH/phase-c-native-kernel.sha256" \
  "$NATIVE_ROOT/manifests/source-native-kernel.sha256"
cmp -s "$NK_PLAN_SCRATCH/phase-c-process-control.sha256" \
  "$NATIVE_ROOT/manifests/source-process-control.sha256"
cmp -s "$NK_PLAN_SCRATCH/phase-c-native-kernel.sha256" \
  "$NATIVE_ROOT/manifests/before-native-kernel.sha256"
cmp -s "$NK_PLAN_SCRATCH/phase-c-process-control.sha256" \
  "$NATIVE_ROOT/manifests/before-process-control.sha256"
compare_native_copy before-native-kernel \
  "$PHASE_SNAPSHOTS/C/Native-Kernel" "$NATIVE_ROOT/before/Native-Kernel"
compare_native_copy before-process-control \
  "$PHASE_SNAPSHOTS/C/Process-Control" "$NATIVE_ROOT/before/Process-Control"
```

Run the Process-Control native gates between the `before` and `after` copies.
Set `HOST_PROFILE` to exactly one of `linux-arm64`, `linux-x86_64`,
`darwin-arm64` or `darwin-x86_64`; set `HOST_OVERRIDE` to the installed
host-local override and bind its `native-kernel.path` to `NK_HOST`. Complete the
capability preflight before this block. A Linux host proceeds only with
`PIDFD_ADMISSION=admitted`. If pidfd is unavailable, retain any standalone
Native-Kernel evidence, name the Process-Control cell under `Limits`, and do not
emit a passed host `native-copy/1` receipt:

```zsh
NK_HOST="$NATIVE_ROOT/source/Native-Kernel"
PC_HOST="$NATIVE_ROOT/source/Process-Control"
HOST_OVERRIDE="$NATIVE_ROOT/host.override.yml"
HOST_MAKE=$(command -v make)
[[ -x "$HOST_MAKE" && -f "$HOST_OVERRIDE" ]]
HOST_NATIVE_KERNEL=$(cd "$PC_HOST/lib/native-kernel" && pwd -P)
[[ "$HOST_NATIVE_KERNEL" == "$NK_HOST" ]]
run_host_native_kernel_gate() {
  local label=$1 compiler=$2
  local evidence="$NATIVE_ROOT/receipts/native-kernel-$1"
  local artifacts="$NATIVE_ROOT/artifacts/native-kernel-$1"
  local command_code=0 evidence_code=0
  [[ ! -e "$evidence" && ! -e "$artifacts" ]] || return 1
  mkdir -p "$evidence" "$NATIVE_ROOT/artifacts"
  print -r -- "$compiler" > "$evidence/compiler.path"
  shasum -a 256 "$compiler" > "$evidence/compiler.sha256"
  "$compiler" --version > "$evidence/compiler.txt" 2>&1 || return 1
  print -r -- "$artifacts" > "$evidence/artifacts.path"
  print -r -- \
    "${(q)HOST_MAKE} -C ${(q)NK_HOST} native" \
    "CRYSTAL=${(q)compiler} RECEIPTS=${(q)artifacts}" \
    > "$evidence/command.zsh"
  {
    print -r -- \
      "CRYSTAL_CACHE_DIR=$NATIVE_ROOT/cache-native-kernel-$label"
    print -r -- "CRYSTAL=$compiler"
    print -r -- "RECEIPTS=$artifacts"
  } > "$evidence/environment.txt"
  repository_content_manifest "$NK_HOST" \
    > "$evidence/native-kernel.before" || return 1
  repository_content_manifest "$PC_HOST" \
    > "$evidence/process-control.before" || return 1
  env CRYSTAL_CACHE_DIR="$NATIVE_ROOT/cache-native-kernel-$label" \
    CRYSTAL="$compiler" RECEIPTS="$artifacts" \
    "$HOST_MAKE" -C "$NK_HOST" native \
    > "$evidence/stdout" 2> "$evidence/stderr" || command_code=$?
  print -r -- "$command_code" > "$evidence/status"
  repository_content_manifest "$NK_HOST" \
    > "$evidence/native-kernel.after" || evidence_code=1
  repository_content_manifest "$PC_HOST" \
    > "$evidence/process-control.after" || evidence_code=1
  cmp -s "$evidence/native-kernel.before" \
    "$evidence/native-kernel.after" || evidence_code=1
  cmp -s "$evidence/process-control.before" \
    "$evidence/process-control.after" || evidence_code=1
  if [[ "$HOST_PROFILE" == linux-* ]]; then
    [[ -f "$artifacts/export/receipt.json" ]] || evidence_code=1
  else
    [[ -f "$artifacts/manifest.json" ]] || evidence_code=1
  fi
  (( command_code == 0 && evidence_code == 0 ))
}

run_host_native_kernel_gate current "$CURRENT_CRYSTAL"
run_host_native_kernel_gate floor "$FLOOR_CRYSTAL"

HOST_PROCESS_ENV=()
if [[ "$HOST_PROFILE" == linux-* ]]; then
  [[ "$PIDFD_ADMISSION" == admitted ]]
  HOST_PROCESS_ENV+=(PROCESS_CONTROL_REQUIRE_PIDFD=1)
  if [[ -n ${ADMITTED_CGROUP_ROOT:-} ]]; then
    HOST_PROCESS_ENV+=(
      "PROCESS_CONTROL_CGROUP_SPEC_ROOT=$ADMITTED_CGROUP_ROOT"
      PROCESS_CONTROL_REQUIRE_CGROUP_BIRTH=1
    )
  fi
fi
run_host_process_control_gate() {
  local label=$1 compiler=$2 receipt="$NATIVE_ROOT/receipts/$1"
  local command_code=0 evidence_code=0 resolved raw_target dependency_link
  shift 2
  [[ ! -e "$receipt" ]] || return 1
  mkdir -p "$receipt"
  dependency_link="$PC_HOST/lib/native-kernel"
  [[ -L "$dependency_link" ]] || return 1
  raw_target=$(readlink "$dependency_link") || return 1
  print -r -- "$raw_target" > "$receipt/dependency-link.before"
  resolved=$(cd "$dependency_link" && pwd -P) || return 1
  [[ "$resolved" == "$NK_HOST" ]] || return 1
  print -r -- "$resolved" > "$receipt/dependency-root.before"
  print -r -- "$compiler" > "$receipt/compiler.path"
  shasum -a 256 "$compiler" > "$receipt/compiler.sha256"
  "$compiler" --version > "$receipt/compiler.txt" 2>&1 || return 1
  print -r -- "${(q)@}" > "$receipt/command.zsh"
  {
    print -r -- "SHARDS_OVERRIDE=$HOST_OVERRIDE"
    print -r -- \
      "CRYSTAL_CACHE_DIR=$NATIVE_ROOT/cache-process-control-$label"
    print -r -- "CRYSTAL=$compiler"
    print -r -- "CRYSTAL_SPEC_COMPILER_BIN=$compiler"
    print -rl -- "${HOST_PROCESS_ENV[@]}"
  } > "$receipt/environment.txt"
  repository_content_manifest "$NK_HOST" \
    > "$receipt/native-kernel.before" || return 1
  repository_content_manifest "$PC_HOST" \
    > "$receipt/process-control.before" || return 1
  (
    cd "$PC_HOST"
    env SHARDS_OVERRIDE="$HOST_OVERRIDE" \
      CRYSTAL_CACHE_DIR="$NATIVE_ROOT/cache-process-control-$label" \
      CRYSTAL="$compiler" CRYSTAL_SPEC_COMPILER_BIN="$compiler" \
      "${HOST_PROCESS_ENV[@]}" "$@"
  ) > "$receipt/stdout" 2> "$receipt/stderr" || command_code=$?
  print -r -- "$command_code" > "$receipt/status"
  repository_content_manifest "$NK_HOST" \
    > "$receipt/native-kernel.after" || evidence_code=1
  repository_content_manifest "$PC_HOST" \
    > "$receipt/process-control.after" || evidence_code=1
  [[ -L "$dependency_link" ]] || evidence_code=1
  raw_target=$(readlink "$dependency_link") || evidence_code=1
  print -r -- "$raw_target" > "$receipt/dependency-link.after"
  resolved=$(cd "$dependency_link" && pwd -P) || evidence_code=1
  print -r -- "$resolved" > "$receipt/dependency-root.after"
  [[ "$resolved" == "$NK_HOST" ]] || evidence_code=1
  cmp -s "$receipt/dependency-link.before" \
    "$receipt/dependency-link.after" || evidence_code=1
  cmp -s "$receipt/dependency-root.before" \
    "$receipt/dependency-root.after" || evidence_code=1
  cmp -s "$receipt/native-kernel.before" \
    "$receipt/native-kernel.after" || evidence_code=1
  cmp -s "$receipt/process-control.before" \
    "$receipt/process-control.after" || evidence_code=1
  (( command_code == 0 && evidence_code == 0 ))
}

if [[ "$HOST_PROFILE" == linux-* ]]; then
  run_host_process_control_gate "$HOST_PROFILE-current" \
    "$CURRENT_CRYSTAL" "$HOST_MAKE" check
  run_host_process_control_gate "$HOST_PROFILE-floor" \
    "$FLOOR_CRYSTAL" "$HOST_MAKE" check
else
  run_host_process_control_gate "$HOST_PROFILE-check-current" \
    "$CURRENT_CRYSTAL" "$HOST_MAKE" check
  run_host_process_control_gate "$HOST_PROFILE-check-floor" \
    "$FLOOR_CRYSTAL" "$HOST_MAKE" check
  run_host_process_control_gate "$HOST_PROFILE-audit-current" \
    "$CURRENT_CRYSTAL" "$CURRENT_CRYSTAL" run \
    scripts/check-darwin.cr -- \
    "$NATIVE_ROOT/receipts/$HOST_PROFILE-audit-current-artifacts"
  run_host_process_control_gate "$HOST_PROFILE-audit-floor" \
    "$FLOOR_CRYSTAL" "$FLOOR_CRYSTAL" run \
    scripts/check-darwin.cr -- \
    "$NATIVE_ROOT/receipts/$HOST_PROFILE-audit-floor-artifacts"
fi
```

The directories created by `run_host_process_control_gate` are gate evidence
directories, not final receipts. The host-level JSON below indexes all of them.
For Linux its required evidence keys are `native-kernel.current`,
`native-kernel.floor`, `process-control.check.current` and
`process-control.check.floor`. For Darwin it also requires
`process-control.audit.current` and `process-control.audit.floor`, including the
two adjacent audit-artifact directories. Linux evidence requires pidfd; when
cgroup birth is admitted, it requires that capability too. No current evidence
substitutes for floor evidence, check for audit, or one architecture for another.

After the last build or test command, make and verify the `after` copy:

```zsh
repository_content_copy "$NATIVE_ROOT/source/Native-Kernel" \
  "$NATIVE_ROOT/after/Native-Kernel"
repository_content_copy "$NATIVE_ROOT/source/Process-Control" \
  "$NATIVE_ROOT/after/Process-Control"
repository_content_manifest "$NATIVE_ROOT/after/Native-Kernel" \
  > "$NATIVE_ROOT/manifests/after-native-kernel.sha256"
repository_content_manifest "$NATIVE_ROOT/after/Process-Control" \
  > "$NATIVE_ROOT/manifests/after-process-control.sha256"
cmp -s "$NK_PLAN_SCRATCH/phase-c-native-kernel.sha256" \
  "$NATIVE_ROOT/manifests/after-native-kernel.sha256"
cmp -s "$NK_PLAN_SCRATCH/phase-c-process-control.sha256" \
  "$NATIVE_ROOT/manifests/after-process-control.sha256"
compare_native_copy after-native-kernel \
  "$PHASE_SNAPSHOTS/C/Native-Kernel" "$NATIVE_ROOT/after/Native-Kernel"
compare_native_copy after-process-control \
  "$PHASE_SNAPSHOTS/C/Process-Control" "$NATIVE_ROOT/after/Process-Control"
```

Store stdout, stderr and status separately for all four comparisons, then write
and independently verify the one host receipt. Set `HOST_TRANSLATION_STATE` to
`native` or `translated`. A Linux passed receipt requires
`PIDFD_ADMISSION=admitted`; set `CGROUP_BIRTH_ADMISSION` to `admitted` or
`unavailable` from the recorded preflight. On Darwin set both to
`not-applicable`.

```zsh
NATIVE_RECEIPT="$NATIVE_ROOT/native-copy.json"
[[ "$HOST_TRANSLATION_STATE" == native || \
   "$HOST_TRANSLATION_STATE" == translated ]]
if [[ "$HOST_PROFILE" == linux-* ]]; then
  [[ "$PIDFD_ADMISSION" == admitted ]]
  [[ "$CGROUP_BIRTH_ADMISSION" == admitted || \
     "$CGROUP_BIRTH_ADMISSION" == unavailable ]]
else
  PIDFD_ADMISSION=not-applicable
  CGROUP_BIRTH_ADMISSION=not-applicable
fi
[[ -d "$NATIVE_ROOT/receipts/native-kernel-current" ]]
[[ -d "$NATIVE_ROOT/receipts/native-kernel-floor" ]]
/usr/bin/python3 -I "$NK_HOST/scripts/ci/namespace_compare.py" \
  native-receipt \
  --root "$NATIVE_ROOT" \
  --profile "$HOST_PROFILE" \
  --translation "$HOST_TRANSLATION_STATE" \
  --current-compiler "$CURRENT_CRYSTAL" \
  --floor-compiler "$FLOOR_CRYSTAL" \
  --pidfd "$PIDFD_ADMISSION" \
  --cgroup-birth "$CGROUP_BIRTH_ADMISSION" \
  --phase-c-native-kernel \
  "$NK_PLAN_SCRATCH/phase-c-native-kernel.sha256" \
  --phase-c-process-control \
  "$NK_PLAN_SCRATCH/phase-c-process-control.sha256" \
  --output "$NATIVE_RECEIPT"
/usr/bin/python3 -m json.tool "$NATIVE_RECEIPT" > /dev/null
/usr/bin/python3 -I "$NK_HOST/scripts/ci/namespace_compare.py" \
  verify-native-receipt --root "$NATIVE_ROOT" \
  --receipt "$NATIVE_RECEIPT"
```

The writer accepts only the exact evidence-directory names established above.
It validates every zero status, compiler identity, resolved dependency,
capability requirement, Phase C inventory, before/after comparison and source
manifest before emitting. Schema `native-copy/1` has required top-level fields
`schema`, `status`, `profile`, `host`, `translation`, `compilers`,
`capabilities`, `phase_c`, `evidence`, `comparisons` and `source_unchanged`.
Every `evidence` entry records its relative directory and a sorted path/SHA-256
file manifest, so logs, commands, environments, statuses and adjacent artifact
directories are transitively bound. Require `status: passed` and
`source_unchanged: true`.

Record this one JSON path as exactly one of
`FINAL_PC_DARWIN_ARM_HOST_RECEIPT`, `FINAL_PC_DARWIN_X86_HOST_RECEIPT`,
`FINAL_PC_LINUX_ARM_HOST_RECEIPT` or `FINAL_PC_LINUX_X86_HOST_RECEIPT`, selected
by `HOST_PROFILE`. These four variables, not the gate evidence directories, are
the Process-Control native receipt contract. A missing, changed or unbound copy
is a failed native gate.

The translated x86-64 Linux host's baseline `ENOSYS`, if still present, is an
unavailable native cell, not a pass. Record it under `Limits`; it does not block
`Implemented locally` when all mandatory local gates and every admitted native
gate pass. It blocks `Release qualified` until an untranslated x86-64 Linux host
executes the mechanism from the final source.

Generic-entry probes:

Run this matrix with both selected compilers. A refused target is `unrun` only
when the dependency-free smoke fixture also fails for that compiler and target.
Every compiler-capable refused cell must contain the exact stable refusal text.

```zsh
GENERIC_ACCEPTED=(
  aarch64-apple-darwin
  x86_64-apple-darwin
  aarch64-linux-gnu
  aarch64-linux-musl
  x86_64-linux-gnu
  x86_64-linux-musl
)
GENERIC_REFUSED=(
  x86_64-pc-windows-msvc
  aarch64-pc-windows-msvc
  x86_64-unknown-freebsd
  aarch64-linux-android24
  riscv64-linux-gnu
  armv7-apple-darwin
)
GENERIC_REFUSAL='Native-Kernel supports only 64-bit Darwin ARM64/x86-64 and '
GENERIC_REFUSAL+='non-Android 64-bit GNU/musl Linux AArch64/x86-64.'
GENERIC_MATRIX="$NK_PLAN_SCRATCH/generic-entry-matrix"
[[ ! -e "$GENERIC_MATRIX" ]]
mkdir -p "$GENERIC_MATRIX/logs" "$GENERIC_MATRIX/manifests"
print -r -- $'compiler\ttarget\texpectation\tstatus\tlog' > "$GENERIC_MATRIX/receipt.tsv"
generic_failures=0

for label compiler in current "$CURRENT_CRYSTAL" floor "$FLOOR_CRYSTAL"; do
  for expectation in accepted refused; do
    if [[ "$expectation" == accepted ]]; then
      targets=("${GENERIC_ACCEPTED[@]}")
    else
      targets=("${GENERIC_REFUSED[@]}")
    fi
    for target in "${targets[@]}"; do
      cell="$label-$target"
      code=0
      proof_manifest > "$GENERIC_MATRIX/manifests/$cell.before" || code=$?
      if (( code == 0 )); then
        CRYSTAL_CACHE_DIR="$NK_PLAN_SCRATCH/cache-generic-$cell" \
          "$compiler" build --no-codegen --cross-compile --target "$target" \
          "$NK_PROOF/scripts/ci/generic_entry.cr" \
          > "$GENERIC_MATRIX/logs/$cell.log" 2>&1 || code=$?
      fi

      if [[ "$expectation" == accepted ]]; then
        if (( code == 0 )); then
          cell_status=passed
        else
          cell_status=failed
          (( generic_failures += 1 ))
        fi
      elif (( code != 0 )) && rg -qF -- "$GENERIC_REFUSAL" "$GENERIC_MATRIX/logs/$cell.log"; then
        cell_status=refused
      elif (( code == 0 )); then
        cell_status=failed
        (( generic_failures += 1 ))
      else
        smoke_code=0
        CRYSTAL_CACHE_DIR="$NK_PLAN_SCRATCH/cache-smoke-$cell" \
          "$compiler" build --no-codegen --cross-compile --target "$target" \
          "$NK_PROOF/scripts/ci/target_smoke.cr" \
          > "$GENERIC_MATRIX/logs/$cell.smoke.log" 2>&1 || smoke_code=$?
        if (( smoke_code != 0 )); then
          cell_status=unrun
        else
          cell_status=failed
          (( generic_failures += 1 ))
        fi
      fi

      after_code=0
      proof_manifest > "$GENERIC_MATRIX/manifests/$cell.after" || after_code=$?
      cmp -s "$GENERIC_MATRIX/manifests/$cell.before" \
        "$GENERIC_MATRIX/manifests/$cell.after" || after_code=$?
      if (( after_code != 0 )); then
        cell_status=failed
        (( generic_failures += 1 ))
      fi
      print -r -- "$label"$'\t'"$target"$'\t'"$expectation"$'\t'"$cell_status"$'\t'"logs/$cell.log" \
        >> "$GENERIC_MATRIX/receipt.tsv"
    done
  done
done
[[ $(wc -l < "$GENERIC_MATRIX/receipt.tsv") -eq 25 ]]
(( generic_failures == 0 ))
```

The receipt must contain twelve `passed` rows for accepted profiles and, for
refused profiles, only `refused` or compiler-incapable `unrun` rows. No cell may
be omitted.

#### Produce comparable artifact evidence

Qualify the evidence tools before using their outputs:

```zsh
proof_manifest > "$NK_PLAN_SCRATCH/namespace-evidence-tests.before.sha256"
python3 -I "$NK_PROOF/scripts/ci/test_namespace_evidence.py" -v \
  > "$NK_PLAN_SCRATCH/namespace-evidence-tests.log" 2>&1
rg -qF -- 'Ran 18 tests' "$NK_PLAN_SCRATCH/namespace-evidence-tests.log"
rg -qF -- 'OK' "$NK_PLAN_SCRATCH/namespace-evidence-tests.log"
proof_manifest > "$NK_PLAN_SCRATCH/namespace-evidence-tests.after.sha256"
cmp -s "$NK_PLAN_SCRATCH/namespace-evidence-tests.before.sha256" \
  "$NK_PLAN_SCRATCH/namespace-evidence-tests.after.sha256"
```

The 18 tests are the twelve planted faults listed in Phase A plus valid controls
for namespace evidence, artifact comparison, route/stale-name detection, seal
verification, source/chain verification and native-receipt verification. A tool
output is inadmissible until every negative and valid control passes under the
final tool bytes.

Run `scripts/ci/namespace_evidence.cr` against both source trees with both
selected compilers. The script prints JSON to stdout and no other stdout text:

```zsh
NAMESPACE_EVIDENCE="$NK_PLAN_SCRATCH/namespace-evidence"
[[ ! -e "$NAMESPACE_EVIDENCE" ]]
mkdir -p "$NAMESPACE_EVIDENCE"
proof_manifest > "$NAMESPACE_EVIDENCE/inputs.before.sha256"
for label compiler in current "$CURRENT_CRYSTAL" floor "$FLOOR_CRYSTAL"; do
  compiler_path=$("$compiler" env CRYSTAL_PATH)
  stdlib_path=${compiler_path#lib:}
  CRYSTAL_PATH="$NK_PLAN_SCRATCH/committed/Native-Kernel/src:$stdlib_path" \
    CRYSTAL_CACHE_DIR="$NK_PLAN_SCRATCH/cache-evidence-before-$label" \
    "$compiler" run "$NK_PROOF/scripts/ci/namespace_evidence.cr" -- \
    --surface before > "$NAMESPACE_EVIDENCE/$label.before.json" \
    2> "$NAMESPACE_EVIDENCE/$label.before.stderr"
  CRYSTAL_PATH="$NK_PROOF/src:$stdlib_path" \
    CRYSTAL_CACHE_DIR="$NK_PLAN_SCRATCH/cache-evidence-after-$label" \
    "$compiler" run -Dnamespace_after \
    "$NK_PROOF/scripts/ci/namespace_evidence.cr" -- \
    --surface after > "$NAMESPACE_EVIDENCE/$label.after.json" \
    2> "$NAMESPACE_EVIDENCE/$label.after.stderr"
  python3 -m json.tool "$NAMESPACE_EVIDENCE/$label.before.json" > /dev/null
  python3 -m json.tool "$NAMESPACE_EVIDENCE/$label.after.json" > /dev/null
done
```

Require empty stderr files and schema `namespace-evidence/1`. Each ABI row has
`logical_name`, `size`, `alignment` and ordered `fields`; each field has `name`,
`crystal_type` and `offset`. Each constant row has `logical_name`,
`crystal_type` and decimal `value`. The generator contains compile-time
`typeof` assertions for every suffixed literal in Appendix A.

Capture the complete baseline and final example inventories with TAP dry runs:

```zsh
(
  cd "$NK_PLAN_SCRATCH/committed/Native-Kernel"
  CRYSTAL_CACHE_DIR="$NK_PLAN_SCRATCH/cache-tap-before" \
    "$CURRENT_CRYSTAL" spec --no-color --error-on-warnings -- \
    --dry-run --tap > "$NAMESPACE_EVIDENCE/specs.before.tap"
)
(
  cd "$NK_PROOF"
  CRYSTAL_CACHE_DIR="$NK_PLAN_SCRATCH/cache-tap-after" \
    "$CURRENT_CRYSTAL" spec --no-color --error-on-warnings -- \
    --dry-run --tap > "$NAMESPACE_EVIDENCE/specs.after.tap"
)
```

Run `scripts/ci/route_closure.cr` against the final custom-entry fixtures. Its
canonical JSON schema is `route-closure/1` and its exact route sets are:

```zsh
CRYSTAL_CACHE_DIR="$NK_PLAN_SCRATCH/cache-route-closure" \
  "$CURRENT_CRYSTAL" run "$NK_PROOF/scripts/ci/route_closure.cr" -- \
  --root "$NK_PROOF" --output "$NAMESPACE_EVIDENCE/route-closure.json"
python3 -m json.tool "$NAMESPACE_EVIDENCE/route-closure.json" > /dev/null
```

- `pid` requires `Native::Kernel::Darwin::Syscall::Number::KILL` and forbids
  `Native::Kernel::Darwin::Process::Info::Call::SIGNAL_AUDIT_TOKEN` and
  `Native::Kernel::Linux::Syscall::Number::PIDFD_SEND_SIGNAL`.
- `audit_token` requires
  `Native::Kernel::Darwin::Syscall::Number::PROC_INFO` and
  `Native::Kernel::Darwin::Process::Info::Call::SIGNAL_AUDIT_TOKEN`; it forbids
  `Native::Kernel::Darwin::Syscall::Number::KILL` and
  `Native::Kernel::Linux::Syscall::Number::PIDFD_SEND_SIGNAL`.
- `pidfd` requires
  `Native::Kernel::Linux::Syscall::Number::PIDFD_SEND_SIGNAL` and forbids
  `Native::Kernel::Darwin::Syscall::Number::KILL` and
  `Native::Kernel::Darwin::Process::Info::Call::SIGNAL_AUDIT_TOKEN`.

Finally run the comparator, using the exact baseline/final native receipt paths
recorded by Phase 0 and Phase D:

```zsh
python3 "$NK_PROOF/scripts/ci/namespace_compare.py" compare \
  --evidence "$NAMESPACE_EVIDENCE" \
  --renames "$NK_PLAN_SCRATCH/renames.tsv" \
  --method-renames "$NK_PLAN_SCRATCH/method-renames.tsv" \
  --route-closure "$NAMESPACE_EVIDENCE/route-closure.json" \
  --before-darwin-current "$BASELINE_DARWIN_CURRENT_RECEIPT" \
  --after-darwin-current "$FINAL_DARWIN_CURRENT_RECEIPT" \
  --before-darwin-floor "$BASELINE_DARWIN_FLOOR_RECEIPT" \
  --after-darwin-floor "$FINAL_DARWIN_FLOOR_RECEIPT" \
  --before-linux-arm-current "$BASELINE_LINUX_ARM_CURRENT_RECEIPT" \
  --after-linux-arm-current "$FINAL_LINUX_ARM_CURRENT_RECEIPT" \
  --before-linux-arm-floor "$BASELINE_LINUX_ARM_FLOOR_RECEIPT" \
  --after-linux-arm-floor "$FINAL_LINUX_ARM_FLOOR_RECEIPT" \
  --before-linux-x86-current "$BASELINE_LINUX_X86_CURRENT_RECEIPT" \
  --after-linux-x86-current "$FINAL_LINUX_X86_CURRENT_RECEIPT" \
  --before-linux-x86-floor "$BASELINE_LINUX_X86_FLOOR_RECEIPT" \
  --after-linux-x86-floor "$FINAL_LINUX_X86_FLOOR_RECEIPT" \
  --output "$NAMESPACE_EVIDENCE/comparison.json"
```

The comparator normalizes only Appendix B.1 qualified names, Appendix B.2 method
owner/symbol names, Phase C source paths, absolute scratch/proof prefixes and
LLVM metadata/temporary-label numbers in first-appearance order. It does not
normalize method signatures or call topology, opcodes, integer constants,
argument order, call targets after mapping, inline-assembly text or multiplicity,
imports, ABI fields or route sets. It requires:

1. schema-valid, byte-equivalent logical ABI and typed constants;
2. identical raw-call constant sequences and inline-assembly multisets;
3. identical normalized reachable LLVM instruction streams;
4. empty Darwin undefined-import lists and the Linux static/no-import boundary;
5. no missing baseline TAP example name and an explicit list of additions;
6. the exact `route-closure/1` sets above; and
7. `Metadata::Source::FILES` coverage plus Process-Control's dependency
   fingerprint for the final paths and bytes.

The output schema `namespace-comparison/1` contains input SHA-256 values, applied
normalizations, per-check counts, every difference and `status`. Require
`status: passed` and an empty differences array. Binary hashes may differ; no
other artifact difference is accepted.

Run the same final scanner bytes against the committed snapshots in report-only
mode, then against final source with the exact allowlist. The baseline report is
descriptive; it does not authorize any final match.

```zsh
STALE_TOOL="$NK_PROOF/scripts/ci/stale_names.zsh"
STALE_PATTERNS="$NK_PROOF/scripts/ci/namespace_removed_patterns.tsv"
STALE_ALLOWLIST="$NK_PROOF/scripts/ci/stale_name_allowlist.tsv"
proof_manifest > "$NAMESPACE_EVIDENCE/stale-before-command.before.sha256"
zsh "$STALE_TOOL" \
  --patterns "$STALE_PATTERNS" \
  --report-only \
  --revision "Native-Kernel=$NK_BASELINE_COMMIT" \
  --revision "Process-Control=$PC_BASELINE_COMMIT" \
  --output "$NAMESPACE_EVIDENCE/stale-names.before.tsv" \
  "$NK_PLAN_SCRATCH/committed/Native-Kernel" \
  "$NK_PLAN_SCRATCH/committed/Process-Control"
proof_manifest > "$NAMESPACE_EVIDENCE/stale-before-command.after.sha256"
cmp -s "$NAMESPACE_EVIDENCE/stale-before-command.before.sha256" \
  "$NAMESPACE_EVIDENCE/stale-before-command.after.sha256"
NK_PHASE_C_MANIFEST_SHA256=$(shasum -a 256 \
  "$NK_PLAN_SCRATCH/phase-c-native-kernel.sha256" | awk '{print $1}')
PC_PHASE_C_MANIFEST_SHA256=$(shasum -a 256 \
  "$NK_PLAN_SCRATCH/phase-c-process-control.sha256" | awk '{print $1}')
proof_manifest > "$NAMESPACE_EVIDENCE/stale-after-command.before.sha256"
zsh "$STALE_TOOL" \
  --patterns "$STALE_PATTERNS" \
  --allowlist "$STALE_ALLOWLIST" \
  --revision "Native-Kernel=proof:C:$NK_PHASE_C_MANIFEST_SHA256" \
  --revision "Process-Control=proof:C:$PC_PHASE_C_MANIFEST_SHA256" \
  --output "$NAMESPACE_EVIDENCE/stale-names.after.tsv" \
  "$NK_PROOF" "$PC_PROOF"
proof_manifest > "$NAMESPACE_EVIDENCE/stale-after-command.after.sha256"
cmp -s "$NAMESPACE_EVIDENCE/stale-after-command.before.sha256" \
  "$NAMESPACE_EVIDENCE/stale-after-command.after.sha256"
proof_manifest > "$NAMESPACE_EVIDENCE/inputs.after.sha256"
cmp -s "$NAMESPACE_EVIDENCE/inputs.before.sha256" \
  "$NAMESPACE_EVIDENCE/inputs.after.sha256"
```

Require zero `unexplained` final rows. Every `allowed` row must match its exact
tracked kind, pattern, repository, path and line hash, and must carry the
externally supplied source revision in the output receipt; unused or duplicate
allowlist rows fail the gate. Search separately for stored or externally emitted
type-name strings. Do not change a stored or published token without a separate
decision.

Release-only native gates:

1. Establish the exact clean final source:

   ```zsh
   git -C "$NK_LIVE" ls-files --error-unmatch docs/namespace-plan.md &&
     [[ -z "$(git -C "$NK_LIVE" status --porcelain=v1 --untracked-files=all)" ]] &&
     NK_FINAL_COMMIT=$(git -C "$NK_LIVE" rev-parse HEAD) &&
     NK_FINAL_TREE=$(git -C "$NK_LIVE" rev-parse 'HEAD^{tree}') &&
     PC_FINAL_COMMIT=$(git -C "$PC_LIVE" rev-parse HEAD) &&
     PC_FINAL_TREE=$(git -C "$PC_LIVE" rev-parse 'HEAD^{tree}') &&
     [[ "$NK_FINAL_COMMIT" == "$NK_CHECKPOINT_C_COMMIT" ]] &&
     [[ "$NK_FINAL_TREE" == "$NK_CHECKPOINT_C_TREE" ]] &&
     [[ "$PC_FINAL_COMMIT" == "$PC_CHECKPOINT_C_COMMIT" ]] &&
     [[ "$PC_FINAL_TREE" == "$PC_CHECKPOINT_C_TREE" ]]
   ```

   The release chain qualifies Native-Kernel at `NK_FINAL_COMMIT`. Record
   `PC_FINAL_COMMIT` and `PC_FINAL_TREE` as the exact consumer-evidence commit;
   Process-Control publication or hosted qualification is outside this runbook.
   The Process-Control worktree may still contain the four named pre-existing
   edits, but neither they nor any other working-tree byte is part of
   `PC_FINAL_TREE` or the release chain.
2. After the owner publishes `NK_FINAL_COMMIT`, run its hosted Linux
   and macOS workflows. The Linux evidence must include an untranslated x86-64
   host that executes every admitted process mechanism. Record each workflow run
   ID, URL, event, conclusion and `head_sha`; require `conclusion == success` and
   `head_sha == NK_FINAL_COMMIT` before joining hosted evidence to the release
   chain.
3. On a native Intel Darwin build host with Xcode selected, create or obtain an
   explicit clean checkout of the published final commit. Supply the expected
   commit and tree through the release record, then bind every release command
   to that checkout:

   ```zsh
   NK_RELEASE_CHECKOUT=/absolute/path/to/clean/Native-Kernel.cr
   [[ -n "$NK_FINAL_COMMIT" && -n "$NK_FINAL_TREE" ]]
   [[ -z "$(git -C "$NK_RELEASE_CHECKOUT" \
     status --porcelain=v1 --untracked-files=all)" ]]
   [[ "$(git -C "$NK_RELEASE_CHECKOUT" rev-parse HEAD)" == \
      "$NK_FINAL_COMMIT" ]]
   [[ "$(git -C "$NK_RELEASE_CHECKOUT" rev-parse 'HEAD^{tree}')" == \
      "$NK_FINAL_TREE" ]]
   (
     cd "$NK_RELEASE_CHECKOUT"
     /usr/bin/python3 -I \
       "$NK_RELEASE_CHECKOUT/scripts/compat/build_monterey_foundations.py" \
       --current /absolute/path/to/crystal-1.22.2/bin/crystal \
       --floor /absolute/path/to/crystal-1.10.0/bin/crystal \
       --output /external/final-monterey-foundations
   )
   ```

   The build uses Crystal 1.22.2 and 1.10.0. Require separate manifest-bound
   spawn and task-token bundles. Their source
   manifests and hashes must bind the committed final tree. Each compiler must
   produce development and release artifacts. Every executable must be thin
   x86-64 with a macOS 12.0 minimum, bounded version-zero chained fixups, a
   verified ad hoc signature and no undefined imports.
4. Retain the complete generated parent directory on the build host, including
   `build-receipt.json`, both campaign directories and build logs. Verify every
   path and SHA-256 in `build-receipt.json.sources` against the same path at
   `NK_FINAL_COMMIT`:

   ```zsh
   /usr/bin/python3 -I \
     "$NK_RELEASE_CHECKOUT/scripts/ci/namespace_compare.py" verify-source \
     --repository "$NK_RELEASE_CHECKOUT" \
     --receipt /external/final-monterey-foundations/build-receipt.json \
     --commit "$NK_FINAL_COMMIT"
   ```

   Require `source_unchanged: true`. Verify each
   `campaigns.KIND.manifest_sha256` against the actual `KIND/manifest.json`.
   Write the chain receipt with the validating helper:

   ```zsh
   /usr/bin/python3 -I \
     "$NK_RELEASE_CHECKOUT/scripts/ci/namespace_compare.py" chain \
     --commit "$NK_FINAL_COMMIT" --tree "$NK_FINAL_TREE" \
     --build-receipt /external/final-monterey-foundations/build-receipt.json \
     --spawn-manifest /external/final-monterey-foundations/spawn/manifest.json \
     --task-token-manifest /external/final-monterey-foundations/task-token/manifest.json \
     --output /external/final-monterey-foundations/qualification-chain.json
   ```
5. Create a new bounded handoff whose `payload/` contains only
   `build-receipt.json`, the chain receipt, `namespace_compare.py`, and the
   complete `spawn/` and `task-token/` directories. Seal every regular payload
   file:

   ```zsh
   HANDOFF=/external/final-handoff
   [[ ! -e "$HANDOFF" ]]
   mkdir -p "$HANDOFF/payload"
   cp /external/final-monterey-foundations/build-receipt.json \
     /external/final-monterey-foundations/qualification-chain.json \
     "$NK_RELEASE_CHECKOUT/scripts/ci/namespace_compare.py" \
     "$HANDOFF/payload/"
   cp -R /external/final-monterey-foundations/spawn \
     /external/final-monterey-foundations/task-token "$HANDOFF/payload/"
   committed_verifier=$(git -C "$NK_RELEASE_CHECKOUT" show \
     "$NK_FINAL_COMMIT:scripts/ci/namespace_compare.py" | shasum -a 256 | awk '{print $1}')
   copied_verifier=$(shasum -a 256 "$HANDOFF/payload/namespace_compare.py" | awk '{print $1}')
   [[ "$copied_verifier" == "$committed_verifier" ]]
   /usr/bin/python3 -I \
     "$NK_RELEASE_CHECKOUT/scripts/ci/namespace_compare.py" seal \
     --root "$HANDOFF/payload" \
     --output "$HANDOFF/transfer-manifest.json"
   TRANSFER_MANIFEST_SHA256=$(shasum -a 256 \
     "$HANDOFF/transfer-manifest.json" | awk '{print $1}')
   print -r -- "$TRANSFER_MANIFEST_SHA256" \
     > /external/final-handoff-transfer-manifest.sha256
   ```

   Keep `/external/final-handoff-transfer-manifest.sha256` outside the handoff and
   deliver its value through the release handoff record, not beside the mutable
   payload. Build logs stay in the retained build-host parent and are not claimed
   as transferred.
6. Transfer exactly the bounded handoff to the untranslated macOS 12.7.6 Intel
   Mini. Verify every payload byte before running either campaign:

   ```zsh
   EXPECTED_NK_FINAL_COMMIT='commit from the separate build-host release record'
   EXPECTED_NK_FINAL_TREE='tree from the separate build-host release record'
   EXPECTED_TRANSFER_MANIFEST_SHA256='digest from the separate build-host release record'
   ACTUAL_TRANSFER_MANIFEST_SHA256=$(shasum -a 256 \
     /path/to/handoff/transfer-manifest.json | awk '{print $1}')
   [[ "$ACTUAL_TRANSFER_MANIFEST_SHA256" == \
      "$EXPECTED_TRANSFER_MANIFEST_SHA256" ]]
   /usr/bin/python3 -I /path/to/handoff/payload/namespace_compare.py \
     verify-seal --root /path/to/handoff/payload \
     --manifest /path/to/handoff/transfer-manifest.json
   /usr/bin/python3 -I /path/to/handoff/payload/namespace_compare.py \
     verify-chain \
     --chain /path/to/handoff/payload/qualification-chain.json \
     --build-receipt /path/to/handoff/payload/build-receipt.json \
     --spawn-manifest /path/to/handoff/payload/spawn/manifest.json \
     --task-token-manifest /path/to/handoff/payload/task-token/manifest.json \
     --expected-commit "$EXPECTED_NK_FINAL_COMMIT" \
     --expected-tree "$EXPECTED_NK_FINAL_TREE"
   ```

   Supply all three expected values through the release handoff record, outside
   the transferred directory. `verify-chain` must return zero after recomputing
   the build-receipt and campaign-manifest hashes and matching the expected
   Native-Kernel commit and tree. Then run each manifest-bound runner in Python
   isolated mode with a new external output directory:

   ```zsh
   cd /path/to/handoff/payload/spawn
   /usr/bin/python3 -I monterey_foundations_runner.py \
     --output /external/final-monterey-spawn-result

   cd /path/to/handoff/payload/task-token
   /usr/bin/python3 -I monterey_foundations_runner.py \
     --output /external/final-monterey-task-token-result
   ```

   Accept the gate only when all 28 spawn and 16 task-token executions pass
   across both compilers and both modes, both runners verify every payload before
   and after execution, and each Mini `receipt.json.manifest_sha256` equals both
   the transferred bundle manifest and its campaign hash in the retained parent
   build receipt. Preserve this chain as:

   ```text
   NK_FINAL_COMMIT and NK_FINAL_TREE
     -> build-receipt.json source inventory
     -> campaign manifest SHA-256
     -> transferred bundle manifest SHA-256
     -> Mini receipt manifest SHA-256
   ```

   A preflight or translated run is unqualified.

Cross-compilation, Rosetta or another macOS release does not replace the Intel
Mini receipt. Hosted CI and the Mini are release-qualification evidence, not a
substitute for local implementation gates.

## Failure handling

Stop before committing or claiming a status when any of these is true:

- a source authority disagrees with Appendix A;
- a proposed name changes domain meaning;
- ABI field type, signedness, size, alignment or offset changes;
- syscall arguments, result decoding, errno/Mach-code provenance, ownership or
  fallback behavior changes;
- name resolution reports an unexplained capture;
- a source or assembly fingerprint omits a built file;
- CST remains inconclusive after the retry and no alternate proof is approved;
- a check changes a repository outside Native-Kernel, Process-Control or the
  approved workspace ledger;
- user work overlaps a required hunk; or
- a required native host is unavailable while claiming `Release qualified`.

When blocked, return the output contract below with `Status: Blocked`. Name the
failed condition, evidence, smallest missing input and last completed phase. Do
not present an unrun or inconclusive gate as passed.

An unavailable macOS 12 Intel Mini does not invalidate `Implemented locally`.
It blocks `Release qualified` until the final-source receipt exists.

## Output contract

At each checkpoint and final handoff, return these sections:

1. `Status`: `In progress`, `Blocked`, `Implemented locally`, `Committed`, or
   `Release qualified`.
2. `Revisions`: repository commits and whether proof trees contain patches.
3. `Changes`: completed phase and exact public surfaces changed.
4. `Evidence`: commands run, counts, native hosts and receipt paths.
5. `Limits`: unrun, unavailable, stale or owner-accepted gates.
6. `Repository state`: branch, staged paths, uncommitted paths and locks.
7. `Next action`: the next phase or smallest action that clears a block.

Status requirements:

- `Implemented locally`: all mandatory Phase D local gates pass in source-bound
  proof trees, every admitted native gate passes, and unavailable native cells
  are named under `Limits` rather than counted as passes.
- `Committed`: local implementation passes and authorized paired A, B and C
  commits exist with declared path/hunk scope.
- `Release qualified`: committed final source has hosted Linux/macOS evidence,
  an executing untranslated Linux x86-64 receipt, a manifest-bound macOS 12.7.6
  Intel receipt with all 44 executions and the complete commit-to-Mini manifest
  chain above, and no pending native or owner-acceptance gate.

Do not claim `Committed` merely because local edits exist. Do not claim
`Release qualified` from cross-compilation or another macOS release.

At final handoff, record the last manifest and repository states and release
only the locks created for this work. Report each released lock under
`Repository state`. If workspace edits were authorized, update the workspace
namespace table and ledger and include those paths in the authorized workspace
commit. If the work remained proof-only, do not mutate the workspace: put the
exact proposed unified diff for the table and ledger under `Limits`, and name
applying that diff as the `Next action`.

## Appendix A: exact Darwin constants

### A.1 BSD syscall numbers

All constants are under `Native::Kernel::Darwin::Syscall::Number`.

| Constant                |    Number | Current wrapper use                     |
| ----------------------- | --------: | --------------------------------------- |
| `EXIT`                  |   `1_i32` | process exit                            |
| `FORK`                  |   `2_i32` | process fork                            |
| `READ`                  |   `3_i32` | descriptor read                         |
| `WRITE`                 |   `4_i32` | descriptor write                        |
| `OPEN`                  |   `5_i32` | descriptor open                         |
| `CLOSE`                 |   `6_i32` | descriptor close                        |
| `WAIT4`                 |   `7_i32` | waitpid/wait4                           |
| `GETPID`                |  `20_i32` | current PID                             |
| `KILL`                  |  `37_i32` | PID signal                              |
| `GETPPID`               |  `39_i32` | parent PID                              |
| `PIPE`                  |  `42_i32` | descriptor pipe                         |
| `SIGACTION`             |  `46_i32` | signal action                           |
| `SIGPROCMASK`           |  `48_i32` | signal mask                             |
| `EXECVE`                |  `59_i32` | process exec                            |
| `SETPGID`               |  `82_i32` | process group set                       |
| `FCNTL`                 |  `92_i32` | descriptor control                      |
| `SELECT`                |  `93_i32` | bounded event sleep                     |
| `SOCKET`                |  `97_i32` | socket creation                         |
| `CONNECT`               |  `98_i32` | socket connect                          |
| `GETRUSAGE`             | `117_i32` | terminal resource usage                 |
| `SETSID`                | `147_i32` | session creation                        |
| `GETPGID`               | `151_i32` | process group query                     |
| `WAITID`                | `173_i32` | typed wait event                        |
| `SIGRETURN`             | `184_i32` | signal context restore                  |
| `GETRLIMIT`             | `194_i32` | resource-limit query                    |
| `SETRLIMIT`             | `195_i32` | resource-limit set                      |
| `LSEEK`                 | `199_i32` | descriptor seek                         |
| `SYSCTL`                | `202_i32` | Darwin release query                    |
| `POLL`                  | `230_i32` | descriptor polling                      |
| `POSIX_SPAWN`           | `244_i32` | restricted native spawn                 |
| `GETSID`                | `310_i32` | session query                           |
| `PROC_INFO`             | `336_i32` | process listing/info/usage/token signal |
| `GETDIRENTRIES64`       | `344_i32` | directory entries                       |
| `KQUEUE`                | `362_i32` | event queue creation                    |
| `KEVENT64`              | `369_i32` | event queue wait                        |
| `PROC_INFO_EXTENDED_ID` | `545_i32` | identity-checked process info           |

### A.2 Mach trap selectors

All constants are under `Native::Kernel::Darwin::Mach::Trap`.

| Constant            |  Selector |
| ------------------- | --------: |
| `VM_DEALLOCATE`     | `-12_i32` |
| `PORT_DEALLOCATE`   | `-18_i32` |
| `PORT_MOD_REFS`     | `-19_i32` |
| `REPLY_PORT`        | `-26_i32` |
| `TASK_SELF`         | `-28_i32` |
| `MESSAGE`           | `-31_i32` |
| `TASK_NAME_FOR_PID` | `-44_i32` |
| `MESSAGE2`          | `-47_i32` |

### A.3 `proc_info` operation numbers

All constants are under `Native::Kernel::Darwin::Process::Info::Call`.

| Constant             |    Value |
| -------------------- | -------: |
| `LIST_PIDS`          |  `1_u64` |
| `PID_INFO`           |  `2_u64` |
| `PID_USAGE`          |  `9_u64` |
| `SIGNAL_AUDIT_TOKEN` | `17_u64` |

The extended-ID syscall uses `PID_INFO` as its operation number.

### A.4 Process information constants

All constants remain under `Native::Kernel::Darwin::Process::Info`.

| Constant                 |      Value |
| ------------------------ | ---------: |
| `ALL_PIDS`               |    `1_u32` |
| `PGRP_ONLY`              |    `2_u32` |
| `PPID_ONLY`              |    `6_u32` |
| `PIDTASKALLINFO`         |    `2_i32` |
| `PIDTBSDINFO`            |    `3_i32` |
| `PIDTASKINFO`            |    `4_i32` |
| `PIDT_SHORTBSDINFO`      |   `13_i32` |
| `PIDUNIQIDENTIFIERINFO`  |   `17_i32` |
| `PIDT_BSDINFOWITHUNIQID` |   `18_i32` |
| `PIF_COMPARE_IDVERSION`  | `0x01_u32` |
| `PIF_COMPARE_UNIQUEID`   | `0x02_u32` |

### A.5 Mach ABI constants

Move these constants from `Darwin::ABI` to `Darwin::Mach::ABI` unchanged:

| Constant                  |    Value |
| ------------------------- | -------: |
| `TASK_AUDIT_TOKEN`        | `15_i32` |
| `MACH_PORT_RIGHT_SEND`    |  `0_u32` |
| `KERN_PROTECTION_FAILURE` |  `2_i32` |
| `KERN_NO_ACCESS`          |  `8_i32` |

## Appendix B: exact rename maps

### B.1 Type and namespace paths

Write these tab-separated rows byte-for-byte to `renames.tsv`. New namespaces,
method renames and constant renames are checked by the other gates.

```text
Native::Kernel::Linux::Number	Native::Kernel::Linux::Syscall::Number
Native::Kernel::Darwin::Resource::Time	Native::Kernel::Darwin::Resource::Timeval
Native::Kernel::Darwin::Mach::ExchangePhase	Native::Kernel::Darwin::Mach::Exchange::Phase
Native::Kernel::Darwin::Process::Info::Short	Native::Kernel::Darwin::Process::Info::BSD::Short
Native::Kernel::Darwin::Process::Info::Bsd	Native::Kernel::Darwin::Process::Info::BSD::Record
Native::Kernel::Darwin::Process::Info::Unique	Native::Kernel::Darwin::Process::Info::Identifier::Unique
Native::Kernel::Darwin::Process::Info::Record	Native::Kernel::Darwin::Process::Info::BSD::Identified
Native::Kernel::Darwin::Process::Info::Task	Native::Kernel::Darwin::Process::Info::Task::Record
Native::Kernel::Darwin::Process::Info::All	Native::Kernel::Darwin::Process::Info::Task::All
Native::Kernel::Darwin::ABI	Native::Kernel::Darwin::Mach::ABI
Native::Kernel::Source	Native::Kernel::Metadata::Source
Native::Kernel::Audit	Native::Kernel::Metadata::Assembly
LinuxKernel	Linux::ABI::Fixture::Kernel
LinuxAlignment	Linux::ABI::Fixture::Alignment
MontereySpawn	Spawn::Monterey
MontereyTaskToken	Task::Token::Monterey
ExecProof	Exec::Proof
LinuxRawProbe	Linux::Raw::Probe
LinuxRawProbe::Linux	Linux::Raw::Probe::Kernel
LinuxBehavior	Linux::Behavior
LinuxBehavior::Linux	Linux::Behavior::Kernel
```

### B.2 Method symbols

Write these tab-separated rows byte-for-byte to `method-renames.tsv`. The
comparator may normalize these owner/method symbols only; parameter types,
arity, result types and call topology remain exact.

```text
Native::Kernel::Darwin::Process.release	Native::Kernel::Darwin::Release.major
Native::Kernel::Darwin::Signal.kill	Native::Kernel::Darwin::Process.kill
Native::Kernel::Darwin::Process.signal	Native::Kernel::Darwin::Process.signal_with_audit_token
Native::Kernel::Darwin::Mach.task	Native::Kernel::Darwin::Mach.task_self
Native::Kernel::Darwin::Mach.open	Native::Kernel::Darwin::Mach.task_name_for_pid
Native::Kernel::Darwin::Mach.retain	Native::Kernel::Darwin::Mach.retain_send_right
Native::Kernel::Darwin::Mach.release	Native::Kernel::Darwin::Mach.release_send_right
Native::Kernel::Darwin::Mach.read	Native::Kernel::Darwin::Mach.read_audit_token
```

## Appendix C: known Process-Control consumers

Search the live tree in addition to this minimum inventory.

- Darwin release: `src/process-control/internal/darwin/context.cr`.
- PID kill observation: `src/process-control/internal/unix/observer.cr`.
- Mach methods: `src/process-control/internal/darwin/mach.cr` and
  `src/process-control/internal/darwin/native.cr`.
- Audit-token signal: `src/process-control/internal/darwin/native.cr` and the
  authority and driver specs.
- Mach ABI errors: `src/process-control/internal/darwin/authority.cr`.
- Process-info ABI: `src/process-control/internal/darwin/inspection.cr` and
  `spec/darwin_bootstrap_spec.cr`.
- Spawn profile: `src/process-control/internal/darwin/bootstrap.cr` and
  `spec/darwin_bootstrap_spec.cr`.
- Source metadata: `src/process-control/platform/unix/helper.cr`,
  `scripts/build-helper.cr`, `scripts/check-darwin.cr` and
  `spec/helper_dependency_spec.cr`.
- Assembly metadata: `src/process-control/platform/unix/helper.cr`,
  `scripts/helper/kernel.cr` and `spec/helper_dependency_spec.cr`.
