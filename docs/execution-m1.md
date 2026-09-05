# Ace6 任务执行记录：首批 T01–T05

日期：2026-09-05。输入材料：`ace6-kernel-project-dossier.md`、
`ace6-kernel-task-plan.md`。执行范围遵循计划第 8 节的首批任务；
原材料作为历史规划保留，本文件登记实际进度。

## 状态结论

| 任务 | 本批结果 | 目标 / 输出 | 未完成事项 |
| --- | --- | --- | --- |
| T01 | 完成 | 下文检查点、`interface-map.md`、legacy inventory、历史日志摘录 | 无新增真机证据；历史问题继续保留 |
| T02 | 首批契约实现完成 | 四层 schema、字段映射、规范化配置、source-preparation manifest、样例 | 真正 build manifest 在 T15/T18 扩展；不冒充已完成构建身份 |
| T03 | **部分完成** | kernel/modules/devicetrees/ReSukiSU/SUSFS 精确 SHA，Clang digest，Actions pin，vendored hash | 宿主环境、apt/mkbootimg、KPM 二进制、部分功能原始上游出处未锁全；完整构建不可复现 |
| T04 | profile 骨架及组合规则完成 | 8 个 profile、standard→extend 继承、兼容矩阵和早期拒绝 | Manual/SUSFS/容器/Re:Kernel 的功能契约及构建/真机未通过 |
| T05 | 共用框架实现并通过测试 | `scripts/profile.py`，精确解析、隔离源码、累计 patch/copy、失败记录和 manifest | 目标 SUSFS/可选功能 patch set 未建立；相应 profile 继续受阻 |
| T06–T27 | 未开始 | 按原计划依赖继续 | 没有把首批框架成果计入功能修复、CI 编译或真机验收 |

M1 的完整出口条件尚未满足，主要受 T03 和目标集成契约约束。
本批交付可审阅、可测试的框架；不是宣称 T01–T05 所有最终验收条件已经满足。

## T01：历史检查点和差异

- 远端 `fix/susfs-makefile-integration` 在实施前仍是
  `c303fae1f308cd8c0a01b22f28b5bd34de6ab21a`，与档案一致。
- 内核锁定为 `cb967c26c2c5689108fa28d3c3be2aba6ba71f5f`，实际 `6.6.142`。
- workflow 的实际默认输入是 `ksu_type=none`、`susfs_enable=false`；
  run `33852164627` 手动启用了 ReSukiSU + SUSFS。
  因此将“默认成功路径”修正为“历史成功用例”，避免覆盖范围混淆。
- 历史 build job `100957196370` 成功；Re:Kernel、BBG、Droidspaces、
  压缩库等可选补丁步骤跳过，Release job 也跳过。
- 9 个补丁的 workflow 累计顺序为：**07 → 00 → 01 → 02 → 03 → 04 → 05 → 06 → 09**。
  历史成功用例只执行前三个；没有 08。
- 每个 legacy patch、额外源码、AK3、config 和本地构建二进制的字节 hash
  见 `manifests/legacy-c303fae.inventory.json`。这证明项目快照内的内容身份，
  不能代替其原始上游 commit 归属。
- Issue #3 只读核对仍为 open；本批没有评论或关闭它。
- 旧 scratch 项目/内核工作区存在本地改动；本批另建 checkout，未清理或覆盖它们。
- `c303fae` 留在 Git 历史中作 legacy 对照；不是已验证安全的刷机回退包。

证据：`docs/evidence/legacy-run-33852164627.txt`、Git 历史、
`manifests/legacy-c303fae.inventory.json`、`docs/interface-map.md`。

## T02/T04：接口、profile 和状态

实现使用 Python 标准库与 JSON，不依赖浮动安装的 Python 包。
Actions 风格 JSON 和本地 feature/identity flags 进入同一 normalizer；
规范化配置再次输入得到相同 canonical identity。

保留原有 feature、署名、缓存、debug、产物和发布输入。
拒绝 none+SUSFS、SUSFS+Droidspaces、隐式混合 hook、冲突别名、错误类型、
缺 KPM pin、实验发布、debug 发布及无 KSU 的模块输出。
standard/extend 的继承在代码中合并并测试；Re:Kernel 明确依附 Manual 基础 profile。

具体字段、优先级、命令、manifest 身份和输出边界见 `profile-contract.md`；
各 profile 的当前门槛见 `compatibility.md`。旧 workflow/reproduce.sh 仍是 legacy
构建入口，只有 Actions 引用在本批固定；新规则尚未接管旧入口，T15 再统一。

## T03：版本选择及缺口

| 来源 | 本批固定身份 / 证据 |
| --- | --- |
| kernel | `cb967c26c2c5689108fa28d3c3be2aba6ba71f5f`；真实获取并检出 |
| modules | `7d5d39a539ddc2b53054e8fa7ae2b5890dccae54`；远端解析并真实检出 |
| devicetrees | `ebb25e3526ad84cc5a1090a5a9242f33ff087bf2`；远端解析并真实检出 |
| ReSukiSU 候选 | `9d0ff6aea9e25fc7dd26f4643175a41f68375e5e`；历史 log 短 SHA + 本地完整 Git commit |
| SUSFS 官方候选 | `937215cb3a1b1f333d764c366c7a49972fa8e7a0`；官方 GitLab 分支解析及 `v2.3.0` header |
| Clang | AOSP r563880c；Release API 提供 SHA-256 `ee099045b1323087e0c1d3962d1d8c582fcdef45986976b82886a6177f142763` |
| Actions | checkout/cache/upload 固定历史 run 的实际 SHA；download/github-script 解析并固定 tag SHA |
| AK3/config/local binary | lock 中逐文件 SHA-256；未生成 AK3 |
| 功能上游候选 | `manifests/upstream-candidates-2026-09-05.json`，仅登记候选；未冒认旧 patch 的原始出处 |

Clang 压缩包大小 1,161,295,162 字节；本批没有下载并本地校验它。
KSU version code `35115` 仅作为历史明确输入登记，实际确定性注入待 T15。
apt 包版本、runner image digest、mkbootimg 及 KPM binary 仍未锁定。
`build_environment.status=not-fully-locked`，字节级可复现结论保持 false。

ReSukiSU/SUSFS 只是选定候选，没有通过配对契约。
已确认候选 ReSukiSU 的 SUSFS faccessat 参数类型为 `struct filename **`；
必须在 T06 重建整套适配后再由 T07 检验，不能据此直接启用旧 patch。

## T05：实现和验收

`normalize` / `check` / `prepare` 是统一入口。完整 SHA 检出、profile 和本地
hash 校验先行；外部源码必须干净且 HEAD 匹配，补丁仅作用于隔离副本。
按 lock steps 累计执行，每步先 `git apply --check`，不使用 fuzz 或失败继续。
失败保留独立 failure.json，后续步骤不执行；已有成功工作目录不复用。

本地测试 **15 项全部通过**，包含多组负例：

- Actions/local flags/normalized JSON 的一致性和特殊文本字面值保留；
- profile 继承、冲突、错误类型、未锁定来源/资源和配置 hash 拒绝；
- 两个相互依赖且名称顺序相反的 patch，验证按 lock 累计而非排序执行；
- 中途失败阻止第三步，外部原树保留；重复新目录执行得到相同 manifest ID；
- dirty/untracked/assume-unchanged 外部树、SHA/hash 错误及路径逃逸拒绝；
- 被阻断 profile 在下载/工作区创建前退出。

真实 minimal 验收先从远端取得三套锁定源码，再用干净本地副本核验最终入口。
运行结果、最终 manifest ID 和树身份见 `docs/evidence/m1-validation.json`
及 `docs/evidence/minimal-preparation.manifest.json`。
kernelFwUpdate/Kconfig 和设备树 vendor 链接有实际目标。
这里只应用 `07_compile_fixes.patch`，不包含旧 KSU/SUSFS 或可选功能补丁。

没有执行内核编译、olddefconfig、CI dispatch、刷机或 runtime test；
没有生成/发布 Image、AK3、boot.img 或 Release。T14/T15 仍需证明 minimal
最终配置确实关闭各功能，不能从这里的规范化 false 值推断内核配置已关闭。

## 续接入口

先收齐 T03 的构建环境和所需资源证据，明确选定配对的补丁序列；
随后按 T06/T07 重建并验证 SUSFS Inline。Manual/容器/Re:Kernel 等 profile
继续保持各自 blocker。构建矩阵由 T25 执行，真机由 T26 独立验收。
后续不得把本文件的框架测试结果当成旧功能风险已经解决的证据。
