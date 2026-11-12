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

/* Freestanding C ABI byte-fill used by LLVM's target lowering. */
.section .text.memset,"ax",%progbits
.p2align 2
.global memset
.type memset,%function
memset:
    mov x3, x0                     /* return the original destination */
    uxtb w1, w1
    cbz x2, .Lmemset_done
.Lmemset_loop:
    strb w1, [x0], #1
    subs x2, x2, #1
    b.ne .Lmemset_loop
.Lmemset_done:
    mov x0, x3
    ret
.size memset, .-memset
.section .note.GNU-stack,"",%progbits
