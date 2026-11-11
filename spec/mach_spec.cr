require "./spec_helper"

{% if flag?(:darwin) %}
  # Test-only FFI observes name-table growth; production has no FFI declarations.
  lib Names
    fun mach_port_names(task : UInt32, names : UInt32**, count : UInt32*, types : UInt32**, type_count : UInt32*) : Int32
    fun mach_vm_deallocate(task : UInt32, address : UInt64, size : UInt64) : Int32
  end

  module Fixture::Mach
    def self.names(task : UInt32) : UInt32
      names = Pointer(UInt32).null
      types = Pointer(UInt32).null
      count = 0_u32
      type_count = 0_u32
      Names.mach_port_names(task, pointerof(names), pointerof(count), pointerof(types), pointerof(type_count)).should eq(0)
      Names.mach_vm_deallocate(task, names.address, count.to_u64 * 4).should eq(0)
      Names.mach_vm_deallocate(task, types.address, type_count.to_u64 * 4).should eq(0)
      count
    end

    def self.reply : StaticArray(UInt32, 128)
      buffer = StaticArray(UInt32, 128).new(0_u32)
      buffer.to_unsafe[1] = 72_u32
      buffer.to_unsafe[5] = 3505_u32
      buffer.to_unsafe[7] = 1_u32
      buffer.to_unsafe[9] = 8_u32
      8.times { |offset| buffer.to_unsafe[10 + offset] = (offset + 100).to_u32 }
      buffer
    end
  end

  describe Native::Kernel::Darwin::Mach do
    it "selects the audited transport without changing the modern default" do
      Darwin::Mach.transport(21).should eq(Darwin::Mach::Transport::MachMsgTrap)
      [22, 23, 24, 25].each { |major| Darwin::Mach.transport(major).should eq(Darwin::Mach::Transport::MachMsg2) }
      [0, 20, 26].each { |major| Darwin::Mach.transport(major).should be_nil }
    end

    it "models interrupted exchanges without a speculative resend" do
      send = Darwin::Mach::ExchangePhase::SendAndReceive
      receive = Darwin::Mach::ExchangePhase::ReceiveOnly
      done = Darwin::Mach::ExchangePhase::Done
      Darwin::Mach.retry_phase(send, 0x10000007).should eq(send)
      Darwin::Mach.retry_phase(send, 0x10004005).should eq(receive)
      Darwin::Mach.retry_phase(receive, 0x10004005).should eq(receive)
      Darwin::Mach.retry_phase(receive, 0x10000007).should eq(done)
      Darwin::Mach.retry_phase(send, 0x10000003).should eq(done)
    end

    it "rejects controlled malformed task-info replies before copying a token" do
      buffer = Fixture::Mach.reply
      words, count, code = Darwin::Mach.decode_task_audit_reply(buffer.to_unsafe)
      {words[0], words[7], count, code}.should eq({100_u32, 107_u32, 8_u32, 0})

      buffer = Fixture::Mach.reply
      buffer.to_unsafe[0] = 0x80000000_u32
      _words, count, code = Darwin::Mach.decode_task_audit_reply(buffer.to_unsafe)
      {count, code}.should eq({0_u32, -300})

      buffer = Fixture::Mach.reply
      buffer.to_unsafe[5] = 3504_u32
      _words, count, code = Darwin::Mach.decode_task_audit_reply(buffer.to_unsafe)
      {count, code}.should eq({0_u32, -301})

      buffer = Fixture::Mach.reply
      buffer.to_unsafe[7] = 0_u32
      _words, count, code = Darwin::Mach.decode_task_audit_reply(buffer.to_unsafe)
      {count, code}.should eq({0_u32, -300})

      buffer = Fixture::Mach.reply
      buffer.to_unsafe[9] = 9_u32
      buffer.to_unsafe[1] = 76_u32
      _words, count, code = Darwin::Mach.decode_task_audit_reply(buffer.to_unsafe)
      {count, code}.should eq({9_u32, -307})

      buffer = Fixture::Mach.reply
      buffer.to_unsafe[1] = 68_u32
      _words, count, code = Darwin::Mach.decode_task_audit_reply(buffer.to_unsafe)
      {count, code}.should eq({8_u32, -300})
    end

    it "releases dedicated reply receive rights after success and invalid destinations" do
      transport = Darwin::Mach.transport(Darwin::Process.release).not_nil!
      task = Darwin::Mach.task
      begin
        before = Fixture::Mach.names(task)
        100.times do
          words, count, code = Darwin::Mach.read(task, task, transport)
          code.should eq(0)
          count.should eq(8)
          words[5].should eq(Process.pid)
          _words, count, code = Darwin::Mach.read(task, 0xfffffffe_u32, transport)
          code.should_not eq(0)
          count.should eq(0)
        end
        Fixture::Mach.names(task).should eq(before)
      ensure
        Darwin::Mach.release(task, task).should eq(0)
      end
    end
  end
{% end %}
