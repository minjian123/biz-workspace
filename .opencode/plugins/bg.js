// bg.js - opencode 后台任务插件（OpenCode V2 插件 API）
// 提供四个工具：
//   bg_run            后台执行任意命令（立即返回任务 ID，日志落盘）
//   bg_status         秒级查询任务状态（运行中/已完成 + 输出尾部）
//   gl_watch_pipeline  GitLab 流水线盯守（内部走 bg 链路，到终态返回结果）
//   bg_stop           停止后台任务
//
// 原理：命令经 python 后台运行，立即返回；状态查询读状态文件与进程存活，
// 彻底避免"命令卡住傻等"。适合下载、构建、ssh 远程、安装等长耗时操作。
//
// V2 说明：插件改为 default 导出一个带 id 与 setup 的定义；工具经 setup 里的
// ctx.tool.transform 注册，参数用 JSON Schema，执行返回 { content }。
// 插件位于 .opencode/plugins/ 会被自动发现，无需在 opencode.json 登记。
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const execFileP = promisify(execFile);
const __dirname = dirname(fileURLToPath(import.meta.url));

function script(name) {
  // python 脚本在 bms/scripts/tools/bg/（插件文件位于工作区根 .opencode/plugins/，bms 为基座仓）
  return join(__dirname, "..", "..", "bms", "scripts", "tools", "bg", name);
}

function gitlabScript(name) {
  // GitLab 流水线盯守脚本在 bms/scripts/tools/gitlab/
  return join(__dirname, "..", "..", "bms", "scripts", "tools", "gitlab", name);
}

async function runPy(name, args) {
  const { stdout } = await execFileP("python", ["-u", script(name), ...args], {
    timeout: 30000,
    maxBuffer: 4 * 1024 * 1024,
    windowsHide: true,
  });
  return stdout.trim();
}

function fail(title, message) {
  return { content: JSON.stringify({ ok: false, error: message }, null, 2) };
}

const BG_RUN_INPUT = {
  type: "object",
  properties: {
    name: { type: "string", description: "任务名（唯一标识，查询/停止时使用）" },
    command: {
      type: "string",
      description: "要执行的命令（如 pnpm install、ssh user@host df -h、git pull）",
    },
    workdir: { type: "string", description: "工作目录（默认当前项目根）" },
    timeout: { type: "number", description: "命令超时秒数（0=不限，默认 0）" },
  },
  required: ["name", "command"],
  additionalProperties: false,
};

const GL_WATCH_INPUT = {
  type: "object",
  properties: {
    pipeline_id: { type: "number", description: "流水线 ID" },
    project: { type: "number", description: "项目 ID（默认 2 = bms/bms）" },
    timeout: { type: "number", description: "盯守上限秒数（默认 600）" },
    interval: { type: "number", description: "轮询间隔秒数（默认 15）" },
    name: { type: "string", description: "bg 任务名（默认自动生成）" },
  },
  required: ["pipeline_id"],
  additionalProperties: false,
};

async function bgRun(args) {
  try {
    if (!args.name || !args.command) return fail("bg_run", "name 与 command 必填");
    const psArgs = ["--name", args.name, "--command", args.command];
    if (args.workdir) psArgs.push("--workdir", args.workdir);
    if (args.timeout) psArgs.push("--timeout", String(args.timeout));
    return { content: await runPy("bg-run.py", psArgs) };
  } catch (e) {
    return fail("bg_run", String((e && e.message) || e));
  }
}

async function bgStatus(args) {
  try {
    if (!args.name) return fail("bg_status", "name 必填");
    return { content: await runPy("bg-status.py", ["--name", args.name]) };
  } catch (e) {
    return fail("bg_status", String((e && e.message) || e));
  }
}

async function glWatchPipeline(args) {
  if (!args.pipeline_id) return fail("gl_watch_pipeline", "pipeline_id 必填");
  const taskName = args.name || `glpipe_${args.pipeline_id}_${Date.now()}`;
  const waitSec = (args.timeout ?? 600) + 30;
  try {
    // 1) 经 bg_run 后台启动盯守脚本
    const cmdParts = [`python -u "${gitlabScript("watch_pipeline.py")}" --pipeline-id ${args.pipeline_id}`];
    if (args.project) cmdParts.push("--project", String(args.project));
    if (args.timeout) cmdParts.push("--timeout", String(args.timeout));
    if (args.interval) cmdParts.push("--interval", String(args.interval));
    await runPy("bg-run.py", ["--name", taskName, "--command", cmdParts.join(" "), "--timeout", String(waitSec)]);
    // 2) 经 bg-wait.py 阻塞到终态（+30s 余量防误杀），非零退出码时取 stdout
    let out;
    try {
      const r = await execFileP(
        "python",
        ["-u", script("bg-wait.py"), "--name", taskName, "--timeout", String(waitSec), "--tail", "20"],
        { timeout: waitSec * 1000 + 15000, maxBuffer: 4 * 1024 * 1024, windowsHide: true },
      );
      out = r.stdout.trim();
    } catch (e) {
      out = [e.stdout?.trim(), e.stderr?.trim()].filter(Boolean).join("\n") || String((e && e.message) || e);
    }
    return { content: `任务名 ${taskName}\n${out}` };
  } catch (e) {
    return fail("gl_watch_pipeline", String((e && e.message) || e));
  }
}

async function bgStop(args) {
  try {
    if (!args.name) return fail("bg_stop", "name 必填");
    return { content: await runPy("bg-stop.py", ["--name", args.name]) };
  } catch (e) {
    return fail("bg_stop", String((e && e.message) || e));
  }
}

export default {
  id: "bg",
  async setup(ctx) {
    await ctx.tool.transform((editor) => {
      editor.add({
        name: "bg_run",
        description:
          "后台执行任意命令：立即返回任务 ID，不等待命令结束（适合下载/构建/ssh/安装等长操作）。" +
          "之后用 bg_status 秒级查询结果。状态文件默认 %USERPROFILE%\\.bg。",
        input: BG_RUN_INPUT,
        execute: bgRun,
      });

      editor.add({
        name: "bg_status",
        description: "秒级查询后台任务状态：运行中（运行秒数 + 输出尾部）或已完成（输出尾部 + stderr）。",
        input: {
          type: "object",
          properties: { name: { type: "string", description: "任务名（bg_run 时指定的 name）" } },
          required: ["name"],
          additionalProperties: false,
        },
        execute: bgStatus,
      });

      editor.add({
        name: "gl_watch_pipeline",
        description:
          "GitLab 流水线盯守：内部经 bg 链路后台运行 watch_pipeline.py 并等待到终态，" +
          "返回 success/failed/canceled 与流水线链接。凭据自动读 deploy/.env 的 GITLAB_API_*。",
        input: GL_WATCH_INPUT,
        execute: glWatchPipeline,
      });

      editor.add({
        name: "bg_stop",
        description: "停止后台任务（按名称查状态文件后杀进程）。",
        input: {
          type: "object",
          properties: { name: { type: "string", description: "任务名（bg_run 时指定的 name）" } },
          required: ["name"],
          additionalProperties: false,
        },
        execute: bgStop,
      });
    });
  },
};
