# CI checks

The repository has two separate automation layers:

1. `scripts/ci.py` is the fast, network-free repository gate. It validates
   profile/lock pairs, build dry-run identities, shell syntax, workflow action
   pinning, generated-file placement, whitespace, and the Python test suite.
2. `.github/workflows/build.yml` is the explicitly dispatched kernel build.
   It owns source fetching, toolchain installation, compilation, packaging,
   and the separate release gate.

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
