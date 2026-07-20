# Dr.Claw Desktop 打包脚本（conda-pack 回滚路径）

> ⚠️ **旧版（仅用于回滚）。** 这套基于 conda-pack 的打包脚本已被 **Tauri**
> 桌面版构建取代（详见 `console/src-tauri/` 与 `scripts/pack-tauri/`），仅作
> 短期回滚保留。

一键打包：脚本会先运行 `scripts/wheel_build.sh` 构建 **wheel**
（包含 console 前端产物），再用 **临时 conda 环境** + **conda-pack**
（不依赖当前开发环境）。依赖以 `pyproject.toml` 为准；Python 包名仍为 `qwenpaw`。

- **Windows**: wheel → conda-pack → 解压 → NSIS 安装包 (`DrClaw-Setup-*.exe`)
- **macOS**: wheel → conda-pack → 解压到 `DrClaw.app` → 可选打 zip

## 系统要求

- **Windows**: Windows 10 或更高版本
- **macOS**: macOS 14 (Sonoma) 或更高版本，推荐 Apple Silicon (M1/M2/M3/M4)

## 前置

- **conda**（Miniconda/Anaconda）在 PATH
- **Node.js / npm**（用于构建 console 前端）
- （仅 Windows）**NSIS**：`makensis` 在 PATH
- **图标**：预生成的 `icon.ico` (Windows) 和 `icon.icns` (macOS) 已包含在 `scripts/pack/assets/` 中

## 一键打包

在**仓库根目录**执行：

```bash
# macOS
bash scripts/pack/build_macos.sh
# 产出: dist/DrClaw.app
# 可选: CREATE_ZIP=1 bash scripts/pack/build_macos.sh  → dist/DrClaw-<version>-macOS.zip
```

```powershell
# Windows
pwsh -File scripts/pack/build_win.ps1
# 产出: dist/DrClaw-Setup-<version>.exe
# 安装目录内启动器:
#   - DrClaw Desktop.vbs (静默启动，无终端窗口)
#   - DrClaw Desktop (Debug).bat (显示终端，便于调试)
```

## 手动调试（跳过安装器）

```bash
APP_ENV="$(pwd)/dist/DrClaw.app/Contents/Resources/env"
PYTHONNOUSERSITE=1 PYTHONPATH= PYTHONHOME="$APP_ENV" "$APP_ENV/bin/python" -m qwenpaw desktop
```

若**双击** .app 没有任何窗口出现，启动器会把 stderr/stdout 写入 `~/.drclaw/desktop.log`，可打开该文件查看报错。

## 环境变量

启动器优先使用 `DRCLAW_*`，并兼容 `QWENPAW_*` / `COPAW_*`（如 `DRCLAW_LOG_LEVEL`、`DRCLAW_DESKTOP_APP`）。

## 脚本说明

| 脚本 | 作用 |
|------|------|
| `build_common.py` | 创建临时 conda 环境，从 wheel 安装 `qwenpaw[full]`，conda-pack 产出归档 |
| `build_macos.sh` | 一键：构建 wheel → build_common → 解压到 DrClaw.app；可选打 zip |
| `build_win.ps1` | 一键：构建 wheel → build_common → NSIS `DrClaw-Setup-*.exe` |
| `desktop.nsi` | NSIS 安装脚本（品牌名 DrClaw；编译期仍用 `QWENPAW_VERSION`） |
