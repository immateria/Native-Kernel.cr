module Behavior
  # Keep LLVM from lowering this variable-length pathname copy to libc memcpy.
  @[NoInline]
  def self.socket_byte(destination : UInt8*, source : UInt8*) : Nil
    destination.value = source.value
  end

  def self.socket(path : UInt8*) : Int32
    size = length(path, 104)
    return 30 unless size > 0 && size < 104
    address = StaticArray(UInt8, 106).new(0_u8)
    address.to_unsafe[0] = (size &+ 3).to_u8!
    address.to_unsafe[1] = 1_u8 # AF_UNIX
    offset = 0
    while offset < size
      socket_byte(address.to_unsafe + (offset &+ 2), path + offset)
      offset &+= 1
    end
    server = Darwin::Descriptor.socket(1, 1, 0)
    return 31 unless server.error == 0 && server.primary >= 0
    server_fd = server.primary.to_i32!
    # Pinned Darwin bind(104), listen(106), accept(30) are the test oracle for
    # Descriptor.connect. They create no reusable production API surface.
    bound = Darwin::Raw.call(104, server_fd.to_u64!, address.to_unsafe.address, (size &+ 3).to_u64!)
    unless bound.error == 0
      Darwin::Descriptor.close(server_fd)
      return 32
    end
    result = socket_body(server_fd, address.to_unsafe.as(Void*), (size &+ 3).to_u32!)
    closed = Darwin::Descriptor.close(server_fd)
    removed = Darwin::Raw.call(10, path.address)
    result == 0 && closed.error == 0 && removed.error == 0 ? 0 : 33
  end

  def self.socket_body(server : Int32, address : Void*, size : UInt32) : Int32
    return 34 unless Darwin::Raw.call(106, server.to_u64!, 1_u64).error == 0
    return 35 unless Darwin::Descriptor.fcntl(server, 4, 4).error == 0 # O_NONBLOCK
    client = Darwin::Descriptor.socket(1, 1, 0)
    return 36 unless client.error == 0 && client.primary >= 0
    fd = client.primary.to_i32!
    connected = Darwin::Descriptor.connect(fd, address, size)
    result = 37
    if connected.error == 0
      poll = Darwin::Event::Poll.new(server)
      ready = Darwin::Event.poll(pointerof(poll), 1_u32, 1000)
      if ready.error == 0 && ready.primary == 1
        accepted = Darwin::Raw.call(30, server.to_u64!, 0_u64, 0_u64)
        if accepted.error == 0 && accepted.primary >= 0
          peer = accepted.primary.to_i32!
          byte = 75_u8
          sent = Darwin::Descriptor.write(fd, pointerof(byte), 1_u64)
          poll = Darwin::Event::Poll.new(peer)
          ready = Darwin::Event.poll(pointerof(poll), 1_u32, 1000)
          if sent.error == 0 && sent.primary == 1 && ready.error == 0 && ready.primary == 1
            byte = 0_u8
            received = Darwin::Descriptor.read(peer, pointerof(byte), 1_u64)
            result = 0 if received.error == 0 && received.primary == 1 && byte == 75
          end
          result = 38 unless Darwin::Descriptor.close(peer).error == 0
        end
      end
    end
    result = 39 unless Darwin::Descriptor.close(fd).error == 0
    result
  end
end
