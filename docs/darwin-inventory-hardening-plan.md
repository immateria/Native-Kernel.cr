# Darwin inventory hardening plan

Plan date: 2026-11-12.

## Purpose

Use this plan to make the uncommitted Darwin syscall and named-operation
inventory exact-source, reproducible and ready for review. Execute the phases
in order. A phase is complete only when its exit checks pass.

This plan covers the catalog generator, its tests, generated data and
provenance documentation. It does not authorize new Native-Kernel runtime APIs,
commits or pushes.

## Execution contract

Before changing a file:

1. Read the workspace and shard `AGENTS.md` files, Native-Kernel `README.md`
   and `docs/support.md`.
2. Record the Native-Kernel branch, HEAD and full working-tree status.
3. Treat every pre-existing tracked or untracked change as user work. Do not
   overwrite a changed inventory file until its relationship to this plan is
   understood.
4. Verify the required inputs in [Inputs](#inputs). If an input is missing or
   has the wrong identity, follow [Blocked behavior](#blocked-behavior).

During execution:

- edit only Native-Kernel files named in [Owned outputs](#owned-outputs);
- use external scratch directories and external Crystal caches;
- inspect Process-Control read-only except when running its consumer checks;
- do not copy third-party implementation code into the repository;
- do not change a pinned count merely to make a test pass;
- do not treat source extraction, type checking or cross-compilation as native
  behavior qualification; and
- do not commit or push unless the user separately requests it.

When evidence conflicts, use this precedence:

1. official exact-tag source bytes admitted by the tracked source manifest;
2. independently reproduced source enumeration;
3. the history bundle and its normalized rows;
4. generated Native-Kernel outputs;
5. third-party bindings and compatibility projects.

If a higher-precedence source changes a count or conclusion, stop at that phase
and report the source-level reason. Do not preserve the old value by weakening
the parser or assertion.

## Inputs

Required history bundle:

- path:
  `/Users/immateria/Downloads/darwin-xnu-syscall-history-first-pass.zip`;
- SHA-256:
  `d6324bdc100c65f94396e2458b3f2dbe199d2fcc2e18d6c1cfd05f9fab94ee16`.

Historical latest-source input:

- path: `/Users/immateria/Downloads/xnu-main.zip`;
- SHA-256:
  `95fa2c70902b240521c2540858270708596208dbb5fc482519b32382b0ba26e2`;
- ZIP comment: `f6217f891ac0bb64f3d375211650a4c1ff8ca1ea`.

Required exact source profile:

- repository: `https://github.com/apple-oss-distributions/xnu`;
- tag: `xnu-12377.121.6`;
- commit: `ac9718fb1af618d5ce8678d0dc6e8a58f252216f`;
- input form: a Git checkout at that commit or an extracted tree with the same
  admitted bytes.

The current disposable checkout is:

`/tmp/native-kernel-github-reference.T4BcoZ/xnu-12377.121.6`

That path is audit convenience only. Do not write it into generated data,
scripts or permanent instructions. The generator continues to receive the
exact source through `--latest-xnu-root`.

Plan-time Native-Kernel baseline:

- commit: `5c1cbb335dfb7da941bc0ad3ed2f266543319d8d`;
- branch: `main`;
- inventory changes: uncommitted.

If HEAD has moved, inspect the intervening changes before continuing. A moved
HEAD is not itself a blocker. An overlapping unreviewed inventory change is.

## Evidence baseline

Independent source enumerations reproduced these values:

| Surface | Count |
| ------- | ----: |
| Active primary logical rows | 533 |
| Active family/number slots | 525 |
| Exact all-status rows | 845 |
| Typed primary entries | 44 |
| Primary gap rows | 489 |
| Selected `proc_info` rows | 94 |
| `PROC_INFO_CALL_*` rows | 20 |
| MIG subsystem source rows | 52 |
| Production MIG source rows | 49 |
| Test-only MIG source rows | 3 |
| MIG routine and simpleroutine declarations | 548 |
| MIG skip declarations | 122 |

These are review invariants, not desired outputs. Investigate any change before
updating a fixture, manifest or document.

## Confirmed defects

| ID | Defect | Required result |
| -- | ------ | --------------- |
| D1 | Only nine XNU files are authenticated; altered `.defs` inputs are accepted under the exact-tag label. | Authenticate the complete `.defs` roster and bytes before parsing. |
| D2 | Diagnostic rows retain the earlier `Diagnostics.c` hash. | Rebuild diagnostic provenance from the exact tag. |
| D3 | `dgGzallocTest` and `dgPermCheck` have `condition=1` instead of `DEVELOPMENT || DEBUG`. | Preserve exact implementation conditions. |
| D4 | Documentation says five reviewed files match; only three match. | Record the exact three-identical/six-different split. |
| D5 | `^\s*subsystem\b` records 49 of 52 MIG declaration lines one line early. | Match horizontal whitespace and validate every receipt. |
| D6 | Used `proc_info` flavors 13 and 18 are marked unreviewed. | Mark issued selectors implemented and bind each mark to a witness. |
| D7 | `--check` ignores stale generator-owned snapshot files. | Fail check mode on stale owned outputs without deleting them. |
| D8 | The script has no stated Python floor and lacks malformed-input regression coverage. | Declare Python 3.8 and add the specified parser/input tests. |

Flavor 17, `PROC_PIDUNIQIDENTIFIERINFO`, is declared but is not directly issued
as a flavor. Keep it unreviewed under the definition in Phase 4.

## Scope exclusions

Do not use this plan to:

- add or rename shipped Crystal APIs;
- build a per-routine MIG ABI catalog;
- enumerate dynamic sysctls, every ioctl, or provider-specific IOKit methods;
- change native support profiles;
- copy GPL implementation code;
- qualify entitlement, sandbox or protected-target behavior; or
- combine source, wrapper, compile and native coverage into one percentage.

Those remain separate projects or consumer-driven decisions.

## Owned outputs

Implementation may change only these Native-Kernel paths:

- `README.md`;
- `docs/darwin-catalog-sources.md`;
- `docs/darwin-inventory-hardening-plan.md`;
- `docs/darwin-syscall-landscape.md`;
- `docs/data/README.md`;
- `docs/data/UPSTREAM_NOTICES.md`;
- `docs/data/darwin-*.csv`;
- `docs/data/darwin-syscall-inventory.json`;
- `docs/data/darwin-xnu-source-manifest-xnu-12377.121.6.json`;
- `scripts/catalog/darwin_syscall_inventory.py`; and
- `tests/test_darwin_syscall_inventory.py` or a focused new test module under
  `tests/`.

Do not change `src/`, Crystal specs, native fixtures or CI merely to complete
this catalog plan. If a required fix genuinely needs one of those paths, stop
and request a scope decision.

## Phase 0: Reproduce the baseline

### Actions

1. Verify the two ZIP hashes and the historical ZIP comment.
2. Verify the exact Git tag and commit when network access is available.
3. Verify the supplied exact source root is readable.
4. Run the existing Python suite and generator check before edits.
5. Independently record the primary, `proc_info` and MIG counts without
   importing the generator's parser functions.

### Exit checks

- Required input identities match [Inputs](#inputs).
- Existing tests and `--check` reproduce their documented baseline.
- Independent counts match [Evidence baseline](#evidence-baseline), with the
  known defects D1 through D8 still present.

If a check disagrees, do not begin Phase 1. Report `Blocked` with the command,
observed result and affected claim.

## Phase 1: Admit every consumed XNU source

### Artifact

Create:

`docs/data/darwin-xnu-source-manifest-xnu-12377.121.6.json`

Use this schema:

```json
{
  "schema_version": 1,
  "snapshot_id": "xnu-12377.121.6",
  "source_repository": "https://github.com/apple-oss-distributions/xnu",
  "commit": "ac9718fb1af618d5ce8678d0dc6e8a58f252216f",
  "files": [
    {
      "path": "relative/source/path",
      "sha256": "64 lowercase hexadecimal characters",
      "role": "primary_table"
    }
  ]
}
```

Allowed `role` values:

- `primary_table`;
- `primary_implementation`;
- `selector_header`;
- `build_manifest`;
- `generation_script`;
- `project_manifest`;
- `mig_subsystem`;
- `mig_include`; and
- `test_source`.

### Actions

1. Include every non-`.defs` file directly consumed by the generator, including
   the kernel MIG build manifests and libsyscall generation inputs.
2. Include all 85 `.defs` files in the exact source tree, not only the 52 files
   that currently declare a subsystem.
3. Sort manifest entries by path and reject duplicate paths.
4. Load the tracked manifest before parsing any exact-source data.
5. Refuse a missing file, unexpected file, hash mismatch, invalid hash, wrong
   snapshot, wrong commit or unknown role.
6. Compare the complete source-root `.defs` roster with the manifest. Refuse
   both additions and removals.
7. When `.git` is present, require `HEAD` to match the manifest commit as an
   additional check. Do not serialize checkout-local state into generated
   output; extracted trees remain reproducible from admitted bytes alone.
8. Record the manifest SHA-256 in `darwin-syscall-inventory.json` and increment
   its schema version.

No output file may be written until admission succeeds.

### Required tests

Use scratch trees to prove refusal of:

- one altered admitted `.defs` file;
- one added `.defs` file;
- one removed `.defs` file;
- one missing directly consumed source;
- one duplicate manifest path; and
- one manifest with the wrong commit.

Also prove that an extracted exact tree without `.git` succeeds when every
manifest byte matches.

### Exit checks

- The manifest covers 99 consumed sources, including all 85 `.defs` files.
- Baseline generation succeeds.
- Every mutation case fails before output changes.
- A second independent script reproduces the manifest roster and hashes.

## Phase 2: Rebuild exact diagnostic rows

### Output schema

Add these output-only columns without making them required history-bundle input
columns:

- `implementation_source_path`;
- `implementation_source_line`; and
- `implementation_source_hash`.

Leave them blank for rows that do not have a separate implementation source.
Increment the generated-data schema version.

### Actions

1. Parse exact `osfmk/i386/Diagnostics.h` declarations.
2. Parse the exact dispatcher in `osfmk/i386/Diagnostics.c` with preprocessor
   conditions intact.
3. Join a declaration to its implementation case by selector identity.
4. Emit declaration path, line and hash through the existing source fields.
5. Emit implementation path, case line and hash through the new fields.
6. Preserve each enclosing implementation condition.
7. Derive active/inactive state from the source-union definition; do not call a
   debug-only row unconditional.
8. Replace retained history diagnostic rows with the exact rows.
9. Retain all 26 exact header declarations, including declared-only `dg64`.

Do not repair D2 by changing only the hash. That would leave D3 in place.

### Required tests

Cover:

- one unconditional case;
- `dgGzallocTest`;
- `dgPermCheck`;
- nested preprocessor conditions;
- a declared selector without an implementation case; and
- a duplicate implementation case.

### Exit checks

- All five active diagnostic rows match exact source independently.
- The corrected all-status inventory contains 845 rows: the exact Mach slot 63
  variant and exact declared-only `dg64` account for the two-row increase over
  the 843-row history export.
- `dgGzallocTest` and `dgPermCheck` retain `DEVELOPMENT || DEBUG`.
- No diagnostic row contains the historical implementation hash
  `68c4cab00fed224432e0e350e29fe4eeadf153c5e4af606ae160beffea6ea5af`.
- The exact implementation hash is
  `e5c7bcad6f97f72d36d0b72bf17c0a9850aa972c37f31daaffc12506864c68d1`.

## Phase 3: Repair MIG receipts and parser boundaries

### Actions

1. Replace `^\s*subsystem\b` with a pattern that permits horizontal whitespace
   only, such as `^[ \t]*subsystem\b`.
2. Scope ARM platform `case` parsing to the intended dispatcher body before
   collecting selectors.
3. Preserve uppercase and lowercase `Routine` and `SimpleRoutine` forms.
4. Keep conditional subsystem names as distinct candidates rather than choosing
   one preprocessor branch.
5. Regenerate the MIG source map from admitted source only.
6. Derive kernel build and libsyscall header-export roles from the admitted XNU
   build controls. Keep those roles separate from repository path scope.

### Required tests

Add fixtures for:

- blank lines before `subsystem`;
- a multiline conditional subsystem declaration;
- an unterminated subsystem declaration;
- uppercase `Routine` and `SimpleRoutine`;
- nested preprocessor branches;
- duplicate active primary keys;
- a multiline Mach trap declaration; and
- an unrelated ARM switch containing numeric `case` labels.

### Exit checks

For all 52 MIG rows, an independent validator confirms:

- `source_line` points to the line containing `subsystem`;
- `source_hash` matches the admitted manifest;
- `declaration` begins at the keyword and ends at its semicolon;
- the base and candidate names come from that declaration; and
- no parser warning is omitted.

The declaration counts remain source counts, not active routine or message-ID
counts.

## Phase 4: Bind `proc_info` implementation state

Use this exact definition:

> `implemented` means Native-Kernel issues this selector through a shipped
> typed mechanism and has a named positive source or spec witness for that
> selector.

It does not mean that every subordinate operation is implemented or that the
selector is natively qualified on every release.

### Actions

1. Add `PROC_PIDT_SHORTBSDINFO` (`13`) and
   `PROC_PIDT_BSDINFOWITHUNIQID` (`18`) to the implemented set.
2. Keep `PROC_PIDUNIQIDENTIFIERINFO` (`17`) unreviewed until it is directly
   issued as a flavor.
3. Create an explicit witness mapping from each implemented symbol to the
   Native-Kernel source or positive spec that issues it.
4. Validate witness paths and symbol/value agreement during tests.
5. Keep equal numeric values in separate selector domains.

### Exit checks

- Every implemented symbol has at least one valid witness.
- Every admitted selector issued by the current typed mechanisms is marked
  implemented.
- A declared record or constant without a direct issued selector is not marked
  implemented merely because its type exists.
- The generated catalog contains 14 implemented `proc_info` symbols unless an
  independently demonstrated source change explains another count.

## Phase 5: Harden input and output behavior

### Actions

1. Declare Python 3.8 as the catalog tooling floor.
2. Keep the script parseable with Python 3.8 syntax.
3. Add rejection tests for malformed CSV, unexpected snapshot IDs, invalid
   UTF-8, numeric aliases that cannot be resolved and malformed conditions.
4. Define these generator-owned output patterns:
   - `darwin-active-syscalls-xnu-*.csv`;
   - `darwin-syscall-gaps-xnu-*.csv`;
   - `darwin-secondary-catalog-candidates-xnu-*.csv`;
   - `darwin-proc-info-operations-xnu-*.csv`;
   - `darwin-mach-mig-subsystems-xnu-*.csv`; and
   - `darwin-syscall-inventory.json`.
5. In `--check` mode, fail when an owned snapshot file is present but is not in
   the expected output set.
6. In normal generation mode, report stale owned files but do not delete them.

Files outside those patterns, including licenses, READMEs and the source
manifest, are not stale generator output.

### Exit checks

- Python 3.8 syntax validation passes.
- Every malformed-input fixture fails with a bounded `CatalogError`.
- Check mode detects a scratch stale snapshot file.
- Normal generation does not delete the scratch stale file.

## Phase 6: Correct provenance and source guidance

### Actions

1. Update `docs/data/README.md` and `docs/darwin-syscall-landscape.md` to name
   exactly three identical and six differing reviewed files.
2. Remove every claim that predates the exact diagnostic regeneration.
3. Keep these states distinct in all prose:
   - source-catalogued;
   - raw-mechanically reachable;
   - typed wrapper present;
   - secondary selector implemented;
   - compile/type checked;
   - natively behavior-qualified; and
   - provider or release bounded.
4. State that the MIG artifact is a subsystem source map, not a per-routine ABI
   catalog.
5. State that debug-only diagnostic operations are not universally available.
6. Update `docs/darwin-catalog-sources.md` with:
   - Apple `bootstrap_cmds` MIG compiler and manual;
   - XNU `libsyscall/xcodescripts` and generated Mach interface configuration;
   - XNU `libsyscall/wrappers/libproc` as the primary `proc_info` wrapper
     semantics source;
   - XNU `bsd/sys/spawn_internal.h`;
   - relevant XNU workqueue, ulock, sysctl, fsctl, code-signing, coalition,
     memorystatus and process-policy headers;
   - IOKitUser transport and XNU DriverKit `.iig` interfaces;
   - libdispatch and dyld as consumer evidence; and
   - Rust, Go, Zig and Darling as bounded cross-checks only.
7. Correct any implication that the separate Libc repository owns XNU's
   in-tree libproc wrapper semantics.
8. Inspect file-level notices for derived material. Retain required Apple,
   Berkeley, NeXT, OSF or CMU notices that apply to repository content.

Do not make legal conclusions. If notice requirements remain uncertain, record
the exact files and missing determination as `Blocked`.

### Exit checks

- Documentation agrees with the generated receipt and exact source manifest.
- Every mutable GitHub fact is dated.
- Source authority is separate from popularity and third-party agreement.
- No prose describes source extraction as native qualification.

## Phase 7: Regenerate and validate

Run this phase only after Phases 1 through 6 pass their exit checks.

### Catalog checks

1. Run every Python test:

   ```sh
   PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
   ```

2. Check tracked regeneration using the verified exact source root:

   ```sh
   python3 scripts/catalog/darwin_syscall_inventory.py \
     --archive /Users/immateria/Downloads/darwin-xnu-syscall-history-first-pass.zip \
     --latest-xnu-root /absolute/path/to/xnu-12377.121.6 \
     --check
   ```

3. Run an independent validator that does not import the generator's parsing
   functions. It must check:
   - source-manifest roster and hashes;
   - all primary family counts and the gap complement;
   - all five diagnostic rows and conditions;
   - all 94 selected `proc_info` rows and implemented witnesses;
   - all 52 MIG rows and declaration lines; and
   - altered, added and removed `.defs` refusal.
4. Run `git diff --check`.
5. Inventory generator-owned outputs and prove that no stale snapshot remains.

### History-bundle consistency checks

Extract the bundle into a fresh external directory, then run its verifier and
16 tests. Record those results as internal consistency evidence only. They do
not prove the source labels.

### Repository regression checks

Use a new external `CRYSTAL_CACHE_DIR` for each command.

From Native-Kernel:

```sh
make check
```

From Process-Control, using the workspace's local Native-Kernel override:

```sh
make check
```

These are regression checks, not catalog-provenance evidence. Because the plan
does not authorize `src/`, native fixture or ABI changes, additional floor and
artifact matrices are required only if the actual implementation exceeds the
owned paths. If that happens, stop before running the expanded matrix and ask
for scope.

### Final invariants

Unless exact source evidence explains a change, require:

- 533 active primary rows;
- 845 exact all-status rows;
- 525 active family/number slots;
- 44 typed primary entries;
- 489 primary gaps;
- 94 selected `proc_info` rows;
- 20 outer `proc_info` calls;
- 14 implemented `proc_info` symbols;
- 52 MIG subsystem rows;
- 49 production and three test-only MIG rows;
- 548 routine/simpleroutine declarations; and
- 122 skips.

## Acceptance criteria

The inventory is ready for a commit decision only when:

- every phase exit check passes;
- every consumed exact-source byte is admitted by the tracked manifest;
- altered, added and removed `.defs` inputs fail before output writes;
- diagnostic provenance and conditions come from the exact tag;
- every MIG source line points to the keyword;
- implemented `proc_info` annotations have valid witnesses;
- stale owned outputs fail check mode;
- generated output reproduces byte for byte;
- independent enumeration agrees with the receipt;
- documentation matches the exact evidence and preserves coverage boundaries;
- applicable source notices are retained;
- Native-Kernel and Process-Control regression checks pass; and
- the final diff contains only intended owned outputs.

Passing these criteria does not authorize a commit or push.

## Blocked behavior

Stop the affected phase and return `Blocked` when:

- a required input is missing or has the wrong identity;
- the exact manifest cannot be reproduced from the official tag;
- a consumed source has ambiguous provenance;
- exact conditions cannot be represented without losing variants;
- independent enumeration disagrees with generated data;
- generated output labels unauthenticated bytes as exact;
- a required source notice cannot be resolved; or
- a required project or consumer check fails for a non-environmental reason.

The blocked report must contain:

1. the phase and exit check;
2. the exact command or source path;
3. expected and observed results;
4. work completed before the block;
5. files changed; and
6. the smallest user decision or external change needed to continue.

For an unavailable service, rate limit, missing compiler or other environmental
failure, record the check as `Unrun` or `Environment-blocked`. Do not convert it
into a pass. Continue only with phases whose evidence does not depend on that
check.

## Completion handoff

When every acceptance criterion passes, return exactly these sections:

### Outcome

State that the inventory is ready for a commit decision. Do not say it is
committed or published.

### Changed files

List every changed path and its purpose.

### Defects resolved

Map D1 through D8 to the implementation and regression test that closes each
one.

### Evidence

Provide a table with command, environment, result and evidence boundary.
Separate source checks, Python tests, independent validation, Native-Kernel
checks and Process-Control checks.

### Counts

Report the final primary, `proc_info` and MIG counts. Explain every departure
from [Evidence baseline](#evidence-baseline).

### Unrun and residual work

Name every unrun check and every deliberately deferred catalog. Write `None`
if there are none.

### Repository state

Report branch, HEAD, staged paths, unstaged paths and untracked paths. Confirm
that no commit or push occurred unless separately authorized.

## Deferred follow-up

Per-routine MIG extraction remains a separate project. It must use the admitted
MIG compiler semantics and build configuration to derive conditional message
IDs, request/reply layouts, implicit fields, port dispositions, descriptors,
ownership and cleanup. Raw declaration counts and `base + ordinal` are not
sufficient.
