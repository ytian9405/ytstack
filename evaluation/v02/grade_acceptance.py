#!/usr/bin/env python3
"""Blind grader: can a fresh session reject known-wrong implementations using only the criteria document?"""
import concurrent.futures as cf, json, os, signal, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS = json.loads((HERE / 'acceptance-tasks.json').read_text())
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["wrong", "ok", "decisions"], "properties": {
    "wrong": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["i", "verdict", "quote"],
              "properties": {"i": {"type": "integer"}, "verdict": {"type": "string", "enum": ["REJECT", "PASS_THROUGH"]}, "quote": {"type": "string"}}}},
    "ok": {"type": "object", "additionalProperties": False, "required": ["verdict", "quote"],
           "properties": {"verdict": {"type": "string", "enum": ["ACCEPT", "REJECT"]}, "quote": {"type": "string"}}},
    "decisions": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["i", "state", "quote"],
                  "properties": {"i": {"type": "integer"}, "state": {"type": "string", "enum": ["ASKED", "DECIDED_SILENTLY", "ABSENT"]}, "quote": {"type": "string"}}}}}}
PROMPT = """下面是一份验收标准。只依据这份文字判断，不要读文件、不要运行任何东西，不要用你自己对“应该怎样”的看法补充它。

<标准>
{doc}
</标准>

一、wrong：对下面每个实现，判断验收人只照这份标准检查时会怎样。标准里有一条明确会让它不通过，填 REJECT，并逐字引用那一条。标准没有写到、或写得含糊到可以放过，填 PASS_THROUGH，quote 留空。
{wrong}

二、ok：下面这个实现，标准会不会拒绝它。会拒绝填 REJECT 并引用；标准把这一点列为待决定、或没有禁止，填 ACCEPT。
{ok}

三、decisions：下面每个问题，这份标准如何处理。明确摆出来请读者决定（即使给了推荐）填 ASKED；直接按某个答案写成要求、没有说明这是可选的填 DECIDED_SILENTLY；完全没提填 ABSENT。逐字引用依据。
{decisions}
"""


def number(items):
    return '\n'.join(f'{i}. {x}' for i, x in enumerate(items))


def grade(path):
    r = json.loads(Path(path).read_text())
    task = TASKS[r['id'].split('-')[0]]
    with tempfile.TemporaryDirectory(prefix='ytgrade-') as temp:
        schema, out = Path(temp) / 's.json', Path(temp) / 'o.json'
        schema.write_text(json.dumps(SCHEMA))
        cmd = ['codex', 'exec', '--json', '--ephemeral', '--skip-git-repo-check', '--sandbox', 'read-only', '-m', 'gpt-6.1-sol',
               '-C', temp, '--output-schema', str(schema), '-o', str(out),
               PROMPT.format(doc=r['final'], wrong=number(task['wrong']), ok=task['ok'], decisions=number(task['decisions']))]
        for _ in range(3):
            p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            try:
                p.wait(timeout=300)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                p.wait()
            if out.exists() and out.read_text().strip():
                return r['id'], json.loads(out.read_text())
    return r['id'], None


if __name__ == '__main__':
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dst.mkdir(parents=True, exist_ok=True)
    files = [f for f in sorted(src.glob('AC*.json')) if not (dst / f.name).exists()]
    with cf.ThreadPoolExecutor(5) as pool:
        for name, result in pool.map(grade, files):
            print(name, 'ok' if result else 'FAILED', flush=True)
            if result:
                (dst / f'{name}.json').write_text(json.dumps(result, ensure_ascii=False, indent=1))
