# Changelog

本项目的版本变更记录，格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [1.0.0] - 2026-11-02

### Added

- 一键启动流程：第三方加速器 → Steam →《恐鬼症》
- 可切换启动顺序：加速器优先 / Steam 优先
- Steam 自动检测：注册表、常见目录、`steam.exe` 校验
- Steam 多库支持：解析 `libraryfolders.vdf` 与 `appmanifest_739630.acf`
- 游戏安装预检，避免对损坏或不存在的安装发起启动
- 加速器配置：exe / com / lnk / URL 协议、命令行参数、等待时间
- 深色 tkinter 界面：状态卡片、运行日志、自动保存
- 无界面 CLI：`--check`、`--launch all|game|steam|accelerator`
- 原子配置写入与损坏配置回退
- 滚动日志（1.5 MB × 3）
- 单元测试：配置、Steam VDF/ACF、加速器参数、启动编排
- Windows 文件夹版打包脚本（可选单文件）与 GitHub Actions CI

### Notes

- 不内置任何加速线路；加速能力来自用户已安装的第三方加速器。
- 仅支持 Windows 10/11。
