require "set"
require "../verification"
require "../../src/native-kernel/audit"

abort "Usage: audit IR_PATH [linux-x86_64|linux-aarch64]" unless 1 <= ARGV.size <= 2
assembly = case ARGV[1]?
           when nil             then Native::Kernel::Audit::ASSEMBLY
           when "linux-x86_64"  then Native::Kernel::Audit::LINUX_X86_64_ASSEMBLY
           when "linux-aarch64" then Native::Kernel::Audit::LINUX_AARCH64_ASSEMBLY
           else                      abort "Unknown assembly profile"
           end
Native::Kernel::Verification.verify(
  File.read(ARGV[0]),
  native_symbols: Set(String).new,
  assembly: assembly.to_set,
)
puts "Reachable LLVM approved; no external symbols allowed"
