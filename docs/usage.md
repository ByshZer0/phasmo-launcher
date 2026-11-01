# 使用说明

## 1. 准备环境

1. 安装 **Python 3.10+**（官方安装包自带 tkinter）。
2. 安装并登录 **Steam**。
3. 在 Steam 中安装 **Phasmophobia（恐鬼症）**，AppID 为 `739630`。
4. 安装你常用的第三方加速器，并在客户端中为 **Steam / 恐鬼症** 配置好线路。

> 本启动器不提供加速节点。它只负责用你本机已安装的加速器，按顺序完成
> “启动加速器 → 启动 Steam → 启动游戏”。

## 2. 启动程序

双击 `run.bat`，或执行：

```powershell
python main.py
```

`run.bat` 使用 `pythonw.exe`，不会留下控制台窗口。

## 3. 首次设置

### 3.1 Steam 目录

程序会先尝试自动检测：

- 注册表 `HKCU\Software\Valve\Steam\SteamPath`
- 注册表 `HKLM\SOFTWARE\WOW6432Node\Valve\Steam\InstallPath`
- `%ProgramFiles(x86)%\Steam`
- `%ProgramFiles%\Steam`
- `C:\Steam`

如果状态卡显示「未找到」，点「浏览」，选择包含 `steam.exe` 的目录。选择错误目录时
程序会拒绝保存并提示。

点击「自动检测」会清空手动路径，重新使用自动检测。

### 3.2 加速器程序

点「浏览」，选择以下之一：

- 加速器主程序 `.exe`
- `.com` 可执行文件
- 桌面快捷方式 `.lnk`（此时不能附加参数）
- 也可以直接在输入框填入协议 URL，例如 `uu://` 开头的地址（需系统已注册该协议）

如果加速器需要命令行参数，在「启动参数」中填写。参数按 Windows 习惯解析，支持双引号：

```text
--profile "Phasmophobia" --mode fast
```

会解析为三个参数：

```text
--profile
Phasmophobia
--mode
fast
```

### 3.3 等待时间

拉起加速器后，程序会等待指定秒数再启动 Steam，给加速器留出登录、连接节点和注入
Steam 的时间。

- 默认：10 秒
- 范围：0–300 秒
- 机器较慢或加速器启动慢：建议 15–30 秒

### 3.4 启动顺序

| 选项 | 实际流程 |
| --- | --- |
| 先加速器，后 Steam | 加速器 → 等待 → Steam → 游戏 |
| 先 Steam，后加速器 | Steam → 加速器 → 等待 → 游戏 |

如果加速器必须在 Steam 运行时才能识别游戏，选「先 Steam，后加速器」。

## 4. 一键启动

点击绿色按钮「一键启动」。

程序按以下顺序执行：

1. 预检 Steam 是否安装
2. 预检游戏是否安装
3. 预检加速器配置是否有效
4. 启动加速器
5. 等待配置的秒数
6. 若 Steam 未运行则启动 Steam，并等待 `steam.exe` 出现（最长 60 秒）
7. 通过 `steam://rungameid/739630` 请求 Steam 启动游戏

任意一步失败都会在弹窗和日志中说明，不会继续执行后续步骤。

> 预检是“全有或全无”的：例如没有配置加速器时，「一键启动」不会先启动 Steam 再报错。

## 5. 其他按钮

| 按钮 | 作用 |
| --- | --- |
| 仅启动恐鬼症 | 确保 Steam 运行，然后请求启动游戏；不拉起加速器 |
| 仅启动 Steam | 只启动 Steam |
| 测试加速器 | 仅执行加速器启动命令，用于验证路径和参数 |
| 重新检测 | 重新扫描 Steam 与游戏库 |
| 打开配置目录 | 打开 `%APPDATA%\PhasmoLauncher` |
| 打开日志目录 | 打开日志文件夹 |
| 保存设置 | 立即保存当前配置 |

## 6. 配置文件

默认路径：

```text
%APPDATA%\PhasmoLauncher\config.json
```

示例见项目根目录的 `config.example.json`。

所有界面修改会在 0.6 秒防抖后自动保存；退出时也会再保存一次。写入采用临时文件 +
`os.replace` 原子替换，异常退出不会留下半个 JSON。

### 自定义数据目录

设置环境变量 `PHASMO_LAUNCHER_HOME`，配置和日志都会放到该目录：

```powershell
$env:PHASMO_LAUNCHER_HOME = "D:\PhasmoLauncherData"
python main.py
```

## 7. 命令行模式

```powershell
python main.py --check
python main.py --launch all
python main.py --launch game
python main.py --launch steam
python main.py --launch accelerator
python main.py --debug
```

`--launch` 使用与 GUI 完全相同的预检和编排逻辑，适合做快捷方式或计划任务。

`--check` 输出示例：

```text
恐鬼症启动器 v1.0.0
配置文件 : C:\Users\you\AppData\Roaming\PhasmoLauncher\config.json
Steam    : OK  D:\Steam
游戏库   : D:\Steam, E:\SteamLibrary
恐鬼症   : OK  E:\SteamLibrary\steamapps\common\Phasmophobia\Phasmophobia.exe
加速器   : OK  UU.exe
```

## 8. 日志

日志按 1.5 MB 滚动，保留 3 个备份：

```text
%APPDATA%\PhasmoLauncher\logs\launcher.log
```

界面只保留最近 600 行，完整记录以文件为准。

## 9. 卸载

本程序不写注册表、不安装服务。删除项目文件夹或 exe 即可；如需清理配置与日志，删除：

```text
%APPDATA%\PhasmoLauncher
```
