{% unless flag?(:linux) && !flag?(:android) && flag?(:bits64) && (flag?(:gnu) || flag?(:musl)) && flag?(:x86_64) %}
  {% raise "Linux x86-64 entry requires non-Android 64-bit Linux x86-64." %}
{% end %}

module Native::Kernel::Linux::Raw
  @[AlwaysInline]
  private def self.trap(number : Int32, a0 : UInt64, a1 : UInt64,
                        a2 : UInt64, a3 : UInt64, a4 : UInt64, a5 : UInt64) : Int64
    primary = 0_i64
    # Linux: rax = number/result; rdi,rsi,rdx,r10,r8,r9 = args.
    # syscall overwrites rcx/r11. The conservative flags clobber uses LLVM's
    # x86 register name (not GCC's cc). Unlike Darwin no stack slots or carry.
    asm("syscall"
            : "={rax}"(primary)
            : "{rax}"(number.to_i64), "{rdi}"(a0), "{rsi}"(a1), "{rdx}"(a2),
              "{r10}"(a3), "{r8}"(a4), "{r9}"(a5)
            : "rcx", "r11", "memory", "flags"
            : "volatile")
    primary
  end
end
