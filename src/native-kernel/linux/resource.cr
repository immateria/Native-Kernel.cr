require "./raw"

module Native::Kernel::Linux::Resource
  RUSAGE_SELF     =  0
  RUSAGE_CHILDREN = -1
  RUSAGE_THREAD   =  1
  RLIMIT_NOFILE   =  7
  RLIM_INFINITY   = UInt64::MAX

  # Native LP64 __kernel_old_timeval: BOTH fields are signed 64-bit words.
  struct Timeval
    property seconds : Int64 = 0_i64
    property microseconds : Int64 = 0_i64
  end

  # Linux max_rss is KiB (1024 bytes), NOT Darwin's bytes. CPU time is seconds
  # plus microseconds. Other counters retain their kernel meaning (some unused
  # counters stay zero); this is not an arbitrary live-PID accounting snapshot.
  struct Usage
    property user : Timeval = Timeval.new
    property system : Timeval = Timeval.new
    property max_rss : Int64 = 0_i64
    property shared_memory : Int64 = 0_i64
    property data_memory : Int64 = 0_i64
    property stack_memory : Int64 = 0_i64
    property reclaims : Int64 = 0_i64
    property faults : Int64 = 0_i64
    property swaps : Int64 = 0_i64
    property input_blocks : Int64 = 0_i64
    property output_blocks : Int64 = 0_i64
    property sent : Int64 = 0_i64
    property received : Int64 = 0_i64
    property signals : Int64 = 0_i64
    property voluntary_switches : Int64 = 0_i64
    property involuntary_switches : Int64 = 0_i64
  end

  struct Limit
    property soft : UInt64 = 0_u64
    property hard : UInt64 = 0_u64
  end

  # Output is valid only on success; errors can leave partially copied bytes.
  # CHILDREN is cumulative accounting of already collected children; THREAD is
  # the calling thread, and SELF is the current process, not an external PID.
  def self.getrusage(who : Int32, usage : Usage*) : Result
    Raw.call(Number::GETRUSAGE, who.to_u64!, usage.address)
  end

  # Null new_limit is a query; null old_limit suppresses the copyout. Neither
  # pointer is retained. On error old_limit is not valid; a set may already have
  # taken effect before a copyout fault. No admission or restoration policy.
  def self.prlimit64(pid : Int32, resource : Int32, new_limit : Limit*, old_limit : Limit*) : Result
    Raw.call(Number::PRLIMIT64, pid.to_u64!, resource.to_u64!, new_limit.address, old_limit.address)
  end
end
