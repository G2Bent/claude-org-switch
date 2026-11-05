---
name: switch
description: 把 Claude Desktop 的 Code 会话和 Code 定时任务整体切到同一账号下的另一个组织（claude-org-switch），常用于某个组织 token 用完时。触发：/switch、/switch <组织>、切组织、切到另一个组织、这个组织没 token 了。不处理 Chat 对话（存在 claude.ai 服务器上，迁不了）。
argument-hint: "[组织名 | alias | uuid 前缀]"
---

# 切换 Claude 组织

脚本：`~/Library/Application Support/claude-org-switch/switch-org.sh`（逻辑在同目录 `switch_org.py`）。

## 步骤

1. **看组织**：运行 `switch-org.sh list`。输出里 `*` 是 CLI 当前登录的组织，每行有会话数、定时任务数，以及已知的名字或 alias。
2. **定目标**：
   - 有参数就用参数，它可以是组织名、`aliases.json` 里的 alias、uuid 或 uuid 前缀。
   - 没参数时，如果只有两个组织，目标就是没带 `*` 的那个。
   - 组织超过两个时，把 list 给用户看，让用户选一个。
3. **看计划**：运行 `switch-org.sh <目标> --dry-run`，用一两句话告诉用户要搬多少条会话、哪些定时任务。
   - 输出「没有要搬的东西」：说明已经在目标组织，告诉用户只需要做第 5 步的登录和 Desktop 切换，然后结束。
   - 退出码 3：Desktop 存储格式变了。把输出给用户看，然后停下，不要自己改文件。
4. **布置切换**：用户输入 `/switch` 就算授权，直接运行 `switch-org.sh <目标>`。launchctl 在 Claude Code 沙箱里跑不了，需要关掉沙箱。如果提示已有切换在等，告诉用户可以用 `switch-org.sh cancel` 取消后重布，并问用户要不要这样做。
5. **告诉用户手动做的三步**（都要本人做）：
   - 在 Claude Desktop 按 ⌘Q。当前对话会断开，大约 20 秒后 Desktop 会自动重开并弹出通知。
   - 在终端运行 `claude /login`，选目标组织。用 CLI 起的后台会话（`claude --bg`、cron 调起的 claude）会落在 CLI 登录的那个组织。
   - 在 Desktop 左下角账号菜单切到目标组织。

## 出问题时

- 日志在脚本目录的 `run.log`。如果 2 小时内没退出 Desktop，脚本会自动放弃，什么都不改。
- 撤销：让用户退出 Desktop，然后按 README「撤销」一节操作。具体是先把 `claude-code-sessions` 改名留底，再解包最新的 `backup-*.tgz`。不要直接解包覆盖，否则已经搬进目标组织的文件会留在那里，两边都有一份。
- 不要用第三方的 `npx claude-transplant`，那是未经审核的第三方包。
