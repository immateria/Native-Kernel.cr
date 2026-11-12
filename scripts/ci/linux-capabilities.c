/* Original MIT diagnostic using libc, deliberately separate from ELF proof.
 * Success proves only these operations in this caller/sandbox, not a kernel
 * release's entire syscall table or permissions on someone else's target. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/resource.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <unistd.h>

static int first = 1;
static void result(const char *name, long value, int error) {
    printf("%s\"%s\":{\"return\":%ld,\"errno\":%d}",first ? "{" : ",",name,value,error);
    first = 0;
}
#define OBSERVE(name,expr) do { errno=0; long r=(expr); result(name,r,r<0 ? errno : 0); } while (0)
int main(void) {
    errno=0;
    int fd=(int)syscall(SYS_pidfd_open,getpid(),0);
    result("pidfd_open_self",fd,fd<0 ? errno : 0);
    OBSERVE("pidfd_send_signal_invalid",syscall(SYS_pidfd_send_signal,-1,0,0,0));
    if (fd>=0) {
        OBSERVE("pidfd_send_signal_self_zero",syscall(SYS_pidfd_send_signal,fd,0,0,0));
        siginfo_t info = {0};
        OBSERVE("pidfd_self_not_waitable",syscall(SYS_waitid,P_PIDFD,fd,&info,WEXITED|WNOHANG,0));
        OBSERVE("close_pidfd",close(fd));
    }
    struct timespec timeout = {0};
    uint64_t kernel_mask = 0;
    OBSERVE("ppoll_kernel_mask",syscall(SYS_ppoll,0,0,&timeout,&kernel_mask,8));
    OBSERVE("ppoll_libc_mask_size_refused",syscall(SYS_ppoll,0,0,&timeout,&kernel_mask,128));
    struct rusage usage;
    struct rlimit limit;
    int status;
    OBSERVE("wait4_no_children",syscall(SYS_wait4,-1,&status,WNOHANG,&usage));
    OBSERVE("getrusage_self",syscall(SYS_getrusage,RUSAGE_SELF,&usage));
    OBSERVE("prlimit64_self",syscall(SYS_prlimit64,0,RLIMIT_NOFILE,0,&limit));
    OBSERVE("unassigned_syscall",syscall(-1));
    int fds[2];
    errno=0; int acquired=pipe2(fds,O_NONBLOCK|O_CLOEXEC);
    result("pipe2",acquired,acquired<0 ? errno : 0);
    if (!acquired) {
        unsigned char byte;
        OBSERVE("nonblocking_read",syscall(SYS_read,fds[0],&byte,1));
        OBSERVE("close_read",close(fds[0])); OBSERVE("close_write",close(fds[1]));
    }
    puts(",\"native_eintr\":\"unqualified: no handler installed or interruption claimed\"}");
    return 0;
}
