module Native::Kernel::Darwin
  struct Result
    getter primary : Int64
    getter secondary : Int64
    getter error : Int32

    def initialize(@primary : Int64, @secondary : Int64, @error : Int32)
    end
  end
end
