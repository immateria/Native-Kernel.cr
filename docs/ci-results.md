# Hosted CI evidence

Reviewed on 2026-11-12. A result applies to its recorded source and actual host;
it does not certify every release in an OS major. The profile inventory remains
separate from these executed observations.

## Mach send-timeout qualification on 2026-11-12

[Run 43371302629](https://github.com/immateria/Native-Kernel.cr/actions/runs/43371302629)
passed all eight native cells and four macOS-15-to-26 forward replays at commit
`3dfe07abe04ec0928313b50a7d4d87f6dde01b8c`. The run began on
2026-11-13 UTC, which was still 2026-11-12 in the reviewer's local time. The
existing GitHub-hosted workflow supplied the external 30-minute job ceiling,
20-minute qualification ceiling, log capture and ephemeral-runner teardown.
Every job returned normally with conclusion `success`; no deadline, forced
teardown, runner loss or incomplete receipt was recorded.

Both Crystal 1.10.0 and 1.22.2 passed on each native host:

| Architecture | Actual macOS / build | Darwin | Native cells |
| --- | --- | --- | --- |
| ARM64 | 15.8.2 / 24H232 | 24.6.0 | Both compilers passed |
| Intel x86-64 | 15.7.9 / 24G830 | 24.6.0 | Both compilers passed |
| ARM64 | 26.7.2 / 25G332 | 25.6.0 | Both compilers passed |
| Intel x86-64 | 26.6.1 / 25G76 | 25.6.0 | Both compilers passed |

No execution was translated. ARM64 hosts reported Apple M1 virtual hardware;
Intel hosts reported Core i7-8700B hardware. Each native cell passed 55 Crystal
examples and 176 Python contracts with one intentional Linux-only skip. The
ordered 13-case roster passed in both development and release modes, giving 26
exact outcomes per cell. The four forward jobs replayed the matching macOS 15
artifacts on macOS 26 without rebuilding and passed the same ordered 26
outcomes. Their receipts bind the exact successful origin receipt, compiler,
case order, source map, core manifest and six executable hashes.

The new `mach-send-timeout` case therefore completed 24 exact executions: two
optimization modes in eight native and four forward cells. Every saved stdout
is exactly `NK_OK mach-send-timeout\n`, with SHA-256
`c67a20608d07dcb4dc2ee0e0e8479fbc9dfc09ee2597a0323912e142e2cf40ae`;
every stderr is empty. The native cells also passed the reachable-LLVM audit
before execution. All 72 saved undefined-import outputs are empty. This is
source-bound hosted behavior evidence for the bounded simple-message fixture;
it does not qualify descriptor or out-of-line pseudo-receive restoration,
Darwin 21, or a public generic Mach messaging API.

The downloaded evidence has these identities:

| Class / profile / compiler | GitHub job | Receipt SHA-256 | Artifact ZIP SHA-256 |
| --- | ---: | --- | --- |
| Native macOS 15 ARM64 / 1.10.0 | `131707457258` | `bbf10bd9e49315a8896e9b004a36b8daae0d8c834c8723fce43d27a51c47e1ae` | `c3bfb60a9c5e1c696f732899052971dbd156c2f513131af8439687c0b549711a` |
| Native macOS 15 ARM64 / 1.22.2 | `131707457044` | `c3557b9f9958f2357689e6e40663816129adc65d4a6abf705b4e94aa769ba184` | `0646efafdcfff5333d23651087bb9cc1ef3fec117f97de4045a1df4f4d3c00aa` |
| Native macOS 15 x86-64 / 1.10.0 | `131707456619` | `f6e209ce7248743384d997acd99dfa444828f0448c202e690fba6ea21c7edfb9` | `4cd6c9c8f0079bc854d792c57939806af61e336771a459489f6ec7c5b537bb21` |
| Native macOS 15 x86-64 / 1.22.2 | `131707457029` | `3d7dd3f9b8aefd3c5d94e7a96f5804c6e54c3c91a9bda323c7bd3bb6610d7c0c` | `b5cb1be7308801a0edc9ed73d6043e30245257f4dd0a802301108c43b079d7f2` |
| Native macOS 26 ARM64 / 1.10.0 | `131707456962` | `855ff089f403fe16bac34367f495b108d36bdad756e2bd9c53cf09b6e3894811` | `d48fea7cf84a83a2669efda670845e64afa0cdd926190bd00e17042fd9f5c2c5` |
| Native macOS 26 ARM64 / 1.22.2 | `131707457019` | `284a368b5db5fac7f075e4986666aed153421a0e6e5a647a7c746b71e83324f8` | `a3b45b7183a59ee6588d08aaa656150e6d9b8a48fafbc1b6e4140a28d5829fba` |
| Native macOS 26 x86-64 / 1.10.0 | `131707456913` | `58c23d8dd222d6578d4188a0877e341a6bdc1cf117e8e8fe03225f5b88d489bf` | `7de493040571cfd3cdb41df8bf5292a50f65e297efce5297700110f36b7c8067` |
| Native macOS 26 x86-64 / 1.22.2 | `131707456968` | `52da15837a60e9670ade3e6194b81b70c665f9f31fe3598ea18dda009c80b305` | `6064278bb4e46194685f66cc112f1ce8bf56d2abc4b3ca5eda609a2dab7d9201` |
| Forward ARM64 / 1.10.0 | `131709747947` | `c9a8c27edb8faa2f8b7e7a8b15aa42ba33a6c072e3fe55590d6b41f08799476d` | `86d4b9c307221441799eb798c37b10a6e7c6b07967cfeb5bd9bbb09cff95ea03` |
| Forward ARM64 / 1.22.2 | `131709747988` | `34fa7007330b4f48a908d07ec767b3345816c69bef89d4b708f2f8b8d997111e` | `6423b552f578cf1897ed59a8e71e1b4211f5bf036a2f74f02d393c4a899223a4` |
| Forward x86-64 / 1.10.0 | `131709747966` | `dce3962216d2633a251ae29f1536a10141982ba620a53b88bbc35215969893e3` | `2bcfd5e07d47fbc916472a492ac8e5e4f54b15a369224bdfbf49f538074e6201` |
| Forward x86-64 / 1.22.2 | `131709747967` | `f42a7af344aa7d49b45a1fb95fa9070f02722d9de1cdb8a23e1a92a176baee53` | `49c5539372118b692afb9bee07279db0d7bca5f96ed0e1ab5d506c9643b826c8` |

The provider run record hashes to
`231673aded3f186f1bdc559902ffd66916d68da53ad5e1ea2975d747f0cc03db`;
the complete provider log archive hashes to
`62eadacbcae49f6842893dbecf6a49c50d7a534a7f84225bc0fc1bf750e1e869`.
Independent review matched all 1,688 declared bundle-file hashes, all 12 core
manifest hashes and all four forward-origin receipt bindings. The downloaded
artifacts were inspected but were not executed locally. The raw fixture has
not been run on the reviewer's long-lived Mac.

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
