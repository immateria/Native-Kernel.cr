/* Original MIT fixture. Linux ELF entry; no CRT or Crystal initialization. */
.section .text._start,"ax",%progbits
.global _start
.type _start,%function
_start:
    mov x29, xzr
    mov x30, xzr
    mov x2, sp                     /* unmodified kernel initial stack */
    tst x2, #15
    b.ne .Lbad
    ldr x0, [sp]                   /* argc */
    add x1, sp, #8                 /* argv */
    mov x3, sp                     /* AAPCS64 stack at the call is aligned */
    bl main
    mov x8, #94                    /* exit_group, even if main returns */
    svc #0
.Lbad:
    mov x0, #125
    mov x8, #94
    svc #0
    brk #0
.size _start, .-_start
.section .note.GNU-stack,"",%progbits
