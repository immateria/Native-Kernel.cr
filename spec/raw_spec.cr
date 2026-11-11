require "./spec_helper"

{% if flag?(:darwin) %}
  alias Darwin = Native::Kernel::Darwin

  describe Darwin::Raw do
    it "preserves BSD values and canonical errno failures" do
      result = Darwin::Raw.call(20)
      result.error.should eq(0)
      result.primary.should eq(Process.pid)
      failed = Darwin::Raw.call(3, UInt64::MAX, 0_u64, 1_u64)
      failed.primary.should eq(-1)
      failed.error.should eq(Errno::EBADF.value)
    end

    it "preserves both native pipe descriptors" do
      result = Darwin::Raw.call(42)
      result.error.should eq(0)
      begin
        byte = 79_u8
        Darwin::Descriptor.write(result.secondary.to_i32!, pointerof(byte), 1_u64).primary.should eq(1)
        byte = 0_u8
        Darwin::Descriptor.read(result.primary.to_i32!, pointerof(byte), 1_u64).primary.should eq(1)
        byte.should eq(79_u8)
      ensure
        Darwin::Descriptor.close(result.primary.to_i32!).error.should eq(0)
        Darwin::Descriptor.close(result.secondary.to_i32!).error.should eq(0)
      end
    end

    it "retains Mach return codes separately from BSD errno" do
      task = Darwin::Mach.task
      begin
        failed = Darwin::Raw.call(-18, task.to_u64, 0xfffffffe_u64)
        failed.error.should eq(0)
        failed.primary.should_not eq(0)
      ensure
        Darwin::Mach.release(task, task).should eq(0)
      end
    end

    it "passes distinct seventh and eighth BSD arguments" do
      Darwin::Raw.call(374, UInt64::MAX).error.should eq(Errno::EBADF.value)
      seventh = Darwin::Raw.call(374, UInt64::MAX, 0_u64, 0_u64, 0_u64, 0_u64, 1_u64, 1_u64, 0_u64)
      seventh.primary.should eq(-1)
      seventh.error.should eq(Errno::EFAULT.value)
      eighth = Darwin::Raw.call(374, UInt64::MAX, 0_u64, 0_u64, 0_u64, 0_u64, 0_u64, 0_u64, 0x400_u64)
      eighth.primary.should eq(-1)
      eighth.error.should eq(Errno::EINVAL.value)
    end
  end
{% end %}
