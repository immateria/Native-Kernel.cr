module LinuxBehavior
  def self.resource : Int32
    usage = R::Usage.new
    return 103 unless R.getrusage(R::RUSAGE_SELF, pointerof(usage)).error == 0 && usage_valid(usage)
    return 104 unless R.getrusage(R::RUSAGE_CHILDREN, pointerof(usage)).error == 0 && usage_valid(usage)
    return 105 unless R.getrusage(R::RUSAGE_THREAD, pointerof(usage)).error == 0 && usage_valid(usage)
    usage.max_rss = -777_i64
    invalid = R.getrusage(2, pointerof(usage))
    return 106 unless invalid.primary == -22 && invalid.error == 22
    return 107 unless R.getrusage(R::RUSAGE_SELF, Pointer(R::Usage).new(1_u64)).error == 14
    original = R::Limit.new
    queried = R.prlimit64(0, R::RLIMIT_NOFILE, Pointer(R::Limit).null, pointerof(original))
    return 108 unless queried.error == 0 && original.hard >= original.soft && original.soft > 0
    return 109 unless R.prlimit64(P.pid.primary.to_i32!, R::RLIMIT_NOFILE, Pointer(R::Limit).null, Pointer(R::Limit).null).error == 0
    return 110 unless R.prlimit64(0, -1, Pointer(R::Limit).null, Pointer(R::Limit).null).error == 22
    return 111 unless R.prlimit64(0, R::RLIMIT_NOFILE, Pointer(R::Limit).null, Pointer(R::Limit).new(1_u64)).error == 14
    lowered = original
    lowered.soft = 0_u64
    previous = R::Limit.new
    changed = R.prlimit64(0, R::RLIMIT_NOFILE, pointerof(lowered), pointerof(previous))
    if changed.error != 0
      restored = R.prlimit64(0, R::RLIMIT_NOFILE, pointerof(original), Pointer(R::Limit).null)
      return restored.error == 0 ? 112 : 122
    end
    fds = StaticArray(Int32, 2).new(-777)
    failed = D.pipe2(fds.to_unsafe, D::O_CLOEXEC)
    # Restore in this disposable unmanaged worker before returning on failures.
    restored = R.prlimit64(0, R::RLIMIT_NOFILE, pointerof(original), Pointer(R::Limit).null)
    if failed.error == 0
      D.close(fds.to_unsafe[0])
      D.close(fds.to_unsafe[1])
    end
    return 113 unless failed.error == 24 && failed.primary == -24 && restored.error == 0
    return 114 unless previous.soft == original.soft && previous.hard == original.hard
    check = R::Limit.new
    verified = R.prlimit64(0, R::RLIMIT_NOFILE, Pointer(R::Limit).null, pointerof(check))
    return 115 unless verified.error == 0 && check.soft == original.soft && check.hard == original.hard
    # A new limit takes effect BEFORE old-limit copyout fails; error is not rollback.
    copyout = R.prlimit64(0, R::RLIMIT_NOFILE, pointerof(lowered), Pointer(R::Limit).new(1_u64))
    observed = R.prlimit64(0, R::RLIMIT_NOFILE, Pointer(R::Limit).null, pointerof(check))
    restored = R.prlimit64(0, R::RLIMIT_NOFILE, pointerof(original), Pointer(R::Limit).null)
    copyout.primary == -14 && copyout.error == 14 && observed.error == 0 && check.soft == 0 && check.hard == original.hard && restored.error == 0 ? 0 : 123
  end

  def self.fd_count : Int32
    count = 0
    fd = 0
    while fd < 128
      result = D.fcntl(fd, D::F_GETFD)
      return -1 unless result.error == 0 || result.error == 9
      count &+= 1 if result.error == 0
      fd &+= 1
    end
    count
  end

  def self.leaks : Int32
    before = fd_count
    return 116 unless before == 3 && no_children
    attempt = 0
    while attempt < 16
      result = descriptor
      return result unless result == 0
      result = collection
      return result unless result == 0
      result = pidfd
      return result unless result == 0
      return 117 unless fd_count == before && no_children
      attempt &+= 1
    end
    0
  end
end
