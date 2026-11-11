module Behavior
  def self.event : Int32
    queue = Darwin::Event.queue
    return 60 unless queue.error == 0 && queue.primary >= 0
    fd = queue.primary.to_i32!
    pipe = Darwin::Descriptor.pipe
    unless pipe.error == 0
      Darwin::Descriptor.close(fd)
      return 61
    end
    read_fd = pipe.primary.to_i32!
    write_fd = pipe.secondary.to_i32!
    child = Darwin::Process.fork
    if child.error != 0
      Darwin::Descriptor.close(read_fd)
      Darwin::Descriptor.close(write_fd)
      Darwin::Descriptor.close(fd)
      return 62
    end
    if child.primary == 0
      Darwin::Descriptor.close(write_fd)
      Darwin::Descriptor.close(fd)
      ready = child_gate(read_fd)
      Darwin::Descriptor.close(read_fd)
      Darwin::Process.exit(ready ? 37 : 63)
    end
    pid = child.primary.to_i32!
    Darwin::Descriptor.close(read_fd)
    result = event_body(fd, pid, write_fd)
    closed_pipe = Darwin::Descriptor.close(write_fd)
    collected = collect(pid, 37 &* 256, result != 0)
    closed = Darwin::Descriptor.close(fd)
    result == 0 && closed_pipe.error == 0 && collected && closed.error == 0 ? 0 : 64
  end

  def self.event_body(fd : Int32, pid : Int32, gate : Int32) : Int32
    change = Darwin::Event::Kevent64.new
    change.ident = pid.to_u64!
    change.filter = Darwin::Event::EVFILT_PROC
    change.flags = Darwin::Event::EV_ADD | Darwin::Event::EV_ONESHOT
    change.fflags = Darwin::Event::NOTE_EXIT
    event = Darwin::Event::Kevent64.new
    registered = Darwin::Event.wait(fd, pointerof(change), 1, pointerof(event), 1, Darwin::Event::IMMEDIATE, Pointer(Void).null)
    return 65 unless registered.error == 0 && registered.primary == 0
    byte = 71_u8
    written = Darwin::Descriptor.write(gate, pointerof(byte), 1_u64)
    return 66 unless written.error == 0 && written.primary == 1
    attempt = 0
    while attempt < 2000
      result = Darwin::Event.wait(fd, Pointer(Darwin::Event::Kevent64).null, 0, pointerof(event), 1, Darwin::Event::IMMEDIATE, Pointer(Void).null)
      if result.error == 0 && result.primary == 1
        return event.ident == pid && event.filter == Darwin::Event::EVFILT_PROC && event.flags & Darwin::Event::EV_ERROR == 0 && event.fflags & Darwin::Event::NOTE_EXIT != 0 ? 0 : 67
      end
      return 68 unless result.error == 4 || (result.error == 0 && result.primary == 0)
      Darwin::Event.sleep(1000_u32)
      attempt &+= 1
    end
    69
  end
end
