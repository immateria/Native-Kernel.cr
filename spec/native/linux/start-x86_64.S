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
.section .note.GNU-stack,"",@progbits
