# CI checks

The repository has three automation layers:

1. `scripts/ci.py` is the fast, network-free repository gate. It validates
   profile/lock pairs, build dry-run identities, shell syntax, workflow action
   pinning, generated-file placement, whitespace, and the Python test suite.
2. `.github/workflows/build.yml` is the explicitly dispatched kernel build.
   It owns source fetching, toolchain installation, compilation, packaging,
   and the separate release gate.
3. `.github/workflows/debug-build.yml` is the bounded validation workflow.
   Its `fast` scope checks every normalized feature combination, all profile
   preflight results, the WebUI bundle, and the upstream checker entrypoint.
   Its `compile` scope builds three representative profiles; `full` builds all
   seven profiles currently allowed through build preflight and runs the
   report-only drift check. The two standalone Droidspaces `extend` profiles
   are checked as expected blockers and are not sent to the compiler.

The debug compiler uses `ACE6_BUILD_TIMEOUT_SECONDS` inside
`scripts/build.py`. The command starts each compiler invocation in its own
process group, so a timeout also terminates compiler children. The workflow
keeps two profiles in flight at most and stores reports under `work/_tmp/`.

The TCP configuration WebUI has its own CI job. It installs only the locked
`package-lock.json` dependency graph, rebuilds `webroot/index.js`, and fails if
the checked-in bundle is stale. `node_modules` is never a repository input or a
KSU runtime payload.

Generated files follow this layout:

- `work/`: isolated source trees and build intermediates;
- `work/_tmp/`: logs, drift reports, CI reports, temporary downloads, and
  other disposable intermediates;
- `out/`: build artifacts and the copied build manifest;
- `.toolchains/`: local locked toolchain cache, never a source input.

The CI gate does not access a device, change locks, publish releases, update
public ccache, or upload files. Those operations require their existing
explicit workflow or runtime gates.
