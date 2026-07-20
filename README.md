# Dr.Claw

Private medical deployment of a personal AI assistant (customized from QwenPaw 2.0).

The Python package name remains `qwenpaw`; the CLI entrypoint is **`drclaw`**.

**中文文档请看 [README_zh.md](README_zh.md)。**

## Docs

| Doc | Description |
|-----|-------------|
| [Environment variables](docs/DRCLAW_ENV_zh.md) | `DRCLAW_*` runtime config (Chinese) |
| [OpenIM channel](docs/DRCLAW_OPENIM_CHANNEL_zh.md) | IM bot integration (Chinese) |
| [Customization plan](docs/DRCLAW_CUSTOMIZATION_PLAN_zh.md) | Migration notes (Chinese) |

## Quick start

```bash
cd console && npm ci && npm run build && cd ..
pip install -e .

drclaw init --defaults
drclaw app
```

Open <http://127.0.0.1:8088/>

Default working directory: `~/.drclaw`. Prefer `DRCLAW_*` environment variables.

## License

See [LICENSE](LICENSE). Upstream base is Apache-2.0.
