# Native-Kernel

Native-Kernel supplies direct Darwin BSD syscall and Mach trap entry for Crystal
1.10.0 and later on ARM64 and x86-64. It has no runtime shard dependencies.
The assembly engines were extracted from Process-Control commit `85b0103` on
2026-11-10. The assembly text, register constraints and clobbers are unchanged.

```crystal
require "native-kernel/darwin/raw"

result = Native::Kernel::Darwin::Raw.call(20) # getpid
# result.primary : Int64, result.secondary : Int64, result.error : Int32
```

`Raw.call` takes a signed Int32 trap number and up to eight UInt64 arguments.
Nonnegative numbers select BSD syscalls. Negative numbers select Mach traps.
A BSD error sets primary to -1 and preserves positive errno in error. Mach
native return codes remain in primary with error zero. Both native result
registers are retained. Raw fork returns the kernel's child discriminator in
secondary; `Darwin::Process.fork` additionally returns primary zero in the child.

```crystal
require "native-kernel/darwin"

alias Kernel = Native::Kernel::Darwin
result = Kernel::Descriptor.pipe
# On success primary is the read fd and secondary is the write fd.
# The caller owns both descriptors and must close each.
```

The typed entry supplies `Descriptor`, `Process`, `Spawn`, `Resource`, `Signal`,
`Event` and `Mach` primitives, plus native ABI records. BSD wrappers return `Result`;
`Process.signal` returns errno, and Mach wrappers return native Mach codes.
These are direct mechanisms with caller-owned buffers and resources. The shard
does not manage process identity, context ownership, signal policy, child status,
retry policy, credentials or supported-release admission.

`Mach.task` returns a caller-owned task-self send reference. Pass that explicit
name to `Mach.open`, `retain`, `release` and `read`; there is no cached task or
process context. `read` requests TASK_AUDIT_TOKEN and returns eight UInt32 words,
a returned count and a Mach/MIG status. Each read creates and releases a dedicated
reply receive right before returning. The caller owns target send references and
must release them independently. A failed cleanup result requires caller policy.
See [the supported profiles](docs/support.md) before using kernel interfaces.

The [Darwin process notes](docs/darwin-process.md) cover numeric group/session
operations and the restricted private spawn layout for Darwin 24 and 25.

The raw and typed entries need no managed runtime initialization, allocation,
exceptions or external function calls. They can be used in an unmanaged custom
entry built with `-Dwithout_main`; the artifact probe demonstrates that boundary.
Ordinary managed Crystal programs retain their own runtime dependencies.

Build metadata has separate, portable require entries:

```crystal
require "native-kernel/source"
require "native-kernel/audit"
```

`Native::Kernel::Source::FILES` maps every shipped `src/` Crystal path to its
actual source bytes, including metadata files and both architecture engines.
`Source.root` gives the repository root. `Audit::ASSEMBLY` contains the exact LLVM
assembly-text/NUL/constraint keys, including the memory barrier. Consumers can
bind helper fingerprints and reachable-IR audits to those inputs. Metadata never
enters the raw or typed require graph.

Run `make check`; on Darwin this also verifies and runs unmanaged development
and release artifacts with no undefined imports. `make native` runs that artifact
check alone; `RECEIPTS=/external/new-directory` retains its source/IR/executable
hash manifest. Use an external `CRYSTAL_CACHE_DIR`. No build output enters this
repository. See [AGENTS.md](AGENTS.md) for maintenance requirements.

The [macOS runner suite](ci/README.md) passed all eight native compiler/host cells
and four macOS-15-to-26 artifact replays at source `0db4c8b` on 2026-11-11.
The [dated CI results](docs/ci-results.md) identify the exact hosts, compilers,
reviewed evidence and limits, plus Process-Control's separate consumer run.
Qualification applies to those source/artifact and host combinations. The
workflow runs only in public repositories on standard runners, with three-day
artifact retention. Consumer lifecycle and release admission need their own
qualification.
