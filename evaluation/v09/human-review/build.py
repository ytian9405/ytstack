#!/usr/bin/env python3
"""Build the v09 blind page from Sol's first run. key.json is the only arm map."""
import importlib.util
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / 'results'
FIXTURES_BUILD = HERE.parent / 'fixtures' / 'build.py'
SEED = 20261113
ORDER = ('U1', 'U2', 'U3', 'U4', 'U5', 'U6')

spec = importlib.util.spec_from_file_location('v09_fixtures_docs', FIXTURES_BUILD)
FIXTURES = importlib.util.module_from_spec(spec)
spec.loader.exec_module(FIXTURES)
DRAFTS = {case: text for case, (_rel, text) in FIXTURES.DOCS.items()}

PAGE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>盲看 · 第九轮</title>
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
.quote{white-space:pre-wrap;overflow-wrap:break-word;margin:0;font-variant-ligatures:none}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media (max-width:760px){.pair{grid-template-columns:1fr}}
.ans{min-width:0;background:var(--panel);border:1px solid var(--line);border-radius:12px;display:flex;flex-direction:column}
.ans.chosen{border-color:var(--pick);box-shadow:0 0 0 1px var(--pick)}
.ans header{display:flex;gap:10px;align-items:baseline;padding:10px 14px;border-bottom:1px solid var(--line)}
.tag{font-weight:700}
.len{color:var(--muted);font-size:13px;font-variant-numeric:tabular-nums}
.md{padding:4px 14px 14px;overflow-wrap:break-word}
.md p{margin:.55em 0}
.md pre{white-space:pre-wrap;overflow-wrap:break-word;background:var(--soft);border-radius:8px;padding:8px 10px;margin:.55em 0;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.9em}
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
    <p>一共 6 题，每题是一份要改写的中文稿子。每题先给你看<strong>原稿全文</strong>，再并排两份改写，左右随机标成甲、乙。</p>
    <p>看内容，选你更愿意收到的一份，也可以选差不多；可以写一句说明。甲乙背后是哪一版，页面上看不出来，选完先别翻别的文件。</p>
    <p>选完点底部「复制结果」，把 JSON 存成 FEEDBACK.json。里面只有甲、乙和题号，没有组别。备注可以空着。</p>
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
const KEY='ytstack-blind-v09';
let S={};try{S=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(S))}catch(e){}};
const st=n=>S[n]||(S[n]={pick:'',why:''});
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function render(s){
  const safe=esc(s);
  const blocks=[];
  const staged=safe.replace(/```(\w*)\n?([\s\S]*?)(?:```|$)/g,(m,lang,body)=>{blocks.push(body);return '\n\n\u0000B'+(blocks.length-1)+'\u0000\n\n'});
  let html=staged.split(/\n{2,}/).map(p=>{
    let inner=p.replace(/`([^`\n]+)`/g,'<code>$1</code>').replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>').replace(/\n/g,'<br>');
    inner=inner.replace(/\u0000B(\d+)\u0000/g,(m,i)=>'<pre>'+blocks[+i]+'</pre>');
    return '<p>'+inner+'</p>';
  }).join('');
  html=html.replace(/<p><pre>([\s\S]*?)<\/pre><\/p>/g,'<pre>$1</pre>');
  return html;
}
function build(){
  const root=document.getElementById('qs');root.innerHTML='';
  for(const q of QS){
    const s=st(q.n);
    const sec=document.createElement('section');sec.className='q';sec.id='q'+q.n;
    const cards=['甲','乙'].map(side=>{
      const text=q[side]||'（这一侧没有回复）';
      return `<article class="ans${s.pick===side?' chosen':''}" data-side="${side}"><header><span class="tag">${side}</span><span class="len">${[...text].length} 字</span></header><div class="md">${render(text)}</div></article>`;
    }).join('');
    sec.innerHTML=`<div class="eyebrow">第 ${q.n} 题</div><h2>${esc(q.title)}</h2>
      <div class="ask"><div class="label">题目原话</div><p class="quote">${esc(q.ask)}</p></div>
      <div class="context"><div class="label">原稿全文（改写前的稿子）</div><p class="quote">${esc(q.draft)}</p></div>
      <div class="pair">${cards}</div>
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
    value = value.replace('$unslop', '（技能）')
    value = value.replace('$technical-bro', '（技能）')
    value = re.sub(r'(?<![A-Za-z])unslop(?![A-Za-z])', '（技能）', value, flags=re.I)
    value = re.sub(r'(?<![A-Za-z-])technical-bro(?![A-Za-z-])', '（技能）', value, flags=re.I)
    value = re.sub(r'\[[^\]]*\]\(\.agents/skills/[^)]*\)', '说明', value)
    value = re.sub(r'\.agents/skills/\S+', '', value)
    value = value.replace('实验组', '一组').replace('对照组', '另一组')
    value = re.sub(r'\bcontrol\b', '一组', value, flags=re.I)
    value = re.sub(r'\btreatment\b', '另一组', value, flags=re.I)
    value = value.replace('a5bfa83', '旧版').replace('12c04f8', '新版')
    value = re.sub(r'[^\n]*没(?:有)?找到[^\n]*技能[^\n]*', '', value)
    value = re.sub(r'\n{3,}', '\n\n', value)
    return value.strip()


def reply_text(record):
    return record.get('final') or ''


def main():
    rng = random.Random(SEED)
    questions, key = [], []
    titles = {
        'U1': '账本这边的两周进展说明',
        'U2': '去重的设计说明',
        'U3': 'v0.4.0 发布说明',
        'U4': '三月合计多算 1200 分的事故记录',
        'U5': '导出少三笔的排查记录',
        'U6': '三月合计多算 36100 分的修复指引',
    }
    for number, case in enumerate(ORDER, 1):
        spec = json.loads((HERE.parent / 'prompts.json').read_text())[case]
        sides = {}
        for arm in ('control', 'treatment'):
            path = RESULTS / f'{case}-sol-{arm}-r1.json'
            if not path.is_file():
                raise SystemExit(f'missing {path.name}')
            record = json.loads(path.read_text())
            if record.get('status') != 'ok':
                raise SystemExit(f'{path.name} status is {record.get("status")}')
            sides[arm] = scrub(reply_text(record))
        if rng.random() < 0.5:
            alias = {'甲': 'treatment', '乙': 'control'}
        else:
            alias = {'甲': 'control', '乙': 'treatment'}
        questions.append({
            'n': number,
            'source': case,
            'title': titles[case],
            'ask': scrub(spec['prompt']),
            'draft': DRAFTS[case].rstrip('\n'),
            '甲': sides[alias['甲']],
            '乙': sides[alias['乙']],
        })
        key.append({'question': number, 'source': case, '甲': alias['甲'], '乙': alias['乙']})
    payload = json.dumps(questions, ensure_ascii=False).replace('</', '<\\/')
    html = PAGE.replace('__QS__', payload)
    (HERE / 'blind-review.html').write_text(html, encoding='utf-8')
    (HERE / 'key.json').write_text(json.dumps(key, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    forbidden = re.compile(
        r'control|treatment|实验组|对照组|对照|实验|a5bfa83|12c04f8|unslop|technical-bro', re.I)
    hits = [f'{n}:{line.strip()[:120]}' for n, line in enumerate(html.splitlines(), 1) if forbidden.search(line)]
    print(f'built {len(questions)} questions, seed {SEED}')
    if hits:
        print('LEAKS')
        print('\n'.join(hits[:30]))
        raise SystemExit(1)
    print('no forbidden tokens in the page')


if __name__ == '__main__':
    main()
