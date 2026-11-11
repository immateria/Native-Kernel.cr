module Behavior
  # A separate store keeps both optimization modes from replacing the bounded
  # initialization loop with an imported memory routine.
  @[NoInline]
  def self.spawn_zero_byte(destination : UInt8*) : Nil
    destination.value = 0_u8
  end

  def self.spawn_zero(destination : UInt8*, size : Int32) : Nil
    offset = 0
    while offset < size
      spawn_zero_byte(destination + offset)
      offset &+= 1
    end
  end

  def self.spawn_output(fd : Int32) : Bool
    bytes = uninitialized UInt8[12]
    size = 0
    attempt = 0
    while attempt < 100
      event = Darwin::Event::Poll.new(fd)
      ready = Darwin::Event.poll(pointerof(event), 1_u32, 50)
      return false unless ready.error == 0 || ready.error == 4
      if ready.error == 0 && ready.primary == 1
        read = Darwin::Descriptor.read(fd, bytes.to_unsafe + size, (12 &- size).to_u64!)
        return false unless read.error == 0 || read.error == 4
        if read.error == 0
          if read.primary == 0
            return false unless size == 11
            bytes.to_unsafe[11] = 0_u8
            return equal(bytes.to_unsafe, "NK_EXEC_OK\n".to_unsafe)
          end
          return false unless read.primary > 0 && read.primary < (12 &- size)
          size &+= read.primary.to_i32!
        end
      end
      attempt &+= 1
    end
    false
  end

  def self.spawn(path : UInt8*) : Int32
    profile = Darwin::Spawn.profile(Darwin::Process.release)
    return 92 unless profile
    # Fixed caller-owned storage: refuse an unexpected profile before encoding.
    return 92 unless profile.attributes_size == 192 && profile.descriptor_size == 144 && profile.actions_header_size == 8 && profile.action_size == 1040 && profile.path_capacity == 1024
    attributes = uninitialized UInt8[192]
    descriptor = uninitialized UInt8[144]
    actions = uninitialized UInt8[3128]
    spawn_zero(attributes.to_unsafe, 192)
    spawn_zero(descriptor.to_unsafe, 144)
    spawn_zero(actions.to_unsafe, 3128)
    (attributes.to_unsafe + profile.flags_offset).as(UInt16*).value = 0x400c_u16
    (attributes.to_unsafe + profile.defaults_offset).as(UInt32*).value = 0xfffefeff_u32
    (attributes.to_unsafe + profile.mask_offset).as(UInt32*).value = 0_u32
    (actions.to_unsafe + profile.actions_capacity_offset).as(Int32*).value = 3
    (actions.to_unsafe + profile.actions_count_offset).as(Int32*).value = 3

    pipe = Darwin::Descriptor.pipe
    return 93 unless pipe.error == 0
    reader, writer = pipe.primary.to_i32!, pipe.secondary.to_i32!
    unless reader >= 3 && writer >= 3
      Darwin::Descriptor.close(reader)
      Darwin::Descriptor.close(writer)
      return 93
    end
    action = actions.to_unsafe + profile.actions_header_size
    (action + profile.action_type_offset).as(Int32*).value = 2 # DUP2
    (action + profile.action_fd_offset).as(Int32*).value = writer
    (action + profile.action_destination_offset).as(Int32*).value = 1
    action += profile.action_size
    (action + profile.action_type_offset).as(Int32*).value = 1 # CLOSE
    (action + profile.action_fd_offset).as(Int32*).value = reader
    action += profile.action_size
    (action + profile.action_type_offset).as(Int32*).value = 5 # CHDIR
    (action + profile.chdir_path_offset).value = 47_u8         # /
    (descriptor.to_unsafe + profile.descriptor_attribute_size_offset).as(UInt64*).value = 192_u64
    (descriptor.to_unsafe + profile.descriptor_attributes_offset).as(UInt64*).value = attributes.to_unsafe.address
    (descriptor.to_unsafe + profile.descriptor_actions_size_offset).as(UInt64*).value = 3128_u64
    (descriptor.to_unsafe + profile.descriptor_actions_offset).as(UInt64*).value = actions.to_unsafe.address
    arguments = StaticArray(UInt8*, 3).new(Pointer(UInt8).null)
    arguments.to_unsafe[0] = path
    arguments.to_unsafe[1] = "nk-exec-proof".to_unsafe
    environment = StaticArray(UInt8*, 2).new(Pointer(UInt8).null)
    environment.to_unsafe[0] = "NK_EXEC_PROOF=1".to_unsafe
    child = 0
    created = Darwin::Spawn.create(pointerof(child), path, descriptor.to_unsafe.as(Void*), arguments.to_unsafe, environment.to_unsafe)
    write_closed = Darwin::Descriptor.close(writer)
    unless created.error == 0 && child > 0
      Darwin::Descriptor.close(reader)
      return 94
    end
    output = write_closed.error == 0 && spawn_output(reader)
    read_closed = Darwin::Descriptor.close(reader)
    collected = collect(child, 37 &* 256, !output)
    output && read_closed.error == 0 && collected ? 0 : 95
  end
end
