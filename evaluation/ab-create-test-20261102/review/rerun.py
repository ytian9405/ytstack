import os,json,pathlib,shutil,subprocess,tempfile,time,hashlib,platform
ROOT=pathlib.Path(__file__).resolve().parent
BLIND=ROOT.parent/'blind'
records=[]
for label,helper in [('run-28','.agents/skills/test-ledger-lite/scripts/verify.py'),('run-17','scripts/verify_tests.py')]:
 for trial in [1,2]:
  out=ROOT/f'{label}-rerun-{trial}';out.mkdir(exist_ok=True)
  with tempfile.TemporaryDirectory(prefix=f'{label}-scratch-',dir=ROOT) as tmp:
   scratch=pathlib.Path(tmp);project=scratch/'project';shutil.copytree(BLIND/label/'project',project)
   env=dict(os.environ,TMPDIR=str(scratch),PYTHONDONTWRITEBYTECODE='1')
   for idx,cmd in enumerate([['python3','-m','unittest','discover','-s','tests','-v'],['python3',helper]]):
    start=time.time();r=subprocess.run(cmd,cwd=project,env=env,capture_output=True,text=True,timeout=60)
    stem=f'command-{idx+1}';(out/(stem+'.stdout.log')).write_text(r.stdout);(out/(stem+'.stderr.log')).write_text(r.stderr)
    records.append({'label':label,'trial':trial,'command':cmd,'cwd':str(project),'exit_code':r.returncode,'elapsed_seconds':time.time()-start,'python':platform.python_version(),'platform':platform.platform(),'target_sha256':hashlib.sha256((project/'expense_cli.py').read_bytes()).hexdigest(),'log_directory':str(out),'scratch':str(scratch)})
   evidence=project/('evidence' if label=='run-28' else 'test-results');shutil.copytree(evidence,out/'generated-evidence',dirs_exist_ok=True)
   (out/'remaining-owned-paths.json').write_text(json.dumps([str(p.relative_to(scratch)) for p in scratch.iterdir()],indent=2))
  for r in records:
   if r['scratch']==tmp:r['scratch_removed']=not pathlib.Path(tmp).exists()
  print(label,trial,[(r['exit_code'],round(r['elapsed_seconds'],2)) for r in records if r['label']==label and r['trial']==trial],flush=True)
(ROOT/'rerun-records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
