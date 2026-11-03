# 插件接入与扩展

优先复用 DSH 原生插件和 Skill。宿主只负责安装、配置、权限入口与按角色选择，不重复实现原生工具。

## 原生模块与 Bundle

在「插件与能力」登记 npm 包名（建议确切版本）、文档、使用说明与权限。安装后默认关闭。DSH CLI 自动启用 Bundle 的行为会被宿主重新分离为「安装」与「启用」。Bundle 通过原生 profile bundles 列表启用；单模块通过宿主 invocation overlay 的 insert 加载。一个角色的开关不会修改其他角色配置。

Bundle 的配置应填写它的原生条目 ID；宿主拒绝覆盖核心人格和凭据条目。复杂 Bundle 必须查阅原生文档；错误配置明确报错。插件版本依赖和许可遵循原包；不自动豁免 DSH 版本兼容检查，不默认批准依赖构建脚本。

文档仅用于查阅。专门填写的「Agent 使用说明」才加入人格上下文；已有原生 Skill 时不必重复填写。基础 JSON Schema 可生成字符串/数字/布尔/枚举表单，复杂字段在原生 JSON 编辑区配置。

## MCP

一个 MCP 服务对应一个定义，例如：

```json
{
  "serverName": "browser",
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "你审查过的MCP包@确切版本"],
  "env": {"SERVICE_KEY": "${credential:PW_BROWSER}"},
  "startupTimeoutMs": 30000
}
```

也可使用 `streamable-http` 和 `url`。宿主使用 DSH 的 `@deepseek-ai/dsh-mcp-client`，开启原生 credential template 解析。凭据区保存 `PW_BROWSER` 到 OS 凭据库，运行时注入，不写入角色 JSON 或补丁。服务文档和原生工具定义由 DSH 暴露给 Agent。

MCP 服务不是被宿主沙箱隔离的低权限代码。stdio 命令及原生插件以用户权限运行，必须审查来源。非主人对话不会运行 DSH 或这些插件，插件的权限描述仅是审查资料，不能冒充强制 OS 权限清单。

## 能力扩展

浏览器、视频、音乐、Bilibili、X、YouTube、截图、电脑操作等从各自原生插件接入。npm 搜索仅帮助寻找候选，不默认安装，不保证检索结果兼容或安全。需要账号的插件由用户按平台授权，宿主不附带第三方凭据。

## 引擎边界

`host.py` 保留身份判定、上下文检索、任务持久化与审批；`engine.py` 是 DSH 传输，`models.py` 是纯模型适配与创作/记忆调用。替换引擎应让宿主持有人格、身份与可导出记忆，不搬走这些数据。当前可选择两种内置引擎，尚未提供随意安装的第三方引擎包加载器。
