#!/usr/bin/env bash
# 工作区一键搭建入口（Linux；调用 setup_workspace.py，用法见 README「从零搭建工作区」）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "未找到 python3 / python，请先安装 Python 3（见 README「从零搭建工作区」）" >&2
  exit 1
fi

exec "$PY" "$SCRIPT_DIR/setup_workspace.py" "$@"
