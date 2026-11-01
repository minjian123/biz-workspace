"""卡顿 / 无响应自检：找出「谁在狂吃 IO」与「当前 pytest 跑到哪个用例」（只读，不改任何东西）。

背景：本地跑全量 / 开发环时偶发「整机变慢、磁盘灯常亮」，常见两类成因——
① 某个测试用例死循环（CPU 高 + 反复写 SQLite journal，但磁盘文件体积不涨）；
② 大量 xdist worker 起来瞬间导入模块（短暂峰值，很快结束）。
两者从任务管理器上看起来一样，本脚本用「两次采样 + pytest 临时目录推进」区分。

用法（工作区根执行）：

```bash
python3 scripts/tools/diagnostics/diagnose_stuck.py            # 默认两次采样、间隔 3 秒
python3 scripts/tools/diagnostics/diagnose_stuck.py --interval 5 --rounds 3
python3 scripts/tools/diagnostics/diagnose_stuck.py --json     # 机器可读
```

判定口径：
- 进程持续写 > `--busy-mbps`（缺省 1 MB/s）→ 记为「高 IO 进程」；
- pytest 临时根（`<tmp>/pytest-of-<user>/pytest-current`）**超过 `--stale-seconds`（缺省 30 秒）无新用例目录**
  且存在高 IO 进程 → 判「疑似卡住」，并打印最近执行的用例目录名与单跑定位命令；
- 否则判「未发现卡住（瞬时峰值或正常推进）」。
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

_WINDOWS = sys.platform == "win32"
_PS_SCRIPT = r"""
$rows = Get-CimInstance Win32_PerfFormattedData_PerfProc_Process |
  Where-Object { [int]$_.IDProcess -ne 0 } |
  Sort-Object { [double]$_.IOReadBytesPerSec + [double]$_.IOWriteBytesPerSec } -Descending |
  Select-Object -First 20
$out = foreach ($row in $rows) {
  $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $($row.IDProcess)" -ErrorAction SilentlyContinue
  [pscustomobject]@{
    pid = [int]$row.IDProcess
    name = ($row.Name -replace '#\d+$', '')
    read = [double]$row.IOReadBytesPerSec
    write = [double]$row.IOWriteBytesPerSec
    cpu = [int]$row.PercentProcessorTime
    cmd = if ($proc) { [string]$proc.CommandLine } else { '' }
  }
}
$out | ConvertTo-Json -Compress
"""
"""Windows 采样脚本（perf 计数器 + 命令行，一次往返）。"""


def _sample_windows() -> list[dict[str, Any]]:
    """Windows：取 IO 前 20 进程。

    Returns:
        list[dict[str, Any]]: 进程采样（pid / name / read / write / cpu / cmd）。
    """
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS_SCRIPT],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    raw = (completed.stdout or "").strip()
    if not raw:
        return []
    payload = json.loads(raw)
    return [payload] if isinstance(payload, dict) else list(payload)


def _sample_posix() -> list[dict[str, Any]]:
    """POSIX：读 `/proc/<pid>/io` 与 `/proc/<pid>/cmdline`（按读写量排序取前 20）。

    Returns:
        list[dict[str, Any]]: 进程采样（pid / name / read / write / cpu / cmd）。
    """
    rows: list[dict[str, Any]] = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            io_text = (entry / "io").read_text(encoding="utf-8", errors="replace")
            cmd = (entry / "cmdline").read_bytes().replace(b"\x00", b" ").decode("utf-8", "replace").strip()
        except OSError:
            continue
        values = dict(line.split(": ", 1) for line in io_text.splitlines() if ": " in line)
        rows.append(
            {
                "pid": int(entry.name),
                "name": Path(cmd.split(" ")[0]).name if cmd else "?",
                "read": float(values.get("rchar", 0)),
                "write": float(values.get("wchar", 0)),
                "cpu": 0,
                "cmd": cmd,
            }
        )
    rows.sort(key=lambda row: float(row["read"]) + float(row["write"]), reverse=True)
    return rows[:20]


def _sample() -> list[dict[str, Any]]:
    """取一次进程采样（跨平台）。

    Returns:
        list[dict[str, Any]]: 进程采样列表。
    """
    return _sample_windows() if _WINDOWS else _sample_posix()


def _pytest_root() -> Path:
    """pytest 临时根（`pytest-of-<user>`）。

    Returns:
        Path: 临时根目录（可能不存在）。
    """
    base = Path(os.environ.get("TEMP") or os.environ.get("TMPDIR") or "/tmp")
    return base / f"pytest-of-{getpass.getuser()}"


def _recent_cases(root: Path, limit: int = 6) -> tuple[list[tuple[str, float]], float]:
    """当前 pytest 临时根下最近写入的用例目录。

    Args:
        root: pytest 临时根。
        limit: 最多返回条数。

    Returns:
        tuple[list[tuple[str, float]], float]: [(用例目录名, 最后写入时间戳)] 与该根最后写入时间戳。
    """
    current = root / "pytest-current"
    if not current.is_dir():
        return [], 0.0
    items: list[tuple[str, float]] = []
    newest = 0.0
    for directory in current.iterdir():
        if not directory.is_dir():
            continue
        try:
            stamp = directory.stat().st_mtime
        except OSError:
            continue
        newest = max(newest, stamp)
        if directory.name.endswith("current"):
            continue
        items.append((directory.name, stamp))
    items.sort(key=lambda item: item[1], reverse=True)
    return items[:limit], newest


def _report(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
    *,
    interval: float,
    busy_mbps: float,
    stale_seconds: float,
) -> int:
    """打印诊断报告并返回退出码（0 = 未发现卡住 / 1 = 疑似卡住）。

    Args:
        before: 首次采样。
        after: 末次采样。
        interval: 采样间隔（秒）。
        busy_mbps: 持续写阈值（MB/s）。
        stale_seconds: pytest 临时目录无推进阈值（秒）。

    Returns:
        int: 退出码（0 正常 / 1 疑似卡住）。
    """
    counts = {int(row["pid"]): row for row in before}
    busy: list[dict[str, Any]] = []
    for row in after:
        pid = int(row["pid"])
        previous = counts.get(pid)
        grown = float(row["write"]) - float(previous["write"]) if previous else 0.0
        delta = grown / max(interval, 0.001) / (1024 * 1024)
        if delta >= busy_mbps:
            busy.append({**row, "mbps": round(delta, 1)})

    root = _pytest_root()
    cases, newest = _recent_cases(root)
    now = time.time()
    idle = round(now - newest, 1) if newest else -1.0

    print(f"== 采样：{time.strftime('%H:%M:%S')}（间隔 {interval:.0f}s）==")
    if busy:
        print(f"[高 IO 进程]（持续写 ≥ {busy_mbps} MB/s）")
        for row in busy:
            cmd = str(row.get("cmd") or "")[:110]
            print(f"  PID {row['pid']:<7} {row['name']:<16} 写 {row['mbps']} MB/s  CPU {row['cpu']}%  {cmd}")
    else:
        print("[高 IO 进程] 无（两次采样差值低于阈值）")

    print(f"[pytest 临时根] {root if root.is_dir() else '（不存在：近期未跑 pytest）'}")
    if cases:
        print(f"  最近用例目录（最后写入 {idle} 秒前）：")
        for name, stamp in cases:
            print(f"    {name}  ({time.strftime('%H:%M:%S', time.localtime(stamp))})")
    elif root.is_dir():
        print("  pytest-current 下暂无用例目录")

    if busy and (idle < 0 or idle > stale_seconds):
        print()
        print("[结论] 疑似卡住：存在持续高 IO 进程，且 pytest 用例目录已停止推进。")
        if cases:
            print(f"  最近执行：{cases[0][0]}（目录名 = 用例函数名前缀 + 序号）")
            print("  定位：把该目录名对应的用例单跑，加超时即可复现——")
            print("    cd bms/backend && python -m pytest <用例文件>::<用例名> -n 0 -v -p no:cacheprovider")
        print("  取完整现场：重跑本脚本并加 --rounds 3；确认后用 Ctrl+C / 任务管理器终止该 PID 的进程树。")
        return 1

    print()
    print("[结论] 未发现卡住：高 IO 已回落或 pytest 仍在推进（多为模块导入 / 建库的瞬时峰值）。")
    if busy:
        print(f"  提示：仍有进程在写（{', '.join(str(row['pid']) for row in busy)}），若持续超过 1 分钟再复跑本脚本。")
    return 0


def main(argv: list[str] | None = None) -> int:
    """入口。

    Args:
        argv: 命令行参数（None 取 `sys.argv`）。

    Returns:
        int: 退出码（0 正常 / 1 疑似卡住 / 2 参数非法）。
    """
    parser = argparse.ArgumentParser(description="卡顿自检：谁在吃 IO、pytest 跑到哪个用例（只读）")
    parser.add_argument("--interval", type=float, default=3.0, help="采样间隔（秒，缺省 3）")
    parser.add_argument("--rounds", type=int, default=2, help="采样轮数（缺省 2，至少 2）")
    parser.add_argument("--busy-mbps", type=float, default=1.0, help="持续写阈值（MB/s，缺省 1）")
    parser.add_argument("--stale-seconds", type=float, default=30.0, help="pytest 无推进阈值（秒，缺省 30）")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出采样结果")
    args = parser.parse_args(None if argv is None else list(argv))
    rounds = max(2, int(args.rounds))

    samples: list[list[dict[str, Any]]] = []
    for index in range(rounds):
        samples.append(_sample())
        if index < rounds - 1:
            time.sleep(max(0.5, float(args.interval)))

    if args.json:
        print(json.dumps({"samples": samples, "pytest_root": str(_pytest_root())}, ensure_ascii=False))
        return 0
    return _report(
        samples[0],
        samples[-1],
        interval=float(args.interval) * (rounds - 1),
        busy_mbps=float(args.busy_mbps),
        stale_seconds=float(args.stale_seconds),
    )


if __name__ == "__main__":
    raise SystemExit(main())
