#!/usr/bin/env bash
# 卡顿自检入口（Linux；调用 diagnose_stuck.py，用法见 scripts/README.md）
# 无参数 = 两次采样间隔 3 秒；--interval / --rounds / --busy-mbps / --stale-seconds / --json
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

exec "$PY" "$SCRIPT_DIR/diagnose_stuck.py" "$@"
