require "./raw"

module Native::Kernel::Darwin::Descriptor
  def self.read(fd : Int32, buffer : Pointer(T), count : UInt64) : Result forall T
    Raw.call(3, fd.to_u64!, buffer.address, count)
  end

  def self.write(fd : Int32, buffer : Pointer(T), count : UInt64) : Result forall T
    Raw.call(4, fd.to_u64!, buffer.address, count)
  end

  def self.close(fd : Int32) : Result
    Raw.call(6, fd.to_u64!)
  end

  def self.open(path : UInt8*, flags : Int32, mode : UInt32 = 0_u32) : Result
    Raw.call(5, path.address, flags.to_u64!, mode.to_u64)
  end

  def self.fcntl(fd : Int32, command : Int32, argument : Int32 = 0) : Result
    Raw.call(92, fd.to_u64!, command.to_u64!, argument.to_u64!)
  end

  # Darwin returns the two new descriptors in separate registers.
  def self.pipe : Result
    Raw.call(42)
  end

  def self.socket(domain : Int32, type : Int32, protocol : Int32) : Result
    Raw.call(97, domain.to_u64!, type.to_u64!, protocol.to_u64!)
  end

  def self.connect(fd : Int32, address : Void*, length : UInt32) : Result
    Raw.call(98, fd.to_u64!, address.address, length.to_u64)
  end

  def self.entries(fd : Int32, bytes : UInt8*, capacity : Int32, base : Int64*) : Result
    Raw.call(344, fd.to_u64!, bytes.address, capacity.to_u64!, base.address)
  end

  def self.seek(fd : Int32, offset : Int64, whence : Int32) : Result
    Raw.call(199, fd.to_u64!, offset.to_u64!, whence.to_u64!)
  end
end
