# 贡献指南

感谢参与改进。提交前请确认：

## 环境

- Windows 10/11
- Python 3.10+
- 无运行时第三方依赖

## 开发流程

```powershell
git clone <repo>
cd 恐鬼症启动器
python -m unittest discover -s tests -t . -v
python main.py
```

## 代码约定

- 使用 4 空格缩进、UTF-8、LF。
- 类型标注使用 `from __future__ import annotations`。
- 不引入 `psutil`、`requests` 等运行时依赖；优先标准库。
- 新增外部副作用（启动进程、打开 URL、sleep）时，通过 `LauncherService` 的构造参数注入，
  保证可测试。
- 面向用户的错误信息使用中文，说明“发生了什么 + 下一步怎么做”。
- 不实现、不封装任何代理/VPN/加速线路；项目只做进程编排。

## 测试

- 新功能需补 `tests/` 下的单元测试。
- 测试不得启动真实 Steam、游戏或加速器，不得访问网络，不得依赖 Windows 注册表。
- 测试临时目录使用 `tempfile.TemporaryDirectory()`。
- 运行全部测试必须全绿。

## 提交信息

建议使用：

```text
feat: 增加 xxx
fix: 修复 xxx
docs: 更新 xxx
test: 增加 xxx
chore: 调整 xxx
```

## 安全

请勿在 issue、日志或测试数据中提交 Steam 账号密码、Steam Guard 令牌、加速器账号或
其他隐私信息。
