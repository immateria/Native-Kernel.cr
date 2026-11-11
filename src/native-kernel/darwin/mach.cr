require "./raw"

module Native::Kernel::Darwin::Mach
  # Each returned send right is owned by the caller. There is no cached task.
  def self.task : UInt32
    Raw.call(-28).primary.to_u32!
  end

  private TYPE_ERROR       =                   -300
  private REPLY_MISMATCH   =                   -301
  private ARRAY_TOO_LARGE  =                   -307
  private SEND_INTERRUPTED =             0x10000007
  private RCV_INTERRUPTED  =             0x10004005
  private SEND_KOBJECT     = 0x0000000200000000_u64

  def self.open(current_task : UInt32, pid : Int32) : Tuple(UInt32, Int32)
    name = 0_u32
    result = Raw.call(-44, current_task.to_u64, pid.to_u64!, pointerof(name).address)
    {name, result.primary.to_i32!}
  end

  def self.retain(current_task : UInt32, name : UInt32) : Int32
    Raw.call(-19, current_task.to_u64, name.to_u64, 0_u64, 1_u64).primary.to_i32!
  end

  def self.release(current_task : UInt32, name : UInt32) : Int32
    Raw.call(-18, current_task.to_u64, name.to_u64).primary.to_i32!
  end

  def self.read(current_task : UInt32, name : UInt32) : Tuple(StaticArray(UInt32, 8), UInt32, Int32)
    words = StaticArray(UInt32, 8).new(0_u32)
    reply = Raw.call(-26).primary.to_u32!
    return {words, 0_u32, 6} if reply == 0 || reply == UInt32::MAX

    # Only the request is initialized here. The kernel fills the reply, whose
    # declared size is validated before its payload is read.
    buffer = uninitialized UInt32[128]
    buffer.to_unsafe[0] = 0x1513_u32 # COPY_SEND target, MAKE_SEND_ONCE reply
    buffer.to_unsafe[1] = 40_u32
    buffer.to_unsafe[2] = name
    buffer.to_unsafe[3] = reply
    buffer.to_unsafe[4] = 0_u32    # no voucher
    buffer.to_unsafe[5] = 3405_u32 # task_info
    buffer.to_unsafe[6] = 0_u32    # NDR protocol, encoding and reserved bytes
    buffer.to_unsafe[7] = 1_u32    # NDR little-endian integer representation
    buffer.to_unsafe[8] = 15_u32   # TASK_AUDIT_TOKEN
    buffer.to_unsafe[9] = 8_u32

    code = exchange(buffer.to_unsafe, name, reply)
    # A dedicated receive right avoids sharing a runtime/TLS reply port.
    cleanup = Raw.call(-19, current_task.to_u64, reply.to_u64, 1_u64, UInt64::MAX).primary.to_i32!
    return {words, 0_u32, code} unless code == 0
    return {words, 0_u32, cleanup} unless cleanup == 0
    return {words, 0_u32, REPLY_MISMATCH} unless buffer.to_unsafe[5] == 3505
    size = buffer.to_unsafe[1]
    unless buffer.to_unsafe[0] & 0x80000000_u32 == 0 && size >= 36 && size <= 512 && buffer.to_unsafe[6] == 0 && buffer.to_unsafe[7] == 1
      return {words, 0_u32, TYPE_ERROR}
    end
    returned = buffer.to_unsafe[8].to_i32!
    return {words, 0_u32, returned} unless returned == 0
    return {words, 0_u32, TYPE_ERROR} unless size >= 40
    count = buffer.to_unsafe[9]
    return {words, count, ARRAY_TOO_LARGE} if count > 8
    return {words, count, TYPE_ERROR} unless size == 40_u32 &+ count &* 4_u32
    offset = 0
    while offset < count
      words.to_unsafe[offset] = buffer.to_unsafe[10_u32 &+ offset]
      offset &+= 1
    end
    {words, count, 0}
  end

  private def self.exchange(buffer : Pointer(UInt32), target : UInt32, reply : UInt32) : Int32
    options = SEND_KOBJECT | 3_u64
    send_size = 40_u64
    loop do
      code = Raw.call(-47, buffer.address, options,
        0x1513_u64 | (send_size.unsafe_shl(32)),
        target.to_u64 | (reply.to_u64.unsafe_shl(32)),
        3405_u64.unsafe_shl(32), reply.to_u64.unsafe_shl(32), 512_u64).primary.to_i32!
      if code == SEND_INTERRUPTED
        next
      elsif code == RCV_INTERRUPTED
        # Sending has completed. An interrupted receive retries only receive.
        options = SEND_KOBJECT | 2_u64
        send_size = 0_u64
      else
        return code
      end
    end
  end
end
