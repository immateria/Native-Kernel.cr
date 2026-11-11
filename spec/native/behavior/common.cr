module Behavior
  alias Darwin = Native::Kernel::Darwin

  def self.equal(left : UInt8*, right : UInt8*) : Bool
    offset = 0
    while offset < 256
      return false unless left[offset] == right[offset]
      return true if left[offset] == 0
      offset &+= 1
    end
    false
  end

  def self.length(value : UInt8*, maximum : Int32) : Int32
    offset = 0
    while offset < maximum
      return offset if value[offset] == 0
      offset &+= 1
    end
    -1
  end

  # No blocking waitpid: the child is ours, and every failure path attempts both
  # termination and collection. The runner supplies an independent outer bound.
  def self.collect(pid : Int32, expected : Int32, terminate : Bool = false) : Bool
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

  def self.child_gate(fd : Int32) : Bool
    poll = Darwin::Event::Poll.new(fd)
    ready = Darwin::Event.poll(pointerof(poll), 1_u32, 3000)
    return false unless ready.error == 0 && ready.primary == 1
    byte = 0_u8
    read = Darwin::Descriptor.read(fd, pointerof(byte), 1_u64)
    read.error == 0 && read.primary == 1 && byte == 71
  end

  def self.success(name : UInt8*) : Int32
    count = length(name, 32)
    return 90 if count < 1
    prefix = Darwin::Descriptor.write(1, "NK_OK ".to_unsafe, 6_u64)
    value = Darwin::Descriptor.write(1, name, count.to_u64!)
    newline = Darwin::Descriptor.write(1, "\n".to_unsafe, 1_u64)
    prefix.error == 0 && prefix.primary == 6 && value.error == 0 && value.primary == count && newline.error == 0 && newline.primary == 1 ? 0 : 91
  end
end
