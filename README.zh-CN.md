# when-to-clear

**看清 Claude Code 的额度有多少花在了「重读长对话」上,并且换新会话不丢进度。**

[English](README.md) · MIT · Python 3.9+,不用装任何依赖 · 只读本机文件

![when-to-clear report: 83% of the work happened in conversations over 200k tokens; restarting at 200k would have saved about 53%](docs/demo.svg)

AI 每回一句话,都要把到这为止的整段对话重新发一遍。有缓存会便宜些,但不是免费。对话只有 5 万 token 时无所谓;到了 40 万,你每说一句「好,继续」,模型动笔之前都要先把这 40 万重读一遍。

我在自己电脑上跑了一下,最近 7 天,83 个会话,9,863 次回复:

- **83% 的消耗发生在对话超过 20 万之后。**
- **如果每到 20 万就带一张交接便条换新会话,大约能省一半(53%)**,写便条和 AI 重新读文件的成本已经算进去了。
- 有 109 次,整段长对话不得不从头重新发一遍,多半是因为我隔了一阵才回来,缓存已经过期。
- 一个全新的会话,我还没打字就已经占了约 7 万:系统提示、工具、MCP 服务、CLAUDE.md、记忆。

按 30 天算,分别是 91% 和 62%。

## 三样东西

**1. 报告。** 跑一下,看你自己的数:

```sh
python3 when_to_clear.py
```

可选参数:`--days 30` 看更长时间;`--at 150k` 试试换一个重开的大小;`--dir` 指定别的记录目录;`--json` 输出原始数字。

**2. 提醒。** 一个收工钩子。对话超过 20 万时,给你一条简短提醒:

```text
when-to-clear: this conversation is at 348k tokens, and every reply re-reads all of it.
At your next stopping point, ask Claude to write a handoff note, then /clear and paste it.
```

到 30 万、40 万……各提醒一次,同一档不重复,也从不拦你。

**3. 交接技能。** 跟 AI 说「写个交接」,它会写好 `HANDOFF.md`,分七项:已完成(带证据)、正在做、未完成、下一步、卡在哪、代码分支、没提交的改动,外加几行代码里看不出来的背景。然后:

```text
/clear
Read HANDOFF.md and continue from Next step.
```

我每个会话一长,就用这同样的七项写交接,下一个会话从这里接着干,不用从头来。

## 安装

**Claude Code 插件**(提醒 + 交接技能):

```text
/plugin marketplace add Balance0014/when-to-clear
/plugin install when-to-clear@when-to-clear
```

装完开一个新会话。报告要单独跑:克隆仓库或下载 `when_to_clear.py`,用 Python 运行。

**不用插件:** 在 `~/.claude/settings.json` 里加上提醒,`--at` 改成你想要的大小:

```json
{
  "hooks": {
    "Stop": [{ "hooks": [{ "type": "command", "command": "python3 /path/to/when_to_clear.py hook --at 200k" }] }]
  }
}
```

**其他 agent:** `npx skills add Balance0014/when-to-clear` 安装交接技能。

## 数字怎么算的

报告读的是 Claude Code 每次回复时本来就记在 `~/.claude/projects` 里的用量。「消耗」按 API 的计价比例加权,以一个新输入 token 为 1:读缓存 0.1、写缓存 1.25、输出 5。Anthropic 没有公开套餐额度怎么给这几类算权重,所以这些百分比请当作「工作量占比」来看,不是套餐用量的精确值。

「能省多少」是拿你自己的历史重放出来的:对话一超过你设的大小,就当作在那里重开,新会话从 3 万起步(约 5 千的便条,加约 2.5 万需要重新读的文件),并算上写便条的成本。实际能省多少,取决于重开之后 AI 要重读多少东西;要读得多,就把 `--at` 设大一点。

数据不发往任何地方。Codex 的记录暂不支持。

## 为什么做这个

我一个人开公司,手下大约 18 个 Claude Code 会话和 20 个定时 AI 任务([具体怎么管](https://github.com/Balance0014/one-person-ai-company);这个工具来自其中的[第 3 章](https://github.com/Balance0014/one-person-ai-company/blob/main/playbook/zh-CN/03-handoff-records.md)和[第 6 章](https://github.com/Balance0014/one-person-ai-company/blob/main/playbook/zh-CN/06-quota-budget.md)),全都用同一个套餐。一周的额度提前用完,定时任务也跟着停,要等到重置才有东西送达。上周就因为这个,少了四天的报告。这个工具,就是我用来找出那一周额度到底花在哪了。

---

作者 [Balance Zhao](https://github.com/Balance0014)。[在 X 上关注](https://x.com/balance0014),下一个工具发布时第一时间知道。
