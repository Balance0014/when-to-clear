"""Synthetic transcripts only. No network, no real usage data."""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import when_to_clear as W  # noqa: E402


def reply(i, ctx, write=2_000, out=500, dup=1, ts='2026-10-28T10:00:00Z'):
    """A transcript line for one reply whose context is `ctx` tokens; Claude Code repeats it per content block."""
    e = {'type': 'assistant', 'timestamp': ts,
         'message': {'id': f'msg_{i}', 'usage': {'input_tokens': 3, 'cache_creation_input_tokens': write,
                                                 'cache_read_input_tokens': ctx - write - 3, 'output_tokens': out}}}
    return [json.dumps(e)] * dup


def write(lines):
    d = tempfile.mkdtemp()
    p = os.path.join(d, 's.jsonl')
    with open(p, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    return d, p


class Parse(unittest.TestCase):
    def test_sizes(self):
        self.assertEqual(W.size('200k'), 200_000)
        self.assertEqual(W.size('1.5m'), 1_500_000)
        self.assertEqual(W.size('90000'), 90_000)

    def test_one_reply_counted_once(self):
        _, p = write(reply(1, 80_000, dup=3) + reply(2, 90_000, dup=2) + ['not json', '{"type":"user"}'])
        cs = W.calls(p)
        self.assertEqual(len(cs), 2)
        self.assertEqual(sum(cs[1][1:4]), 90_000)


class Records(unittest.TestCase):
    def test_api_errors_are_not_replies(self):
        err = json.dumps({'type': 'assistant', 'timestamp': '2026-10-28T10:00:00Z', 'message': {
            'id': 'msg_err', 'model': '<synthetic>', 'usage': {'input_tokens': 0, 'output_tokens': 0}}})
        _, p = write([err] + reply(1, 70_000))
        self.assertEqual(len(W.calls(p)), 1)

    def test_first_reply_is_not_a_resend(self):
        r = W.analyze({'a': W.calls(write(reply(1, 70_000, write=69_000) + reply(2, 72_000))[1])}, 200_000)
        self.assertEqual(r['rewrites'], 0)


class Analyze(unittest.TestCase):
    def test_short_sessions_cost_nothing_extra(self):
        r = W.analyze({'a': W.calls(write([l for i in range(20) for l in reply(i, 60_000 + i * 2_000)])[1])}, 200_000)
        self.assertEqual(r['share_over'], 0)
        self.assertEqual(r['saved_share'], 0)
        self.assertEqual(r['clears'], 0)

    def test_long_session_shows_the_tax_and_the_saving(self):
        lines = [l for i in range(200) for l in reply(i, 60_000 + i * 4_000)]   # grows to ~856k
        r = W.analyze({'a': W.calls(write(lines)[1])}, 200_000)
        self.assertGreater(r['share_over'], 0.7)
        self.assertGreater(r['saved_share'], 0.3)
        self.assertLess(r['saved_share'], r['share_over'])
        self.assertGreaterEqual(r['clears'], 4)

    def test_cache_rewrite_is_counted(self):
        lines = reply(1, 300_000, write=2_000) + reply(2, 302_000, write=290_000)   # came back after the cache expired
        r = W.analyze({'a': W.calls(write(lines)[1])}, 200_000)
        self.assertEqual(r['rewrites'], 1)

    def test_real_compaction_resets_the_simulation(self):
        lines = ([l for i in range(60) for l in reply(i, 60_000 + i * 5_000)]
                 + [l for i in range(60, 80) for l in reply(i, 40_000 + (i - 60) * 2_000)])
        r = W.analyze({'a': W.calls(write(lines)[1])}, 200_000)
        self.assertGreaterEqual(r['saved_share'], 0)

    def test_window_filters_old_replies(self):
        d, _ = write(reply(1, 300_000, ts='2020-01-01T00:00:00Z') + reply(2, 310_000, ts='2999-01-01T00:00:00Z'))
        sessions = W.load(d, 7)
        self.assertEqual(sum(len(v) for v in sessions.values()), 1)


class Hook(unittest.TestCase):
    def run_hook(self, lines, sid='s1'):
        _, p = write(lines)
        sys.stdin = io.StringIO(json.dumps({'transcript_path': p, 'session_id': sid}))
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(W.hook(200_000), 0)
        return buf.getvalue()

    def setUp(self):
        W.STATE = os.path.join(tempfile.mkdtemp(), 'nudged.json')

    def test_quiet_below_the_size(self):
        self.assertEqual(self.run_hook(reply(1, 150_000)), '')

    def test_reminds_once_per_step(self):
        out = self.run_hook(reply(1, 210_000))
        self.assertIn('210k tokens', json.loads(out)['systemMessage'])
        self.assertEqual(self.run_hook(reply(1, 250_000)), '')          # same step: stays quiet
        self.assertIn('systemMessage', self.run_hook(reply(1, 320_000)))  # next step: reminds again

    def test_reminds_again_after_compaction(self):
        self.assertIn('systemMessage', self.run_hook(reply(1, 210_000)))
        self.assertIn('systemMessage', self.run_hook(reply(2, 320_000)))
        self.assertEqual(self.run_hook(reply(3, 60_000)), '')            # compacted
        self.assertIn('systemMessage', self.run_hook(reply(4, 220_000)))

    def test_bad_size_never_crashes_the_hook(self):
        _, p = write(reply(1, 300_000))
        sys.stdin = io.StringIO(json.dumps({'transcript_path': p, 'session_id': 'x'}))
        self.assertEqual(W.hook('200kb'), 0)

    def test_never_blocks_or_crashes(self):
        out = self.run_hook(reply(1, 900_000))
        self.assertNotIn('decision', json.loads(out))
        sys.stdin = io.StringIO('garbage')
        self.assertEqual(W.hook(200_000), 0)


if __name__ == '__main__':
    unittest.main()
