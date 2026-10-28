# 工作区 README

> 工作区（组合层）：以 **bms 克隆**为基座，与一个或多个**产品仓库克隆**平级并置；AI 工作区（AGENTS、.opencode、.codebuddy）位于工作区根

## 1. 定位与组合

- 本目录是一个**工作区**：以 **bms 克隆**为基座（平台与通用基座权威源），与一个或多个**产品仓库克隆**平级并置。
- 组合示例（本文件在工作区之间保持同一份）：
  - `bizs/` = `bms/`（BMS 平台/基座）+ `biz/`（biz 企业运营管理）+ `mdm/`（mdm 主数据管理）
  - `cws/` = `bms/`（BMS 平台/基座）+ `cw/`（CW 创作系统）
- 工作区本身是一个 **git 仓库**，只跟踪工作区配置；扩展新产品只需在工作区根克隆对应产品仓库（bms 保持平级不动）。

## 2. 目录结构

```text
工作区/
├── README.md              # 本文件
├── AGENTS.md              # AI 协作约定（工作区级通用）
├── LICENSE                # MIT 许可
├── *.code-workspace       # 工作区配置（多根并置：工作区配置 / 基座 / 产品 / 测试）
├── scripts/               # 工作区工具链（tools/ 下按工具分目录）
│   ├── README.md          # 工具链清单与职责边界
│   └── tools/workspace/   # 一键搭建（setup_workspace.py + 搭建工作区.sh/.bat）
├── .opencode/             # AI 工作区配置（插件、模型）
├── .vscode/               # 编辑器配置（settings / tasks / launch）
├── .codebuddy/            # AI 跨会话工作记忆（memory/，本地维护、不入库）
├── .gitignore             # 工作区仓库忽略规则（全忽略 + 配置白名单）
├── .ignore                # 检索可见性规则（反消除 bms/ 等五目录，与 .gitignore 分管两件事）
├── bms/                   # BMS 平台/基座（权威源克隆，独立 git 仓库）
│   ├── bms文档/            # 平台文档（权威）
│   ├── mdm文档 -> ../mdm/mdm文档  # 主数据文档软链（含在 .gitignore，不入库）
│   └── test文档 -> ../test/test文档   # 测试资产软链（含在 .gitignore，不入库）
├── engkit/                # 跨仓工程化工具包（独立 git 仓库，必选）
│   ├── src/engkit/        # 包源码（links / docs-scope / preflight / run_once / kiwi …）
│   ├── engkit文档/         # 工具包文档根（概述 / 接入说明 / 开发约定）
│   └── bms文档 -> ../bms/bms文档  # 基座软链（自动建立，不入库）
├── test/                  # 测试资产（独立 git 仓库，可选克隆）
│   ├── test文档/           # 测试文档
│   ├── scripts/           # 测试侧脚本
│   └── bms文档 -> ../bms/bms文档      # 基座软链（不入库）
├── <产品仓库>/             # 产品仓库克隆（如 biz、mdm、cw，各自独立 git 仓库）
│   ├── bms文档 -> ../bms/bms文档      # 基座软链（自动建立，不入库）
│   └── mdm文档 -> ../mdm/mdm文档      # 产品互引软链（仅 biz 等需引主数据者，不入库）
├── database/              # 本地数据库落点（各仓 database/<仓库>/，已 gitignore，不入库）
└── tmp/                   # 项目临时目录（临时文件 / 截图 / 脚本草稿等，已 gitignore，不入库）
```

## 3. 多仓 git 同步

- **每个仓库独立提交**：bms、各产品仓库、工作区仓库分别 commit / push（提交信息遵循《命名规范》`type(scope): 中文描述`）。
- **改一处、处处更新**：改动任一处 bms 克隆 → 提交推送 → 其他工作区 `git -C bms pull` 更新；产品仓库同理；没有文档同步脚本。
- **基座引用**：产品仓库文档根按项目命名（如 `biz文档/`、`cw文档/`）；各产品仓库根以软链 `bms文档 → ../bms/bms文档` 与产品文档根并排，产品文档引用基座统一用 `../bms文档/…`；通过该软链编辑基座文件时，实际修改的是 bms 克隆，须回 bms 仓库提交。
- **测试资产仓 `test/`（可选）**：承载模板 / 数据 / 压测场景 / 用例维护脚本，与 bms、产品仓平级并置，文档根 `test文档/`。
  双向软链**均不入 git**：`bms/test文档 → ../test/test文档`（bms 仓根，与 `bms文档/` 同级）、`test/bms文档 → ../bms/bms文档`（test 仓根）。
  **bms 文档正文不写真链接指向测试文档**（CI 只 clone bms 会判断链），仅写纯文本路径。被流水线调用的脚本仍留 `bms/scripts/tools/`。

## 4. AI 工作区

- `AGENTS.md`：工作区级 AI 协作约定（唯一一份，含 bms 工具链、后台任务执行、镜像、讨论确认与提交流程；产品仓库不单设）。
- `.opencode/`：AI 工作区配置（插件、模型）。
- `.codebuddy/memory/`：AI 跨会话工作记忆（按日期的日报 + 长期记忆 `MEMORY.md`），随会话自行维护、不入库。
- 开发工具链（bg 后台执行器、wol 电源控制、defect 缺陷工具、base-check 基座自检与 check-links 链接自洽校验等）在 `bms/scripts/tools/`。

## 5. 从零搭建工作区

> 以当前 bizs（`bms` + `engkit` + `biz` + `mdm` + `test`）为例；其他组合（如 cws = `bms` + `engkit` + `cw`）把产品仓参数换成对应仓库即可。`engkit`（跨仓工程化工具包）为**必选仓**。

前置条件：Linux（软链以 Linux 为准）、`git`、Python 3。opencode 等 AI 工具链按需另装，脚本只检测并提示。

1. 克隆本配置仓库（远端地址以 GitLab 导航或本地凭据文档为准）：

   ```bash
   git clone <工作区配置仓远端> bizs
   cd bizs
   ```

2. 一键搭建（克隆 bms / engkit 与产品 / 测试仓、建跨仓软链、核对）：

  ```bash
  scripts/tools/workspace/搭建工作区.sh \
    --bms <bms 远端> \
    --engkit <engkit 远端> \   # 跨仓工程化工具包（必选）
    --product biz=<biz 远端> \
    --product mdm=<mdm 远端> \
    --link mdm=bms \      # bms 仓根建「mdm文档 → ../mdm/mdm文档」软链
    --link mdm=biz \      # biz 仓根建「mdm文档 → ../mdm/mdm文档」软链（主数据互引）
    --test <test 远端>
  ```

  - 远端也可用环境变量传入（命令行优先）：`WS_BMS_REMOTE`、`WS_ENGKIT_REMOTE`、`WS_PRODUCTS`（如 `biz=<url>,mdm=<url>`）、`WS_TEST_REMOTE`。
   - 主数据互引软链也可用环境变量：`WS_LINKS`（如 `mdm=bms,mdm=biz` 表示在 bms / biz 仓根各建 `mdm文档 → ../mdm/mdm文档`）。
   - 默认工作区根为配置仓库根（可用 `--dir` 覆盖）；必填项缺失时，交互终端逐项提问；非交互环境（CI / 管道）直接报错。
   - 已存在的目录跳过克隆并纳入核对；软链已正确则跳过，冲突报错并提示人工处理（不静默覆盖）。
   - Windows 入口为 `scripts\tools\workspace\搭建工作区.bat`；软链需开发者模式或管理员权限，文档工作区仍以 Linux 为准。

3. 手动等价命令（脚本不便使用时兜底）：

   ```bash
   git clone <bms 远端> bms
   git clone <engkit 远端> engkit
   git clone <biz 远端> biz
   git clone <mdm 远端> mdm
   git clone <test 远端> test
   ln -sfn ../bms/bms文档 engkit/bms文档
   ln -sfn ../bms/bms文档 biz/bms文档
   ln -sfn ../bms/bms文档 mdm/bms文档
   ln -sfn ../mdm/mdm文档 biz/mdm文档   # biz 引用 mdm 主数据
   ln -sfn ../mdm/mdm文档 bms/mdm文档   # bms 引用 mdm 主数据
   ln -sfn ../test/test文档 bms/test文档
   ln -sfn ../bms/bms文档 test/bms文档
   ```

   > `engkit` 与 bms / 各产品仓必须**平级并置**：bms 侧包装入口按「`import engkit` → `ENGKIT_HOME` → 同级 `../engkit`」定位，缺失即报安装指引。

4. 后续（可选）：
   - 凭据：各仓库 `deploy/.env` 复制自 `deploy/.env.example` 并填值（已 gitignore，凭据见 bms《本地资源》，不入库）。
   - AI 工作区：opencode 安装见 bms《AI开发规范》与《开发机部署使用说明总览》。
   - 测试资产落点与边界见 bms《测试规范》「测试资产落点与组织」节。

## 6. 扩展新产品 / 新工作区

1. **新建工作区**：克隆工作区配置仓库后，按「从零搭建工作区」节用一键脚本或手动命令搭建。
2. **加产品**：在工作区根克隆对应产品仓库，产品仓库根建软链 `bms文档 → ../bms/bms文档` 并排引用基座（机制详见 bms《平台可扩展性规划》4.3）。
3. **加测试资产（按需）**：在工作区根克隆测试仓 `test`，建双向软链（`bms/test文档`、`test/bms文档`），并在 `*.code-workspace` 的 folders 加入 `test`。

## 7. 注意

- **公开文档红线**：不写本地资源信息（服务器/开发机名称、内网 IP、端口、账号等），细节只放已 gitignore 的凭据文档。
- **忽略文件分工**：`.gitignore`（白名单）与 `.ignore`（检索可见性）分管「能提交什么」与「能检索到什么」，新增平级仓库时两者都要补——详见 bms《[内容检索工具部署使用说明](bms/bms文档/资料/工具/内容检索工具部署使用说明.md#scope)》「检索范围与工作区忽略文件」节。
- **临时文件**：统一放工作区根 `tmp/`（临时文件 / 截图 / 脚本草稿等）——已写入工作区 `.gitignore`，不入库、不上传 git。**禁止落在各仓根 / 源码目录**（即使已 gitignore 也算污染工作区）；自查与清理用 `python scripts/tools/workspace/check_workspace_hygiene.py`（`--clean` 隔离），该检查已接入 bms 预检第一步，违规即预检失败——口径见 [`AGENTS.md`](AGENTS.md)「工作区卫生」节。
- **本地库与 AI 记忆**：`database/`（本地数据库落点）与 `.codebuddy/`（AI 工作记忆）均为本地产物，已 gitignore、不入库。
- 产品仓库根的 `bms文档` 基座软链接在 GitLab/GitHub 网页端与 Windows 克隆下不可用，文档工作区以 Linux 为准。
- 平台机制、扩展接入与标识符登记以 `bms/bms文档/` 为权威；协作规则先读 `AGENTS.md`。

> 许可证：MIT（见 [`LICENSE`](LICENSE)），与 `bms/` / `biz/` 仓库保持一致。
>
> 依《文档生成规范》编写 · 工作区配置仓库
