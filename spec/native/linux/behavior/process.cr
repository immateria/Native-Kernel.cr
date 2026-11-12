module LinuxBehavior
  def self.group_child(reader : Int32, parent : Int32, session : Int64) : NoReturn
    code = 41
    if !gate(reader) || P.parent.primary != parent || P.getsid.primary != session || P.getpgid.primary != P.pid.primary
      code = 34
    elsif P.setpgid(0, 0).error != 0 || P.kill(0, 0).error != 0 || P.setsid.error != 1
      code = 35
    end
    D.close(reader)
    terminate(code)
  end

  def self.process : Int32
    parent = P.pid
    session = P.getsid
    group = P.getpgid
    return 36 unless parent.error == 0 && parent.primary > 0 && P.parent.primary > 0 && session.error == 0 && group.error == 0
    return 37 unless P.getsid(parent.primary.to_i32!).primary == session.primary && P.getpgid(parent.primary.to_i32!).primary == group.primary
    return 38 unless P.kill(parent.primary.to_i32!, 0).error == 0 && P.getpgid(-1).error == 3 && P.getsid(-1).error == 3
    fds = StaticArray(Int32, 2).new(-1)
    return 39 unless D.pipe2(fds.to_unsafe, D::O_CLOEXEC | D::O_NONBLOCK).error == 0
    reader, writer = fds.to_unsafe[0], fds.to_unsafe[1]
    child = create
    if child.error != 0 || child.primary < 0 || child.primary > Int32::MAX
      D.close(reader)
      D.close(writer)
      return 40
    end
    if child.primary == 0
      D.close(writer)
      group_child(reader, parent.primary.to_i32!, session.primary)
    end
    pid = child.primary.to_i32!
    D.close(reader)
    configured = P.setpgid(pid, pid).error == 0 && P.getpgid(pid).primary == pid && P.getsid(pid).primary == session.primary && P.kill(0_i32 &- pid, 0).error == 0
    released = release(writer)
    D.close(writer)
    collected = configured && released && collect(pid, 41 &* 256)
    cleaned = cleanup(pid)
    return 42 unless collected && cleaned

    child = create
    return 43 unless child.error == 0 && child.primary >= 0 && child.primary <= Int32::MAX
    if child.primary == 0
      own = P.pid.primary
      acquired = P.setsid
      valid = acquired.error == 0 && acquired.primary == own && P.getsid.primary == own && P.getpgid.primary == own
      valid = valid && P.setsid.error == 1 && P.setpgid(0, 0).error == 1
      terminate(valid ? 42 : 44)
    end
    pid = child.primary.to_i32!
    collected = collect(pid, 42 &* 256)
    cleaned = cleanup(pid)
    collected && cleaned ? 0 : 45
  end

  def self.signal_status : Int32
    fds = StaticArray(Int32, 2).new(-1)
    return 46 unless D.pipe2(fds.to_unsafe, D::O_CLOEXEC | D::O_NONBLOCK).error == 0
    reader, writer = fds.to_unsafe[0], fds.to_unsafe[1]
    child = create
    if child.error != 0 || child.primary < 0 || child.primary > Int32::MAX
      D.close(reader)
      D.close(writer)
      return 47
    end
    if child.primary == 0
      D.close(writer)
      gate(reader)
      D.close(reader)
      terminate(125)
    end
    pid = child.primary.to_i32!
    D.close(reader)
    code = signal_body(pid)
    D.close(writer)
    cleaned = cleanup(pid)
    cleaned ? code : 48
  end

  def self.signal_body(pid : Int32) : Int32
    info = S::Info.new
    usage = R::Usage.new
    usage.max_rss = -777_i64
    status = -777
    return 49 unless P.kill(pid, S::STOP).error == 0 && observe(pid, W::WSTOPPED, pointerof(info))
    return 50 unless info.code == S::CLD_STOPPED && info.status == S::STOP
    stopped = P.wait4(pid, pointerof(status), W::WUNTRACED | W::WNOHANG, pointerof(usage))
    return 51 unless stopped.primary == pid && status == ((S::STOP &* 256) | 0x7f) && usage_valid(usage)
    return 52 unless P.kill(pid, S::CONT).error == 0 && observe(pid, W::WCONTINUED, pointerof(info))
    return 53 unless info.code == S::CLD_CONTINUED && info.status == S::CONT
    continued = P.wait4(pid, pointerof(status), W::WCONTINUED | W::WNOHANG, pointerof(usage))
    return 54 unless continued.primary == pid && status == 0xffff && usage_valid(usage)
    return 55 unless P.kill(pid, S::KILL).error == 0 && observe(pid, W::WEXITED, pointerof(info))
    return 56 unless info.code == S::CLD_KILLED && info.status == S::KILL
    collect(pid, S::KILL) ? 0 : 57
  end
end
