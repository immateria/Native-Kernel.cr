require "./spec_helper"

{% if flag?(:darwin) %}
  module Behavior
    alias Darwin = Native::Kernel::Darwin
  end

  require "./native/behavior/mach_send_timeout"

  module Behavior
    class MachSendScript
      property copy_fail_at : Int32?
      property copy_fail_result = 0x10000003
      property copy_fail_restored = false
      property copy_fail_ambiguous = false
      property move_result = 0x10000004
      property receive_result = 0
      property receive_valid = true
      property receive_cleanup_result = 0
      property task_cleanup_result = 0
      property allocate_result = 0
      property insert_result = 0
      property task_value = 41_i64
      property destination = 42_u32

      getter ref_scripts = [
        {1_u32, 0, true},
        {2_u32, 0, true},
        {1_u32, 0, true},
        {1_u32, 0, true},
      ]
      getter reply_cleanup_results = [] of Int32
      getter destination_release_results = [] of Int32
      getter events = [] of String
      getter reply_receive_calls = 0
      getter get_refs_calls = 0
      getter reply_remove_calls = 0
      getter destination_remove_calls = 0
      getter copy_send_calls = 0
      getter move_send_calls = 0
      getter receive_calls = 0
      getter destination_release_calls = 0
      getter task_release_calls = 0

      def task_self : Int64
        @events << "task-self"
        @task_value
      end

      def allocate_receive(task : UInt32, output : Pointer(UInt32)) : Int32
        @events << "allocate"
        output.value = @destination if @allocate_result == 0
        @allocate_result
      end

      def insert_send(task : UInt32, destination : UInt32) : Int32
        @events << "insert"
        @insert_result
      end

      def reply_receive : Int64
        @events << "reply"
        reply = 100_i64 + @reply_receive_calls
        @reply_receive_calls += 1
        reply
      end

      def get_refs_exchange(words : Pointer(UInt32), task : UInt32, reply : UInt32) : Int32
        @events << "get-refs"
        script = @ref_scripts[@get_refs_calls]? || {0_u32, -302, false}
        @get_refs_calls += 1
        refs, operation, valid = script
        if operation == 0
          words[0] = 0_u32
          words[1] = valid ? 40_u32 : 39_u32
          words[2] = 0_u32
          words[5] = 3307_u32
          words[6] = 0_u32
          words[7] = 1_u32
          words[8] = 0_u32
          words[9] = refs
        end
        operation
      end

      def remove_receive(task : UInt32, name : UInt32) : Int32
        if name == @destination
          @events << "remove-destination"
          @destination_remove_calls += 1
          @receive_cleanup_result
        else
          @events << "remove-reply"
          index = @reply_remove_calls
          @reply_remove_calls += 1
          @reply_cleanup_results[index]? || 0
        end
      end

      def send_message(words : Pointer(UInt32), destination : UInt32,
                       disposition : UInt32, identifier : UInt32) : Int32
        if disposition == 19_u32
          @events << "copy-send"
          @copy_send_calls += 1
          if @copy_fail_at == @copy_send_calls
            if @copy_fail_ambiguous
              words[0] = 0_u32
            elsif @copy_fail_restored
              words[0] = 17_u32
            end
            return @copy_fail_result
          end
          if @copy_send_calls == 6
            words[0] = 17_u32
            return 0x10000004
          end
          return 0
        end

        @events << "move-send"
        @move_send_calls += 1
        @move_result
      end

      def receive_message(words : Pointer(UInt32), destination : UInt32) : Int32
        @events << "receive"
        @receive_calls += 1
        if @receive_result == 0
          words[0] = @receive_valid ? 0_u32 : 0x80000000_u32
          words[1] = 28_u32
          words[5] = 0x5101_u32
          words[6] = 0x6101_u32
        end
        @receive_result
      end

      def release_send(task : UInt32, name : UInt32) : Int32
        if name == @destination
          @events << "release-destination"
          index = @destination_release_calls
          @destination_release_calls += 1
          @destination_release_results[index]? || 0
        else
          @events << "release-task"
          @task_release_calls += 1
          @task_cleanup_result
        end
      end
    end
  end

  describe "Mach send-timeout ownership state" do
    it "distinguishes pre-copyin and post-copyin COPY_SEND failures" do
      Behavior.mach_copy_send_ownership(true, false, true, 1_u32).should eq(Behavior::MachSendOwnership::None)
      Behavior.mach_copy_send_ownership(false, true, true, 2_u32).should eq(Behavior::MachSendOwnership::Owned)
    end

    it "keeps malformed or uncounted COPY_SEND restoration uncertain" do
      Behavior.mach_copy_send_ownership(false, false, true, 1_u32).should eq(Behavior::MachSendOwnership::Uncertain)
      Behavior.mach_copy_send_ownership(false, true, true, 1_u32).should eq(Behavior::MachSendOwnership::Uncertain)
      Behavior.mach_copy_send_ownership(true, false, true, 2_u32).should eq(Behavior::MachSendOwnership::Uncertain)
      Behavior.mach_copy_send_ownership(false, true, false, 2_u32).should eq(Behavior::MachSendOwnership::Uncertain)
      Behavior.mach_copy_send_ownership(false, true, true, 3_u32).should eq(Behavior::MachSendOwnership::Uncertain)
    end

    it "releases MOVE_SEND only after exact timeout restoration" do
      timeout = 0x10000004
      Behavior.mach_move_send_ownership(0, false, false, 0_u32).should eq(Behavior::MachSendOwnership::Consumed)
      Behavior.mach_move_send_ownership(timeout, true, true, 1_u32).should eq(Behavior::MachSendOwnership::Owned)
      Behavior.mach_move_send_ownership(timeout, false, true, 1_u32).should eq(Behavior::MachSendOwnership::Uncertain)
      Behavior.mach_move_send_ownership(timeout, true, false, 1_u32).should eq(Behavior::MachSendOwnership::Uncertain)
      Behavior.mach_move_send_ownership(timeout, true, true, 2_u32).should eq(Behavior::MachSendOwnership::Uncertain)
      Behavior.mach_move_send_ownership(0x10000003, true, true, 1_u32).should eq(Behavior::MachSendOwnership::Uncertain)
    end

    it "distinguishes exact original and restored headers" do
      words = StaticArray(UInt32, 32).new(0_u32)
      words[0] = 19_u32
      words[1] = 28_u32
      words[2] = 41_u32
      words[5] = 0x5200_u32
      words[6] = 0x6200_u32
      Behavior.mach_send_header_states(words.to_unsafe, 41_u32, 0x5200_u32, 0x6200_u32).should eq({true, false})
      words[0] = 17_u32
      Behavior.mach_send_header_states(words.to_unsafe, 41_u32, 0x5200_u32, 0x6200_u32).should eq({false, true})
      words[3] = 1_u32
      Behavior.mach_send_header_states(words.to_unsafe, 41_u32, 0x5200_u32, 0x6200_u32).should eq({false, false})
    end

    it "decodes only the exact get-refs success and error forms" do
      words = StaticArray(UInt32, 32).new(0_u32)
      words[1] = 40_u32
      words[5] = 3307_u32
      words[7] = 1_u32
      words[9] = 2_u32
      Behavior.mach_get_refs_reply(words.to_unsafe).should eq({2_u32, 0, true})

      words[1] = 36_u32
      words[8] = 4_u32
      Behavior.mach_get_refs_reply(words.to_unsafe).should eq({0_u32, 4, false})
      words[8] = 0_u32
      Behavior.mach_get_refs_reply(words.to_unsafe).should eq({0_u32, -302, false})
    end

    it "rejects malformed get-refs envelopes" do
      valid = StaticArray(UInt32, 32).new(0_u32)
      valid[1] = 40_u32
      valid[5] = 3307_u32
      valid[7] = 1_u32

      words = valid
      words[0] = 0x80000000_u32
      Behavior.mach_get_refs_reply(words.to_unsafe)[2].should be_false
      words = valid
      words[2] = 1_u32
      Behavior.mach_get_refs_reply(words.to_unsafe)[2].should be_false
      words = valid
      words[5] = 1_u32
      Behavior.mach_get_refs_reply(words.to_unsafe)[2].should be_false
      words = valid
      words[6] = 1_u32
      Behavior.mach_get_refs_reply(words.to_unsafe)[2].should be_false
      words = valid
      words[7] = 2_u32
      Behavior.mach_get_refs_reply(words.to_unsafe)[2].should be_false
      words = valid
      words[8] = 1_u32
      Behavior.mach_get_refs_reply(words.to_unsafe)[2].should be_false
      words = valid
      words[1] = 39_u32
      Behavior.mach_get_refs_reply(words.to_unsafe)[2].should be_false
    end

    it "rejects a malformed received filler" do
      words = StaticArray(UInt32, 32).new(0_u32)
      words[1] = 28_u32
      words[5] = 0x5101_u32
      words[6] = 0x6101_u32
      Behavior.mach_received_filler(words.to_unsafe).should be_true
      words[0] = 0x80000000_u32
      Behavior.mach_received_filler(words.to_unsafe).should be_false
      words[0] = 0_u32
      words[1] = 27_u32
      Behavior.mach_received_filler(words.to_unsafe).should be_false
      words[1] = 28_u32
      words[5] = 0_u32
      Behavior.mach_received_filler(words.to_unsafe).should be_false
      words[5] = 0x5101_u32
      words[6] = 0_u32
      Behavior.mach_received_filler(words.to_unsafe).should be_false
    end

    it "keeps every cleanup failure distinct from the primary result" do
      Behavior.mach_cleanup_result(193, 0, 0, 0, 0, 0).should eq(193)
      Behavior.mach_cleanup_result(193, 1, 0, 0, 0, 0).should eq(230)
      Behavior.mach_cleanup_result(193, 0, 1, 0, 0, 0).should eq(231)
      Behavior.mach_cleanup_result(193, 0, 0, 1, 0, 0).should eq(232)
      Behavior.mach_cleanup_result(193, 0, 0, 0, 1, 0).should eq(233)
      Behavior.mach_cleanup_result(193, 0, 0, 0, 0, 1).should eq(234)
    end

    it "runs the successful ownership and cleanup sequence exactly once" do
      ops = Behavior::MachSendScript.new
      Behavior.mach_send_timeout_with(ops).should eq(0)
      ops.copy_send_calls.should eq(6)
      ops.move_send_calls.should eq(1)
      ops.receive_calls.should eq(1)
      ops.get_refs_calls.should eq(4)
      ops.reply_remove_calls.should eq(4)
      ops.destination_release_calls.should eq(2)
      ops.destination_remove_calls.should eq(1)
      ops.task_release_calls.should eq(1)
      ops.events.last(4).should eq([
        "receive",
        "release-destination",
        "remove-destination",
        "release-task",
      ])
    end

    it "distinguishes pre-copyin filler failure cleanup" do
      ops = Behavior::MachSendScript.new
      ops.copy_fail_at = 1
      ops.ref_scripts.replace([{1_u32, 0, true}, {1_u32, 0, true}])
      Behavior.mach_send_timeout_with(ops).should eq(176)
      ops.destination_release_calls.should eq(1)
      ops.destination_remove_calls.should eq(1)
      ops.task_release_calls.should eq(1)
    end

    it "releases an exact post-copyin filler restoration separately" do
      ops = Behavior::MachSendScript.new
      ops.copy_fail_at = 1
      ops.copy_fail_restored = true
      ops.ref_scripts.replace([{1_u32, 0, true}, {2_u32, 0, true}])
      Behavior.mach_send_timeout_with(ops).should eq(176)
      ops.destination_release_calls.should eq(2)
      ops.destination_remove_calls.should eq(1)
      ops.task_release_calls.should eq(1)
    end

    it "does not guess cleanup for ambiguous filler restoration" do
      ops = Behavior::MachSendScript.new
      ops.copy_fail_at = 1
      ops.copy_fail_ambiguous = true
      ops.ref_scripts.replace([{1_u32, 0, true}, {2_u32, 0, true}])
      Behavior.mach_send_timeout_with(ops).should eq(176)
      ops.destination_release_calls.should eq(1)
      ops.destination_remove_calls.should eq(1)
      ops.task_release_calls.should eq(1)
    end

    it "does not release a MOVE_SEND reference consumed by success" do
      ops = Behavior::MachSendScript.new
      ops.move_result = 0
      Behavior.mach_send_timeout_with(ops).should eq(186)
      ops.destination_release_calls.should eq(1)
      ops.receive_calls.should eq(0)
      ops.destination_remove_calls.should eq(1)
      ops.task_release_calls.should eq(1)
    end

    it "preserves uncertain MOVE_SEND restoration after a failed refs query" do
      ops = Behavior::MachSendScript.new
      ops.ref_scripts.replace([
        {1_u32, 0, true},
        {2_u32, 0, true},
        {1_u32, 0, true},
        {0_u32, 0, false},
      ])
      Behavior.mach_send_timeout_with(ops).should eq(189)
      ops.destination_release_calls.should eq(1)
      ops.receive_calls.should eq(0)
      ops.destination_remove_calls.should eq(1)
      ops.task_release_calls.should eq(1)
    end

    it "rejects a malformed initial RPC reply and still cleans known ownership" do
      ops = Behavior::MachSendScript.new
      ops.ref_scripts.replace([{0_u32, 0, false}])
      Behavior.mach_send_timeout_with(ops).should eq(173)
      ops.copy_send_calls.should eq(0)
      ops.destination_release_calls.should eq(1)
      ops.destination_remove_calls.should eq(1)
      ops.task_release_calls.should eq(1)
    end

    it "preserves receive failure beside complete known cleanup" do
      ops = Behavior::MachSendScript.new
      ops.receive_result = 5
      Behavior.mach_send_timeout_with(ops).should eq(192)
      ops.destination_release_calls.should eq(2)
      ops.destination_remove_calls.should eq(1)
      ops.task_release_calls.should eq(1)
    end

    it "surfaces every injected cleanup failure from the wired fixture" do
      reply = Behavior::MachSendScript.new
      reply.reply_cleanup_results << 7
      Behavior.mach_send_timeout_with(reply).should eq(230)

      extra = Behavior::MachSendScript.new
      extra.destination_release_results.concat([7, 0])
      Behavior.mach_send_timeout_with(extra).should eq(231)
      extra.destination_release_calls.should eq(2)

      send = Behavior::MachSendScript.new
      send.destination_release_results.concat([0, 7])
      Behavior.mach_send_timeout_with(send).should eq(232)
      send.destination_release_calls.should eq(2)

      receive = Behavior::MachSendScript.new
      receive.receive_cleanup_result = 7
      Behavior.mach_send_timeout_with(receive).should eq(233)
      receive.destination_remove_calls.should eq(1)

      task = Behavior::MachSendScript.new
      task.task_cleanup_result = 7
      Behavior.mach_send_timeout_with(task).should eq(234)
      task.task_release_calls.should eq(1)
    end
  end
{% end %}
