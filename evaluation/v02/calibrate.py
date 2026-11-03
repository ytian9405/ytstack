import json, concurrent.futures as cf
from pathlib import Path
from judge import both_orders
E_ = Path(__file__).resolve().parents[1]
w = E_/'ab-writing-20261102/runs'; u = E_/'ab-unslop-20261102/runs'
key = json.load(open(E_/'ab-unslop-20261102/control/human-review-key.json'))['mapping']
fb = json.load(open(E_/'ab-unslop-20261102/human-review/FEEDBACK.json'))['records']
L = [('bro-1', w/'sample-35', w/'sample-66'), ('bro-2', w/'sample-48', w/'sample-74'), ('tech-1', w/'sample-53', w/'sample-89')]
for r in fb:
    if r.get('preferred_alias') in ('A','B'):
        q=r['question']; win=r['preferred_original_label']
        lose=[m['original_label'] for m in key if m['question']==q and m['original_label']!=win][0]
        L.append((f'unslop-{q}', u/win, u/lose))
def run(t):
    n,x,y=t
    src=json.load(open(x.parent.parent/'control/assignment.json')) if False else None
    return n, both_orders((x/'project/output.md').read_text(), (y/'project/output.md').read_text(), repeats=4)
out={}
with cf.ThreadPoolExecutor(6) as p:
    for n,v in p.map(run,L): out[n]=v
Path(__file__).with_name('calibration.json').write_text(json.dumps(out,ensure_ascii=False,indent=1))
agree=0;tot=0
for n,v in out.items():
    picks=[i.get('pick','ERR') for i in v]; tot+=len(picks); agree+=picks.count('x')
    print(n,'user_choice=x','judge:',picks,'| terms x/y',[ (len(i.get('x_terms',[])),len(i.get('y_terms',[]))) for i in v])
print('agreement',agree,'/',tot)
print(json.dumps({n:v[0].get('reason') for n,v in out.items()},ensure_ascii=False,indent=0))
print('sample terms tech', out['tech-1'][0].get('y_terms'), out['bro-1'][0].get('y_terms'))
