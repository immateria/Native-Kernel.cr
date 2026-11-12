# Unmanaged -Dwithout_main fixture. Startup is the original start-*.S, not CRT.
require "../../../src/native-kernel/linux/raw"

module LinuxRawProbe
  alias Linux = Native::Kernel::Linux

  def self.equal(left : UInt8*, right : UInt8*) : Bool
    offset = 0
    while offset < 1024
      return false if left[offset] != right[offset]
      return true if left[offset] == 0
      offset &+= 1
    end
    false
  end

  def self.entry(argc : Int32, argv : UInt8**, stack : UInt64*, call_stack : UInt64) : Bool
    return false unless argc == 4 && stack.value == 4 && argv.address == stack.address &+ 8
    return false unless stack.address & 15 == 0 && call_stack & 15 == 0
    return false unless argv[argc].null? && equal(argv[1], "raw".to_unsafe) && equal(argv[2], "ELF-argument".to_unsafe)
    environment = argv + (argc &+ 1)
    count = 0
    while count < 256 && !environment[count].null?
      return true if equal(environment[count], "NK_ELF_PROOF=stack-arguments".to_unsafe)
      count &+= 1
    end
    false
  end

  def self.mapping(path : UInt8*) : Int32
    # Only this fixture needs openat/mmap/munmap. Offset 64 KiB works with all
    # supported native page sizes and gives slots four, five and six real values.
    opened = Linux::Raw.call(Linux::Number::OPENAT, -100_i64.to_u64!, path.address, 0x80000_u64, 0_u64)
    return 11 unless opened.error == 0 && opened.primary >= 0
    fd = opened.primary.to_i32!
    mapped = Linux::Raw.call(Linux::Number::MMAP, 0_u64, 4096_u64, 1_u64, 2_u64, fd.to_u64!, 65536_u64)
    result = 12
    if mapped.error == 0
      bytes = Pointer(UInt8).new(mapped.primary.to_u64!)
      result = equal(bytes, "sixth-slot-nonzero-offset".to_unsafe) ? 0 : 13
      unmapped = Linux::Raw.call(Linux::Number::MUNMAP, bytes.address, 4096_u64)
      result = 14 unless unmapped.error == 0
    end
    closed = Linux::Raw.call(Linux::Number::CLOSE, fd.to_u64!)
    closed.error == 0 ? result : 15
  end

  def self.run(argc : Int32, argv : UInt8**, stack : UInt64*, call_stack : UInt64) : Int32
    return 1 unless entry(argc, argv, stack, call_stack)
    return 2 unless Linux::Result.new(-4096_i64).error == 0 && Linux::Result.new(-4095_i64).error == 4095
    return 3 unless Linux::Result.new(-1_i64).error == 1 && Linux::Result.new(0_i64).error == 0
    return 4 unless Linux::Result.new(Int64::MIN).primary == Int64::MIN && Linux::Result.new(Int64::MIN).error == 0
    pid = Linux::Raw.call(Linux::Number::GETPID)
    return 5 unless pid.error == 0 && pid.primary > 0
    failed = Linux::Raw.call(Linux::Number::READ, UInt64::MAX, 0_u64, 1_u64)
    return 6 unless failed.primary == -9 && failed.error == 9
    missing = Linux::Raw.call(-1)
    return 7 unless missing.primary == -38 && missing.error == 38
    result = mapping(argv[3])
    return result unless result == 0
    written = Linux::Raw.call(Linux::Number::WRITE, 1_u64, "NK linux raw passed\n".to_unsafe.address, 20_u64)
    written.error == 0 && written.primary == 20 ? 0 : 16
  end
end

fun main(argc : Int32, argv : UInt8**, stack : UInt64*, call_stack : UInt64) : Int32
  code = LinuxRawProbe.run(argc, argv, stack, call_stack)
  loop do
    Native::Kernel::Linux::Raw.call(Native::Kernel::Linux::Number::EXIT_GROUP, code.to_u64!)
  end
end
