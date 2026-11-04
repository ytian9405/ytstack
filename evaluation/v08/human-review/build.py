#!/usr/bin/env python3
"""Build the v08 blind page from Sol's first run. key.json is the only arm map."""
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / 'results'
PROMPTS = json.loads((HERE.parent / 'prompts.json').read_text())
SEED = 20261108
ORDER = ('H1', 'H2', 'T1', 'T2', 'I1', 'I2')
TWO_TURN = {'H1', 'H2'}
HANDOFF = {'H1', 'H2'}

PAGE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>盲看 · 第八轮</title>
<style>
:root{--bg:#f4f1ea;--panel:#fffdf8;--fg:#241f1a;--muted:#6d645b;--line:#e3d9cc;--accent:#8a4b2f;--soft:#f3e6da;--pick:#1f6b45;--pick-soft:#e5f3eb;
--display:"Iowan Old Style","Palatino Linotype","Songti SC",serif;--body:"Avenir Next","PingFang SC","Noto Sans SC",sans-serif}
@media (prefers-color-scheme:dark){:root{--bg:#171411;--panel:#221e1a;--fg:#f3ece3;--muted:#b7aa9e;--line:#3a322b;--accent:#e0a07a;--soft:#3a2a22;--pick:#8dcfab;--pick-soft:#1c3328;color-scheme:dark}}
*{box-sizing:border-box}
html,body{margin:0;max-width:100%;overflow-x:hidden}
body{background:var(--bg);color:var(--fg);font-family:var(--body);font-size:16px;line-height:1.65}
.wrap{max-width:1100px;margin:0 auto;padding:24px 16px 72px;display:flex;flex-direction:column;gap:22px}
.wrap>*{min-width:0;max-width:100%}
h1{font-family:var(--display);font-size:1.7rem;line-height:1.25;margin:0}
.intro{color:var(--muted);display:flex;flex-direction:column;gap:8px;max-width:min(68ch,100%)}
.intro p{margin:0}
.intro strong{color:var(--fg)}
.progress{position:sticky;top:0;z-index:2;background:var(--bg);padding:8px 0;border-bottom:1px solid var(--line);display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.dot{min-width:2.4em;min-height:2.4em;display:grid;place-items:center;border-radius:999px;border:1px solid var(--line);color:var(--muted);text-decoration:none}
.dot.done{background:var(--pick-soft);border-color:var(--pick);color:var(--pick)}
.progress .count{margin-left:auto;color:var(--muted);font-size:14px}
section.q{display:flex;flex-direction:column;gap:12px;scroll-margin-top:64px}
.eyebrow{font-size:13px;letter-spacing:.04em;color:var(--accent)}
h2{font-family:var(--display);font-size:1.25rem;margin:0}
.context,.ask{background:var(--soft);border-radius:12px;padding:12px 14px}
.context p,.ask p{margin:0}
.label{font-size:13px;color:var(--muted);margin-bottom:6px}
.quote{white-space:pre-wrap;overflow-wrap:break-word;margin:0}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media (max-width:760px){.pair{grid-template-columns:1fr}}
.ans{min-width:0;background:var(--panel);border:1px solid var(--line);border-radius:12px;display:flex;flex-direction:column}
.ans.chosen{border-color:var(--pick);box-shadow:0 0 0 1px var(--pick)}
.ans header{display:flex;gap:10px;align-items:baseline;padding:10px 14px;border-bottom:1px solid var(--line)}
.tag{font-weight:700}
.len{color:var(--muted);font-size:13px;font-variant-numeric:tabular-nums}
.md{padding:4px 14px 14px;overflow-wrap:break-word}
.md p{margin:.55em 0}
.md code{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.92em;background:var(--soft);padding:0 4px;border-radius:4px}
.vote{display:flex;flex-direction:column;gap:10px;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}
.choices{display:flex;gap:8px;flex-wrap:wrap}
button{font:inherit;font-size:16px;min-height:44px;cursor:pointer;border-radius:10px;border:1px solid var(--line);background:var(--panel);color:var(--fg);padding:8px 16px}
button[aria-pressed="true"]{background:var(--pick);border-color:var(--pick);color:#fff}
textarea{font:inherit;font-size:16px;width:100%;min-height:72px;border:1px solid var(--line);border-radius:10px;background:var(--bg);color:var(--fg);padding:10px}
label{color:var(--muted);font-size:14px}
.finish{display:flex;flex-direction:column;gap:10px;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}
#out{font:13px ui-monospace,Menlo,Consolas,monospace;min-height:140px}
.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.status{color:var(--pick);min-height:1.2em}
</style>
</head>
<body>
<div class="wrap">
  <div class="intro">
    <h1>盲看</h1>
    <p>一共 6 题。每题两份回复，左右标成甲、乙，顺序是随的。看内容，选你更愿意收到的一份，也可以选差不多。</p>
    <p>两轮的题先给你看第一轮的原话，再并排第二轮的回复。换电脑的两题还会并排放两边写出的交接。</p>
    <p>选完点底部「复制结果」。结果是 JSON，里面只有甲、乙和题号，没有组别。备注可以空着。</p>
  </div>
  <nav class="progress" id="progress" aria-label="进度"></nav>
  <div id="qs"></div>
  <div class="finish">
    <h2>复制结果</h2>
    <p id="remain"></p>
    <button class="primary" id="copy" type="button">复制结果</button>
    <div class="status" id="status" role="status"></div>
    <textarea id="out" readonly aria-label="结果 JSON"></textarea>
  </div>
</div>
<script>
const QS=__QS__;
const KEY='ytstack-blind-v08';
let S={};try{S=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(S))}catch(e){}};
const st=n=>S[n]||(S[n]={pick:'',why:''});
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function render(s){
  const parts=esc(s).split(/\n{2,}/);
  return parts.map(p=>'<p>'+p.replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>').replace(/\n/g,'<br>')+'</p>').join('');
}
function build(){
  const root=document.getElementById('qs');root.innerHTML='';
  for(const q of QS){
    const s=st(q.n);
    const sec=document.createElement('section');sec.className='q';sec.id='q'+q.n;
    const round=q.turns===2?`<div class="context"><div class="label">第一轮让模型做的事，用的是原话</div><p class="quote">${esc(q.round1)}</p></div><div class="ask"><div class="label">第二轮问的是</div><p class="quote">${esc(q.ask)}</p></div>`:`<div class="ask"><div class="label">题目原话</div><p class="quote">${esc(q.ask)}</p></div>`;
    const cards=['甲','乙'].map(side=>{
      const text=q[side]||'（这一侧没有回复）';
      return `<article class="ans${s.pick===side?' chosen':''}" data-side="${side}"><header><span class="tag">${side}</span><span class="len">${[...text].length} 字</span></header><div class="md">${render(text)}</div></article>`;
    }).join('');
    let files='';
    if(q.handoff){
      files=`<h2>交接文件</h2><div class="pair">`+['甲','乙'].map(side=>{
        const text=q[side+'文件']||'（这一侧没有写出交接文件）';
        return `<article class="ans"><header><span class="tag">${side}</span></header><div class="md">${render(text)}</div></article>`;
      }).join('')+`</div>`;
    }
    sec.innerHTML=`<div class="eyebrow">第 ${q.n} 题</div><h2>${esc(q.title)}</h2>${round}<div class="pair">${cards}</div>${files}
      <div class="vote"><div class="choices" role="group" aria-label="第 ${q.n} 题">${[['甲','甲更好'],['乙','乙更好'],['tie','差不多']].map(([v,t])=>`<button type="button" data-v="${v}" aria-pressed="${s.pick===v}">${t}</button>`).join('')}</div>
      <label for="why${q.n}">备注（可不填）</label><textarea id="why${q.n}">${esc(s.why)}</textarea></div>`;
    root.append(sec);
    sec.querySelectorAll('.choices button').forEach(b=>b.onclick=()=>{s.pick=b.dataset.v;save();
      sec.querySelectorAll('.choices button').forEach(x=>x.setAttribute('aria-pressed',x===b));
      sec.querySelectorAll('.ans[data-side]').forEach(a=>a.classList.toggle('chosen',a.dataset.side===s.pick));update()});
    sec.querySelector('textarea').oninput=e=>{s.why=e.target.value;save();update()};
  }
}
function update(){
  const p=document.getElementById('progress');p.innerHTML='';let done=0;
  for(const q of QS){const ok=!!st(q.n).pick;done+=ok;const a=document.createElement('a');a.href='#q'+q.n;a.className='dot'+(ok?' done':'');a.textContent=q.n;p.append(a)}
  const c=document.createElement('span');c.className='count';c.textContent=`已选 ${done} / ${QS.length}`;p.append(c);
  const rem=QS.filter(q=>!st(q.n).pick).map(q=>q.n);
  document.getElementById('remain').textContent=rem.length?`还有第 ${rem.join('、')} 题没选。`:`6 题都选完了，可以复制。`;
  const records=QS.map(q=>{const s=st(q.n);return {
    question:q.n, source:q.source,
    preferred_alias:s.pick==='甲'?'甲':s.pick==='乙'?'乙':s.pick==='tie'?'tie':'',
    preferred_arm:'', A:'甲', B:'乙', arm_A:'', arm_B:'',
    chars_A:[...(q['甲']||'')].length, chars_B:[...(q['乙']||'')].length,
    reason_verbatim:(s.why||'').trim()
  };});
  document.getElementById('out').value=JSON.stringify({recorded_at:new Date().toISOString(), rater:'user', records}, null, 1);
}
document.getElementById('copy').onclick=()=>{const o=document.getElementById('out');const st_=document.getElementById('status');
  const fallback=()=>{o.focus();o.select();st_.textContent='已选中，请手动复制。'};
  try{navigator.clipboard.writeText(o.value).then(()=>st_.textContent='已复制。',fallback)}catch(e){fallback()}};
build();update();
</script>
</body>
</html>
'''


def scrub(text):
    if not text:
        return ''
    value = str(text)
    value = value.replace('$in-your-own-words', '（手动调用）')
    value = value.replace('/in-your-own-words', '（手动调用）')
    value = re.sub(r'in-your-own-words', '（手动调用）', value, flags=re.I)
    value = re.sub(r'ketchup', '（技能）', value, flags=re.I)
    value = value.replace('实验组', '一组').replace('对照组', '另一组')
    value = re.sub(r'\bcontrol\b', '一组', value, flags=re.I)
    value = re.sub(r'\btreatment\b', '另一组', value, flags=re.I)
    value = re.sub(r'(?<![A-Za-z])teach(?![A-Za-z])', '（技能）', value, flags=re.I)
    value = re.sub(r'\[[^\]]*\]\(\.agents/skills/[^)]*\)', '说明', value)
    value = re.sub(r'\.agents/skills/\S+', '', value)
    value = re.sub(r'[^\n]*没(?:有)?找到[^\n]*技能[^\n]*', '', value)
    value = re.sub(r'\n{3,}', '\n\n', value)
    return value.strip()


def handoff_text(record):
    texts = record.get('followup_texts') or {}
    if 'HANDOFF.md' in texts:
        return texts['HANDOFF.md']
    for key, value in texts.items():
        if key.endswith('HANDOFF.md') or '交接' in Path(key).name:
            return value
    added = [name for name in (record.get('followup_files') or {}).get('added') or [] if name.endswith('.md')]
    if len(added) == 1 and added[0] in texts:
        return texts[added[0]]
    if texts:
        return '\n\n'.join(texts.values())
    return ''


def reply_text(record, case):
    if case in TWO_TURN:
        return record.get('followup_final') or ''
    return record.get('final') or ''


def main():
    rng = random.Random(SEED)
    questions, key = [], []
    titles = {
        'H1': '换电脑之前，待办和没提交的备注',
        'H2': '换电脑之前，这个月的账和后台任务',
        'T1': '按标题作废会碰到哪些账',
        'T2': '显示成元是怎么算出来的',
        'I1': '报销和自己花的，先说说要干嘛',
        'I2': '自己的支出和家里人的支出',
    }
    for number, case in enumerate(ORDER, 1):
        spec = PROMPTS[case]
        sides = {}
        files = {}
        for arm in ('control', 'treatment'):
            path = RESULTS / f'{case}-sol-{arm}-r1.json'
            if not path.is_file():
                raise SystemExit(f'missing {path.name}')
            record = json.loads(path.read_text())
            if record.get('status') != 'ok':
                raise SystemExit(f'{path.name} status is {record.get("status")}')
            sides[arm] = scrub(reply_text(record, case))
            files[arm] = scrub(handoff_text(record)) if case in HANDOFF else ''
        if rng.random() < 0.5:
            alias = {'甲': 'treatment', '乙': 'control'}
        else:
            alias = {'甲': 'control', '乙': 'treatment'}
        questions.append({
            'n': number,
            'source': case,
            'title': titles[case],
            'turns': 2 if case in TWO_TURN else 1,
            'round1': scrub(spec['prompt']) if case in TWO_TURN else '',
            'ask': scrub(spec['followup'] if case in TWO_TURN else spec['prompt']),
            'handoff': case in HANDOFF,
            '甲': sides[alias['甲']],
            '乙': sides[alias['乙']],
            '甲文件': files[alias['甲']],
            '乙文件': files[alias['乙']],
        })
        key.append({'question': number, 'source': case, '甲': alias['甲'], '乙': alias['乙']})
    payload = json.dumps(questions, ensure_ascii=False).replace('</', '<\\/')
    html = PAGE.replace('__QS__', payload)
    (HERE / 'blind-review.html').write_text(html, encoding='utf-8')
    (HERE / 'key.json').write_text(json.dumps(key, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    forbidden = re.compile(
        r'control|treatment|实验组|对照组|ketchup|teach|in-your-own-words', re.I)
    hits = [f'{n}:{line.strip()[:120]}' for n, line in enumerate(html.splitlines(), 1) if forbidden.search(line)]
    print(f'built {len(questions)} questions, seed {SEED}')
    if hits:
        print('LEAKS')
        print('\n'.join(hits[:30]))
        raise SystemExit(1)
    print('no forbidden tokens in the page')


if __name__ == '__main__':
    main()
