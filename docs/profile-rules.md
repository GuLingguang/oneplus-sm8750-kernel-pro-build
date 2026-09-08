# Profile, build and publication rules

Status: the shared profile/build path is implemented; this document still does
not turn a local build into runtime or release acceptance. `scripts/profile.py`
owns normalization, locks and preflight; `scripts/build.py` is the single local
and Actions build implementation.

## Four input layers

| Layer | Responsibility | Rule |
| --- | --- | --- |
| `version` | Select an exact profile/lock and one hook mode | Explicit profile must agree with root/SUSFS/container/Re:Kernel choices |
| `features` | Select features, including explicit false values | Strict booleans/enums; unsupported combinations rejected before downloads |
| `identity` | Suffix, user, host, time, attribution, tag | Literal Unicode strings; control characters rejected; never evaluated as shell |
| `artifacts` | Output selection and build/cache/publication switches | Output intent only; preparation produces no Image, AK3, boot.img, module or Release |

The complete typed field catalog, defaults and aliases are in
`schemas/input-fields.json`; `schemas/config.schema.json` defines the normalized
form. JSON is used to avoid a YAML runtime dependency and implicit YAML boolean
conversion (especially the legacy string `droidspaces="false"`).

Priority: explicit user fields > profile feature defaults > field defaults.
An explicit core field that conflicts with the selected profile is an error,
not a request to silently change profiles. Without a profile, the adapter selects
one from the explicit root/SUSFS/container/Re:Kernel inputs. Re:Kernel alone
selects its declared ReSukiSU Manual base. Equal aliases are accepted; conflicting
aliases, unknown fields, duplicate JSON keys and implicit truthiness are rejected.
Normalized input is complete and strictly typed; legacy Actions input accepts
boolean JSON values or exactly `"true"`/`"false"` strings.

`normalize` establishes a valid configuration shape/combination. `check` also
validates the lock and reports whether source preparation is available. The
build preflight permits statically implemented feature patches while retaining
warnings for userspace/device-only gates. Hard blockers still stop before
source preparation. No local command publishes or uploads anything;
`release_allowed` remains false until runtime, rollback and handoff evidence
are complete.

The automatic main Release composition is
`ace6-main-release-compat-6.6`: ReSukiSU + SUSFS Inline + Droidspaces extend +
Re:Kernel. SUSFS and Droidspaces are not intrinsically exclusive; the lock
separates standard NTSYNC, EVDI integration and Re:Kernel patches and excludes
the rejected `ghost_task` workaround. LZ4/zstd, LZ4KD, all algorithm backends,
writeback, Baseband Guard, Better network and BBR remain independent toggles.

## Commands

```sh
# Minimal, matching current workflow defaults (none / SUSFS false).
python3 scripts/profile.py normalize
python3 scripts/profile.py check

# Actions-style JSON and local flags use the same normalizer.
python3 scripts/profile.py normalize --inputs examples/ace6-minimal-6.6.inputs.json
python3 scripts/profile.py normalize --legacy-args --ksu resukisu --susfs --user Lingguang

# Source preparation: exact commits, fresh workspace, ordered steps.
python3 scripts/profile.py prepare --work /absolute/new/work-directory

# Reuse CLEAN local repositories as source providers; they are never patched.
python3 scripts/profile.py prepare --work /absolute/new/work-directory \
  --source kernel=/absolute/clean/kernel \
  --source modules=/absolute/clean/modules \
  --source devicetrees=/absolute/clean/devicetrees

python3 -m unittest discover -s tests -v

# Main Release feature composition, local-only dry run.
python3 scripts/build.py --ksu resukisu --susfs --lz4 --lz4kd \
  --show-all-algos --zram-writeback --droidspaces extend --bbg --cve \
  --better-net --bbr --rekernel --dry-run

# A real local build uses a fresh work directory and an explicit 30-job limit.
python3 scripts/build.py --workflow --jobs 30 \
  --work work/main-release-compat-6.6 --out out/main-release-compat-6.6
```

`KERNEL_SRC` is recognized by both preparer/build entry points as an alternative
to `--source kernel=...`; setting both is an error. External HEAD must match the
lock, and tracked/untracked/ignored changes, assume-unchanged and skip-worktree
entries are rejected. The build entry clones an external provider into its
fresh workspace and never patches the provider in place.

`--legacy-args` accepts the legacy feature/identity flags and must come last.
`--out`, `--clean`, `WORK_DIR`, `OUT_DIR`, and `REPO_BASE` remain legacy execution
interfaces; they are not interpreted as binary identity. In the new preparer,
`--work` must be fresh, `--output` must not already exist, and changing repository
origins requires a reviewed lock change. There is no destructive clean option.

## Lock, manifest and reproducibility

`manifests/locks/*.lock.json` are fixed inputs. Their source `reference` fields
are descriptive only: fetch/checkout uses full `commit`, never a branch fallback.
Profile content, local patch/config/AK3/binary bytes, toolchain archive identity
and Actions references are recorded. The exact steps array is authoritative;
neither directory listing nor lexical patch names determine order. Operations
carry `upstream`, `integration`, or `feature` provenance layers. Every patch/copy
must appear in the hashed inventory. The legacy 00/01 patches are deliberately
absent from the new source-preparation locks; T06 constructs their replacements.

The standard-library validator supports the documented subset used by the
checked-in schemas and rejects unsupported schema keywords. It is not advertised
as a general-purpose JSON Schema implementation.

Preparation verifies inputs before network access, uses a fresh staging directory,
checks the cumulative tree before each `git apply`, stops on the first failure,
and records initial and prepared Git tree identities. No fuzzy `-F3`, reverse
fallback, ignored errors, or automatic version updates are used. Source
submodules need explicit future resolver support and are rejected if encountered.
On failure, the isolated `*.preparing-*/failure.json` and partial trees remain for
inspection; the requested final directory does not become a successful result.
Retry with a fresh destination. A successful directory contains `manifest.json`
and a copy of the exact `lock.json` used.

Canonical identity is SHA-256 of UTF-8 JSON with sorted keys, compact separators
and literal Unicode. `config_id` covers normalized inputs; `lock_id` covers the
lock; `manifest_id` covers the manifest before its own ID is added. Machine-local
paths and wall-clock preparation time do not affect successful manifest identity.

The M1 manifest schema is intentionally limited to **source preparation**:
`build=not-run`, `runtime=not-tested`, and no artifacts. It must not be passed off
as a build manifest. T15's `build-manifest.json` records resolved build inputs,
final `.config`, actual tool versions and product hashes; T18 may extend the
artifact mapping. T26 stores
runtime evidence separately, keyed by build manifest ID and artifact SHA-256;
it must not edit the original build identity.

The toolchain digest is recorded in the lock and is verified before an actual
build. Host image, apt package versions and mkbootimg are not fully locked.
Empty build time and auto tag are valid requests, and their resolved values
enter the build manifest before handoff. The manifest also records the build
preflight report and a publication object with `requested`, `allowed` and
`published=false`; a requested Release is auditable without being published.
KBUILD build number, timezone, environment, tool versions, user/host, KSU
identity and packaging timestamps must still be fixed before asserting
byte-identical builds. **A source lock is not a byte-identical-build claim.**

## Output and feature boundaries

`artifact_mode` retains `ak3` and admits an explicit local `image` intent.
`ak3` produces the AnyKernel3 package; `image` produces a raw development
Image. `boot` and `all` remain schema-compatible legacy intents but are blocked
before compilation because a valid target boot input (ramdisk, DTB and AVB
metadata) is not supplied; the builder never fabricates a boot.img from fixed
guesses. With `independent_modules=true`, the self-authored KSU modules are
packaged as separate module zips and are not inserted into AK3. No output here
is asserted flashable without the target-specific runtime gate.

False BBR/LZ4KD/writeback requests remain false in normalized inputs. T14 and
the common entry verify the corresponding final `.config` settings, including
the selected Droidspaces/Re:Kernel/KSU symbols and the all-algorithms set;
writeback backing-device behavior and all device claims remain later gates.
`cve_patch` is retained as an explicit no-op and produces an explanatory note.
Debug skip cannot request a Release or public cache update and never results in
a compiled-kernel success claim. Release requests are recorded as intent, but
the workflow Release job also requires the build manifest's
`release_allowed=true`; current experimental/runtime-pending profiles do not
produce that value. Publication remains a separate explicitly authorized
action.
