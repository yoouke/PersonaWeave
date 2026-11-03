# 验证记录

2026-11-03（Asia/Shanghai 执行期间）/ 开发预览

实际运行：13 项 Python unittest 通过；JavaScript 语法检查通过。JSON-RPC 测试使用本地模拟进程，验证审批请求与 RPC 响应交错处理；没有调用付费模型，没有登录真实 QQ。

来源核验：DSH 官方 SDK protocol types、SDK/headless README、CLI 帮助、headless JSON stream 实现。协议采用 newline-delimited JSON-RPC 2.0；assistant/message 数据位于 data.message.content；turn/end 检查 data.reason.kind。

待外部环境：Windows WebView2/托盘/开机自启、凭据库、Node 下载与校验、npm DSH 安装兼容性、NapCat release 结构与扫码、真实 OneBot 往返、真实模型任务、审批取消、重启恢复。

当前测试不证明端到端验收完成。所有未实现功能见 README。

补充打包配置：PyInstaller spec 显式包含页面资源、WebView2 与凭据库后端；Inno Setup 用户级安装脚本；main 推送触发 Windows 构建及冻结程序 HTTP 冒烟检查。新增同数据目录单实例 OS 文件锁及测试。上述 Windows 构建配置未在 Windows 或 GitHub Actions 实际执行。

## GitHub Windows 构建验证

源码提交：`4634859b16b463c6622daeb3ecb3f10c176a7669`。

- Linux 与 Windows 的 13 项 unittest 均通过。
- Node.js JavaScript 语法检查通过。
- Windows Server 2025 x64 上 PyInstaller 成功生成桌面程序。
- Inno Setup 成功生成 `PersonaWeave-0.1.0-Windows-x64-Setup.exe`。
- 打包后的 exe 成功启动本机 HTTP 服务；首页与 app.js 资源检查通过。
- 构建生成便携版 ZIP、安装包和 SHA256SUMS，已上传 Actions 构建产物。

构建记录：https://github.com/yoouke/1/actions/runs/41616053661

以上不覆盖真实 QQ 扫码、模型 API、桌面 GUI/托盘交互、安装器实际安装与卸载、DSH 工具执行和重启恢复。未将这些项目标为已验收。
