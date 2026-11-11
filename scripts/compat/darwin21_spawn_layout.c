/*
 * Independent native64 layout gate for the Darwin 21 spawn subset.
 *
 * This transcribes only the declarations consumed by Native-Kernel from the
 * pinned XNU xnu-8020.140.41 source; it deliberately does not include an SDK
 * header. Compile with an x86-64 C compiler in syntax-only mode. See
 * docs/darwin-monterey-foundations.md for the source manifest and limits.
 */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef uint32_t darwin_sigset_t;
typedef int32_t pid_type;
typedef int32_t cpu_type;
typedef int32_t cpu_subtype;
typedef int32_t task_role;
typedef uint16_t mode_type;
typedef uint64_t darwin_size;
typedef uint32_t mach_port_name;

enum psfa_type {
  PSFA_OPEN = 0,
  PSFA_CLOSE = 1,
  PSFA_DUP2 = 2,
  PSFA_INHERIT = 3,
  PSFA_FILEPORT_DUP2 = 4,
  PSFA_CHDIR = 5,
  PSFA_FCHDIR = 6,
};

struct posix_spawnattr {
  int16_t psa_flags;
  int16_t flags_padding;
  darwin_sigset_t psa_sigdefault;
  darwin_sigset_t psa_sigmask;
  pid_type psa_pgroup;
  cpu_type psa_binprefs[4];
  int32_t psa_pcontrol;
  int32_t psa_apptype;
  uint64_t psa_cpumonitor_percent;
  uint64_t psa_cpumonitor_interval;
  uint64_t psa_reserved;
  int16_t psa_jetsam_flags;
  int16_t short_padding;
  int32_t psa_priority;
  int32_t psa_memlimit_active;
  int32_t psa_memlimit_inactive;
  uint64_t psa_qos_clamp;
  task_role psa_darwin_role;
  int32_t psa_thread_limit;
  uint64_t psa_max_addr;
  bool psa_no_smt;
  bool psa_tecs;
  int32_t psa_platform;
  cpu_subtype psa_subcpuprefs[4];
  uint32_t psa_options;
  uint32_t psa_port_soft_limit;
  uint32_t psa_port_hard_limit;
  uint32_t psa_filedesc_soft_limit;
  uint32_t psa_filedesc_hard_limit;
  void *psa_ports;
  void *psa_mac_extensions;
  void *psa_coalition_info;
  void *psa_persona_info;
  void *psa_posix_cred_info;
  char *psa_subsystem_root_path;
};

struct psfa_action {
  enum psfa_type psfaa_type;
  union {
    int32_t psfaa_filedes;
    mach_port_name psfaa_fileport;
  } descriptor;
  union {
    struct {
      int32_t psfao_oflag;
      mode_type psfao_mode;
      char psfao_path[1024];
    } open;
    struct {
      int32_t psfad_newfiledes;
    } dup2;
    struct {
      char psfac_path[1024];
    } chdir;
  } payload;
};

struct posix_spawn_file_actions {
  int32_t psfa_act_alloc;
  int32_t psfa_act_count;
  struct psfa_action psfa_act_acts[];
};

struct posix_spawn_args_desc {
  darwin_size attr_size;
  void *attrp;
  darwin_size file_actions_size;
  void *file_actions;
  darwin_size port_actions_size;
  void *port_actions;
  darwin_size mac_extensions_size;
  void *mac_extensions;
  darwin_size coal_info_size;
  void *coal_info;
  darwin_size persona_info_size;
  void *persona_info;
  darwin_size posix_cred_info_size;
  void *posix_cred_info;
  darwin_size subsystem_root_path_size;
  char *subsystem_root_path;
};

_Static_assert(sizeof(void *) == 8, "native64 requires eight-byte pointers");
_Static_assert(sizeof(darwin_size) == 8, "Darwin native64 size_t width");
_Static_assert(offsetof(struct posix_spawnattr, psa_flags) == 0, "flags offset");
_Static_assert(offsetof(struct posix_spawnattr, psa_sigdefault) == 4, "sigdefault offset");
_Static_assert(offsetof(struct posix_spawnattr, psa_sigmask) == 8, "sigmask offset");
_Static_assert(offsetof(struct posix_spawnattr, psa_ports) == 152, "Darwin 21 fixed attribute copy");
_Static_assert(sizeof(struct posix_spawnattr) == 200, "Darwin 21 complete attribute layout");
_Static_assert(sizeof(struct posix_spawn_args_desc) == 128, "Darwin 21 native64 descriptor");
_Static_assert(offsetof(struct posix_spawn_args_desc, attr_size) == 0, "attribute size offset");
_Static_assert(offsetof(struct posix_spawn_args_desc, attrp) == 8, "attribute pointer offset");
_Static_assert(offsetof(struct posix_spawn_args_desc, file_actions_size) == 16, "actions size offset");
_Static_assert(offsetof(struct posix_spawn_args_desc, file_actions) == 24, "actions pointer offset");
_Static_assert(sizeof(struct posix_spawn_file_actions) == 8, "action header size");
_Static_assert(sizeof(struct psfa_action) == 1040, "action stride");
_Static_assert(offsetof(struct psfa_action, psfaa_type) == 0, "action type offset");
_Static_assert(offsetof(struct psfa_action, descriptor) == 4, "action fd offset");
_Static_assert(offsetof(struct psfa_action, payload.dup2.psfad_newfiledes) == 8, "dup2 destination offset");
_Static_assert(offsetof(struct psfa_action, payload.open.psfao_oflag) == 8, "open flags offset");
_Static_assert(offsetof(struct psfa_action, payload.open.psfao_mode) == 12, "open mode offset");
_Static_assert(offsetof(struct psfa_action, payload.open.psfao_path) == 14, "open path offset");
_Static_assert(offsetof(struct psfa_action, payload.chdir.psfac_path) == 8, "chdir path offset");
