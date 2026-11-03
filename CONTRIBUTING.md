# 参与开发

当前为开发预览，欢迎可复现的错误报告与小范围修复。

## 本地检查

```shell
python -m pip install -e .
python -m unittest discover -s tests -v
node --check personaweave/web/app.js
```

Windows 打包请运行 `packaging/build-windows.ps1`。源代码更改须保持前端与后端接口一致，不把模拟测试描述为真实 QQ/DSH 测试。提交 PR 时写清问题、修改行为、实际验证和未验证条件。

## 数据与权限

不要提交 API Key、账号登录缓存、角色私人记忆、数据库或包含敏感信息的日志。不同角色、不同用户的权限隔离应由程序执行，不依赖人格提示词。增加插件之前检查上游许可与 DSH 兼容性。
