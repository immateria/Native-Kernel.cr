# Darwin 21 private-spawn proof. Build with -Dwithout_main.
# Parent -> at most one syscall-created target child; the parent is the sole
# collector for a confirmed successful creation and has bounded termination.
require "../../src/native-kernel/darwin"

module MontereySpawn
  alias Darwin = Native::Kernel::Darwin

  enum Rejection
    Expected
    UnexpectedSuccessCollected
    Failed
  end

  def self.equal(left : UInt8*, right : UInt8*) : Bool
    offset = 0
    while offset < 64
      return false unless left[offset] == right[offset]
      return true if left[offset] == 0
      offset &+= 1
    end
    false
  end

  @[NoInline]
  def self.zero_byte(destination : UInt8*) : Nil
    destination.value = 0_u8
  end

  def self.zero(destination : UInt8*, size : Int32) : Nil
    offset = 0
    while offset < size
      zero_byte(destination + offset)
      offset &+= 1
    end
  end

  def self.copy(source : UInt8*, destination : UInt8*, capacity : Int32) : Bool
    offset = 0
    while offset < capacity
      byte = source[offset]
      destination[offset] = byte
      return true if byte == 0
      offset &+= 1
    end
    false
  end

  def self.decimal(value : Int32, destination : UInt8*) : Int32
    return -1 if value < 0
    if value == 0
      destination[0] = 48_u8
      destination[1] = 0_u8
      return 1
    end
    digits = uninitialized UInt8[10]
    count = 0
    number = value
    while number > 0
      digits.to_unsafe[count] = (number.unsafe_mod(10) &+ 48).to_u8!
      number = number.unsafe_div(10)
      count &+= 1
    end
    offset = 0
    while offset < count
      destination[offset] = digits.to_unsafe[count &- offset &- 1]
      offset &+= 1
    end
    destination[count] = 0_u8
    count
  end

  # The parent is the only collector. A forced cleanup treats any observed exit
  # as collected; a normal success still requires the exact target status.
  def self.collect(pid : Int32, expected : Int32, terminate : Bool, accept_any_exit : Bool = false) : Bool
    status = 0
    attempt = 0
    while attempt < 2000
      result = Darwin::Process.waitpid(pid, pointerof(status), 1) # WNOHANG
      return result.error == 0 && (accept_any_exit || status == expected) if result.primary == pid
      return false unless result.error == 0 || result.error == 4
      if terminate && result.error == 0 && result.primary == 0
        Darwin::Signal.kill(pid, 9)
        terminate = false
      end
      Darwin::Event.sleep(1000_u32)
      attempt &+= 1
    end
    Darwin::Signal.kill(pid, 9)
    attempt = 0
    while attempt < 2000
      result = Darwin::Process.waitpid(pid, pointerof(status), 1)
      return result.error == 0 && accept_any_exit if result.primary == pid
      return false unless result.error == 0 || result.error == 4
      Darwin::Event.sleep(1000_u32)
      attempt &+= 1
    end
    false
  end

  def self.output(fd : Int32) : Bool
    bytes = uninitialized UInt8[13]
    size = 0
    attempt = 0
    while attempt < 100
      event = Darwin::Event::Poll.new(fd)
      ready = Darwin::Event.poll(pointerof(event), 1_u32, 50)
      return false unless ready.error == 0 || ready.error == 4
      if ready.error == 0 && ready.primary == 1
        read = Darwin::Descriptor.read(fd, bytes.to_unsafe + size, (13 &- size).to_u64!)
        return false unless read.error == 0 || read.error == 4
        if read.error == 0
          if read.primary == 0
            return false unless size == 12
            bytes.to_unsafe[12] = 0_u8
            return equal(bytes.to_unsafe, "NK_SPAWN_OK\n".to_unsafe)
          end
          return false unless read.primary > 0 && read.primary < (13 &- size)
          size &+= read.primary.to_i32!
        end
      end
      attempt &+= 1
    end
    false
  end

  def self.profile : Darwin::Spawn::Profile?
    profile = Darwin::Spawn.profile(Darwin::Process.release)
    return nil unless profile && profile.layout == Darwin::Spawn::Layout::Darwin21
    return nil unless profile.attributes_size == 152 && profile.fixed_attribute_copy_size == 152 &&
                      profile.descriptor_size == 128 && profile.actions_header_size == 8 &&
                      profile.action_size == 1040 && profile.path_capacity == 1024
    profile
  end

  def self.empty_descriptor(profile : Darwin::Spawn::Profile, descriptor : UInt8*) : Nil
    # The local allocation remains the largest audited profile, but Darwin 21
    # reads exactly its native 128-byte descriptor prefix.
    zero(descriptor, profile.descriptor_size)
  end

  # Only a successful create plus a positive PID grants collection ownership.
  # A rejection regression must clean up that child while remaining a failure.
  # A PID copied out alongside an error can already have been reaped by XNU;
  # it is evidence of the activation path, never a control/collection input.
  def self.check_rejection(result : Darwin::Result, child : Int32, expected_error : Int32,
                           expected_child : Int32, activation : Bool = false) : Rejection
    if result.error == 0 && child > 0
      return collect(child, 0, true, true) ? Rejection::UnexpectedSuccessCollected : Rejection::Failed
    end
    return Rejection::Failed unless result.primary == -1 && result.error == expected_error
    expected_pid = activation ? child > 0 : child == expected_child
    expected_pid ? Rejection::Expected : Rejection::Failed
  end

  def self.rejected_null_arguments : Int32
    child = 0
    rejected = Darwin::Spawn.create(pointerof(child), Pointer(UInt8).null, Pointer(Void).null,
      Pointer(Pointer(UInt8)).null, Pointer(Pointer(UInt8)).null)
    # Darwin 21 rejects the null pathname during activation, after fork. XNU
    # copies out a positive PID and internally reaps it before returning EFAULT;
    # this error-result PID never grants caller collection ownership.
    check_rejection(rejected, child, 14, 0, true) == Rejection::Expected ? 0 : 3
  end

  # The descriptor's file_actions_size and the copied action count/size are
  # independently rejected before fork in the audited Darwin 21 copyin path.
  # Their sentinel PID storage remains untouched; no ambiguous creation is
  # retried or collected.
  def self.malformed_actions(target : UInt8*, count_mismatch : Bool) : Int32
    profile = self.profile
    return 20 unless profile
    descriptor = uninitialized UInt8[144]
    actions = uninitialized UInt8[1048]
    arguments = StaticArray(UInt8*, 2).new(Pointer(UInt8).null)
    environment = StaticArray(UInt8*, 1).new(Pointer(UInt8).null)
    arguments.to_unsafe[0] = target

    empty_descriptor(profile, descriptor.to_unsafe)
    zero(actions.to_unsafe, 1048)
    (actions.to_unsafe + profile.actions_capacity_offset).as(Int32*).value = 1
    (actions.to_unsafe + profile.actions_count_offset).as(Int32*).value = 1
    (descriptor.to_unsafe + profile.descriptor_actions_offset).as(UInt64*).value = actions.to_unsafe.address
    if count_mismatch
      (actions.to_unsafe + profile.actions_count_offset).as(Int32*).value = 2
      (descriptor.to_unsafe + profile.descriptor_actions_size_offset).as(UInt64*).value = 1048_u64
      child = -78
      mismatch = Darwin::Spawn.create(pointerof(child), target, descriptor.to_unsafe.as(Void*), arguments.to_unsafe, environment.to_unsafe)
      return check_rejection(mismatch, child, 22, -78) == Rejection::Expected ? 0 : 22
    end

    (descriptor.to_unsafe + profile.descriptor_actions_size_offset).as(UInt64*).value = 8_u64
    child = -77
    too_small = Darwin::Spawn.create(pointerof(child), target, descriptor.to_unsafe.as(Void*), arguments.to_unsafe, environment.to_unsafe)
    check_rejection(too_small, child, 22, -77) == Rejection::Expected ? 0 : 21
  end

  # A failed activation can have an internal spawn process which XNU reaps
  # itself. The error result never confirms caller collection ownership, so this
  # fixture deliberately does not use a returned numeric PID as recovery input.
  def self.activation_rejected(target : UInt8*, invalid_cwd : Bool) : Int32
    profile = self.profile
    return 23 unless profile
    descriptor = uninitialized UInt8[144]
    actions = uninitialized UInt8[1048]
    arguments = StaticArray(UInt8*, 2).new(Pointer(UInt8).null)
    environment = StaticArray(UInt8*, 1).new(Pointer(UInt8).null)
    arguments.to_unsafe[0] = target
    empty_descriptor(profile, descriptor.to_unsafe)

    path = target
    if invalid_cwd
      zero(actions.to_unsafe, 1048)
      (actions.to_unsafe + profile.actions_capacity_offset).as(Int32*).value = 1
      (actions.to_unsafe + profile.actions_count_offset).as(Int32*).value = 1
      action = actions.to_unsafe + profile.actions_header_size
      (action + profile.action_type_offset).as(Int32*).value = 5 # CHDIR
      return 24 unless copy("/dev/null/nk-invalid-cwd".to_unsafe, action + profile.chdir_path_offset, profile.path_capacity)
      (descriptor.to_unsafe + profile.descriptor_actions_size_offset).as(UInt64*).value = 1048_u64
      (descriptor.to_unsafe + profile.descriptor_actions_offset).as(UInt64*).value = actions.to_unsafe.address
    else
      path = "/dev/null/nk-missing-executable".to_unsafe
      arguments.to_unsafe[0] = path
    end

    child = -79
    rejected = Darwin::Spawn.create(pointerof(child), path, descriptor.to_unsafe.as(Void*), arguments.to_unsafe, environment.to_unsafe)
    # /dev/null is not a directory: both paths must reach ENOTDIR, not merely
    # any failure. The post-fork error path copies a positive PID before its
    # internal reap; an early copyin/resource rejection cannot satisfy this.
    check_rejection(rejected, child, 20, -79, true) == Rejection::Expected ? 0 : 25
  end

  # Controlled regression for a negative case that unexpectedly creates a
  # child. The ordinary exec target exits immediately with argc == 1; even if
  # it has already exited, the rejection handler must perform its sole reap.
  def self.rejection_cleanup(target : UInt8*) : Int32
    profile = self.profile
    return 48 unless profile
    descriptor = uninitialized UInt8[144]
    arguments = StaticArray(UInt8*, 2).new(Pointer(UInt8).null)
    environment = StaticArray(UInt8*, 1).new(Pointer(UInt8).null)
    arguments.to_unsafe[0] = target
    empty_descriptor(profile, descriptor.to_unsafe)

    # Error results never authorize collection, even with a positive copied
    # PID. Use this probe's own PID so a broken guard cannot target a stranger.
    own_pid = Darwin::Process.pid.primary.to_i32!
    rejected = Darwin::Result.new(-1_i64, 0_i64, 14)
    return 49 unless check_rejection(rejected, own_pid, 14, 0, true) == Rejection::Expected
    return 50 unless check_rejection(rejected, own_pid, 20, 0, true) == Rejection::Failed

    child = 0
    created = Darwin::Spawn.create(pointerof(child), target, descriptor.to_unsafe.as(Void*), arguments.to_unsafe, environment.to_unsafe)
    return 51 unless created.error == 0 && child > 0
    disposition = check_rejection(created, child, 20, -79, true)
    status = 0
    observed = Darwin::Process.waitpid(child, pointerof(status), 1)
    if observed.primary == -1 && observed.error == 10 # ECHILD proves the handler collected.
      return disposition == Rejection::UnexpectedSuccessCollected ? 0 : 52
    end
    # Preserve ownership if the controlled check itself detects a regression.
    # A successful wait already collected; zero/EINTR still permits cleanup.
    if (observed.error == 0 && observed.primary == 0) || observed.error == 4
      collect(child, 0, true, true)
    end
    53
  end

  def self.spawn_success(target : UInt8*) : Int32
    profile = self.profile
    return 26 unless profile

    attributes = uninitialized UInt8[192]
    descriptor = uninitialized UInt8[144]
    actions = uninitialized UInt8[3128]
    zero(attributes.to_unsafe, profile.attributes_size)
    zero(descriptor.to_unsafe, profile.descriptor_size)
    zero(actions.to_unsafe, 3128)
    (attributes.to_unsafe + profile.flags_offset).as(UInt16*).value = 0x400c_u16
    (attributes.to_unsafe + profile.defaults_offset).as(UInt32*).value = 0xfffefeff_u32
    (attributes.to_unsafe + profile.mask_offset).as(UInt32*).value = 0_u32
    (actions.to_unsafe + profile.actions_capacity_offset).as(Int32*).value = 3
    (actions.to_unsafe + profile.actions_count_offset).as(Int32*).value = 3

    pipe = Darwin::Descriptor.pipe
    return 27 unless pipe.error == 0
    reader, writer = pipe.primary.to_i32!, pipe.secondary.to_i32!
    unless reader >= 3 && writer >= 3
      Darwin::Descriptor.close(reader)
      Darwin::Descriptor.close(writer)
      return 27
    end

    action = actions.to_unsafe + profile.actions_header_size
    (action + profile.action_type_offset).as(Int32*).value = 2 # DUP2 writer -> stdout
    (action + profile.action_fd_offset).as(Int32*).value = writer
    (action + profile.action_destination_offset).as(Int32*).value = 1
    action += profile.action_size
    (action + profile.action_type_offset).as(Int32*).value = 1 # CLOSE reader
    (action + profile.action_fd_offset).as(Int32*).value = reader
    action += profile.action_size
    (action + profile.action_type_offset).as(Int32*).value = 5 # CHDIR /
    (action + profile.chdir_path_offset).value = 47_u8

    # profile() already validated the exact positive 152-byte copy boundary;
    # use its native conversion without introducing an unmanaged overflow path.
    (descriptor.to_unsafe + profile.descriptor_attribute_size_offset).as(UInt64*).value = profile.attributes_size.to_u64!
    (descriptor.to_unsafe + profile.descriptor_attributes_offset).as(UInt64*).value = attributes.to_unsafe.address
    (descriptor.to_unsafe + profile.descriptor_actions_size_offset).as(UInt64*).value = 3128_u64
    (descriptor.to_unsafe + profile.descriptor_actions_offset).as(UInt64*).value = actions.to_unsafe.address

    fd_text = uninitialized UInt8[12]
    return 28 unless decimal(writer, fd_text.to_unsafe) > 0
    arguments = StaticArray(UInt8*, 4).new(Pointer(UInt8).null)
    arguments.to_unsafe[0] = target
    arguments.to_unsafe[1] = "nk-spawn-proof".to_unsafe
    arguments.to_unsafe[2] = fd_text.to_unsafe
    environment = StaticArray(UInt8*, 2).new(Pointer(UInt8).null)
    environment.to_unsafe[0] = "NK_SPAWN_PROOF=1".to_unsafe

    # Install a non-default disposition/mask. This executable is the runner's
    # owned probe process and exits after the case. Do not reconstruct a prior
    # action: sigaction copyout omits sa_tramp, while a raw replacement needs it.
    ignored = Darwin::Signal::Action.new(1_u64, 0_u64, 0_u32, 0)
    installed = Darwin::Signal.action(30, pointerof(ignored))
    unless installed.error == 0
      Darwin::Descriptor.close(reader)
      Darwin::Descriptor.close(writer)
      return 29
    end
    blocked = 1_u32.unsafe_shl(29)
    masked = Darwin::Signal.mask(1, pointerof(blocked), Pointer(UInt32).null)
    unless masked.error == 0
      Darwin::Descriptor.close(reader)
      Darwin::Descriptor.close(writer)
      return 30
    end

    child = 0
    created = Darwin::Spawn.create(pointerof(child), target, descriptor.to_unsafe.as(Void*), arguments.to_unsafe, environment.to_unsafe)
    write_closed = Darwin::Descriptor.close(writer)
    if created.error != 0 || child <= 0
      read_closed = Darwin::Descriptor.close(reader)
      # No success result and positive PID pair confirms a caller-owned child.
      # The audited kernel error path performs its own reap; never guess/retry.
      return write_closed.error == 0 && read_closed.error == 0 ? 31 : 32
    end

    received = write_closed.error == 0 && output(reader)
    read_closed = Darwin::Descriptor.close(reader)
    collected = collect(child, 37 &* 256, !received)
    received && read_closed.error == 0 && collected ? 0 : 33
  end

  def self.finish(which : UInt8*) : Int32
    if equal(which, "spawn-success".to_unsafe)
      completed = Darwin::Descriptor.write(1, "NK_OK spawn-success\n".to_unsafe, 20_u64)
      return completed.error == 0 && completed.primary == 20 ? 0 : 40
    elsif equal(which, "spawn-null-arguments".to_unsafe)
      completed = Darwin::Descriptor.write(1, "NK_OK spawn-null-arguments\n".to_unsafe, 27_u64)
      return completed.error == 0 && completed.primary == 27 ? 0 : 41
    elsif equal(which, "spawn-malformed-descriptor-size".to_unsafe)
      completed = Darwin::Descriptor.write(1, "NK_OK spawn-malformed-descriptor-size\n".to_unsafe, 38_u64)
      return completed.error == 0 && completed.primary == 38 ? 0 : 42
    elsif equal(which, "spawn-malformed-action-size".to_unsafe)
      completed = Darwin::Descriptor.write(1, "NK_OK spawn-malformed-action-size\n".to_unsafe, 34_u64)
      return completed.error == 0 && completed.primary == 34 ? 0 : 43
    elsif equal(which, "spawn-invalid-cwd".to_unsafe)
      completed = Darwin::Descriptor.write(1, "NK_OK spawn-invalid-cwd\n".to_unsafe, 24_u64)
      return completed.error == 0 && completed.primary == 24 ? 0 : 44
    elsif equal(which, "spawn-missing-executable".to_unsafe)
      completed = Darwin::Descriptor.write(1, "NK_OK spawn-missing-executable\n".to_unsafe, 31_u64)
      return completed.error == 0 && completed.primary == 31 ? 0 : 45
    elsif equal(which, "spawn-rejection-cleanup".to_unsafe)
      completed = Darwin::Descriptor.write(1, "NK_OK spawn-rejection-cleanup\n".to_unsafe, 30_u64)
      return completed.error == 0 && completed.primary == 30 ? 0 : 54
    end
    46
  end

  def self.run(argc : Int32, argv : UInt8**) : Int32
    return 2 unless argc == 3 && !argv[1].null? && !argv[2].null?
    target, which = argv[1], argv[2]
    result = if equal(which, "spawn-success".to_unsafe)
               spawn_success(target)
             elsif equal(which, "spawn-null-arguments".to_unsafe)
               rejected_null_arguments
             elsif equal(which, "spawn-malformed-descriptor-size".to_unsafe)
               malformed_actions(target, false)
             elsif equal(which, "spawn-malformed-action-size".to_unsafe)
               malformed_actions(target, true)
             elsif equal(which, "spawn-invalid-cwd".to_unsafe)
               activation_rejected(target, true)
             elsif equal(which, "spawn-missing-executable".to_unsafe)
               activation_rejected(target, false)
             elsif equal(which, "spawn-rejection-cleanup".to_unsafe)
               rejection_cleanup(target)
             else
               47
             end
    result == 0 ? finish(which) : result
  end
end

fun main(argc : Int32, argv : UInt8**) : Int32
  Native::Kernel::Darwin::Process.exit(MontereySpawn.run(argc, argv))
end
