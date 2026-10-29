# scripts — 工作区工具链

本目录存放**工作区级工具链**（跨仓库、与工作区结构相关的脚本）；平台与工程工具在 `bms/scripts/`，两边不互相收纳。

## 工具链清单（`tools/` 子目录）

| 工具 | 用途 |
| --- | --- |
| `tools/workspace/` | 一键搭建工作区：`setup_workspace.py` 克隆 bms / 产品 / test 仓、建三处软链、核对分支与本地待办；入口 `搭建工作区.sh`（Linux）/ `搭建工作区.bat`（Windows）。用法见 [README](../README.md)「从零搭建工作区」节 |
| `tools/workspace/` | 工作区卫生护栏：`check_workspace_hygiene.py` 检查临时 / 日志文件是否只落在工作区根 `tmp/` 与各仓 `.cache/`（违规退出码 1），`--clean` 隔离到 `tmp/_quarantine/<时间戳>/`；入口 `检查工作区卫生.sh` / `.bat`。已接入 bms 预检第一步（`bms/engkit.toml`），判定口径见下文「工作区卫生」节 |
| `tools/workspace/` | 计划表盘点与体检：`list_pending_tasks.py` 扫描**全部平级仓**的计划表（`<仓>/<仓>文档/项目/<项目>/计划/*.md`，软链文档根按真实路径去重），列出未完成任务 / 逾期项 / 列形问题（兼容「状态」/「完成日期」/无状态列三种列形）；`--lint` 按《计划文档规范》§4/§5 校列名顺序、列数、状态取值、「已完成」是否误留剩余表、窗口形态（区间 / 单日 / 搁置）、完成日期形态与编号重复。入口 `列出待办任务.sh` / `.bat`。用法：`python3 scripts/tools/workspace/list_pending_tasks.py [--all] [--repo bms] [--project 07B] [--overdue] [--exclude-parked] [--sort window|task] [--json] [--check] [--lint] [--today YYYY-MM-DD] [--self-test]`；`--check` / `--lint` 命中问题即退出码 1 |

## 工作区卫生 <a id="hygiene"></a>

**落点红线**：临时文件、日志、截图、脚本草稿、探针产物一律落**工作区根 `tmp/`**；工程缓存落**各仓 `.cache/`**。除此以外的任何位置出现日志 / 临时类文件都算**污染工作区**。

- **禁止落在仓库根 / 源码目录**：`bms/`、`mdm/`、`engkit/`、`biz/`、`test/` 的仓根与源码目录内**不得**出现 `*.log` / `*.err` / `*.out` / `tmp-*` / `.coverage*` 等产物——即使已 gitignore 也不许（污染的是磁盘落点与检索噪音，不是提交历史）。
- **判定口径**：以**落点白名单**为主（不依赖扩展名黑名单）；**已 git 跟踪的项目文件天然豁免**；依赖与构建目录（`node_modules` / `.venv` / `__pycache__` / `dist` …）整体剪枝。
- **护栏即时报错**：`bms/engkit.toml` 预检第一步已接入该检查（bms 薄包装 `bms/scripts/tools/preflight/check_workspace_hygiene.py` → 本目录实现），白名单落点之外出现日志 / 临时文件即**预检失败**；CI 只 clone bms 单仓、无工作区上下文时自动跳过。
- **随手自查 / 清理**：工作区根执行 `python scripts/tools/workspace/check_workspace_hygiene.py`（违规退出码 1）；加 `--clean` 把违规文件隔离到 `tmp/_quarantine/<时间戳>/`；入口脚本 `检查工作区卫生.sh` / `.bat`。
- **工具产物落点**：Playwright MCP 已配 `--output-dir tmp/playwright/mcp`（会话截图 / 快照直落 `tmp/`）；新增工具若默认往仓根写产物，**改配置指到 `tmp/`**，不要事后搬运。

## 职责边界

- 只放**工作区级**工具（克隆与软链、跨仓库核对等）；平台机制与 CI 依赖的脚本留在 `bms/scripts/tools/`，不迁入本目录。
- 命名沿用 bms 工具链风格：Python 脚本 snake_case 英文名，入口脚本中文名（如「搭建工作区.sh」），与《命名规范》代码标识符英文化的要求一致。
- 不写凭据：凭据统一存各仓库 `deploy/.env`（不入库），脚本读取而非硬编码。
- 结构：`tools/<工具名>/` 一工具一目录、自包含（脚本 + docstring 或自带 README）。

> 依《文档生成规范》编写 · 工作区配置仓库
