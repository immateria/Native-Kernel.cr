module Native::Kernel::Linux
  # Linux returns a single signed word. Only [-4095, -1] encodes errno.
  # In particular -4096 and other high-bit values are not errors. No TLS/libc
  # errno, Darwin carry flag or synthetic second result register is involved.
  struct Result
    getter primary : Int64
    getter error : Int32

    def initialize(@primary : Int64)
      @error = @primary >= -4095 && @primary <= -1 ? (0_i64 &- @primary).to_i32! : 0
    end
  end
end
