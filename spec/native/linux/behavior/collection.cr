module LinuxBehavior
  def self.collection_body(pid : Int32, writer : Int32) : Int32
    status = -777
    usage = R::Usage.new
    usage.max_rss = -777_i64
    empty = P.wait4(pid, pointerof(status), W::WNOHANG, pointerof(usage))
    return 81 unless empty.error == 0 && empty.primary == 0 && status == -777 && usage.max_rss == -777
    info = S::Info.new
    info.number = -777
    empty = P.waitid(W::P_PID, pid.to_u32!, pointerof(info), W::WEXITED | W::WNOHANG, pointerof(usage))
    return 82 unless empty.error == 0 && empty.primary == 0 && info.pid == 0 && info.number == 0 && usage.max_rss == -777
    # Only the explicit SIGCHLD fields are copyouts; the tail is not accounting.
    pointerof(info).as(UInt64*)[4] = UInt64::MAX
    return 83 unless release(writer) && observe(pid, W::WEXITED, pointerof(info), pointerof(usage))
    return 84 unless info.number == S::CHLD && info.error == 0 && info.code == S::CLD_EXITED && info.status == 37 && usage_valid(usage)
    return 85 unless pointerof(info).as(UInt64*)[4] == UInt64::MAX
    usage.max_rss = -777_i64
    info.pid = 0
    again = P.waitid(W::P_PID, pid.to_u32!, pointerof(info), W::WEXITED | W::WNOWAIT | W::WNOHANG, pointerof(usage))
    return 86 unless again.error == 0 && info.pid == pid && info.status == 37 && usage_valid(usage)
    info.pid = 0
    usage.max_rss = -777_i64
    collected = P.waitid(W::P_PID, pid.to_u32!, pointerof(info), W::WEXITED | W::WNOHANG, pointerof(usage))
    return 87 unless collected.error == 0 && info.pid == pid && info.code == S::CLD_EXITED && info.status == 37 && usage_valid(usage)
    duplicate = P.wait4(pid, pointerof(status), W::WNOHANG, pointerof(usage))
    duplicate.error == 10 && duplicate.primary == -10 ? 0 : 88
  end

  def self.collection : Int32
    fds = StaticArray(Int32, 2).new(-1)
    return 92 unless D.pipe2(fds.to_unsafe, D::O_CLOEXEC | D::O_NONBLOCK).error == 0
    reader, writer = fds.to_unsafe[0], fds.to_unsafe[1]
    child = create
    if child.error != 0 || child.primary < 0 || child.primary > Int32::MAX
      D.close(reader)
      D.close(writer)
      return 93
    end
    if child.primary == 0
      D.close(writer)
      ready = gate(reader)
      D.close(reader)
      count = 0
      while count < 5000
        P.pid
        count &+= 1
      end
      terminate(ready ? 37 : 125)
    end
    pid = child.primary.to_i32!
    D.close(reader)
    code = collection_body(pid, writer)
    D.close(writer)
    cleaned = cleanup(pid)
    cleaned ? code : 94
  end

  def self.copyout_child(kind : Int32) : Int32
    child = create
    return 95 unless child.error == 0 && child.primary >= 0 && child.primary <= Int32::MAX
    terminate(37) if child.primary == 0
    pid = child.primary.to_i32!
    info = S::Info.new
    code = 96
    if observe(pid, W::WEXITED, pointerof(info))
      code = copyout_body(pid, kind)
    end
    cleaned = cleanup(pid)
    cleaned ? code : 97
  end

  def self.copyout_body(pid : Int32, kind : Int32) : Int32
    info = S::Info.new
    status = -777
    usage = R::Usage.new
    if kind == 0
      # Linux reaps BEFORE attempting the rusage copyout (unlike Darwin).
      failed = P.wait4(pid, pointerof(status), W::WNOHANG, Pointer(R::Usage).new(1_u64))
      return 98 unless failed.error == 14 && failed.primary == -14
    elsif kind == 1
      failed = P.waitid(W::P_PID, pid.to_u32!, pointerof(info), W::WEXITED | W::WNOWAIT | W::WNOHANG, Pointer(R::Usage).new(1_u64))
      return 99 unless failed.error == 14 && failed.primary == -14
      # WNOWAIT, even with copyout fault, did not consume the terminal status.
      return 100 unless collect(pid, 37 &* 256)
    else
      failed = P.waitid(W::P_PID, pid.to_u32!, Pointer(S::Info).new(1_u64), W::WEXITED | W::WNOHANG, pointerof(usage))
      return 101 unless failed.error == 14 && failed.primary == -14
    end
    duplicate = P.wait4(pid, pointerof(status), W::WNOHANG, pointerof(usage))
    duplicate.error == 10 ? 0 : 102
  end

  def self.copyout : Int32
    kind = 0
    while kind < 3
      result = copyout_child(kind)
      return result unless result == 0
      kind &+= 1
    end
    0
  end
end
