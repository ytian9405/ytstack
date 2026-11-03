from pathlib import Path
import json,hashlib,datetime
R=Path(__file__).resolve().parent;B=R.parent/'blind'
weights=[5,6,5,5,5,5,4,6,4,6,5,4,10,8,7,10,5]
ids=[f'B{i:02}' for i in range(1,13)]+['R01','R02','R03','E01','E02']
mutmap=[[1,2],[3,4,5],[6,7],[8,9],[10],[11,12],[13],[14,15],[16],[17,18,19],[20,21],[22]]
reasons=['原样标题/类别含 Unicode 与空格的完整记录断言','正常金额和 0/-1/1.5/abc 拒绝、stderr、状态不变断言','首 id、连续新增和 void 后新增 id 断言','独立子进程写读、存在状态文件、多次新增保留历史','空与多记录列表，作废记录仍可见','void 保留目标字段和持久化；其他记录完整性见具体备注','重复 void 成功且状态字节不变','空、混合有效/作废、全部作废的 count 和 total_cents','多类别、同类别累计和作废排除','空白输入/未知 id 非零退出、stderr 非空、状态字节和重读数据不变','缺失状态读取及不存在嵌套目录首次写入','共用成功调用帮助函数解析完整 stdout JSON，覆盖四种命令','技能说明有前提、根目录、原始命令、通过/失败标准、证据保存和范围','标准库独立 TemporaryDirectory；两轮原交付命令通过且临时副本删除','旧 smoke 字节保留并由发现入口执行；行为命名及文档映射支持定位/扩展','作者原始运行日志与机器回执核对命令、版本、退出结果；不要求额外平台轨迹','原始日志、作者报告、独立复跑结论一致；明确非穷尽变异及未覆盖范围']
for label in ['run-28','run-17']:
 p=B/label;obj=json.loads((p/'objective/objective.json').read_text());items=[]
 for i,(key,w,reason) in enumerate(zip(ids,weights,reasons)):
  evidence=['project/tests/test_behavior.py'] if key.startswith('B') else ['project/.agents/skills/test-ledger-lite/SKILL.md',f'../../review/{label}-rerun-1',f'../../review/{label}-rerun-2']
  if key.startswith('B'):evidence += [f'objective/M{m:02}.stderr.log' for m in mutmap[i]]
  if key.startswith('E'):evidence += ['DELIVERY.md','project/evidence/20261102T123809463314Z/receipt.json','project/evidence/20261102T123809463314Z/baseline.log','project/evidence/RESULTS.md'] if label=='run-28' else ['DELIVERY.md','project/test-results/verification.json','project/test-results/baseline.log','project/test-results/RESULTS.md']
  level=2
  if label=='run-28' and key=='B06':
   level=1;reason='目标记录字段和 void 持久化有精确断言；M12 由 LL04 汇总间接检出，但 void 多记录时没有重读并比较其他记录的标题、类别等完整字段。不改变其他记录这一合同要求仅部分覆盖。'
  items.append({'id':key,'weight':w,'level':level,'score':w*level/2,'reason':reason,'evidence':evidence})
 mutations=[]
 for n in range(1,23):
  k=f'M{n:02}';s=(p/'objective'/f'{k}.stderr.log').read_text();ls=[x for x in s.splitlines() if x.startswith(('FAIL:','ERROR:','AssertionError:','json.decoder.')) or 'self.assert' in x]
  why='相应输入/状态断言失败，已核对补丁与断言目标。'
  if n==8:why='LL02 在 add 成功后断言状态文件存在失败，直接证明未持久化；其他用例的缺文件错误不作为检出依据。'
  if n==12 and label=='run-28':why='LL04 在仅作废第4条后预期 count=3/total=2300，实际全为0；补丁把所有记录作废，属目标行为的下游可观察检出。只证明非目标记录有效性，非全部字段完整性。'
  if n==20:why='缺失状态 list 的成功退出断言失败，FileNotFoundError 来自目标缺失状态语义；属于目标行为，不是测试导入错误。'
  if n==21:why='首次写入不存在的嵌套父目录失败，目标 mkdir 缺失导致 FileNotFoundError；属于目标行为。'
  if n==22:why='完整 stdout 的 json.loads 因前置 INFO 杂音失败，JSONDecodeError 正是目标 JSON 输出合同违例，算有效检出。'
  mutations.append({'id':k,'valid_kill':True,'evidence':f'objective/{k}.stderr.log','patch':f'objective/{k}.patch','witness':ls[:7],'reason':why})
 result={'label':label,'framework_version':'1.0','blind':True,'group_guess_before_reading':'UNKNOWN','initial_confidence':0,'quality_score':sum(i['score'] for i in items),'quality_interval':[sum(i['score'] for i in items)]*2,'items':items,'major_gates':{f'G{i:02}':'NOT_TRIGGERED' for i in range(1,6)},'defects':[],'mutation_review':mutations,'K_old':['M20','M22'],'K_added':'UNKNOWN','K_added_note':'未把新增测试作为独立入口另跑全部22变异；现有最终运行日志均有新增测试目标失败证据，但不冒充独立拆分实验。','K_final':[f'M{i:02}' for i in range(1,23)],'net_added_kills':[f'M{i:02}' for i in range(1,22) if i!=20],'net_added_count':20,'regressions':[],'original_inputs_byte_equal':{f:(p/'project'/f).read_bytes()==(B/'baseline-project'/f).read_bytes() for f in ['README.md','expense_cli.py','tests/test_smoke.py']},'clean_reruns':[r for r in json.loads((R/'rerun-records.json').read_text()) if r['label']==label],'cost':json.loads((p/'COST.json').read_text()),'scope':'仅本项目公开合同、固定22个变异与当前Linux/Python3.12.3；不证明穷尽缺陷或跨平台。旧 smoke 检出2个，净新增20个。成本未知，不排名效率。','locked_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 if label=='run-28':result['defects']=[{'defect_id':'run-28-D01','owner':'B06','reason':'对多记录 void 后其他记录原字段的完整保留未直接核验；汇总仅检查有效数量金额。','score_impact':2.5,'cross_impact':'不再扣 B08/B09/R/E；M12 仍算有效检出。'}]
 (R/f'{label}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(R/'first-batch-lock.json').write_text(json.dumps({'blind':True,'files':{f'{l}.json':hashlib.sha256((R/f'{l}.json').read_bytes()).hexdigest() for l in ['run-28','run-17']}},indent=2)+'\n')
print([(l,json.loads((R/f'{l}.json').read_text())['quality_score']) for l in ['run-28','run-17']])
