/* Original MIT assertions against INSTALLED Linux UAPI, not libc ABI types.
 * Header dependencies and hashes are retained by linux_runner.py (-MD).
 * This oracle may use libc to print; it is NOT the Crystal unmanaged proof. */
#include <stddef.h>
#include <asm/unistd.h>
#include <asm/signal.h>
#include <asm/siginfo.h>
#include <asm/errno.h>
#include <linux/poll.h>
#include <linux/fcntl.h>
#include <linux/pidfd.h>
#include <linux/resource.h>
#include <linux/time_types.h>
#include <linux/wait.h>
#include <linux/mman.h>

#if defined(__ANDROID__) || defined(__ILP32__) || \
    !(defined(__x86_64__) || defined(__aarch64__))
#error Unsupported layout target
#endif
#define EQ(a,b) _Static_assert((a) == (b), #a " != " #b)
#define RECORD(t,s,a) EQ(sizeof(t),s); EQ(_Alignof(t),a)
#define OFFSET(t,f,n) EQ(offsetof(t,f),n)
RECORD(struct pollfd,8,4);
OFFSET(struct pollfd,fd,0); OFFSET(struct pollfd,events,4); OFFSET(struct pollfd,revents,6);
RECORD(struct __kernel_timespec,16,8);
OFFSET(struct __kernel_timespec,tv_sec,0); OFFSET(struct __kernel_timespec,tv_nsec,8);
RECORD(struct __kernel_old_timeval,16,8);
OFFSET(struct __kernel_old_timeval,tv_sec,0); OFFSET(struct __kernel_old_timeval,tv_usec,8);
RECORD(struct rusage,144,8);
OFFSET(struct rusage,ru_utime,0); OFFSET(struct rusage,ru_stime,16);
OFFSET(struct rusage,ru_maxrss,32); OFFSET(struct rusage,ru_ixrss,40);
OFFSET(struct rusage,ru_idrss,48); OFFSET(struct rusage,ru_isrss,56);
OFFSET(struct rusage,ru_minflt,64); OFFSET(struct rusage,ru_majflt,72);
OFFSET(struct rusage,ru_nswap,80); OFFSET(struct rusage,ru_inblock,88);
OFFSET(struct rusage,ru_oublock,96); OFFSET(struct rusage,ru_msgsnd,104);
OFFSET(struct rusage,ru_msgrcv,112); OFFSET(struct rusage,ru_nsignals,120);
OFFSET(struct rusage,ru_nvcsw,128); OFFSET(struct rusage,ru_nivcsw,136);
RECORD(struct rlimit64,16,8);
OFFSET(struct rlimit64,rlim_cur,0); OFFSET(struct rlimit64,rlim_max,8);
RECORD(siginfo_t,128,8);
OFFSET(siginfo_t,si_signo,0); OFFSET(siginfo_t,si_errno,4); OFFSET(siginfo_t,si_code,8);
OFFSET(siginfo_t,si_pid,16); OFFSET(siginfo_t,si_uid,20); OFFSET(siginfo_t,si_status,24);
/* Raw waitid does not populate si_utime/si_stime. They begin its opaque tail. */
OFFSET(siginfo_t,si_utime,32); OFFSET(siginfo_t,si_stime,40);
RECORD(sigset_t,8,8); RECORD(unsigned long,8,8);
#ifdef __aarch64__
OFFSET(sigset_t,sig,0);
#endif
EQ(O_NONBLOCK,0x800); EQ(O_CLOEXEC,0x80000); EQ(FD_CLOEXEC,1);
EQ(F_DUPFD,0); EQ(F_GETFD,1); EQ(F_SETFD,2); EQ(F_GETFL,3); EQ(F_SETFL,4);
EQ(F_DUPFD_CLOEXEC,1030); EQ(PIDFD_NONBLOCK,0x800);
EQ(POLLIN,1); EQ(POLLOUT,4); EQ(POLLERR,8); EQ(POLLHUP,16); EQ(POLLNVAL,32);
EQ(SIGKILL,9); EQ(SIGTERM,15); EQ(SIGCHLD,17); EQ(SIGCONT,18); EQ(SIGSTOP,19);
EQ(CLD_EXITED,1); EQ(CLD_KILLED,2); EQ(CLD_DUMPED,3); EQ(CLD_STOPPED,5); EQ(CLD_CONTINUED,6);
EQ(WNOHANG,1); EQ(WUNTRACED,2); EQ(WSTOPPED,2); EQ(WEXITED,4);
EQ(WCONTINUED,8); EQ(WNOWAIT,0x01000000);
EQ(P_ALL,0); EQ(P_PID,1); EQ(P_PGID,2); EQ(P_PIDFD,3);
EQ(RUSAGE_SELF,0); EQ(RUSAGE_CHILDREN,-1); EQ(RUSAGE_THREAD,1); EQ(RLIMIT_NOFILE,7);
EQ(RLIM64_INFINITY,~0ULL);
EQ(EINTR,4); EQ(EAGAIN,11); EQ(ENOSYS,38); EQ(EBADF,9); EQ(EINVAL,22);
EQ(EFAULT,14); EQ(ECHILD,10); EQ(ESRCH,3); EQ(EPERM,1); EQ(EMFILE,24);
EQ(AT_FDCWD,-100); EQ(PROT_READ,1); EQ(MAP_PRIVATE,2);
/* The complete shipping subset, including the five fixture-only raw entries. */
#if defined(__x86_64__)
#define NUMBER(n,x,a) EQ(__NR_##n,x)
#else
#define NUMBER(n,x,a) EQ(__NR_##n,a)
#endif
NUMBER(read,0,63); NUMBER(write,1,64); NUMBER(close,3,57);
NUMBER(mmap,9,222); NUMBER(munmap,11,215); NUMBER(openat,257,56);
NUMBER(clone,56,220); NUMBER(execve,59,221);
NUMBER(getpid,39,172); NUMBER(getppid,110,173);
NUMBER(getpgid,121,155); NUMBER(setpgid,109,154); NUMBER(getsid,124,156); NUMBER(setsid,112,157);
NUMBER(kill,62,129); NUMBER(exit_group,231,94);
NUMBER(fcntl,72,25); NUMBER(dup3,292,24); NUMBER(pipe2,293,59);
NUMBER(pidfd_open,434,434); NUMBER(pidfd_send_signal,424,424); NUMBER(ppoll,271,73);
NUMBER(wait4,61,260); NUMBER(waitid,247,95); NUMBER(getrusage,98,165); NUMBER(prlimit64,302,261);
#ifndef NK_LAYOUT_ONLY
extern int puts(const char *);
int main(void) { return puts("NK linux installed-UAPI layout passed") < 0; }
#endif
