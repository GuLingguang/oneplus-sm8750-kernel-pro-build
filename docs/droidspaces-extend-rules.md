# Droidspaces extend 6.6 rules

Status: the standalone extend profiles remain **blocked by incomplete userspace
evidence**; the main composite is **build-capable with runtime warnings**
because it now carries the source-locked EVDI integration.

`extend` is not a larger kernel configuration label. It inherits the
standard container baseline and adds a separate virtual-display/userspace
requirement set. The two profile identities are preserved:

| Profile | Base inheritance | Hook | SUSFS | Current status |
| --- | --- | --- | --- | --- |
| `ace6-droidspaces-extend-6.6` | standard | none | off | blocked T11 |
| `ace6-droidspaces-resukisu-extend-6.6` | ReSukiSU standard | Manual | off | blocked T11 |
| `ace6-main-release-compat-6.6` | ReSukiSU + SUSFS + Re:Kernel | SUSFS Inline | on | build-capable; T11 runtime warning |

The inheritance checker verifies that each extend profile keeps every base
feature other than `droidspaces`, changes only that selector to `extend`, and
contains the base capabilities plus `droidspaces-extend`. It does not infer
EVDI, HCI or coredump behavior from inheritance.

## EVDI source candidate

The 14 checked-in EVDI files under
`patches/extra/drivers/gpu/drm/evdi/` exactly match the
`Linux-on-droid/lindroid-drm-loopback` source at:

```text
commit: f15bc3ee6e9a90e85e70ef3da057f027c68cbefd
tree:   e6fa7935a0bbd44f27ccf41e0cf6b2f18feca568
```

The candidate was compared against the local clone and is recorded as audit
evidence. The legacy `05_droidspaces.patch` is not applied wholesale: it also
contains NTSYNC, SYSVIPC layout edits and the rejected global `ghost_task`
workaround. The main operational extend lock copies this exact EVDI source with
per-file hashes and applies a separate Kconfig/Makefile integration patch. The
legacy standalone extend locks remain intentionally incomplete.

With the target 6.6 configuration, `CONFIG_DRM_LINDROID_EVDI=y` and the EVDI
Kconfig/Makefile connection applied in a disposable tree, all EVDI source
objects combine into `drivers/gpu/drm/evdi/evdi.o`. This is an object-level
KABI/API check only. The final Image build still needs to complete before a
module/modpost or device claim is made.

## Userspace and ABI boundary

The current candidate snapshots used for audit are:

| Component | Ref / commit | Role | Acceptance |
| --- | --- | --- | --- |
| `vendor_lindroid` | `lindroid-22.1` / `eadbb70f13209133d96a5355464388db8c6578de` | Android app, daemon, HWC/input integration | candidate only |
| `vendor_extra` | `lindroid-21` / `39da805f20765a245f93f2d4ab6227ba40e1ce35` | Android build extras | candidate only |
| `libhybris` | `lindroid-21` / `29e0fa6da0166261f6b9437582fe2d56bab8530c` | Android graphics bridge | candidate only |
| `external_lxc` | `lindroid-21` / `4e3a3630fff3dc04e0d4a761309f87f248e40b17` | container runtime | candidate only |
| `create-disp` | `master` / `46c1d0414b3acb28b5902a2cb16b5ee40c1898ce` | EVDI display userspace | ABI mismatch |

The `create-disp` candidate defines and calls
`DRM_IOCTL_EVDI_SET_POWER_MODE` (`0x0f`) when
`TARGET_USES_REAL_HWC` is not defined. The locked EVDI UAPI at the source
candidate above defines no `DRM_EVDI_SET_POWER_MODE`, and the kernel driver has
no corresponding ioctl. The build flag and an alternative compatible
`create-disp` commit are not locked, so this is a concrete ABI blocker rather
than a runtime guess.

Virtual HCI is also userspace/framework work: the candidate app requests
`android.permission.VIRTUAL_INPUT_DEVICE` and creates uinput devices. The
Ace6 kernel profile does not automatically provide the Android framework
permission or device policy. `systemd-coredump` is a userspace service/socket
and its systemd/rootfs version, unit activation and `kernel.core_pattern`
definition is not present in the repository or locked to a target ROM/rootfs.

## Acceptance table

| Item | Current evidence | Status |
| --- | --- | --- |
| standard feature inheritance | profile normalizer + unit test | passed |
| EVDI source provenance | exact 14-file match at pinned candidate commit | passed, audit-only |
| EVDI C/API compilation | target `evdi.o` object | passed, object-only |
| EVDI module link/modpost | target `Module.symvers` absent | blocked |
| `create-disp` UAPI | power-mode ioctl absent in kernel candidate | blocked |
| virtual HCI | Android permission/uinput/framework path | unverified |
| systemd-coredump | systemd/rootfs/version/socket path | unverified |
| device/ROM/display pipeline | no Ace6 device definition or runtime trace | unverified |

The standalone extend locks remain blocked and the main lock does not turn
these audit candidates into a release or generic container claim. Runtime
enablement requires an ABI-matched userspace set, target Android/framework and
rootfs versions, a complete kernel build/module link, and device tests for
display, input, coredump and container lifecycle.
