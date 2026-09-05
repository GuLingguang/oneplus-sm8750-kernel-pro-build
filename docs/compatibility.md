# M1 capability and compatibility matrix

All rows are **not built and not runtime tested by M1**. These statuses describe
the new profiles, not the historical run. `check` success only permits source
preparation. Profiles preserve selectable intents while rejecting unavailable
integration paths.

| Profile | Base / inheritance | Hook | SUSFS | Container | Source preparation / outstanding gate |
| --- | --- | --- | --- | --- | --- |
| `ace6-minimal-6.6` | Ace6 6.6.142 | none | off | off | available; final config/build pending T14/T15/T25 |
| `ace6-resukisu-manual-6.6` | Ace6 + fixed ReSukiSU candidate | Manual | off | off | blocked T07 |
| `ace6-resukisu-susfs-inline-6.6` | Ace6 + fixed ReSukiSU/SUSFS candidates | SUSFS Inline | on | off | source-ready; static contract verified; build/runtime pending T07/T25/T26 |
| `ace6-droidspaces-standard-6.6` | Ace6 | none | off | standard | blocked T09/T10 |
| `ace6-droidspaces-extend-6.6` | inherits standard | none | off | extend | blocked T09/T10/T11; experimental |
| `ace6-droidspaces-resukisu-standard-6.6` | inherits standard + ReSukiSU | Manual | off | standard | blocked T07/T09/T10 |
| `ace6-droidspaces-resukisu-extend-6.6` | inherits ReSukiSU standard | Manual | off | extend | blocked T07/T09/T10/T11; experimental |
| `ace6-rekernel-experimental` | inherits ReSukiSU Manual | Manual | off | off | blocked T07/T12/T13; experimental |

The fixed ReSukiSU Kconfig presents Manual, Tracepoint and SUSFS Inline as a
choice. M1 explicitly chooses Manual for the root-without-SUSFS candidate and
adds no Tracepoint support promise. Its hooks still need T07's version-specific
contract. Inline cannot silently combine with another hook mode.

Rejected before preparation: none+SUSFS; SUSFS+Droidspaces; conflicting core
inputs/profile; mixed/unknown hook input; ghost_task without containers; KSU module
output without KSU; Re:Kernel/extend formal release; debug skip plus publishing;
KPM without a binary version/hash and kernel compatibility record. Every profile's
actual release capability remains false until independent build/runtime evidence.

The extend profiles merge standard capabilities and blockers in code; inheritance
is tested. Neither EVDI nor userspace HCI/systemd-coredump availability is inferred
from this structural inheritance. No ghost_task workaround is applied by M1.
