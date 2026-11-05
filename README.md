# claude-org-switch

一个 Claude 账号挂了多个组织（organization）时，用一条命令把 Claude Desktop 里的 **Code 会话**和 **Code 定时任务**整体搬到另一个组织。常见场景是某个组织的 token 用完了，要切到另一个组织继续干活，同时保留侧边栏的历史会话和定时任务。

## 适合谁

- 你的 Claude 账号下有 **两个或更多组织**，并且会在它们之间切换。
- 你在 Claude Desktop 的 Code tab 里攒了很多会话，或者建了 Code 定时任务。

只有一个组织的话用不上这个工具。

## 为什么需要它

Claude Desktop 按组织分开存 Code 侧边栏和定时任务：

```
~/Library/Application Support/Claude/claude-code-sessions/<account>/<org>/
  local_*.json              每条会话的侧边栏记录
  archived-sessions.idx     已归档的会话
  scheduled-tasks.json      Code 定时任务
```

切了组织，侧边栏就是空的，定时任务也不在了。会话正文（`~/.claude/projects/`）和定时任务的 prompt（`~/.claude/scheduled-tasks/`）是所有组织共用的，所以只要把上面这几个文件搬过去，会话和定时任务就都回来了。

## 能搬什么、不能搬什么

| 内容 | 能搬吗 |
|---|---|
| Code tab 侧边栏的会话（包括已归档的） | 能 |
| Code 定时任务 | 能（搬走后，原组织里就不再登记，不会跑两遍） |
| Chat 对话 | 不能。Chat 存在 claude.ai 服务器上，按组织隔离 |
| Cowork（local agent mode）会话 | 不处理 |
| CLI 当前登录的组织 | 不能，要自己运行 `claude /login` |

## 安装

需要 macOS 和 `/usr/bin/python3`。没有的话先运行 `xcode-select --install`。

```bash
git clone https://github.com/G2Bent/claude-org-switch.git
```

```bash
cd claude-org-switch && ./install.sh
```

安装脚本会做三件事：

- 把脚本放到 `~/Library/Application Support/claude-org-switch/`
- 把 `/switch` skill 放到 `~/.claude/skills/switch/`
- 列出你的组织

如果你已经有一个别的 `/switch` skill，安装会停下来提示你。确认要替换就运行 `./install.sh --force`。

## 使用

在 Claude Code 里输入：

```
/switch
```

或者指定目标组织：`/switch My Team Org`（组织名）、`/switch 1a2b`（uuid 前缀）。Claude 会先给你看要搬多少条会话、哪些定时任务，然后布置切换。

接下来有 **三步要你自己做**：

1. 在 Claude Desktop 按 **⌘Q** 退出。脚本会等到 Desktop 退出后再动文件（Desktop 开着时会用内存里的状态覆盖文件），搬完大约 20 秒后自动重新打开 Desktop。
2. 在终端运行 `claude /login`，选目标组织。用 CLI 起的后台会话（`claude --bg`、cron / LaunchAgent 调起的 claude）会落在 CLI 登录的那个组织，不切的话它们还会跑到旧组织。
3. 在 Desktop 左下角的账号菜单里切到目标组织。

不用 Claude 也可以直接在终端操作：

```bash
~/Library/Application\ Support/claude-org-switch/switch-org.sh list
```

```bash
~/Library/Application\ Support/claude-org-switch/switch-org.sh <目标> --dry-run
```

```bash
~/Library/Application\ Support/claude-org-switch/switch-org.sh <目标>
```

```bash
~/Library/Application\ Support/claude-org-switch/switch-org.sh cancel
```

### 组织怎么写

`list` 里能看到每个组织的 uuid、会话数和定时任务数。目标组织可以用以下任意一种写法：

- 完整 uuid，或至少 4 位的 uuid 前缀。
- 组织名。CLI 登录过的组织，脚本会自动记住名字。
- `aliases.json` 里的 alias。这个文件在脚本目录，格式是 `{"work": "<uuid>", "backup": "<uuid>"}`。

`list` 里带 `*` 的是 CLI 当前登录的组织。只有两个组织时，直接输入 `/switch` 就会切到另一个。

## 安全措施

- **先校验格式**：动文件前，脚本会检查每条会话记录、归档索引和定时任务的结构。如果和脚本认识的不一致（例如 Desktop 更新改了格式），就直接退出（退出码 3），什么都不改。
- **Desktop 开着时不动**：脚本检测到 Desktop 还在运行，或者判断不了，就不执行。
- **先备份**：每次切换前，会把整个 `claude-code-sessions` 打包成 `backup-<时间>.tgz`，保留最新 5 份。
- **记录**：每次切换会写一份 `manifest-<时间>.json`，记下搬了哪些文件。日志在 `run.log`。
- **只动本地文件**：不联网，不读取凭证。从 `~/.claude.json` 里只读 `oauthAccount.organizationUuid` 和 `organizationName` 两个字段。
- **超时放弃**：布置后 2 小时内没有退出 Desktop，就自动放弃。

## 撤销

退出 Desktop 后运行下面这条命令。它先把当前目录改名留底，再解包最新的备份：

```bash
cd ~/Library/Application\ Support/Claude && mv claude-code-sessions "claude-code-sessions.undo-$(date +%Y%m%d-%H%M%S)" && tar -xzf "$(ls -t ~/Library/Application\ Support/claude-org-switch/backup-*.tgz | head -1)"
```

确认会话都回来以后，可以删掉 `claude-code-sessions.undo-*`。

## 卸载

```bash
~/Library/Application\ Support/claude-org-switch/switch-org.sh cancel; rm -rf ~/Library/Application\ Support/claude-org-switch ~/.claude/skills/switch
```

## 局限

- 依赖 Claude Desktop 的内部存储结构，这部分没有官方文档。App 更新后格式可能变化，到时脚本会拒绝执行（不会写坏数据），需要更新脚本。
- 只在同一个 Claude 账号的组织之间搬。不同账号之间搬不了。
- 不要用第三方的 `npx claude-transplant` 之类的工具代替，它们是未经审核的第三方包。
