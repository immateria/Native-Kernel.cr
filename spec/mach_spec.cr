require "./spec_helper"

{% if flag?(:darwin) %}
  # Test-only FFI observes name-table growth; production has no FFI declarations.
  lib Names
    fun mach_port_names(task : UInt32, names : UInt32**, count : UInt32*, types : UInt32**, type_count : UInt32*) : Int32
    fun mach_vm_deallocate(task : UInt32, address : UInt64, size : UInt64) : Int32
  end

  module Fixture::Mach
    def self.names(task : UInt32) : UInt32
      names = Pointer(UInt32).null
      types = Pointer(UInt32).null
      count = 0_u32
      type_count = 0_u32
      Names.mach_port_names(task, pointerof(names), pointerof(count), pointerof(types), pointerof(type_count)).should eq(0)
      Names.mach_vm_deallocate(task, names.address, count.to_u64 * 4).should eq(0)
      Names.mach_vm_deallocate(task, types.address, type_count.to_u64 * 4).should eq(0)
      count
    end
  end

  describe Native::Kernel::Darwin::Mach do
    it "releases dedicated reply receive rights after success and invalid destinations" do
      task = Darwin::Mach.task
      begin
        before = Fixture::Mach.names(task)
        100.times do
          words, count, code = Darwin::Mach.read(task, task)
          code.should eq(0)
          count.should eq(8)
          words[5].should eq(Process.pid)
          _words, count, code = Darwin::Mach.read(task, 0xfffffffe_u32)
          code.should_not eq(0)
          count.should eq(0)
        end
        Fixture::Mach.names(task).should eq(before)
      ensure
        Darwin::Mach.release(task, task).should eq(0)
      end
    end
  end
{% end %}
