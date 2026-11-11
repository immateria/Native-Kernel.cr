{% unless flag?(:darwin) && (flag?(:aarch64) || flag?(:x86_64)) %}
  {% raise "Darwin kernel calls require ARM64 or x86-64." %}
{% end %}

require "./result"

module Native::Kernel::Darwin::Raw
  # Positive numbers select BSD syscalls. Negative numbers select Mach traps,
  # whose native return code remains in primary instead of using errno.
  def self.call(number : Int32, a0 : UInt64 = 0_u64, a1 : UInt64 = 0_u64,
                a2 : UInt64 = 0_u64, a3 : UInt64 = 0_u64,
                a4 : UInt64 = 0_u64, a5 : UInt64 = 0_u64,
                a6 : UInt64 = 0_u64, a7 : UInt64 = 0_u64) : Result
    result = trap(number, a0, a1, a2, a3, a4, a5, a6, a7)
    return Result.new(-1_i64, result.secondary, result.error) unless result.error == 0
    result
  end
end

{% if flag?(:aarch64) %}
  require "./raw/arm64"
{% elsif flag?(:x86_64) %}
  require "./raw/x86_64"
{% end %}
