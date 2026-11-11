module Behavior
  def self.signal : Int32
    # The kernel invokes this native six-argument trampoline directly. Returning
    # through Signal.restore proves actual context restoration; rejected returns
    # terminate the fixture instead of returning into an absent caller frame.
    trampoline = ->(_handler : Void*, style : Int32, number : Int32, _info : Void*, context : Void*, token : UInt64) {
      byte = 83_u8
      written = Darwin::Descriptor.write(2, pointerof(byte), 1_u64)
      Darwin::Process.exit(51) unless number == 30 && written.error == 0 && written.primary == 1
      Darwin::Signal.restore(context, style, token)
      Darwin::Process.exit(52)
    }
    function = trampoline.pointer.address
    action = Darwin::Signal::Action.new(function, function, 0_u32, 0x40) # SA_SIGINFO
    old_action = uninitialized UInt8[32]
    original = 0_u32
    blocked = 1_u32.unsafe_shl(29) # SIGUSR1 (30)
    return 53 unless Darwin::Signal.mask(1, pointerof(blocked), pointerof(original)).error == 0
    installed = Darwin::Signal.action(30, pointerof(action), old_action.to_unsafe.as(Void*))
    unless installed.error == 0
      Darwin::Signal.mask(3, pointerof(original), Pointer(UInt32).null)
      return 54
    end
    result = signal_body(blocked)
    # The kernel old-action record is handler/mask/flags, without trampoline.
    # This worker starts with SIG_DFL; assert it and restore that exact default.
    previous_handler = old_action.to_unsafe.as(UInt64*).value
    previous_mask = (old_action.to_unsafe + 8).as(UInt32*).value
    previous_flags = (old_action.to_unsafe + 12).as(Int32*).value
    restored_action = Darwin::Signal::Action.new(previous_handler, 0_u64, previous_mask, previous_flags)
    restored = Darwin::Signal.action(30, pointerof(restored_action))
    mask_restored = Darwin::Signal.mask(3, pointerof(original), Pointer(UInt32).null)
    result == 0 && previous_handler == 0 && restored.error == 0 && mask_restored.error == 0 ? 0 : 55
  end

  def self.signal_body(blocked : UInt32) : Int32
    observed = 0_u32
    return 56 unless Darwin::Signal.mask(0, Pointer(UInt32).null, pointerof(observed)).error == 0 && observed & blocked == blocked
    return 57 unless Darwin::Signal.kill(Darwin::Process.pid.primary.to_i32!, 30).error == 0
    # Pending delivery must remain blocked until SIG_UNBLOCK. The trampoline's
    # single stderr byte plus completion after this call proves one restoration.
    return 58 unless Darwin::Signal.mask(2, pointerof(blocked), Pointer(UInt32).null).error == 0
    observed = blocked
    return 59 unless Darwin::Signal.mask(0, Pointer(UInt32).null, pointerof(observed)).error == 0 && observed & blocked == 0
    0
  end
end
