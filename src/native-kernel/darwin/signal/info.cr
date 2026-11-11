module Native::Kernel::Darwin::Signal
  CLD_EXITED    = 1
  CLD_KILLED    = 2
  CLD_DUMPED    = 3
  CLD_TRAPPED   = 4
  CLD_STOPPED   = 5
  CLD_CONTINUED = 6

  # Native64 siginfo_t. value preserves all eight bytes of the sigval union;
  # integer payloads occupy its low Int32, pointer payloads the entire word.
  struct Info
    property number : Int32 = 0
    property error : Int32 = 0
    property code : Int32 = 0
    property pid : Int32 = 0
    property uid : UInt32 = 0_u32
    property status : Int32 = 0
    property address : UInt64 = 0_u64
    property value : UInt64 = 0_u64
    property band : Int64 = 0_i64
    property reserved : StaticArray(UInt64, 7) = StaticArray(UInt64, 7).new(0_u64)
  end
end
