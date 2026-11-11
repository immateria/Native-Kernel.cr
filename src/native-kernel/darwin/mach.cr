require "./raw"

module Native::Kernel::Darwin::Mach
  enum Transport
    # The seven-argument mach_msg_trap route in the Darwin 21 source profile.
    MachMsgTrap
    # Existing modern route. mach_msg2 is introduced after the Darwin 21 lane.
    MachMsg2
  end

  # A small pure state model permits controlled interruption tests without
  # injecting a kernel message. It never owns a message or a right.
  enum ExchangePhase
    SendAndReceive
    ReceiveOnly
    Done
  end

  # Each returned send right is owned by the caller. There is no cached task.
  def self.task : UInt32
    Raw.call(-28).primary.to_u32!
  end

  # Selection is explicit so a caller can admit a release before it sends.
  # The default read route remains mach_msg2 for existing modern callers.
  def self.transport(major : Int32) : Transport?
    case major
    when 21         then Transport::MachMsgTrap
    when 22, 23, 24, 25
      Transport::MachMsg2
    else
      nil
    end
  end

  private TYPE_ERROR       =                   -300
  private REPLY_MISMATCH   =                   -301
  private ARRAY_TOO_LARGE  =                   -307
  private SEND_INTERRUPTED =             0x10000007
  private RCV_INTERRUPTED  =             0x10004005
  private SEND_KOBJECT     = 0x0000000200000000_u64

  # mach_msg_trap options. The interrupt flags return ownership-relevant
  # states to this caller instead of making the kernel restart invisibly.
  private TRAP_SEND_RECEIVE_OPTIONS = 0x443_u64 # SEND | RCV | SEND_INTERRUPT | RCV_INTERRUPT
  private TRAP_RECEIVE_OPTIONS      = 0x402_u64 # RCV | RCV_INTERRUPT

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

  # `transport` is selected before the first send. A failed exchange never
  # sends the request again through a different transport.
  def self.read(current_task : UInt32, name : UInt32,
                transport : Transport = Transport::MachMsg2) : Tuple(StaticArray(UInt32, 8), UInt32, Int32)
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

    code = exchange(buffer.to_unsafe, name, reply, transport)
    # A dedicated receive right avoids sharing a runtime/TLS reply port. This
    # release is attempted after every exchange return, including malformed and
    # failed replies. A failed exchange keeps its native Mach result.
    cleanup = Raw.call(-19, current_task.to_u64, reply.to_u64, 1_u64, UInt64::MAX).primary.to_i32!
    return {words, 0_u32, code} unless code == 0
    return {words, 0_u32, cleanup} unless cleanup == 0
    decode_task_audit_reply(buffer.to_unsafe)
  end

  # This pure state transition permits controlled interruption fixtures. Only a
  # receive interruption following the send enters receive-only; no phase ever
  # selects another transport or resends after that transition.
  def self.retry_phase(phase : ExchangePhase, code : Int32) : ExchangePhase
    case phase
    when ExchangePhase::SendAndReceive
      return ExchangePhase::SendAndReceive if code == SEND_INTERRUPTED
      return ExchangePhase::ReceiveOnly if code == RCV_INTERRUPTED
    when ExchangePhase::ReceiveOnly
      return ExchangePhase::ReceiveOnly if code == RCV_INTERRUPTED
    end
    ExchangePhase::Done
  end

  # This pure, bounded decoder is public to permit controlled malformed-reply
  # fixtures without injecting a live kernel message. `buffer` must designate
  # at least 512 readable bytes. It does not take ownership of any right.
  def self.decode_task_audit_reply(buffer : Pointer(UInt32)) : Tuple(StaticArray(UInt32, 8), UInt32, Int32)
    words = StaticArray(UInt32, 8).new(0_u32)
    return {words, 0_u32, REPLY_MISMATCH} unless buffer[5] == 3505
    size = buffer[1]
    unless buffer[0] & 0x80000000_u32 == 0 && size >= 36 && size <= 512 && buffer[6] == 0 && buffer[7] == 1
      return {words, 0_u32, TYPE_ERROR}
    end
    returned = buffer[8].to_i32!
    return {words, 0_u32, returned} unless returned == 0
    return {words, 0_u32, TYPE_ERROR} unless size >= 40
    count = buffer[9]
    return {words, count, ARRAY_TOO_LARGE} if count > 8
    return {words, count, TYPE_ERROR} unless size == 40_u32 &+ count &* 4_u32
    offset = 0
    while offset < count
      words.to_unsafe[offset] = buffer[10_u32 &+ offset]
      offset &+= 1
    end
    {words, count, 0}
  end

  private def self.exchange(buffer : Pointer(UInt32), target : UInt32, reply : UInt32,
                            transport : Transport) : Int32
    phase = ExchangePhase::SendAndReceive
    loop do
      code = if phase == ExchangePhase::ReceiveOnly
               receive(buffer, reply, transport)
             else
               send_and_receive(buffer, target, reply, transport)
             end
      next_phase = retry_phase(phase, code)
      return code if next_phase == ExchangePhase::Done
      # XNU documents that send interruption leaves the caller with its message;
      # receive interruption has completed sending and keeps this transport.
      phase = next_phase
    end
  end

  private def self.send_and_receive(buffer : Pointer(UInt32), target : UInt32, reply : UInt32,
                                    transport : Transport) : Int32
    case transport
    when Transport::MachMsgTrap
      Raw.call(-31, buffer.address, TRAP_SEND_RECEIVE_OPTIONS, 40_u64, 512_u64,
        reply.to_u64, 0_u64, 0_u64).primary.to_i32!
    when Transport::MachMsg2
      Raw.call(-47, buffer.address, SEND_KOBJECT | 3_u64,
        0x1513_u64 | (40_u64.unsafe_shl(32)),
        target.to_u64 | (reply.to_u64.unsafe_shl(32)),
        3405_u64.unsafe_shl(32), reply.to_u64.unsafe_shl(32), 512_u64).primary.to_i32!
    end
  end

  private def self.receive(buffer : Pointer(UInt32), reply : UInt32, transport : Transport) : Int32
    case transport
    when Transport::MachMsgTrap
      Raw.call(-31, buffer.address, TRAP_RECEIVE_OPTIONS, 0_u64, 512_u64,
        reply.to_u64, 0_u64, 0_u64).primary.to_i32!
    when Transport::MachMsg2
      Raw.call(-47, buffer.address, SEND_KOBJECT | 2_u64,
        0x1513_u64, reply.to_u64.unsafe_shl(32),
        3405_u64.unsafe_shl(32), reply.to_u64.unsafe_shl(32), 512_u64).primary.to_i32!
    end
  end
end
