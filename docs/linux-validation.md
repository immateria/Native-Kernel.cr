# Linux validation — 2026-11-11 to 2026-11-12

The local attempt started from clean task branch
`arena/ee5586fa-native-kernel-cr` at
`9a11fc2e64c739000e9dc6aa4d33182ea700a7dd`. Only Native-Kernel was changed.
That environment could not produce native Crystal Linux evidence. The final
branch at `2ef0ade5bf4c145e9cdde5cea5a177af892f829f` subsequently passed all
four native hosted cells. The source is reviewable and its recorded mechanisms
passed, but broader qualification remains incomplete.

## Hosted native mechanisms — 2026-11-12

[GitHub Actions run 43162651064](https://github.com/immateria/Native-Kernel.cr/actions/runs/43162651064)
passed exact Crystal 1.10.0 and 1.22.2 on native `ubuntu-24.04` x86-64 and
`ubuntu-24.04-arm` AArch64. The ARM64 floor cell built Crystal 1.10.0 from the
pinned official source because that release has no official ARM64 binary. The
other cells used their reviewed native compiler installations. All four final
receipts report `mechanisms-passed`, with no failed stages or cases, and bind
the source, compiler, standard library, LLVM tools and generated artifacts.

Crystal 1.10.0's emitted LLVM was lowered with hash-recorded LLVM 15 `llc`,
matching the compiler's LLVM major. The runner rechecked the same audited IR
before and after lowering, required one function per executable section, linked
static no-import ELF executables and ran both development and release probes
natively. Crystal 1.22.2 retained the existing audited assembly path. These
results supersede the original host's download block for the four native
mechanisms cells; they do not rewrite or erase that historical local evidence.

Each receipt intentionally retains `qualification: incomplete`. Genuinely
delivered EINTR, foreign credentials and protected targets, PID reuse, raw
threads, cgroups and Process-Control lifecycle integration remain outside this
mechanisms run. A successful workflow is evidence for its recorded source,
artifacts and hosts, not a general Linux support claim.

## Original host and installation block

The available host is Debian GNU/Linux 12, kernel `6.1.158+`, x86-64 (sandbox/VM).
GCC is Debian `12.2.0-14+deb12u1`; binutils identity and the actual sandbox
seccomp/capability status are retained in receipts. Crystal and Clang were
initially absent. Exact official bundled Crystal **1.10.0** and **1.22.2**
release downloads were attempted outside the checkout. Both GitHub release URLs
redirect to `release-assets.githubusercontent.com`, which this sandbox's
outbound-host allowlist does not permit. Curl failed with exit 35
(`SSL_ERROR_SYSCALL`), and the public release-asset API also returns that blocked
redirect. No compiler installation or execution success is claimed.

Consequently these required cells were **blocked/unrun on that original host**:

| Compiler | x86-64 development/release | AArch64 development/release |
| --- | --- | --- |
| official 1.10.0 | specs, raw/typed Crystal codegen, reachable LLVM, link/import and runtime blocked | Crystal cross build/type-check and native run unrun |
| official 1.22.2 | specs, raw/typed Crystal codegen, reachable LLVM, link/import and runtime blocked | Crystal cross build/type-check and native run unrun |

At that point the new four-cell native Linux workflow had not been executed.
Its native ARM64 floor-source bootstrap was therefore locally unrun, not an
official 1.10.0 ARM64 binary download: that release has no such asset. The
later hosted result is recorded above. Darwin runtime regression execution was
unrun on this Linux host; the existing Darwin engines, APIs, exact audit keys
and workflows were preserved.

## Executed checks and receipt locations

All build products, checkouts, compilers and receipts are external under
`/home/user/nk-linux-work/`, not tracked repository artifacts.

* `evidence/linux-1.10.0-x86_64-final/export/receipt.json` and
  `evidence/linux-1.22.2-x86_64-final/export/receipt.json` bind final source hashes
  before/after, commands/exits, OS/tool identity, installed-header hashes,
  C oracle and startup hashes/import/link evidence, and the explicit missing
  Crystal artifact roster. Both return **1, blocked** for the absent compiler.
* Native C layout assertions and C-only capability diagnostics pass via
  `python3 scripts/ci/linux_runner.py --compiler PATH --expected-compiler VERSION
  --architecture x86_64 --output EXTERNAL_NEW_DIRECTORY` before its compiler
  gate. They use installed Debian UAPI, **not pinned v6.6 headers**. The C-only
  static ELF startup test uses the actual original `start-x86_64.S`, no default
  CRT, no interpreter/dynamic dependencies/imports, and passes entry/argc/argv/
  envp/stack checks. This establishes **startup-only C evidence**, not the
  Crystal unmanaged boundary.
* `evidence/linux-{1.10.0,1.22.2}-aarch64-cross-final/export/receipt.json`: the same driver with
  `--cross-target aarch64 --cc '.../zig cc -target aarch64-linux-gnu'` compiles
  installed Zig 0.13.0 UAPI assertions and the original ARM64 startup to AArch64
  ELF, links/inspects the C-only startup executable, then records the missing
  reviewed Crystal compiler. **Cross-only; never executed or counted native.**
* `python3 -m unittest discover -s tests -v` runs portable runner, metadata,
  ELF-rejection and manifest contracts, including existing macOS contracts.
  **108 tests: 106 passed, two existing setup-contract tests skipped** because
  this host lacks `pkg-config` (the tests require bash and pkg-config). Final
  bounded output, skip reasons and exits are in `evidence/final-checks.json`.
  Neither those skips nor portable success qualify native Linux execution.
* `make check CRYSTAL=...` is attempted for both exact unavailable installations;
  their failures are retained in `evidence/final-checks.json`. No zero-test or
  broad-skip result is substituted for compiler specs/native probes.

An auxiliary npm-packaged **patched Crystal 1.22.0 WASM** compiler was used only
for parser/format and type diagnostics outside the checkout. Target guards
were removed/selected in external in-memory copies to examine both entry
bodies without codegen; its LLVM lacks x86/AArch64 backends. That is **not an
unchanged-source Linux type-check, floor/current proof, assembly verification
or native execution**. Auxiliary commands/results are recorded separately in
`evidence/auxiliary-checks.json`. That receipt also binds the integrity-verified
npm tarball, local harness change and third-party license notices. A user-local
Zig installation supplies only native/cross C/assembly tools, not a Crystal
compiler or runtime dependency. The first C-only section-layout diagnostic
failed because Zig defaults to DWARF at O0. Adding `-g0` (matching the existing
Crystal `--no-debug` flag) made that diagnostic pass on native x86-64 and
cross-only AArch64. An attempted auxiliary macro-only x32 check failed on its
missing X86 backend, and is not counted as a refusal or native compiler test.
Reviewed-compiler negative audits/refusals remained unrun in this original
local evidence set; the later hosted cells exercised their required gates.

After continuation, the source patch was intact but the earlier local commit
object and external scratch directory were absent. The receipts named here
were regenerated against the restored source; the earlier two diagnostic
failures are retained as historical observations, not surviving raw logs or
qualification. A downloadable evidence archive includes the regenerated
receipts and the final commit patch, with generated files kept outside Git.

The C capability diagnostic observes successful self pidfd acquisition and
signal-zero delivery, EBADF for an invalid pidfd signal, ECHILD for pidfd-self
collection, ppoll with the 8-byte kernel mask, EINVAL for 128-byte masks,
getrusage and prlimit64 queries, pipe2, native EAGAIN on an empty nonblocking
pipe, and native ENOSYS on an unassigned number. These qualify only those C
calls in this caller/sandbox. Kernel version alone is not availability proof;
child pidfd signaling/readiness and every Crystal behavior case remained unrun
in this original local evidence set.

EINTR decoding is explicitly **synthetic**. A genuinely delivered native
interruption is unqualified; no handler/restorer installation was added to
manufacture it. Foreign credentials, PID reuse, consumer lifecycle, cgroups
and raw threads are likewise not qualified by these mechanisms tests. The
hosted `mechanisms-passed` receipts retain `qualification: incomplete` and
these limits; a zero mechanism-check exit is not an overall consumer/support
claim.

## Runnable native proof

On a supported native Linux host with a reviewed compiler:

```sh
CRYSTAL_CACHE_DIR=/external/cache-110 make check CRYSTAL=/tools/crystal-1.10.0/bin/crystal \
  RECEIPTS=/external/new-linux-110
CRYSTAL_CACHE_DIR=/external/cache-122 make native CRYSTAL=/tools/crystal-1.22.2/bin/crystal \
  RECEIPTS=/external/new-linux-122
```

The driver stops on a failed layer. Both raw optimization modes must pass before
building the typed worker. Every public primitive has a named positive case in
`ci/linux.json`; every body is reachable from the audited worker. Raw mmap uses
a fixture-owned file at **nonzero 64-KiB offset**, exercising real slots four
through six and releasing the mapping/fd. Original assembly startup bytes are
in the receipt. Both generated LLVM modes must reject runtime/allocator/
exception/mutable-global/external/indirect references and any nonselected exact
assembly. Four negative IR fixtures and opposite-architecture checks test the
auditor. Unsupported direct requires (also x32/ILP32) must fail for the intended
diagnostic; an empty refusal-only prelude isolates guards from missing target
stdlibs. Full and separately selected Linux specs must both execute; portable
examples cannot mask skipped Linux examples.

For ELF dead-section removal, the driver audits **unmodified** emitted LLVM,
then gives each complete compiler-emitted assembly function a separate section.
Only `.section` and `.p2align` directives are inserted; **no original line,
instruction, call, function or import is deleted or rewritten**. This is needed
because Crystal's O0 single-module ELF object otherwise shares `.text` with
unused runtime helpers. The driver retains the compiler object hash, both
assembly hashes/compressed texts, function map and reassembly command/object
hash. Unexpected function/section syntax fails closed. This layout-only build
step is not a reachable-IR filter or a runtime dependency. The original startup
is assembled separately without transformation. C/LLVM-assembly-only checks of
this build step are diagnostic, never Crystal qualification.

Linking uses `-nostdlib -static -no-pie`, explicit `_start`, dead-section removal
and no CRT. Both executables must have empty `nm -u`, no ELF interpreter or
dynamic segment/dependencies, no initialization arrays and no retained Crystal
initialization/runtime symbols. ELF machine and entry are independently checked.
The C oracle remains separate. Receipts retain exact commands/exits, compiler
and stdlib hashes, target triples, LLVM/object/executable hashes, compressed IR,
executables and bounded logs, including rejected IR/failure state.

Ten typed cases cover descriptors, actual close-on-exec re-exec, group/session
operations, pidfd observation/signaling/non-child refusal, raw ppoll mutation/
mask sizes, waitid no-event/WNOWAIT/fifth-slot accounting/collection, exit and
signal statuses, resource validity/failed acquisition and Linux copyout-after-
reaping. Sixteen repeated cycles check fd counts and absence of remaining
children. Only unmanaged workers clone; each confirmed target has one exclusive
collector and bounded failure cleanup. The managed driver uses subreaper
containment and reserved leader/group cleanup; adopted children make a case
fail, never pass. Captures and deadlines are bounded. These cases were
unexecuted only in the original local evidence set; the hosted run above
qualifies their recorded executions on its four native hosts.
