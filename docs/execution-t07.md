# Ace6 T07 execution record: ReSukiSU Manual Hook 6.6

日期：2026-09-06。范围是 `ace6-resukisu-manual-6.6` 的锁定输入、源码级
Manual Hook 规则和隔离 source-preparation；不包含内核编译、刷机或真机验收。

## 结果

| 项目 | 结果 | 边界 |
| --- | --- | --- |
| Manual Hook 补丁 | 已锁定 | 精确应用到 Ace6 `6.6.142`，不代表 build 通过 |
| ReSukiSU 自动 hook 组合 | 静态验证 | 8 组 setuid/initrc/input 开关组合均通过官方 checker |
| SELinux 静态符号检查 | 静态验证 | 4 个 6.6 需要的对象通过 `static_export_check.mk` |
| source-preparation | 完成 | 见证据 JSON；只生成准备树和 manifest，不生成 Image |
| build / olddefconfig | 未执行 | 留给 T15/T25 |
| runtime / release | 未测试 / 禁止 | 留给 T26/T27 |

## 锁定顺序

1. `07_compile_fixes.patch`
2. `resukisu-kernel.link` → `ReSukiSU/kernel`
3. `ace6-resukisu-drivers.patch`
4. `ace6-resukisu-manual-6.6.patch`

这套 profile 不应用 SUSFS 或旧的 KernelSU 适配补丁。详细的符号、签名、
guard 和未选择路径见 `docs/manual-hook-rules.md`。

## 结论

T07 的 source-level blocker 已解除：Manual profile 可进入 source preparation，
但仍不能宣称已编译、可启动、可获取 root 或可发布。手工 profile 的当前状态
为 `source-ready` / `static-verified` / `not-tested` / `not-tested`。

最终 lock ID 为
`58dba9148352d94a18b6c282ec2d63f88c5276fabf38584a6391dc90dfc20dc9`；准备
manifest ID 为
`ec37996612f59d96219d2c10b84cdbacb0903b44a6ca682952f1c8f489406764`。
完整树 ID、四个步骤和静态断言见
`docs/evidence/t07-manual-hook-preparation.json`。
