# DSQQ 与现有插件复用

本版本改为优先复用用户指定的 [DSQQ](https://github.com/Jack-Cherish/DSQQ)
所采用的组件。DSQQ 的实际底层是 **AstrBot + NapCat**，不是 DSH 插件。
DSH 继续作为执行任务的 Agent，通过现成双端插件接入 AstrBot。

## 组件归属

| 能力 | 实际运行的上游组件 | 织灵负责 |
| --- | --- | --- |
| QQ / OneBot 消息 | DSQQ 中的 AstrBot + NapCat | 连接已有实例、打开控制台 |
| 长期记忆 | lxfight/astrbot_plugin_livingmemory | 原生安装与启停入口 |
| 群聊表达 | Him666233/astrbot_plugin_group_chat_plus | 同上 |
| 表情包 | anka/meme_manager | 同上 |
| QQ 空间 | Zhalslar/astrbot_plugin_qzone | 同上 |
| QQ 资料 | Zhalslar/astrbot_plugin_qqprofile | 同上 |
| 主动聊天 | DBJD-CR/astrbot_plugin_proactive_chat | 同上 |
| AstrBot→DSH | CCYellowStar2/astrbot_plugin_dsh + dsh-astrbot-ingress@0.3.23 | 安装与权限检查、原生控制台进程 |
| 画图 | shanliuling/dsh-image-gen@0.10.2 | 安装到 web profile、使用原生配置与 UI |

前六个插件标识来自 DSQQ 的 MIT `vendor/dafeiyu-config-pack/settings/pack.json`。
未将这些 AstrBot 插件冒充为 DSH 原生插件，也不把候选清单标记为已安装。
这是一组 DSQQ 实际采用的插件，不代表所有插件都是“主流”、经过安全审计或完全适配。

## 使用

1. 使用 DSQQ 上游安装包部署已有 AstrBot / NapCat；也可连接独立安装的 AstrBot。
   当前不把 DSQQ 安装器内嵌、改名再分发。扫码及协议端设置由其原生界面完成。
2. 在织灵「插件与能力 → 复用 DSQQ / AstrBot 插件」选择角色，填写本机后台地址、
   账号与密码并连接。后台密码保存到系统凭据库，JWT 只留在请求期间的内存。
3. 设置此实例的唯一主人管理员与私聊消息白名单，点击「同步当前角色设定到 AstrBot」，
   通过其原生人格 API 导入用户自己的设定，并选为此实例的日常聊天人格。
   读取原生安装状态，选择需要的插件。首次安装后停用，先在 AstrBot 原生控制台完成
   模型、Embedding、权限等插件配置，再启用。已经安装的插件不会重装或覆盖配置。
4. 每个角色使用独立 AstrBot 实例及数据目录；同一个地址不能绑定两个角色。
   当前复用分支只允许主人私聊：启用插件及 DSH 桥前，检查唯一管理员和消息白名单。
   上游多用户记忆权限尚未验证，不能宣称已支持此分支的普通用户私密记忆隔离。
5. 以该角色作为默认角色，在织灵安装现成 ingress 插件并启动原生 DSH 控制台。
   在控制台配置模型、工作区及权限。
6. 安装 AstrBot 侧「DSH 桥接」，token 留空，点击「配置主人专用 DSH 桥」，自动读取
   此角色进程写入的原生信标并连接。外部 DSH 实例可手动填写 ingress 地址和 token；
   token 位于其 `DSH_HOME/dsh-astrbot-ingress/config.json`。
   普通人格聊天留在 AstrBot，主人发送 `/dsh 任务` 才交给 DSH。
   配置成功仅表示 API 已接受设置，真实消息往返仍需账号联调。
7. 画图使用「安装现成画图插件」，在原生 DSH 控制台填写图像服务及凭据。
   尚未验收生成图片自动回传 QQ。接入聊天模型本身不代表拥有图像生成服务。

连接 DSQQ 后，织灵的「连接 QQ / 重新联动」检测 AstrBot 插件接口，**不会再创建自有
OneBot 消息接收器**；启动/覆盖配置的入口拒绝再管理同一角色的第二个 NapCat。
旧版自有 OneBot 路径保留供未连接 AstrBot 的既有配置使用。

## 数据和验证边界

不自动导入“大肥鱼”固定人格、声音或表情资料。织灵角色资料保留在自己的角色目录，
用户可按需将当前设定同步到所绑定 AstrBot；后续修改需再次同步，尚无双向实时同步。
AstrBot 插件数据使用原生控制台管理，此版本尚未实现插件记忆的统一导出及迁移，
不能把它当作织灵本地记忆页中的同一套记忆库。

API 管理适配以 AstrBot **4.29.3** 的 `/api/v1` 接口源码核对，安装默认遵循上游市场
的版本兼容检查。复用配置包的 API helper，修改为直连本机并拒绝重定向；署名与 MIT
许可见 `THIRD_PARTY_NOTICES.md` 和 `personaweave/vendor/LICENSE`。

DSH web profile 插件与旧版 SDK profile 分开管理，原生插件的 UI、工具、Skill 不重新实现。
上游插件自己保存的凭据受其原生存储规则约束；织灵不宣称能替外部 AstrBot / DSH
加密所有配置文件。原生服务日志和 ingress token 属于本机私密数据，不上传仓库。

测试覆盖本机 HTTP 接口委托、真实安装状态、重复安装跳过、凭据不进入设置、重定向拒绝、
角色实例排他、主人/群聊权限拒绝及原生 CLI profile 参数。真实 QQ、真实插件依赖加载、
Embedding、付费画图及图片回传尚未验收。
