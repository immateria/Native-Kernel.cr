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
