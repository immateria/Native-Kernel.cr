require "set"
require "../verification"
require "../../src/native-kernel/audit"

abort "Usage: audit IR_PATH" unless ARGV.size == 1
Native::Kernel::Verification.verify(
  File.read(ARGV[0]),
  native_symbols: Set(String).new,
  assembly: Native::Kernel::Audit::ASSEMBLY.to_set,
)
puts "Reachable LLVM approved; no external symbols allowed"
