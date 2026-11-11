require "./spec_helper"

{% if flag?(:darwin) %}
  alias Accounting = Native::Kernel::Darwin

  describe "Darwin native64 collection and inspection ABI" do
    it "pins timeval and every rusage counter offset" do
      sizeof(Accounting::Resource::Time).should eq(16)
      offsetof(Accounting::Resource::Time, @seconds).should eq(0)
      offsetof(Accounting::Resource::Time, @microseconds).should eq(8)
      sizeof(Accounting::Resource::Usage).should eq(144)
      offsetof(Accounting::Resource::Usage, @user).should eq(0)
      offsetof(Accounting::Resource::Usage, @system).should eq(16)
      {% for field, index in {max_rss: 0, shared_memory: 1, data_memory: 2, stack_memory: 3, reclaims: 4, faults: 5, swaps: 6, input_blocks: 7, output_blocks: 8, sent: 9, received: 10, signals: 11, voluntary_switches: 12, involuntary_switches: 13} %}
        offsetof(Accounting::Resource::Usage, @{{field.id}}).should eq(32 + 8 * {{index}})
      {% end %}
    end

    it "pins siginfo including the full sigval word and reserved tail" do
      sizeof(Accounting::Signal::Info).should eq(104)
      {% for field, offset in {number: 0, error: 4, code: 8, pid: 12, uid: 16, status: 20, address: 24, value: 32, band: 40, reserved: 48} %}
        offsetof(Accounting::Signal::Info, @{{field.id}}).should eq({{offset}})
      {% end %}
    end

    it "pins task records and each explicit usage version boundary" do
      sizeof(Accounting::Process::Info::Task).should eq(96)
      offsetof(Accounting::Process::Info::Task, @virtual_size).should eq(0)
      offsetof(Accounting::Process::Info::Task, @threads_system).should eq(40)
      offsetof(Accounting::Process::Info::Task, @policy).should eq(48)
      offsetof(Accounting::Process::Info::Task, @priority).should eq(92)
      sizeof(Accounting::Process::Info::All).should eq(232)
      offsetof(Accounting::Process::Info::All, @task).should eq(136)
      sizeof(Accounting::Process::Usage::V0).should eq(96)
      sizeof(Accounting::Process::Usage::V1).should eq(144)
      sizeof(Accounting::Process::Usage::V2).should eq(160)
      {% for record in ["V0", "V1", "V2"] %}
        offsetof(Accounting::Process::Usage::{{record.id}}, @user_time).should eq(16)
        offsetof(Accounting::Process::Usage::{{record.id}}, @resident_size).should eq(64)
        offsetof(Accounting::Process::Usage::{{record.id}}, @start).should eq(80)
        offsetof(Accounting::Process::Usage::{{record.id}}, @exit).should eq(88)
      {% end %}
      offsetof(Accounting::Process::Usage::V1, @child_user_time).should eq(96)
      offsetof(Accounting::Process::Usage::V1, @child_elapsed).should eq(136)
      offsetof(Accounting::Process::Usage::V2, @child_user_time).should eq(96)
      offsetof(Accounting::Process::Usage::V2, @child_elapsed).should eq(136)
      offsetof(Accounting::Process::Usage::V2, @read_bytes).should eq(144)
      offsetof(Accounting::Process::Usage::V2, @written_bytes).should eq(152)
    end

    it "reads native self accounting and rejects an unsupported selector" do
      usage = Accounting::Resource::Usage.new
      result = Accounting::Resource.getrusage(Accounting::Resource::RUSAGE_SELF, pointerof(usage))
      result.error.should eq(0)
      result.primary.should eq(0)
      [usage.user, usage.system].each do |time|
        time.seconds.should be >= 0
        time.microseconds.should be >= 0
        time.microseconds.should be < 1_000_000
      end
      usage.max_rss.should be > 0
      usage.max_rss = -777_i64
      invalid = Accounting::Resource.getrusage(1, pointerof(usage))
      invalid.primary.should eq(-1)
      invalid.error.should eq(22)
      usage.max_rss.should eq(-777)
    end

    it "reads typed PID information and keeps versioned usage separate" do
      bsd = Accounting::Process::Info::Bsd.new
      task = Accounting::Process::Info::Task.new
      all = Accounting::Process::Info::All.new
      result = Accounting::Process.info(Process.pid.to_i32, pointerof(bsd))
      result.error.should eq(0)
      result.primary.should eq(136)
      bsd.pid.should eq(Process.pid)
      result = Accounting::Process.info(Process.pid.to_i32, pointerof(task))
      result.error.should eq(0)
      result.primary.should eq(96)
      task.threads.should be > 0
      result = Accounting::Process.info(Process.pid.to_i32, pointerof(all))
      result.error.should eq(0)
      result.primary.should eq(232)
      all.bsd.pid.should eq(Process.pid)
      usage = Accounting::Process::Usage::V2.new
      result = Accounting::Process.usage(Process.pid.to_i32, pointerof(usage))
      result.error.should eq(0)
      result.primary.should eq(0)
      usage.start.should be > 0
      usage.exit.should eq(0)
      usage.resident_size.should be > 0
    end
  end
{% end %}
