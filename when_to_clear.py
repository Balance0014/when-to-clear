#!/usr/bin/env python3
"""when-to-clear: how much of your Claude Code usage goes to re-reading long conversations.

Every reply re-sends the whole conversation so far. Early in a session that is cheap; at
300k tokens, every "ok, next" re-reads 300k tokens. This script reads the usage numbers
Claude Code already writes to ~/.claude/projects and tells you:

  * how much of your usage happened while a conversation was past a size you choose,
  * how much you would have saved by starting fresh at that size with a short handoff note,
  * how often a long session had to be re-sent at full price after its cache expired,
  * how big a brand-new session is before you type anything.

Usage:
  when_to_clear.py [--days 7] [--at 200k] [--dir ~/.claude/projects] [--json]
  when_to_clear.py hook [--at 200k]     Stop hook: a one-line reminder when a session passes
                                        the size (once per size step, never blocks)

Costs are weighted the way the API prices them, relative to a fresh input token:
cache reads 0.1x, cache writes 1.25x, output 5x. Anthropic doesn't publish how plan limits
weigh each kind, so read the percentages as "share of the work", not as exact plan usage.
Standard library only. Python 3.9+. Reads local files, sends nothing anywhere.
"""
import glob
import json
import os
import statistics
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.expanduser('~/.claude/projects')
STATE = os.environ.get('WHEN_TO_CLEAR_STATE') or os.path.expanduser('~/.claude/when-to-clear/nudged.json')
W_READ, W_WRITE, W_OUT = 0.1, 1.25, 5.0
# What a restart costs, on the cautious side: the new session starts from the same fixed overhead as
# this one (system prompt, tools, CLAUDE.md), plus a ~5k handoff note and ~25k of files the agent
# has to read again; writing the note takes ~2k output tokens.
HANDOFF = 30_000
HANDOFF_COST = 2_000
BREAK = 300               # seconds of quiet before a full re-send counts as "after a break"


def size(text):
    """'200k' -> 200000, '1.5m' -> 1500000."""
    t = str(text).strip().lower().replace(',', '').replace('_', '')
    mult = 1_000 if t.endswith('k') else 1_000_000 if t.endswith('m') else 1
    return int(float(t.rstrip('km')) * mult)


def calls(path):
    """One record per API reply in a transcript: (time, input, cache_write, cache_read, output).

    Claude Code writes a line per content block, all carrying the same usage, so replies are
    de-duplicated by message id.
    """
    seen, out = set(), []
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            if '"usage"' not in line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                continue
            m = e.get('message') or {}
            u = m.get('usage')
            if e.get('type') != 'assistant' or not isinstance(u, dict):
                continue
            key = m.get('id') or e.get('requestId') or e.get('uuid')
            if key in seen:
                continue
            seen.add(key)
            out.append((e.get('timestamp') or '', u.get('input_tokens') or 0, u.get('cache_creation_input_tokens') or 0,
                        u.get('cache_read_input_tokens') or 0, u.get('output_tokens') or 0))
    return out


def weight(inp, cw, cr, out):
    return inp + W_WRITE * cw + W_READ * cr + W_OUT * out


def analyze(sessions, at):
    """sessions: {name: [call, ...]}. Returns the numbers the report prints."""
    tot_w = over_w = saved_w = 0.0
    raw = over_raw = 0
    rewrites, after_break, rewrite_w, starts, n_calls, clears = 0, 0, 0.0, [], 0, 0
    biggest = []
    for name, cs in sessions.items():
        if not cs:
            continue
        base = sum(cs[0][1:4])
        starts.append(base)
        floor = base + HANDOFF                         # where a fresh session would start
        peak, offset, s_w, prev = 0, 0, 0.0, None
        for ts, inp, cw, cr, out in cs:
            ctx = inp + cw + cr
            w = weight(inp, cw, cr, out)
            n_calls += 1
            tot_w += w
            s_w += w
            raw += ctx
            peak = max(peak, ctx)
            if ctx > at:
                over_w += w
                over_raw += ctx
            if ctx > 50_000 and cw > ctx / 2:          # the whole conversation re-sent at write price
                rewrites += 1
                rewrite_w += W_WRITE * cw
                if prev and _gap(prev, ts) >= BREAK:
                    after_break += 1
            prev = ts
            # Start fresh at `at` with a handoff note: everything above the note is not re-read.
            if ctx < offset:                            # the real session was compacted or cleared
                offset = 0
            if ctx - offset > at and floor < at:
                offset = ctx - floor
                clears += 1
                saved_w -= W_WRITE * HANDOFF + W_OUT * HANDOFF_COST
            cut = max(0, min(ctx - floor, offset))
            saved_w += W_READ * min(cut, cr) + W_WRITE * min(max(0, cut - cr), cw) + max(0, cut - cr - cw)
        biggest.append((s_w, peak, len(cs), name))
    biggest.sort(reverse=True)
    return {
        'sessions': len(starts), 'calls': n_calls, 'tokens_read': raw,
        'share_over': over_w / tot_w if tot_w else 0.0, 'raw_share_over': over_raw / raw if raw else 0.0,
        'saved_share': max(0.0, saved_w) / tot_w if tot_w else 0.0, 'clears': clears,
        'rewrites': rewrites, 'rewrites_after_break': after_break, 'rewrite_share': rewrite_w / tot_w if tot_w else 0.0,
        'start_median': int(statistics.median(starts)) if starts else 0,
        'biggest': [{'session': n, 'share': w / tot_w if tot_w else 0, 'peak': p, 'calls': c}
                    for w, p, c, n in biggest[:5]],
    }


def _gap(a, b):
    try:
        t = [datetime.fromisoformat(x.replace('Z', '+00:00')) for x in (a, b)]
        return (t[1] - t[0]).total_seconds()
    except ValueError:
        return 0


def load(root, days):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%S')
    sessions = {}
    for path in glob.glob(os.path.join(root, '**', '*.jsonl'), recursive=True):
        try:
            if datetime.fromtimestamp(os.path.getmtime(path), timezone.utc) < datetime.now(timezone.utc) - timedelta(days=days):
                continue
            cs = [c for c in calls(path) if c[0] >= since]
        except OSError:
            continue
        if cs:
            sessions[os.path.relpath(path, root)] = sorted(cs)
    return sessions


def human(n):
    return f'{n / 1e9:.1f}B' if n >= 1e9 else f'{n / 1e6:.1f}M' if n >= 1e6 else f'{n / 1e3:.0f}k'


def report(r, days, at):
    k = human(at)
    print(f'when-to-clear · last {days} days · {r["sessions"]} transcripts · {r["calls"]:,} replies')
    print(f'Tokens re-read as context: {human(r["tokens_read"])}')
    print(f'  {r["share_over"]:.0%} of the work happened while a conversation was over {k} tokens.')
    print(f'  Starting fresh at {k} with a short handoff note would have saved about {r["saved_share"]:.0%}'
          f' ({r["clears"]} restarts).')
    print(f'  Long conversations were re-sent from scratch {r["rewrites"]} times, {r["rewrites_after_break"]} of them'
          f' after a break of 5+ minutes ({r["rewrite_share"]:.0%} of the work).')
    print(f'  A new session holds about {human(r["start_median"])} tokens by its first reply'
          ' (system prompt, tools, MCP servers, CLAUDE.md, memory, your first message).')
    if r['biggest']:
        print('Heaviest sessions:')
        for b in r['biggest']:
            print(f'  {b["share"]:5.1%} of the work · peaked at {human(b["peak"])} · {b["calls"]} replies · {b["session"]}')


def hook(at):
    """Stop hook: remind once per size step (at, 1.5x, 2x, ...). Never blocks, never fails loudly."""
    try:
        payload = json.loads(sys.stdin.read() or '{}')
        cs = calls(payload['transcript_path'])
        if not cs:
            return 0
        ctx = sum(cs[-1][1:4])
        step = at // 2
        level = 0 if ctx < at else (ctx - at) // step + 1
        if not level:
            return 0
        try:
            with open(STATE, encoding='utf-8') as f:
                state = json.load(f)
        except (OSError, ValueError):
            state = {}
        sid = str(payload.get('session_id'))
        if state.get(sid, 0) >= level:
            return 0
        state[sid] = level
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        with open(STATE, 'w', encoding='utf-8') as f:
            json.dump(dict(list(state.items())[-200:]), f)
        print(json.dumps({'systemMessage': (
            f'when-to-clear: this conversation is at {human(ctx)} tokens, and every reply re-reads all of it. '
            'At your next stopping point, ask Claude to write a handoff note, then /clear and paste it.')}))
    except Exception:
        pass
    return 0


def main(argv):
    args = argv[1:]
    opt = {'--days': '7', '--at': '200k', '--dir': ROOT}
    mode = 'hook' if args[:1] == ['hook'] else 'report'
    args = args[1:] if mode == 'hook' else args
    as_json = '--json' in args
    args = [a for a in args if a != '--json']
    for i in range(0, len(args) - 1, 2):
        if args[i] not in opt:
            print(__doc__)
            return 2
        opt[args[i]] = args[i + 1]
    if len(args) % 2:
        print(__doc__)
        return 2
    at = size(opt['--at'])
    if mode == 'hook':
        return hook(at)
    days = int(opt['--days'])
    r = analyze(load(os.path.expanduser(opt['--dir']), days), at)
    if as_json:
        print(json.dumps(r, indent=1))
    elif not r['calls']:
        print(f'No Claude Code usage found in {opt["--dir"]} for the last {days} days.')
    else:
        report(r, days, at)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
