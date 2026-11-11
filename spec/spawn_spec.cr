require "./spec_helper"

{% if flag?(:darwin) %}
  describe "Darwin spawn profiles" do
    it "encodes the fixed native64 buffer boundaries for audited releases" do
      {% if Native::Kernel::Darwin.has_constant?(:Spawn) %}
        [24, 25].each do |major|
          profile = Native::Kernel::Darwin::Spawn.profile(major).not_nil!
          {profile.attributes_size, profile.descriptor_size, profile.actions_header_size,
           profile.action_size, profile.path_capacity}.should eq({192, 144, 8, 1040, 1024})
          {profile.flags_offset, profile.defaults_offset, profile.mask_offset}.should eq({0, 4, 8})
          {profile.descriptor_attribute_size_offset, profile.descriptor_attributes_offset,
           profile.descriptor_actions_size_offset, profile.descriptor_actions_offset}.should eq({0, 8, 16, 24})
          {profile.actions_capacity_offset, profile.actions_count_offset}.should eq({0, 4})
          {profile.action_type_offset, profile.action_fd_offset, profile.action_destination_offset,
           profile.open_flags_offset, profile.open_mode_offset, profile.open_path_offset,
           profile.chdir_path_offset}.should eq({0, 4, 8, 8, 12, 14, 8})
        end
      {% else %}
        fail "the audited Darwin spawn profiles are unavailable"
      {% end %}
    end

    it "refuses releases outside the audited private ABI profiles" do
      {% if Native::Kernel::Darwin.has_constant?(:Spawn) %}
        [0, 23, 26].each { |major| Native::Kernel::Darwin::Spawn.profile(major).should be_nil }
      {% else %}
        fail "the audited Darwin spawn profiles are unavailable"
      {% end %}
    end

    it "preserves spawn errno and leaves child output untouched on failure" do
      {% if Native::Kernel::Darwin.has_constant?(:Spawn) %}
        child = 0
        result = Native::Kernel::Darwin::Spawn.create(pointerof(child), Pointer(UInt8).null, Pointer(Void).null,
          Pointer(Pointer(UInt8)).null, Pointer(Pointer(UInt8)).null)
        result.primary.should eq(-1)
        result.error.should eq(14) # EFAULT
        child.should eq(0)
      {% else %}
        fail "the typed Darwin spawn entry is unavailable"
      {% end %}
    end
  end
{% end %}
