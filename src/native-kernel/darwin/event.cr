require "./raw"
require "./abi"

module Native::Kernel::Darwin::Event
  struct Poll
    property fd : Int32
    property events : Int16
    property revents : Int16

    def initialize(@fd, @events = 1_i16, @revents = 0_i16)
    end
  end

  struct Timeout
    @seconds : Int64
    @microseconds : Int32

    def initialize(microseconds : UInt32)
      @seconds = microseconds.unsafe_div(1_000_000_u32).to_i64
      @microseconds = microseconds.unsafe_mod(1_000_000_u32).to_i32!
    end
  end

  def self.queue : Result
    Raw.call(362)
  end

  def self.wait(fd : Int32, changes : Kevent64*, count : Int32, events : Kevent64*, capacity : Int32,
                flags : UInt32, timeout : Void*) : Result
    Raw.call(369, fd.to_u64!, changes.address, count.to_u64!, events.address, capacity.to_u64!, flags.to_u64, timeout.address)
  end

  def self.poll(events : Poll*, count : UInt32, milliseconds : Int32) : Result
    Raw.call(230, events.address, count.to_u64, milliseconds.to_u64!)
  end

  def self.sleep(microseconds : UInt32) : Result
    timeout = Timeout.new(microseconds)
    Raw.call(93, 0_u64, 0_u64, 0_u64, 0_u64, pointerof(timeout).address)
  end
end
