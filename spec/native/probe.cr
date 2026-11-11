# Compile with -Dwithout_main. No Crystal runtime initialization takes place.
require "../../src/native-kernel/darwin"

module Probe
  alias Darwin = Native::Kernel::Darwin

  def self.collect(pid : Int32, code : Int32) : Bool
    status = 0
    result = Darwin::Process.waitpid(pid, pointerof(status), 0)
    while result.error == 4
      result = Darwin::Process.waitpid(pid, pointerof(status), 0)
    end
    result.error == 0 && result.primary == pid && status == code &* 256
  end

  def self.raw : Int32
    pipe = Darwin::Raw.call(42)
    return 1 unless pipe.error == 0 && pipe.primary >= 0 && pipe.secondary >= 0 && pipe.primary != pipe.secondary
    byte = 71_u8
    written = Darwin::Descriptor.write(pipe.secondary.to_i32!, pointerof(byte), 1_u64)
    byte = 0_u8
    read = Darwin::Descriptor.read(pipe.primary.to_i32!, pointerof(byte), 1_u64)
    first = Darwin::Descriptor.close(pipe.primary.to_i32!)
    second = Darwin::Descriptor.close(pipe.secondary.to_i32!)
    return 2 unless written.primary == 1 && read.primary == 1 && byte == 71 && first.error == 0 && second.error == 0
    failed = Darwin::Raw.call(3, UInt64::MAX, 0_u64, 1_u64)
    return 3 unless failed.primary == -1 && failed.error == 9
    seventh = Darwin::Raw.call(374, UInt64::MAX, 0_u64, 0_u64, 0_u64, 0_u64, 1_u64, 1_u64, 0_u64)
    eighth = Darwin::Raw.call(374, UInt64::MAX, 0_u64, 0_u64, 0_u64, 0_u64, 0_u64, 0_u64, 0x400_u64)
    return 4 unless seventh.error == 14 && eighth.error == 22
    child = Darwin::Raw.call(2)
    return 5 unless child.error == 0
    if child.secondary != 0
      Darwin::Process.exit(child.primary == Darwin::Process.pid.primary ? 41 : 42)
    end
    return 6 unless child.primary > 0 && collect(child.primary.to_i32!, 41)
    child = Darwin::Process.fork
    return 7 unless child.error == 0
    if child.secondary != 0
      Darwin::Process.exit(child.primary == 0 ? 43 : 44)
    end
    return 8 unless child.primary > 0 && collect(child.primary.to_i32!, 43)
    0
  end

  def self.mach : Int32
    transport = Darwin::Mach.transport(Darwin::Process.release)
    return 9 unless transport
    task = Darwin::Mach.task
    return 9 if task == 0 || task == UInt32::MAX
    before_names, names_read, names_cleanup = Darwin::Mach.port_name_count(task, transport)
    return 10 unless names_read == 0 && names_cleanup == 0
    name, code = Darwin::Mach.open(task, Darwin::Process.pid.primary.to_i32!)
    return 11 unless code == 0
    retained = Darwin::Mach.retain(task, name)
    words, count, read = Darwin::Mach.read(task, name, transport)
    _invalid, _count, invalid = Darwin::Mach.read(task, 0xfffffffe_u32, transport)
    # Measure repeated exchanges without managed-runtime observers or GC.
    repeated = 0
    while repeated < 100
      _words, repeated_count, repeated_code = Darwin::Mach.read(task, name, transport)
      read = repeated_code if repeated_code != 0
      read = -300 unless repeated_count == 8
      _failed, failed_count, failed_code = Darwin::Mach.read(task, 0xfffffffe_u32, transport)
      invalid = 0 if failed_code == 0 || failed_count != 0
      repeated &+= 1
    end
    release = Darwin::Mach.release(task, name)
    release_again = Darwin::Mach.release(task, name)
    after_names, names_after, after_cleanup = Darwin::Mach.port_name_count(task, transport)
    task_release = Darwin::Mach.release(task, task)
    return 12 unless retained == 0 && read == 0 && count == 8 && words.to_unsafe[5] == Darwin::Process.pid.primary && invalid != 0 && names_after == 0 && after_cleanup == 0 && after_names == before_names
    return 13 unless release == 0 && release_again == 0 && task_release == 0
    0
  end

  def self.typed : Int32
    return 13 unless Darwin::Process.release > 0 && Darwin::Process.parent.error == 0
    limit = Darwin::Resource::Limit.new
    return 14 unless Darwin::Resource.get(8, pointerof(limit)).error == 0 && limit.soft > 0
    return 15 if Darwin::Resource.set(-1, pointerof(limit)).error == 0
    queue = Darwin::Event.queue
    return 16 unless queue.error == 0
    change = Darwin::Event::Kevent64.new
    result = Darwin::Event.wait(queue.primary.to_i32!, pointerof(change), 0, pointerof(change), 1, Darwin::Event::IMMEDIATE, Pointer(Void).null)
    Darwin::Descriptor.close(queue.primary.to_i32!)
    return 17 unless result.error == 0 && result.primary == 0
    return 18 unless Darwin::Event.sleep(1_u32).error == 0
    poll = Darwin::Event::Poll.new(-1)
    return 19 unless Darwin::Event.poll(pointerof(poll), 1_u32, 0).error == 0
    socket = Darwin::Descriptor.socket(1, 1, 0)
    return 20 unless socket.error == 0
    Darwin::Descriptor.close(socket.primary.to_i32!)
    return 21 unless Darwin::Signal.action(1, Pointer(Darwin::Signal::Action).null, Pointer(Void).null).error == 0
    return 22 unless Darwin::Signal.mask(0, Pointer(UInt32).null, Pointer(UInt32).null).error == 0
    return 23 unless Darwin::Signal.kill(Darwin::Process.pid.primary.to_i32!, 0).error == 0
    bytes = uninitialized UInt8[256]
    base = 0_i64
    return 24 unless Darwin::Descriptor.open(Pointer(UInt8).null, 0).error != 0
    return 25 unless Darwin::Descriptor.fcntl(-1, 1).error == 9
    return 26 unless Darwin::Descriptor.connect(-1, Pointer(Void).null, 0_u32).error == 9
    return 27 unless Darwin::Descriptor.entries(-1, bytes.to_unsafe, 256, pointerof(base)).error == 9
    return 28 unless Darwin::Descriptor.seek(-1, 0_i64, 0).error == 9
    return 29 unless Darwin::Process.list(Pointer(Void).null, 0).error == 0
    record = uninitialized Darwin::Process::Info::Short
    info = Darwin::Process.info(Darwin::Process.pid.primary.to_i32!, Darwin::Process::Info::PIDT_SHORTBSDINFO, 0_u64, pointerof(record).as(Void*), sizeof(typeof(record)))
    return 30 unless info.error == 0 && record.pid == Darwin::Process.pid.primary
    return 31 unless Darwin::Process.execve(Pointer(UInt8).null, Pointer(Pointer(UInt8)).null, Pointer(Pointer(UInt8)).null).error != 0
    return 32 if Darwin::Process.signal(Pointer(UInt32).null, 1) == 0
    0
  end

  def self.run(argc : Int32) : Int32
    result = raw
    return result unless result == 0
    result = mach
    return result unless result == 0
    # Instantiate remaining primitives without changing the probe's session.
    if argc == 99
      Darwin::Process.setsid
      Darwin::Signal.restore(Pointer(Void).null, 0, 0_u64)
    end
    typed
  end
end

fun main(argc : Int32, argv : UInt8**) : Int32
  Native::Kernel::Darwin::Process.exit(Probe.run(argc))
end
