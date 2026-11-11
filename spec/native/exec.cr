# Audited successful execve target, with no managed runtime initialization.
require "../../src/native-kernel/darwin"

module ExecProof
  def self.equal(left : UInt8*, right : UInt8*) : Bool
    offset = 0
    while offset < 64
      return false unless left[offset] == right[offset]
      return true if left[offset] == 0
      offset &+= 1
    end
    false
  end

  def self.run(argc : Int32, argv : UInt8**, environment : UInt8**) : Int32
    return 2 unless argc == 2 && !argv[1].null? && equal(argv[1], "nk-exec-proof".to_unsafe)
    return 3 if environment.null?
    found = false
    offset = 0
    while offset < 256 && !environment[offset].null?
      found = true if equal(environment[offset], "NK_EXEC_PROOF=1".to_unsafe)
      offset &+= 1
    end
    return 4 unless found && offset < 256
    written = Native::Kernel::Darwin::Descriptor.write(1, "NK_EXEC_OK\n".to_unsafe, 11_u64)
    written.error == 0 && written.primary == 11 ? 37 : 5
  end
end

fun main(argc : Int32, argv : UInt8**) : Int32
  # Darwin lays envp immediately after argv[argc] and its null terminator.
  # Keep the two-argument main signature also declared by Crystal 1.10.
  environment = argv + (argc &+ 1)
  Native::Kernel::Darwin::Process.exit(ExecProof.run(argc, argv, environment))
end
