{% unless flag?(:linux) && !flag?(:android) && flag?(:bits64) && (flag?(:gnu) || flag?(:musl)) && flag?(:aarch64) %}
  {% raise "Linux AArch64 numbers require non-Android 64-bit Linux AArch64." %}
{% end %}

# Linux v6.6 asm-generic/unistd.h as selected by arm64's UAPI unistd.h.
module Native::Kernel::Linux::Number
  DUP3              =  24
  FCNTL             =  25
  OPENAT            =  56
  CLOSE             =  57
  PIPE2             =  59
  READ              =  63
  WRITE             =  64
  PPOLL             =  73
  EXIT_GROUP        =  94
  WAITID            =  95
  KILL              = 129
  SETPGID           = 154
  GETPGID           = 155
  GETSID            = 156
  SETSID            = 157
  GETRUSAGE         = 165
  GETPID            = 172
  GETPPID           = 173
  MUNMAP            = 215
  CLONE             = 220
  EXECVE            = 221
  MMAP              = 222
  WAIT4             = 260
  PRLIMIT64         = 261
  PIDFD_SEND_SIGNAL = 424
  PIDFD_OPEN        = 434
end
