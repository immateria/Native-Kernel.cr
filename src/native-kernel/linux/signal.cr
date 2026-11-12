require "./raw"

module Native::Kernel::Linux::Signal
  KILL =  9
  TERM = 15
  CHLD = 17
  CONT = 18
  STOP = 19

  CLD_EXITED    = 1
  CLD_KILLED    = 2
  CLD_DUMPED    = 3
  CLD_STOPPED   = 5
  CLD_CONTINUED = 6

  SET_BYTES = 8_u64

  # Kernel sigset_t: 64 signal bits, NOT libc's 128-byte sigset_t. Bit n-1
  # represents signal n. No signal-handler or restorer installation is supplied.
  struct Set
    property bits : UInt64

    def initialize(@bits = 0_u64)
    end
  end

  # Full 128-byte, 8-aligned native siginfo storage with a SIGCHLD view only.
  # Other union variants are intentionally opaque. Raw waitid writes number,
  # error, code, pid, uid and status, NOT the tail (including si_utime/stime).
  struct Info
    property number : Int32 = 0
    property error : Int32 = 0
    property code : Int32 = 0
    @reserved0 : Int32 = 0
    property pid : Int32 = 0
    property uid : UInt32 = 0_u32
    property status : Int32 = 0
    @reserved1 : Int32 = 0
    @tail : StaticArray(UInt64, 12) = StaticArray(UInt64, 12).new(0_u64)
  end
end
