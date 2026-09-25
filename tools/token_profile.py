#!/usr/bin/env python3
"""Token + API-equivalent $ profile of local Claude Code transcripts.

Reads ~/.claude/projects/**/*.jsonl, keeps ONE usage record per assistant
message.id (Claude Code writes the same message once per content block, so a
raw sum overcounts ~2x; cost-guardian undercounts ~3x because it ignores cache
reads).  Prices are Anthropic list $/MTok (claude-api skill table 2026-06):
5-minute cache write = 1.25x input, 1-hour write = 2x input, cache read per model.
Subscription (Max/Pro) users pay quota, not $ -- treat the $ as relative weights.

Usage: python3 tools/token_profile.py [--days 7] [--top 12] [--slug SUBSTR]
Measured 2026-09-25 (session cto-ce3535eb): see
Agents/Wikis/research/2026-09-25-token-saving-techniques-caveman-survey.md
"""
import argparse, collections, datetime, glob, json, os, time

# model -> (input, cache_write_5m, cache_write_1h, cache_read, output) $/MTok
PRICES = {
    'fable-5-1': (10, 12.5, 20, 0.25, 50), 'fable-5': (10, 12.5, 20, 0.25, 50),
    'opus-5-5': (4, 5, 8, 0.20, 20), 'opus-5': (5, 6.25, 10, 0.50, 25),
    'opus-4-8': (5, 6.25, 10, 0.50, 25), 'opus-4-7': (5, 6.25, 10, 0.50, 25),
    'sonnet-5': (2, 2.5, 4, 0.20, 10), 'sonnet-4-6': (3, 3.75, 6, 0.30, 15),
    'haiku-4-5': (1, 1.25, 2, 0.10, 5),
}
SPIKE = 100_000   # cache_creation tokens in ONE turn that counts as a cache re-write


def price(model, u):
    p = PRICES.get(model.replace('claude-', '').split('[')[0])
    if not p:
        return None
    cc = u.get('cache_creation') or {}
    cw5, cw1 = cc.get('ephemeral_5m_input_tokens'), cc.get('ephemeral_1h_input_tokens')
    if cw5 is None and cw1 is None:
        cw5, cw1 = u.get('cache_creation_input_tokens', 0), 0
    return {'in': u.get('input_tokens', 0) * p[0] / 1e6,
            'cw': ((cw5 or 0) * p[1] + (cw1 or 0) * p[2]) / 1e6,
            'cr': u.get('cache_read_input_tokens', 0) * p[3] / 1e6,
            'out': u.get('output_tokens', 0) * p[4] / 1e6}


def result_len(cc):
    if isinstance(cc, str):
        return len(cc)
    if isinstance(cc, list):
        return sum(len(x.get('text', '')) if x.get('type') == 'text' else 3000 if x.get('type') == 'image' else 0
                   for x in cc if isinstance(x, dict))
    return 0


def scan(path):
    seen, blocks, id2name = {}, set(), {}
    s = dict(tok=collections.Counter(), usd=collections.Counter(), comp=collections.Counter(),
             tools=collections.Counter(), spikes=0, spike_tok=0, gaps=0, img=0, models=set(), max_ctx=0)
    last_ts = None
    with open(path, errors='ignore') as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except Exception:
                continue
            t, m = d.get('type'), d.get('message') or {}
            c = m.get('content')
            if t == 'assistant':
                u, mid = m.get('usage'), m.get('id')
                if u and mid and mid not in seen:
                    seen[mid] = 1
                    model = m.get('model') or '?'
                    s['models'].add(model.replace('claude-', ''))
                    for k, key in (('in', 'input_tokens'), ('cw', 'cache_creation_input_tokens'),
                                   ('cr', 'cache_read_input_tokens'), ('out', 'output_tokens')):
                        s['tok'][k] += u.get(key, 0)
                    cc = u.get('cache_creation') or {}
                    s['tok']['cw1h'] += cc.get('ephemeral_1h_input_tokens', 0)
                    s['max_ctx'] = max(s['max_ctx'], u.get('cache_read_input_tokens', 0) + u.get('cache_creation_input_tokens', 0))
                    if u.get('cache_creation_input_tokens', 0) > SPIKE:
                        s['spikes'] += 1
                        s['spike_tok'] += u['cache_creation_input_tokens']
                    pr = price(model, u)
                    if pr:
                        s['usd'].update(pr)
                    ts = d.get('timestamp')
                    if ts:
                        try:
                            tt = datetime.datetime.fromisoformat(ts.replace('Z', '+00:00'))
                            if last_ts and (tt - last_ts).total_seconds() > 3600:
                                s['gaps'] += 1
                            last_ts = tt
                        except ValueError:
                            pass
                if isinstance(c, list):
                    for b in c:
                        if not isinstance(b, dict):
                            continue
                        bt = b.get('type')
                        if bt == 'tool_use':
                            id2name[b.get('id')] = b.get('name')
                            payload = json.dumps(b.get('input'), ensure_ascii=False)
                        elif bt in ('text', 'thinking'):
                            payload = b.get(bt) or ''
                        else:
                            continue
                        key = (mid, bt, hash(payload))
                        if key not in blocks:
                            blocks.add(key)
                            s['comp'][bt] += len(payload)
            elif t == 'user' and isinstance(c, list):
                for b in c:
                    if not isinstance(b, dict):
                        continue
                    if b.get('type') == 'image':
                        s['img'] += 1
                    elif b.get('type') == 'tool_result':
                        cc = b.get('content')
                        s['img'] += sum(1 for x in cc if isinstance(x, dict) and x.get('type') == 'image') if isinstance(cc, list) else 0
                        s['tools'][id2name.get(b.get('tool_use_id'), '?')] += result_len(cc)
    s['turns'] = len(seen)
    return s


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--days', type=float, default=7)
    ap.add_argument('--top', type=int, default=12)
    ap.add_argument('--slug', default='', help='only project slugs containing this substring')
    ap.add_argument('--min-bytes', type=int, default=20000)
    a = ap.parse_args()
    root = os.path.expanduser('~/.claude/projects')
    cut = time.time() - a.days * 86400
    rows = []
    for f in glob.glob(root + '/**/*.jsonl', recursive=True):
        slug = f[len(root) + 1:].split('/')[0]
        if a.slug and a.slug not in slug:
            continue
        try:
            if os.path.getmtime(f) < cut or os.path.getsize(f) < a.min_bytes:
                continue
        except OSError:
            continue
        s = scan(f)
        if s['turns']:
            s['slug'], s['sid'] = slug, os.path.basename(f)[:8]
            rows.append(s)
    G = collections.Counter(); U = collections.Counter(); comp = collections.Counter(); tools = collections.Counter()
    spikes = spike_tok = gaps = turns = 0
    for s in rows:
        G.update(s['tok']); U.update(s['usd']); comp.update(s['comp']); tools.update(s['tools'])
        spikes += s['spikes']; spike_tok += s['spike_tok']; gaps += s['gaps']; turns += s['turns']
    T = G['in'] + G['cw'] + G['cr'] + G['out'] or 1
    D = sum(U.values()) or 1
    M = lambda x: f'{x / 1e6:,.1f}M'
    print(f"{len(rows)} sessions, {turns} turns, last {a.days:g} days (dedup by message.id)")
    print(f"tokens {M(T)}: fresh {G['in'] / T:.1%} | cache_write {G['cw'] / T:.1%} (1h-TTL {G['cw1h'] / max(1, G['cw']):.0%}) | cache_read {G['cr'] / T:.1%} | output {G['out'] / T:.2%}")
    print(f"API-equiv ${D:,.0f}: fresh {U['in'] / D:.0%} | cache_write {U['cw'] / D:.0%} | cache_read {U['cr'] / D:.0%} | output {U['out'] / D:.0%}")
    print(f"cache re-write spikes (>{SPIKE // 1000}k in one turn): {spikes} events / {M(spike_tok)} tokens; idle gaps >60 min: {gaps}")
    ct = sum(comp.values()) or 1
    print(f"assistant output chars: text {comp['text'] / ct:.0%} | thinking(visible) {comp['thinking'] / ct:.0%} | tool_use input {comp['tool_use'] / ct:.0%}")
    tt = sum(tools.values()) or 1
    print('context inflow by tool: ' + ', '.join(f'{n} {v / tt:.0%}' for n, v in tools.most_common(6)))
    print(f"\n{'slug':32} {'sid':8} {'model':18} {'turns':>5} {'$':>6} {'cr%':>4} {'cw%':>4} {'out%':>4} {'spk':>3} {'gap':>3} {'img':>3} {'maxctx':>6}")
    for s in sorted(rows, key=lambda r: -sum(r['usd'].values()))[:a.top]:
        d = sum(s['usd'].values()) or 1
        print(f"{s['slug'][-32:]:32} {s['sid']:8} {'+'.join(sorted(s['models']))[:18]:18} {s['turns']:5d} {d:6,.0f} "
              f"{s['usd']['cr'] / d:4.0%} {s['usd']['cw'] / d:4.0%} {s['usd']['out'] / d:4.0%} {s['spikes']:3d} {s['gaps']:3d} {s['img']:3d} {s['max_ctx'] / 1e3:5.0f}k")


if __name__ == '__main__':
    main()
