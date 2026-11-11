module Behavior
  alias Wait = Darwin::Process::Wait

  def self.usage_valid(usage : Darwin::Resource::Usage) : Bool
    usage.user.seconds >= 0 && usage.system.seconds >= 0 &&
      usage.user.microseconds >= 0 && usage.user.microseconds < 1_000_000 &&
      usage.system.microseconds >= 0 && usage.system.microseconds < 1_000_000 && usage.max_rss >= 0
  end

  # Every poll clears pid: Darwin's no-event waitid does not clear the record.
  def self.observe(pid : Int32, options : Int32, info : Darwin::Signal::Info*) : Bool
    attempt = 0
    while attempt < 2000
      info.value.pid = 0
      result = Darwin::Process.waitid(Wait::P_PID, pid.to_u32!, info, options | Wait::WNOHANG | Wait::WNOWAIT)
      return true if result.error == 0 && info.value.pid != 0
      return false unless result.error == 0 || result.error == 4
      Darwin::Event.sleep(1000_u32)
      attempt &+= 1
    end
    false
  end

  def self.collection_exit(pid : Int32, writer : Int32) : Int32
    usage = Darwin::Resource::Usage.new
    usage.max_rss = -777_i64
    status = -777
    empty = Darwin::Process.wait4(pid, pointerof(status), Wait::WNOHANG, pointerof(usage))
    return 100 unless empty.error == 0 && empty.primary == 0 && status == -777 && usage.max_rss == -777
    info = Darwin::Signal::Info.new
    info.number = -777
    empty = Darwin::Process.waitid(Wait::P_PID, pid.to_u32!, pointerof(info), Wait::WEXITED | Wait::WNOHANG)
    return 101 unless empty.error == 0 && empty.primary == 0 && info.pid == 0 && info.number == -777
    byte = 71_u8
    return 102 unless Darwin::Descriptor.write(writer, pointerof(byte), 1_u64).primary == 1
    return 103 unless observe(pid, Wait::WEXITED, pointerof(info))
    return 104 unless info.number == 20 && info.pid == pid && info.code == Darwin::Signal::CLD_EXITED && info.status == 42
    info.pid = 0
    repeat = Darwin::Process.waitid(Wait::P_PID, pid.to_u32!, pointerof(info), Wait::WEXITED | Wait::WNOWAIT | Wait::WNOHANG)
    return 105 unless repeat.error == 0 && info.pid == pid && info.code == Darwin::Signal::CLD_EXITED && info.status == 42

    # A usage-copy fault follows status copyout but does not reap this child.
    failed = Darwin::Process.wait4(pid, pointerof(status), Wait::WNOHANG, Pointer(Darwin::Resource::Usage).new(1_u64))
    return 106 unless failed.primary == -1 && failed.error == 14 && status == 42 &* 256
    collected = Darwin::Process.wait4(pid, pointerof(status), Wait::WNOHANG, pointerof(usage))
    return 107 unless collected.error == 0 && collected.primary == pid && status == 42 &* 256 && usage_valid(usage)
    return 108 unless usage.user.seconds > 0 || usage.system.seconds > 0 || usage.user.microseconds > 0 || usage.system.microseconds > 0
    duplicate = Darwin::Process.wait4(pid, pointerof(status), Wait::WNOHANG, pointerof(usage))
    return 109 unless duplicate.primary == -1 && duplicate.error == 10
    duplicate = Darwin::Process.waitid(Wait::P_PID, pid.to_u32!, pointerof(info), Wait::WEXITED | Wait::WNOHANG)
    duplicate.primary == -1 && duplicate.error == 10 ? 0 : 110
  end

  def self.collection_signal(pid : Int32) : Int32
    info = Darwin::Signal::Info.new
    usage = Darwin::Resource::Usage.new
    usage.max_rss = -777_i64
    status = -777
    return 111 unless Darwin::Signal.kill(pid, 17).error == 0 # SIGSTOP
    return 112 unless observe(pid, Wait::WSTOPPED, pointerof(info))
    return 113 unless info.pid == pid && info.code == Darwin::Signal::CLD_STOPPED && info.status == 17
    stopped = Darwin::Process.wait4(pid, pointerof(status), Wait::WUNTRACED | Wait::WNOHANG, pointerof(usage))
    return 114 unless stopped.error == 0 && stopped.primary == pid && status == 0x117f && usage.max_rss == -777
    consumed = Darwin::Process.wait4(pid, pointerof(status), Wait::WUNTRACED | Wait::WNOHANG, pointerof(usage))
    return 115 unless consumed.error == 0 && consumed.primary == 0 && usage.max_rss == -777
    return 116 unless Darwin::Signal.kill(pid, 19).error == 0 # SIGCONT
    return 117 unless observe(pid, Wait::WCONTINUED, pointerof(info))
    # The child acknowledged its default, unblocked SIGCONT setup before stop.
    return 118 unless info.pid == pid && info.code == Darwin::Signal::CLD_CONTINUED && info.status == 19
    continued = Darwin::Process.wait4(pid, pointerof(status), Wait::WCONTINUED | Wait::WNOHANG, pointerof(usage))
    return 119 unless continued.error == 0 && continued.primary == pid && status == 0x137f && usage.max_rss == -777
    return 120 unless Darwin::Signal.kill(pid, 9).error == 0
    return 121 unless observe(pid, Wait::WEXITED, pointerof(info))
    return 122 unless info.pid == pid && info.code == Darwin::Signal::CLD_KILLED && info.status == 9
    collected = Darwin::Process.wait4(pid, pointerof(status), Wait::WNOHANG, pointerof(usage))
    return 123 unless collected.error == 0 && collected.primary == pid && status == 9 && usage_valid(usage)
    duplicate = Darwin::Process.wait4(pid, pointerof(status), Wait::WNOHANG, pointerof(usage))
    duplicate.primary == -1 && duplicate.error == 10 ? 0 : 124
  end

  def self.collection_child(signal : Bool) : Int32
    pipe = Darwin::Descriptor.pipe
    return 125 unless pipe.error == 0
    reader, writer = pipe.primary.to_i32!, pipe.secondary.to_i32!
    prepared = Darwin::Descriptor.pipe
    if prepared.error != 0
      Darwin::Descriptor.close(reader)
      Darwin::Descriptor.close(writer)
      return 139
    end
    ready_reader, ready_writer = prepared.primary.to_i32!, prepared.secondary.to_i32!
    child = Darwin::Process.fork
    if child.error != 0
      Darwin::Descriptor.close(reader)
      Darwin::Descriptor.close(writer)
      Darwin::Descriptor.close(ready_reader)
      Darwin::Descriptor.close(ready_writer)
      return 126
    end
    if child.primary == 0
      Darwin::Descriptor.close(writer)
      Darwin::Descriptor.close(ready_reader)
      configured = collection_prepare
      byte = 71_u8
      sent = configured ? Darwin::Descriptor.write(ready_writer, pointerof(byte), 1_u64).primary : -1_i64
      # Preserve the write result across another trap. The optimized x86 case
      # catches a missing flags clobber when checking this result after close.
      Darwin::Descriptor.close(ready_writer)
      Darwin::Process.exit(139) unless configured && sent == 1
      ready = child_gate(reader)
      Darwin::Descriptor.close(reader)
      Darwin::Process.exit(127) unless ready
      count = 0
      while count < 5000
        Darwin::Process.pid
        count &+= 1
      end
      Darwin::Process.exit(42)
    end
    Darwin::Descriptor.close(reader)
    Darwin::Descriptor.close(ready_writer)
    pid = child.primary.to_i32!
    prepared = child_gate(ready_reader)
    Darwin::Descriptor.close(ready_reader)
    result = prepared ? (signal ? collection_signal(pid) : collection_exit(pid, writer)) : 139
    Darwin::Descriptor.close(writer)
    # Success paths already collected. Failure paths retain this owned PID
    # through termination and the bounded exclusive cleanup collector.
    collect(pid, 9, true) unless result == 0
    result
  end

  def self.collection_waitid : Int32
    group = Darwin::Process.getpgid
    return 134 unless group.error == 0
    child = Darwin::Process.fork
    return 134 unless child.error == 0
    Darwin::Process.exit(43) if child.primary == 0
    pid = child.primary.to_i32!
    info = Darwin::Signal::Info.new
    unless observe(pid, Wait::WEXITED, pointerof(info))
      collect(pid, 9, true)
      return 135
    end
    info.pid = 0
    observed = Darwin::Process.waitid(Wait::P_ALL, 0_u32, pointerof(info), Wait::WEXITED | Wait::WNOWAIT | Wait::WNOHANG)
    unless observed.error == 0 && info.pid == pid && info.code == Darwin::Signal::CLD_EXITED && info.status == 43
      collect(pid, 9, true)
      return 136
    end
    info.pid = 0
    collected = Darwin::Process.waitid(Wait::P_PGID, group.primary.to_u32!, pointerof(info), Wait::WEXITED | Wait::WNOHANG)
    unless collected.error == 0 && info.pid == pid && info.code == Darwin::Signal::CLD_EXITED && info.status == 43
      collect(pid, 9, true)
      return 137
    end
    status = 0
    duplicate = Darwin::Process.waitpid(pid, pointerof(status), Wait::WNOHANG)
    duplicate.primary == -1 && duplicate.error == 10 ? 0 : 138
  end

  def self.collection_prepare : Bool
    # Set and query the target's policy after fork. A parent-side setup alone
    # does not establish the state of a translated child at its readiness gate.
    action = Darwin::Signal::Action.new(0_u64, 0_u64, 0_u32, 0)
    return false unless Darwin::Signal.action(19, pointerof(action)).error == 0
    continuation = 1_u32.unsafe_shl(18)
    return false unless Darwin::Signal.mask(2, pointerof(continuation), Pointer(UInt32).null).error == 0
    previous = uninitialized UInt8[16]
    queried = Darwin::Signal.action(19, Pointer(Darwin::Signal::Action).null, previous.to_unsafe.as(Void*))
    return false unless queried.error == 0 && previous.to_unsafe.as(UInt64*).value == 0
    observed = UInt32::MAX
    queried = Darwin::Signal.mask(0, Pointer(UInt32).null, pointerof(observed))
    queried.error == 0 && observed & continuation == 0
  end

  def self.collection : Int32
    usage = Darwin::Resource::Usage.new
    self_usage = Darwin::Resource.getrusage(Darwin::Resource::RUSAGE_SELF, pointerof(usage))
    return 128 unless self_usage.error == 0 && self_usage.primary == 0 && usage_valid(usage)
    child_usage = Darwin::Resource.getrusage(Darwin::Resource::RUSAGE_CHILDREN, pointerof(usage))
    return 129 unless child_usage.error == 0 && child_usage.primary == 0 && usage_valid(usage)
    usage.max_rss = -777_i64
    invalid = Darwin::Resource.getrusage(1, pointerof(usage))
    return 130 unless invalid.primary == -1 && invalid.error == 22 && usage.max_rss == -777
    status = -777
    invalid = Darwin::Process.wait4(Int32::MIN, pointerof(status), Wait::WNOHANG, pointerof(usage))
    return 131 unless invalid.primary == -1 && invalid.error == 22 && status == -777 && usage.max_rss == -777
    info = Darwin::Signal::Info.new
    info.pid = -777
    invalid = Darwin::Process.waitid(Wait::P_ALL, 0_u32, pointerof(info), 0x40000000)
    return 132 unless invalid.primary == -1 && invalid.error == 22 && info.pid == -777
    result = collection_child(false)
    return result unless result == 0
    result = collection_child(true)
    return result unless result == 0
    result = collection_waitid
    return result unless result == 0
    result = Darwin::Resource.getrusage(Darwin::Resource::RUSAGE_CHILDREN, pointerof(usage))
    result.error == 0 && usage_valid(usage) && usage.max_rss > 0 ? 0 : 133
  end
end
