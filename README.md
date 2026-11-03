<p align="center">
  <img src="personaweave/web/icon.png" width="112" height="112" alt="织灵 Logo">
</p>

<h1 align="center">织灵 · PersonaWeave</h1>

<p align="center"><strong>将想象织成人格，让故事在日常中延续。</strong></p>
<p align="center">Windows 本地 AI 角色创作与运行框架</p>

<p align="center">
  <a href="https://github.com/yoouke/PersonaWeave/actions/workflows/check.yml"><img src="https://github.com/yoouke/PersonaWeave/actions/workflows/check.yml/badge.svg" alt="自动化检查"></a>
  <a href="https://github.com/yoouke/PersonaWeave/actions/workflows/windows.yml"><img src="https://github.com/yoouke/PersonaWeave/actions/workflows/windows.yml/badge.svg" alt="Windows 构建"></a>
</p>

<p align="center">
  <a href="https://github.com/yoouke/PersonaWeave/actions/workflows/windows.yml">下载 Windows 版</a> ·
  <a href="docs/getting-started.md">使用指南</a> ·
  <a href="docs/plugins.md">插件与扩展</a> ·
  <a href="docs/coverage.md">功能状态</a>
</p>

## 关于织灵

织灵让你在自己的电脑上创造、运行和管理 AI 角色。你可以决定角色的性格、表达方式、记忆与能力，为其连接聊天平台，也可以让它通过 Agent 引擎处理任务。

从一句描述开始创作，或者直接导入已有设定。每个角色都有独立的资料、工作目录和配置，你可以随时修改、备份和带走这些内容。

**角色由你定义。** 织灵提供创作和运行工具，不附带固定人格，也不要求使用预设性格模板。

## 你可以做什么

### 创造自己的角色

- **AI 辅助创作**：通过对话讨论、补充和修改角色设定。
- **直接导入**：粘贴提示词，或导入 Markdown、TXT 文件。
- **联网创作**：配置搜索服务后搜集资料，整理人物设定并保留来源，区分官方候选、二创和社区内容。

创作和日常运行可使用不同的模型与 API 配置。生成的设定始终允许手动编辑。

### 管理人格、记忆与知识

- 创建多个角色，分别保存人格文案、行为规则、头像、立绘和来源资料。
- 记录与检索经历、事件、事实和人物关系，查看、编辑或删除记忆。
- 导入文本知识资料，为对话提供可检索的背景信息。
- 导出角色资料包，或另行备份私密数据。

宿主记忆支持按角色与对话身份区分访问范围。插件中的记忆由对应插件管理，目前与宿主记忆分别存储。

### 把角色连接到日常交流

提供 QQ 接入与 Telegram、Discord 私聊适配器。在 QQ 通道中，可以配置日常角色聊天，并通过主人专用的 `/dsh` 命令提交 Agent 任务。

QQ 协议端可选择 NapCat，或连接自行安装的 SnowLuma 兼容端；同一通道二选一。通信服务、账号登录与插件需要按指南完成配置，实际平台收发仍待账号验收。

### 按需添加能力

在「插件与能力」管理角色使用的插件、MCP 服务和工具配置，查看安装状态、使用说明及权限描述。

可准备长期记忆、消息桥接等基础组件，选装画图插件，或继续扩展浏览器、媒体与内容平台能力。**插件需要安装和配置，能力入口不代表功能已经开通。** 图像生成还需要相应的图像服务。

当前任务引擎采用 DeepSeek Harness（DSH），同时提供兼容 API 的纯对话方式。

### 统一查看运行情况

- 查看模型请求、输入与输出 Token、按角色和周期统计的使用量。
- 配置模型单价、费用估算和预算预警。
- 查看 CPU、内存、磁盘、网络与服务进程状态。
- 管理维护任务、连接检查、运行日志和控制台入口。
- 配置后台运行、系统托盘、开机启动与主题图标。

费用统计会区分实际返回用量与估算数据；插件自行发起的请求可能不在宿主统计范围内。

## 下载与开始使用

当前版本：**0.2.5 · 开发预览**。

前往 [Windows 构建页面](https://github.com/yoouke/PersonaWeave/actions/workflows/windows.yml)，打开成功的构建记录，在 **Artifacts** 中下载 `PersonaWeave-Windows-x64`。下载构建产物通常需要登录 GitHub。

压缩包提供安装程序、便携版和校验文件。软件包含 Python 与桌面依赖；Windows 还需要 WebView2 运行时。Node.js、DSH 及通信服务按使用需要另外准备，安装包暂未签名。

首次使用的主要步骤：

1. 配置模型 API，测试连接。
2. 创建或导入角色，选择默认角色。
3. 在初始化向导准备 Agent 运行环境。
4. 根据需要连接通信服务、登录账号并绑定主人身份。
5. 准备插件、同步人格，完成连接检查。

详细操作见 [使用指南](docs/getting-started.md)。只体验本机纯对话时，可以先完成前两步。

## 本地数据与权限

角色资料和运行数据默认保存在：

```text
%LOCALAPPDATA%\PersonaWeave
```

支持通过 `--data` 指定其他目录。每个角色拥有独立目录及 DSH 运行配置；角色目录隔离不等于操作系统级沙箱。

宿主 API Key 和平台凭据使用系统凭据库保存。权限由程序判断，角色好感和提示词不会授予系统权限。宿主直连通道中的非主人与群聊使用受限对话；插件通信通道当前限定主人私聊。

公开角色资料包默认不包含私人聊天、私密记忆和凭据。通信服务登录缓存、插件配置、对话数据库与日志不保证全部加密，分享运行目录前应单独检查。

## 当前进展

已通过 Linux / Windows 回归、真实 DSH 本机集成、浏览器流程及 Windows 安装包构建检查。0.2.5 集成作业执行了 **50 项测试**。

真实 QQ 收发、真实第三方模型与记忆服务、画图回传，以及 Windows 托盘、安装卸载和休眠恢复仍需进一步验证。自动升级与回滚、统一插件记忆迁移、语音播放、完整媒体套件和插件市场仍在规划中。

详见 [功能状态](docs/coverage.md) 与 [验证记录](docs/verification.md)。

## 参与开发

欢迎提交问题、改进建议与代码贡献。开发环境、测试与打包命令见 [开发指南](docs/development.md)，贡献流程见 [CONTRIBUTING.md](CONTRIBUTING.md)，安全问题见 [SECURITY.md](SECURITY.md)。

织灵使用 [MIT 许可证](LICENSE)。依赖、插件及其他资源的许可信息见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
