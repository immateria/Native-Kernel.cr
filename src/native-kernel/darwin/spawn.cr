require "./raw"

module Native::Kernel::Darwin::Spawn
  # Native64 layouts read on 2026-11-11 from Apple XNU xnu-11417.101.15
  # (e3723e1f17661b24996789d8afc084c0c3303b26) and xnu-12377.121.6
  # (ac9718fb1af618d5ce8678d0dc6e8a58f252216f), bsd/sys/spawn_internal.h
  # and bsd/kern/kern_exec.c. The kernel copies the entire descriptor and,
  # for any nonzero attr_size, the fixed prefix before psa_ports. A smaller
  # declared attribute size does not negotiate a shorter copy.
  struct Profile
    {% for name, value in {
                            attributes_size: 192, descriptor_size: 144,
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
    when 24, 25 then Profile.new
    else             nil
    end
  end

  def self.create(child : Int32*, path : UInt8*, descriptor : Void*,
                  arguments : UInt8**, environment : UInt8**) : Result
    Raw.call(244, child.address, path.address, descriptor.address, arguments.address, environment.address)
  end
end
