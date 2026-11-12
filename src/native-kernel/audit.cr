module Native::Kernel::Audit
  ASSEMBLY = [
    "\0~{memory}",
    "mov x16, $3\\0Asvc #0x80\\0Acset $2, cs\0={x0},={x1},=r,r,{x0},{x1},{x2},{x3},{x4},{x5},{x6},{x7},~{x16},~{memory},~{cc}",
    "subq $$160, %rsp\\0Amovq $10, 8(%rsp)\\0Amovq $11, 16(%rsp)\\0Asyscall\\0Asetc ${2:b}\\0Aaddq $$160, %rsp\0={rax},={rdx},=r,{rax},{rdi},{rsi},{rdx},{r10},{r8},{r9},r,r,~{rcx},~{r11},~{memory},~{flags}",
  ] of String
end

# Deliberately separate from ASSEMBLY: the Darwin keys above are unchanged.
# Select exactly one Linux architecture; never union these with Darwin admission.
module Native::Kernel::Audit
  LINUX_X86_64_ASSEMBLY = [
    "\0~{memory}",
    "syscall\0={rax},{rax},{rdi},{rsi},{rdx},{r10},{r8},{r9},~{rcx},~{r11},~{memory},~{flags}",
  ] of String

  LINUX_AARCH64_ASSEMBLY = [
    "\0~{memory}",
    "svc #0\0={x0},{x8},{x0},{x1},{x2},{x3},{x4},{x5},~{memory},~{cc}",
  ] of String
end
