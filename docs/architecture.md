# 架构说明

## 目标

用尽量少的依赖，把“检测环境 → 拉起加速器 → 启动 Steam → 启动游戏”做成可测试、
可解释、失败可定位的流程。GUI 与 CLI 共享同一套编排逻辑，避免两套行为不一致。

## 模块职责

| 模块 | 职责 |
| --- | --- |
| `constants.py` | AppID、默认等待时间、启动模式等常量 |
| `paths.py` | `%APPDATA%` 数据目录、日志目录、打包资源路径 |
| `config.py` | `AppConfig` 数据类、字段清洗、JSON 原子读写 |
| `windows.py` | `tasklist` 进程检测、独立进程启动、系统打开、轮询等待 |
| `steam.py` | Steam 注册表/默认路径检测、VDF 解析、多库游戏查找 |
| `accelerator.py` | 加速器路径校验、Windows 参数拆分、exe/lnk/协议启动 |
| `launcher.py` | 预检、启动顺序编排、超时与错误信息 |
| `app.py` | tkinter 界面、状态展示、线程与 UI 队列 |
| `cli.py` | `--check` / `--launch` / GUI 入口 |
| `ui/theme.py` | clam 主题、深色配色、字体选择 |
| `ui/widgets.py` | 状态卡片 |

## 数据流

```text
                ┌─────────────────────┐
                │     AppConfig       │
                │  (config.json)      │
                └──────────┬──────────┘
                           │
       ┌───────────────────┴───────────────────┐
       │                                       │
┌──────▼──────┐                        ┌───────▼───────┐
│  LauncherApp│                        │  CLI          │
│  (tkinter)  │                        │  --check      │
└──────┬──────┘                        │  --launch     │
       │                               └───────┬───────┘
       └───────────────┬───────────────────────┘
                       │
              ┌────────▼────────┐
              │ LauncherService │
              │  预检 + 编排     │
              └───┬────┬────┬───┘
                  │    │    │
      ┌───────────┘    │    └──────────────┐
      │                │                   │
┌─────▼─────┐   ┌──────▼──────┐   ┌────────▼────────┐
│accelerator│   │   steam.py  │   │ steam:// URI    │
│  launch   │   │ detect env  │   │ open_target     │
└───────────┘   └─────────────┘   └─────────────────┘
```

## 启动编排

`LauncherService.run(mode, config, environment=None, progress=None)`：

1. 解析模式：`all` / `game` / `steam` / `accelerator`
2. 预检：
   - `all`、`game`、`steam` 需要可用 Steam
   - `all`、`game` 需要已安装游戏
   - `all`、`accelerator` 需要有效加速器配置
3. 按顺序执行：
   - `all` + `accelerator_first`：加速器 → 等待 → Steam → 游戏
   - `all` + `steam_first`：Steam → 加速器 → 等待 → 游戏
   - `game`：Steam → 游戏
   - `steam`：Steam
   - `accelerator`：只启动加速器
4. 返回 `LaunchResult`，记录每一步是否发生

所有外部副作用都通过构造参数注入：

```python
LauncherService(
    environment_provider=detect_environment,
    process_checker=is_process_running,
    starter=start_detached,
    opener=open_target,
    clock=time.monotonic,
    sleeper=time.sleep,
    steam_start_timeout=60,
)
```

单元测试因此可以在不启动真实程序的情况下验证调用顺序、等待和错误路径。

## Steam 检测

```text
注册表 HKCU/HKLM
        ↓
常见安装目录
        ↓
steam_dir/steamapps/libraryfolders.vdf
        ↓
每个库的 appmanifest_739630.acf
        ↓
installdir → steamapps/common/<installdir>/Phasmophobia.exe
        ↓
找不到 manifest 时回退到 common/Phasmophobia
```

`libraryfolders.vdf` 是 Valve 的 KeyValues 文本格式。这里没有引入完整 VDF 解析器，而是
用正则提取 `"path" "..."`（新版）并兼容旧版 `"1" "D:\\..."`。对本项目而言，路径提取
足够且更不容易受格式版本影响。

## 进程与启动

- 进程检测：`tasklist /FO CSV /NH`，按第一列进程名匹配。故意不依赖 `psutil`。
- 子进程：`subprocess.Popen`，Windows 下使用
  `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`，启动器退出后子进程继续运行。
- 标准输入/输出/错误都接到 `DEVNULL`，避免 GUI 模式下出现控制台。
- 游戏启动使用 Steam 官方 URI，而不是直接执行游戏 exe；这样能正确走 Steam 的
  启动参数、DRM 和更新检查。

## 线程模型

tkinter 不是线程安全的，因此：

- 检测、启动流程都在 `launcher-worker` 后台线程执行；
- 后台线程只把 `(callback, args)` 放进 `queue.Queue`；
- 主线程每 100 ms 调用 `_drain_queue()` 执行回调；
- 忙碌时禁用操作按钮，避免并发启动；
- 关闭窗口时，如果仍在执行，先询问用户。

## 配置写入

`ConfigStore.save()`：

1. 创建同目录临时文件
2. 写入 UTF-8 JSON
3. `flush` + `os.fsync`
4. `os.replace` 原子替换

读取时对损坏 JSON、未知字段、越界等待时间做容错；未知字段被忽略，等待时间被夹到
0–300。

## 安全边界

- 不读取 Steam 凭据，不注入进程，不修改游戏文件。
- 不实现代理/VPN/加速节点；不修改 hosts、系统代理或路由。
- 加速器必须由用户在界面上显式选择；只允许 `.exe` / `.com` / `.lnk` / 协议 URL。
- 拒绝 `.bat` / `.cmd` / `.ps1` 作为加速器入口，减少误执行脚本的风险。
- 日志不记录账号密码；仅记录路径、命令和错误。

## 扩展点

- 新增启动模式：在 `constants.py` 增加常量，在 `LaunchMode` 和 `LauncherService.run`
  增加分支。
- 新增加速器协议：无需改代码，直接填 URL；系统需注册协议。
- 新增平台：`windows.py` 已做非 Windows 降级；Steam 检测目前以 Windows 路径为主。
- 新增主题：修改 `ui/theme.py` 的配色和 ttk style 即可。
