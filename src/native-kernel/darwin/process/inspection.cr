require "../raw"
require "../abi"

module Native::Kernel::Darwin::Process
  lib Info
    PGRP_ONLY = 2_u32
    PPID_ONLY = 6_u32

    PIDTASKALLINFO = 2
    PIDTBSDINFO    = 3
    PIDTASKINFO    = 4

    PIF_COMPARE_IDVERSION = 0x01_u32
    PIF_COMPARE_UNIQUEID  = 0x02_u32

    # proc_taskinfo. CPU fields retain Mach absolute-time ticks, not ns.
    struct Task
      virtual_size : UInt64
      resident_size : UInt64
      total_user : UInt64
      total_system : UInt64
      threads_user : UInt64
      threads_system : UInt64
      policy : Int32
      faults : Int32
      pageins : Int32
      cow_faults : Int32
      sent : Int32
      received : Int32
      mach_calls : Int32
      unix_calls : Int32
      switches : Int32
      threads : Int32
      running : Int32
      priority : Int32
    end

    struct All
      bsd : Bsd
      task : Task
    end
  end

  # Explicit rusage_info prefixes. No CURRENT alias or implicit version upgrade.
  # CPU/start/exit/elapsed times retain Mach absolute-time ticks; sizes and I/O
  # are bytes. These PID-keyed snapshots do not compare a process incarnation.
  lib Usage
    struct V0
      uuid : UInt8[16]
      user_time : UInt64
      system_time : UInt64
      idle_wakeups : UInt64
      interrupt_wakeups : UInt64
      pageins : UInt64
      wired_size : UInt64
      resident_size : UInt64
      footprint : UInt64
      start : UInt64
      exit : UInt64
    end

    struct V1
      uuid : UInt8[16]
      user_time : UInt64
      system_time : UInt64
      idle_wakeups : UInt64
      interrupt_wakeups : UInt64
      pageins : UInt64
      wired_size : UInt64
      resident_size : UInt64
      footprint : UInt64
      start : UInt64
      exit : UInt64
      child_user_time : UInt64
      child_system_time : UInt64
      child_idle_wakeups : UInt64
      child_interrupt_wakeups : UInt64
      child_pageins : UInt64
      child_elapsed : UInt64
    end

    struct V2
      uuid : UInt8[16]
      user_time : UInt64
      system_time : UInt64
      idle_wakeups : UInt64
      interrupt_wakeups : UInt64
      pageins : UInt64
      wired_size : UInt64
      resident_size : UInt64
      footprint : UInt64
      start : UInt64
      exit : UInt64
      child_user_time : UInt64
      child_system_time : UInt64
      child_idle_wakeups : UInt64
      child_interrupt_wakeups : UInt64
      child_pageins : UInt64
      child_elapsed : UInt64
      read_bytes : UInt64
      written_bytes : UInt64
    end
  end

  # Native result is a byte count, including for filtered queries. A null buffer
  # reports an advisory all-process capacity, not a stable filtered count.
  def self.list(type : UInt32, filter : UInt32, buffer : Void*, size : Int32) : Result
    Raw.call(336, 1_u64, type.to_u64, filter.to_u64, 0_u64, buffer.address, size.to_u64!)
  end

  # Slot 545 with PIDINFO only. Both comparison flags together produce EINVAL;
  # a mismatched selected identity produces ESRCH before record copyout.
  def self.info(pid : Int32, flavor : Int32, argument : UInt64, buffer : Void*, size : Int32, flags : UInt32, identity : UInt64) : Result
    Raw.call(545, 2_u64, pid.to_u64!, flavor.to_u64!, flags.to_u64, identity, argument, buffer.address, size.to_u64!)
  end

  def self.info(pid : Int32, buffer : Info::Bsd*) : Result
    info(pid, Info::PIDTBSDINFO, 0_u64, buffer.as(Void*), sizeof(Info::Bsd))
  end

  def self.info(pid : Int32, buffer : Info::Bsd*, flags : UInt32, identity : UInt64) : Result
    info(pid, Info::PIDTBSDINFO, 0_u64, buffer.as(Void*), sizeof(Info::Bsd), flags, identity)
  end

  def self.info(pid : Int32, buffer : Info::Task*) : Result
    info(pid, Info::PIDTASKINFO, 0_u64, buffer.as(Void*), sizeof(Info::Task))
  end

  def self.info(pid : Int32, buffer : Info::Task*, flags : UInt32, identity : UInt64) : Result
    info(pid, Info::PIDTASKINFO, 0_u64, buffer.as(Void*), sizeof(Info::Task), flags, identity)
  end

  def self.info(pid : Int32, buffer : Info::All*) : Result
    info(pid, Info::PIDTASKALLINFO, 0_u64, buffer.as(Void*), sizeof(Info::All))
  end

  def self.info(pid : Int32, buffer : Info::All*, flags : UInt32, identity : UInt64) : Result
    info(pid, Info::PIDTASKALLINFO, 0_u64, buffer.as(Void*), sizeof(Info::All), flags, identity)
  end

  # PIDRUSAGE uses its version's fixed copy size; it returns zero, not a length.
  def self.usage(pid : Int32, buffer : Usage::V0*) : Result
    Raw.call(336, 9_u64, pid.to_u64!, 0_u64, 0_u64, buffer.address, 0_u64)
  end

  # PIDRUSAGE uses its version's fixed copy size; it returns zero, not a length.
  def self.usage(pid : Int32, buffer : Usage::V1*) : Result
    Raw.call(336, 9_u64, pid.to_u64!, 1_u64, 0_u64, buffer.address, 0_u64)
  end

  # PIDRUSAGE uses its version's fixed copy size; it returns zero, not a length.
  def self.usage(pid : Int32, buffer : Usage::V2*) : Result
    Raw.call(336, 9_u64, pid.to_u64!, 2_u64, 0_u64, buffer.address, 0_u64)
  end
end
