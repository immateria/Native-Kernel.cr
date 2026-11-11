module Behavior
  def self.inspection_self : Int32
    pid = Darwin::Process.pid.primary.to_i32!
    record = uninitialized Darwin::Process::Info::Record
    identified = Darwin::Process.info(pid, Darwin::Process::Info::PIDT_BSDINFOWITHUNIQID, 0_u64, pointerof(record).as(Void*), sizeof(typeof(record)))
    return 140 unless identified.error == 0 && identified.primary == sizeof(typeof(record)) && record.bsd.pid == pid && record.unique.unique_id != 0
    bsd = uninitialized Darwin::Process::Info::Bsd
    task = uninitialized Darwin::Process::Info::Task
    all = uninitialized Darwin::Process::Info::All
    b = Darwin::Process.info(pid, pointerof(bsd))
    t = Darwin::Process.info(pid, pointerof(task))
    a = Darwin::Process.info(pid, pointerof(all))
    return 141 unless b.error == 0 && b.primary == sizeof(typeof(bsd)) && bsd.pid == pid && t.error == 0 && t.primary == sizeof(typeof(task)) && task.virtual_size >= task.resident_size && task.threads > 0 && a.error == 0 && a.primary == sizeof(typeof(all)) && all.bsd.pid == pid && all.task.threads > 0
    flags = Darwin::Process::Info::PIF_COMPARE_UNIQUEID
    identity = record.unique.unique_id
    b = Darwin::Process.info(pid, pointerof(bsd), flags, identity)
    t = Darwin::Process.info(pid, pointerof(task), flags, identity)
    a = Darwin::Process.info(pid, pointerof(all), flags, identity)
    return 142 unless b.error == 0 && b.primary == sizeof(typeof(bsd)) && bsd.pid == pid && t.error == 0 && t.primary == sizeof(typeof(task)) && a.error == 0 && a.primary == sizeof(typeof(all)) && all.bsd.pid == pid
    version = record.unique.pid_version.to_u32!.to_u64
    b = Darwin::Process.info(pid, pointerof(bsd), Darwin::Process::Info::PIF_COMPARE_IDVERSION, version)
    return 143 unless b.error == 0 && b.primary == sizeof(typeof(bsd)) && bsd.pid == pid
    bsd.pid = 0xffffffff_u32
    mismatch = Darwin::Process.info(pid, pointerof(bsd), flags, identity ^ 1_u64)
    return 144 unless mismatch.primary == -1 && mismatch.error == 3 && bsd.pid == 0xffffffff_u32
    mismatch = Darwin::Process.info(pid, pointerof(bsd), Darwin::Process::Info::PIF_COMPARE_IDVERSION, version ^ 1_u64)
    return 145 unless mismatch.primary == -1 && mismatch.error == 3 && bsd.pid == 0xffffffff_u32
    invalid = Darwin::Process.info(pid, pointerof(bsd), 3_u32, identity)
    return 146 unless invalid.primary == -1 && invalid.error == 22 && bsd.pid == 0xffffffff_u32
    short = Darwin::Process.info(pid, Darwin::Process::Info::PIDTBSDINFO, 0_u64, pointerof(bsd).as(Void*), sizeof(typeof(bsd)) &- 1)
    return 147 unless short.primary == -1 && short.error == 12 && bsd.pid == 0xffffffff_u32
    invalid = Darwin::Process.info(pid, -1, 0_u64, pointerof(bsd).as(Void*), sizeof(typeof(bsd)))
    return 148 unless invalid.primary == -1 && invalid.error == 22 && bsd.pid == 0xffffffff_u32

    v0 = uninitialized Darwin::Process::Usage::V0
    v1 = uninitialized Darwin::Process::Usage::V1
    v2 = uninitialized Darwin::Process::Usage::V2
    r0 = Darwin::Process.usage(pid, pointerof(v0))
    r1 = Darwin::Process.usage(pid, pointerof(v1))
    r2 = Darwin::Process.usage(pid, pointerof(v2))
    return 149 unless r0.error == 0 && r0.primary == 0 && v0.resident_size > 0 && v0.start > 0 && v0.exit == 0 && r1.error == 0 && r1.primary == 0 && v1.start == v0.start && r2.error == 0 && r2.primary == 0 && v2.start == v0.start && v2.exit == 0
    v0.resident_size = UInt64::MAX
    invalid = Darwin::Raw.call(336, 9_u64, pid.to_u64!, 99_u64, 0_u64, pointerof(v0).address, 0_u64)
    invalid.primary == -1 && invalid.error == 22 && v0.resident_size == UInt64::MAX ? 0 : 150
  end

  def self.inspection_list(type : UInt32, filter : UInt32, pid : Int32) : Bool
    pids = uninitialized Int32[256]
    listed = Darwin::Process.list(type, filter, pids.to_unsafe.as(Void*), sizeof(typeof(pids)))
    return false unless listed.error == 0 && listed.primary >= 4 && listed.primary < sizeof(typeof(pids)) && listed.primary.unsafe_mod(4_i64) == 0
    offset = 0_i64
    while offset < listed.primary.unsafe_div(4_i64)
      return true if pids.to_unsafe[offset] == pid
      offset &+= 1
    end
    false
  end

  def self.inspection_child(pid : Int32) : Int32
    return 151 unless Darwin::Process.setpgid(pid, pid).error == 0
    return 152 unless inspection_list(Darwin::Process::Info::PGRP_ONLY, pid.to_u32!, pid)
    return 153 unless inspection_list(Darwin::Process::Info::PPID_ONLY, Darwin::Process.pid.primary.to_u32!, pid)
    record = uninitialized Darwin::Process::Info::Record
    identified = Darwin::Process.info(pid, Darwin::Process::Info::PIDT_BSDINFOWITHUNIQID, 0_u64, pointerof(record).as(Void*), sizeof(typeof(record)))
    return 154 unless identified.error == 0 && identified.primary == sizeof(typeof(record)) && record.bsd.pid == pid && record.bsd.ppid == Darwin::Process.pid.primary
    task = uninitialized Darwin::Process::Info::Task
    read = Darwin::Process.info(pid, pointerof(task), Darwin::Process::Info::PIF_COMPARE_UNIQUEID, record.unique.unique_id)
    return 155 unless read.error == 0 && read.primary == sizeof(typeof(task)) && task.threads > 0
    usage = uninitialized Darwin::Process::Usage::V2
    read = Darwin::Process.usage(pid, pointerof(usage))
    return 156 unless read.error == 0 && read.primary == 0 && usage.exit == 0 && usage.start > 0
    0
  end

  def self.inspection : Int32
    result = inspection_self
    return result unless result == 0
    pipe = Darwin::Descriptor.pipe
    return 157 unless pipe.error == 0
    reader, writer = pipe.primary.to_i32!, pipe.secondary.to_i32!
    child = Darwin::Process.fork
    if child.error != 0
      Darwin::Descriptor.close(reader)
      Darwin::Descriptor.close(writer)
      return 158
    end
    if child.primary == 0
      Darwin::Descriptor.close(writer)
      ready = child_gate(reader)
      Darwin::Descriptor.close(reader)
      Darwin::Process.exit(ready ? 0 : 1)
    end
    Darwin::Descriptor.close(reader)
    pid = child.primary.to_i32!
    result = inspection_child(pid)
    unless result == 0
      Darwin::Descriptor.close(writer)
      collect(pid, 9, true)
      return result
    end
    byte = 71_u8
    released = Darwin::Descriptor.write(writer, pointerof(byte), 1_u64)
    Darwin::Descriptor.close(writer)
    collected = collect(pid, 0, released.error != 0)
    return 159 unless released.error == 0 && collected
    # A reaped owned PID is absent at this instant. These numeric queries are
    # not a promise against later reuse; the fixture does not signal it again.
    task = uninitialized Darwin::Process::Info::Task
    missing = Darwin::Process.info(pid, pointerof(task))
    return 160 unless missing.primary == -1 && missing.error == 3
    usage = uninitialized Darwin::Process::Usage::V0
    missing = Darwin::Process.usage(pid, pointerof(usage))
    missing.primary == -1 && missing.error == 3 ? 0 : 161
  end
end
