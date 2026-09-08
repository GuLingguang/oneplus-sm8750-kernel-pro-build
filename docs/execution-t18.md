# T18 — artifact and release boundaries

## Mapping

| Request | Result | Boundary |
| --- | --- | --- |
| `artifact_mode=ak3` | Supported | Produces one AnyKernel3 zip containing the built `Image`; it is the only kernel artifact intended for the manual OFRP/recovery flashing workflow. |
| `artifact_mode=image` | Supported locally | Produces a raw development `Image`; no ramdisk, DTB or AVB packaging, so it is not a flash instruction. |
| `artifact_mode=boot` | Blocked before compilation | Requires a target boot input set; the builder no longer fabricates a boot image with guessed header values. |
| `artifact_mode=all` | Blocked before compilation | It would include the unsupported `boot.img` path, so no partial “all” artifact claim is made. |
| `independent_modules=true` | Supported with KSU | Produces one standalone zip per self-authored module. These zips are not copied into AK3 and must be installed separately in KernelSU. |
| `release_enable=true` | Separate publication gate | Publication remains blocked by T25–T27 until build/runtime evidence and handoff material are complete. No release was made. |

## Checks

- The preflight table accepts `ak3`, `image`, and a ReSukiSU profile with
  `independent_modules=true`.
- `boot` and `all` reject with the explicit T18 boot-input blocker.
- A temporary packaging smoke test produced one AK3 zip plus three standalone
  module zips (`azram-backing`, `selinux_perf`, `tcp-config`). The module zips
  exclude `webui-src` and `node_modules`.
- Existing AK3 outputs were checked through their build manifests, ZIP hashes,
  and `zip -T`; no Image or boot.img is being presented as a flashable output.

## Installation boundary

The current intended device flow is: manually flash the AK3 zip in OFRP, then
install selected standalone module zips through KernelSU only after their own
device/runtime gates pass. The AK3 script's optional `zram.zip` and `kpn.zip`
hooks are not used for these self-authored modules.
