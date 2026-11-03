import json,glob,re,concurrent.futures as cf,subprocess,tempfile,os,signal
from pathlib import Path
import judge as J
from judge import both_orders
J.SLOTS=__import__('threading').BoundedSemaphore(3); J.TIMEOUT=300
HERE=Path(__file__).parent
strip=lambda t:re.sub(r'\]\(/tmp/[^)]*\)',']',t)
# finish calibration
E_=HERE.parent;w=E_/'ab-writing-20261102/runs';u=E_/'ab-unslop-20261102/runs'
key=json.load(open(E_/'ab-unslop-20261102/control/human-review-key.json'))['mapping']
fb=json.load(open(E_/'ab-unslop-20261102/human-review/FEEDBACK.json'))['records']
L={'bro-1':(w/'sample-35',w/'sample-66'),'bro-2':(w/'sample-48',w/'sample-74'),'tech-1':(w/'sample-53',w/'sample-89')}
for r in fb:
    if r.get('preferred_alias') in('A','B'):
        q=r['question'];win=r['preferred_original_label'];lose=[m['original_label'] for m in key if m['question']==q and m['original_label']!=win][0]
        L[f'unslop-{q}']=(u/win,u/lose)
cal=json.load(open(HERE/'calibration.json'))
def fix(n,i):
    if 'error' not in cal[n][i]: return
    x,y=[(p/'project/output.md').read_text() for p in L[n]]
    swap=i%2==1
    r=J.judge(y,x) if swap else J.judge(x,y)
    if 'error' in r: return
    win=r['preferred'];pick='TIE' if win=='TIE' else('x' if (win=='A')!=swap else 'y')
    sx,sy=('b','a') if swap else('a','b')
    cal[n][i]={'pick':pick,'reason':r['reason'],'x_terms':r[f'{sx}_unexplained_terms'],'y_terms':r[f'{sy}_unexplained_terms'],'x_needless':r[f'{sx}_needless'],'y_needless':r[f'{sy}_needless'],'x_lost':r[f'{sx}_lost_or_wrong'],'y_lost':r[f'{sy}_lost_or_wrong']}
with cf.ThreadPoolExecutor(3) as p: list(p.map(lambda a:fix(*a),[(n,i) for n in cal for i in range(4)]))
(HERE/'calibration.json').write_text(json.dumps(cal,ensure_ascii=False,indent=1))
print('calibration',{n:[i.get('pick','ERR') for i in v] for n,v in cal.items()},flush=True)
# holdout pairs: x=v01 baseline, y=v02
ids=sorted({f.split('/')[-1].rsplit('-v0',1)[0]+'|'+f.split('-r')[-1][0] for f in glob.glob('/tmp/ytev/holdout/H*.json')})
res={}
def one(s):
    b,rp=s.split('|')
    x=json.load(open(f'/tmp/ytev/holdout/{b}-v01-r{rp}.json'));y=json.load(open(f'/tmp/ytev/holdout/{b}-v02-r{rp}.json'))
    return f'{b}-r{rp}',both_orders(strip(x['final']),strip(y['final']),context='读者问的问题是：'+x['prompt'],repeats=2)
with cf.ThreadPoolExecutor(6) as p:
    for k,v in p.map(one,ids): res[k]=v; print(k,[i.get('pick','ERR') for i in v],flush=True)
(HERE/'holdout-pairs.json').write_text(json.dumps(res,ensure_ascii=False,indent=1))
# bro retention
SCH={"type":"object","additionalProperties":False,"required":["points"],"properties":{"points":{"type":"array","items":{"type":"object","additionalProperties":False,"required":["point","kept"],"properties":{"point":{"type":"string"},"kept":{"type":"string","enum":["KEPT","LOST","CHANGED"]}}}}}}
def keep(f):
    r=json.load(open(f))
    with tempfile.TemporaryDirectory(prefix='ytgrade-') as t:
        s,o=Path(t)/'s.json',Path(t)/'o.json';s.write_text(json.dumps(SCH))
        pr=f"原回复：\n{strip(r['final'])}\n\n改写：\n{strip(r['followup_final'])}\n\n列出原回复里读者做决定需要的每一条内容（结论、数字、前提、例外、推荐做法、备选方案），逐条判断改写是否保留：KEPT 保留（换说法也算），LOST 丢了，CHANGED 意思变了。不读文件，不运行任何东西。"
        for _ in range(3):
            p=subprocess.Popen(['codex','exec','--json','--ephemeral','--skip-git-repo-check','--sandbox','read-only','-m','gpt-6.1-sol','-C',t,'--output-schema',str(s),'-o',str(o),pr],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
            try:p.wait(timeout=240)
            except subprocess.TimeoutExpired: os.killpg(p.pid,signal.SIGKILL);p.wait()
            if o.exists() and o.read_text().strip(): return r['id'],json.loads(o.read_text())['points']
    return r['id'],None
with cf.ThreadPoolExecutor(6) as p: B=dict(p.map(keep,sorted(glob.glob('/tmp/ytev/holdout/H*-sol-*-r1.json'))))
(HERE/'bro-retention.json').write_text(json.dumps(B,ensure_ascii=False,indent=1))
for k,v in B.items(): print(k,None if v is None else (len(v),sum(i['kept']=='KEPT' for i in v),sum(i['kept']=='LOST' for i in v),sum(i['kept']=='CHANGED' for i in v)),flush=True)
print('ALLDONE')
