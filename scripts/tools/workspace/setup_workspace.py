#!/usr/bin/env python3
"""工作区一键搭建脚本（Linux / Windows 通用，软链以 Linux 为准）。

按「配置仓 + bms + engkit + 产品仓 + test 测试仓」模型从零搭起工作区：
克隆仓库（已存在则跳过）、建立跨仓软链（各产品仓与 engkit 的 `bms文档`、`bms/test文档`、
`test/bms文档`，以及主数据等产品互引软链如 `bms/mdm文档`、`biz/mdm文档`）、
补齐工作区根 `.ignore`（检索可见性规则，与 `.gitignore` 分工见 ensure_ignore），
最后核对各仓 git 状态与本地待办（`deploy/.env`、opencode / graphify 工具链）。

用法（在配置仓库根运行）::

    scripts/tools/workspace/搭建工作区.sh \
        --bms <bms 远端> \
        --engkit <engkit 远端> \
        --product biz=<biz 远端> \
        --product mdm=<mdm 远端> \
        --link mdm=bms \
        --test <test 远端>

    # 远端与互引软链也可用环境变量（命令行优先）
    WS_BMS_REMOTE=<bms 远端> \
    WS_ENGKIT_REMOTE=<engkit 远端> \
    WS_PRODUCTS="biz=<biz 远端>,mdm=<mdm 远端>" \
    WS_LINKS="mdm=bms" \
    WS_TEST_REMOTE=<test 远端> \
    scripts/tools/workspace/搭建工作区.sh

说明：脚本只做克隆与软链，不写凭据、不安装软件、不改编辑器配置；
默认工作区根为脚本所在配置仓库的根目录（可用 `--dir` 覆盖）；
必填项（bms 远端、engkit 远端）缺失时在交互终端逐项提问，非交互环境直接报错。
`engkit` 为**必选仓**（跨仓工程化工具包：文档链接与口径护栏 / 预检与重命令包装 / 用例登记）。

退出码：0 搭建完成；1 有需人工处理项；2 参数或环境错误。
"""

import argparse
import os
import shutil
import subprocess
import sys

BMS_NAME = "bms"
ENGKIT_NAME = "engkit"
TEST_NAME = "test"
DOC_LINK = "bms文档"
TO_BMS_DOC = os.path.join("..", "bms", "bms文档")
TO_TEST_DOC = os.path.join("..", "test", "test文档")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IGNORE_FILE = ".ignore"

# 工作区根 .ignore 模板：.gitignore 白名单管「能提交什么」，rg 类工具却把它当可见性规则
# 读，会把 bms/ 等四个仓目录读成「都不要」——本文件用 ! 反消除恢复检索可见性（分工与
# 实测见 bms《内容检索工具部署使用说明》「检索范围与工作区忽略文件」节）。
# 改本模板必须同步工作区根 .ignore：ensure_ignore 以「内容 == 模板」判定是否跳过，
# 不一致会按模板覆盖；新增平级仓库（如 cw）时两处一起补一行。
IGNORE_TEMPLATE = """\
# 检索可见性规则（仅 rg 类检索工具读取；优先级高于 .gitignore，两者的分工见
# bms《内容检索工具部署使用说明》「检索范围与工作区忽略文件」节）
#
# 勿删下面五行；新增平级仓库时补一行，并同步 setup_workspace.py 的 IGNORE_TEMPLATE
# （以「内容 == 模板」判跳过，不一致会被覆盖）。
!bms/
!mdm/
!biz/
!engkit/
!test/
"""

# 产品互引软链：{仓名}=文档根名。为产品仓建「<目标>文档 → ../<目标>/<目标>文档」，
# 或为 bms 仓建「<目标>文档 → ../<目标>/<目标>文档」（主数据等产品文档反引）。
# 默认 bizs 组合建「mdm文档」：bms/mdm文档 与 biz/mdm文档 → ../mdm/mdm文档。
DEFAULT_LINKS = [("bms", "mdm"), ("biz", "mdm")]

errors = 0
warnings = 0


def out(msg=""):
    print(msg, flush=True)


def default_root():
    """默认工作区根：脚本所在配置仓库的根目录（非 git 环境时按目录深度上溯）。"""
    result = subprocess.run(
        ["git", "-C", SCRIPT_DIR, "rev-parse", "--show-toplevel"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        return os.path.abspath(result.stdout.strip())
    return os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR)))


def fail(msg):
    out(msg)
    sys.exit(2)


def masked(url):
    """隐藏远端 URL 中的凭据（user:password@）后再展示。"""
    if "://" in url:
        scheme, rest = url.split("://", 1)
        host = rest.split("/", 1)[0]
        if "@" in host:
            return scheme + "://***@" + rest.split("@", 1)[1]
    return url


def ask(prompt):
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def ask_required(prompt):
    while True:
        value = ask(prompt)
        if value:
            return value
        out("  必填，请重新输入（Ctrl+C 退出）。")


def parse_product(value):
    if "=" not in value:
        fail(f"产品仓参数格式应为「名称=远端」，收到：{value}")
    name, url = value.split("=", 1)
    name, url = name.strip(), url.strip()
    if not name or not url:
        fail(f"产品仓参数格式应为「名称=远端」，收到：{value}")
    if name in (BMS_NAME, TEST_NAME) or "/" in name or "\\" in name:
        fail(f"产品仓名称不可用：{name}（保留名 bms/test，且不能含路径分隔符）")
    return name, url


def parse_link(value):
    """解析产品互引软链参数「仓名=文档根」：在 <仓名>/ 仓根建 <文档根>文档 → ../<文档根>/<文档根>文档。"""
    if "=" not in value:
        fail(f"互引软链参数格式应为「仓名=文档根」，收到：{value}")
    holder, target = value.split("=", 1)
    holder, target = holder.strip(), target.strip()
    if not holder or not target:
        fail(f"互引软链参数格式应为「仓名=文档根」，收到：{value}")
    for name in (holder, target):
        if "/" in name or "\\" in name:
            fail(f"互引软链名称不能含路径分隔符：{name}")
    return holder, target


def git(args, cwd=None, capture=True):
    kwargs = {"cwd": cwd}
    if capture:
        kwargs.update(stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    return subprocess.run(["git"] + args, **kwargs)


def is_git_repo(path):
    result = git(["-C", path, "rev-parse", "--show-toplevel"])
    top = result.stdout.strip() if result.returncode == 0 else ""
    return bool(top) and os.path.abspath(top) == os.path.abspath(path)


def repo_info(path):
    def head(args):
        result = git(["-C", path] + args)
        return result.stdout.strip() if result.returncode == 0 else ""

    branch = head(["rev-parse", "--abbrev-ref", "HEAD"])
    commit = head(["rev-parse", "--short", "HEAD"])
    remote = head(["remote", "get-url", "origin"])
    return branch, commit, remote


def clone(name, url, root):
    global errors
    if os.path.lexists(os.path.join(root, name)):
        out(f"[跳过] {name}/ 已存在，纳入核对")
        return
    out(f"[克隆] {name}/ ← {masked(url)}")
    result = git(["clone", "--", url, name], cwd=root, capture=False)
    if result.returncode != 0:
        errors += 1
        out(f"[失败] {name}/ 克隆失败（git 返回码 {result.returncode}）")


def link_state(link, target):
    if not os.path.lexists(link):
        return "missing", None
    if os.path.islink(link):
        actual = os.readlink(link)
        if os.path.normpath(actual) == os.path.normpath(target):
            return "ok", actual
        return "wrong", actual
    return "conflict", None


def ensure_link(root, rel_link, target):
    global errors
    link = os.path.join(root, rel_link)
    state, actual = link_state(link, target)
    if state == "ok":
        out(f"[跳过] {rel_link} 软链已正确 -> {target}")
    elif state == "missing":
        try:
            os.symlink(target, link)
            out(f"[创建] {rel_link} -> {target}")
        except OSError as exc:
            errors += 1
            out(f"[失败] {rel_link} 软链创建失败：{exc}")
            out("        Windows 需开发者模式或管理员权限；文档工作区以 Linux 为准。")
    elif state == "wrong":
        errors += 1
        out(f"[冲突] {rel_link} 已存在且指向 {actual}（预期 {target}）")
        out(f"        请人工确认后移除 {rel_link}，再重跑本脚本。")
    else:
        errors += 1
        out(f"[冲突] {rel_link} 已存在且不是软链")
        out(f"        请人工确认后移除 {rel_link}，再重跑本脚本。")


def ensure_ignore(root):
    """落盘工作区根 .ignore（检索可见性规则），让 rg 类工具能看见四个仓目录。

    与 .gitignore 分工：`.gitignore` 首行的 `/*` 白名单管「工作区仓能提交什么」，
    而 rg 类工具默认把 .gitignore 当可见性规则读，会把白名单读成「这下面都不要」；
    本文件用 `!bms/` 等反消除恢复可见性（优先级高于 .gitignore）。

    配置仓本身已提交本文件，克隆后天然存在；此处兜底两种情形：
    ① 从旧版配置仓升级而来（新增本机制前克隆的工作区没有 .ignore）；
    ② 手工删除了该文件。内容与模板一致则跳过，不一致则按模板重写。
    """
    global errors
    target = os.path.join(root, IGNORE_FILE)
    if os.path.lexists(target) and not os.path.isfile(target):
        errors += 1
        out(f"[冲突] {IGNORE_FILE} 已存在且不是普通文件，请人工确认后移除再重跑")
        return
    try:
        with open(target, "r", encoding="utf-8") as handle:
            current = handle.read()
    except (OSError, UnicodeDecodeError):
        current = None
    if current is None:
        try:
            with open(target, "w", encoding="utf-8") as handle:
                handle.write(IGNORE_TEMPLATE)
            out(f"[创建] {IGNORE_FILE}（恢复工作区根检索可见性）")
        except OSError as exc:
            errors += 1
            out(f"[失败] {IGNORE_FILE} 写入失败：{exc}")
    elif current == IGNORE_TEMPLATE:
        out(f"[跳过] {IGNORE_FILE} 已符合模板")
    else:
        try:
            with open(target, "w", encoding="utf-8") as handle:
                handle.write(IGNORE_TEMPLATE)
            out(f"[重写] {IGNORE_FILE} 与模板不一致，已按模板覆盖")
        except OSError as exc:
            errors += 1
            out(f"[失败] {IGNORE_FILE} 重写失败：{exc}")


def tool_info(command):
    path = shutil.which(command)
    if not path:
        return None
    try:
        result = subprocess.run(
            [command, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5,
        )
        first = result.stdout.strip().splitlines()
        version = first[0] if first else "版本未知"
    except Exception:
        version = "版本未知"
    return f"{path}（{version}）"


def check_deploy_env(root, name):
    global warnings
    deploy = os.path.join(root, name, "deploy")
    if not os.path.isdir(deploy):
        return
    if os.path.exists(os.path.join(deploy, ".env")):
        out(f"  - {name}/deploy/.env 已存在")
    else:
        warnings += 1
        out(f"  [!] {name}/deploy/.env 未配置：复制 .env.example 并填值（不入库，凭据见本地资源文档）")


def main():
    global errors, warnings

    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass

    if shutil.which("git") is None:
        fail("未找到 git，请先安装 git 再运行本脚本。")

    parser = argparse.ArgumentParser(
        description="工作区一键搭建：克隆仓库 + 建软链 + 核对。"
    )
    parser.add_argument("--bms", metavar="远端", help="bms 平台仓库远端（必填；或用 WS_BMS_REMOTE）")
    parser.add_argument(
        "--engkit",
        metavar="远端",
        help="工程化工具包仓库远端（必填；或用 WS_ENGKIT_REMOTE）",
    )
    parser.add_argument(
        "--product",
        metavar="名称=远端",
        action="append",
        default=[],
        help="产品仓库远端，可重复传入（或用 WS_PRODUCTS，逗号分隔）",
    )
    parser.add_argument("--test", metavar="远端", help="测试资产仓远端（可选；或用 WS_TEST_REMOTE）")
    parser.add_argument(
        "--link",
        metavar="仓名=文档根",
        action="append",
        default=[],
        help="产品互引软链，可重复传入（或用 WS_LINKS，逗号分隔）；如 mdm=bms 表示 bms 仓根建 mdm文档 → ../mdm/mdm文档",
    )
    parser.add_argument("--dir", metavar="目录", help="工作区根目录（默认：脚本所在目录）")
    args = parser.parse_args()

    root = os.path.abspath(args.dir) if args.dir else default_root()
    if not os.path.isdir(root):
        fail(f"工作区根目录不存在：{root}")

    bms_remote = (args.bms or os.environ.get("WS_BMS_REMOTE", "")).strip()
    engkit_remote = (args.engkit or os.environ.get("WS_ENGKIT_REMOTE", "")).strip()
    test_remote = (args.test or os.environ.get("WS_TEST_REMOTE", "")).strip()
    products = [parse_product(value) for value in args.product]
    if not products and os.environ.get("WS_PRODUCTS", "").strip():
        products = [
            parse_product(value)
            for value in os.environ["WS_PRODUCTS"].split(",")
            if value.strip()
        ]

    # 产品互引软链：命令行 --link 优先，其次 WS_LINKS，最后默认组合
    raw_links = args.link
    if not raw_links and os.environ.get("WS_LINKS", "").strip():
        raw_links = [v for v in os.environ["WS_LINKS"].split(",") if v.strip()]
    extra_links = [parse_link(value) for value in raw_links] if raw_links else []

    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    if not bms_remote:
        if not interactive:
            fail("缺少 bms 远端：请用 --bms 或环境变量 WS_BMS_REMOTE 传入。")
        bms_remote = ask_required("bms 平台仓库远端（必填）：")
    if not engkit_remote:
        if not interactive:
            fail("缺少 engkit 远端：请用 --engkit 或环境变量 WS_ENGKIT_REMOTE 传入。")
        engkit_remote = ask_required("工程化工具包仓库远端（必填）：")
    if interactive and not products:
        value = ask("产品仓库（名称=远端，多个用逗号分隔，留空跳过）：")
        if value:
            products = [parse_product(item) for item in value.split(",") if item.strip()]
    if interactive and not test_remote:
        test_remote = ask("测试资产仓远端（可选，留空跳过）：")

    names = [name for name, _ in products]
    if len(set(names)) != len(names):
        fail(f"产品仓名称重复：{names}")

    combo = " + ".join([BMS_NAME, ENGKIT_NAME] + names + ([TEST_NAME] if test_remote else []))
    out("== 工作区一键搭建 ==")
    out(f"工作区根：{root}")
    out(f"仓库组合：{combo}")
    out()

    out("[1/4] 克隆仓库")
    clone(BMS_NAME, bms_remote, root)
    clone(ENGKIT_NAME, engkit_remote, root)
    for name, url in products:
        clone(name, url, root)
    if test_remote:
        clone(TEST_NAME, test_remote, root)
    out()

    out("[2/4] 建立软链")
    if not os.path.isdir(os.path.join(root, BMS_NAME)):
        warnings += 1
        out("[跳过] bms/ 不存在，无法建立软链")
    else:
        for name, _ in products:
            if os.path.isdir(os.path.join(root, name)):
                ensure_link(root, os.path.join(name, DOC_LINK), TO_BMS_DOC)
            else:
                warnings += 1
                out(f"[跳过] {name}/ 不存在，跳过其基座软链")
        # 工程化工具包同样以 `bms文档` 软链引用基座（engkit 文档根为 `engkit文档/`，两者并排）
        if os.path.isdir(os.path.join(root, ENGKIT_NAME)):
            ensure_link(root, os.path.join(ENGKIT_NAME, DOC_LINK), TO_BMS_DOC)
        else:
            warnings += 1
            out(f"[跳过] {ENGKIT_NAME}/ 不存在，跳过其基座软链")
        if test_remote:
            if os.path.isdir(os.path.join(root, TEST_NAME)):
                ensure_link(root, os.path.join(BMS_NAME, "test文档"), TO_TEST_DOC)
                ensure_link(root, os.path.join(TEST_NAME, DOC_LINK), TO_BMS_DOC)
            else:
                warnings += 1
                out("[跳过] test/ 不存在，跳过测试资产软链")
        # 产品互引软链（如 bms/mdm文档、biz/mdm文档 → ../mdm/mdm文档）
        for holder, target in extra_links:
            holder_dir = os.path.join(root, holder)
            target_doc = f"{target}文档"
            if not os.path.isdir(holder_dir):
                warnings += 1
                out(f"[跳过] {holder}/ 不存在，跳过其 {target_doc} 互引软链")
                continue
            if not os.path.isdir(os.path.join(root, target)):
                warnings += 1
                out(f"[跳过] {target}/ 不存在，跳过 {holder}/{target_doc} 互引软链")
                continue
            rel_link = os.path.join(holder, target_doc)
            rel_target = os.path.join("..", target, target_doc)
            ensure_link(root, rel_link, rel_target)
    out()

    out("[3/4] 补齐检索可见性规则")
    ensure_ignore(root)
    out()

    out("[4/4] 核对")
    repos = [BMS_NAME, ENGKIT_NAME] + names + ([TEST_NAME] if test_remote else [])
    for name in repos:
        path = os.path.join(root, name)
        if not os.path.isdir(path):
            warnings += 1
            out(f"  [!] {name}/ 不存在")
        elif not is_git_repo(path):
            warnings += 1
            out(f"  [!] {name}/ 存在但不是 git 仓库")
        else:
            branch, commit, remote = repo_info(path)
            out(
                f"  - {name}/：分支 {branch or '?'}，提交 {commit or '?'}，"
                f"远端 {masked(remote) if remote else '未设置'}"
            )
    for name in [BMS_NAME] + names:
        check_deploy_env(root, name)
    for command in ("opencode", "graphify"):
        info = tool_info(command)
        if info:
            out(f"  - {command} 已检测到：{info}")
        else:
            warnings += 1
            out(f"  [!] {command} 未检测到：安装见 bms《AI开发规范》与《开发机部署使用说明总览》")
    out()

    if errors:
        out(f"未完成：{errors} 项需人工处理（详见上文）；警告 {warnings} 项。")
        return 1
    out(f"完成：仓库 {combo}；警告 {warnings} 项。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
