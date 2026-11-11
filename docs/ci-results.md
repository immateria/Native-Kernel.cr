# Hosted CI evidence

Reviewed on 2026-11-11. A result applies to its recorded source and actual host;
it does not certify every release in an OS major. The profile inventory remains
separate from these executed observations.

## First run

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

## Corrections for the next run

The verification step restores the selected OpenSSL search path after compiler
installation and persists it for qualification. Regression coverage models the
installer's OpenSSL 1.1 or 4 prepend and a fresh following workflow step.
The driver also records the actual compiler binary separately from its launcher,
with an explicit binary path required for otherwise unrecognized wrappers.

These changes concern CI setup and evidence. Production kernel sources and
Process-Control's private spawn ABI and release admission are unchanged.
The corrected run must supply its own passing receipts before its macOS 15
and forward cells can be recorded here as qualified.
