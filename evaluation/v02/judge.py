#!/usr/bin/env python3
"""Blind pairwise reader judge run through Codex CLI; calibrated against the user's recorded choices."""
import concurrent.futures as cf, json, os, signal, subprocess, tempfile, threading
from pathlib import Path

SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["a_unexplained_terms", "b_unexplained_terms", "a_needless", "b_needless",
                       "a_lost_or_wrong", "b_lost_or_wrong", "preferred", "reason"],
          "properties": {"a_unexplained_terms": {"type": "array", "items": {"type": "string"}},
                         "b_unexplained_terms": {"type": "array", "items": {"type": "string"}},
                         "a_needless": {"type": "array", "items": {"type": "string"}},
                         "b_needless": {"type": "array", "items": {"type": "string"}},
                         "a_lost_or_wrong": {"type": "array", "items": {"type": "string"}},
                         "b_lost_or_wrong": {"type": "array", "items": {"type": "string"}},
                         "preferred": {"type": "string", "enum": ["A", "B", "TIE"]},
                         "reason": {"type": "string"}}}

SLOTS = threading.BoundedSemaphore(5)
TIMEOUT = 180
ATTEMPTS = 3

PROMPT = """你在替一位读者比较两份中文文字。读者负责这个项目、做决定，但没有读过相关代码，也不是这个具体领域的专家。

{context}

=== A ===
{a}

=== B ===
{b}

请逐句读完再判断，只依据文字本身：
- a_unexplained_terms / b_unexplained_terms：逐字摘出这位读者不查资料就看不懂、且文中没有解释的词。命令、路径、字段名这类要照抄的内容不算。
- a_needless / b_needless：逐字摘出删掉后读者也不会少知道什么的句子。
- a_lost_or_wrong / b_lost_or_wrong：相比另一份，这一份丢掉了读者做决定需要的内容，或说错了什么。
- preferred：这位读者更愿意收到哪一份。两份确实没有差别才选 TIE。
- reason：一句话。
"""


def judge(a, b, context='', model='gpt-6-astra'):
    with tempfile.TemporaryDirectory(prefix='ytjudge-') as temp:
        schema = Path(temp) / 'schema.json'
        out = Path(temp) / 'out.json'
        schema.write_text(json.dumps(SCHEMA))
        cmd = ['codex', 'exec', '--json', '--ephemeral', '--skip-git-repo-check', '--sandbox', 'read-only',
               '-m', model, '-C', temp, '--output-schema', str(schema), '-o', str(out),
               PROMPT.format(context=context, a=a, b=b)]
        err = ''
        for _ in range(ATTEMPTS):
            with SLOTS:
                # New session so a timeout can kill the native child, which outlives its node wrapper.
                p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.PIPE, text=True, start_new_session=True)
                try:
                    _, err = p.communicate(timeout=TIMEOUT)
                except subprocess.TimeoutExpired:
                    os.killpg(p.pid, signal.SIGKILL)
                    p.communicate()
                    err = 'timeout'
            if out.exists() and out.read_text().strip():
                return json.loads(out.read_text())
        return {'error': err[-300:]}


def both_orders(x, y, context='', repeats=2):
    """Returns list of verdicts normalized to x/y whichever slot each was shown in."""
    def one(i):
        swap = i % 2 == 1
        r = judge(y, x, context) if swap else judge(x, y, context)
        if 'error' in r:
            return r
        win = r['preferred']
        pick = 'TIE' if win == 'TIE' else ('x' if (win == 'A') != swap else 'y')
        sx, sy = ('b', 'a') if swap else ('a', 'b')
        return {'pick': pick, 'reason': r['reason'],
                'x_terms': r[f'{sx}_unexplained_terms'], 'y_terms': r[f'{sy}_unexplained_terms'],
                'x_needless': r[f'{sx}_needless'], 'y_needless': r[f'{sy}_needless'],
                'x_lost': r[f'{sx}_lost_or_wrong'], 'y_lost': r[f'{sy}_lost_or_wrong']}
    with cf.ThreadPoolExecutor(repeats) as pool:
        return list(pool.map(one, range(repeats)))
