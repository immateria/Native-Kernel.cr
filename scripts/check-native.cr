require "digest/sha256"
require "file_utils"
require "json"
require "random/secure"
require "set"
require "../src/native-kernel/source"
require "../src/native-kernel/audit"
require "./verification"

{% if flag?(:darwin) && (flag?(:aarch64) || flag?(:x86_64)) %}

compiler = ENV["CRYSTAL"]? || "crystal"
description = IO::Memory.new
unless Process.run(compiler, ["--version"], output: description).success? && description.to_s.strip == Crystal::DESCRIPTION.strip
  abort "Select the compiler running this script with CRYSTAL=PATH."
end
abort "Pass at most one external receipt directory." if ARGV.size > 1
root = Native::Kernel::Source.root
destination = File.expand_path(ARGV.first? || File.join(Dir.tempdir, "native-kernel-#{Random::Secure.hex(8)}"))
abort "Artifact directory must be outside this repository." if destination == root || destination.starts_with?(root + File::SEPARATOR)
abort "Artifact directory already exists." if File.exists?(destination)
Dir.mkdir_p(destination, 0o700)
inputs = Native::Kernel::Source::FILES.keys + %w(spec/native/probe.cr scripts/check-native.cr scripts/verification.cr)
sources = inputs.to_h { |name| {name, Digest::SHA256.hexdigest(File.read(File.join(root, name)))} }
source = File.join(root, "spec/native/probe.cr")
output = File.join(destination, "probe")
assembly = Native::Kernel::Audit::ASSEMBLY.to_set
artifacts = {} of String => String
log_path = File.join(destination, "build.log")
environment = {"CRYSTAL_CACHE_DIR" => File.join(destination, "compiler")}
[false, true].each do |release|
  profile = release ? "release" : "development"
  artifact = output + "-" + profile
  flags = %w(build --cross-compile --single-module --no-debug --error-on-warnings -Dwithout_main --emit llvm-ir)
  if release
    flags << "--release"
  else
    {% if compare_versions(Crystal::VERSION, "1.11.0") >= 0 %}
      flags << "-O0"
    {% end %}
  end
  flags.concat([source, "-o", artifact])
  File.open(log_path, "a") do |log|
    unless Process.run(compiler, flags, env: environment, output: log, error: log).success?
      abort "Compilation failed: #{log_path}"
    end
  end
  Native::Kernel::Verification.verify(File.read(artifact + ".ll"), native_symbols: Set(String).new, assembly: assembly)
  architecture = {{ flag?(:aarch64) ? "arm64" : "x86_64" }}
  File.open(log_path, "a") do |log|
    unless Process.run("cc", ["-arch", architecture, artifact + ".o", "-o", artifact, "-Wl,-dead_strip"], output: log, error: log).success?
      abort "Link failed: #{log_path}"
    end
  end
  imports = IO::Memory.new
  unless Process.run("xcrun", ["nm", "-u", artifact], output: imports, error: STDERR).success?
    abort "Import inspection failed."
  end
  abort "Artifact imports external symbols:\n#{imports}" unless imports.to_s.strip.empty?
  result = Process.run(artifact, output: STDOUT, error: STDERR)
  abort "Native #{profile} probe failed with #{result.exit_code}." unless result.success?
  artifacts[profile + ".ir"] = Digest::SHA256.hexdigest(File.read(artifact + ".ll"))
  artifacts[profile + ".executable"] = Digest::SHA256.hexdigest(File.read(artifact))
  puts "#{profile}: reachable LLVM approved, zero imports, native probe passed"
end
sources.each do |name, digest|
  abort "Source changed during verification: #{name}" unless Digest::SHA256.hexdigest(File.read(File.join(root, name))) == digest
end
File.write(File.join(destination, "manifest.json"), {"compiler" => Crystal::DESCRIPTION, "sources" => sources, "artifacts" => artifacts, "assembly" => assembly.to_a.sort}.to_json)
puts "Receipts #{destination}"

{% elsif flag?(:linux) && !flag?(:android) && flag?(:bits64) && (flag?(:gnu) || flag?(:musl)) && (flag?(:aarch64) || flag?(:x86_64)) %}
  abort "Pass at most one external receipt directory." if ARGV.size > 1
  compiler = ENV["CRYSTAL"]? || "crystal"
  destination = File.expand_path(
    ARGV.first? || File.join(Dir.tempdir, "native-kernel-linux-#{Random::Secure.hex(8)}")
  )
  result = Process.run(
    "python3",
    [File.join(Native::Kernel::Source.root, "scripts/ci/linux_runner.py"), "--compiler", compiler, "--output", destination],
    chdir: Native::Kernel::Source.root,
    output: STDOUT,
    error: STDERR
  )
  exit result.exit_code
{% else %}
  {% raise "Native artifact verification requires Darwin ARM64/x86-64 or non-Android Linux LP64 AArch64/x86-64." %}
{% end %}
