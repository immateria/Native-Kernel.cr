# Upstream notices for Darwin inventory data

Inventory date: 2026-11-12.

The Darwin catalogs derive names, numbers, declarations, paths, source lines
and hashes from the XNU files admitted by
[`darwin-xnu-source-manifest-xnu-12377.121.6.json`](darwin-xnu-source-manifest-xnu-12377.121.6.json).
The separate [APPLE_LICENSE](APPLE_LICENSE) is the verbatim Apple Public Source
License 2.0 distributed with that XNU revision. The additional notices below
are retained because admitted files carry them alongside Apple's notice.

This is a provenance record, not a legal conclusion. The exact admitted source
file remains authoritative for its file-level notices.

## Carnegie Mellon notice

The following notice is reproduced from admitted Mach sources including
`osfmk/mach/task.defs` and `osfmk/arm64/proc_reg.h`:

```text
Mach Operating System
Copyright (c) 1991,1990,1989 Carnegie Mellon University
All Rights Reserved.

Permission to use, copy, modify and distribute this software and its
documentation is hereby granted, provided that both the copyright
notice and this permission notice appear in all copies of the
software, derivative works or modified versions, and any portions
thereof, and that both notices appear in supporting documentation.

CARNEGIE MELLON ALLOWS FREE USE OF THIS SOFTWARE IN ITS "AS IS"
CONDITION.  CARNEGIE MELLON DISCLAIMS ANY LIABILITY OF ANY KIND FOR
ANY DAMAGES WHATSOEVER RESULTING FROM THE USE OF THIS SOFTWARE.

Carnegie Mellon requests users of this software to return to

 Software Distribution Coordinator  or  Software.Distribution@CS.CMU.EDU
 School of Computer Science
 Carnegie Mellon University
 Pittsburgh PA 15213-3890

any improvements or extensions that they make and grant Carnegie Mellon
the rights to redistribute these changes.
```

Twenty-six admitted files carry a Carnegie Mellon notice or reference:

```text
libsyscall/mach/servers/netname.defs
osfmk/arm64/proc_reg.h
osfmk/device/device.defs
osfmk/device/device_types.defs
osfmk/kern/syscall_sw.c
osfmk/mach/exc.defs
osfmk/mach/host_priv.defs
osfmk/mach/host_security.defs
osfmk/mach/mach_exc.defs
osfmk/mach/mach_host.defs
osfmk/mach/mach_port.defs
osfmk/mach/mach_types.defs
osfmk/mach/mach_vm.defs
osfmk/mach/notify.defs
osfmk/mach/processor.defs
osfmk/mach/processor_set.defs
osfmk/mach/prof.defs
osfmk/mach/std_types.defs
osfmk/mach/task.defs
osfmk/mach/thread_act.defs
osfmk/mach/upl.defs
osfmk/mach/vm32_map.defs
osfmk/mach/vm_map.defs
osfmk/mach_debug/mach_debug_types.defs
tests/excserver_backtrace.defs
tests/mach_exc.defs
```

`libsyscall/mach/servers/netname.defs` carries the older notice:

```text
Mach Operating System
Copyright (c) 1987 Carnegie-Mellon University
All rights reserved.  The CMU software License Agreement specifies
the terms and conditions for use and redistribution.
```

## OSF and Apple free-copyright markers

The exact XNU files retain literal source placeholders rather than expanded
notice text. This catalog preserves those marker identities without inventing
replacement terms:

- 10 admitted files carry `@OSF_FREE_COPYRIGHT@`;
- 26 admitted files carry `@OSF_COPYRIGHT@`; and
- `osfmk/i386/Diagnostics.c` and `osfmk/i386/Diagnostics.h` carry
  `@APPLE_FREE_COPYRIGHT@`.

## NeXT notice

`osfmk/i386/machdep_call.c` carries this notice:

```text
Copyright (c) 1992 NeXT Computer, Inc.

Machine dependent kernel calls.
```
