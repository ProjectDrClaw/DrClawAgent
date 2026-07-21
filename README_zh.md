# Dr.Claw

医疗私有化部署的个人 AI 助手（基于 QwenPaw 2.0 定制）。

配套：`DrClawApp`（Flutter + OpenIM）、`DrClawBusiness`（业务中心）。Python 包名仍为 `qwenpaw`，命令行入口为 **`drclaw`**。

## 文档

| 文档 | 说明 |
|------|------|
| [环境变量](docs/DRCLAW_ENV_zh.md) | `DRCLAW_*` 运行时配置 |
| [OpenIM 频道](docs/DRCLAW_OPENIM_CHANNEL_zh.md) | IM 机器人联调 |
| [定制说明](docs/DRCLAW_CUSTOMIZATION_zh.md) | 品牌与私有化能力总览 |

## 快速开始

**要求**：Python `>=3.11,<3.14`，建议使用 [uv](https://docs.astral.sh/uv/)。

```bash
# 源码安装（开发）
cd console && npm ci && npm run build && cd ..
pip install -e .

drclaw init --defaults
drclaw app
```

浏览器打开控制台：<http://127.0.0.1:8088/>

脚本安装（默认目录 `~/.drclaw`）：

```bash
# macOS / Linux
bash scripts/install.sh --from-source .

# Windows PowerShell
.\scripts\install.ps1 -FromSource -SourceDir .
```

Docker：

```bash
docker compose up -d
```

## 常用命令

```bash
drclaw --version
drclaw init          # 首次初始化
drclaw app           # 启动服务
drclaw doctor        # 环境自检
drclaw uninstall     # 卸载（保留数据；加 --purge 清空）
```

## 目录说明

```
DrClawAgent/
├── src/qwenpaw/          # 后端（包名 qwenpaw）
├── console/              # 控制台前端 + Tauri 桌面壳
├── deploy/               # Docker / 入口脚本
├── docs/                 # Dr.Claw 运维文档
├── scripts/              # 安装与打包脚本
├── plugins/              # 可选插件
└── tests/ · e2e/         # 测试
```

默认工作目录：`~/.drclaw`（兼容已有 `~/.qwenpaw` / `~/.copaw`）。环境变量优先使用 `DRCLAW_*`。

## 许可证

见 [LICENSE](LICENSE)。上游基础为 Apache-2.0。
