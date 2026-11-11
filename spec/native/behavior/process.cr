module Behavior
  def self.resource : Int32
    original = Darwin::Resource::Limit.new
    return 40 unless Darwin::Resource.get(8, pointerof(original)).error == 0 && original.soft > 1
    changed = Darwin::Resource::Limit.new(original.soft &- 1_u64, original.hard)
    return 41 unless Darwin::Resource.set(8, pointerof(changed)).error == 0
    observed = Darwin::Resource::Limit.new
    read = Darwin::Resource.get(8, pointerof(observed))
    restored = Darwin::Resource.set(8, pointerof(original))
    final = Darwin::Resource::Limit.new
    checked = Darwin::Resource.get(8, pointerof(final))
    read.error == 0 && observed.soft == changed.soft && observed.hard == original.hard && restored.error == 0 && checked.error == 0 && final.soft == original.soft && final.hard == original.hard ? 0 : 42
  end

  def self.session : Int32
    inherited_group = Darwin::Process.getpgid
    inherited_session = Darwin::Process.getsid
    return 43 unless inherited_group.error == 0 && inherited_session.error == 0
    child = Darwin::Process.fork
    return 43 unless child.error == 0
    if child.primary == 0
      pid = Darwin::Process.pid.primary.to_i32!
      invalid = Darwin::Process.setpgid(0, -1)
      Darwin::Process.exit(44) unless invalid.primary == -1 && invalid.error == 22
      created = Darwin::Process.setpgid(pid, pid)
      group = Darwin::Process.getpgid
      session = Darwin::Process.getsid
      Darwin::Process.exit(44) unless created.error == 0 && created.primary == 0 && group.error == 0 && group.primary == pid && session.error == 0 && session.primary == inherited_session.primary

      joined = Darwin::Process.setpgid(pid, inherited_group.primary.to_i32!)
      group = Darwin::Process.getpgid(pid)
      Darwin::Process.exit(44) unless joined.error == 0 && joined.primary == 0 && group.error == 0 && group.primary == inherited_group.primary

      restored = Darwin::Process.setpgid(0, 0)
      group = Darwin::Process.getpgid(pid)
      session = Darwin::Process.getsid(pid)
      refused = Darwin::Process.setsid
      Darwin::Process.exit(restored.error == 0 && restored.primary == 0 && group.error == 0 && group.primary == pid && session.error == 0 && session.primary == inherited_session.primary && refused.primary == -1 && refused.error == 1 ? 0 : 44)
    end
    return 45 unless collect(child.primary.to_i32!, 0)

    child = Darwin::Process.fork
    return 43 unless child.error == 0
    if child.primary == 0
      pid = Darwin::Process.pid.primary
      session = Darwin::Process.setsid
      observed = Darwin::Process.getsid
      group = Darwin::Process.getpgid
      Darwin::Process.exit(44) unless session.error == 0 && session.primary == pid && observed.error == 0 && observed.primary == pid && group.error == 0 && group.primary == pid
      observed = Darwin::Process.getsid(pid.to_i32!)
      group = Darwin::Process.getpgid(pid.to_i32!)
      refused_group = Darwin::Process.setpgid(0, 0)
      refused_session = Darwin::Process.setsid
      Darwin::Process.exit(observed.error == 0 && observed.primary == pid && group.error == 0 && group.primary == pid && refused_group.primary == -1 && refused_group.error == 1 && refused_session.primary == -1 && refused_session.error == 1 ? 0 : 44)
    end
    collect(child.primary.to_i32!, 0) ? 0 : 45
  end

  def self.exec(path : UInt8*) : Int32
    arguments = StaticArray(UInt8*, 3).new(Pointer(UInt8).null)
    arguments.to_unsafe[0] = path
    arguments.to_unsafe[1] = "nk-exec-proof".to_unsafe
    environment = StaticArray(UInt8*, 2).new(Pointer(UInt8).null)
    environment.to_unsafe[0] = "NK_EXEC_PROOF=1".to_unsafe
    Darwin::Process.execve(path, arguments.to_unsafe, environment.to_unsafe)
    46
  end

  def self.process(path : UInt8*) : Int32
    required = Darwin::Process.list(Pointer(Void).null, 0)
    return 47 unless required.error == 0 && required.primary > 0 && required.primary < 1_000_000
    # Fixed caller-owned storage, with headroom and an explicit saturation check.
    # Darwin's sizing result is advisory: processes can appear between calls.
    pids = uninitialized Int32[262144]
    listed = Darwin::Process.list(pids.to_unsafe.as(Void*), sizeof(typeof(pids)))
    return 48 unless listed.error == 0 && listed.primary > 0 && listed.primary < sizeof(typeof(pids)) && listed.primary.unsafe_mod(4_i64) == 0
    pid = Darwin::Process.pid.primary
    found = false
    offset = 0_i64
    while offset < listed.primary.unsafe_div(4_i64)
      found = true if pids.to_unsafe[offset] == pid
      offset &+= 1
    end
    record = uninitialized Darwin::Process::Info::Record
    info = Darwin::Process.info(pid.to_i32!, Darwin::Process::Info::PIDT_BSDINFOWITHUNIQID, 0_u64, pointerof(record).as(Void*), sizeof(typeof(record)))
    return 49 unless found && info.error == 0 && info.primary == sizeof(typeof(record)) && record.bsd.pid == pid && record.bsd.ppid == Darwin::Process.parent.primary && record.unique.unique_id != 0
    spawn(path)
  end
end
