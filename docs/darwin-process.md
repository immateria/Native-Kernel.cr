# Darwin process primitives

Source audit: 2026-11-11. Runtime qualification belongs to the exact host,
compiler and artifact named in each receipt.

`Process.setpgid(pid, group)`, `getpgid(pid = 0)` and `getsid(pid = 0)` expose
Darwin's numeric process-group and session operations. Zero selects the calling
process where the native operation permits it. These calls return `Result` and
retain native errno. They do not retain a process identity or establish group
ownership, membership stability or descendant containment.

The unmanaged session fixture changes only owned children. It checks group
creation and joining, zero-argument substitution, inherited sessions, session
creation and leader restrictions, then collects each child through its sole
collector. Error precedence depends on the caller's state: a session leader can
receive `EPERM` before a negative group argument would otherwise yield `EINVAL`.
The managed specs never change the test runner's group or session.

## Private spawn ABI

`Spawn.profile(major)` returns separately audited native64 layout data for
Darwin 21, 24 and 25; other values return nil. Darwin majors are kernel
versions: macOS 12 uses Darwin 21, macOS 15 uses Darwin 24, and macOS 26 uses
Darwin 25. Darwin 21 is not an alias for the later profile. Profile selection
describes source-audited layout only; the consumer still owns release admission
and runtime checks. The dated [Monterey foundations audit](darwin-monterey-foundations.md)
records immutable source bytes, static-layout gate, fixture topology and native
build/runtime gates.

`Spawn.create(child, path, descriptor, arguments, environment)` invokes BSD
syscall 244. The caller owns every buffer, descriptor, returned child and later
collection. The entry neither initializes buffers nor retries creation. A
native failure does not supply a general rollback guarantee.

The Darwin 24/25 profile describes a 192-byte copied attribute prefix and a
144-byte descriptor. Darwin 21 instead describes a 152-byte copied prefix and
128-byte descriptor. Each kernel copies its whole native64 descriptor; any
nonzero declared attribute size selects that profile's fixed prefix, rather than
negotiating a shorter copy. The shared restricted action layout is an 8-byte
header plus 1040-byte action records. Fields after the copied prefix are outside
these restricted profiles.

File-action payloads overlap. Open flags start at byte 8, the UInt16 open mode
at byte 12, and its path at byte 14. A chdir path instead starts at byte 8. Both
paths have a 1024-byte capacity including the terminator. Use the profile's
offsets rather than treating these as independent fields.

Process-Control uses a zero-filled restricted attribute prefix with signal
default/reset and close-on-exec flags `0x400c`. That subset leaves Darwin 25's
additional fields unrequested. It is not a claim that arbitrary zero-filled
bytes reproduce every default installed by the platform's spawn library.

## Source and runtime evidence

The layout and copy paths were checked against these Apple XNU revisions:

- Darwin 21 nearby published source: [xnu-8020.140.41](https://github.com/apple-oss-distributions/xnu/tree/27b03b360a988dfd3dfdf34262bb0042026747cc). It is not asserted to be the shipping `xnu-8020.240.18.709.2` source; see the Monterey foundations audit for byte hashes and remaining gate.
- Darwin 24: [xnu-11417.101.15](https://github.com/apple-oss-distributions/xnu/tree/e3723e1f17661b24996789d8afc084c0c3303b26).
- Initial Darwin 25: [xnu-12377.1.9](https://github.com/apple-oss-distributions/xnu/tree/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea).
- Published Darwin 25 update: [xnu-12377.121.6](https://github.com/apple-oss-distributions/xnu/tree/ac9718fb1af618d5ce8678d0dc6e8a58f252216f).

The audit read `bsd/sys/spawn_internal.h`, `bsd/kern/kern_exec.c` and the
associated action and syscall definitions. The group/session entries are
syscalls 82, 151 and 310. The action stride and payload offsets agree across
these revisions, but Darwin 21 has its separately encoded 152-byte prefix and
128-byte descriptor. Darwin 25 adds fields inside bytes that this consumer
keeps zero; the complete structures should not be treated as interchangeable.

The exact XNU `.161.*` source used by the current macOS 26 runners was not
published at audit time. Runtime receipts identify those kernels separately;
passing them does not establish a matching-source audit. Likewise, a passing
Native-Kernel spawn fixture does not qualify Process-Control's authenticated
startup protocol, target collection or rollback. Its full consumer suite is a
separate gate.
