require "../raw"
require "../resource/usage"
require "../signal/info"

module Native::Kernel::Darwin::Process
  module Wait
    P_ALL  = 0
    P_PID  = 1
    P_PGID = 2

    WNOHANG    = 0x01
    WUNTRACED  = 0x02
    WEXITED    = 0x04
    WSTOPPED   = 0x08
    WCONTINUED = 0x10
    WNOWAIT    = 0x20
  end

  # Usage is filled only for a successfully collected terminal event. A stop,
  # continuation or WNOHANG/no-event leaves usage untouched. On error, either
  # buffer may have been partially written; neither is a successful result.
  def self.wait4(pid : Int32, status : Int32*, options : Int32, usage : Resource::Usage*) : Result
    Raw.call(7, pid.to_u64!, status.address, options.to_u64!, usage.address)
  end

  # Darwin leaves info untouched on WNOHANG/no-event. Before every call, callers
  # must clear info.pid, then require error zero and a nonzero pid for an event.
  # WNOWAIT observes without reaping; it does not grant collection ownership.
  def self.waitid(type : Int32, id : UInt32, info : Signal::Info*, options : Int32) : Result
    Raw.call(173, type.to_u64!, id.to_u64, info.address, options.to_u64!)
  end
end
