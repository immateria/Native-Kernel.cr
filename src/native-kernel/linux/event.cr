require "./raw"
require "./signal"

module Native::Kernel::Linux::Event
  POLLIN   = 0x01_i16
  POLLOUT  = 0x04_i16
  POLLERR  = 0x08_i16
  POLLHUP  = 0x10_i16
  POLLNVAL = 0x20_i16

  struct Poll
    property fd : Int32
    property events : Int16
    property revents : Int16 = 0_i16

    def initialize(@fd = -1, @events = POLLIN)
    end
  end

  struct Timespec
    property seconds : Int64
    property nanoseconds : Int64

    def initialize(@seconds = 0_i64, @nanoseconds = 0_i64)
    end
  end

  # Raw ppoll: timeout is caller-owned and MAY BE MODIFIED to remaining time,
  # including on interruption. There is no timeout copy or retry. Reinitialize
  # it before reuse. A null timeout waits indefinitely. The temporary signal
  # mask, if nonnull, must use the 8-byte kernel Set, not libc's signal set.
  # nfds is the kernel's unsigned int slot; output revents is valid on success
  # only. On failure neither timeout nor revents is a successful observation.
  def self.ppoll(fds : Poll*, nfds : UInt32, timeout : Timespec*,
                 mask : Signal::Set*, mask_bytes : UInt64 = Signal::SET_BYTES) : Result
    Raw.call(Number::PPOLL, fds.address, nfds.to_u64, timeout.address, mask.address, mask_bytes)
  end
end
