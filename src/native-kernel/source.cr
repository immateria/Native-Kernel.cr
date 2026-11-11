# Managed build metadata. Never require this from an unmanaged entry point.
module Native::Kernel::Source
  {% begin %}
    FILES = {
      {% for path in ["src/native-kernel.cr", "src/native-kernel/audit.cr", "src/native-kernel/darwin.cr", "src/native-kernel/darwin/abi.cr", "src/native-kernel/darwin/descriptor.cr", "src/native-kernel/darwin/event.cr", "src/native-kernel/darwin/mach.cr", "src/native-kernel/darwin/process.cr", "src/native-kernel/darwin/raw.cr", "src/native-kernel/darwin/raw/arm64.cr", "src/native-kernel/darwin/raw/x86_64.cr", "src/native-kernel/darwin/resource.cr", "src/native-kernel/darwin/result.cr", "src/native-kernel/darwin/signal.cr", "src/native-kernel/darwin/spawn.cr", "src/native-kernel/source.cr"] %}
        {{path}} => {{read_file(__DIR__ + "/../../" + path)}},
      {% end %}
    } of String => String
  {% end %}

  def self.root : String
    File.expand_path("../..", __DIR__)
  end
end
