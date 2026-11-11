# Darwin 21 task-token transport proof. Build with -Dwithout_main.
# Parent -> one gated owned child. The parent is the sole collector; it does
# not change sessions or groups, so the runner's process-group cleanup remains
# an independent outer bound only.
require "../../src/native-kernel/darwin"

module MontereyTaskToken
  alias Darwin = Native::Kernel::Darwin

  def self.collect(pid : Int32, expected : Int32, terminate : Bool) : Bool
    status = 0
    attempt = 0
    while attempt < 2000
      result = Darwin::Process.waitpid(pid, pointerof(status), 1) # WNOHANG
      return result.error == 0 && status == expected if result.primary == pid
      return false unless result.error == 0 || result.error == 4
      if terminate && result.error == 0 && result.primary == 0
        Darwin::Signal.kill(pid, 9)
        terminate = false
      end
      Darwin::Event.sleep(1000_u32)
      attempt &+= 1
    end
    Darwin::Signal.kill(pid, 9)
    attempt = 0
    while attempt < 2000
      result = Darwin::Process.waitpid(pid, pointerof(status), 1)
      return false if result.primary == pid || result.error == 10
      return false unless result.error == 0 || result.error == 4
      Darwin::Event.sleep(1000_u32)
      attempt &+= 1
    end
    false
  end

  def self.gate(fd : Int32) : Bool
    event = Darwin::Event::Poll.new(fd)
    ready = Darwin::Event.poll(pointerof(event), 1_u32, 5000)
    return false unless ready.error == 0 && ready.primary == 1
    byte = 0_u8
    read = Darwin::Descriptor.read(fd, pointerof(byte), 1_u64)
    read.error == 0 && read.primary == 1 && byte == 71
  end

  def self.token_matches(task : UInt32, target : UInt32, transport : Darwin::Mach::Transport,
                         pid : Int32) : Bool
    words, count, code = Darwin::Mach.read(task, target, transport)
    code == 0 && count == 8 && words.to_unsafe[5] == pid && words.to_unsafe[7] != 0_u32
  end

  def self.run : Int32
    transport = Darwin::Mach.transport(Darwin::Process.release)
    return 2 unless transport == Darwin::Mach::Transport::MachMsgTrap
    task = Darwin::Mach.task
    return 3 if task == 0 || task == UInt32::MAX

    self_pid = Darwin::Process.pid.primary.to_i32!
    repeated = 0
    while repeated < 32
      unless token_matches(task, task, transport, self_pid)
        Darwin::Mach.release(task, task)
        return 4
      end
      _words, count, failed = Darwin::Mach.read(task, 0xfffffffe_u32, transport)
      unless failed != 0 && count == 0
        Darwin::Mach.release(task, task)
        return 5
      end
      repeated &+= 1
    end

    pipe = Darwin::Descriptor.pipe
    unless pipe.error == 0
      Darwin::Mach.release(task, task)
      return 6
    end
    reader, writer = pipe.primary.to_i32!, pipe.secondary.to_i32!
    child = Darwin::Process.fork
    if child.error != 0
      Darwin::Descriptor.close(reader)
      Darwin::Descriptor.close(writer)
      Darwin::Mach.release(task, task)
      return 7
    end
    if child.primary == 0
      Darwin::Descriptor.close(writer)
      ready = gate(reader)
      Darwin::Descriptor.close(reader)
      Darwin::Process.exit(ready ? 0 : 8)
    end

    pid = child.primary.to_i32!
    Darwin::Descriptor.close(reader)
    name, opened = Darwin::Mach.open(task, pid)
    if opened != 0
      Darwin::Descriptor.close(writer)
      collected = collect(pid, 9, true)
      Darwin::Mach.release(task, task)
      return collected ? 9 : 10
    end

    target_reads = 0
    target_ok = true
    while target_reads < 32
      target_ok = false unless token_matches(task, name, transport, pid)
      target_reads &+= 1
    end
    byte = 71_u8
    released_gate = Darwin::Descriptor.write(writer, pointerof(byte), 1_u64)
    closed = Darwin::Descriptor.close(writer)
    # The child exits naturally only after the owned gate. This establishes the
    # post-death request path without leaving a session/group-changing child.
    collected = released_gate.error == 0 && released_gate.primary == 1 && closed.error == 0 && collect(pid, 0, false)
    _words, dead_count, dead = Darwin::Mach.read(task, name, transport)
    released_name = Darwin::Mach.release(task, name)
    released_task = Darwin::Mach.release(task, task)
    target_ok && collected && dead != 0 && dead_count == 0 && released_name == 0 && released_task == 0 ? 0 : 11
  end

  def self.finish(code : Int32) : Int32
    return code unless code == 0
    completed = Darwin::Descriptor.write(1, "NK_OK task-token\n".to_unsafe, 17_u64)
    completed.error == 0 && completed.primary == 17 ? 0 : 13
  end
end

fun main(argc : Int32, argv : UInt8**) : Int32
  code = argc == 1 ? MontereyTaskToken.run : 12
  Native::Kernel::Darwin::Process.exit(MontereyTaskToken.finish(code))
end
