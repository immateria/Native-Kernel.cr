require "./raw"
require "./signal"
require "./resource"

module Native::Kernel::Linux::Process
  module Wait
    P_ALL   = 0
    P_PID   = 1
    P_PGID  = 2
    P_PIDFD = 3

    WNOHANG    = 0x00000001
    WUNTRACED  = 0x00000002
    WSTOPPED   = 0x00000002
    WEXITED    = 0x00000004
    WCONTINUED = 0x00000008
    WNOWAIT    = 0x01000000
  end

  def self.pid : Result
    Raw.call(Number::GETPID)
  end

  def self.parent : Result
    Raw.call(Number::GETPPID)
  end

  def self.getpgid(pid : Int32 = 0) : Result
    Raw.call(Number::GETPGID, pid.to_u64!)
  end

  def self.setpgid(pid : Int32, group : Int32) : Result
    Raw.call(Number::SETPGID, pid.to_u64!, group.to_u64!)
  end

  def self.getsid(pid : Int32 = 0) : Result
    Raw.call(Number::GETSID, pid.to_u64!)
  end

  def self.setsid : Result
    Raw.call(Number::SETSID)
  end

  # Numeric kernel mechanism: positive, zero and negative PID/group selectors
  # retain Linux semantics. This does not establish PID identity or authority.
  def self.kill(pid : Int32, number : Int32) : Result
    Raw.call(Number::KILL, pid.to_u64!, number.to_u64!)
  end

  # Normally never returns. A sandbox can reject exit; expose that raw error
  # rather than embedding a retry/fallback policy or managed shutdown here.
  def self.exit_group(code : Int32) : Result
    Raw.call(Number::EXIT_GROUP, code.to_u64!)
  end

  # A positive result supplies status and optional usage for that event (also
  # stop/continue on Linux). Zero/WNOHANG supplies neither. On error no output
  # is valid, and EFAULT MAY FOLLOW REAPING: an error does not prove the child
  # remains waitable. Only the caller's exclusive collector should use this.
  def self.wait4(pid : Int32, status : Int32*, options : Int32, usage : Resource::Usage*) : Result
    Raw.call(Number::WAIT4, pid.to_u64!, status.address, options.to_u64!, usage.address)
  end

  # Raw Linux has a FIFTH rusage pointer. Clear info.pid before each call and
  # require error == 0 && info.pid != 0 for an event. No-event leaves usage
  # untouched; do not read it. Only the documented SIGCHLD fields are copied.
  # WNOWAIT observes without collecting. P_PIDFD does not grant permission to
  # reap a non-child. Errors may follow collection and/or partial output.
  def self.waitid(type : Int32, id : UInt32, info : Signal::Info*, options : Int32,
                  usage : Resource::Usage*) : Result
    Raw.call(Number::WAITID, type.to_u64!, id.to_u64, info.address, options.to_u64!, usage.address)
  end
end
