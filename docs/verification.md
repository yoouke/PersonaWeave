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

## 0.2.0 本地扩展验证

- 32 项 Python 测试全部通过（设置 PW_DSH_BIN 包含真实 DSH 测试）。
- 实际安装 npm `@deepseek-ai/dsh@0.2.1-rc.5`，SDK 初始化成功。
- 真实 DSH 通过宿主配置的兼容适配器调用本机 SSE 模拟模型，收到人格内容，完成任务并返回 100 输入 / 5 输出 Token。
- OneBot 实际 WebSocket 模拟端校验认证、投递重复事件，单次调用并返回经确认的私聊回复。
- Chromium 实际创建角色、记忆、知识文档、访问十个管理页面、刷新本机 Token；无 pageerror。
- 已检查中文界面截图；截图中的数据均为测试角色，无私人凭据。
- 新增 CI 持续执行以上集成与界面流程；Windows 新版构建结果须以对应 Actions 结果为准。

仍未登录真实 QQ / Telegram / Discord，未使用真实付费 API；未完成 Windows GUI 托盘、自启动、安装卸载、系统重启和休眠实测。
