{% unless flag?(:linux) && !flag?(:android) && flag?(:bits64) && (flag?(:gnu) || flag?(:musl)) && flag?(:x86_64) %}
  {% raise "Linux x86-64 numbers require non-Android 64-bit Linux x86-64." %}
{% end %}

# Linux v6.6 arch/x86/entry/syscalls/syscall_64.tbl (not the x32 table).
module Native::Kernel::Linux::Number
  READ              =   0
  WRITE             =   1
  CLOSE             =   3
  MMAP              =   9
  MUNMAP            =  11
  GETPID            =  39
  CLONE             =  56
  EXECVE            =  59
  WAIT4             =  61
  KILL              =  62
  FCNTL             =  72
  GETRUSAGE         =  98
  SETPGID           = 109
  GETPPID           = 110
  SETSID            = 112
  GETPGID           = 121
  GETSID            = 124
  EXIT_GROUP        = 231
  WAITID            = 247
  OPENAT            = 257
  PPOLL             = 271
  DUP3              = 292
  PIPE2             = 293
  PRLIMIT64         = 302
  PIDFD_SEND_SIGNAL = 424
  PIDFD_OPEN        = 434
end
