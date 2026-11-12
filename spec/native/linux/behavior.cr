# Unmanaged -Dwithout_main worker, reached only from the original ELF startup.
require "../../../src/native-kernel/linux"
require "./behavior/common"
require "./behavior/descriptor"
require "./behavior/process"
require "./behavior/pidfd"
require "./behavior/collection"
require "./behavior/resource"

module LinuxBehavior
  def self.run(argc : Int32, argv : UInt8**, stack : UInt64*, call_stack : UInt64) : Int32
    return 118 unless entry(argc, argv, stack, call_stack)
    name = argv[1]
    code = if equal(name, "descriptor".to_unsafe)
             descriptor
           elsif equal(name, "exec".to_unsafe)
             exec(argv, argv + (argc &+ 1))
           elsif equal(name, "exec-check".to_unsafe)
             exec_check
           elsif equal(name, "process".to_unsafe)
             process
           elsif equal(name, "pidfd".to_unsafe)
             pidfd
           elsif equal(name, "poll".to_unsafe)
             poll
           elsif equal(name, "collection".to_unsafe)
             collection
           elsif equal(name, "signal-status".to_unsafe)
             signal_status
           elsif equal(name, "copyout".to_unsafe)
             copyout
           elsif equal(name, "resource".to_unsafe)
             resource
           elsif equal(name, "leaks".to_unsafe)
             leaks
           else
             119
           end
    return code unless code == 0
    success(equal(name, "exec-check".to_unsafe) ? "exec".to_unsafe : name)
  end
end

fun main(argc : Int32, argv : UInt8**, stack : UInt64*, call_stack : UInt64) : Int32
  LinuxBehavior.terminate(LinuxBehavior.run(argc, argv, stack, call_stack))
end
