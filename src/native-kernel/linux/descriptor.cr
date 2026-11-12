require "./raw"

module Native::Kernel::Linux::Descriptor
  O_NONBLOCK = 0x00800
  O_CLOEXEC  = 0x80000

  F_DUPFD         =    0
  F_GETFD         =    1
  F_SETFD         =    2
  F_GETFL         =    3
  F_SETFL         =    4
  F_DUPFD_CLOEXEC = 1030
  FD_CLOEXEC      =    1

  # Count is bytes, not elements of T. On success only primary bytes were
  # read/written (possibly zero/short). On error no successful buffer output is
  # promised; a partial transfer may instead be returned as a successful count.
  def self.read(fd : Int32, buffer : Pointer(T), capacity : UInt64) : Result forall T
    Raw.call(Number::READ, fd.to_u64!, buffer.address, capacity)
  end

  def self.write(fd : Int32, buffer : Pointer(T), count : UInt64) : Result forall T
    Raw.call(Number::WRITE, fd.to_u64!, buffer.address, count)
  end

  # Never retry automatically: on Linux an error need not leave fd open.
  def self.close(fd : Int32) : Result
    Raw.call(Number::CLOSE, fd.to_u64!)
  end

  # fds must point to two writable Int32 slots. On success primary is zero and
  # the caller owns BOTH output descriptors; no descriptor lives in Result.
  # Error outputs are not acquisitions and must not be used or closed as fds.
  def self.pipe2(fds : Int32*, flags : Int32) : Result
    Raw.call(Number::PIPE2, fds.address, flags.to_u64!)
  end

  # Success owns new_fd, atomically replacing it if it was open. Failure is not
  # an acquisition. old_fd == new_fd is EINVAL, unlike dup2.
  def self.dup3(old_fd : Int32, new_fd : Int32, flags : Int32) : Result
    Raw.call(Number::DUP3, old_fd.to_u64!, new_fd.to_u64!, flags.to_u64!)
  end

  # The third slot is a raw word (integer or caller-owned pointer address).
  # Successful F_DUPFD[_CLOEXEC] acquires a caller-owned descriptor in primary.
  # Other commands retain their native per-command output/ownership contracts.
  def self.fcntl(fd : Int32, command : Int32, argument : UInt64 = 0_u64) : Result
    Raw.call(Number::FCNTL, fd.to_u64!, command.to_u64!, argument)
  end
end
