# 工作区 README

> 工作区（组合层）：以 **bms 克隆**为基座，与一个或多个**产品仓库克隆**平级并置；AI 工作区（AGENTS、.opencode）位于工作区根

## 1. 定位与组合

- 本目录是一个**工作区**：以 **bms 克隆**为基座（平台与通用基座权威源），与一个或多个**产品仓库克隆**平级并置。
- 组合示例（本文件在工作区之间保持同一份）：
  - `bizs/` = `bms/`（BMS 平台/基座）+ `biz/`（biz 企业运营管理）
  - `cws/` = `bms/`（BMS 平台/基座）+ `cw/`（CW 创作系统）
- 工作区本身是一个 **git 仓库**，只跟踪工作区配置；扩展新产品只需在工作区根克隆对应产品仓库（bms 保持平级不动）。

## 2. 目录结构

```text
工作区/
├── README.md            # 本文件
├── AGENTS.md            # AI 协作约定（工作区级通用）
├── scripts/             # 工作区工具链（tools/ 下按工具分目录）
│   └── tools/workspace/ # 一键搭建（setup_workspace.py + 搭建工作区.sh/.bat）
├── .opencode/           # AI 工作区配置（插件、模型、MCP 登记）
├── .gitignore           # 工作区仓库忽略规则（bms/产品目录等）
├── bms/                 # BMS 平台/基座（权威源克隆，独立 git 仓库）
│   ├── bms文档/          # 平台文档（权威）
│   └── test文档 -> ../test/test文档   # 测试资产软链（含在 .gitignore，不入库）
├── test/                # 测试资产（独立 git 仓库，可选克隆）
│   ├── test文档/         # 测试文档
│   ├── scripts/         # 测试侧脚本
│   └── bms文档 -> ../bms/bms文档      # 基座软链（不入库）
├── <产品仓库>/           # 产品仓库克隆（如 biz、cw，各自独立 git 仓库）
└── tmp/                 # 项目临时目录（临时文件 / 截图 / 脚本草稿等，已 gitignore，不入库）
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
- 开发工具链（bg 后台执行器、wol 电源控制、defect 缺陷工具、base-check 基座自检与 check-links 链接自洽校验等）在 `bms/scripts/tools/`。

## 5. 从零搭建工作区

> 以当前 bizs（`bms` + `biz` + `test`）为例；其他组合（如 cws = `bms` + `cw`）把产品仓参数换成对应仓库即可。

前置条件：Linux（软链以 Linux 为准）、`git`、Python 3。opencode 等 AI 工具链按需另装，脚本只检测并提示。

1. 克隆本配置仓库（远端地址以 GitLab 导航或本地凭据文档为准）：

   ```bash
   git clone <工作区配置仓远端> bizs
   cd bizs
   ```

2. 一键搭建（克隆 bms 与产品 / 测试仓、建三处软链、核对）：

   ```bash
   scripts/tools/workspace/搭建工作区.sh \
     --bms <bms 远端> \
     --product biz=<biz 远端> \
     --test <test 远端>
   ```

   - 远端也可用环境变量传入（命令行优先）：`WS_BMS_REMOTE`、`WS_PRODUCTS`（如 `biz=<url>,cw=<url>`）、`WS_TEST_REMOTE`。
   - 默认工作区根为配置仓库根（可用 `--dir` 覆盖）；必填项缺失时，交互终端逐项提问；非交互环境（CI / 管道）直接报错。
   - 已存在的目录跳过克隆并纳入核对；软链已正确则跳过，冲突报错并提示人工处理（不静默覆盖）。
   - Windows 入口为 `scripts\tools\workspace\搭建工作区.bat`；软链需开发者模式或管理员权限，文档工作区仍以 Linux 为准。

3. 手动等价命令（脚本不便使用时兜底）：

   ```bash
   git clone <bms 远端> bms
   git clone <biz 远端> biz
   git clone <test 远端> test
   ln -sfn ../bms/bms文档 biz/bms文档
   ln -sfn ../test/test文档 bms/test文档
   ln -sfn ../bms/bms文档 test/bms文档
   ```

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
- **临时文件**：统一放工作区根 `tmp/`（临时文件 / 截图 / 脚本草稿等）——已写入工作区 `.gitignore`，不入库、不上传 git。
- 产品仓库根的 `bms文档` 基座软链接在 GitLab/GitHub 网页端与 Windows 克隆下不可用，文档工作区以 Linux 为准。
- 平台机制、扩展接入与标识符登记以 `bms/bms文档/` 为权威；协作规则先读 `AGENTS.md`。

> 许可证：MIT（见 [`LICENSE`](LICENSE)），与 `bms/` / `biz/` 仓库保持一致。
>
> 依《文档生成规范》编写 · 工作区配置仓库
