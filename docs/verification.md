# 验证记录

2026-11-03（Asia/Shanghai 执行期间）/ 开发预览

实际运行：13 项 Python unittest 通过；JavaScript 语法检查通过。JSON-RPC 测试使用本地模拟进程，验证审批请求与 RPC 响应交错处理；没有调用付费模型，没有登录真实 QQ。

来源核验：DSH 官方 SDK protocol types、SDK/headless README、CLI 帮助、headless JSON stream 实现。协议采用 newline-delimited JSON-RPC 2.0；assistant/message 数据位于 data.message.content；turn/end 检查 data.reason.kind。

待外部环境：Windows WebView2/托盘/开机自启、凭据库、Node 下载与校验、npm DSH 安装兼容性、NapCat release 结构与扫码、真实 OneBot 往返、真实模型任务、审批取消、重启恢复。

当前测试不证明端到端验收完成。所有未实现功能见 README。

补充打包配置：PyInstaller spec 显式包含页面资源、WebView2 与凭据库后端；Inno Setup 用户级安装脚本；main 推送触发 Windows 构建及冻结程序 HTTP 冒烟检查。新增同数据目录单实例 OS 文件锁及测试。上述 Windows 构建配置未在 Windows 或 GitHub Actions 实际执行。
