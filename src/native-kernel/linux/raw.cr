# Only reviewed LP64 GNU/musl environments: bits64 alone is also set for x32.
{% unless flag?(:linux) && !flag?(:android) && flag?(:bits64) && (flag?(:gnu) || flag?(:musl)) && (flag?(:x86_64) || flag?(:aarch64)) %}
  {% raise "Linux kernel calls require non-Android LP64 GNU/musl Linux x86-64 or AArch64." %}
{% end %}

require "./result"

module Native::Kernel::Linux::Raw
  # Zero through six raw argument words. Callers supply valid kernel pointers,
  # capacities and lifetimes; all unused slots are zero. No retry or ownership
  # policy is applied, and the raw signed return word is retained on errors.
  def self.call(number : Int32, a0 : UInt64 = 0_u64, a1 : UInt64 = 0_u64,
                a2 : UInt64 = 0_u64, a3 : UInt64 = 0_u64,
                a4 : UInt64 = 0_u64, a5 : UInt64 = 0_u64) : Result
    Result.new(trap(number, a0, a1, a2, a3, a4, a5))
  end
end

{% if flag?(:x86_64) %}
  require "./syscall/x86_64"
  require "./raw/x86_64"
{% elsif flag?(:aarch64) %}
  require "./syscall/aarch64"
  require "./raw/aarch64"
{% end %}
