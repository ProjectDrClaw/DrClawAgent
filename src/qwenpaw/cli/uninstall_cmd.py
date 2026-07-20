# -*- coding: utf-8 -*-
"""drclaw uninstall — 移除 Dr.Claw 环境与 CLI 包装脚本。"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import click

from ..constant import WORKING_DIR


# 安装脚本创建的目录（相对于 WORKING_DIR）。
_INSTALLER_DIRS = ("venv", "bin")

# 需要清理 PATH 的 shell 配置文件。
_SHELL_PROFILES = (
    Path.home() / ".zshrc",
    Path.home() / ".bashrc",
    Path.home() / ".bash_profile",
)


def _remove_path_entry(profile: Path) -> bool:
    """移除 Dr.Claw / 旧品牌 PATH 行。有改动则返回 True。"""
    if not profile.is_file():
        return False

    text = profile.read_text(encoding="utf-8")
    cleaned = text
    # Dr.Claw / 兼容旧注释与路径
    patterns = (
        r"\n?# Dr\.Claw\nexport PATH=\"\$HOME/\.drclaw/bin:\$PATH\"\n?",
        r"\n?# QwenPaw\nexport PATH=\"\$HOME/\.qwenpaw/bin:\$PATH\"\n?",
        r"\n?# CoPaw\nexport PATH=\"\$HOME/\.copaw/bin:\$PATH\"\n?",
        r"\n?# QwenPaw\nexport PATH=\"\$HOME/\.drclaw/bin:\$PATH\"\n?",
    )
    for pattern in patterns:
        cleaned = re.sub(pattern, "\n", cleaned)
    if cleaned == text:
        return False

    profile.write_text(cleaned, encoding="utf-8")
    return True


@click.command("uninstall")
@click.option(
    "--purge",
    is_flag=True,
    help="同时删除全部数据（配置、会话、模型等）",
)
@click.option("--yes", is_flag=True, help="跳过确认提示")
def uninstall_cmd(purge: bool, yes: bool) -> None:
    """移除 Dr.Claw 环境、CLI 包装与 shell PATH 条目。"""
    wd = WORKING_DIR

    if purge:
        click.echo(f"将删除 {wd} 下的全部 Dr.Claw 数据")
    else:
        click.echo("将删除 Dr.Claw Python 环境与 CLI 包装脚本。")
        click.echo(f"{wd} 中的配置与数据会保留。")

    if not yes:
        ok = click.confirm("继续？", default=False)
        if not ok:
            click.echo("已取消。")
            return

    for dirname in _INSTALLER_DIRS:
        d = wd / dirname
        if d.exists():
            shutil.rmtree(d)
            click.echo(f"  已删除 {d}")

    if purge and wd.exists():
        shutil.rmtree(wd)
        click.echo(f"  已删除 {wd}")

    for profile in _SHELL_PROFILES:
        if _remove_path_entry(profile):
            click.echo(f"  已清理 {profile}")

    click.echo("")
    click.echo("Dr.Claw 已卸载。请重新打开终端。")
