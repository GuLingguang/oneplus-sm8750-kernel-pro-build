# Droidspaces standard 6.6 rules

This document records the T09 kernel-side rules for the two standard
profiles. It is not a claim that a Droidspaces container has booted on an Ace6
device.

## Profile boundary

`ace6-droidspaces-standard-6.6` is the no-KernelSU baseline. It enables the
kernel capabilities required by the standard container path but does not add a
root provider. `ace6-droidspaces-resukisu-standard-6.6` inherits the same
baseline and selects ReSukiSU's non-SUSFS Manual Hook path.

The standard integration deliberately does not apply the legacy
`patches/split/05_droidspaces.patch`: that file also contains EVDI and the
global `find_task_by_vpid()`/`ghost_task` workaround. EVDI belongs to T11 and
the vendor workaround belongs to T10. The T09 patch contains only the
NTSYNC Kconfig/build entries and the 6.6 Android-kABI SYSVIPC layout change.

## Kernel configuration

The authoritative fragment is
`config/config_droidspaces_standard_6.6.fragment`. It is a separate input from
`config/config_ace6_final.config`, so minimal and SUSFS profiles do not gain
container-only options implicitly.

| Area | Required settings in the Ace6 fragment | Purpose |
| --- | --- | --- |
| IPC/namespaces | `SYSCTL`, `SYSVIPC`, `POSIX_MQUEUE`, `NAMESPACES`, `PID_NS`, `UTS_NS`, `IPC_NS`, `USER_NS`, `NET_NS` | process, mount/UTS/IPC and network isolation prerequisites |
| seccomp/cgroups | `SECCOMP`, `SECCOMP_FILTER`, `CGROUPS`, `CGROUP_DEVICE`, `CGROUP_PIDS`, `MEMCG`, `CGROUP_SCHED`, `FAIR_GROUP_SCHED`, `CGROUP_FREEZER`, `CGROUP_NET_PRIO` | container policy, device and process accounting |
| filesystems | `DEVTMPFS`, `OVERLAY_FS`, `TMPFS_POSIX_ACL`, `TMPFS_XATTR` | `/dev`, volatile mode and rootfs metadata |
| NAT/none networking | `NETFILTER`, `BRIDGE_NETFILTER`, `VETH`, `BRIDGE`, conntrack/NAT/iptables/nftables and routing settings | the standard isolated networking path |
| synchronization | `NTSYNC` | Windows-compatible synchronization primitive used by the userspace runtime |

The target 6.6 Kconfig calls the connection-tracking netlink option
`CONFIG_NF_CT_NETLINK`; the upstream guide's `CONFIG_NF_CONNTRACK_NETLINK`
spelling is not a valid symbol in this tree. The fragment uses the target
symbol and `olddefconfig` retained it as `y`.

`SYSVIPC`/`POSIX_MQUEUE` are not enabled by configuration alone. The T09
integration patch moves the existing `task_struct` fields into the reserved
Android-kABI slots 6–8. This is a source-level kABI adaptation, not a proof
that every vendor module is ABI-compatible; that requires the later build and
device gates.

## ReSukiSU standard variant

The ReSukiSU standard lock applies the common compile fix, the T09 standard
patch and NTSYNC files, then links the locked ReSukiSU kernel tree and applies
the T07 driver and Manual Hook patches. Its intended configuration is:

```text
CONFIG_KSU=y
CONFIG_KSU_MANUAL_HOOK=y
CONFIG_KSU_TRACEPOINT_HOOK=n
CONFIG_KSU_SUSFS=n
```

The automatic setuid/init-rc/input options remain the T07-selected 6.6 Manual
Hook defaults. No SUSFS files, SUSFS hook choice or old KernelSU adapter is
layered into this profile.

## Userspace prerequisites and limits

The kernel-side rules do not include or pin an Android APK, a Droidspaces
static userspace binary, a rootfs image/tarball, init configuration, SELinux
policy, host firewall/forwarding policy, or a device/ROM. A runtime attempt
therefore still needs:

- a root provider; the no-KernelSU profile does not supply one;
- the matching Droidspaces userspace and a supported rootfs;
- the required host mounts and cgroup setup; and
- host networking/firewall policy when NAT is selected.

The upstream Droidspaces documentation states that SUSFS is unsupported for
its historical userspace path. The validator therefore does not silently add
SUSFS to the two standard profiles. The separately locked
`ace6-main-release-compat-6.6` composition is an explicit source-level
experiment: it combines SUSFS Inline with the extend kernel pieces, records the
userspace/ABI risk as a warning, and does not claim that the upstream
userspace is compatible. A `ghost_task=true` request is separately blocked by
T10; neither standard nor main source trees contain that workaround.

The Droidspaces candidate recorded during the upstream audit is
`ravindu644/Droidspaces-OSS@9c6a1c056e6cdb096c8cfd037e3221fcdf39bf7d` in
`manifests/upstream-candidates-2026-09-05.json`. The newer mirror checkout
observed during T09 was not substituted into any lock; the exact candidate
could not be re-fetched in this network environment. Its userspace source is
not a kernel-preparation input.

## Acceptance boundary

T09 evidence covers cumulative source preparation, `olddefconfig`, the 42
fragment settings, NTSYNC object compilation and profile inheritance. The main
composite additionally records the EVDI integration and keeps the EVDI ABI,
module modpost, full Image, boot, container creation, namespace isolation, NAT
connectivity, rootfs behavior, device modules and release publication as
separate gates.
