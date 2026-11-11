# Fresh unmanaged worker; build with -Dwithout_main. All state is caller-owned.
require "../../src/native-kernel/darwin"
require "./behavior/common"
require "./behavior/descriptor"
require "./behavior/socket"
require "./behavior/process"
require "./behavior/spawn"
require "./behavior/signal"
require "./behavior/audit"
require "./behavior/event"

module Behavior
  def self.run(argc : Int32, argv : UInt8**) : Int32
    return 2 unless argc == 4
    name = argv[1]
    path = argv[2]
    target = argv[3]
    return 2 if name.null? || path.null? || target.null?
    result = if equal(name, "descriptor".to_unsafe)
               descriptor(path)
             elsif equal(name, "directory".to_unsafe)
               directory(path)
             elsif equal(name, "socket".to_unsafe)
               socket(path)
             elsif equal(name, "resource".to_unsafe)
               resource
             elsif equal(name, "session".to_unsafe)
               session
             elsif equal(name, "exec".to_unsafe)
               exec(target)
             elsif equal(name, "signal".to_unsafe)
               signal
             elsif equal(name, "audit".to_unsafe)
               audit
             elsif equal(name, "event".to_unsafe)
               event
             elsif equal(name, "process".to_unsafe)
               process(target)
             else
               return 3
             end
    result == 0 ? success(name) : result
  end
end

fun main(argc : Int32, argv : UInt8**) : Int32
  Native::Kernel::Darwin::Process.exit(Behavior.run(argc, argv))
end
