require "./raw"

module Native::Kernel::Darwin::Resource
  struct Limit
    property soft : UInt64
    property hard : UInt64

    def initialize(@soft = 0_u64, @hard = 0_u64)
    end
  end

  def self.set(resource : Int32, limits : Limit*) : Result
    Raw.call(195, resource.to_u64!, limits.address)
  end

  def self.get(resource : Int32, limits : Limit*) : Result
    Raw.call(194, resource.to_u64!, limits.address)
  end
end
