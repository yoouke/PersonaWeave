# 织灵 · PersonaWeave

[![Checks](https://github.com/yoouke/1/actions/workflows/check.yml/badge.svg)](https://github.com/yoouke/1/actions/workflows/check.yml) [![Windows](https://github.com/yoouke/1/actions/workflows/windows.yml/badge.svg)](https://github.com/yoouke/1/actions/workflows/windows.yml)

**你的世界，她们的故事。** Windows 本地优先的 AI 人格宿主，MIT 开源。

[Windows 软件构建与下载](https://github.com/yoouke/1/actions/workflows/windows.yml) · [功能与验证范围](docs/coverage.md) · [插件接入规范](docs/plugins.md) · [验证记录](docs/verification.md)

当前软件版本 **0.2.2 开发预览**。已有实际功能和跨模块测试，不等于 PRD 全部验收完成。没有通过真实 QQ 账号、第三方模型服务、Windows 安装卸载/休眠恢复的端到端验收。未来能力与未验证项不伪装为已完成。

**0.2.2 优先复用 [DSQQ](https://github.com/Jack-Cherish/DSQQ) 的 AstrBot / NapCat 及同款插件生态。**
新增已有实例连接、原生插件管理、现成 AstrBot→DSH 桥和 `dsh-image-gen` 安装入口。
实际组件、操作流程及隔离/迁移边界见 [DSQQ 复用说明](docs/dsqq-reuse.md)。
不自动套用“大肥鱼”固定人格，不声称插件清单已在用户电脑全部安装或验收。

## 视觉设计

原创交织线环 Logo，月光紫 / 杏桃 / 雾白界面。统一工作空间、人格工坊、配置页面、空状态、图标与托盘视觉；保留自定义主题。见 [视觉规范与源文件](design/README.md)。

## 功能

- 多角色独立目录、原始人格文案、行为补充、头像、立绘与来源资料；不附赠预设人格。
- 三种创建通道：AI 辅助讨论、MD/TXT/System Prompt 导入、搜索驱动创作。联网通过用户配置的 SearXNG 或 Tavily 搜集资料，区分官方候选、二创与社区梗；官方候选需要用户核验。
- DSH Agent / 兼容 API 纯对话两种运行方式；运行和创作使用独立 API 配置。
- 自动提取长期记忆（额外模型调用）、事件/关系/事实/经历分类、查看编辑删除；中文词组检索；知识文档导入、按范围检索与上下文注入。
- QQ OneBot v11 正向 WebSocket，私聊与群内 @ 消息、重复消息去重、重连、发送结果确认、登录状态与连接状态区分。
- NapCat 官方下载校验、进程管理、OneBot 配置生成；SnowLuma 只连接用户自行安装的兼容端，二选一。
- Telegram Bot 私聊适配器与 Discord Bot 私聊适配器；Discord 使用 discord.py 管理 Gateway、心跳与限流。
- 主人/熟人/普通用户/未知用户/屏蔽规则。主人私聊可用 DSH；其他用户和群聊使用无电脑工具的隔离对话。群聊不能继承主人的私密记忆。
- DSH 原生插件、Bundle、MCP 和自定义 DSH 模块登记；按角色安装、更新、卸载、启用、禁用。MCP 使用 DSH 原生客户端。插件文档、权限描述、Schema 基础表单和凭据引用。
- npm 插件搜索与资料查看；搜索结果不代表安全或兼容性背书。
- 模型请求/Token/人格/用途/周期统计，真实返回值与估算区分，用户单价费用估算与预算预警；DSH 仅记录可确认的 canonical usage。
- CPU/内存/磁盘/网络及服务进程资源；任务和会话持久化；审批五分钟超时拒绝。
- 后台安装任务、初始化向导、重新联动、可选自动连接、NapCat 崩溃有限重启；重启后中断任务不自动重放副作用。
- Windows 桌面/托盘/开机启动配置；可关闭窗口保持运行。
- 颜色主题导入导出、界面图标与托盘图标自定义；角色资料包导入导出、可选私密备份、SQLite 数据库备份。

## 安装与使用

普通用户从绿色 **Windows software** 构建的 Artifacts 下载 ZIP，解压后运行 `PersonaWeave-0.2.2-Windows-x64-Setup.exe`，或使用 Portable ZIP。软件包包含 Python 与桌面依赖，无需自行安装 Python。安装包未签名。Windows 需要微软 WebView2 运行时。

1. 打开「偏好与安全」，填写运行 API 地址、模型、Key；创作 API 单独填写，并测试连接。
2. DSH 路由默认 `personaweave`，由宿主配置为下方兼容 API；使用官方原生 Messages 路由时可选择 `deepseek-official`，其认证与接口由 DSH 管理。上下文大小需按模型实际能力设置。
3. 在「人格工坊」创造或导入角色；选择默认角色。
4. 在「初始化向导」安装独立 Node.js 和 DSH。当前锁定已验证的 DSH `0.2.1-rc.5`，同时安装 pnpm；运行时不内嵌在软件包中。
5. 优先使用 DSQQ 上游安装器部署 AstrBot / NapCat 并扫码；在织灵「插件与能力」连接该角色的独立 AstrBot 实例，绑定主人并设置仅主人私聊白名单。该分支不再重复安装或启动 NapCat。
6. 点击「同步当前角色设定到 AstrBot」，选择需要的 DSQQ 同款插件，在原生控制台完成配置后启用。日常聊天、表情与记忆由 AstrBot 插件运行。
7. 安装现成 DSH 双端桥接插件、启动原生 DSH 控制台并配置模型与工作区，点击「配置主人专用 DSH 桥」；主人发送 `/dsh 任务`。画图选装现成 `dsh-image-gen`。详细流程及待验收项见 [复用说明](docs/dsqq-reuse.md)。

未连接 AstrBot 的既有配置仍可使用旧版「通信平台」OneBot 直连路径，其 `/status`、`/cancel`、`/new`、`/approve`、`/reject` 命令与原生 DSH 桥的 `/dsh` 命令分别管理。

搜索驱动创作需配置搜索服务。自动记忆需要兼容 API；DSH 原生引擎也可搭配宿主记忆。未设置单价时，费用栏中的 0 不能当作免费账单。第三方插件可能产生未进入宿主调用层的请求，不作虚假归因。

## 数据和权限

数据默认位于 `%LOCALAPPDATA%\PersonaWeave`，可通过 `--data D:\PersonaWeaveData` 更改。角色数据在 `Characters/<UUID>/` 中，宿主 SQLite 元数据包含记忆、知识、对话、用量与任务。每个角色拥有独立 DSH_HOME 和工作目录。

API Key 与宿主平台 Token 使用系统凭据库；保存失败会报错，不回退明文。DSH/MCP 凭据通过运行环境与引用提供，不写入人格补丁。原生插件是受信代码，不能把角色工作目录当作操作系统沙箱。主人仍受 DSH 原生审批规则约束；非主人根本不会进入 DSH 工具进程。

同一角色的主人私聊跨已授权平台使用 `owner` 记忆；其他用户为 `平台:用户ID`；群聊为单独的群/发送者范围。`public` 是明确公开给该角色所有对话的资料。权限判断不依赖提示词或角色好感。

默认角色分享包不包含私人记忆、聊天记录、宿主配置、插件配置和凭据。用户可单独导出包含私密记忆/知识的备份；导入后这些数据置于 `imported-private`，须人工检查再改范围。导入包不会自动启用插件或代码。

协议端的登录缓存及 OneBot 配置由上游读取；自动生成的 NapCat 配置需要包含连接 Token。**不声称上游 QQ 缓存、宿主对话数据库或所有日志已加密。** 不要分享运行数据和私密备份。运行时审计日志会脱敏已知宿主凭据，但不能保证移除用户主动写入对话的所有私人信息。

## 开发与验证

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[desktop]"
.venv\Scripts\python -m personaweave
```

浏览器模式：`python -m personaweave --browser`。GUI 依赖缺失时使用此模式。

```powershell
python -m unittest discover -s tests -v
node --check personaweave/web/app.js
```

可选真实 DSH 集成测试：安装锁定的 npm 包后，将 `PW_DSH_BIN` 指向它的 CLI JS 入口，再运行测试。模型服务由测试在本机模拟，不使用付费 Key。浏览器验证：安装 Playwright Chromium 后运行 `python tests/ui/smoke.py`。CI 同时执行 Linux/Windows 回归、真实 DSH 本地模型集成、Chromium 流程检查及 Windows 软件打包。

Windows 本机构建：`powershell -ExecutionPolicy Bypass -File packaging/build-windows.ps1`。GitHub Actions 生成便携版、Inno Setup 安装包及 SHA256SUMS。程序更新不会默认清理用户数据。

## 边界与后续工作

完整清单见 [功能覆盖](docs/coverage.md)。尚未完整产品化的内容包括：自动版本升级/回滚、凭据迁移、操作系统级跨角色文件沙箱、真实 QQ 图片/文件接收链路、语音播放、完整媒体/社交插件套件、专门运营的插件市场及任意 UI 插件加载。浏览器/视频/音乐/内容平台通过用户安装的现有插件提供，不能将适配接口等同于这些插件已安装或实测。

当前内置两种引擎方式，第三方引擎适配器仍需开发接入；JSON Schema 表单覆盖基础字段，复杂插件配置保留原生 JSON。SnowLuma 不自动分发。QQ 登录、手机授权及第三方 API 授权无法由测试虚构，待用户有设备和账号时实际验证；本项目不以这些外部条件作为停止功能开发的理由。

## 上游与许可

- [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)：SDK、CLI、原生插件与 MCP。
- [NapCat](https://github.com/NapNeko/NapCatQQ)：QQ 协议及 OneBot。
- [DSQQ](https://github.com/Jack-Cherish/DSQQ)：流程参考，没有复制其源码或资源。

宿主原创代码使用 MIT；上游运行时、第三方插件和角色素材遵循各自许可。
