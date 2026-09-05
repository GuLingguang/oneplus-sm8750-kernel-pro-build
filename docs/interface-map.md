# Legacy interface mapping

The old workflow and reproduce.sh remain available. M1 supplies the following shared input adapter; final .config, naming and packaging behavior is migrated in T14–T18. Defaults below are normalizer defaults; an explicit profile supplies its own core feature defaults.

| Canonical input | Layer | Default | Actions aliases | Local feature/identity flag |
| --- | --- | --- | --- | --- |
| `ksu_type` | `features` | `"none"` | same name | `--ksu` |
| `susfs` | `features` | `false` | `susfs_enable` | `--susfs` |
| `lz4_zstd` | `features` | `false` | same name | `--lz4` |
| `lz4kd` | `features` | `false` | `lz4kd_enable` | `--lz4kd` |
| `show_all_algos` | `features` | `false` | same name | `--show-all-algos` |
| `zram_writeback` | `features` | `false` | same name | `--zram-writeback` |
| `baseband_guard` | `features` | `false` | same name | `--bbg` |
| `cve_patch` | `features` | `false` | same name | `--cve` |
| `better_net` | `features` | `false` | same name | `--better-net` |
| `bbr` | `features` | `false` | `bbr_enable` | `--bbr` |
| `kpm` | `features` | `false` | `kpm_enable` | `--kpm` |
| `rekernel` | `features` | `false` | `rekernel_enable` | `--rekernel` |
| `ghost_task` | `features` | `false` | same name | JSON input |
| `droidspaces` | `features` | `"false"` | same name | `--droidspaces` |
| `kernel_suffix` | `identity` | `""` | same name | `--suffix` |
| `build_user` | `identity` | `"Lingguang"` | same name | `--user` |
| `build_host` | `identity` | `"kernel-builder"` | same name | `--host` |
| `build_time` | `identity` | `""` | same name | `--time` |
| `tag` | `identity` | `""` | same name | JSON input |
| `attribution_enable` | `identity` | `true` | same name | `--no-attribution` |
| `release_enable` | `artifacts` | `false` | same name | JSON input |
| `ccache_update` | `artifacts` | `false` | same name | JSON input |
| `ccache_debug` | `artifacts` | `false` | same name | JSON input |
| `debug_skip_build` | `artifacts` | `false` | same name | JSON input |
| `ccache_enable` | `artifacts` | `true` | same name | JSON input |
| `artifact_mode` | `artifacts` | `"ak3"` | same name | JSON input |
| `independent_modules` | `artifacts` | `false` | same name | JSON input |

| Other existing interface | M1 preservation / follow-up |
| --- | --- |
| `--out`, `OUT_DIR`, `--clean`, `WORK_DIR` | Legacy execution controls remain; new preparer uses a fresh `--work` and never deletes an existing tree |
| `REPO_BASE` | Legacy download-origin control remains; new preparer requires explicit locked source URLs |
| `KERNEL_SRC` | New preparer accepts a clean exact-HEAD provider and clones it; legacy reproduce still mutates in place until T15 |
| azram-backing | Separate KSU module retained; device/partition checks pending T20 |
| tcp-config / WebUI | Separate module retained; permission boundary and clean build pending T19 |
| selinux_perf | Separate module retained; rule/effect review pending T21 |
| AK3 / Image / boot.img / all | Output intent retained, actual output contract pending T18; no M1 kernel output |
| Release and public ccache updates | Inputs retained; no publication in the new entry; debug cannot request either |
| GhostLock/CVE compatibility switch | Explicit no-op note, no nonexistent 08 patch |
