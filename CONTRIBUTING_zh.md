# 贡献指南

> [English](CONTRIBUTING.md) | **中文**

小项目、单人维护、业余时间。保持简单就会被回复。

## Bug 报告

使用 [bug 报告模板](.github/ISSUE_TEMPLATE/bug_report.md)（中文模板：[bug_report_zh.md](.github/ISSUE_TEMPLATE/bug_report_zh.md)）—— 最关键的三个字段是 **ROM 版本**、**用到的 workflow 开关**、**日志**。没有这些的报告通常只会得到"请填模板"的回复，而不是修复。

开 issue 之前：先刷一次**最小构建**（全部开关关闭）。如果能开机，bug 就在某个功能开关里，模板里的开关清单就是定位手段。如果最小构建也 bootloop，请一并写进去——这直接排除了一半的补丁栈。

## Pull Request

- 每个 PR 只做**一件事**。本仓库拆分补丁是有原因的。
- 代码、注释、提交信息一律英文。
- 先跑 `./reproduce.sh --help` 看看本地路径能验证什么；改了 workflow 逻辑的 PR 应该再跑一次 GitHub Actions（那才是真实环境）。
- 改动涉及补丁时：`patches/split/` 是唯一事实来源 —— 重新生成或编辑拆分补丁，`extra/` 文件放在内核相对路径下，并确认拆分补丁仍能按序应用（`patch -p1 -F3 --batch -f < patches/split/0*.patch`）。

## 许可证

GPL-2.0，与内核一致。你贡献的代码继承该许可证。

## 响应时间

单人项目，有正职。issue 迟早会回；意图清晰的 PR 优先审阅。项目历史说明维护者在意什么：**可验证的说法胜过自信的说法**。
