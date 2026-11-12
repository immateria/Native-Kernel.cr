# This verifier runs in the ordinary build process, never in the native helper.
module Native::Kernel::Verification
  TOKEN      = /([@%])("(?:\\.|[^"\\])*"|[-a-zA-Z$._0-9]+)|"(?:\\.|[^"\\])*"|;[^\n]*/
  CALL       = /\A\s*(?:%(?:"(?:\\.|[^"\\])*"|[-a-zA-Z$._0-9]+)\s*=\s*)?(?:(?:tail|musttail|notail)\s+)?(?:call|invoke|callbr)\s+/
  ASM        = /\basm(?: sideeffect)? "((?:\\.|[^"\\])*)", "((?:\\.|[^"\\])*)"/
  INTRINSICS = %w(llvm.memcpy. llvm.memmove. llvm.memset. llvm.lifetime.start. llvm.lifetime.end. llvm.expect. llvm.smin. llvm.smax. llvm.experimental.cttz.elts. llvm.uadd.with.overflow. llvm.sadd.with.overflow. llvm.usub.with.overflow. llvm.ssub.with.overflow. llvm.umul.with.overflow. llvm.smul.with.overflow.)

  private def self.symbol(line : String) : String?
    line.scan(TOKEN) { |match| return match[2] if match[1]? == "@" }
    nil
  end

  private def self.direct_call?(line : String, assembly : Set(String)) : Bool
    call = CALL.match(line)
    return true unless call
    if code = ASM.match(line)
      return assembly.includes?(code[1] + '\0' + code[2])
    end
    line[call.end(0)..].scan(TOKEN) do |match|
      if match[1]? && line[call.end(0)..][match.end(0)..].lstrip.starts_with?('(')
        return match[1] == "@"
      end
    end
    false
  end

  def self.verify(ir : String, *, native_symbols : Set(String) = Set(String).new,
                  assembly : Set(String) = Set(String).new) : Nil
    if ir.matches?(/^@llvm\.global_(?:ctors|dtors)\s*=/m)
      raise ArgumentError.new("native helper cannot contain runtime constructors or destructors")
    end
    bodies = {} of String => String
    current = nil.as(String?)
    function = false
    ir.each_line do |line|
      if line.starts_with?("define ") && (name = symbol(line))
        current = name
        function = true
        bodies[current] = line + '\n'
      elsif line.starts_with?('@') && (name = symbol(line)) && line.includes?('=')
        current = name
        function = false
        bodies[current] = line + '\n'
      elsif owner = current
        if function
          bodies[owner] += line + '\n'
          current = nil if line.starts_with?('}')
        elsif line.empty? || !line[0].whitespace?
          current = nil
        else
          bodies[owner] += line + '\n'
        end
      end
    end
    raise ArgumentError.new("native helper has no main entry point") unless bodies.has_key?("main")

    pending = ["main"]
    seen = Set(String).new
    until pending.empty?
      name = pending.pop
      next unless seen.add?(name)
      if name.starts_with?("__crystal_") || name.includes?("Crystal::") || name.starts_with?("GC_")
        raise ArgumentError.new("native helper reaches runtime symbol #{name}")
      end
      if body = bodies[name]?
        if body.matches?(/\A@[^\n]*=\s*(?:[-a-zA-Z_][a-zA-Z_0-9]*(?:\([^)]*\))?\s+)*global\s/)
          raise ArgumentError.new("native helper reaches mutable global #{name}; runtime initialization is inactive")
        end
        body.each_line do |line|
          unless direct_call?(line, assembly)
            raise ArgumentError.new("native helper contains an indirect or unrecognized call: #{line.strip}")
          end
        end
        body.scan(TOKEN) { |match| pending << match[2] if match[1]? == "@" }
      else
        plain = name.strip('"')
        unless native_symbols.includes?(plain) || INTRINSICS.any? { |prefix| plain.starts_with?(prefix) }
          raise ArgumentError.new("native helper reaches unapproved symbol #{name}")
        end
      end
    end
  end
end
