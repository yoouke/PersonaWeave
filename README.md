# 织灵 · PersonaWeave

[![Checks](https://github.com/yoouke/1/actions/workflows/check.yml/badge.svg)](https://github.com/yoouke/1/actions/workflows/check.yml) [![Windows](https://github.com/yoouke/1/actions/workflows/windows.yml/badge.svg)](https://github.com/yoouke/1/actions/workflows/windows.yml)

[Windows 构建与下载](https://github.com/yoouke/1/actions/workflows/windows.yml) · [问题反馈](https://github.com/yoouke/1/issues) · [贡献指南](CONTRIBUTING.md)

**你的世界，她们的故事。** 一个本地优先、人格独立、引擎可替换的 AI 虚拟人格宿主。

Windows 桌面应用，Python + WebView2 + DSH SDK + OneBot v11。MIT 开源。

> 开发预览 v0.1.0。已实现跨模块的可运行宿主，尚未完成 PRD V0.2 全部功能，尚未通过真实 QQ / DSH / Windows 全链路验收。不要将此版本当作成熟的一键安装成品。

## 启动

安装 Python 3.11+，在项目目录执行：

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[desktop]"
.venv\Scripts\python -m personaweave
```

纯浏览器管理模式：`python -m personaweave --browser`。不装桌面依赖时自动采用此模式。

本地数据默认存于 `%LOCALAPPDATA%\PersonaWeave`。可用 `--data D:\PersonaWeaveData` 指定。不得把运行数据上传到公开仓库。

## 使用流程

1. 在人格工坊创建角色，粘贴设定或导入 Markdown / TXT。不会附赠固定人格。
2. 连接与设置中填写主人 QQ、默认角色、运行模型和 Key。凭据使用系统凭据库保存，保存失败会报错，不回退明文。
3. 安装独立 Node.js 24 LTS，再安装 DSH。安装器从官方分发源下载；Node 和 NapCat 必须通过 SHA256 校验。
4. 选择 NapCat 或外部 SnowLuma。选择 SnowLuma 时不会安装 NapCat。
5. NapCat 安装、启动后，先在它的官方控制台扫码并配置本机 OneBot v11 正向 WebSocket 与 Token。QQ 普通账号接入可能受平台风控，使用小号。
6. 将相同 WebSocket 地址和 Token 填入宿主，保存，点击重新联动。
7. 用主人 QQ 私聊机器人账号发送任务。每个角色同一时间运行一个任务。
8. `/status` 查看状态，`/cancel` 停止角色任务，`/new` 开新会话。审批用 `/approve 编号` 或 `/reject 编号`。

角色 API 创作使用独立的 OpenAI 兼容 HTTPS API 配置。联网创作入口会明确提示尚未接通搜索插件。

## 已实现

- 多角色资料、人格文案及独立目录；SQLite WAL 宿主元数据和记忆记录。
- 人工维护的持久记忆与按角色/访问对象检索，不声称已实现自动长期记忆提炼。
- DSH SDK JSON-RPC stdio：初始化、会话持久化/恢复、发送任务、事件与完成结果。
- 角色人格通过 `system-prompt.personaPrefix` 注入；每角色独立 DSH_HOME 和工作目录。
- OneBot v11 正向 WebSocket 连接、私聊主人验证、消息去重、文本分段返回、自动重连。
- 宿主与 QQ 审批入口、五分钟过期拒绝、取消关闭角色进程。
- DSH 插件按角色安装、更新和卸载；启用挂载配置仍遵循插件原生文档。
- 系统凭据库、本机接口 Token、Host/Origin 校验、前端 textContent 防止角色内容执行 HTML。
- Windows 桌面托盘、关闭窗口隐藏、退出停止服务、开机自启开关（均待 Windows 实测）。
- 环境检测、Node 与 NapCat 官方下载校验、DSH npm 安装、NapCat 启停。
- 资源监控、任务状态、审批列表、事件记录、独立创作 API。
- Windows 构建工作流和跨平台单元测试工作流。

## 尚未完成，不能视为已验收

- 一键无人值守部署、内嵌扫码、协议端控制台自动登录、版本升级/回滚与异常恢复。
- 搜索驱动的第三种角色创作、资料来源管理、自动记忆/向量知识库。
- 插件发现市场、结构化配置 UI、自动按角色启用/禁用、MCP 图形配置。
- 各身份级别和群聊；当前只接受主人私聊。
- 完整 API/Token/预算/费用统计；当前不把事件计数伪装成模型消耗。
- QQ 图片/文件双向传输、语音、多账号路由、内容平台与远程电脑操作的产品化接入。
- DIY 主题/图标导入、角色包导入导出、WebView 控制台嵌入。
- Windows 安装器与完整端到端验收。

## 安全边界

人格提示词不是权限系统。QQ 入口只接受配置的主人 ID，其他人不进入引擎。OneBot 仅连接本机；宿主不对外监听。若要开放其他用户，必须先完成按用户会话、记忆和工具权限隔离。

DSH 原生权限与审批仍生效；人格工作目录不是操作系统沙箱的替代。安装的原生插件会执行第三方代码。DSH 插件管理器可能触发包安装脚本，安装前应审阅来源。

宿主数据库包含私人经历及工具执行事件；仅 API Key 等凭据进入系统凭据库，数据库和协议端缓存没有全部加密。日志不得公开。未实现完整日志脱敏。

使用 OS 文件锁阻止同一数据目录的重复启动。不要同时使用同一数据目录运行多个进程。切换模型、人格或插件请停止角色后操作。DSH 预览版协议可能变更，需做版本兼容验证。

## 验证与打包

```powershell
python -m unittest discover -s tests -v
node --check personaweave/web/app.js
```

GitHub Actions 的 **Windows executable** 可手动触发，产出未签名便携目录。以 Actions 的实际结果为准；绿色构建记录中的 Artifacts 提供 Windows 下载包。

新版 Windows software 工作流在 main 分支推送后自动执行，输出便携版 ZIP、Setup.exe（构建机有 Inno Setup 时）和 SHA256 校验文件。应用内含 Python 与桌面依赖，使用者无需安装 Python。DSH/Node/QQ 运行时仍在首次配置时下载，不内嵌第三方账号或 API Key。

本机 Windows 也可执行 `powershell -ExecutionPolicy Bypass -File packaging/build-windows.ps1` 构建。WebView2 运行时需由系统提供；若系统缺少，请安装微软官方 Edge WebView2 Evergreen Runtime。

## 参考上游

- [DSH](https://github.com/deepseek-ai/deepseek-harness)：使用 SDK 公开协议与插件 CLI；不依赖 DSH 网页界面。
- [NapCat](https://github.com/NapNeko/NapCatQQ)：OneBot 接入；遵循上游许可。
- [DSQQ](https://github.com/Jack-Cherish/DSQQ)：仅阅读作为流程参考，没有复制其启动器源码或资源。

宿主原创代码使用 MIT。上游运行时、第三方包和角色素材各自遵循其许可证，不因本仓库 MIT 许可而改变。

## 自动发布辅助脚本

源码包中双击 `Publish-to-GitHub.cmd`，脚本会验证 GitHub CLI 当前账号为 `yoouke`、使用公开仓库 `yoouke/1` 并推送允许列表内的代码，触发 Windows 构建。需要本机已安装官方 Git for Windows 和 GitHub CLI；未登录时会打开 GitHub 正常登录流程。不会要求粘贴 Token，不会强推覆盖远端历史，不会上传运行数据。此脚本尚未在 Windows 实测；它是受当前发布环境限制时的辅助路径，不表示仓库已发布或软件已构建。
