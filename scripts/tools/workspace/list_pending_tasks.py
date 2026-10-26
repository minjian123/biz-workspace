#!/usr/bin/env python3
"""工作区计划表盘点：扫描全部平级仓的计划表，列出未完成任务（跨仓复用）。

**只读脚本**：只读计划表、不改任何文档；用于「下一项做什么」「哪些项逾期」「某个项目还剩什么」这类追问。

扫描范围（缺省值，均在**存在**时纳入）：

    <工作区根>/<仓>/<仓>文档/项目/<项目>/计划/*.md
    <工作区根>/<仓>/<仓>文档/计划/*.md          # 少数仓没有「项目」层级时的兜底

仓清单：`bms` / `mdm` / `biz` / `cw` / `engkit` / `test`。**软链文档根按真实路径去重**——各仓根还有
`bms文档` / `mdm文档` / `test文档` 之类的软链，不去重会把同一份计划表数两遍。

兼容三种列形（同一工作区内并存，逐表按表头识别）：

    A) 编号 | 任务 | 工时（重估）| 完成日期 | 任务文件 | 偏差与遗留
       → 「完成日期」带日期前缀即完成（允许 `2026-10-22（_01 / _02 已完成…）` 这类括注；
         空 / `—` / `-` / 纯文字视为未完成）
    B) 编号 | 任务 | 状态 | 工时 | 依赖 | 排期窗口 | 备注 | 偏差与遗留
       → 按「状态」判定；合法取值见 `LEGAL_STATUSES`
    C) 编号 | 任务 | 工时 | 依赖 | 排期窗口 | 备注 | 偏差与遗留
       → 既无状态也无完成日期：一律按未完成上报，并记一条「缺状态列」提示（催补列，不静默放过）

逾期判定：排期窗口形如 `2026-10-26 ~ 2026-10-28`，末日期早于基准日（缺省今天）且任务未完成即逾期；
窗口不是日期区间（如「搁置（占位已交付…）」）时不计逾期，原样展示。

用法（在工作区根运行）::

    python3 scripts/tools/workspace/list_pending_tasks.py                 # 未完成项，按窗口紧急度排序
    python3 scripts/tools/workspace/list_pending_tasks.py --all           # 含已完成
    python3 scripts/tools/workspace/list_pending_tasks.py --repo bms --project 07B
    python3 scripts/tools/workspace/list_pending_tasks.py --overdue       # 只看逾期
    python3 scripts/tools/workspace/list_pending_tasks.py --exclude-parked  # 排除「搁置」
    python3 scripts/tools/workspace/list_pending_tasks.py --json          # 机器可读
    python3 scripts/tools/workspace/list_pending_tasks.py --check         # 有未完成即退出码 1
    python3 scripts/tools/workspace/list_pending_tasks.py --today 2026-10-26   # 固定基准日（复盘用）
    python3 scripts/tools/workspace/list_pending_tasks.py --self-test      # 内置用例

退出码：0 正常；1 `--check` 命中未完成（或发现非法状态 / 缺状态列）；2 参数或工作区结构错误。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
"""本脚本所在目录（`<工作区根>/scripts/tools/workspace`）。"""

DEFAULT_ROOT = SCRIPT_DIR.parents[2]
"""缺省工作区根：脚本位置上溯三级（workspace → tools → scripts → 工作区根）。"""

REPO_NAMES = ("bms", "mdm", "biz", "cw", "engkit", "test")
"""工作区内的平级仓目录名（存在才纳入；`cw` 属于另一组合的产品仓，按需）。"""

TASK_KEY_RE = re.compile(r"^\d{2}[A-Z]?_\d{2}$")
"""任务编号形态：`01_01` / `07B_01` 这类两段编号。"""

WINDOW_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\s*~\s*(\d{4}-\d{2}-\d{2})")
"""排期窗口形态：`2026-10-26 ~ 2026-10-28`。"""

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
"""完成日期前缀形态：`2026-10-08`（允许其后带括注）。"""

DONE_STATUSES = frozenset({"已完成", "已关闭", "已交付"})
"""视为完成的状态取值。"""

PARKED_STATUSES = frozenset({"搁置"})
"""有意暂停的状态取值：算未完成但不阻塞（`--check` 可排除）。"""

LEGAL_STATUSES = frozenset(
    {"未开始", "进行中", "部分完成", "已完成", "搁置", "已关闭", "已交付"}
)
"""计划表「状态」列的合法取值（与《文档生成规范》保持一致）。"""

HEADER_KEY, HEADER_TASK, HEADER_STATUS = "编号", "任务", "状态"
HEADER_FINISH, HEADER_WINDOW, HEADER_HOURS = "完成日期", "排期窗口", "工时"

SCHEMA_B, SCHEMA_A, SCHEMA_C = "B（状态）", "A（完成日期）", "C（无状态列）"


@dataclass(frozen=True)
class Task:
    """一条计划表任务行。"""

    repo: str
    project: str
    key: str
    name: str
    status: str
    schema: str
    window: str
    window_end: dt.date | None
    done: bool
    plan: str

    @property
    def parked(self) -> bool:
        """是否「搁置」（未完成但不阻塞）。"""
        return self.status in PARKED_STATUSES

    def overdue(self, today: dt.date) -> bool:
        """是否逾期：未完成且窗口末日期早于基准日。"""
        return not self.done and self.window_end is not None and self.window_end < today


@dataclass(frozen=True)
class PlanInfo:
    """一份计划表的扫描结果概要。"""

    repo: str
    project: str
    path: str
    schema: str
    tasks: int


@dataclass(frozen=True)
class Report:
    """整次盘点的完整结果（文本与 JSON 共用）。"""

    plans: list[PlanInfo]
    tasks: list[Task]
    problems: list[str]
    missing_repos: list[str]


def split_row(line: str) -> list[str] | None:
    """切分 Markdown 表格行；非表格行与表头分隔行返回 `None`。"""
    text = line.strip()
    if len(text) < 2 or not text.startswith("|") or not text.endswith("|"):
        return None
    cells = [cell.strip() for cell in text[1:-1].split("|")]
    if all(cell and set(cell) <= set("-: ") for cell in cells):
        return None
    return cells


def column_index(header: list[str], name: str) -> int | None:
    """按列名取下标（容忍「工时（重估）」这类括注后缀）。"""
    for index, cell in enumerate(header):
        if cell == name or cell.startswith(name):
            return index
    return None


def cell_at(cells: list[str], index: int | None) -> str:
    """按下标取单元格；缺列或越界返回空串（列形差异不致命）。"""
    if index is None or index >= len(cells):
        return ""
    return cells[index]


def plain_name(cell: str) -> str:
    """去掉 Markdown 链接与强调标记，只留任务名文本。"""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", cell)
    return text.replace("**", "").replace("`", "").strip()


def detect_schema(header: list[str]) -> str:
    """按表头判定列形。"""
    if HEADER_STATUS in header:
        return SCHEMA_B
    if HEADER_FINISH in header:
        return SCHEMA_A
    return SCHEMA_C


def window_end_of(window: str) -> dt.date | None:
    """从排期窗口取末日期；非日期区间（如「搁置（…）」）返回 `None`。"""
    match = WINDOW_RE.search(window)
    if not match:
        return None
    try:
        return dt.date.fromisoformat(match.group(2))
    except ValueError:
        return None


def build_task(
    *,
    repo: str,
    project: str,
    cells: list[str],
    header: list[str],
    schema: str,
    plan: str,
) -> Task:
    """把一行表格单元格转成任务对象（列缺失按空值处理）。"""
    status = cell_at(cells, column_index(header, HEADER_STATUS))
    finish = cell_at(cells, column_index(header, HEADER_FINISH))
    window = cell_at(cells, column_index(header, HEADER_WINDOW))
    if schema == SCHEMA_B:
        done = status in DONE_STATUSES
    elif schema == SCHEMA_A:
        done = bool(DATE_RE.match(finish))
    else:
        done = False
    label = status or ("已完成" if done else "未完成")
    return Task(
        repo=repo,
        project=project,
        key=cells[0],
        name=plain_name(cell_at(cells, column_index(header, HEADER_TASK)))
        or "（任务名缺失）",
        status=label,
        schema=schema,
        window=window or "—",
        window_end=window_end_of(window),
        done=done,
        plan=plan,
    )


def parse_plan(
    *, repo: str, project: str, path: Path, plan_label: str
) -> tuple[PlanInfo, list[Task], list[str]]:
    """解析一份计划表：返回概要、任务行与问题清单（一文件可含多张表，逐表判定列形）。"""
    tasks: list[Task] = []
    problems: list[str] = []
    tables: list[tuple[str, int]] = []
    header: list[str] = []
    schema = ""
    rows = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("|"):
            if header:
                tables.append((schema, rows))
            header, rows = [], 0
            continue
        cells = split_row(line)
        if cells is None:
            continue
        if HEADER_KEY in cells and HEADER_TASK in cells:
            if header:
                tables.append((schema, rows))
            header, schema, rows = cells, detect_schema(cells), 0
            continue
        if not header or not TASK_KEY_RE.match(cells[0]):
            continue
        task = build_task(
            repo=repo,
            project=project,
            cells=cells,
            header=header,
            schema=schema,
            plan=plan_label,
        )
        tasks.append(task)
        rows += 1
        if schema == SCHEMA_B and task.status not in LEGAL_STATUSES:
            problems.append(
                f"{plan_label}：{task.key} 状态「{task.status}」不在合法取值（{sorted(LEGAL_STATUSES)}）"
            )
    if header:
        tables.append((schema, rows))
    for table_schema, count in tables:
        if table_schema == SCHEMA_C and count:
            problems.append(
                f"{plan_label}：该表表头无「状态 / 完成日期」列，{count} 行按未完成上报（建议补列）"
            )
    if not tasks:
        problems.append(f"{plan_label}：未解析到任务行（列形可能已变更，请核对表头）")
    labels = (
        " / ".join(sorted({table_schema for table_schema, _ in tables if table_schema}))
        or "未识别"
    )
    return PlanInfo(repo, project, plan_label, labels, len(tasks)), tasks, problems


def discover_plans(
    ws_root: Path, repos: tuple[str, ...]
) -> tuple[list[tuple[str, str, Path]], list[str]]:
    """发现各仓计划表；返回 `(仓, 项目, 路径)` 列表与缺失仓清单。"""
    found: list[tuple[str, str, Path]] = []
    missing: list[str] = []
    seen_plans: set[Path] = set()
    seen_docs: set[Path] = set()
    for repo in repos:
        repo_dir = ws_root / repo
        if not repo_dir.is_dir():
            missing.append(repo)
            continue
        for doc_root in sorted(repo_dir.glob("*文档")):
            if not doc_root.is_dir() or doc_root.is_symlink():
                continue  # 软链文档根（`bms/mdm文档 → ../mdm/mdm文档`）归属本仓之外的仓，交给真实仓扫
            real_doc = doc_root.resolve()
            if real_doc in seen_docs:
                continue
            seen_docs.add(real_doc)
            for plan in sorted(
                [*doc_root.glob("项目/*/计划/*.md"), *doc_root.glob("计划/*.md")]
            ):
                real_plan = plan.resolve()
                if real_plan in seen_plans:
                    continue
                seen_plans.add(real_plan)
                found.append((repo, plan.parent.parent.name, plan))
    return found, missing


def collect(ws_root: Path, repos: tuple[str, ...] = REPO_NAMES) -> Report:
    """扫描并汇总整次盘点结果。"""
    plans_files, missing = discover_plans(ws_root, repos)
    plans: list[PlanInfo] = []
    tasks: list[Task] = []
    problems: list[str] = []
    for repo, project, path in plans_files:
        label = path.relative_to(ws_root).as_posix()
        info, parsed, plan_problems = parse_plan(
            repo=repo, project=project, path=path, plan_label=label
        )
        plans.append(info)
        tasks.extend(parsed)
        problems.extend(plan_problems)
    return Report(plans=plans, tasks=tasks, problems=problems, missing_repos=missing)


def select_tasks(
    tasks: list[Task], args: argparse.Namespace, today: dt.date
) -> list[Task]:
    """按命令行过滤条件筛选任务。"""
    chosen: list[Task] = []
    for task in tasks:
        if not args.all and task.done:
            continue
        if args.repo and task.repo not in args.repo:
            continue
        if args.project and not any(word in task.project for word in args.project):
            continue
        if args.status and task.status not in args.status:
            continue
        if args.exclude_parked and task.parked:
            continue
        if args.overdue and not task.overdue(today):
            continue
        chosen.append(task)
    if args.sort == "task":
        return sorted(chosen, key=lambda item: (item.repo, item.project, item.key))
    return sorted(
        chosen,
        key=lambda item: (
            item.window_end is None,
            item.window_end or dt.date.max,
            item.repo,
            item.project,
            item.key,
        ),
    )


def summarize(tasks: list[Task], today: dt.date) -> dict[str, int]:
    """统计各项计数（口径写进文本与 JSON 输出）。"""
    pending = [task for task in tasks if not task.done]
    return {
        "tasks": len(tasks),
        "done": len(tasks) - len(pending),
        "pending": len(pending),
        "overdue": sum(1 for task in pending if task.overdue(today)),
        "parked": sum(1 for task in pending if task.parked),
    }


def render_text(
    report: Report, chosen: list[Task], args: argparse.Namespace, today: dt.date
) -> str:
    """渲染人工阅读的文本报告（Markdown 表格，分组按仓 / 项目）。"""
    lines: list[str] = []
    stats = summarize(report.tasks, today)
    repos = sorted({plan.repo for plan in report.plans})
    lines.append(f"工作区：{args.root}")
    lines.append(f"基准日：{today.isoformat()}")
    lines.append(
        f"计划表：{len(report.plans)} 份（仓 {len(repos)} 个：{' / '.join(repos) or '无'}）；"
        f"任务 {stats['tasks']} 项：已完成 {stats['done']}、未完成 {stats['pending']}"
        f"（逾期 {stats['overdue']}、搁置 {stats['parked']}）"
    )
    if report.missing_repos:
        lines.append(f"未纳入（目录不存在）：{' / '.join(report.missing_repos)}")
    if args.project or args.repo or args.overdue or args.status or args.exclude_parked:
        lines.append(f"已按条件过滤，本次展示 {len(chosen)} 项")
    lines.append("")

    if not chosen:
        lines.append("无可展示任务（若预期非空，加 `--all` 或放宽过滤条件）。")
    else:
        lines.append("| 仓 | 项目 | 编号 | 任务 | 状态 | 排期窗口 | 逾期 | 计划表 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for task in chosen:
            mark = "是" if task.overdue(today) else ""
            lines.append(
                f"| {task.repo} | {task.project} | {task.key} | {task.name} | {task.status} "
                f"| {task.window} | {mark} | `{task.plan}` |"
            )

    if report.problems:
        lines.append("")
        lines.append("需人工确认：")
        for problem in report.problems:
            lines.append(f"- {problem}")
    return "\n".join(lines)


def render_json(
    report: Report, chosen: list[Task], args: argparse.Namespace, today: dt.date
) -> str:
    """渲染机器可读报告（`--json`）。"""
    payload = {
        "workspace": str(args.root),
        "today": today.isoformat(),
        "summary": summarize(report.tasks, today),
        "shown": len(chosen),
        "plans": [
            {
                "repo": plan.repo,
                "project": plan.project,
                "path": plan.path,
                "schema": plan.schema,
                "tasks": plan.tasks,
            }
            for plan in report.plans
        ],
        "tasks": [
            {
                "repo": task.repo,
                "project": task.project,
                "key": task.key,
                "name": task.name,
                "status": task.status,
                "done": task.done,
                "parked": task.parked,
                "overdue": task.overdue(today),
                "window": task.window,
                "window_end": task.window_end.isoformat() if task.window_end else None,
                "schema": task.schema,
                "plan": task.plan,
            }
            for task in chosen
        ],
        "problems": report.problems,
        "missing_repos": report.missing_repos,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def self_test() -> int:
    """内置用例：三种列形、逾期判定、搁置语义、非法状态与缺状态列提示。"""
    checks: list[tuple[str, bool]] = []
    with tempfile.TemporaryDirectory(prefix="plan-overview-") as tmp:
        root = Path(tmp)
        _write(
            root / "bms/bms文档/项目/01_甲/计划/01_计划_甲.md",
            "| 编号 | 任务 | 状态 | 工时 | 依赖 | 排期窗口 | 备注 | 偏差与遗留 |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| 01_01 | [已完成项](../任务/a.md) | 已完成 | 8h | 无 | 2026-10-01 ~ 2026-10-02 | 无 | 无 |\n"
            "| 01_02 | 逾期项 | 未开始 | 8h | 无 | 2026-10-01 ~ 2026-10-02 | 无 | 无 |\n"
            "| 01_03 | 在窗口内 | 进行中 | 8h | 无 | 2026-10-30 ~ 2026-11-02 | 无 | 无 |\n"
            "| 01_04 | 搁置项 | 搁置 | 4h | 无 | 搁置（占位已交付） | 无 | 无 |\n"
            "| 01_05 | 状态写错 | 收尾中 | 2h | 无 | — | 无 | 无 |\n",
        )
        _write(
            root / "mdm/mdm文档/项目/01_乙/计划/01_计划_乙.md",
            "| 编号 | 任务 | 工时（重估） | 完成日期 | 任务文件 | 偏差与遗留 |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| 01_01 | 已交付项 | 8h | 2026-10-08 | [x](../x.md) | 无 |\n"
            "| 01_02 | 未填日期 | 8h |  | [y](../y.md) | 无 |\n"
            "| 01_03 | 带括注完成 | 8h | 2026-10-22（`_01` 已完成） | [z](../z.md) | 无 |\n",
        )
        _write(
            root / "biz/biz文档/项目/01_丙/计划/01_计划_丙.md",
            "| 编号 | 任务 | 工时 | 依赖 | 排期窗口 | 备注 | 偏差与遗留 |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
            "| 01_01 | 无状态列项 | 4h | 无 | 2026-10-26 ~ 2026-10-28 | 无 | 无 |\n",
        )
        report = collect(root, ("bms", "mdm", "biz"))
        today = dt.date(2026, 10, 26)
        stats = summarize(report.tasks, today)
        by_key = {(task.repo, task.key): task for task in report.tasks}
        checks.append(("扫到 3 份计划表", len(report.plans) == 3))
        checks.append(("任务总数 9", stats["tasks"] == 9))
        checks.append(("已完成 3", stats["done"] == 3))
        checks.append(("未完成 6", stats["pending"] == 6))
        checks.append(("逾期 1", stats["overdue"] == 1))
        checks.append(("搁置 1", stats["parked"] == 1))
        checks.append(
            (
                "列形识别正确",
                {plan.schema for plan in report.plans}
                == {SCHEMA_A, SCHEMA_B, SCHEMA_C},
            )
        )
        checks.append(
            (
                "完成日期列判定",
                by_key[("mdm", "01_01")].done and not by_key[("mdm", "01_02")].done,
            )
        )
        checks.append(("带括注日期按完成", by_key[("mdm", "01_03")].done))
        checks.append(("逾期只在未完成项上", by_key[("bms", "01_02")].overdue(today)))
        checks.append(("窗口内不算逾期", not by_key[("bms", "01_03")].overdue(today)))
        checks.append(
            ("非日期窗口不计逾期", by_key[("bms", "01_04")].window_end is None)
        )
        checks.append(("缺状态列按未完成", not by_key[("biz", "01_01")].done))
        checks.append(
            (
                "非法状态入问题清单",
                any("状态写错" in item or "收尾中" in item for item in report.problems),
            )
        )
        checks.append(
            (
                "缺状态列提示",
                any(
                    "缺状态列" in item or "无「状态" in item for item in report.problems
                ),
            )
        )
        args = argparse.Namespace(
            root=root,
            all=False,
            repo=[],
            project=[],
            status=[],
            exclude_parked=False,
            overdue=False,
            sort="window",
        )
        chosen = select_tasks(report.tasks, args, today)
        checks.append(("缺省只展示未完成", len(chosen) == 6))
        args.exclude_parked = True
        checks.append(
            ("排除搁置后 5 项", len(select_tasks(report.tasks, args, today)) == 5)
        )
        args.overdue = True
        checks.append(
            ("只看逾期剩 1 项", len(select_tasks(report.tasks, args, today)) == 1)
        )
    failures = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"  [{'通过' if ok else '失败'}] {name}")
    if failures:
        print(f"[list_pending_tasks --self-test] 失败 {len(failures)} 项")
        return 1
    print(f"[list_pending_tasks --self-test] 全部通过（{len(checks)} 项）")
    return 0


def _write(path: Path, text: str) -> None:
    """自测用：写文件（自动建目录、固定 LF 行尾）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def build_parser() -> argparse.ArgumentParser:
    """构造命令行参数。"""
    parser = argparse.ArgumentParser(
        prog="list_pending_tasks.py",
        description="扫描工作区各仓计划表，列出未完成任务（只读）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="退出码：0 正常；1 `--check` 命中未完成或发现问题；2 参数 / 结构错误。",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help=f"工作区根（缺省 {DEFAULT_ROOT}）",
    )
    parser.add_argument(
        "--repo", action="append", choices=list(REPO_NAMES), help="限定仓（可重复）"
    )
    parser.add_argument(
        "--project", action="append", default=[], help="限定项目（包含匹配，可重复）"
    )
    parser.add_argument(
        "--status", action="append", default=[], help="限定状态（精确匹配，可重复）"
    )
    parser.add_argument("--all", action="store_true", help="含已完成任务")
    parser.add_argument("--overdue", action="store_true", help="只看逾期")
    parser.add_argument("--exclude-parked", action="store_true", help="排除「搁置」")
    parser.add_argument(
        "--sort",
        choices=("window", "task"),
        default="window",
        help="排序：窗口紧急度 / 编号",
    )
    parser.add_argument("--today", help="基准日 YYYY-MM-DD（缺省今天；复盘或自测用）")
    parser.add_argument("--json", action="store_true", help="输出 JSON（机器可读）")
    parser.add_argument("--check", action="store_true", help="有未完成任务即退出码 1")
    parser.add_argument("--self-test", action="store_true", help="跑内置用例")
    return parser


def main(argv: list[str] | None = None) -> int:
    """命令行入口。"""
    args = build_parser().parse_args(argv)
    if args.self_test:
        return self_test()
    root = args.root.resolve()
    if not root.is_dir():
        print(f"工作区根不存在：{root}", file=sys.stderr)
        return 2
    try:
        today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    except ValueError:
        print(f"--today 需形如 2026-10-26，收到：{args.today}", file=sys.stderr)
        return 2
    repos = tuple(args.repo) if args.repo else REPO_NAMES
    report = collect(root, repos)
    if not report.plans:
        print(
            f"未发现计划表（查 `<仓>/*文档/项目/*/计划/*.md`）：{root}", file=sys.stderr
        )
        return 2
    chosen = select_tasks(report.tasks, args, today)
    if args.json:
        print(render_json(report, chosen, args, today))
    else:
        print(render_text(report, chosen, args, today))
    if args.check:
        blocking = [task for task in report.tasks if not task.done and not task.parked]
        if blocking or report.problems:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
