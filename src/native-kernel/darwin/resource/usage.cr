module Native::Kernel::Darwin::Resource
  RUSAGE_SELF     =  0
  RUSAGE_CHILDREN = -1

  # Native64 timeval: the final word is padding, not fractional time.
  struct Time
    property seconds : Int64 = 0_i64
    property microseconds : Int32 = 0
    @reserved : Int32 = 0
  end

  # Native64 rusage. CPU time is seconds plus microseconds; max_rss is bytes.
  # Other counters retain their native, implementation-defined meaning.
  struct Usage
    property user : Time = Time.new
    property system : Time = Time.new
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
end
