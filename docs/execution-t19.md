# T19：tcp-config 模块权限边界与 WebUI 构建审查

日期：2026-09-07。记录时源码修改和验证均在本地完成，尚未提交或上传；真机完成旧模块备份、替换、重启、脚本和 WebUI 点击验收。后续仓库整理已在本地提交，仍未上传。

## 结论

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| 特权入口 | 已收敛 | 只保留 KernelSU WebUI 的 `kernelsu.exec()` 通道 |
| TCP/nc fallback | 已移除 | TCP 无法证明 Android 调用者身份，旧 8090 root 控制面不安全 |
| 参数校验 | 静态通过 | algorithm 和 qdisc 均使用固定白名单 |
| 状态文件 | 已加固 | 不再 `source`；只解析预期字段，原子写入，权限 600 |
| WebUI 干净构建 | 通过 | `npm ci` + `npm run build`，依赖来自 `package-lock.json` |
| 依赖入库 | 已清理 | 已提交的 `webui-src/node_modules` 从本地 diff 移除并加入 ignore |
| shell/JS 语法 | 通过 | `sh -n` 和 `node --check` |
| 真机模块行为 | 通过（显示修复候选待安装） | 旧 `v1.0` 已备份并替换为本地 `v1.1`；重启后 `boot=1`、无 `*:8090`，脚本和 WebUI 均验证 `cubic/fq` |

## 安全决策

旧实现用 KSU busybox `nc` 在 `:8090` 监听，并由无认证 HTTP 请求调用 root
`sysctl`。仅绑定 loopback 也不能解决本地 Android 应用的调用者认证问题，
因此没有加临时 token 或继续保留 socket，而是删除 fallback。正常 KernelSU
WebUI 仍通过已有的本地特权桥调用同一个 `apply.sh`。

`service.sh` 启动时不再执行状态文件；它只接受 `cubic`、`bbr`、
`kerneldflt` 和 `fq`、`fq_codel`、`pfifo_fast`，不匹配就停止。`apply.sh`
同样执行白名单检查，并先成功设置 sysctl，再以临时文件和 `mv` 原子更新状态。

## 边界

此任务证明了源码权限边界和 WebUI 构建链；新版代码不再提供 8090。
真机上的旧版模块已备份并替换为本地 `v1.1`；重启后系统正常启动，旧 8090
监听未恢复，正式 `apply.sh` 和 KernelSU WebUI 点击均可将设备收敛到支持的
`cubic/fq`。验收同时发现“内核编译默认”只影响显示的解析 bug，已在本地源码
和新候选包修复；新候选尚未替换真机。
