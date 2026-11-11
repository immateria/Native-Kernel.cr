# Audited successful execve/spawn target, with no managed runtime initialization.
require "../../src/native-kernel/darwin"

module ExecProof
  alias Darwin = Native::Kernel::Darwin

  def self.equal(left : UInt8*, right : UInt8*) : Bool
    offset = 0
    while offset < 64
      return false unless left[offset] == right[offset]
      return true if left[offset] == 0
      offset &+= 1
    end
    false
  end

  def self.environment_contains(environment : UInt8**, expected : UInt8*) : Bool
    return false if environment.null?
    offset = 0
    while offset < 256 && !environment[offset].null?
      return true if equal(environment[offset], expected)
      offset &+= 1
    end
    false
  end

  def self.decimal(value : UInt8*) : Int32
    number = 0_i32
    offset = 0
    while offset < 10
      byte = value[offset]
      return number if byte == 0
      return -1 unless byte >= 48 && byte <= 57 && number <= 100_000_000
      number = number &* 10 &+ byte &- 48
      offset &+= 1
    end
    -1
  end

  def self.exec_proof(argc : Int32, argv : UInt8**, environment : UInt8**) : Int32
    return 2 unless argc == 2 && !argv[1].null? && equal(argv[1], "nk-exec-proof".to_unsafe)
    return 3 unless environment_contains(environment, "NK_EXEC_PROOF=1".to_unsafe)
    written = Darwin::Descriptor.write(1, "NK_EXEC_OK\n".to_unsafe, 11_u64)
    written.error == 0 && written.primary == 11 ? 37 : 5
  end

  # Spawn fixture target: exact argv/environment, reset signal state/mask,
  # close-on-exec of the source pipe descriptor, and chdir('/') are all checked
  # before its one bounded stdout record and terminal status.
  def self.spawn_proof(argc : Int32, argv : UInt8**, environment : UInt8**) : Int32
    return 11 unless argc == 3 && !argv[1].null? && !argv[2].null? && equal(argv[1], "nk-spawn-proof".to_unsafe)
    return 12 unless environment_contains(environment, "NK_SPAWN_PROOF=1".to_unsafe)
    inherited_fd = decimal(argv[2])
    return 13 unless inherited_fd >= 3
    closed = Darwin::Descriptor.fcntl(inherited_fd, 1) # F_GETFD: CLOEXEC_DEFAULT closes the source fd.
    return 14 unless closed.primary == -1 && closed.error == 9

    # The spawn action changes the target to /. The runner's per-case directory
    # is otherwise empty and cannot satisfy this relative lookup.
    relative = Darwin::Descriptor.open("dev/null".to_unsafe, 0)
    return 15 unless relative.error == 0 && relative.primary >= 3
    return 16 unless Darwin::Descriptor.close(relative.primary.to_i32!).error == 0

    previous = uninitialized UInt8[32]
    queried = Darwin::Signal.action(30, Pointer(Darwin::Signal::Action).null, previous.to_unsafe.as(Void*))
    return 17 unless queried.error == 0 && previous.to_unsafe.as(UInt64*).value == 0_u64
    mask = 0_u32
    return 18 unless Darwin::Signal.mask(0, Pointer(UInt32).null, pointerof(mask)).error == 0 && (mask & 1_u32.unsafe_shl(29)) == 0_u32

    written = Darwin::Descriptor.write(1, "NK_SPAWN_OK\n".to_unsafe, 12_u64)
    written.error == 0 && written.primary == 12 ? 37 : 19
  end

  def self.run(argc : Int32, argv : UInt8**, environment : UInt8**) : Int32
    return 2 if argc < 2 || argv[1].null?
    if equal(argv[1], "nk-exec-proof".to_unsafe)
      exec_proof(argc, argv, environment)
    elsif equal(argv[1], "nk-spawn-proof".to_unsafe)
      spawn_proof(argc, argv, environment)
    else
      2
    end
  end
end

fun main(argc : Int32, argv : UInt8**) : Int32
  # Darwin lays envp immediately after argv[argc] and its null terminator.
  # Keep the two-argument main signature also declared by Crystal 1.10.
  environment = argv + (argc &+ 1)
  Native::Kernel::Darwin::Process.exit(ExecProof.run(argc, argv, environment))
end
