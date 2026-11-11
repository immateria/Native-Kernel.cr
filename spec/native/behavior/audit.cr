module Behavior
  def self.audit : Int32
    return 77 if Darwin::Process.release < 24
    pipe = Darwin::Descriptor.pipe
    return 70 unless pipe.error == 0
    read_fd = pipe.primary.to_i32!
    write_fd = pipe.secondary.to_i32!
    child = Darwin::Process.fork
    if child.error != 0
      Darwin::Descriptor.close(read_fd)
      Darwin::Descriptor.close(write_fd)
      return 71
    end
    if child.primary == 0
      Darwin::Descriptor.close(write_fd)
      ready = child_gate(read_fd)
      Darwin::Descriptor.close(read_fd)
      Darwin::Process.exit(ready ? 72 : 73)
    end
    pid = child.primary.to_i32!
    Darwin::Descriptor.close(read_fd)
    result = audit_body(pid)
    closed = Darwin::Descriptor.close(write_fd)
    collected = collect(pid, 15, result != 0)
    result == 0 && closed.error == 0 && collected ? 0 : 74
  end

  def self.audit_body(pid : Int32) : Int32
    task = Darwin::Mach.task
    return 75 if task == 0 || task == UInt32::MAX
    name, opened = Darwin::Mach.open(task, pid)
    if opened != 0
      Darwin::Mach.release(task, task)
      return 76
    end
    words, count, read = Darwin::Mach.read(task, name)
    released = Darwin::Mach.release(task, name)
    task_released = Darwin::Mach.release(task, task)
    return 78 unless read == 0 && count == 8 && words.to_unsafe[5] == pid && released == 0 && task_released == 0
    version = words.to_unsafe[7]
    words.to_unsafe[7] = version ^ 1_u32
    rejected = Darwin::Process.signal(words.to_unsafe, 15)
    return 79 unless rejected == 3 # ESRCH: same PID, stale version must not signal
    status = 0
    alive = Darwin::Process.waitpid(pid, pointerof(status), 1)
    return 80 unless alive.error == 0 && alive.primary == 0
    words.to_unsafe[7] = version
    Darwin::Process.signal(words.to_unsafe, 15) == 0 ? 0 : 81
  end
end
