target=spec/native/behavior/mach_send_timeout.cr

zmutant.literal copy-restored-needs-two "$target" \
  'return MachSendOwnership::Owned if !original_header_valid && restored_header_valid && refs_valid && refs == 2_u32' \
  'return MachSendOwnership::Owned if !original_header_valid && restored_header_valid && refs_valid && refs == 1_u32'

zmutant.literal copy-original-needs-one "$target" \
  'return MachSendOwnership::None if original_header_valid && !restored_header_valid && refs_valid && refs == 1_u32' \
  'return MachSendOwnership::None if original_header_valid && !restored_header_valid && refs_valid && refs == 2_u32'

zmutant.literal relax-mig-success-size "$target" \
  'words[1] == 40_u32' 'words[1] >= 39_u32'

zmutant.literal skip-reply-cleanup "$target" \
  'reply_cleanup = ops.remove_receive(task, reply)' 'reply_cleanup = 0'

zmutant.literal release-uncertain-copy "$target" \
  'extra_send_owned = true if ownership == MachSendOwnership::Owned' \
  'extra_send_owned = true'

zmutant.literal skip-extra-before-baseline "$target" \
  'if primary_error == 0 && extra_send_owned' 'if false && extra_send_owned'

zmutant.perl keep-consumed-move-owned "$target" \
  's/(MACH_MSG_TYPE_MOVE_SEND,\n        0x5300_u32, 0x6300_u32\)\n(?:.*\n){2}      )original_send_owned = false/${1}original_send_owned = true/'

zmutant.literal ignore-receive-failure "$target" \
  'if received != 0' 'if false'

zmutant.literal mask-extra-cleanup-error "$target" \
  'extra_cleanup_error = released' 'extra_cleanup_error = 0'

zmutant.literal skip-original-send-cleanup "$target" \
  'if original_send_owned' 'if false && original_send_owned'

zmutant.literal mask-send-cleanup-error "$target" \
  'send_cleanup_error = released if released != 0' \
  'send_cleanup_error = 0 if released != 0'

zmutant.literal skip-receive-cleanup "$target" \
  'if receive_owned' 'if false && receive_owned'

zmutant.literal mask-receive-cleanup-error "$target" \
  'receive_cleanup_error = removed if removed != 0' \
  'receive_cleanup_error = 0 if removed != 0'

zmutant.literal skip-task-cleanup "$target" \
  'if task_owned' 'if false && task_owned'

zmutant.literal mask-task-cleanup-error "$target" \
  'task_cleanup_error = released if released != 0' \
  'task_cleanup_error = 0 if released != 0'
