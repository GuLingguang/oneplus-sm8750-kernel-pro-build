# Droidspaces extend 6.6 rules

Status: both standalone extend profiles are **build-capable experimental
profiles** with runtime warnings. Their locks now include the standard kernel
configuration, the extend integration, and the source-locked EVDI driver.

`extend` is not a larger kernel configuration label. It inherits the
standard container baseline and adds a separate virtual-display/userspace
requirement set. The two profile identities are preserved:

| Profile | Base inheritance | Hook | SUSFS | Current status |
| --- | --- | --- | --- | --- |
| `ace6-droidspaces-extend-6.6` | standard | none | off | build-capable; T11 runtime warning |
| `ace6-droidspaces-resukisu-extend-6.6` | ReSukiSU standard | Manual | off | build-capable; T11 runtime warning |
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
commit: d3b85f3251beae4bc8481538f37d13b7f30abde0
tree:   5e437ce3db2ccf3f73a4d5f876d716105886b736
```

The candidate was compared against the local clone and is recorded as audit
evidence. The legacy `05_droidspaces.patch` is not applied wholesale: it also
contains NTSYNC, SYSVIPC layout edits and the rejected global `ghost_task`
workaround. Both standalone extend locks and the main lock copy this exact EVDI
source with per-file hashes and apply a separate Kconfig/Makefile integration
patch. The EVDI source now includes the power-mode ioctl used by the selected
`create-disp` candidate.

With the target 6.6 configuration, `CONFIG_DRM_LINDROID_EVDI=y` and the EVDI
Kconfig/Makefile connection applied in a disposable tree, all EVDI source
objects combine into `drivers/gpu/drm/evdi/built-in.a`. Both standalone extend
profiles then completed a full Image build and AK3 package check with 30 jobs.
Device checks remain open.

## Userspace and ABI boundary

The current candidate snapshots used for audit are:

| Component | Ref / commit | Role | Acceptance |
| --- | --- | --- | --- |
| `vendor_lindroid` | `lindroid-22.1` / `eadbb70f13209133d96a5355464388db8c6578de` | Android app, daemon, HWC/input integration | candidate only |
| `vendor_extra` | `lindroid-21` / `39da805f20765a245f93f2d4ab6227ba40e1ce35` | Android build extras | candidate only |
| `libhybris` | `lindroid-21` / `29e0fa6da0166261f6b9437582fe2d56bab8530c` | Android graphics bridge | candidate only |
| `external_lxc` | `lindroid-21` / `4e3a3630fff3dc04e0d4a761309f87f248e40b17` | container runtime | candidate only |
| `create-disp` | `master` / `46c1d0414b3acb28b5902a2cb16b5ee40c1898ce` | EVDI display userspace | ABI matched; runtime pending |

The `create-disp` candidate defines and calls
`DRM_IOCTL_EVDI_SET_POWER_MODE` (`0x0f`) when
`TARGET_USES_REAL_HWC` is not defined. The locked EVDI UAPI now defines the
same command and the driver registers its handler. The display path still needs
an Ace6 framework build and device test.

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
| EVDI source provenance | exact 14-file match at pinned candidate commit | passed |
| EVDI C/API compilation | target `built-in.a` | passed in both full builds |
| EVDI module link/modpost | EVDI selected as built-in | not applicable for this profile |
| `create-disp` UAPI | power-mode ioctl present in both candidates | passed, runtime pending |
| virtual HCI | Android permission/uinput/framework path | unverified |
| systemd-coredump | systemd/rootfs/version/socket path | unverified |
| device/ROM/display pipeline | no Ace6 device definition or runtime trace | unverified |

The extend locks now admit kernel preparation and compilation. They do not turn
the candidate userspace into a release or generic container claim. Runtime
enablement requires the target Android/framework and rootfs versions, a
complete kernel build, and device tests for display, input, coredump and
container lifecycle.
