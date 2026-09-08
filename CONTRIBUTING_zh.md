# 贡献指南

> [English](CONTRIBUTING.md) | **中文**

本项目由单人维护。请将报告和改动控制在明确范围内。

## Bug 报告

使用 [bug 报告模板](.github/ISSUE_TEMPLATE/bug_report.md)（中文模板：[bug_report_zh.md](.github/ISSUE_TEMPLATE/bug_report_zh.md)）。请至少提供 **ROM 版本**、**使用的 workflow 开关**和**日志**；缺少这些信息的报告可能会被退回补充。

开 issue 之前：先刷一次**最小构建**（全部开关关闭）。如果能开机，问题通常位于某个功能开关，模板中的开关清单可用于缩小范围。如果最小构建也 bootloop，请一并记录，因为这有助于排除功能开关因素。

## Pull Request

- 每个 PR 只做**一件事**。本仓库拆分补丁是有原因的。
- 代码、注释、提交信息一律英文。
- 先跑 `python3 scripts/ci.py` 和 `./reproduce.sh --help` 检查本地规则；改动 workflow 逻辑的 PR 还应运行一次 GitHub Actions，以覆盖托管 runner 环境。
- 改动涉及补丁时：`patches/split/` 是唯一事实来源 —— 重新生成或编辑拆分补丁，`extra/` 文件放在内核相对路径下，并确认拆分补丁仍能按序应用（`patch -p1 -F3 --batch -f < patches/split/0*.patch`）。

## 许可证

GPL-2.0，与内核一致。贡献代码适用同一许可证。

## 响应时间

本项目由单人利用业余时间维护。信息完整、目标单一的 issue 和 PR 将优先审阅。项目历史优先记录**可验证的结论**，不采用缺乏证据的推断。
