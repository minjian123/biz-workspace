#!/usr/bin/env python3
"""工作区卫生检查与清理（护栏）：临时 / 日志文件只许落在约定临时目录，否则立即报错。

口径（2026-10-26 用户拍板）：

- **落点白名单**：只允许工作区根 `tmp/` 与各仓 `.cache/` 等约定目录；
- **检查范围**：整个工作区（工作区根 + `bms` / `engkit` / `mdm` / `biz` / `test` 各仓）；
- **判定**：白名单落点之外的日志 / 临时类文件即违规（落点判据为主，不依赖扩展名黑名单）；
- **剪枝**：依赖与构建目录（`node_modules` / `.venv` / `__pycache__` / `dist` …）整体跳过。

「立即报错」的落地方式是接入 bms 预检（`bms/engkit.toml` 的 `[[preflight.steps]]`）：
预检一跑就查一遍，违规即非零退出；CI 只 clone bms 单仓、无工作区上下文时自动跳过。

用法（在工作区根运行）::

    python3 scripts/tools/workspace/check_workspace_hygiene.py           # 检查（违规退出码 1）
    python3 scripts/tools/workspace/check_workspace_hygiene.py --clean   # 隔离到 tmp/_quarantine/<时间戳>/
    python3 scripts/tools/workspace/check_workspace_hygiene.py --quiet   # 只报违规清单（预检用）

    # 指定工作区根（缺省按脚本位置推导：<工作区根>/scripts/tools/workspace/）
    python3 scripts/tools/workspace/check_workspace_hygiene.py --root D:/Develop/bizs

退出码：0 干净（或清理后干净）；1 存在违规；2 参数或环境错误。
"""

from __future__ import annotations

import argparse
import datetime
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
"""本脚本所在目录（`<工作区根>/scripts/tools/workspace`）。"""

DEFAULT_ROOT = SCRIPT_DIR.parents[2]
"""缺省工作区根：脚本位置上溯三级（workspace → tools → scripts → 工作区根）。"""

REPO_NAMES = ("bms", "engkit", "mdm", "biz", "cw", "test")
"""工作区内的平级仓库目录名（存在才纳入检查；`cw` 为另一组合的产品仓，按需）。"""

TEMP_ROOT_NAME = "tmp"
"""工作区根唯一合法的临时落点目录名（各仓内同名目录**不**放行）。"""

CACHE_DIR_NAME = ".cache"
"""仓内缓存目录名（`run_once` / `coverage` 等工程产物落点，任意层级放行）。"""

PRUNE_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "node_modules",
        "site-packages",
        "dist",
        "build",
        ".pnpm-store",
        ".turbo",
        ".next",
        ".nuxt",
        ".svelte-kit",
        "target",
        ".gradle",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".pyright",
        "__pycache__",
        "htmlcov",
        ".nyc_output",
        "playwright-report",
        "test-results",
        ".idea",
    }
)
"""整体剪枝的目录名（依赖 / 构建 / 工具缓存，均非人工产物，不参与判定）。"""

LOG_SUFFIXES = (
    ".log",
    ".err",
    ".out",
    ".tmp",
    ".temp",
    ".bak",
    ".orig",
    ".rej",
    ".trace",
    ".pstats",
    ".prof",
    ".lcov",
    ".tsbuildinfo",
)
"""日志 / 临时类文件的扩展名。"""

LOG_NAMES = frozenset({".coverage", "coverage.xml", ".coverage.json"})
"""日志 / 临时类文件的精确文件名（无扩展名或扩展名不便枚举者）。"""

LOG_PREFIXES = ("tmp-", "tmp_", ".coverage.")
"""日志 / 临时类文件名前缀（覆盖 `tmp-xxx` / `tmp_xxx` 这类命名变体）。"""


def out(msg: str = "") -> None:
    """打印一行（即时 flush，便于预检实时透传）。

    Args:
        msg: 输出内容。
    """
    print(msg, flush=True)


def is_temp_or_log(name: str) -> bool:
    """判断文件名是否属于日志 / 临时类产物。

    Args:
        name: 文件名（不含目录）。

    Returns:
        bool: 是日志 / 临时类文件返回 True。
    """
    lower = name.lower()
    if lower in LOG_NAMES:
        return True
    if lower.startswith(LOG_PREFIXES):
        return True
    return lower.endswith(LOG_SUFFIXES)


def repo_roots(ws_root: Path) -> list[Path]:
    """列出参与检查的仓库根（工作区根自身 + 存在的平级仓库）。

    Args:
        ws_root: 工作区根。

    Returns:
        list[Path]: 仓库根列表（工作区根恒在首位）。
    """
    roots = [ws_root]
    for name in REPO_NAMES:
        candidate = ws_root / name
        if candidate.is_dir() and not candidate.is_symlink():
            roots.append(candidate)
    return roots


def tracked_files(repo: Path) -> set[str]:
    """读取该 git 仓已跟踪文件集合（相对仓根、正斜杠）。

    已跟踪文件视为「项目文件」，天然豁免——仓库里正当存在的 `*.log` 配置等不误报。

    Args:
        repo: 仓库根。

    Returns:
        set[str]: 相对路径集合；非 git 目录或 git 不可用时为空集。
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "-z", "--cached"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return set()
    if result.returncode != 0:
        return set()
    return {item.replace("\\", "/") for item in result.stdout.decode("utf-8", "replace").split("\0") if item}


def iter_candidate_files(repo: Path, ws_root: Path):
    """遍历仓内候选文件（剪掉白名单落点与依赖构建目录）。

    Args:
        repo: 仓库根。
        ws_root: 工作区根（用于判定「工作区根 tmp/」白名单）。

    Yields:
        tuple[Path, str]: （绝对路径, 相对仓根的正斜杠路径）。
    """
    for dirpath, dirnames, filenames in os.walk(repo, topdown=True, followlinks=False, onerror=lambda _e: None):
        current = Path(dirpath)
        rel_dir = "" if current == repo else current.relative_to(repo).as_posix()
        kept: list[str] = []
        for name in dirnames:
            if name in PRUNE_DIRS or name == CACHE_DIR_NAME:
                continue
            # 工作区根：tmp/ 是白名单落点，各平级仓库由 repo_roots 单独扫描
            # （否则同一文件会被工作区根与仓库根各扫一次，重复计数）。
            if repo == ws_root and not rel_dir and (name == TEMP_ROOT_NAME or name in REPO_NAMES):
                continue
            kept.append(name)
        dirnames[:] = kept
        for name in filenames:
            yield current / name, (f"{rel_dir}/{name}" if rel_dir else name)


def scan(ws_root: Path) -> list[tuple[Path, str]]:
    """扫描整个工作区，收集白名单落点之外的日志 / 临时文件。

    Args:
        ws_root: 工作区根。

    Returns:
        list[tuple[Path, str]]: 违规项（绝对路径, 相对工作区根路径），按路径排序。
    """
    found: list[tuple[Path, str]] = []
    for repo in repo_roots(ws_root):
        tracked = tracked_files(repo)
        for path, rel_in_repo in iter_candidate_files(repo, ws_root):
            if rel_in_repo in tracked:
                continue
            if not is_temp_or_log(path.name):
                continue
            try:
                rel_in_ws = path.relative_to(ws_root).as_posix()
            except ValueError:
                rel_in_ws = path.as_posix()
            found.append((path, rel_in_ws))
    found.sort(key=lambda item: item[1])
    return found


def quarantine(ws_root: Path, items: list[tuple[Path, str]]) -> Path:
    """把违规文件移入 `tmp/_quarantine/<时间戳>/`（保留原相对路径结构）。

    Args:
        ws_root: 工作区根。
        items: `scan` 收集的违规项。

    Returns:
        Path: 隔离目录（本次时间戳目录）。
    """
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bucket = ws_root / TEMP_ROOT_NAME / "_quarantine" / stamp
    for path, rel_in_ws in items:
        target = bucket / rel_in_ws
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(target))
    return bucket


def main(argv: list[str]) -> int:
    """入口。

    Args:
        argv: 命令行参数（不含脚本名）。

    Returns:
        int: 退出码（0 干净 / 1 有违规 / 2 参数错误）。
    """
    parser = argparse.ArgumentParser(
        description="工作区卫生检查：临时 / 日志文件只许落在工作区根 tmp/ 与各仓 .cache/",
    )
    parser.add_argument("--root", default="", help="工作区根（缺省按脚本位置推导）")
    parser.add_argument("--clean", action="store_true", help="把违规文件隔离到 tmp/_quarantine/")
    parser.add_argument("--quiet", action="store_true", help="只输出违规清单与结论（预检用）")
    args = parser.parse_args(argv)

    ws_root = Path(args.root).resolve() if args.root else DEFAULT_ROOT.resolve()
    if not ws_root.is_dir():
        out(f"[卫生] 工作区根不存在：{ws_root}")
        return 2

    if not args.quiet:
        out(f"[卫生] 检查工作区：{ws_root}")
        out(f"[卫生] 纳入范围：{', '.join(root.name for root in repo_roots(ws_root))}")
        out("[卫生] 合法落点：工作区根 tmp/、各仓 .cache/（依赖与构建目录自动跳过）")

    items = scan(ws_root)

    if not items:
        if not args.quiet:
            out("[卫生] 通过：白名单落点之外没有日志 / 临时文件")
        return 0

    out(f"[卫生] 发现 {len(items)} 个白名单落点之外的日志 / 临时文件：")
    for path, rel_in_ws in items:
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        out(f"  - {rel_in_ws}  ({size} B)")

    if not args.clean:
        out("[卫生] 处理建议：`--clean` 隔离到 tmp/_quarantine/，或按落点约定手工移入工作区根 tmp/")
        return 1

    bucket = quarantine(ws_root, items)
    out(f"[卫生] 已隔离 {len(items)} 个文件 → {bucket.relative_to(ws_root).as_posix()}/")
    remaining = scan(ws_root)
    if remaining:
        out(f"[卫生] 仍有 {len(remaining)} 个违规项（可能为只读或占用中）：")
        for _path, rel_in_ws in remaining:
            out(f"  - {rel_in_ws}")
        return 1
    out("[卫生] 清理后复查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
