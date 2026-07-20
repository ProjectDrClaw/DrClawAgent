# Dr.Claw Desktop packaging scripts (conda-pack rollback path)

> ⚠️ **Legacy (rollback only).** These conda-pack scripts have been superseded by
> the **Tauri** desktop build (`console/src-tauri/`, `scripts/pack-tauri/`).

One-click packaging builds a wheel (with console assets), then packs a temporary
conda env. The Python package name remains `qwenpaw`.

- **Windows**: `dist/DrClaw-Setup-<version>.exe`
- **macOS**: `dist/DrClaw.app` (optional `CREATE_ZIP=1` → `dist/DrClaw-<version>-macOS.zip`)

Launchers prefer `DRCLAW_*` and accept `QWENPAW_*` / `COPAW_*` fallbacks.
NSIS still uses compile-time `QWENPAW_VERSION`.

See `README_zh.md` for full usage.
