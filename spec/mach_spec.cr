require "./spec_helper"

{% if flag?(:darwin) %}
  # Test-only FFI observes name-table growth; production has no FFI declarations.
  lib Names
    fun mach_port_names(task : UInt32, names : UInt32**, count : UInt32*, types : UInt32**, type_count : UInt32*) : Int32
    fun mach_vm_deallocate(task : UInt32, address : UInt64, size : UInt64) : Int32
  end

  module Native::Kernel::Darwin::Mach
    def self.fixture_decode_port_names_reply(buffer : Pointer(UInt32))
      decode_port_names_reply(buffer)
    end

    def self.fixture_received_mappings(buffer : Pointer(UInt32))
      addresses = StaticArray(UInt64, 30).new(0_u64)
      sizes = StaticArray(UInt64, 30).new(0_u64)
      count, code = received_port_names_mappings(buffer, addresses.to_unsafe, sizes.to_unsafe)
      {addresses, sizes, count, code}
    end

    def self.fixture_finish_port_names(task : UInt32, buffer : Pointer(UInt32), code : Int32 = 0, cleanup : Int32 = 0)
      finish_port_names_reply(task, buffer, code, cleanup)
    end
  end

  module Fixture::Mach
    VM_BYTES = 65536_u64

    def self.allocate(task : UInt32, requested : UInt64 = 0_u64) : UInt64
      address = requested
      result = Darwin::Raw.call(-10, task.to_u64, pointerof(address).address, VM_BYTES, requested == 0 ? 1_u64 : 0_u64)
      raise "VM fixture allocation failed: #{result.primary}" unless result.primary == 0
      address
    end

    def self.release(task : UInt32, address : UInt64)
      Darwin::Raw.call(-12, task.to_u64, address, VM_BYTES).primary.should eq(0)
    end

    def self.reclaim(task : UInt32, address : UInt64)
      # FIXED without OVERWRITE fails if the previous mapping still exists.
      # Own only a confirmed successful replacement, never a failed request.
      replacement = allocate(task, address)
      begin
        replacement.should eq(address)
      ensure
        release(task, replacement)
      end
    end

    def self.port_names_reply(first : UInt64 = 0x1234_u64, second : UInt64 = 0x30000_u64)
      buffer = StaticArray(UInt32, 128).new(0_u32)
      buffer[0] = 0x80000000_u32
      buffer[1] = 76_u32
      buffer[5] = 3300_u32
      buffer[6] = 2_u32
      buffer[7] = first.to_u32!
      buffer[8] = first.unsafe_shr(32).to_u32!
      buffer[9] = 0x01000101_u32 # OOL, virtual copy, received deallocation
      buffer[10] = VM_BYTES.to_u32!
      buffer[11] = second.to_u32!
      buffer[12] = second.unsafe_shr(32).to_u32!
      buffer[13] = 0x01000101_u32
      buffer[14] = VM_BYTES.to_u32!
      buffer[16] = 1_u32
      buffer[17] = (VM_BYTES // 4).to_u32!
      buffer[18] = buffer[17]
      buffer
    end

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
    it "rejects a successful code in a simple port-names error envelope" do
      buffer = StaticArray(UInt32, 128).new(0_u32)
      buffer[1] = 36_u32
      buffer[5] = 3300_u32
      buffer[7] = 1_u32
      decoded = Darwin::Mach.fixture_decode_port_names_reply(buffer.to_unsafe)
      decoded[5].should eq(-300)
      buffer[8] = 5_u32
      Darwin::Mach.fixture_decode_port_names_reply(buffer.to_unsafe)[5].should eq(5)
    end

    it "retains descriptor ownership independently of invalid MIG fields" do
      3.times do |fault|
        buffer = Fixture::Mach.port_names_reply
        case fault
        when 0 then buffer[5] = 3299_u32
        when 1 then buffer[16] = 0_u32
        when 2 then buffer[17] = UInt32::MAX
        end
        addresses, sizes, count, code = Darwin::Mach.fixture_received_mappings(buffer.to_unsafe)
        {count, code}.should eq({2_u32, 0})
        addresses.to_a.first(2).should eq([0x1234_u64, 0x30000_u64])
        sizes.to_a.first(2).should eq([Fixture::Mach::VM_BYTES, Fixture::Mach::VM_BYTES])
        Darwin::Mach.fixture_decode_port_names_reply(buffer.to_unsafe)[5].should_not eq(0)
      end
    end

    it "coalesces duplicate and overlapping offset mappings without page-alignment assumptions" do
      [0x1234_u64, 0x1235_u64].each do |second|
        buffer = Fixture::Mach.port_names_reply(0x1234_u64, second)
        addresses, sizes, count, code = Darwin::Mach.fixture_received_mappings(buffer.to_unsafe)
        {count, code}.should eq({1_u32, 0})
        addresses[0].should eq(0x1234_u64)
        sizes[0].should eq(Fixture::Mach::VM_BYTES + second - 0x1234_u64)
      end
    end

    it "keeps valid mappings and reports unsupported or overflowing ownership" do
      buffer = Fixture::Mach.port_names_reply(UInt64::MAX - 1, 0x30000_u64)
      addresses, _sizes, count, code = Darwin::Mach.fixture_received_mappings(buffer.to_unsafe)
      {count, code, addresses[0]}.should eq({1_u32, 4, 0x30000_u64})
      [0x02000101_u32, 0x01000100_u32].each do |flags|
        buffer = Fixture::Mach.port_names_reply
        buffer[9] = flags
        addresses, _sizes, count, code = Darwin::Mach.fixture_received_mappings(buffer.to_unsafe)
        {count, code, addresses[0]}.should eq({1_u32, 4, 0x30000_u64})
        Darwin::Mach.fixture_decode_port_names_reply(buffer.to_unsafe)[5].should eq(-300)
      end
      buffer = Fixture::Mach.port_names_reply
      buffer[1] = 48_u32 # first complete descriptor, truncated second
      addresses, _sizes, count, code = Darwin::Mach.fixture_received_mappings(buffer.to_unsafe)
      {count, code, addresses[0]}.should eq({1_u32, 4, 0x1234_u64})
    end

    it "does not read an unreceived buffer and preserves both operation and cleanup errors" do
      Darwin::Mach.fixture_finish_port_names(0_u32, Pointer(UInt32).null, 0x1000400b, 23).should eq({0_u32, 0x1000400b, 23})
    end

    it "retains the first mapping when partial copyout leaves the second descriptor empty" do
      buffer = Fixture::Mach.port_names_reply
      buffer[11] = 0_u32
      buffer[12] = 0_u32
      buffer[14] = 0_u32
      addresses, sizes, count, code = Darwin::Mach.fixture_received_mappings(buffer.to_unsafe)
      {count, code, addresses[0], sizes[0]}.should eq({1_u32, 0, 0x1234_u64, Fixture::Mach::VM_BYTES})
    end

    it "releases both owned mappings after semantic rejection and partial receive errors" do
      task = Darwin::Mach.task
      begin
        5.times do |fault|
          owned = [] of UInt64
          begin
            first = Fixture::Mach.allocate(task)
            owned << first
            second = Fixture::Mach.allocate(task)
            owned << second
            buffer = Fixture::Mach.port_names_reply(first, second)
            raw_error = 0
            reply_cleanup = 0
            case fault
            when 0 then buffer[5] = 3299_u32
            when 1 then buffer[16] = 0_u32
            when 2 then buffer[17] = UInt32::MAX
            when 3 then raw_error = 0x1000420c # body error plus copyout status
            when 4
              buffer[16] = 0_u32
              reply_cleanup = 23
            end
            # Transfer ownership to the private received-reply cleanup path;
            # never retry disposal after an uncertain native result.
            owned.clear
            count, code, cleanup = Darwin::Mach.fixture_finish_port_names(task, buffer.to_unsafe, raw_error, reply_cleanup)
            count.should eq(0_u32)
            code.should eq(raw_error) if raw_error != 0
            code.should_not eq(0)
            cleanup.should eq(reply_cleanup)
            Fixture::Mach.reclaim(task, first)
            Fixture::Mach.reclaim(task, second)
          ensure
            owned.each { |address| Fixture::Mach.release(task, address) }
          end
        end
      ensure
        Darwin::Mach.release(task, task).should eq(0)
      end
    end

    it "releases a later known mapping after the first descriptor has unsupported ownership" do
      task = Darwin::Mach.task
      second = Fixture::Mach.allocate(task)
      begin
        # Never ask native code to dispose this synthetic borrowed address.
        # Only the second descriptor transfers a real owned mapping.
        buffer = Fixture::Mach.port_names_reply(0x1234_u64, second)
        buffer[9] = 0x01000100_u32
        addresses, _sizes, owned, ownership_error = Darwin::Mach.fixture_received_mappings(buffer.to_unsafe)
        {owned, ownership_error, addresses[0]}.should eq({1_u32, 4, second})
        count, code, cleanup = Darwin::Mach.fixture_finish_port_names(task, buffer.to_unsafe)
        count.should eq(0_u32)
        code.should eq(-300)
        cleanup.should_not eq(0)
        Fixture::Mach.reclaim(task, second)
      ensure
        # The received-reply path consumed mapping ownership. Never repeat an
        # uncertain disposal through the original address.
        Darwin::Mach.release(task, task).should eq(0)
      end
    end

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

    it "returns a deterministic native failure for an unchecked transport value" do
      task = Darwin::Mach.task
      begin
        unchecked = 99_i32.unsafe_as(Darwin::Mach::Transport)
        _words, count, code = Darwin::Mach.read(task, task, unchecked)
        count.should eq(0_u32)
        code.should eq(4)
      ensure
        Darwin::Mach.release(task, task).should eq(0)
      end
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
