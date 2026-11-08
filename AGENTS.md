# AGENTS.md

思维链使用中文，用户是中国人，英文看不懂。

**注意1**：用户是中国人，英文看不懂。
**注意2**：如果缺乏对应知识，就去网上查资料。

## 讨论与确认（强制执行）

- **凡是待用户拍板的事项（技术选型、方案取舍、范围划分、是否执行某项修改、执行方式等），必须先逐项提出并逐一确认，严禁擅自替用户拍板——包括不得按推荐值或默认值直接执行。**
- **逐项确认必须使用 question 工具**，把本次所有待决项一次性列出（一项一个问题），每项格式固定：
  - 候选选项至少 2 个；
  - 推荐项放在第一位并标注"（推荐）"；
  - 每个选项附上差异说明，如果差异说明太长，可以先在会话中输出选项的差异说明，以供用户查看判断。
- **推荐项着眼长期**：候选选项的推荐一律优先**以后演化成本更低**的方案（可扩展 / 兼容 / 与设计节点一致 / 便于后续接入），不得为省眼前工作量推荐应付式方案；差异说明同时写明长期收益与迁移成本（若有）。
- 不要顾虑问题数量，问的越多越细越好；宁可把一项问题拆成多项问题来提问，也不要合并问题、不要遗漏问题或简化成"你看着办"。
- 用户未明确回答的项目保持未定，不得默认通过；继续追问，直到逐项确认完毕。
- 全部确认后，把确认结果汇总成表格回显给用户，用户无异议后才进入执行。
- 执行中如出现新的待拍板事项（原确认范围外），同样先询问再执行，不得自行扩展。
- 完整纪律：《[AI开发规范](bms/bms文档/规范/AI开发规范.md)》第 7 节「红线与纪律」；确认流程见第 3 节「产出与执行流程」。

## 工作区

- 本目录是**工作区**（组合层）：以 **bms 克隆**为基座，与 **engkit 克隆**（跨仓工程化工具包，必选）及一个或多个产品仓库克隆平级并置。
  - `bizs/`：`bms/`（BMS 平台/基座）+ `engkit/`（跨仓工程化工具包）+ `biz/`（biz 企业运营管理产品）+ `mdm/`（mdm 主数据管理产品）
  - `cws/`：`bms/`（BMS 平台/基座）+ `engkit/`（跨仓工程化工具包）+ `cw/`（CW 创作系统产品）

- **产品仓库只放产品专属内容**：产品文档根按项目命名（如 `biz文档/`、`mdm文档/`、`cw文档/`），不再在文档根下用软链占位基座目录（`规范`/`资料`/`资源`）；各产品仓库根设软链 `bms文档 → ../bms/bms文档` 与产品文档根并排，产品文档引用基座统一用 `../bms文档/…`。**主数据产品 mdm 与其他产品互引**：`bms/mdm文档 → ../mdm/mdm文档`、`biz/mdm文档 → ../mdm/mdm文档`（产品仓库根软链，同 `bms文档` 口径，正文分治见下）；通过 `bms文档` 软链编辑基座文件时，实际修改的是 bms 克隆，须回 bms 仓库提交，通过 `mdm文档` 软链编辑主数据文档时须回 mdm 仓库提交。

- **引用写法分治**：bms 正文提及主数据写**纯文本路径**（`mdm/mdm文档/…`，不写相对链接——CI 只 clone bms 会判断链，可类比 test 文档约定）；biz / mdm 正文可用相对链接（`../mdm文档/…`、`../bms文档/…`）跨仓跳转。

- **测试资产放独立仓库 `test/`（可选克隆）**：承载用例模板、测试数据、压测场景、探索性测试记录与测试侧脚本，文档根 `test文档/`（与 `bms文档/`、`biz文档/`、`mdm文档/` 同构）；**双向软链且两侧均不入 git**——`bms/test文档 → ../test/test文档`（**bms 仓根**，与 `bms文档/` 同级）、`test/bms文档 → ../bms/bms文档`（test 仓根）。bms 侧软链已写 `bms/.gitignore`，test 侧 `.gitignore` 忽略 `bms文档`。**bms 文档正文禁止写真链接指向测试文档或主数据文档**（CI 只 clone bms 会判断链），需提及时写纯文本路径。边界详见 bms《测试规范》「测试资产落点与组织」节。
- 工作区根目录本身是一个 **git 仓库**，只跟踪工作区配置（`AGENTS.md`、`README.md`、`scripts/`、`.opencode/`、`.gitignore`、`.vscode/`、`*.code-workspace`）；`bms/`、产品目录一律忽略。新工作区可先克隆本配置仓库，再运行 `scripts/tools/workspace/搭建工作区.sh`（或 `搭建工作区.bat`，用法见 `README.md`「从零搭建工作区」节）自动克隆各仓库并建软链；扩展新组合只需在工作区根新增产品仓库克隆（bms 保持平级不动）。
- IDE 使用：用工作区根的 `*.code-workspace` 打开（「工作区配置 / BMS 基座 / 产品」多根并置）；产品文档以产品仓库根的 `bms文档` 软链引用基座，权威基座文档统一从 BMS 根查看。
- 目录使用中文名；文档根按项目命名（bms 为 `bms文档/`、产品为 `<产品>文档/`，如 `biz文档/`、`cw文档/`）；回复与文档保持中文。

> **本节细节**：《[平台可扩展性规划](bms/bms文档/规划/平台可扩展性规划.md)》4.3「工作区模型与基座引用」（软链、配置仓、权威源、跨层引用盲区）；测试资产组织见《[测试规范](bms/bms文档/规范/测试规范.md)》14「测试资产落点与组织」；搭建步骤见 [README](README.md)「从零搭建工作区」。

## 各仓入口

| 仓 | 定位 | 入口文档 |
| --- | --- | --- |
| `bms/` | BMS 平台 / 基座（后端管理平台，业务不入平台） | `bms/README.md`、`bms/bms文档/文档首页.md` |
| `engkit/` | 护栏与开发脚本的**唯一实现**（文档校验 / 预检 / 选测 / 覆盖率 / 用例登记） | `engkit/README.md`、`engkit/engkit文档/文档首页.md` |
| `mdm/` `biz/` `cw/` | 产品仓（只放产品专属内容） | 各仓 `README.md` |

- 平台机制、扩展接入、标识符（表前缀 / 业务码 / 错误码段 / 事件域）登记以 bms 文档为权威。
- 工具配置只在各仓根 `engkit.toml`；新增仓库只加配置、不改工具包代码。

> **细节**：平台三层模型与扩展接入见《[平台可扩展性规划](bms/bms文档/规划/平台可扩展性规划.md)》与《[项目规划说明](bms/bms文档/规划/项目规划说明.md)》「平台扩展接入流程」；基座边界见《[基座文档清单](bms/bms文档/基座文档清单.md)》；engkit 的「各仓只放配置 / 包内不含仓名」见 [engkit 文档首页](engkit/engkit文档/文档首页.md) 与《[工具包开发约定](engkit/engkit文档/规范/工具包开发约定.md)》。

## 动手前

- 动手前先读《[AI开发规范](bms/bms文档/规范/AI开发规范.md)》**全文**（尤其 §5 交付一条龙、§7 红线与纪律、§8 检查清单——历次踩坑都沉淀在这里，只读前几节必漏），按「本地资源 → 规划 → 规范 → 设计 → 项目 → 需求 → 任务 → 计划 → 详细设计」建上下文；**先设计后编码**，偏差回写设计。
- **解释器只认仓内 venv**：本仓 `pyproject.toml` 为 `target-version = "py314"`，代码使用 Python 3.14 语法（如 PEP 758 的无括号 `except A, B:`）。验证一律走 `bms/backend/.venv/Scripts/python.exe`（3.14）与同目录 `ruff.exe`；**禁止用 PATH 上的 `python`**——PATH 首个命中是 WorkBuddy 内置的 3.13 运行时（`~/.workbuddy/binaries/python/`），拿它跑 `ast.parse` / `pytest` 会把合法语法误报成 `SyntaxError`。**不要删除该内置运行时**（归宿主应用所有，删除会损伤宿主脚本执行且升级后回滚）。
- 生成文档前读《[文档生成规范](bms/bms文档/规范/文档生成规范.md)》，三条最常踩的：
  - **逻辑图形**（流程 / 时序 / 状态 / 类 / 关系 / 甘特）一律 mermaid；**目录树、文件清单**用框线文本（`└├│─` + 行尾 `#`），不得画成 mermaid；**线框图 / 可交互原型**用 html。
  - html 的图片 / 音视频放同级「资源」下同名目录。
  - md 预览 mermaid 用 VS Code **内置扩展**，**勿装** `bierner.markdown-mermaid`（会抢注配置键、日志刷错）。
- 命名（代码 / 数据库 / API / 基础设施）遵循《[命名规范](bms/bms文档/规范/命名规范.md)》。
- 测试分层、覆盖率门禁（100% 行 + 分支）与测试资产落点见《[测试规范](bms/bms文档/规范/测试规范.md)》。
- **集合声明只落插入序并发集合类（高频踩坑，护栏常拦）**：类字段、函数参数与返回、带注解的局部变量，只要声明集合就**一律用继承 `BaseCollection` 的插入序并发集合类**——可变落 `ConcurrentStableList` / `ConcurrentStableSet` / `ConcurrentStableDict`，**值对象字段落不可变形态 `ConcurrentStableFrozen*`**；**禁裸** `dict` / `list` / `set` / `frozenset` 及 typing 别名，**禁只读 / 可变抽象** `Sequence` / `Mapping` / `AbstractSet` / `Collection` / `Mutable*`，**禁直接声明或继承** `Sorted*` / `ConcurrentSorted*`（体系内部实现，排序走排序契约）。省事记法：先判「这个集合写不写」——要写落 `ConcurrentStable*`，只读 / 冻结语义（值对象、常量）落 `ConcurrentStableFrozen*`（冻结后写入抛 `TypeError`，**别拿它当可写集合用**），**没有第三选项**；同构 `tuple[X, ...]` 视同集合声明、同样落 `ConcurrentStableList`，固定元数 `tuple[A, B]`（多返回值 / 元组值）才是显式豁免。
  - **不查**：`Iterable` / `Iterator` / `Callable` 等迭代与调用协议；**照查**：测试目录、`ClassVar` 类级常量、`BaseSettings` 配置字段、函数体带注解局部变量（这四处是最常见的「我明明没用裸 list」型失败）。
  - 框架强制内置类型的边界（ASGI `scope`、查询入参绑定、pydantic-settings 配置源等）才可在声明行行尾或紧邻上一行标注 `# bare-collections:allow`（附一句理由），**不得用于业务侧**。
  - 护栏 `engkit base bare-collections`（=`scripts/tools/base_check/check_bare_collections.py`）已进提交环与推送环，存量以基线快照「只减不增」豁免；细节见《[后端开发规范](bms/bms文档/规范/后端开发规范.md)》「集合与排序」节、《[后端基类清单](bms/bms文档/后端基类清单.md)》「集合体系」节。

## 日常怎么干

### 测试用例登记（Kiwi）：设计定稿后、写用例前

- **先登记、后编码**：一个任务通常只登记**一条**用例，取得平台自增主键后，代码用 `@pytest.mark.kiwi_id(<编号>)` 标注（多条断言共用同一编号）；**禁止复用或改派已有编号**。
- 登记走容器内 Django shell（不依赖登录态、可脚本化）：
  `ssh minjian@192.168.0.107 "docker exec -i bms-kiwi /Kiwi/manage.py shell" < register_cases.py`
  （已配免密；中文脚本先落本地文件再重定向，避免控制台编码破坏 UTF-8）。
- 字段口径：Category「平台骨架」、Priority `P2`、状态 `CONFIRMED`、Tag「自动化」；`text` 写覆盖范围（用例清单）与自动化文件路径。
- 登记后**回读核对**用例号与代码 `kiwi_id` 标注一致：
  `... manage.py shell -c "from tcms.testcases.models import TestCase as T; print([(c.pk, c.summary) for c in T.objects.order_by('-pk')[:5]])"`
- 平台连不上时**停下来问**，不得挂空号、不得「先编码后补号」。
- 细节（平台信息 / 脚本模板 / JSON-RPC 现状）：《[KiwiTCMS 部署使用说明](bms/bms文档/资料/开发服务器/linux/KiwiTCMS部署使用说明.md)》§5.2、§5.3。

### 提交前：钩子自动跑（预检的提交环）

- 每次 `git commit` 自动执行：`.git/hooks/pre-commit` → `bms/scripts/tools/preflight/提交前预检.py`（与推送预检读同一份步骤表，范围收敛到改动文件）。
- **必须拿到完整预检结果**：输出完整落盘（含 stderr）后整体阅读；**禁止**用 `Select-Object -Last N` / `Select-String` / `head` / `tail` 等方式截断或过滤后再判断——被滤掉的正是失败明细与行号。以「失败 N 项」全表为准。
- **一次改完再重跑**：预检会跑完全部适用步骤才汇总；拿到全表后按清单批量修，不得「改一处、跑一次」。
- 紧急回滚可用 `git commit --no-verify`（推送环仍会完整复判，不构成绕过）。
- 细节（判据分类与增量资格）：《[AI开发规范](bms/bms文档/规范/AI开发规范.md)》「提交环 / 推送环」节。

### 推送：唯一入口，预检是它的内部步骤

- 命令：`bms/scripts/tools/preflight/推送.py`（Linux `.sh` / Windows `.bat`；mdm 同款；等价 `engkit push`）。
- 干什么：按**待推提交**自动选档 → 跑预检 → 通过才 `git push`。全为文档 → 快速档；含代码 / 配置 → 定向档（静态 + 定向用例 + 模块级覆盖率 100%）。只验不推加 `--check`；全量档加 `--full`。
- **必须拿到完整预检结果**：同样完整落盘（含 stderr）后整体阅读，禁止截断 / 过滤；按「失败 N 项」清单一次修完再重跑。
- 前提：工作树必须干净（先提交）。**本地手动跑 `engkit preflight` 会被拒绝**，这是设计（只有推送与 CI 能触发）。
- 细节（档位判据、`[push]` 配置、审计）：《[工程化工具包说明](engkit/engkit文档/概述/工程化工具包说明.md)》§4.3「预检段」。

### 重命令：只跑单文件 / 单节点

- 单文件 / 单节点直跑（秒级）：`ruff check <文件>` / `pyright <文件>` / `pytest <文件>` / `pytest <文件>::<节点>`。
- **不再提供重命令包装**：窄多目录 `pytest`、无参数 `ruff` / `pyright` 会被重命令守卫拦下；跨模块排查走推送预检或 CI。`ENGKIT_ALLOW_UNWRAPPED=1` 仅用于排查守卫误判。
- **全量测试只由 CI 执行**：开发时跑无目标 / 宽目录 / `--pyargs` 的 `pytest` 会被全量测试守卫拒绝；前端 vitest 无过滤全跑一个包同样拒绝。没有 `--full` 或环境变量逃生口；`run-selected --force-full` 仅 CI 可用。
- **不要为挑几行报错整轮重跑**：改看单文件 `ruff check <文件>` / `pyright <文件>` / `pytest <文件>`，秒级。
- 细节（守卫安装、`ruff` 原生二进制的覆盖边界）：《[AI开发规范](bms/bms文档/规范/AI开发规范.md)》「重命令不重跑」节。

### 覆盖率：查缺口只走一个入口

- **唯一入口**：在 `bms` 仓根执行 `backend\.venv\Scripts\python.exe scripts\tools\preflight\coverage_report.py`（Linux 为 `backend/.venv/bin/python`）。它**只读最近一次采集的数据、不重跑用例**，缺口明细落 `.cache/coverage/gaps.txt`；**排障只看该文件，不得用终端过滤后的残缺输出下结论**。
- **模块级（推送环 / CI 口径，行 + 分支 100%）**：`... coverage_report.py --module <点分模块> --module <点分模块>`（`--module` 可重复）。
- **改动行（提交环口径）**：先把改动加入暂存区，再 `git diff --cached --name-only | ... coverage_report.py --changed`；只判本次 diff 触达的可执行行，不要求未改动代码达标。
- **禁止** `pytest --cov` / `coverage run` 手工采集：门禁只认 `.cache/coverage/.coverage`，手工数据会得出与门禁不一致的假缺口，pytest 入口守卫会直接 `exit(2)`、用例零执行。
- **先采集、后查缺口**：数据由提交前预检 / 推送预检 / CI 采集；代码改动后先跑相应入口再查，否则看到的是旧数据。退出码：`0` 达标 / `1` 未达标（含未采集到数据）/ `2` 参数或环境错误。
- 细节（口径分工 / 豁免 / 守卫）：《[AI开发规范](bms/bms文档/规范/AI开发规范.md)》「覆盖率要求」节、《[测试规范](bms/bms文档/规范/测试规范.md)》§6。

### 检索：找东西先用它

- MCP `bizssearch`（DSH / CodeBuddy 为 `mcp__bizssearch__*`，opencode 为 `tools.bizssearch.*`）：
  - `search_with_snippet`：带命中行片段，**最省 token，首选**；
  - `search_content`：只返回路径 / 标题 / 摘要；
  - `index_update`：刚改过文件、怀疑索引旧时先刷（1~2 秒）。
- 选档：不知道去哪找 → 检索服务；已知精确符号 → `rg`；已知在哪 → 限定目录后 `rg`。命中太多先加 `kind` / `path` 收敛，别把 `limit` 拉满。
- 命令行兜底：`python3 bms/scripts/tools/search/search_mcp.py -q 关键词`（在**工作区根**执行）；索引在 `<工作区根>/.cache/search/`，`--update` 增量、`--rebuild` 重建。
- **WorkBuddy 专用（其它 agent 跳过本条）**：WorkBuddy 把 MCP 工具放进延迟加载池，调用前要先检索工具定义、多一次往返，与其绕一圈不如直调命令行 —— `python3 bms/scripts/tools/search/search_mcp.py -q 关键词`（同一索引、同一排序、同一摘要；`--snippet` 带命中片段、`--update` 刷索引）。工具直接可见的 agent（opencode / CodeBuddy / Claude Code 等）仍按上方 MCP 用法，不必绕命令行。
- **禁用** `--no-ignore` / `-uu`（会扫进依赖与产物）。
- 细节（安装、`.ignore` 与 `.gitignore` 分工、各 agent 的 MCP 配置、索引维护与实测）：《[内容检索工具部署使用说明](bms/bms文档/资料/工具/内容检索工具部署使用说明.md)》。

### 文档校验

- `engkit links`：相对链接与锚点；改完文档就跑。
- `engkit docs-scope`：进度类字段只允许落在阶段计划。
- `engkit eol`：行尾检查。**仓根缺 `.gitattributes`（或未写 `eol=lf`）时退 2**——护栏失效即失败，不静默报 0 违规；**工作树残留 CRLF 只告警（退 0）**，因为 `.gitattributes` 的 clean 过滤器已保证入库内容恒为 LF，要工作树也干净就跑 `engkit eol --fix`（提交钩子已自愈暂存文件）。
- 细节（三项护栏的判定与配置）：[engkit 文档首页](engkit/engkit文档/文档首页.md)、《[工程化工具包说明](engkit/engkit文档/概述/工程化工具包说明.md)》。

### 依赖维护（依赖外置在仓外，原位置是符号链接）

- `bms/scripts/tools/deps/外置依赖.sh`（`.bat`）：平时保持外置态。
- `bms/scripts/tools/deps/还原依赖.sh`（`.bat`）：**`pnpm install` / `uv sync` 前必须先做**（安装器见到符号链接会误判跳过）。
- `bms/scripts/tools/deps/重装依赖.sh`（`.bat`）：还原 → 安装 → 再外置（`--frontend-only` / `--backend-only`）。
- 位置：`DEPS_DIR` 环境变量 > `bms/deploy/.env` > `$HOME/dev-deps/bms`。
- 细节（依赖仓布局、pnpm 单一 workspace、严格依赖树、跨仓路径依赖与镜像口径）：《[开发机部署使用说明总览](bms/bms文档/资料/开发机/windows/开发机部署使用说明总览.md)》、《[pnpm 部署使用说明](bms/bms文档/资料/开发机/windows/pnpm部署使用说明.md)》、《[uv 部署使用说明](bms/bms文档/资料/开发机/windows/uv部署使用说明.md)》。

### 工作区卫生

- `python scripts/tools/workspace/check_workspace_hygiene.py`：临时 / 日志落点自查（违规退出码 1）；`--clean` 隔离到 `tmp/_quarantine/<时间戳>/`。
- 细节（白名单落点、已跟踪文件豁免、依赖目录剪枝、工具产物默认落点）：[scripts/README](scripts/README.md)「工作区卫生」节。

### 浏览器真机验证

- Playwright MCP（`mcp__playwright__*`）：导航 / 点击 / 填表 / 截图 / 读控制台。
- 页面结构用 `browser_snapshot` / `browser_find`（a11y 树带 `[ref=eNN]`），**不要依赖** `.playwright-mcp/*.yml`。
- 截图落 `tmp/`；控制台只认预期错误（favicon 404 / 模块宿主未起 `remoteEntry` 拒连 / 未登录 401）。
- 细节（登记、与 `playwright-cli` 的取舍、长会话口径）：《[CodeBuddy部署使用说明](bms/bms文档/资料/开发机/linux/CodeBuddy部署使用说明.md)》「浏览器真机验证」节。

### 服务器电源控制

- `bms/scripts/tools/wol/`：`唤醒mjbk.sh` / `睡眠mjbk.sh` / `关机mjbk.sh`（Python 实现在同目录）。
- **关机是破坏性操作，执行前必须问用户**；凭据从 `bms/deploy/.env` 读。
- 细节（每日自动睡醒、S3 口径、凭据键位）：《[开发服务器电源控制使用说明](bms/bms文档/资料/开发服务器/linux/开发服务器电源控制使用说明.md)》。

### CI

- 推送**不触发**流水线；要跑全量 / 集成时手工触发：`python3 bms/scripts/tools/ci/trigger.py`（`--project mdm|engkit`、`--ref <分支>`、`--watch` 盯终态）。
- 手工触发即全量；推送后默认**不盯** CI。
- 细节（`workflow.rules` 口径、tag 发布语义、job 分区）：《[开发部署规划](bms/bms文档/规划/开发部署规划.md)》「开发工作流与 CI」节。

## 红线

- **凭据与本地资源不入库**：`bms文档/用户文档/本地资源.md`、各仓 `deploy/.env` 已 gitignore——勿恢复跟踪、勿提交、勿写入其他文档或回答；公开文档（README 等）不得出现服务器 / 内网 IP / 端口 / 账号。
- **临时产物落点**：日志 / 截图 / 草稿一律 `tmp/`，工程缓存落各仓 `.cache/`，不得落在仓库根或源码目录。
- **提交与推送分离**：每仓独立提交，只暂存本次相关文件；说「提交」只 commit、说「推送」才 push（直推 main，不走 MR）；提交信息 `type(scope): 中文描述`。
- **不手改生成物**：`.reasonix/`、opencode 插件产物等。
- **网络走国内镜像**：PyPI 阿里云 / 清华、npm npmmirror、Docker 加速器；GitHub 用 `ghfast.top` 前缀。
- 细节：本地资源与凭据口径见《[开发服务器部署使用说明总览](bms/bms文档/资料/开发服务器/linux/开发服务器部署使用说明总览.md)》；公开文档写法见《[文档生成规范](bms/bms文档/规范/文档生成规范.md)》。

