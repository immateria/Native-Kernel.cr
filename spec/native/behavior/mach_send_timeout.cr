module Behavior
  private MACH_SEND_TIMED_OUT      = 0x10000004
  private MACH_MSG_TYPE_MOVE_SEND  =     17_u32
  private MACH_MSG_TYPE_COPY_SEND  =     19_u32
  private MACH_MSG_TYPE_MAKE_SEND  =     20_u64
  private MACH_PORT_RIGHT_SEND     =      0_u32
  private MACH_PORT_RIGHT_RECEIVE  =      1_u64
  private MACH_PORT_QLIMIT_DEFAULT =      5_u32
  private MACH_GET_REFS_REQUEST    =   3207_u32
  private MACH_GET_REFS_REPLY      =   3307_u32
  private MACH_MESSAGE_BYTES       =     28_u32
  private MACH_RECEIVE_BYTES       =    128_u64
  private MACH_FILLER_ID           = 0x5101_u32
  private MACH_FILLER_VALUE        = 0x6101_u32

  # mach_msg2 option classes are part of the fixture-local, source-reviewed
  # contract. Every operation has a finite kernel timeout. The outer runner
  # supplies a separate process deadline and disposable-host teardown.
  private MACH64_SEND_KOBJECT_CALL = 0x0000000200000000_u64
  private MACH64_SEND_MQ_CALL      = 0x0000000400000000_u64
  private MACH_SEND_MSG            =                0x1_u64
  private MACH_RCV_MSG             =                0x2_u64
  private MACH_SEND_TIMEOUT        =               0x10_u64
  private MACH_RCV_TIMEOUT         =              0x100_u64

  enum MachSendOwnership
    None
    Owned
    Consumed
    Uncertain
  end

  # The production specialization is a stateless, compile-time adapter. Tests
  # supply a scripted adapter to exercise cleanup wiring without invoking Mach.
  # Crystal specializes the generic fixture for this value type, so the native
  # artifact retains direct raw calls rather than an indirect operations table.
  struct MachSendSystem
    def task_self : Int64
      Darwin::Raw.call(-28).primary
    end

    def allocate_receive(task : UInt32, destination : Pointer(UInt32)) : Int32
      Darwin::Raw.call(-16, task.to_u64, MACH_PORT_RIGHT_RECEIVE,
        destination.address).primary.to_i32!
    end

    def insert_send(task : UInt32, destination : UInt32) : Int32
      Darwin::Raw.call(-21, task.to_u64, destination.to_u64,
        destination.to_u64, MACH_MSG_TYPE_MAKE_SEND).primary.to_i32!
    end

    def reply_receive : Int64
      Darwin::Raw.call(-26).primary
    end

    def get_refs_exchange(words : Pointer(UInt32), task : UInt32, reply : UInt32) : Int32
      Darwin::Raw.call(-47, words.address,
        MACH64_SEND_KOBJECT_CALL | MACH_SEND_MSG | MACH_RCV_MSG | MACH_SEND_TIMEOUT | MACH_RCV_TIMEOUT,
        0x1513_u64 | 40_u64.unsafe_shl(32),
        task.to_u64 | reply.to_u64.unsafe_shl(32),
        MACH_GET_REFS_REQUEST.to_u64.unsafe_shl(32),
        reply.to_u64.unsafe_shl(32), 128_u64, 1000_u64).primary.to_i32!
    end

    def remove_receive(task : UInt32, name : UInt32) : Int32
      Darwin::Raw.call(-19, task.to_u64, name.to_u64,
        MACH_PORT_RIGHT_RECEIVE, UInt64::MAX).primary.to_i32!
    end

    def send_message(words : Pointer(UInt32), destination : UInt32,
                     disposition : UInt32, identifier : UInt32) : Int32
      Darwin::Raw.call(-47, words.address,
        MACH64_SEND_MQ_CALL | MACH_SEND_MSG | MACH_SEND_TIMEOUT,
        disposition.to_u64 | MACH_MESSAGE_BYTES.to_u64.unsafe_shl(32),
        destination.to_u64, identifier.to_u64.unsafe_shl(32),
        0_u64, 0_u64, 0_u64).primary.to_i32!
    end

    def receive_message(words : Pointer(UInt32), destination : UInt32) : Int32
      Darwin::Raw.call(-47, words.address,
        MACH64_SEND_MQ_CALL | MACH_RCV_MSG | MACH_RCV_TIMEOUT,
        0_u64, 0_u64, 0_u64, destination.to_u64.unsafe_shl(32),
        MACH_RECEIVE_BYTES, 1000_u64).primary.to_i32!
    end

    def release_send(task : UInt32, name : UInt32) : Int32
      Darwin::Raw.call(-18, task.to_u64, name.to_u64).primary.to_i32!
    end
  end

  # Pure transitions keep the pre-copyin, pseudo-receive and uncertain states
  # independently mutation-testable without injecting a live kernel message.
  def self.mach_copy_send_ownership(original_header_valid : Bool,
                                    restored_header_valid : Bool, refs_valid : Bool,
                                    refs : UInt32) : MachSendOwnership
    return MachSendOwnership::Owned if !original_header_valid && restored_header_valid && refs_valid && refs == 2_u32
    return MachSendOwnership::None if original_header_valid && !restored_header_valid && refs_valid && refs == 1_u32
    MachSendOwnership::Uncertain
  end

  def self.mach_move_send_ownership(result : Int32, header_valid : Bool,
                                    refs_valid : Bool, refs : UInt32) : MachSendOwnership
    return MachSendOwnership::Consumed if result == 0
    return MachSendOwnership::Owned if result == MACH_SEND_TIMED_OUT && header_valid && refs_valid && refs == 1_u32
    MachSendOwnership::Uncertain
  end

  # Successful copyin replaces the caller's COPY_SEND disposition with the
  # received PORT_SEND/MOVE_SEND type. Every other request field must remain
  # byte-for-byte identifiable before either state authorizes cleanup.
  def self.mach_send_header_states(words : Pointer(UInt32), destination : UInt32,
                                   identifier : UInt32, value : UInt32) : Tuple(Bool, Bool)
    shared = words[1] == MACH_MESSAGE_BYTES && words[2] == destination &&
             words[3] == 0_u32 && words[4] == 0_u32 &&
             words[5] == identifier && words[6] == value
    original = shared && words[0] == MACH_MSG_TYPE_COPY_SEND
    restored = shared && words[0] == MACH_MSG_TYPE_MOVE_SEND
    {original, restored}
  end

  # Decode only the two exact MIG reply forms. The generated client requires a
  # null request port in the received reply; a malformed envelope owns no refs.
  def self.mach_get_refs_reply(words : Pointer(UInt32)) : Tuple(UInt32, Int32, Bool)
    envelope = words[0] & 0x80000000_u32 == 0 && words[2] == 0_u32 &&
               words[5] == MACH_GET_REFS_REPLY && words[6] == 0_u32 && words[7] == 1_u32
    return {0_u32, -302, false} unless envelope
    if words[1] == 36_u32
      returned = words[8].unsafe_as(Int32)
      return {0_u32, returned == 0 ? -302 : returned, false}
    end
    return {0_u32, -302, false} unless words[1] == 40_u32 && words[8] == 0_u32
    {words[9], 0, true}
  end

  def self.mach_received_filler(words : Pointer(UInt32)) : Bool
    words[0] & 0x80000000_u32 == 0 && words[1] == MACH_MESSAGE_BYTES &&
      words[5] == MACH_FILLER_ID && words[6] == MACH_FILLER_VALUE
  end

  def self.mach_cleanup_result(primary : Int32, reply : Int32, extra : Int32,
                               send : Int32, receive : Int32, task : Int32) : Int32
    return 230 if reply != 0
    return 231 if extra != 0
    return 232 if send != 0
    return 233 if receive != 0
    return 234 if task != 0
    primary
  end

  # Returns {refs, operation, reply-right cleanup, valid scalar reply}. The
  # dedicated reply receive right is retired after every bounded exchange.
  private def self.mach_send_refs(ops : T, task : UInt32, name : UInt32) : Tuple(UInt32, Int32, Int32, Bool) forall T
    reply_value = ops.reply_receive
    return {0_u32, 6, 0, false} if reply_value <= 0 || reply_value > UInt32::MAX
    reply = reply_value.to_u32!

    buffer = StaticArray(UInt32, 32).new(0_u32)
    words = buffer.to_unsafe
    words[0] = 0x1513_u32 # COPY_SEND request, MAKE_SEND_ONCE reply
    words[1] = 40_u32
    words[2] = task
    words[3] = reply
    words[5] = MACH_GET_REFS_REQUEST
    words[7] = 1_u32 # NDR little-endian integer representation
    words[8] = name
    words[9] = MACH_PORT_RIGHT_SEND

    operation = ops.get_refs_exchange(words, task, reply)
    reply_cleanup = ops.remove_receive(task, reply)
    return {0_u32, operation, reply_cleanup, false} unless operation == 0

    refs, decoded, valid = mach_get_refs_reply(words)
    {refs, decoded, reply_cleanup, valid}
  end

  private def self.prepare_mach_message(words : Pointer(UInt32), destination : UInt32,
                                        disposition : UInt32, identifier : UInt32,
                                        value : UInt32) : Nil
    offset = 0
    while offset < 32
      words[offset] = 0_u32
      offset &+= 1
    end
    words[0] = disposition
    words[1] = MACH_MESSAGE_BYTES
    words[2] = destination
    words[5] = identifier
    words[6] = value
  end

  private def self.mach_send_message(ops : T, words : Pointer(UInt32), destination : UInt32,
                                     disposition : UInt32, identifier : UInt32,
                                     value : UInt32) : Int32 forall T
    prepare_mach_message(words, destination, disposition, identifier, value)
    ops.send_message(words, destination, disposition, identifier)
  end

  private def self.mach_release_send(ops : T, task : UInt32, name : UInt32) : Int32 forall T
    ops.release_send(task, name)
  end

  # This case intentionally has no general Mach-message abstraction. It owns
  # one namespace entry and accounts for each receive/send reference separately.
  # On uncertain pseudo-receive ownership it does not guess a reference delta;
  # the disposable GitHub runner contains the remaining process namespace.
  def self.mach_send_timeout : Int32
    mach_send_timeout_with(MachSendSystem.new)
  end

  def self.mach_send_timeout_with(ops : T) : Int32 forall T
    primary_error = 0
    reply_cleanup_error = 0
    extra_cleanup_error = 0
    send_cleanup_error = 0
    receive_cleanup_error = 0
    task_cleanup_error = 0

    task = 0_u32
    destination = 0_u32
    task_owned = false
    receive_owned = false
    original_send_owned = false
    extra_send_owned = false
    buffer = StaticArray(UInt32, 32).new(0_u32)
    words = buffer.to_unsafe

    task_value = ops.task_self
    if task_value <= 0 || task_value > UInt32::MAX
      primary_error = 170
    else
      task = task_value.to_u32!
      task_owned = true
    end

    if primary_error == 0
      allocated = ops.allocate_receive(task, pointerof(destination))
      if allocated != 0 || destination == 0_u32 || destination == UInt32::MAX
        primary_error = 171
      else
        receive_owned = true
      end
    end

    if primary_error == 0
      inserted = ops.insert_send(task, destination)
      if inserted != 0
        primary_error = 172
      else
        original_send_owned = true
      end
    end

    if primary_error == 0
      refs, operation, reply_cleanup, valid = mach_send_refs(ops, task, destination)
      reply_cleanup_error = reply_cleanup if reply_cleanup != 0
      if operation != 0 || !valid
        primary_error = 173
      elsif reply_cleanup != 0
        primary_error = 174
      elsif refs != 1_u32
        primary_error = 175
      end
    end

    filled = 0_u32
    while primary_error == 0 && filled < MACH_PORT_QLIMIT_DEFAULT
      result = mach_send_message(ops, words, destination, MACH_MSG_TYPE_COPY_SEND,
        MACH_FILLER_ID &+ filled, MACH_FILLER_VALUE &+ filled)
      if result == 0
        filled &+= 1_u32
      else
        # A failed COPY_SEND can preserve only the original reference or can
        # pseudo-receive a second reference after copyin. Classify the count
        # before cleanup; never infer it from the native result alone.
        refs, operation, reply_cleanup, valid = mach_send_refs(ops, task, destination)
        reply_cleanup_error = reply_cleanup if reply_cleanup_error == 0 && reply_cleanup != 0
        # Successful copyin converts COPY_SEND to the received PORT_SEND type,
        # whose user-visible numeric value is MOVE_SEND.
        original_header, restored_header = mach_send_header_states(words, destination,
          MACH_FILLER_ID &+ filled, MACH_FILLER_VALUE &+ filled)
        ownership = mach_copy_send_ownership(original_header, restored_header,
          valid && operation == 0, refs)
        extra_send_owned = true if ownership == MachSendOwnership::Owned
        primary_error = 176
      end
    end

    if primary_error == 0
      result = mach_send_message(ops, words, destination, MACH_MSG_TYPE_COPY_SEND,
        0x5200_u32, 0x6200_u32)
      original_header, restored_header = mach_send_header_states(words, destination,
        0x5200_u32, 0x6200_u32)
      refs, operation, reply_cleanup, valid = mach_send_refs(ops, task, destination)
      reply_cleanup_error = reply_cleanup if reply_cleanup_error == 0 && reply_cleanup != 0
      ownership = mach_copy_send_ownership(original_header, restored_header,
        valid && operation == 0, refs)
      if result != MACH_SEND_TIMED_OUT
        extra_send_owned = true if ownership == MachSendOwnership::Owned
        primary_error = 177
      elsif !restored_header
        primary_error = 178
      elsif operation != 0 || !valid
        primary_error = 179
      elsif reply_cleanup != 0
        primary_error = 180
      elsif refs != 2_u32
        primary_error = 181
      else
        extra_send_owned = true
      end
    end

    if primary_error == 0 && extra_send_owned
      released = mach_release_send(ops, task, destination)
      # Never retry a failed deallocation: its resulting ownership is unknown.
      extra_send_owned = false
      if released != 0
        extra_cleanup_error = released
        primary_error = 182
      end
    end

    if primary_error == 0
      refs, operation, reply_cleanup, valid = mach_send_refs(ops, task, destination)
      reply_cleanup_error = reply_cleanup if reply_cleanup_error == 0 && reply_cleanup != 0
      if operation != 0 || !valid
        primary_error = 183
      elsif reply_cleanup != 0
        primary_error = 184
      elsif refs != 1_u32
        primary_error = 185
      end
    end

    if primary_error == 0
      result = mach_send_message(ops, words, destination, MACH_MSG_TYPE_MOVE_SEND,
        0x5300_u32, 0x6300_u32)
      # MOVE_SEND consumes the known reference during copyin. It becomes owned
      # again only after timeout, returned-header and exact-count validation.
      original_send_owned = false
      if result == 0
        primary_error = 186
      elsif result != MACH_SEND_TIMED_OUT
        primary_error = 187
      elsif words[2] != destination || words[0] & 0xff_u32 != MACH_MSG_TYPE_MOVE_SEND
        primary_error = 188
      else
        refs, operation, reply_cleanup, valid = mach_send_refs(ops, task, destination)
        reply_cleanup_error = reply_cleanup if reply_cleanup_error == 0 && reply_cleanup != 0
        ownership = mach_move_send_ownership(result, true, valid && operation == 0, refs)
        if operation != 0 || !valid
          primary_error = 189
        elsif reply_cleanup != 0
          original_send_owned = true if refs == 1_u32
          primary_error = 190
        elsif refs != 1_u32
          primary_error = 191
        elsif ownership == MachSendOwnership::Owned
          original_send_owned = true
        else
          primary_error = 191
        end
      end
    end

    if primary_error == 0
      offset = 0
      while offset < 32
        words[offset] = 0_u32
        offset &+= 1
      end
      received = ops.receive_message(words, destination)
      if received != 0
        primary_error = 192
      elsif !mach_received_filler(words)
        primary_error = 193
      end
    end

    if extra_send_owned
      released = mach_release_send(ops, task, destination)
      extra_cleanup_error = released if released != 0
      extra_send_owned = false
    end
    if original_send_owned
      released = mach_release_send(ops, task, destination)
      send_cleanup_error = released if released != 0
      original_send_owned = false
    end
    if receive_owned
      removed = ops.remove_receive(task, destination)
      receive_cleanup_error = removed if removed != 0
      receive_owned = false
    end
    if task_owned
      released = mach_release_send(ops, task, task)
      task_cleanup_error = released if released != 0
      task_owned = false
    end

    mach_cleanup_result(primary_error, reply_cleanup_error, extra_cleanup_error,
      send_cleanup_error, receive_cleanup_error, task_cleanup_error)
  end
end
