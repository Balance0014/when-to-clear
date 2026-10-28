# when-to-clear

**Find out how much of your Claude Code usage goes to re-reading long conversations, and get told when it's time to /clear.**

[中文说明](README.zh-CN.md) · MIT · Python 3.9+, no dependencies · reads local files only

![when-to-clear report: 82% of the work happened in conversations over 200k tokens; restarting at 200k would have saved about a third](docs/demo.svg)

Every reply re-sends the whole conversation. Caching cuts the price of that to a tenth, but at 400k tokens even "ok, go on" re-reads 400k tokens before the model writes a word.

I ran the report on my own sessions on October 28, 2026. Over the last 7 days (91 transcripts, including subagents, and 9,837 replies):

- **82% of the work happened while a conversation was over 200k tokens.** ("Work" means tokens weighted by API price; details below.)
- Starting fresh at 200k with a short handoff note would have saved about a third (33%), after paying for the note and for the files the agent reads again.
- A long conversation missed the cache and was re-sent in full 109 times. 96 of those came after a break of five minutes or more.
- A new session already holds about 63k tokens by its first reply: system prompt, tools, MCP servers, CLAUDE.md, memory, and your first message.

Over 30 days, 90% of the work was past 200k, and restarting there would have saved 42%.

## Three parts

**1. The report.** Clone the repo (or download `when_to_clear.py`) and run:

```sh
python3 when_to_clear.py
```

```text
when-to-clear · last 7 days · 91 transcripts · 9,837 replies
Tokens re-read as context: 2.9B
  82% of the work happened while a conversation was over 200k tokens.
  Starting fresh at 200k with a short handoff note would have saved about 33% (124 restarts).
  Long conversations were re-sent from scratch 109 times, 96 of them after a break of 5+ minutes (11% of the work).
  A new session holds about 63k tokens by its first reply (system prompt, tools, MCP servers, CLAUDE.md, memory, your first message).
Heaviest sessions:
  ...
```

Options: `--days 30`, `--at 150k` to try a different restart size, `--dir` for another transcripts folder, `--json` for raw numbers.

**2. The reminder.** A Stop hook. When a conversation passes 200k tokens, you get a short note:

```text
when-to-clear: this conversation is at 348k tokens, and every reply re-reads all of it.
At your next stopping point, ask Claude to write a handoff note, then /clear and paste it.
```

With the default 200k, it reminds you again every 100k (300k, 400k and so on), once per level. It never blocks anything.

**3. The handoff skill.** Say "write a handoff." The agent writes `HANDOFF.md`: what's done (with proof), what's in progress, what's not started, the next step, what it's blocked on, the branch, and uncommitted changes, plus a few lines of context the code can't tell you. Then:

```text
/clear
Read HANDOFF.md and continue from Next step.
```

## Install

**Claude Code**, as a plugin (reminder and handoff skill):

```text
/plugin marketplace add Balance0014/when-to-clear
/plugin install when-to-clear@when-to-clear
```

Then start a new session. The report isn't part of the plugin; run it from a clone as shown above.

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

The report reads the token counts Claude Code already saves with every reply in `~/.claude/projects`. "Work" weights each token the way the API prices it, relative to a fresh input token: cache reads 0.1×, cache writes 1.25× (the 5-minute cache price), output 5×. Anthropic doesn't publish how plan limits weigh each kind, so read the percentages as shares of the work, not as exact plan usage.

The saving replays your own history. Whenever a conversation would have passed the size you set, it restarts from that session's own starting size plus 30k (a ~5k note and ~25k of files read again), and it charges for writing the note. It assumes the rest of the session would have gone the same way. If your agent has to re-read much more after a restart, your real saving is smaller; change `HANDOFF` in the script to model that.

Nothing is sent anywhere. Codex logs aren't supported yet.

## Why I built it

I run a one-person company on about 18 Claude Code sessions and 20 scheduled AI jobs ([how that works](https://github.com/Balance0014/one-person-ai-company); this tool comes from chapters [3](https://github.com/Balance0014/one-person-ai-company/blob/main/playbook/03-handoff-records.md) and [6](https://github.com/Balance0014/one-person-ai-company/blob/main/playbook/06-quota-budget.md)). They all share one plan. When the week's limit runs out early, the scheduled jobs stop too, and nothing gets delivered until it resets. Last week that cost me four days of reports. I used this report to find out where the week was going.

---

Made by [Balance Zhao](https://github.com/Balance0014). [Follow on X](https://x.com/balance0014) for the next one.
