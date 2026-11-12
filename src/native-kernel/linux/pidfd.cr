require "./raw"
require "./signal"

module Native::Kernel::Linux::Pidfd
  NONBLOCK = 0x00800_u32

  # Success acquires a CLOEXEC descriptor in primary; the caller owns its close.
  # Failure acquires nothing. No feature, permission or acquisition failure
  # ever falls back to PID-only control, and no capability is cached here.
  def self.open(pid : Int32, flags : UInt32 = 0_u32) : Result
    Raw.call(Number::PIDFD_OPEN, pid.to_u64!, flags.to_u64)
  end

  # info is null or caller-owned native siginfo storage, never a libc binding.
  # Readiness of a pidfd is observation, not exclusive child-collection rights.
  def self.send_signal(fd : Int32, number : Int32, info : Signal::Info* = Pointer(Signal::Info).null,
                       flags : UInt32 = 0_u32) : Result
    Raw.call(Number::PIDFD_SEND_SIGNAL, fd.to_u64!, number.to_u64!, info.address, flags.to_u64)
  end
end
