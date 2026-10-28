"""Reproduce app checks in one local network namespace. No Docker/hosted release implied."""
import os,time,subprocess,json,shutil
from pathlib import Path
import httpx
root=Path(__file__).resolve().parents[1];os.chdir(root);evidence=root/'evidence/maintenance';evidence.mkdir(exist_ok=True)
env={**os.environ,'ASPNETCORE_URLS':'http://127.0.0.1:8080','PlannerUrl':'http://127.0.0.1:8001','WorkspacePath':'/tmp/apollo-qa-workspace','ConnectionStrings__Analytics':'Host=127.0.0.1;Port=55441;Database=postgres;Username=askdb_reader;Password=local-demo-reader;SSL Mode=Disable','Logging__LogLevel__Default':'Warning'}
shutil.rmtree(env['WorkspacePath'],ignore_errors=True)
children=[];logs=[]
def start(args,cwd,name,childenv=env):
 log=open(evidence/(name+'.log'),'w');logs.append(log);p=subprocess.Popen(args,cwd=cwd,env=childenv,stdout=log,stderr=log);children.append(p);return p
def ready(c,path):
 for _ in range(150):
  try:
   if c.get(path).status_code==200:return
  except httpx.HTTPError:pass
  time.sleep(.1)
 raise RuntimeError('Service not ready: '+path)
def api(build,name):return start(['/tmp/apollo-dotnet/dotnet',str(Path(build)/'AskDb.Api.dll')],build,name)
def run(args,report):
 with open(evidence/report,'w') as out:r=subprocess.run(args,stdout=out,stderr=subprocess.STDOUT)
 print(report, 'passed' if r.returncode==0 else 'FAILED',flush=True)
 if r.returncode:print((evidence/report).read_text()[-5000:]);raise RuntimeError(report)
try:
 start(['node','scripts/serve_pglite.mjs'],root,'database')
 start(['/tmp/apollo-python/bin/python','-m','uvicorn','main:app','--port','8001'],root/'query_service','planner')
 active=api('/tmp/apollo-optimized-build','api')
 with httpx.Client(base_url='http://127.0.0.1:8080',trust_env=False,timeout=10) as c:
  ready(c,'/api/schema')
  run(['/tmp/apollo-python/bin/python','-m','pytest','scripts/qa/test_endpoints.py','-q'],'endpoint-tests.txt')
  run(['node','scripts/browser_test.cjs'],'browser-existing.txt')
  run(['node','scripts/browser_regressions.cjs'],'browser-regressions.txt')
  # Failure injection at atomic-write boundary: failed save must not enter memory snapshot.
  path=Path(env['WorkspacePath'])/'workspace.json.tmp';path.mkdir()
  body={'name':'failed-write-test','sql':'SELECT * FROM analytics.customers'}
  r=c.post('/api/saved',json=body);assert r.status_code==500
  assert not any(x['name']=='failed-write-test' for x in c.get('/api/saved').json());path.rmdir()
  r=c.post('/api/saved',json=body);assert r.status_code==201;marker=r.json()['id']
  steps=['failed atomic write leaves snapshot unchanged','successful retry persists saved query']
  for build,label in [('/tmp/apollo-baseline-build','rollback'),('/tmp/apollo-optimized-build','redeploy')]:
   active.terminate();active.wait(timeout=10);active=api(build,'api-'+label);ready(c,'/api/schema')
   assert any(x['id']==marker for x in c.get('/api/saved').json());assert c.get('/api/history').json()
   assert c.post('/api/query',json={'sql':'SELECT * FROM analytics.customers'}).status_code==200
   assert c.get('/').status_code==200
   steps.append(label+' health, schema, UI, query smoke and persistent state')
  (evidence/'local-release-rehearsal.json').write_text(json.dumps({'status':'passed','target':'local loopback ASP.NET processes; release directories share workspace file; not Docker or production','steps':steps},indent=2))
  print('local release, persistence and failure-injection checks passed',flush=True)
finally:
 for p in reversed(children):
  if p.poll() is None:p.terminate()
 for p in children:
  try:p.wait(timeout=5)
  except subprocess.TimeoutExpired:p.kill()
 for log in logs:log.close()
