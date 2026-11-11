# Hosted CI evidence

Reviewed on 2026-11-11. A result applies to its recorded source and actual host;
it does not certify every release in an OS major. The profile inventory remains
separate from these executed observations.

## Complete run on 2026-11-11

[Run 42979523044](https://github.com/immateria/Native-Kernel.cr/actions/runs/42979523044)
passed all eight native cells and four macOS-15-to-26 forward replays at commit
`0db4c8b7428b210c69edd465a75e44ccad26a9ea`, on `ci/macos-process-next`.
Both Crystal 1.10.0 and 1.22.2 passed on each native host below:

| Architecture | Actual macOS / build | Darwin | Native cells |
| --- | --- | --- | --- |
| ARM64 | 15.8.2 / 24H232 | 24.6.0 | Both compilers passed |
| Intel x86-64 | 15.7.9 / 24G830 | 24.6.0 | Both compilers passed |
| ARM64 | 26.7.2 / 25G332 | 25.6.0 | Both compilers passed |
| Intel x86-64 | 26.6.1 / 25G76 | 25.6.0 | Both compilers passed |

ARM64 hosts reported Apple M1 virtual hardware; Intel hosts reported
Core i7-8700B hardware. No execution was translated. Each native cell passed
19 Crystal specs, with zero failures, errors or pending examples, and 35 Python
contracts. All ten behavior cases passed in both development and release modes,
giving 20 exact outcomes per cell and positive coverage for 41 typed operations.
That mapping is regression coverage, not exhaustive syscall semantics.

The four forward cells executed the macOS 15 artifacts on the matching macOS 26
architecture, for each compiler version. Each passed the same 20 behavior
outcomes. Their receipts bind the exact successful origin receipt and all six
executable hashes. Forward jobs neither rebuilt artifacts nor reran managed
Crystal specs; their results are separate from native macOS 26 builds.

The independent review on 2026-11-11 checked all 12 receipts, their 50 declared
source/configuration hashes against the commit, workflow identity, artifact ZIP
digests, 1,544 declared bundle-file hashes and 1,404 saved log payloads. It checked
the exact forward origins and inspected all 72 executable references for empty
undefined-import tables. Retained LLVM hashes matched their proofs. Native
execution and LLVM approval are recorded hosted outcomes; the reviewer inspected
the downloaded artifacts without executing or rebuilding them locally.

The receipts identify the actual compiler binary separately from its launcher.
They do not content-address every stdlib, SDK or linker input; those inputs
remain trusted. The runtime evidence binds the shard revision to the actual
patched kernels, without claiming matching published XNU source for those
kernels. Later Darwin releases require separate qualification.

## Separate consumer qualification

Process-Control's [run 42980976671](https://github.com/immateria/Process-Control.cr/actions/runs/42980976671)
passed all eight native cells on the same host/compiler combinations at commit
`d4fcf3fb21d9f60838163e3049a061e8a3f1d386`, using Native-Kernel dependency
`0db4c8b7428b210c69edd465a75e44ccad26a9ea`. Each cell passed the complete
122-example Crystal suite with zero failures, errors or pending examples,
plus 11 Python contracts. Independent review verified the source and dependency
maps, helper fingerprints, both helper IR proofs and empty helper import tables.

That suite exercises authenticated startup, stdio, arguments, environment,
working directory, signals, abort, target collection and cleanup paths. It is
separate consumer evidence; Native-Kernel's primitive receipts alone do not
establish it. No consumer forward replay or repeat of the high-churn PID-reuse
and interruption qualifications is claimed. Protected targets, foreign
credentials, arbitrary raw-thread contexts, group containment and later Darwin
majors remain outside this qualification.

## First run (historical)

[Run 42967015096](https://github.com/immateria/Native-Kernel.cr/actions/runs/42967015096)
executed commit `13120074263955bcf435e593a2022a2ca6ebcb50`. The overall run
failed, with four passing native cells:

| Architecture | Crystal | Actual macOS / build | Darwin | Result |
| --- | --- | --- | --- | --- |
| ARM64 | 1.10.0 | 26.7.2 / 25G332 | 25.6.0 | Passed |
| ARM64 | 1.22.2 | 26.7.2 / 25G332 | 25.6.0 | Passed |
| Intel x86-64 | 1.10.0 | 26.6.1 / 25G76 | 25.6.0 | Passed |
| Intel x86-64 | 1.22.2 | 26.6.1 / 25G76 | 25.6.0 | Passed |

ARM64 ran on Apple M1 virtual hardware; Intel ran on Core i7-8700B hardware.
Neither execution was translated. Each cell passed 14 Crystal specs, 24 Python
tests and all ten native behavior cases in development and release modes. The
36 typed-operation mappings all have positive evidence in both modes.

Review matched all 12 original artifact ZIP digests and member bytes, bound the
46 selected source/configuration hashes to the published commit, repeated all
24 retained LLVM audits, and checked all 24 native executables' architectures
and empty undefined-import tables. The uploaded executables were inspected,
not run on the reviewer's different local OS.

All four macOS 15 cells stopped before qualification. Dependency setup selected
OpenSSL 3, then the pinned compiler installer prepended OpenSSL 1.1 to
`PKG_CONFIG_PATH`. That path outranks `PKG_CONFIG_LIBDIR`, so the existing
OpenSSL 3 assertion failed. The exported receipts are explicitly incomplete.
All four forward cells refused those origins before executing any fixture.
This run supplies no hosted macOS 15 or 15-to-26 replay result.

The first receipts' compiler hash identifies the official Bash launcher, shared
across the tested versions. Observed versions, compiled targets and native
execution are established; the underlying compiler binary was not hashed in
that run. Full toolchain attestation is not claimed.

## Corrections after the first run

Commit `f464208` restored the selected OpenSSL search path after compiler
installation and persisted it for qualification. Regression coverage models the
installer's OpenSSL 1.1 or 4 prepend and a fresh following workflow step.
The driver also began recording the actual compiler binary separately from its
launcher, with an explicit binary path required for otherwise unrecognized
wrappers.

Those corrections concerned CI setup and evidence. The later complete run
recorded above includes them and the process-group/session and spawn additions.
Its own passing receipts establish the macOS 15 and forward results; the first
run's incomplete receipts remain incomplete.
