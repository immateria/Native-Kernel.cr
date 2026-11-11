module Behavior
  def self.descriptor(path : UInt8*) : Int32
    opened = Darwin::Descriptor.open(path, 0xa02, 0o600_u32) # O_RDWR | O_CREAT | O_EXCL
    return 10 unless opened.error == 0 && opened.primary >= 0
    fd = opened.primary.to_i32!
    result = descriptor_body(fd)
    closed = Darwin::Descriptor.close(fd)
    removed = Darwin::Raw.call(10, path.address) # unlink only our O_EXCL creation
    result == 0 && closed.error == 0 && removed.error == 0 ? 0 : 11
  end

  def self.descriptor_body(fd : Int32) : Int32
    written = Darwin::Descriptor.write(fd, "kernel".to_unsafe, 6_u64)
    return 12 unless written.error == 0 && written.primary == 6
    seek = Darwin::Descriptor.seek(fd, 1_i64, 0)
    return 13 unless seek.error == 0 && seek.primary == 1
    bytes = StaticArray(UInt8, 6).new(0_u8)
    read = Darwin::Descriptor.read(fd, bytes.to_unsafe, 5_u64)
    return 14 unless read.error == 0 && read.primary == 5 && equal(bytes.to_unsafe, "ernel".to_unsafe)
    return 15 unless Darwin::Descriptor.fcntl(fd, 2, 1).error == 0 # F_SETFD, FD_CLOEXEC
    flags = Darwin::Descriptor.fcntl(fd, 1)
    return 16 unless flags.error == 0 && flags.primary & 1 == 1
    return 17 unless Darwin::Descriptor.fcntl(fd, 4, 8).error == 0 # F_SETFL, O_APPEND
    flags = Darwin::Descriptor.fcntl(fd, 3)
    flags.error == 0 && flags.primary & 8 == 8 ? 0 : 18
  end

  def self.directory(path : UInt8*) : Int32
    opened = Darwin::Descriptor.open(path, 0)
    return 20 unless opened.error == 0 && opened.primary >= 0
    fd = opened.primary.to_i32!
    result = directory_body(fd)
    closed = Darwin::Descriptor.close(fd)
    result == 0 && closed.error == 0 ? 0 : 21
  end

  def self.directory_body(fd : Int32) : Int32
    bytes = uninitialized UInt8[8192]
    base = 0_i64
    attempt = 0
    while attempt < 64
      result = Darwin::Descriptor.entries(fd, bytes.to_unsafe, 8192, pointerof(base))
      return 22 unless result.error == 0 && result.primary > 0 && result.primary <= 8192
      offset = 0_i64
      while offset < result.primary
        return 23 if result.primary &- offset < 22
        entry = bytes.to_unsafe + offset
        size = (entry + 16).as(UInt16*).value
        name_size = (entry + 18).as(UInt16*).value
        return 24 unless size >= 22 && size <= result.primary &- offset && name_size < size &- 21 && entry[21 &+ name_size] == 0
        return 0 if name_size == 8 && equal(entry + 21, "nk-entry".to_unsafe)
        offset &+= size
      end
      attempt &+= 1
    end
    25
  end
end
