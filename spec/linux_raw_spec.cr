require "./spec_helper"
require "../src/native-kernel/linux/result"

describe Native::Kernel::Linux::Result do
  it "decodes exactly the negative errno interval without changing any bits" do
    {-4096_i64 => 0, -4095_i64 => 4095, -1_i64 => 1, 0_i64 => 0, 1_i64 => 0,
     Int64::MIN => 0, Int64::MAX => 0, -4097_i64 => 0}.each do |word, error|
      result = Native::Kernel::Linux::Result.new(word)
      result.primary.should eq(word)
      result.primary.to_u64!.should eq(word.to_u64!)
      result.error.should eq(error)
    end
  end

  it "decodes every word in the reserved errno interval" do
    (1..4095).each do |error|
      result = Native::Kernel::Linux::Result.new(-error.to_i64)
      result.primary.should eq(-error.to_i64)
      result.error.should eq(error)
    end
  end

  it "synthetically decodes EINTR, EAGAIN and ENOSYS (not a delivered signal)" do
    [4, 11, 38].each do |error|
      Native::Kernel::Linux::Result.new(-error.to_i64).error.should eq(error)
    end
  end
end

{% if flag?(:linux) && !flag?(:android) && flag?(:bits64) && (flag?(:gnu) || flag?(:musl)) && (flag?(:x86_64) || flag?(:aarch64)) %}
  require "../src/native-kernel/linux/raw"

  describe Native::Kernel::Linux::Raw do
    it "executes a native zero-argument syscall and retains a native ENOSYS" do
      result = Native::Kernel::Linux::Raw.call(Native::Kernel::Linux::Number::GETPID)
      result.primary.should eq(Process.pid)
      result.error.should eq(0)
      failed = Native::Kernel::Linux::Raw.call(-1)
      failed.primary.should eq(-38)
      failed.error.should eq(38)
    end
  end
{% end %}
