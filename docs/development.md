# 开发指南

织灵是一个 Windows 本地优先的 AI 人格宿主。主程序负责角色数据、身份权限、任务生命周期、插件配置及桌面界面。

## 环境

- Python 3.11 或更新版本。
- Windows 桌面模式需要 WebView2。
- Agent 集成需要 Node.js 和 DSH。
- 浏览器自动化测试需要 Playwright Chromium。

## 从源码启动

在仓库根目录执行：

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[desktop]"
.venv\Scripts\python -m personaweave
```

浏览器管理模式：

```powershell
.venv\Scripts\python -m personaweave --browser
```

自定义数据目录：

```powershell
.venv\Scripts\python -m personaweave --data D:\PersonaWeaveData
```

## 代码结构

| 路径 | 职责 |
| --- | --- |
| `personaweave/host.py` | 身份、上下文、任务、审批与联动 |
| `personaweave/store.py` | 角色、记忆、知识、记录与备份 |
| `personaweave/models.py` | 模型请求、角色创作、记忆提取与用量 |
| `personaweave/engine.py` | Agent 传输接口 |
| `personaweave/runtime.py` | 引擎安装、进程与控制台 |
| `personaweave/astrbot.py` | 插件通信实例管理与人格同步 |
| `personaweave/extensions.py` | 插件登记、安装、配置与启停 |
| `personaweave/platforms.py` | 通信适配器 |
| `personaweave/server.py` | 本机管理 API 与静态资源 |
| `personaweave/web/` | 管理界面 |
| `packaging/` | Windows 安装与打包配置 |
| `tests/` | 回归、协议及浏览器流程测试 |

## 测试

```powershell
python -m unittest discover -s tests -v
node --check personaweave/web/app.js
node --check personaweave/web/upstream.js
```

普通测试会跳过两个需要真实 DSH CLI 的集成用例。安装锁定版本 `@deepseek-ai/dsh@0.2.1-rc.5` 后，将 `PW_DSH_BIN` 指向其 CLI JS 入口，再运行测试即可执行这些用例。模型服务在本机模拟，不需要付费 Key。

浏览器流程：

```powershell
python -m pip install playwright
python -m playwright install chromium
python tests/ui/smoke.py
```

CI 包含 Linux / Windows 回归、真实 DSH 本机集成、浏览器流程，以及 Windows 打包与冻结服务检查。真实平台登录、付费 API 和桌面系统行为的验证单独记录，见 [验证记录](verification.md)。

## Windows 打包

```powershell
powershell -ExecutionPolicy Bypass -File packaging/build-windows.ps1
```

输出包括便携版、Inno Setup 安装包。GitHub Actions 同时生成 SHA256SUMS，并上传构建产物。

## 扩展原则

人格、身份与可导出数据由宿主管理；新引擎和平台通过适配接口接入。插件配置应保留原生工具定义和文档，避免将能力描述误当成强制的系统权限。

新增功能需同步更新使用指南和 [功能状态](coverage.md)，并为重要的权限、数据隔离与故障恢复行为提供测试。

[返回首页](../README.md) · [贡献流程](../CONTRIBUTING.md)
