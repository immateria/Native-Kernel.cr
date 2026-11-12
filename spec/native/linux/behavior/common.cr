module LinuxBehavior
  alias Linux = Native::Kernel::Linux
  alias D = Linux::Descriptor
  alias P = Linux::Process
  alias E = Linux::Event
  alias S = Linux::Signal
  alias R = Linux::Resource
  alias W = P::Wait

  def self.equal(left : UInt8*, right : UInt8*) : Bool
    index = 0
    while index < 1024
      return false if left[index] != right[index]
      return true if left[index] == 0
      index &+= 1
    end
    false
  end

  def self.entry(argc : Int32, argv : UInt8**, stack : UInt64*, call_stack : UInt64) : Bool
    return false unless argc == 4 && stack.value == 4 && argv.address == stack.address &+ 8
    return false unless stack.address & 15 == 0 && call_stack & 15 == 0 && argv[argc].null?
    return false unless equal(argv[2], "ELF-argument".to_unsafe)
    environment = argv + (argc &+ 1)
    index = 0
    while index < 256 && !environment[index].null?
      return true if equal(environment[index], "NK_ELF_PROOF=stack-arguments".to_unsafe)
      index &+= 1
    end
    false
  end

  def self.success(name : UInt8*) : Int32
    length = 0
    while length < 32 && name[length] != 0
      length &+= 1
    end
    return 90 if length == 0 || length == 32
    first = D.write(1, "NK_OK linux ".to_unsafe, 12_u64)
    second = D.write(1, name, length.to_u64!)
    third = D.write(1, "\n".to_unsafe, 1_u64)
    first.primary == 12 && second.primary == length && third.primary == 1 ? 0 : 91
  end

  # Disposable fixture termination only. If exit is sandbox-denied the external
  # driver deadline kills this worker; production exit_group itself never retries.
  def self.terminate(code : Int32) : NoReturn
    loop do
      P.exit_group(code)
    end
  end

  # Fixture-only fork-like clone: no CLONE_VM, no managed Crystal fork/launch API.
  # All non-flag slots are zero on both architectures. Never control primary
  # unless error == 0 and primary > 0. Child/parent each own their own stack.
  def self.create : Linux::Result
    Linux::Raw.call(Linux::Number::CLONE, S::CHLD.to_u64!)
  end

  def self.pause : Nil
    timeout = E::Timespec.new(0_i64, 1_000_000_i64)
    E.ppoll(Pointer(E::Poll).null, 0_u32, pointerof(timeout), Pointer(S::Set).null)
  end

  def self.gate(fd : Int32) : Bool
    poll = E::Poll.new(fd)
    timeout = E::Timespec.new(3_i64, 0_i64)
    ready = E.ppoll(pointerof(poll), 1_u32, pointerof(timeout), Pointer(S::Set).null)
    return false unless ready.error == 0 && ready.primary == 1 && poll.revents & E::POLLIN != 0
    byte = 0_u8
    got = D.read(fd, pointerof(byte), 1_u64)
    got.error == 0 && got.primary == 1 && byte == 71
  end

  def self.release(fd : Int32) : Bool
    byte = 71_u8
    sent = D.write(fd, pointerof(byte), 1_u64)
    sent.error == 0 && sent.primary == 1
  end

  def self.usage_valid(usage : R::Usage) : Bool
    usage.user.seconds >= 0 && usage.system.seconds >= 0 &&
      usage.user.microseconds >= 0 && usage.user.microseconds < 1_000_000 &&
      usage.system.microseconds >= 0 && usage.system.microseconds < 1_000_000 && usage.max_rss >= 0
  end

  # Single, exclusive collector, bounded both locally and by the Python driver.
  def self.collect(pid : Int32, expected : Int32) : Bool
    attempt = 0
    status = -777
    usage = R::Usage.new
    while attempt < 3000
      result = P.wait4(pid, pointerof(status), W::WNOHANG, pointerof(usage))
      return status == expected && usage_valid(usage) if result.error == 0 && result.primary == pid
      return false unless result.error == 4 || (result.error == 0 && result.primary == 0)
      pause
      attempt &+= 1
    end
    false
  end

  # A copyout failure can FOLLOW collection. Check waitability before any kill;
  # ECHILD means no PID control, even on a test failure. No other collector runs.
  # Numeric termination here is cleanup of an exclusively owned child, NOT a
  # fallback for a failed pidfd acquisition or denied control operation.
  def self.cleanup(pid : Int32) : Bool
    return false unless pid > 0
    attempt = 0
    status = 0
    signaled = false
    while attempt < 3000
      result = P.wait4(pid, pointerof(status), W::WNOHANG, Pointer(R::Usage).null)
      return true if result.error == 10 || (result.error == 0 && result.primary == pid)
      return false unless result.error == 4 || (result.error == 0 && result.primary == 0)
      if result.error == 0 && !signaled
        signaled = P.kill(pid, S::KILL).error == 0
      end
      pause
      attempt &+= 1
    end
    false
  end

  def self.observe(pid : Int32, flags : Int32, info : S::Info*, usage : R::Usage* = Pointer(R::Usage).null) : Bool
    attempt = 0
    while attempt < 3000
      info.value.pid = 0
      result = P.waitid(W::P_PID, pid.to_u32!, info, flags | W::WNOWAIT | W::WNOHANG, usage)
      return true if result.error == 0 && info.value.pid == pid
      return false unless result.error == 0 || result.error == 4
      pause
      attempt &+= 1
    end
    false
  end

  def self.no_children : Bool
    status = 0
    result = P.wait4(-1, pointerof(status), W::WNOHANG, Pointer(R::Usage).null)
    result.primary == -10 && result.error == 10
  end
end
