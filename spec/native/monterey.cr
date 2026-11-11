# Selected BSD-only compatibility probes. The runner owns host admission and
# labels newer-host/Rosetta execution as preflight evidence only.
require "../../src/native-kernel/darwin"
require "./behavior/common"
require "./behavior/descriptor"
require "./behavior/process"
require "./behavior/collection"
require "./behavior/inspection"
require "./behavior/signal"
require "./behavior/event"

module Monterey
  alias Darwin = Native::Kernel::Darwin

  def self.collection : Int32
    # Darwin 21 does not share the later INT_MIN wait4 validation path. Keep
    # that version-specific assertion out of this compatibility experiment.
    usage = Darwin::Resource::Usage.new
    result = Darwin::Resource.getrusage(Darwin::Resource::RUSAGE_SELF, pointerof(usage))
    return 128 unless result.error == 0 && result.primary == 0 && Behavior.usage_valid(usage)
    result = Darwin::Resource.getrusage(Darwin::Resource::RUSAGE_CHILDREN, pointerof(usage))
    return 129 unless result.error == 0 && result.primary == 0 && Behavior.usage_valid(usage)
    usage.max_rss = -777_i64
    invalid = Darwin::Resource.getrusage(1, pointerof(usage))
    return 130 unless invalid.primary == -1 && invalid.error == 22 && usage.max_rss == -777
    info = Darwin::Signal::Info.new
    info.pid = -777
    invalid = Darwin::Process.waitid(Behavior::Wait::P_ALL, 0_u32, pointerof(info), 0x40000000)
    return 132 unless invalid.primary == -1 && invalid.error == 22 && info.pid == -777
    result = Behavior.collection_child(false)
    return result unless result == 0
    result = Behavior.collection_child(true)
    return result unless result == 0
    result = Behavior.collection_waitid
    return result unless result == 0
    result = Darwin::Resource.getrusage(Darwin::Resource::RUSAGE_CHILDREN, pointerof(usage))
    result.error == 0 && Behavior.usage_valid(usage) && usage.max_rss > 0 ? 0 : 133
  end

  def self.run(argc : Int32, argv : UInt8**) : Int32
    return 2 unless argc == 4
    name, path, target = argv[1], argv[2], argv[3]
    return 2 if name.null? || path.null? || target.null?
    result = if Behavior.equal(name, "descriptor".to_unsafe)
               Behavior.descriptor(path)
             elsif Behavior.equal(name, "resource".to_unsafe)
               Behavior.resource
             elsif Behavior.equal(name, "session".to_unsafe)
               Behavior.session
             elsif Behavior.equal(name, "exec".to_unsafe)
               Behavior.exec(target)
             elsif Behavior.equal(name, "signal".to_unsafe)
               Behavior.signal
             elsif Behavior.equal(name, "event".to_unsafe)
               Behavior.event
             elsif Behavior.equal(name, "collection".to_unsafe)
               collection
             elsif Behavior.equal(name, "inspection".to_unsafe)
               Behavior.inspection
             else
               return 3
             end
    result == 0 ? Behavior.success(name) : result
  end
end

fun main(argc : Int32, argv : UInt8**) : Int32
  Native::Kernel::Darwin::Process.exit(Monterey.run(argc, argv))
end
