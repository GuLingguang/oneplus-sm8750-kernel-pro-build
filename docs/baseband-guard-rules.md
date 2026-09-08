# Baseband Guard rules

T08 locks the vendored Baseband Guard source to
`cctv18/Baseband-guard@a5b57f15d6b597a1bd157c42330fe80020b1d628`. The mirror
used to obtain the disposable audit checkout does not change that repository or
commit identity. The checked-in source keeps the upstream files as the base and
contains a local delta for the dentry predicate, operation coverage, null
guards, and build identity.

## Decision rules

`is_protected_blkdev()` is a boolean protection predicate:

- `NULL`, `ERR_PTR`, negative, or inode-less dentries return allow without
  dereferencing the dentry or inode.
- A block device is protected when it is not trusted and is not in the
  configured allowlist. The protected device is cached in `blocked_devs` and
  returns true to the caller.
- An absolute symlink is resolved with `kern_path(..., LOOKUP_FOLLOW, ...)`.
  A symlink to a protected block device returns true; regular targets and
  allowlisted block devices pass. Relative links remain outside this
  conservative by-name check.
- Every successful `get_link()` path releases its delayed callback. Every
  successful `kern_path()` path calls `path_put()`.

The `inode_rename` and `inode_setattr` hooks deny when this predicate is true
and allow trusted processes. `inode_symlink` denies untrusted creation in
`/dev/block/by-name`. `file_permission` and destructive `file_ioctl` continue
to enforce the write/ioctl policy on block-device inodes.

## Registration and configuration

The 6.6 disposable compile uses `CONFIG_BBG=y` and a `CONFIG_LSM` value that
contains `baseband_guard`. The source keeps the version-conditional LSM
registration: the 6.6 path uses `security_add_hooks(..., "baseband_guard")`,
while newer kernels use the `lsm_id` path. The object-level check found both
`inode_rename` and `inode_setattr` in the registered hook table.

## Evidence boundary

The exact 6.6 kernel source accepted the cumulative 07 compile-fix and 06 BBG
integration patches, `olddefconfig` completed, and the BBG directory objects
compiled. A disposable decision model covers NULL/ERR/negative dentries,
regular files, allowed/protected block devices, symlink targets, and trusted vs
untrusted operation gates.

This is source and object-level evidence only. No complete kernel/image build,
device boot, real partition write, destructive ioctl, or release is claimed.
The upstream BBG documentation remains WIP; T08 does not turn it into a
runtime-accepted baseband or anti-format guarantee.
