require "./raw"

module Native::Kernel::Darwin::Signal
  # XNU __user64_sigaction includes the trampoline before mask and flags.
  struct Action
    @handler : UInt64
    @trampoline : UInt64
    @mask : UInt32
    @flags : Int32

    def initialize(@handler, @trampoline, @mask, @flags)
    end
  end

  def self.kill(pid : Int32, number : Int32) : Result
    Raw.call(37, pid.to_u64!, number.to_u64!)
  end

  # This accepts the exact native record; signal reset policy belongs to callers.
  def self.action(number : Int32, action : Action*, previous : Void* = Pointer(Void).null) : Result
    Raw.call(46, number.to_u64!, action.address, previous.address)
  end

  def self.mask(how : Int32, mask : UInt32*, previous : UInt32*) : Result
    Raw.call(48, how.to_u64!, mask.address, previous.address)
  end

  def self.restore(context : Void*, style : Int32, token : UInt64) : Result
    Raw.call(184, context.address, style.to_u64!, token)
  end
end
