require "./spec_helper"

describe Native::Kernel::Source do
  it "captures every shipped source byte including metadata and raw engines" do
    root = Native::Kernel::Source.root
    paths = Dir.glob(Path[root, "src", "**", "*.cr"].to_posix.to_s).map { |path| Path[path].relative_to(root).to_posix.to_s }.sort
    Native::Kernel::Source::FILES.keys.sort.should eq(paths)
    Native::Kernel::Source::FILES.each do |path, bytes|
      bytes.should eq(File.read(File.join(root, path)))
      Path[path].absolute?.should be_false
      bytes.includes?(root).should be_false
    end
  end

  it "keeps exact assembly keys separate from executable requires" do
    Native::Kernel::Audit::ASSEMBLY.size.should eq(3)
    Native::Kernel::Audit::ASSEMBLY.should contain("\0~{memory}")
    Native::Kernel::Audit::ASSEMBLY.each { |key| key.count('\0').should eq(1) }
  end
end

describe "portable Linux assembly metadata" do
  it "keeps the OS and architecture admission sets distinct" do
    darwin = Native::Kernel::Audit::ASSEMBLY
    x86 = Native::Kernel::Audit::LINUX_X86_64_ASSEMBLY
    arm = Native::Kernel::Audit::LINUX_AARCH64_ASSEMBLY
    x86.size.should eq(2)
    arm.size.should eq(2)
    [x86, arm].each do |keys|
      keys.should contain("\0~{memory}")
      keys.each { |key| key.count('\0').should eq(1) }
      keys.each { |key| darwin.should_not contain(key) unless key == "\0~{memory}" }
    end
    x86.last.should_not eq(arm.last)
  end
end
