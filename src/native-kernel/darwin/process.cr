require "./raw"
require "./abi"

module Native::Kernel::Darwin::Process
  def self.pid : Result
    Raw.call(20)
  end

  def self.parent : Result
    Raw.call(39)
  end

  def self.fork : Result
    result = Raw.call(2)
    if result.error == 0 && result.secondary != 0
      return Result.new(0_i64, result.secondary, 0)
    end
    result
  end

  def self.waitpid(pid : Int32, status : Int32*, options : Int32) : Result
    Raw.call(7, pid.to_u64!, status.address, options.to_u64!, 0_u64)
  end

  def self.setsid : Result
    Raw.call(147)
  end

  def self.execve(path : UInt8*, arguments : UInt8**, environment : UInt8**) : Result
    Raw.call(59, path.address, arguments.address, environment.address)
  end

  def self.exit(code : Int32) : NoReturn
    loop do
      Raw.call(1, code.to_u64!)
    end
  end

  def self.list(buffer : Void*, size : Int32) : Result
    Raw.call(336, 1_u64, 1_u64, 0_u64, 0_u64, buffer.address, size.to_u64!)
  end

  def self.info(pid : Int32, flavor : Int32, argument : UInt64, buffer : Void*, size : Int32) : Result
    Raw.call(336, 2_u64, pid.to_u64!, flavor.to_u64!, argument, buffer.address, size.to_u64!)
  end

  def self.signal(words : Pointer(UInt32), number : Int32) : Int32
    Raw.call(336, 17_u64, 0_u64, number.to_u64!, 0_u64, words.address, 32_u64).error
  end

  def self.release : Int32
    name = StaticArray(Int32, 2).new(0)
    name.to_unsafe[0] = 1 # CTL_KERN
    name.to_unsafe[1] = 2 # KERN_OSRELEASE
    bytes = uninitialized UInt8[256]
    size = 256_u64
    result = Raw.call(202, name.to_unsafe.address, 2_u64, bytes.to_unsafe.address, pointerof(size).address)
    return 0 unless result.error == 0 && size > 0 && size <= 256
    major = 0
    offset = 0
    while offset < size && bytes.to_unsafe[offset] >= 48 && bytes.to_unsafe[offset] <= 57
      return 0 if major > 1000
      major = major &* 10 &+ bytes.to_unsafe[offset] &- 48
      offset &+= 1
    end
    return 0 if offset == 0 || offset >= size || bytes.to_unsafe[offset] != 46
    major
  end
end
