require "./spec_helper"

{% if flag?(:darwin) %}
  describe Native::Kernel::Darwin do
    it "pins ABI record sizes and kevent offsets" do
      sizeof(Darwin::Event::Kevent64).should eq(48)
      offsetof(Darwin::Event::Kevent64, @filter).should eq(8)
      offsetof(Darwin::Event::Kevent64, @data).should eq(16)
      offsetof(Darwin::Event::Kevent64, @ext).should eq(32)
      sizeof(Darwin::Process::Info::Short).should eq(64)
      sizeof(Darwin::Process::Info::Bsd).should eq(136)
      sizeof(Darwin::Process::Info::Unique).should eq(56)
      sizeof(Darwin::Process::Info::Record).should eq(192)
      sizeof(Darwin::Resource::Limit).should eq(16)
      sizeof(Darwin::Signal::Action).should eq(24)
      sizeof(Darwin::Event::Poll).should eq(8)
      sizeof(Darwin::Event::Timeout).should eq(16)
    end

    it "reports readable data through mutable poll records" do
      pipe = Darwin::Descriptor.pipe
      pipe.error.should eq(0)
      begin
        event = Darwin::Event::Poll.new(pipe.primary.to_i32!)
        Darwin::Event.poll(pointerof(event), 1_u32, 0).primary.should eq(0)
        event.revents.should eq(0)
        byte = 7_u8
        Darwin::Descriptor.write(pipe.secondary.to_i32!, pointerof(byte), 1_u64).primary.should eq(1)
        Darwin::Event.poll(pointerof(event), 1_u32, 0).primary.should eq(1)
        event.fd.should eq(pipe.primary)
        (event.revents & 1).should eq(1)
      ensure
        Darwin::Descriptor.close(pipe.primary.to_i32!).error.should eq(0)
        Darwin::Descriptor.close(pipe.secondary.to_i32!).error.should eq(0)
      end
    end

    it "queries release, process records and limits without cached context" do
      Darwin::Process.pid.primary.should eq(Process.pid)
      Darwin::Process.parent.primary.should eq(Process.ppid)
      Darwin::Process.release.should be > 0
      record = Darwin::Process::Info::Short.new
      result = Darwin::Process.info(Process.pid.to_i32, Darwin::Process::Info::PIDT_SHORTBSDINFO, 0_u64, pointerof(record).as(Void*), sizeof(typeof(record)))
      result.error.should eq(0)
      result.primary.should eq(sizeof(typeof(record)))
      record.pid.should eq(Process.pid)
      limit = Darwin::Resource::Limit.new
      Darwin::Resource.get(8, pointerof(limit)).error.should eq(0)
      limit.soft.should be > 0
      limit.hard.should be >= limit.soft
    end
  end
{% end %}
