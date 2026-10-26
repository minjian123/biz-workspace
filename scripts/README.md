# scripts — 工作区工具链

本目录存放**工作区级工具链**（跨仓库、与工作区结构相关的脚本）；平台与工程工具在 `bms/scripts/`，两边不互相收纳。

## 工具链清单（`tools/` 子目录）

| 工具 | 用途 |
| --- | --- |
| `tools/workspace/` | 一键搭建工作区：`setup_workspace.py` 克隆 bms / 产品 / test 仓、建三处软链、核对分支与本地待办；入口 `搭建工作区.sh`（Linux）/ `搭建工作区.bat`（Windows）。用法见 [README](../README.md)「从零搭建工作区」节 |
| `tools/workspace/` | 工作区卫生护栏：`check_workspace_hygiene.py` 检查临时 / 日志文件是否只落在工作区根 `tmp/` 与各仓 `.cache/`（违规退出码 1），`--clean` 隔离到 `tmp/_quarantine/<时间戳>/`；入口 `检查工作区卫生.sh` / `.bat`。已接入 bms 预检第一步（`bms/engkit.toml`），口径见 [AGENTS.md](../AGENTS.md)「工作区卫生」节 |
| `tools/workspace/` | 计划表盘点：`list_pending_tasks.py` 扫描**全部平级仓**的计划表（`<仓>/<仓>文档/项目/<项目>/计划/*.md`，软链文档根按真实路径去重），列出未完成任务、逾期项与列形问题（兼容「状态」/「完成日期」/无状态列三种列形）；入口 `列出待办任务.sh` / `.bat`。用法：`python3 scripts/tools/workspace/list_pending_tasks.py [--all] [--repo bms] [--project 07B] [--overdue] [--exclude-parked] [--json] [--check] [--today YYYY-MM-DD] [--self-test]`；未完成即退出码 1（`--check`） |

## 职责边界

- 只放**工作区级**工具（克隆与软链、跨仓库核对等）；平台机制与 CI 依赖的脚本留在 `bms/scripts/tools/`，不迁入本目录。
- 命名沿用 bms 工具链风格：Python 脚本 snake_case 英文名，入口脚本中文名（如「搭建工作区.sh」），与《命名规范》代码标识符英文化的要求一致。
- 不写凭据：凭据统一存各仓库 `deploy/.env`（不入库），脚本读取而非硬编码。
- 结构：`tools/<工具名>/` 一工具一目录、自包含（脚本 + docstring 或自带 README）。

> 依《文档生成规范》编写 · 工作区配置仓库
