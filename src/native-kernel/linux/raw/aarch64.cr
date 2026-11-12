{% unless flag?(:linux) && !flag?(:android) && flag?(:bits64) && (flag?(:gnu) || flag?(:musl)) && flag?(:aarch64) %}
  {% raise "Linux AArch64 entry requires non-Android 64-bit Linux AArch64." %}
{% end %}

module Native::Kernel::Linux::Raw
  @[AlwaysInline]
  private def self.trap(number : Int32, a0 : UInt64, a1 : UInt64,
                        a2 : UInt64, a3 : UInt64, a4 : UInt64, a5 : UInt64) : Int64
    primary = 0_i64
    # Linux: x8 = number, x0..x5 = args, x0 = sole result. svc #0 is not
    # Darwin's svc #0x80/x16/carry convention. No stack or second result.
    asm("svc #0"
            : "={x0}"(primary)
            : "{x8}"(number.to_i64), "{x0}"(a0), "{x1}"(a1), "{x2}"(a2),
              "{x3}"(a3), "{x4}"(a4), "{x5}"(a5)
            : "memory", "cc"
            : "volatile")
    primary
  end
end
