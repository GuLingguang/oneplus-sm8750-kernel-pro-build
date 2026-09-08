# Ace6 T09 执行记录：Droidspaces standard 6.6

日期：2026-09-06。范围是建立无 SUSFS 的 standard 内核基线，并把
ReSukiSU standard 作为独立的非 SUSFS Manual Hook 变体接入。没有进行完整
内核、刷机、容器或真机验收。

## 结果

| 项目 | 结果 | 边界 |
| --- | --- | --- |
| standard profile | source-ready | `ace6-droidspaces-standard-6.6`，SUSFS 关闭 |
| ReSukiSU standard | source-ready | `ace6-droidspaces-resukisu-standard-6.6`，Manual Hook，SUSFS 关闭 |
| 配置 fragment | 42/42 保持为 `y` | `olddefconfig` 后核对；fragment 独立于历史 final config |
| SYSVIPC kABI | 累计补丁通过 | 仅源代码/kABI 布局适配，未作 vendor module ABI 结论 |
| NTSYNC | 对象编译通过 | none 与 ReSukiSU Manual 两个隔离配置均通过 |
| source preparation | 两个 profile 均完成 | standard 4 步；ReSukiSU standard 7 步 |
| SUSFS 冲突 | 提前拒绝 | `resukisu + SUSFS + droidspaces=standard` 在下载/补丁前失败 |
| ghost_task | 保持独立 | `ghost_task=true` 仍由 T10 blocker 拒绝；T09 patch 不含 `kernel/pid.c` |
| build/runtime/release | 未测试 / 禁止 | 留给 T25/T26/T27 |

## 锁定输入和准备结果

| Profile | Lock ID | Manifest ID | kernel prepared tree |
| --- | --- | --- | --- |
| standard | `11b6346efbe27e7742c728dc9b6bb9688a6947ce1e0571989f4887b742fae07b` | `413386bc182a70b46b30ed4162a655e930cbedb87696fd7fea933b35887151a6` | `5a877e4eef951fce1d6ea0d022291ec43e95ddb6` |
| ReSukiSU standard | `acbf1ca682f9eed628a9ed0487a592f0c372f8348e1ed083bad0455fff571685` | `4bcf14b9e1f681cb10b4d00e637b46e520134c31bae46a573338ebc440364304` | `a6247e0da76abc373192e7df0c30c483cc1ecdc9` |

Both preparations used the exact locked Ace6 kernel/modules/devicetrees and
ReSukiSU commits. The external source providers were checked clean before the
isolated preparation; no provider tree was modified.

## Configuration evidence

The none configuration after merge and `olddefconfig` is
`8612298ff33292a2cbcb5d0c96d6aa3111de89269c9561056497e7463fcda053`.
The ReSukiSU Manual configuration is
`cc3a980ee593af0907dd93a6aa886e7b58ca4ab180a642df5e07bee461016e36`.
Both retain `CGROUP_DEVICE`, `CGROUP_PIDS`, `BRIDGE_NETFILTER`, `NTSYNC` and
the other fragment settings as `y`. The ReSukiSU variant additionally records
`KSU=y`, `KSU_MANUAL_HOOK=y`, `KSU_TRACEPOINT_HOOK=n` and `KSU_SUSFS=n`.

The resulting NTSYNC object hashes are:

```text
none:       7677a977c283361593322fc7d1f3fc9b9043e0374ee2bf344bb989cd4e0c99e8
ReSukiSU:   c8030f53967f0f9347a978bb298f252142b33f03b05ff0b6026228954dab8161
```

These are object-level checks only. The host lacked `bc`, so the disposable
HZ=250 helper already used in the T08 isolated checks was supplied; no helper
was added to the repository.

Detailed machine-readable evidence is in `docs/evidence/t09-droidspaces-standard.json`.
