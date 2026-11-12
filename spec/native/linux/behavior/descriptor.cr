module LinuxBehavior
  def self.descriptor_body(reader : Int32, writer : Int32) : Int32
    byte = 0_u8
    empty = D.read(reader, pointerof(byte), 1_u64)
    return 10 unless empty.primary == -11 && empty.error == 11 # genuinely native EAGAIN
    return 11 unless D.fcntl(reader, D::F_GETFL).primary & D::O_NONBLOCK != 0
    return 12 unless D.fcntl(reader, D::F_GETFD).primary == D::FD_CLOEXEC
    return 13 unless D.fcntl(reader, D::F_SETFD, 0_u64).error == 0
    return 14 unless D.fcntl(reader, D::F_GETFD).primary == 0
    return 15 unless D.fcntl(reader, D::F_SETFD, D::FD_CLOEXEC.to_u64!).error == 0
    flags = D.fcntl(reader, D::F_GETFL)
    return 16 unless flags.error == 0 && D.fcntl(reader, D::F_SETFL, flags.primary.to_u64!).error == 0
    same = D.dup3(reader, reader, 0)
    return 17 unless same.primary == -22 && same.error == 22
    duplicated = D.fcntl(reader, D::F_DUPFD_CLOEXEC, 32_u64)
    return 18 unless duplicated.error == 0 && duplicated.primary >= 32
    copy = duplicated.primary.to_i32!
    code = 0
    if D.fcntl(copy, D::F_GETFD).primary != D::FD_CLOEXEC
      code = 19
    else
      replacement = D.dup3(reader, copy, D::O_CLOEXEC)
      byte = 79_u8
      sent = D.write(writer, pointerof(byte), 1_u64)
      byte = 0_u8
      got = D.read(copy, pointerof(byte), 1_u64)
      # Keep a result live across another trap: regression for bad flags clobber.
      checked = D.fcntl(copy, D::F_GETFD)
      code = 20 unless replacement.error == 0 && replacement.primary == copy && sent.primary == 1 && got.primary == 1 && byte == 79 && checked.primary == D::FD_CLOEXEC
    end
    closed = D.close(copy)
    closed.error == 0 ? code : 21
  end

  def self.descriptor : Int32
    fds = StaticArray(Int32, 2).new(-777)
    failed = D.pipe2(fds.to_unsafe, 0x40000000)
    return 22 unless failed.primary == -22 && failed.error == 22
    failed = D.pipe2(Pointer(Int32).new(1_u64), 0)
    return 23 unless failed.primary == -14 && failed.error == 14
    return 24 unless D.read(-1, Pointer(UInt8).null, 1_u64).error == 9 && D.write(-1, Pointer(UInt8).null, 1_u64).error == 9
    return 25 unless D.close(-1).error == 9 && D.fcntl(-1, D::F_GETFD).error == 9 && D.dup3(-1, -1, 0).error != 0
    opened = D.pipe2(fds.to_unsafe, D::O_CLOEXEC | D::O_NONBLOCK)
    return 26 unless opened.error == 0 && opened.primary == 0
    reader, writer = fds.to_unsafe[0], fds.to_unsafe[1]
    code = descriptor_body(reader, writer)
    one = D.close(reader)
    two = D.close(writer)
    one.error == 0 && two.error == 0 ? code : 27
  end

  # Same executable is genuinely exec'd. The driver gives it only 0/1/2; all
  # acquired numbers are checked before relying on this fixture's fixed slots.
  def self.exec(argv : UInt8**, environment : UInt8**) : Int32
    fds = StaticArray(Int32, 2).new(-1)
    opened = D.pipe2(fds.to_unsafe, D::O_CLOEXEC)
    return 28 unless opened.error == 0
    reader, writer = fds.to_unsafe[0], fds.to_unsafe[1]
    first = D.fcntl(writer, D::F_DUPFD_CLOEXEC, 64_u64)
    second = D.fcntl(writer, D::F_DUPFD, 65_u64)
    third = D.fcntl(writer, D::F_DUPFD, 66_u64)
    pidfd = Linux::Pidfd.open(P.pid.primary.to_i32!)
    code = 29
    if reader == 3 && writer == 4 && first.primary == 64 && second.primary == 65 && third.primary == 66 &&
       first.error == 0 && second.error == 0 && third.error == 0 && pidfd.error == 0 && pidfd.primary == 5 && D.dup3(writer, 66, D::O_CLOEXEC).error == 0
      arguments = StaticArray(UInt8*, 5).new(Pointer(UInt8).null)
      arguments.to_unsafe[0] = argv[0]
      arguments.to_unsafe[1] = "exec-check".to_unsafe
      arguments.to_unsafe[2] = argv[2]
      arguments.to_unsafe[3] = argv[3]
      Linux::Raw.call(Linux::Number::EXECVE, argv[0].address, arguments.to_unsafe.address, environment.address)
      code = 30 # An exec failure is not success, regardless of errno.
    end
    D.close(reader)
    D.close(writer)
    D.close(first.primary.to_i32!) if first.error == 0
    D.close(second.primary.to_i32!) if second.error == 0
    D.close(third.primary.to_i32!) if third.error == 0
    D.close(pidfd.primary.to_i32!) if pidfd.error == 0
    code
  end

  def self.exec_check : Int32
    return 31 unless D.fcntl(3, D::F_GETFD).error == 9 && D.fcntl(4, D::F_GETFD).error == 9 && D.fcntl(5, D::F_GETFD).error == 9
    return 32 unless D.fcntl(64, D::F_GETFD).error == 9 && D.fcntl(66, D::F_GETFD).error == 9
    inherited = D.fcntl(65, D::F_GETFD)
    closed = D.close(65)
    inherited.error == 0 && inherited.primary == 0 && closed.error == 0 ? 0 : 33
  end
end
