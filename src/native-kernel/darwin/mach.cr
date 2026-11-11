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
    when 21 then Transport::MachMsgTrap
    when 22, 23, 24, 25
      Transport::MachMsg2
    else
      nil
    end
  end

  private TYPE_ERROR      = -300
  private REPLY_MISMATCH  = -301
  private ARRAY_TOO_LARGE = -307
  # An enum can hold an unchecked integral value. Return the native
  # KERN_INVALID_ARGUMENT value rather than throwing or selecting a route.
  private INVALID_TRANSPORT =                      4
  private SEND_INTERRUPTED  =             0x10000007
  private RCV_INTERRUPTED   =             0x10004005
  private SEND_KOBJECT      = 0x0000000200000000_u64

  # MACH_SEND_INTERRUPT and MACH_RCV_INTERRUPT are mach_msg-library options.
  # Darwin's raw mach_msg path masks them out with MACH_MSG_OPTION_USER, so a
  # direct trap must use only the user-visible SEND/RCV bits. The retry state
  # below still distinguishes an interrupted send from an interrupted receive
  # if the raw path reports either native result.
  private TRAP_SEND_RECEIVE_OPTIONS = 0x003_u64 # SEND | RCV
  private TRAP_RECEIVE_OPTIONS      = 0x002_u64 # RCV

  private TASK_INFO_REQUEST_ID    =   3405_u32
  private TASK_INFO_REPLY_ID      =   3505_u32
  private PORT_NAMES_REQUEST_ID   =   3200_u32
  private PORT_NAMES_REPLY_ID     =   3300_u32
  private PORT_NAMES_REPLY_SIZE   =     76_u32
  private MACH_MSG_OOL_DESCRIPTOR =      1_u32
  private RCV_BODY_ERROR          = 0x1000400c
  private RCV_ERROR_MASK          =     0x3e00
  private CLEANUP_UNCERTAIN       =          4

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
    buffer.to_unsafe[4] = 0_u32 # no voucher
    buffer.to_unsafe[5] = TASK_INFO_REQUEST_ID
    buffer.to_unsafe[6] = 0_u32  # NDR protocol, encoding and reserved bytes
    buffer.to_unsafe[7] = 1_u32  # NDR little-endian integer representation
    buffer.to_unsafe[8] = 15_u32 # TASK_AUDIT_TOKEN
    buffer.to_unsafe[9] = 8_u32

    code = exchange(buffer.to_unsafe, name, reply, transport, 40_u64, 512_u64, TASK_INFO_REQUEST_ID)
    # A dedicated receive right avoids sharing a runtime/TLS reply port. This
    # release is attempted after every exchange return, including malformed and
    # failed replies. A failed exchange keeps its native Mach result.
    cleanup = Raw.call(-19, current_task.to_u64, reply.to_u64, 1_u64, UInt64::MAX).primary.to_i32!
    return {words, 0_u32, code} unless code == 0
    return {words, 0_u32, cleanup} unless cleanup == 0
    decode_task_audit_reply(buffer.to_unsafe)
  end

  # This unmanaged-only metric is used by the Darwin 21 handoff fixture to
  # prove that repeated exchanges do not grow the caller's Mach name table. It
  # owns only the out-of-line arrays returned by this kernel RPC. The result is
  # {count, operation_code, cleanup_code}; success requires both codes zero.
  # All recognized mappings are disposed even after malformed/partial replies.
  def self.port_name_count(current_task : UInt32, transport : Transport) : Tuple(UInt32, Int32, Int32)
    reply = Raw.call(-26).primary.to_u32!
    return {0_u32, 6, 0} if reply == 0 || reply == UInt32::MAX

    buffer = uninitialized UInt32[128]
    buffer.to_unsafe[0] = 0x1513_u32 # COPY_SEND task, MAKE_SEND_ONCE reply
    buffer.to_unsafe[1] = 24_u32
    buffer.to_unsafe[2] = current_task
    buffer.to_unsafe[3] = reply
    buffer.to_unsafe[4] = 0_u32
    buffer.to_unsafe[5] = PORT_NAMES_REQUEST_ID

    code = exchange(buffer.to_unsafe, current_task, reply, transport, 24_u64, 512_u64, PORT_NAMES_REQUEST_ID)
    reply_cleanup = Raw.call(-19, current_task.to_u64, reply.to_u64, 1_u64, UInt64::MAX).primary.to_i32!
    finish_port_names_reply(current_task, buffer.to_unsafe, code, reply_cleanup)
  end

  # Only successful receives and partial body-copyout failures can have handed
  # us mappings. Never inspect the request/uninitialized buffer after send or
  # header failures. Keep the operation and cleanup results separate.
  private def self.finish_port_names_reply(current_task : UInt32, buffer : Pointer(UInt32),
                                           code : Int32, reply_cleanup : Int32) : Tuple(UInt32, Int32, Int32)
    return {0_u32, code, reply_cleanup} unless code == 0 || code & ~RCV_ERROR_MASK == RCV_BODY_ERROR

    addresses = uninitialized UInt64[30]
    sizes = uninitialized UInt64[30]
    owned, ownership_error = received_port_names_mappings(buffer, addresses.to_unsafe, sizes.to_unsafe)
    cleanup = reply_cleanup
    offset = 0_u32
    while offset < owned
      disposed = deallocate(current_task, addresses.to_unsafe[offset], sizes.to_unsafe[offset])
      cleanup = disposed if cleanup == 0 && disposed != 0
      offset &+= 1
    end
    cleanup = ownership_error if cleanup == 0
    return {0_u32, code, cleanup} unless code == 0

    count, _names_address, _names_bytes, _types_address, _types_bytes, decoded = decode_port_names_reply(buffer)
    {decoded == 0 ? count : 0_u32, decoded, cleanup}
  end

  # Snapshot only kernel-received port_names OOL memory before MIG validation.
  # The fixed buffer admits at most 30 sixteen-byte descriptors. Addresses and
  # byte sizes come from the descriptors, never from the MIG array counts.
  # This is not a general Mach-message destructor: unexpected carried rights or
  # structural variants produce a distinct unresolved-cleanup result. The caller
  # must supply a real received 512-byte buffer; synthetic plans are test-only.
  private def self.received_port_names_mappings(buffer : Pointer(UInt32), addresses : Pointer(UInt64),
                                                sizes : Pointer(UInt64)) : Tuple(UInt32, Int32)
    count = 0_u32
    failure = 0
    size = buffer[1]
    return {count, CLEANUP_UNCERTAIN} unless size >= 24_u32 && size <= 512_u32
    failure = CLEANUP_UNCERTAIN if buffer[2] != 0_u32 || buffer[4] != 0_u32
    return {count, failure} if buffer[0] & 0x80000000_u32 == 0
    return {count, CLEANUP_UNCERTAIN} unless size >= 28_u32

    descriptors = buffer[6]
    offset = 28_u32
    index = 0_u32
    bytes = buffer.as(UInt8*)
    while index < descriptors
      return {count, CLEANUP_UNCERTAIN} unless offset <= size && size &- offset >= 12_u32
      descriptor = (bytes + offset).as(UInt32*)
      kind = descriptor[2].unsafe_shr(24)
      if kind == 0_u32
        # Ordinary port descriptors are twelve bytes. A null name from partial
        # copyout owns nothing; non-null rights are outside this RPC contract.
        failure = CLEANUP_UNCERTAIN if descriptor[0] != 0_u32
        offset &+= 12_u32
      elsif kind == 1_u32 || kind == 2_u32 || kind == 3_u32
        return {count, CLEANUP_UNCERTAIN} unless size &- offset >= 16_u32
        address = descriptor[0].to_u64 | descriptor[1].to_u64.unsafe_shl(32)
        length = descriptor[3].to_u64
        if kind == 2_u32
          # OOL-port arrays can own rights as well as memory. Never misinterpret
          # them as the UInt32 data arrays returned by mach_port_names.
          failure = CLEANUP_UNCERTAIN if address != 0_u64 && length != 0_u64
        elsif kind == 1_u32 && address != 0_u64 && length != 0_u64
          failure = CLEANUP_UNCERTAIN if descriptor[2] & 0xffff_u32 != 0x0101_u32
          if descriptor[2] & 0xff_u32 == 0_u32 || length > UInt64::MAX &- address
            failure = CLEANUP_UNCERTAIN
            offset &+= 16_u32
            index &+= 1_u32
            next
          end
          # Merge duplicate/overlapping owned ranges so malformed semantic data
          # cannot make us release the same mapping twice. No alignment is
          # imposed: VM copyout can return an offset into a mapped page.
          finish = address &+ length
          prior = 0_u32
          while prior < count
            previous_finish = addresses[prior] &+ sizes[prior]
            if address <= previous_finish && addresses[prior] <= finish
              set_mapping_bound(pointerof(address), addresses[prior]) if addresses[prior] < address
              set_mapping_bound(pointerof(finish), previous_finish) if previous_finish > finish
              count &-= 1_u32
              addresses[prior] = addresses[count]
              sizes[prior] = sizes[count]
              prior = 0_u32
            else
              prior &+= 1_u32
            end
          end
          return {count, CLEANUP_UNCERTAIN} unless count < 30_u32
          addresses[count] = address
          sizes[count] = finish &- address
          count &+= 1_u32
        end
        # Apple's received-message destroy path deliberately skips volatile OOL.
        offset &+= 16_u32
      else
        return {count, CLEANUP_UNCERTAIN}
      end
      index &+= 1_u32
    end
    {count, failure}
  end

  # Keep these conditional updates as memory operations. LLVM 15 otherwise
  # folds the bounds into min/max intrinsics outside the exact native allowlist.
  @[NoInline]
  private def self.set_mapping_bound(destination : Pointer(UInt64), value : UInt64) : Nil
    destination.value = value
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
    return {words, 0_u32, REPLY_MISMATCH} unless buffer[5] == TASK_INFO_REPLY_ID
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
                            transport : Transport, send_size : UInt64, receive_size : UInt64,
                            message_id : UInt32) : Int32
    phase = ExchangePhase::SendAndReceive
    loop do
      code = if phase == ExchangePhase::ReceiveOnly
               receive(buffer, reply, transport, receive_size, message_id)
             else
               send_and_receive(buffer, target, reply, transport, send_size, receive_size, message_id)
             end
      next_phase = retry_phase(phase, code)
      return code if next_phase == ExchangePhase::Done
      # A reported send interruption leaves the request unsent; a reported
      # receive interruption means this route already completed its send.
      phase = next_phase
    end
  end

  private def self.send_and_receive(buffer : Pointer(UInt32), target : UInt32, reply : UInt32,
                                    transport : Transport, send_size : UInt64, receive_size : UInt64,
                                    message_id : UInt32) : Int32
    case transport
    when Transport::MachMsgTrap
      Raw.call(-31, buffer.address, TRAP_SEND_RECEIVE_OPTIONS, send_size, receive_size,
        reply.to_u64, 0_u64, 0_u64).primary.to_i32!
    when Transport::MachMsg2
      Raw.call(-47, buffer.address, SEND_KOBJECT | 3_u64,
        0x1513_u64 | send_size.unsafe_shl(32),
        target.to_u64 | reply.to_u64.unsafe_shl(32),
        message_id.to_u64.unsafe_shl(32), reply.to_u64.unsafe_shl(32), receive_size).primary.to_i32!
    else
      INVALID_TRANSPORT
    end
  end

  private def self.receive(buffer : Pointer(UInt32), reply : UInt32, transport : Transport,
                           receive_size : UInt64, message_id : UInt32) : Int32
    case transport
    when Transport::MachMsgTrap
      Raw.call(-31, buffer.address, TRAP_RECEIVE_OPTIONS, 0_u64, receive_size,
        reply.to_u64, 0_u64, 0_u64).primary.to_i32!
    when Transport::MachMsg2
      Raw.call(-47, buffer.address, SEND_KOBJECT | 2_u64,
        0x1513_u64, reply.to_u64.unsafe_shl(32),
        message_id.to_u64.unsafe_shl(32), reply.to_u64.unsafe_shl(32), receive_size).primary.to_i32!
    else
      INVALID_TRANSPORT
    end
  end

  private def self.decode_port_names_reply(buffer : Pointer(UInt32)) : Tuple(UInt32, UInt64, UInt64, UInt64, UInt64, Int32)
    return {0_u32, 0_u64, 0_u64, 0_u64, 0_u64, REPLY_MISMATCH} unless buffer[5] == PORT_NAMES_REPLY_ID
    # A kernel/MIG error reply is the non-complex header/NDR/RetCode form.
    if buffer[0] & 0x80000000_u32 == 0 && buffer[1] == 36_u32 && buffer[6] == 0 && buffer[7] == 1
      returned = buffer[8].to_i32!
      return {0_u32, 0_u64, 0_u64, 0_u64, 0_u64, returned == 0 ? TYPE_ERROR : returned}
    end
    return {0_u32, 0_u64, 0_u64, 0_u64, 0_u64, TYPE_ERROR} unless buffer[0] & 0x80000000_u32 != 0 &&
                                                                  buffer[1] == PORT_NAMES_REPLY_SIZE && buffer[6] == 2_u32 && buffer[15] == 0_u32 && buffer[16] == 1_u32

    # MIG packs the reply as header, body, two OOL descriptors, NDR, then
    # namesCnt/typesCnt: the two counts occupy words 17 and 18 (76 bytes).
    count = buffer[17]
    return {0_u32, 0_u64, 0_u64, 0_u64, 0_u64, TYPE_ERROR} unless buffer[18] == count
    names_bytes = count.to_u64.unsafe_shl(2)
    types_bytes = names_bytes
    names_address = buffer[7].to_u64 | buffer[8].to_u64.unsafe_shl(32)
    types_address = buffer[11].to_u64 | buffer[12].to_u64.unsafe_shl(32)
    names_type = buffer[9].unsafe_shr(24)
    types_type = buffer[13].unsafe_shr(24)
    return {0_u32, 0_u64, 0_u64, 0_u64, 0_u64, TYPE_ERROR} unless names_type == MACH_MSG_OOL_DESCRIPTOR && types_type == MACH_MSG_OOL_DESCRIPTOR &&
                                                                  buffer[10].to_u64 == names_bytes && buffer[14].to_u64 == types_bytes &&
                                                                  (count == 0_u32 || names_address != 0_u64 && types_address != 0_u64 &&
                                                                  buffer[9] & 0xffff_u32 == 0x0101_u32 && buffer[13] & 0xffff_u32 == 0x0101_u32)
    {count, names_address, names_bytes, types_address, types_bytes, 0}
  end

  private def self.deallocate(current_task : UInt32, address : UInt64, size : UInt64) : Int32
    return 0 if size == 0_u64
    Raw.call(-12, current_task.to_u64, address, size).primary.to_i32!
  end
end
