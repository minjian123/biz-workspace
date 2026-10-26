#!/usr/bin/env bash

# 计划表盘点入口（Linux；调用 list_pending_tasks.py，用法见 scripts/README.md）
# 无参数 = 列出全部未完成任务（按窗口紧急度排序）；--all / --overdue / --repo / --json / --check 见脚本 docstring
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "未找到 python3 / python，请先安装 Python 3" >&2
  exit 2
fi

exec "$PY" "$SCRIPT_DIR/list_pending_tasks.py" "$@"
