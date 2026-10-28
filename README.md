# when-to-clear

**See how much of your Claude Code usage goes to re-reading long conversations, and start fresh without losing your place.**

[中文说明](README.zh-CN.md) · MIT · Python 3.9+, no dependencies · reads local files only

![when-to-clear report: 83% of the work happened in conversations over 200k tokens; restarting at 200k would have saved about 53%](docs/demo.svg)

Every reply re-sends the whole conversation so far. Caching makes that cheaper, not free. At 50k tokens it doesn't matter. At 400k, every "ok, go on" re-reads 400k tokens before the model writes a word.

I ran it on my own machine on October 28, 2026. Last 7 days, 83 sessions, 9,863 replies:

- **83% of the work happened while a conversation was over 200k tokens.**
- **Starting fresh at 200k with a short handoff note would have saved about half (53%)**, after paying for the note and for the files the agent would read again.
- 109 times a long session had to be re-sent from scratch, usually because I came back after its cache had expired.
- A brand-new session already holds about 70k tokens before I type anything: system prompt, tools, MCP servers, CLAUDE.md, memory.

Over 30 days the numbers were 91% and 62%.

## Three parts

**1. The report.** Run it and see your own numbers:

```sh
python3 when_to_clear.py
```

```text
when-to-clear · last 7 days · 83 sessions · 9,863 replies
Tokens re-read as context: 2.9B
  83% of the work happened while a conversation was over 200k tokens.
  Starting fresh at 200k with a short handoff note would have saved about 53% (112 restarts).
  Long sessions were re-sent from scratch 109 times, usually after their cache expired (11% of the work).
  A new session starts at about 70k tokens before your first message (system prompt, tools, MCP servers, CLAUDE.md, memory).
Heaviest sessions:
  ...
```

Options: `--days 30`, `--at 150k` to try a different restart size, `--dir` for another transcripts folder, `--json` for raw numbers.

**2. The reminder.** A Stop hook. When a conversation passes 200k tokens, you get a short note:

```text
when-to-clear: this conversation is at 348k tokens, and every reply re-reads all of it.
At your next stopping point, ask Claude to write a handoff note, then /clear and paste it.
```

It reminds you again at 300k, 400k and so on, never twice for the same step, and it never blocks anything.

**3. The handoff skill.** Say "write a handoff." The agent writes `HANDOFF.md`: done (with proof), in progress, not done, next step, blocked on, branch, uncommitted changes, and a few lines of context the code can't tell you. Then:

```text
/clear
Read HANDOFF.md and continue from Next step.
```

I use the same seven sections every time one of my sessions gets long, and the next session starts from them instead of from scratch.

## Install

**Claude Code**, as a plugin (reminder and handoff skill):

```text
/plugin marketplace add Balance0014/when-to-clear
/plugin install when-to-clear@when-to-clear
```

Then start a new session. For the report, clone the repo or download `when_to_clear.py` and run it with Python.

**Without the plugin system:** add the reminder to `~/.claude/settings.json`, with `--at` set to the size you want:

```json
{
  "hooks": {
    "Stop": [{ "hooks": [{ "type": "command", "command": "python3 /path/to/when_to_clear.py hook --at 200k" }] }]
  }
}
```

**Other agents:** `npx skills add Balance0014/when-to-clear` installs the handoff skill.

## How the numbers work

The report reads the token counts Claude Code already saves with every reply in `~/.claude/projects`. "Work" is weighted the way the API prices tokens, relative to a fresh input token: cache reads 0.1×, cache writes 1.25×, output 5×. Anthropic doesn't publish how plan limits weigh each kind, so read the percentages as shares of the work, not as exact plan usage.

The saving is a replay of your own history: whenever a conversation would have passed the size you set, it restarts with 30k tokens (a ~5k note plus ~25k of files read again) and charges the cost of writing the note. Your real saving depends on how much the agent has to re-read after a restart. If it needs more, set `--at` higher.

Nothing is sent anywhere. Codex logs aren't supported yet.

## Why I built it

I run a one-person company on about 18 Claude Code sessions and 20 scheduled AI jobs ([how that works](https://github.com/Balance0014/one-person-ai-company); this tool comes from chapters [3](https://github.com/Balance0014/one-person-ai-company/blob/main/playbook/03-handoff-records.md) and [6](https://github.com/Balance0014/one-person-ai-company/blob/main/playbook/06-quota-budget.md)). They all share one plan. When the week's limit runs out early, the scheduled jobs stop too, and nothing gets delivered until it resets. Last week that cost me four days of reports. This is how I found out where the week was going.

---

Made by [Balance Zhao](https://github.com/Balance0014). [Follow on X](https://x.com/balance0014) for the next one.
