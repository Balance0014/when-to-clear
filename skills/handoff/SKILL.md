---
name: handoff
description: Use when the user asks for a handoff note, wants to /clear or start a new session without losing their place, or when the when-to-clear reminder says the conversation is getting long. Writes HANDOFF.md so a fresh session can pick up the work.
---

# handoff

A long conversation costs more with every reply, because every reply re-reads all of it. A fresh session that starts from a good note re-reads a few thousand tokens instead of hundreds of thousands. Your job is to write the note that lets the fresh session pick up where this one stopped.

## When to write it

At a natural stopping point: a change is committed, a question is answered, a test run has finished. Not halfway through an edit.

## What to write

Write `HANDOFF.md` in the project root (or the path the user names), replacing the previous note. Ask the user once whether they want it committed with the work or listed in `.gitignore`. First line:

`Updated: <date and time with time zone>`

Then these seven sections, in this order. Write "none" rather than dropping a section, so the next session knows you checked.

1. **Done.** What is finished, with the proof: commit hashes, test results, URLs that return 200.
2. **In progress.** What you were in the middle of, down to the file and function.
3. **Not done.** What was asked for and not started yet.
4. **Next step.** The single next action, specific enough to start without asking: the command to run or the file to open.
5. **Blocked on.** Anything waiting on the user or someone else, and what exactly is needed.
6. **Branch.** The branch you are on and where it should go.
7. **Uncommitted changes.** Run `git status --short` and list what is not committed or not pushed (leave HANDOFF.md itself out). Offer to commit or stash them before the user clears.

Then add a short **Context** section with only what the next session can't get from the code: decisions the user made and why, approaches you tried that failed, numbers you measured. Leave out anything a quick read of the repo would show.

## Keep it short

Aim for under 60 lines. The next session reads all of it before doing anything, so every line costs something too. Link to files instead of pasting them.

## Then tell the user

Two lines:

> Handoff written to HANDOFF.md. Run /clear, then send: "Read HANDOFF.md and continue from Next step."

## Starting from a handoff

If you start a session and HANDOFF.md exists, read it first. Check its "Updated" time against `git log -1`. If the code is newer than the note, say so before you trust it.
