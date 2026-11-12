/* Original MIT fixture. Linux ELF entry, not a C main renamed as an entry. */
.section .text._start,"ax",@progbits
.global _start
.type _start,@function
_start:
    xor %ebp, %ebp
    mov %rsp, %rdx                 /* unmodified kernel initial stack */
    test $15, %rsp
    jnz .Lbad
    mov (%rsp), %rdi               /* argc */
    lea 8(%rsp), %rsi              /* argv (followed by NULL, envp, auxv) */
    and $-16, %rsp
    mov %rsp, %rcx                 /* stack immediately before CALL */
    call main                     /* SysV callee entry has rsp % 16 == 8 */
    mov %eax, %edi
    mov $231, %eax                 /* exit_group, even if main returns */
    syscall
.Lbad:
    mov $125, %edi
    mov $231, %eax
    syscall
    ud2
.size _start, .-_start

/* Freestanding C ABI byte-fill used by LLVM's target lowering. */
.section .text.memset,"ax",@progbits
.p2align 4
.global memset
.type memset,@function
memset:
    mov %rdi, %rax                 /* return the original destination */
    test %rdx, %rdx
    jz .Lmemset_done
.Lmemset_loop:
    movb %sil, (%rdi)
    inc %rdi
    dec %rdx
    jnz .Lmemset_loop
.Lmemset_done:
    ret
.size memset, .-memset
.section .note.GNU-stack,"",@progbits
