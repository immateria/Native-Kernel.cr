require "./spec_helper"

{% if flag?(:linux) && !flag?(:android) && flag?(:bits64) && (flag?(:gnu) || flag?(:musl)) && (flag?(:x86_64) || flag?(:aarch64)) %}
  require "../src/native-kernel/linux"
  alias LinuxKernel = Native::Kernel::Linux

  # offsetof of the second field is a floor-compatible alignment observation.
  # Crystal 1.10 has no alignof expression; the C oracle asserts _Alignof too.
  struct LinuxAlignment(T)
    @prefix : UInt8 = 0_u8
    @value : T

    def initialize(@value : T)
    end
  end

  describe "Linux LP64 kernel records (independently asserted by the C oracle)" do
    it "pins poll, timeout and kernel signal mask size/alignment/offsets" do
      sizeof(LinuxKernel::Event::Poll).should eq(8)
      offsetof(LinuxAlignment(LinuxKernel::Event::Poll), @value).should eq(4)
      offsetof(LinuxKernel::Event::Poll, @fd).should eq(0)
      offsetof(LinuxKernel::Event::Poll, @events).should eq(4)
      offsetof(LinuxKernel::Event::Poll, @revents).should eq(6)
      sizeof(LinuxKernel::Event::Timespec).should eq(16)
      offsetof(LinuxAlignment(LinuxKernel::Event::Timespec), @value).should eq(8)
      offsetof(LinuxKernel::Event::Timespec, @seconds).should eq(0)
      offsetof(LinuxKernel::Event::Timespec, @nanoseconds).should eq(8)
      sizeof(LinuxKernel::Signal::Set).should eq(8)
      offsetof(LinuxAlignment(LinuxKernel::Signal::Set), @value).should eq(8)
      offsetof(LinuxKernel::Signal::Set, @bits).should eq(0)
      LinuxKernel::Signal::SET_BYTES.should eq(8_u64)
    end

    it "pins full siginfo storage and only the accessed SIGCHLD fields" do
      sizeof(LinuxKernel::Signal::Info).should eq(128)
      offsetof(LinuxAlignment(LinuxKernel::Signal::Info), @value).should eq(8)
      {% for field, offset in {number: 0, error: 4, code: 8, reserved0: 12, pid: 16, uid: 20, status: 24, reserved1: 28, tail: 32} %}
        offsetof(LinuxKernel::Signal::Info, @{{field.id}}).should eq({{offset}})
      {% end %}
    end

    it "pins native timeval, every rusage field and prlimit64 limits" do
      sizeof(LinuxKernel::Resource::Timeval).should eq(16)
      offsetof(LinuxAlignment(LinuxKernel::Resource::Timeval), @value).should eq(8)
      offsetof(LinuxKernel::Resource::Timeval, @seconds).should eq(0)
      offsetof(LinuxKernel::Resource::Timeval, @microseconds).should eq(8)
      sizeof(LinuxKernel::Resource::Usage).should eq(144)
      offsetof(LinuxAlignment(LinuxKernel::Resource::Usage), @value).should eq(8)
      offsetof(LinuxKernel::Resource::Usage, @user).should eq(0)
      offsetof(LinuxKernel::Resource::Usage, @system).should eq(16)
      {% for field, index in {max_rss: 0, shared_memory: 1, data_memory: 2, stack_memory: 3, reclaims: 4, faults: 5, swaps: 6, input_blocks: 7, output_blocks: 8, sent: 9, received: 10, signals: 11, voluntary_switches: 12, involuntary_switches: 13} %}
        offsetof(LinuxKernel::Resource::Usage, @{{field.id}}).should eq(32 + 8 * {{index}})
      {% end %}
      sizeof(LinuxKernel::Resource::Limit).should eq(16)
      offsetof(LinuxAlignment(LinuxKernel::Resource::Limit), @value).should eq(8)
      offsetof(LinuxKernel::Resource::Limit, @soft).should eq(0)
      offsetof(LinuxKernel::Resource::Limit, @hard).should eq(8)
    end

    it "uses Linux wait and descriptor constants, not Darwin values" do
      LinuxKernel::Process::Wait::WNOWAIT.should eq(0x01000000)
      LinuxKernel::Process::Wait::WCONTINUED.should eq(8)
      LinuxKernel::Process::Wait::P_PIDFD.should eq(3)
      LinuxKernel::Descriptor::F_DUPFD_CLOEXEC.should eq(1030)
      LinuxKernel::Descriptor::O_CLOEXEC.should eq(0x80000)
      LinuxKernel::Pidfd::NONBLOCK.should eq(0x800_u32)
      LinuxKernel::Resource::RLIM_INFINITY.should eq(UInt64::MAX)
    end
  end

  describe "Linux managed caller smoke (no raw process creation in Crystal specs)" do
    it "queries process identity, numeric signal zero and native refusals" do
      LinuxKernel::Process.pid.primary.should eq(Process.pid)
      LinuxKernel::Process.parent.primary.should eq(Process.ppid)
      LinuxKernel::Process.getpgid.primary.should eq(Process.pgid)
      LinuxKernel::Process.getsid.error.should eq(0)
      LinuxKernel::Process.kill(Process.pid.to_i32!, 0).error.should eq(0)
      LinuxKernel::Process.getpgid(-1).error.should eq(3)
      LinuxKernel::Process.setpgid(-1, 0).error.should eq(22)
    end

    it "round-trips caller-owned buffers and leaves resource cleanup to the caller" do
      fds = StaticArray(Int32, 2).new(-777)
      result = LinuxKernel::Descriptor.pipe2(fds.to_unsafe, LinuxKernel::Descriptor::O_CLOEXEC | LinuxKernel::Descriptor::O_NONBLOCK)
      result.error.should eq(0)
      result.primary.should eq(0)
      if result.error == 0
        reader, writer = fds.to_unsafe[0], fds.to_unsafe[1]
        begin
          byte = 0_u8
          failed = LinuxKernel::Descriptor.read(reader, pointerof(byte), 1_u64)
          failed.error.should eq(11)
          failed.primary.should eq(-11)
          byte = 73_u8
          LinuxKernel::Descriptor.write(writer, pointerof(byte), 1_u64).primary.should eq(1)
          byte = 0_u8
          LinuxKernel::Descriptor.read(reader, pointerof(byte), 1_u64).primary.should eq(1)
          byte.should eq(73_u8)
        ensure
          LinuxKernel::Descriptor.close(reader).error.should eq(0)
          LinuxKernel::Descriptor.close(writer).error.should eq(0)
        end
      end
    end

    it "queries self usage and limits without an external PID snapshot claim" do
      usage = LinuxKernel::Resource::Usage.new
      LinuxKernel::Resource.getrusage(LinuxKernel::Resource::RUSAGE_SELF, pointerof(usage)).error.should eq(0)
      usage.user.microseconds.should be >= 0
      usage.user.microseconds.should be < 1_000_000
      limit = LinuxKernel::Resource::Limit.new
      LinuxKernel::Resource.prlimit64(0, LinuxKernel::Resource::RLIMIT_NOFILE, Pointer(LinuxKernel::Resource::Limit).null, pointerof(limit)).error.should eq(0)
      limit.hard.should be >= limit.soft
    end
  end
{% end %}
