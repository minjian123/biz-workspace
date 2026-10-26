#!/usr/bin/env bash
# 工作区卫生检查入口（Linux；调用 check_workspace_hygiene.py，用法见 scripts/README.md）
# 无参数 = 检查（违规退出码 1）；--clean = 隔离到 tmp/_quarantine/
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

exec "$PY" "$SCRIPT_DIR/check_workspace_hygiene.py" "$@"
