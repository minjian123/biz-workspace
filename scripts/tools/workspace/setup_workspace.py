#!/usr/bin/env python3
"""工作区一键搭建脚本（Linux / Windows 通用，软链以 Linux 为准）。

按「配置仓 + bms + 产品仓 + test 测试仓」模型从零搭起工作区：
克隆仓库（已存在则跳过）、建立三处跨仓软链（`<产品>/bms文档`、
`bms/test文档`、`test/bms文档`）、最后核对各仓 git 状态与本地待办
（`deploy/.env`、opencode / graphify 工具链）。

用法（在配置仓库根运行）::

    scripts/tools/workspace/搭建工作区.sh \
        --bms <bms 远端> \
        --product biz=<biz 远端> \
        --test <test 远端>

    # 远端也可用环境变量（命令行优先）
    WS_BMS_REMOTE=<bms 远端> \
    WS_PRODUCTS="biz=<biz 远端>,cw=<cw 远端>" \
    WS_TEST_REMOTE=<test 远端> \
    scripts/tools/workspace/搭建工作区.sh

说明：脚本只做克隆与软链，不写凭据、不安装软件、不改编辑器配置；
默认工作区根为脚本所在配置仓库的根目录（可用 `--dir` 覆盖）；
必填项（bms 远端）缺失时在交互终端逐项提问，非交互环境直接报错。

退出码：0 搭建完成；1 有需人工处理项；2 参数或环境错误。
"""

import argparse
import os
import shutil
import subprocess
import sys

BMS_NAME = "bms"
TEST_NAME = "test"
DOC_LINK = "bms文档"
TO_BMS_DOC = os.path.join("..", "bms", "bms文档")
TO_TEST_DOC = os.path.join("..", "test", "test文档")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

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
        "--product",
        metavar="名称=远端",
        action="append",
        default=[],
        help="产品仓库远端，可重复传入（或用 WS_PRODUCTS，逗号分隔）",
    )
    parser.add_argument("--test", metavar="远端", help="测试资产仓远端（可选；或用 WS_TEST_REMOTE）")
    parser.add_argument("--dir", metavar="目录", help="工作区根目录（默认：脚本所在目录）")
    args = parser.parse_args()

    root = os.path.abspath(args.dir) if args.dir else default_root()
    if not os.path.isdir(root):
        fail(f"工作区根目录不存在：{root}")

    bms_remote = (args.bms or os.environ.get("WS_BMS_REMOTE", "")).strip()
    test_remote = (args.test or os.environ.get("WS_TEST_REMOTE", "")).strip()
    products = [parse_product(value) for value in args.product]
    if not products and os.environ.get("WS_PRODUCTS", "").strip():
        products = [
            parse_product(value)
            for value in os.environ["WS_PRODUCTS"].split(",")
            if value.strip()
        ]

    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    if not bms_remote:
        if not interactive:
            fail("缺少 bms 远端：请用 --bms 或环境变量 WS_BMS_REMOTE 传入。")
        bms_remote = ask_required("bms 平台仓库远端（必填）：")
    if interactive and not products:
        value = ask("产品仓库（名称=远端，多个用逗号分隔，留空跳过）：")
        if value:
            products = [parse_product(item) for item in value.split(",") if item.strip()]
    if interactive and not test_remote:
        test_remote = ask("测试资产仓远端（可选，留空跳过）：")

    names = [name for name, _ in products]
    if len(set(names)) != len(names):
        fail(f"产品仓名称重复：{names}")

    combo = " + ".join([BMS_NAME] + names + ([TEST_NAME] if test_remote else []))
    out("== 工作区一键搭建 ==")
    out(f"工作区根：{root}")
    out(f"仓库组合：{combo}")
    out()

    out("[1/3] 克隆仓库")
    clone(BMS_NAME, bms_remote, root)
    for name, url in products:
        clone(name, url, root)
    if test_remote:
        clone(TEST_NAME, test_remote, root)
    out()

    out("[2/3] 建立软链")
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
        if test_remote:
            if os.path.isdir(os.path.join(root, TEST_NAME)):
                ensure_link(root, os.path.join(BMS_NAME, "test文档"), TO_TEST_DOC)
                ensure_link(root, os.path.join(TEST_NAME, DOC_LINK), TO_BMS_DOC)
            else:
                warnings += 1
                out("[跳过] test/ 不存在，跳过测试资产软链")
    out()

    out("[3/3] 核对")
    repos = [BMS_NAME] + names + ([TEST_NAME] if test_remote else [])
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
