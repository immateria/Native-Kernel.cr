module LinuxBehavior
  def self.pidfd_body(pid : Int32, fd : Int32) : Int32
    return 58 unless D.fcntl(fd, D::F_GETFD).primary == D::FD_CLOEXEC
    poll = E::Poll.new(fd)
    timeout = E::Timespec.new
    initial = E.ppoll(pointerof(poll), 1_u32, pointerof(timeout), Pointer(S::Set).null)
    return 59 unless initial.error == 0 && initial.primary == 0 && poll.revents == 0
    nonblocking = Linux::Pidfd.open(pid, Linux::Pidfd::NONBLOCK)
    return 120 unless nonblocking.error == 0
    no_event = S::Info.new
    refused = P.waitid(W::P_PIDFD, nonblocking.primary.to_u32!, pointerof(no_event), W::WEXITED, Pointer(R::Usage).null)
    closed_nonblocking = D.close(nonblocking.primary.to_i32!)
    return 121 unless refused.primary == -11 && refused.error == 11 && closed_nonblocking.error == 0
    return 60 unless Linux::Pidfd.send_signal(fd, 0).error == 0
    return 61 unless Linux::Pidfd.send_signal(fd, 0, Pointer(S::Info).null, UInt32::MAX).error == 22
    return 62 unless Linux::Pidfd.send_signal(fd, S::TERM).error == 0
    timeout = E::Timespec.new(3_i64, 0_i64)
    ready = E.ppoll(pointerof(poll), 1_u32, pointerof(timeout), Pointer(S::Set).null)
    return 63 unless ready.error == 0 && ready.primary == 1 && poll.revents & E::POLLIN != 0
    info = S::Info.new
    usage = R::Usage.new
    observed = P.waitid(W::P_PIDFD, fd.to_u32!, pointerof(info), W::WEXITED | W::WNOWAIT | W::WNOHANG, pointerof(usage))
    return 64 unless observed.error == 0 && info.pid == pid && info.code == S::CLD_KILLED && info.status == S::TERM && usage_valid(usage)
    return 65 unless collect(pid, S::TERM)
    timeout = E::Timespec.new
    gone = E.ppoll(pointerof(poll), 1_u32, pointerof(timeout), Pointer(S::Set).null)
    return 66 unless gone.error == 0 && gone.primary == 1 && poll.revents & E::POLLHUP != 0
    Linux::Pidfd.send_signal(fd, 0).error == 3 ? 0 : 67
  end

  def self.pidfd : Int32
    failed = Linux::Pidfd.open(-1)
    return 68 unless failed.error == 22 && failed.primary == -22
    return 69 unless Linux::Pidfd.send_signal(-1, 0).error == 9
    own = Linux::Pidfd.open(P.pid.primary.to_i32!)
    return 70 unless own.error == 0
    info = S::Info.new
    unrelated = P.waitid(W::P_PIDFD, own.primary.to_u32!, pointerof(info), W::WEXITED | W::WNOHANG, Pointer(R::Usage).null)
    closed = D.close(own.primary.to_i32!)
    # Having a pidfd does not turn the caller itself into its own waitable child.
    return 71 unless unrelated.error == 10 && closed.error == 0
    fds = StaticArray(Int32, 2).new(-1)
    return 72 unless D.pipe2(fds.to_unsafe, D::O_CLOEXEC | D::O_NONBLOCK).error == 0
    reader, writer = fds.to_unsafe[0], fds.to_unsafe[1]
    child = create
    if child.error != 0 || child.primary < 0 || child.primary > Int32::MAX
      D.close(reader)
      D.close(writer)
      return 73
    end
    if child.primary == 0
      D.close(writer)
      gate(reader)
      D.close(reader)
      terminate(125)
    end
    pid = child.primary.to_i32!
    D.close(reader)
    opened = Linux::Pidfd.open(pid)
    code = 74
    if opened.error == 0
      fd = opened.primary.to_i32!
      code = pidfd_body(pid, fd)
      code = 75 unless D.close(fd).error == 0
    end
    # No control fallback on failed acquisition. Close the gate; exclusive
    # owned-child cleanup is the fixture's separate failure responsibility.
    D.close(writer)
    cleaned = cleanup(pid)
    cleaned ? code : 76
  end

  def self.poll : Int32
    timeout = E::Timespec.new(0_i64, 2_000_000_i64)
    mask = S::Set.new
    result = E.ppoll(Pointer(E::Poll).null, 0_u32, pointerof(timeout), pointerof(mask))
    return 77 unless result.error == 0 && result.primary == 0 && timeout.seconds == 0 && timeout.nanoseconds == 0
    timeout = E::Timespec.new
    invalid = E.ppoll(Pointer(E::Poll).null, 0_u32, pointerof(timeout), pointerof(mask), 128_u64)
    return 78 unless invalid.error == 22 && invalid.primary == -22
    timeout = E::Timespec.new(-1_i64, 0_i64)
    invalid = E.ppoll(Pointer(E::Poll).null, 0_u32, pointerof(timeout), Pointer(S::Set).null)
    return 79 unless invalid.error == 22
    invalid_poll = E::Poll.new(0x7fffffff)
    timeout = E::Timespec.new
    observed = E.ppoll(pointerof(invalid_poll), 1_u32, pointerof(timeout), Pointer(S::Set).null)
    observed.error == 0 && observed.primary == 1 && invalid_poll.revents == E::POLLNVAL ? 0 : 80
  end
end
