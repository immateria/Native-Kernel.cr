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
    return 64 unless result == 0 && closed_pipe.error == 0 && collected && closed.error == 0
    signal_event
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

  def self.signal_event : Int32
    previous = uninitialized UInt8[32]
    queried = Darwin::Signal.action(30, Pointer(Darwin::Signal::Action).null, previous.to_unsafe.as(Void*))
    return 70 unless queried.error == 0
    previous_handler = previous.to_unsafe.as(UInt64*).value
    previous_mask = (previous.to_unsafe + 8).as(UInt32*).value
    previous_flags = (previous.to_unsafe + 12).as(Int32*).value
    return 70 unless previous_handler == 0_u64

    ignored = Darwin::Signal::Action.new(1_u64, 0_u64, 0_u32, 0_i32)
    installed = Darwin::Signal.action(30, pointerof(ignored))
    return 71 unless installed.error == 0

    result = signal_event_body
    # The returned old-action record omits the trampoline field present in the
    # installation record, so reconstruct the exact default mask and flags.
    restored_action = Darwin::Signal::Action.new(previous_handler, 0_u64, previous_mask, previous_flags)
    restored = Darwin::Signal.action(30, pointerof(restored_action))
    restored.error == 0 ? result : 80
  end

  def self.signal_event_body : Int32
    queue = Darwin::Event.queue
    return 72 unless queue.error == 0 && queue.primary >= 0
    fd = queue.primary.to_i32!
    change = Darwin::Event::Kevent64.new
    change.ident = 30_u64
    change.filter = Darwin::Event::EVFILT_SIGNAL
    change.flags = Darwin::Event::EV_ADD | Darwin::Event::EV_ONESHOT
    event = Darwin::Event::Kevent64.new
    registered = Darwin::Event.wait(fd, pointerof(change), 1, pointerof(event), 1,
      Darwin::Event::IMMEDIATE, Pointer(Void).null)
    result = registered.error == 0 && registered.primary == 0 ? 0 : 73

    if result == 0
      pid = Darwin::Process.pid
      sent = pid.error == 0 ? Darwin::Signal.kill(pid.primary.to_i32!, 30) : pid
      result = 74 unless pid.error == 0 && sent.error == 0
    end

    attempt = 0
    while result == 0 && attempt < 2000
      waited = Darwin::Event.wait(fd, Pointer(Darwin::Event::Kevent64).null, 0,
        pointerof(event), 1, Darwin::Event::IMMEDIATE, Pointer(Void).null)
      if waited.error == 0 && waited.primary == 1
        result = event.ident == 30_u64 && event.filter == Darwin::Event::EVFILT_SIGNAL &&
                 event.flags & Darwin::Event::EV_ERROR == 0 && event.data >= 1 ? 0 : 75
        break
      end
      unless waited.error == 4 || (waited.error == 0 && waited.primary == 0)
        result = 76
        break
      end
      Darwin::Event.sleep(1000_u32)
      attempt &+= 1
    end
    result = 77 if result == 0 && attempt == 2000

    current = uninitialized UInt8[32]
    current_action = Darwin::Signal.action(30, Pointer(Darwin::Signal::Action).null,
      current.to_unsafe.as(Void*))
    result = 78 if result == 0 &&
                   (current_action.error != 0 || current.to_unsafe.as(UInt64*).value != 1_u64)
    closed = Darwin::Descriptor.close(fd)
    result == 0 && closed.error != 0 ? 79 : result
  end
end
