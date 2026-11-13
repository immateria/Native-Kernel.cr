require "./spec_helper"

{% if flag?(:darwin) %}
  module Behavior
    alias Darwin = Native::Kernel::Darwin
  end

  require "./native/behavior/mach_send_timeout"

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
  end
{% end %}
