# Darwin 21 private-spawn proof. Build with -Dwithout_main.
# Parent -> one syscall-created target child; the parent is the exclusive
# collector and has bounded output/termination cleanup.
require "../../src/native-kernel/darwin"

module MontereySpawn
  alias Darwin = Native::Kernel::Darwin

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

  def self.collect(pid : Int32, expected : Int32, terminate : Bool) : Bool
    status = 0
    attempt = 0
    while attempt < 2000
      result = Darwin::Process.waitpid(pid, pointerof(status), 1) # WNOHANG
      return result.error == 0 && status == expected if result.primary == pid
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
      return false if result.primary == pid || result.error == 10
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

  def self.spawn(target : UInt8*) : Int32
    profile = Darwin::Spawn.profile(Darwin::Process.release)
    return 20 unless profile && profile.layout == Darwin::Spawn::Layout::Darwin21
    return 21 unless profile.attributes_size == 152 && profile.fixed_attribute_copy_size == 152 &&
                     profile.descriptor_size == 128 && profile.actions_header_size == 8 &&
                     profile.action_size == 1040 && profile.path_capacity == 1024

    # The largest local storage is explicit, while each kernel copy length is
    # encoded from the selected profile. Darwin 21 receives only 152/128 bytes.
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
    return 22 unless pipe.error == 0
    reader, writer = pipe.primary.to_i32!, pipe.secondary.to_i32!
    unless reader >= 3 && writer >= 3
      Darwin::Descriptor.close(reader)
      Darwin::Descriptor.close(writer)
      return 22
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

    (descriptor.to_unsafe + profile.descriptor_attribute_size_offset).as(UInt64*).value = profile.attributes_size.to_u64
    (descriptor.to_unsafe + profile.descriptor_attributes_offset).as(UInt64*).value = attributes.to_unsafe.address
    (descriptor.to_unsafe + profile.descriptor_actions_size_offset).as(UInt64*).value = 3128_u64
    (descriptor.to_unsafe + profile.descriptor_actions_offset).as(UInt64*).value = actions.to_unsafe.address

    fd_text = uninitialized UInt8[12]
    return 23 unless decimal(writer, fd_text.to_unsafe) > 0
    arguments = StaticArray(UInt8*, 4).new(Pointer(UInt8).null)
    arguments.to_unsafe[0] = target
    arguments.to_unsafe[1] = "nk-spawn-proof".to_unsafe
    arguments.to_unsafe[2] = fd_text.to_unsafe
    environment = StaticArray(UInt8*, 2).new(Pointer(UInt8).null)
    environment.to_unsafe[0] = "NK_SPAWN_PROOF=1".to_unsafe

    # Install a non-default disposition/mask. This executable is the runner's
    # owned probe process and exits after the case. Do not reconstruct a prior
    # action: sigaction copyout omits sa_tramp, while a raw replacement needs it.
    # The spawned target checks that SETSIGDEF and SETSIGMASK reset these states.
    ignored = Darwin::Signal::Action.new(1_u64, 0_u64, 0_u32, 0)
    installed = Darwin::Signal.action(30, pointerof(ignored))
    unless installed.error == 0
      Darwin::Descriptor.close(reader)
      Darwin::Descriptor.close(writer)
      return 24
    end
    blocked = 1_u32.unsafe_shl(29)
    masked = Darwin::Signal.mask(1, pointerof(blocked), Pointer(UInt32).null)
    unless masked.error == 0
      Darwin::Descriptor.close(reader)
      Darwin::Descriptor.close(writer)
      return 25
    end

    child = 0
    created = Darwin::Spawn.create(pointerof(child), target, descriptor.to_unsafe.as(Void*), arguments.to_unsafe, environment.to_unsafe)
    write_closed = Darwin::Descriptor.close(writer)
    if created.error != 0 || child <= 0
      read_closed = Darwin::Descriptor.close(reader)
      # Do not retry an ambiguous creation. If the kernel did return a positive
      # PID, retain the only collector and make one bounded cleanup attempt.
      uncertain_cleanup = child > 0 ? collect(child, 9, true) : true
      return write_closed.error == 0 && read_closed.error == 0 && uncertain_cleanup ? 27 : 28
    end

    received = write_closed.error == 0 && output(reader)
    read_closed = Darwin::Descriptor.close(reader)
    collected = collect(child, 37 &* 256, !received)
    received && read_closed.error == 0 && collected ? 0 : 29
  end

  def self.run(argc : Int32, argv : UInt8**) : Int32
    return 2 unless argc == 2 && !argv[1].null?
    # This error path must not create a child or alter the caller's output.
    child = 0
    rejected = Darwin::Spawn.create(pointerof(child), Pointer(UInt8).null, Pointer(Void).null,
      Pointer(Pointer(UInt8)).null, Pointer(Pointer(UInt8)).null)
    return 3 unless rejected.primary == -1 && rejected.error == 14 && child == 0
    result = spawn(argv[1])
    return result unless result == 0
    completed = Darwin::Descriptor.write(1, "NK_OK spawn\n".to_unsafe, 12_u64)
    completed.error == 0 && completed.primary == 12 ? 0 : 30
  end
end

fun main(argc : Int32, argv : UInt8**) : Int32
  Native::Kernel::Darwin::Process.exit(MontereySpawn.run(argc, argv))
end
