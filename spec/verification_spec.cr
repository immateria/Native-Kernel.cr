require "./spec_helper"
require "set"
require "../scripts/verification"

describe Native::Kernel::Verification do
  it "rejects runtime state reachable through a callback global" do
    ir = <<-LLVM
      @counter = global i32 0
      @callback = constant ptr @handler
      define void @handler() {
        store i32 1, ptr @counter
        ret void
      }
      define i32 @main() {
        %callback = load ptr, ptr @callback
        ret i32 0
      }
      LLVM
    expect_raises(ArgumentError, /mutable global/) { Native::Kernel::Verification.verify(ir) }
  end

  it "rejects a reachable FFI call even when declared" do
    ir = <<-LLVM
      declare i64 @write(i32, ptr, i64)
      define i32 @main() {
        %result = call i64 @write(i32 1, ptr null, i64 0)
        ret i32 0
      }
      LLVM
    expect_raises(ArgumentError, /unapproved symbol write/) { Native::Kernel::Verification.verify(ir) }
  end

  it "rejects indirect calls and unapproved inline assembly" do
    ir = <<-LLVM
      define i32 @main(ptr %callback) {
        call void %callback()
        ret i32 0
      }
      LLVM
    expect_raises(ArgumentError, /indirect or unrecognized/) { Native::Kernel::Verification.verify(ir) }
    ir = <<-LLVM
      define i32 @main() {
        call void asm sideeffect "svc #0x81", "~{memory}"()
        ret i32 0
      }
      LLVM
    expect_raises(ArgumentError, /indirect or unrecognized/) { Native::Kernel::Verification.verify(ir, assembly: Native::Kernel::Audit::ASSEMBLY.to_set) }
  end

  it "accepts the approved memory barrier and refuses runtime constructors" do
    ir = <<-LLVM
      define i32 @main() {
        call void asm sideeffect "", "~{memory}"()
        ret i32 0
      }
      LLVM
    Native::Kernel::Verification.verify(ir, assembly: Native::Kernel::Audit::ASSEMBLY.to_set)
    expect_raises(ArgumentError, /constructors or destructors/) do
      Native::Kernel::Verification.verify("@llvm.global_ctors = appending global [0 x ptr] []\n" + ir)
    end
  end
end

describe "exact Linux assembly admission" do
  it "admits only the separately selected OS and architecture template" do
    profiles = [Native::Kernel::Audit::ASSEMBLY, Native::Kernel::Audit::LINUX_X86_64_ASSEMBLY, Native::Kernel::Audit::LINUX_AARCH64_ASSEMBLY]
    profiles.each_with_index do |keys, selected|
      instruction, constraints = keys.last.split('\0')
      ir = "define i32 @main() {\n  %x = call i64 asm sideeffect \"#{instruction}\", \"#{constraints}\"()\n  ret i32 0\n}\n"
      profiles.each_with_index do |admitted, profile|
        if selected == profile
          Native::Kernel::Verification.verify(ir, assembly: admitted.to_set)
        else
          expect_raises(ArgumentError, /indirect or unrecognized/) do
            Native::Kernel::Verification.verify(ir, assembly: admitted.to_set)
          end
        end
      end
    end
  end

  it "rejects all source-bound Linux negative fixtures under either Linux profile" do
    root = Native::Kernel::Source.root
    files = Dir.glob(File.join(root, "spec/native/linux/rejections/*.ll"))
    files.size.should eq(4)
    [Native::Kernel::Audit::LINUX_X86_64_ASSEMBLY, Native::Kernel::Audit::LINUX_AARCH64_ASSEMBLY].each do |keys|
      files.each do |file|
        expect_raises(ArgumentError) { Native::Kernel::Verification.verify(File.read(file), assembly: keys.to_set) }
      end
    end
  end
end
