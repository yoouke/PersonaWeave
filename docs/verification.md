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

## 0.2.0 云端最终构建

- 软件源码提交：`760b915328216240c47145c6f1e51da230a06a41`。
- Windows 软件构建成功，冻结 exe 本机服务和打包资源检查成功：https://github.com/yoouke/1/actions/runs/41628600143
- Linux/Windows 回归、真实 DSH 本机模型集成与 Chromium 流程检查全部成功：https://github.com/yoouke/1/actions/runs/41628600091
- 构建产物包含 0.2.0 安装器、便携版和 SHA256SUMS；取回后已验证外层 ZIP 及两个内含文件校验值。
- Actions 下载：https://github.com/yoouke/1/actions/runs/41628600143/artifacts/13225999168
- 以上不新增真实 QQ/第三方账号或 Windows 桌面系统行为的验收结论。

## 0.2.1 视觉更新验证

- 原有 Python 回归测试通过；本次主要修改界面和品牌资源，未改变引擎协议。
- Chromium 检查创建/保存角色、记忆与知识、全部管理页面、刷新认证。
- 新增 900px / 390px 宽度检查，无文档横向溢出；检查了中文界面与 Logo 导出。
- 界面、托盘与 Windows 图标复用同一原创资源；SVG/PNG 由本机静态资源提供。
- Windows 打包与冻结资源检查结果以本版本对应 Actions 为准；不新增真实 QQ 账号或桌面系统行为的验收结论。

### 0.2.1 云端构建结果

- 软件源码：`89761ef4341fdd0ccb0febd3b5abdeeedab88085`。
- Windows 构建、冻结程序启动及打包页面资源检查成功：https://github.com/yoouke/1/actions/runs/41641387700
- Linux / Windows 回归、真实 DSH 本机模型及 Chromium 界面流程成功：https://github.com/yoouke/1/actions/runs/41641387728
- Artifact 提供 0.2.1 Setup.exe、Portable.zip 与 SHA256SUMS：https://github.com/yoouke/1/actions/runs/41641387700/artifacts/13231839614
- 本地 wheel 包含全部六项页面与品牌资源；ICO 包含 16–256px 共七个尺寸。

## 0.2.2 上游插件复用验证

- 使用 DSQQ 指定仓库的 GitHub 插件读取源码、配置包和许可；核对 AstrBot 4.29.3 原生 API，
  区分 AstrBot 插件与 DSH 插件，未继续将 DSQQ 描述为 DSH QQ 插件。
- 两个 npm 确切版本已经查询并实际通过 DSH 官方 CLI 安装：
  `dsh-astrbot-ingress@0.3.23`、`dsh-image-gen@0.10.2`。
- 在独立本机验证目录加载两个原生插件并启动真实 DSH web profile：认证网页可打开，
  ingress `/health` 返回 `ok: true`、`plugin: dsh-astrbot-ingress` 及能力列表。
  唯一 pending 条目为宿主停用登录账户后等待该服务的 account-controller。
- 原生网页认证 URL 从 DSH 输出取得，只存于进程内存；日志隐藏 token，原生控制台打开流程
  已用真实 DSH 和 CookieJar 验证。DSH→本机模拟模型的 SDK 回归仍通过。
- 新增本机 AstrBot HTTP 合约测试，覆盖真实列表委托、市场安装、重复安装跳过、按角色排他、
  私密凭据不进入设置、重定向拒绝、管理员/群聊白名单拒绝及不再启动自有 QQ 桥。
- 覆盖本角色进程信标匹配后自动配置原生桥、用户人格通过原生 API 同步且保留平台配置。
- 未登录真实 QQ，未完成真实 AstrBot 插件依赖加载、长期记忆检索、付费图像生成或 QQ 图片回传。
  不能将 HTTP 合约测试和 ingress 存活检查写成这些功能的端到端验收。
