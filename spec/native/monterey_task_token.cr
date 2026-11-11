# Darwin 21 task-token transport proof. Build with -Dwithout_main.
# Parent -> one gated owned child. The parent is the sole collector; it does
# not change sessions or groups, so the runner's process-group cleanup remains
# an independent outer bound only.
require "../../src/native-kernel/darwin"

module MontereyTaskToken
  alias Darwin = Native::Kernel::Darwin

  # A forced cleanup only promises collection, not the child's normal status.
  # The normal gate path still requires its exact successful exit status.
  def self.collect(pid : Int32, expected : Int32, terminate : Bool, accept_any_exit : Bool = false) : Bool
    status = 0
    attempt = 0
    while attempt < 2000
      result = Darwin::Process.waitpid(pid, pointerof(status), 1) # WNOHANG
      return result.error == 0 && (accept_any_exit || status == expected) if result.primary == pid
      return false unless result.error == 0 || result.error == 4
      if terminate && result.error == 0 && result.primary == 0
        Darwin::Signal.kill(pid, 9)
        terminate = false
      end
      Darwin::Event.sleep(1000_u32)
      attempt &+= 1
    end
    Darwin::Signal.kill(pid, 9)
    attempt = 0
    while attempt < 2000
      result = Darwin::Process.waitpid(pid, pointerof(status), 1)
      return result.error == 0 && accept_any_exit if result.primary == pid
      return false unless result.error == 0 || result.error == 4
      Darwin::Event.sleep(1000_u32)
      attempt &+= 1
    end
    false
  end

  def self.gate(fd : Int32) : Bool
    event = Darwin::Event::Poll.new(fd)
    ready = Darwin::Event.poll(pointerof(event), 1_u32, 5000)
    return false unless ready.error == 0 && ready.primary == 1
    byte = 0_u8
    read = Darwin::Descriptor.read(fd, pointerof(byte), 1_u64)
    read.error == 0 && read.primary == 1 && byte == 71
  end

  # proc_bsdinfowithuniqid supplies the same signed p_idversion which XNU
  # places in audit_token.val[7]. Compare it while the gated child is alive,
  # before any PID can be re-used.
  def self.token_matches(task : UInt32, target : UInt32, transport : Darwin::Mach::Transport,
                         pid : Int32) : Bool
    words, count, code = Darwin::Mach.read(task, target, transport)
    record = uninitialized Darwin::Process::Info::Record
    inspected = Darwin::Process.info(pid, Darwin::Process::Info::PIDT_BSDINFOWITHUNIQID,
      0_u64, pointerof(record).as(Void*), sizeof(typeof(record)))
    code == 0 && count == 8 && words.to_unsafe[5] == pid.to_u32! &&
      inspected.error == 0 && inspected.primary == sizeof(typeof(record)) &&
      record.bsd.pid == pid.to_u32! &&
      words.to_unsafe[7].unsafe_as(Int32) == record.unique.pid_version
  end

  # Repeated successful and failed exchanges each allocate a temporary receive
  # right. port_name_count owns/deallocates its two OOL arrays, so equal before
  # and after counts are a direct name-table growth metric rather than a leak.
  def self.exchange_growth(task : UInt32, transport : Darwin::Mach::Transport, self_pid : Int32) : Bool
    before, before_code = Darwin::Mach.port_name_count(task, transport)
    return false unless before_code == 0
    repeated = 0
    while repeated < 32
      return false unless token_matches(task, task, transport, self_pid)
      _words, count, failed = Darwin::Mach.read(task, 0xfffffffe_u32, transport)
      return false unless failed != 0 && count == 0
      repeated &+= 1
    end
    after, after_code = Darwin::Mach.port_name_count(task, transport)
    after_code == 0 && after == before
  end

  # Each controlled error still attempts the real writer close and lets the
  # parent collect. An invalid write or a repeated gate-writer close supplies a
  # deterministic EBADF without retrying an ambiguous child creation.
  def self.release_gate(writer : Int32, fail_write : Bool, fail_close : Bool) : Tuple(Int32, Int32, Int32)
    byte = 71_u8
    write = fail_write ? Darwin::Descriptor.write(-1, pointerof(byte), 1_u64) : Darwin::Descriptor.write(writer, pointerof(byte), 1_u64)
    if fail_close
      # Close the actual gate writer first, then deliberately close that same
      # descriptor again. The second close is a deterministic EBADF from a
      # gate-close attempt, while the first release lets collection proceed.
      actual = Darwin::Descriptor.close(writer)
      reported = Darwin::Descriptor.close(writer)
      {write.error, reported.error, actual.error}
    else
      closed = Darwin::Descriptor.close(writer)
      {write.error, closed.error, closed.error}
    end
  end

  # This branch is not executed by the shipped roster. It makes the changed
  # dispatch methods instantiate for both valid routes in every native Crystal
  # compile, rather than relying on a source-only assertion.
  def self.compile_transport_dispatch : Int32
    task = 0_u32
    _trap_words, _trap_count, trap = Darwin::Mach.read(task, task, Darwin::Mach::Transport::MachMsgTrap)
    _modern_words, _modern_count, modern = Darwin::Mach.read(task, task, Darwin::Mach::Transport::MachMsg2)
    trap &+ modern
  end

  def self.run(which : UInt8*) : Int32
    transport = Darwin::Mach.transport(Darwin::Process.release)
    return 2 unless transport == Darwin::Mach::Transport::MachMsgTrap
    task = Darwin::Mach.task
    return 3 if task == 0 || task == UInt32::MAX

    self_pid = Darwin::Process.pid.primary.to_i32!
    unless exchange_growth(task, transport, self_pid)
      Darwin::Mach.release(task, task)
      return 4
    end

    pipe = Darwin::Descriptor.pipe
    unless pipe.error == 0
      Darwin::Mach.release(task, task)
      return 5
    end
    reader, writer = pipe.primary.to_i32!, pipe.secondary.to_i32!
    child = Darwin::Process.fork
    if child.error != 0
      Darwin::Descriptor.close(reader)
      Darwin::Descriptor.close(writer)
      Darwin::Mach.release(task, task)
      return 6
    end
    if child.primary == 0
      Darwin::Descriptor.close(writer)
      ready = gate(reader)
      Darwin::Descriptor.close(reader)
      Darwin::Process.exit(ready ? 0 : 8)
    end

    pid = child.primary.to_i32!
    Darwin::Descriptor.close(reader)
    name, opened = Darwin::Mach.open(task, pid)
    if opened != 0
      closed = Darwin::Descriptor.close(writer)
      # A child PID from fork is confirmed ownership. Even a close error cannot
      # short-circuit this bounded collector; it changes only its expected exit.
      collected = collect(pid, 8, closed.error != 0, closed.error != 0)
      released_task = Darwin::Mach.release(task, task)
      return collected && released_task == 0 ? 7 : 8
    end

    target_reads = 0
    target_ok = true
    while target_reads < 32
      target_ok = false unless token_matches(task, name, transport, pid)
      target_reads &+= 1
    end

    fail_write = equal(which, "task-token-gate-write-failure".to_unsafe)
    fail_close = equal(which, "task-token-gate-close-failure".to_unsafe)
    write_error, close_error, actual_close_error = release_gate(writer, fail_write, fail_close)
    # This collection is unconditional once fork returned a confirmed child.
    # A gate write/close failure cannot bypass it. The original gate error is
    # checked before normal outcome checks, while a collection/release error
    # retains a distinct result so cleanup failure remains observable.
    forced_cleanup = write_error != 0 || close_error != 0 || actual_close_error != 0
    collected = collect(pid, 0, forced_cleanup, forced_cleanup)
    _words, dead_count, dead = Darwin::Mach.read(task, name, transport)
    released_name = Darwin::Mach.release(task, name)
    released_task = Darwin::Mach.release(task, task)
    cleanup_ok = collected && dead != 0 && dead_count == 0 && released_name == 0 && released_task == 0

    if fail_write
      return 9 unless write_error == 9 && close_error == 0 && actual_close_error == 0
      return cleanup_ok && target_ok ? 0 : 10
    end
    if fail_close
      return 11 unless write_error == 0 && close_error == 9 && actual_close_error == 0
      return cleanup_ok && target_ok ? 0 : 12
    end
    return 13 unless write_error == 0 && close_error == 0 && actual_close_error == 0
    return 14 unless target_ok
    cleanup_ok ? 0 : 15
  end

  def self.equal(left : UInt8*, right : UInt8*) : Bool
    offset = 0
    while offset < 64
      return false unless left[offset] == right[offset]
      return true if left[offset] == 0
      offset &+= 1
    end
    false
  end

  def self.finish(which : UInt8*) : Int32
    if equal(which, "task-token-exchange-growth".to_unsafe)
      completed = Darwin::Descriptor.write(1, "NK_OK task-token-exchange-growth\n".to_unsafe, 33_u64)
      return completed.error == 0 && completed.primary == 33 ? 0 : 16
    elsif equal(which, "task-token-attribution".to_unsafe)
      completed = Darwin::Descriptor.write(1, "NK_OK task-token-attribution\n".to_unsafe, 29_u64)
      return completed.error == 0 && completed.primary == 29 ? 0 : 17
    elsif equal(which, "task-token-gate-write-failure".to_unsafe)
      completed = Darwin::Descriptor.write(1, "NK_OK task-token-gate-write-failure\n".to_unsafe, 36_u64)
      return completed.error == 0 && completed.primary == 36 ? 0 : 18
    elsif equal(which, "task-token-gate-close-failure".to_unsafe)
      completed = Darwin::Descriptor.write(1, "NK_OK task-token-gate-close-failure\n".to_unsafe, 36_u64)
      return completed.error == 0 && completed.primary == 36 ? 0 : 19
    end
    20
  end
end

fun main(argc : Int32, argv : UInt8**) : Int32
  code = if argc == 99
           MontereyTaskToken.compile_transport_dispatch
         elsif argc == 2 && !argv[1].null?
           MontereyTaskToken.run(argv[1])
         else
           21
         end
  exit_code = if code == 0 && argc == 2
                MontereyTaskToken.finish(argv[1])
              else
                code
              end
  Native::Kernel::Darwin::Process.exit(exit_code)
end
