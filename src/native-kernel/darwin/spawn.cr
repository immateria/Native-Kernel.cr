require "./raw"

module Native::Kernel::Darwin::Spawn
  # The Darwin 21 native64 constants below were audited on 2026-11-11 from
  # Apple XNU xnu-8020.140.41 (27b03b360a988dfd3dfdf34262bb0042026747cc).
  # They deliberately remain distinct from the Darwin 24/25 layout: Darwin 21
  # copies only the prefix ending at psa_ports and has an eight-pair descriptor.
  # The retained Darwin 24/25 constants were audited from xnu-11417.101.15
  # (e3723e1f17661b24996789d8afc084c0c3303b26) and xnu-12377.121.6
  # (ac9718fb1af618d5ce8678d0dc6e8a58f252216f). See the Monterey audit for
  # immutable source bytes and layout gates.
  enum Layout
    Darwin21
    Darwin24And25
  end

  struct Profile
    getter major : Int32
    getter layout : Layout

    # Keep the former zero-argument construction source-compatible with its
    # historical modern values; audited selection always passes both fields.
    def initialize(@major : Int32 = 24, @layout : Layout = Layout::Darwin24And25)
    end

    # This is the fixed kernel copy length, not a negotiated user buffer size.
    # attributes_size remains as the original public spelling for consumers.
    def fixed_attribute_copy_size : Int32
      attributes_size
    end

    def attributes_size : Int32
      case @layout
      when Layout::Darwin21 then 152
      else                       192
      end
    end

    def descriptor_size : Int32
      case @layout
      when Layout::Darwin21 then 128
      else                       144
      end
    end

    # The following native64 action values are equal across the audited source
    # pins. The payload union intentionally overlaps open and chdir paths.
    {% for name, value in {
                            actions_header_size: 8, action_size: 1040, path_capacity: 1024,
                            flags_offset: 0, defaults_offset: 4, mask_offset: 8,
                            descriptor_attribute_size_offset: 0, descriptor_attributes_offset: 8,
                            descriptor_actions_size_offset: 16, descriptor_actions_offset: 24,
                            actions_capacity_offset: 0, actions_count_offset: 4,
                            action_type_offset: 0, action_fd_offset: 4, action_destination_offset: 8,
                            open_flags_offset: 8, open_mode_offset: 12, open_path_offset: 14,
                            chdir_path_offset: 8,
                          } %}
      def {{name}} : Int32
        {{value}}
      end
    {% end %}
  end

  # This selects audited ABI data only. The caller owns release admission and
  # runtime qualification, including the exact initialized buffer contents.
  def self.profile(major : Int32) : Profile?
    case major
    when 21     then Profile.new(21, Layout::Darwin21)
    when 24, 25 then Profile.new(major, Layout::Darwin24And25)
    else             nil
    end
  end

  def self.create(child : Int32*, path : UInt8*, descriptor : Void*,
                  arguments : UInt8**, environment : UInt8**) : Result
    Raw.call(244, child.address, path.address, descriptor.address, arguments.address, environment.address)
  end
end
