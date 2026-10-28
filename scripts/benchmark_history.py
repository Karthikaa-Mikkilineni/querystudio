"""Same HTTP history workload; alternating baseline/optimized process rounds, raw samples retained."""
import json,os,sys,subprocess,time,hashlib,statistics,platform
from pathlib import Path
import httpx
root=Path(__file__).resolve().parents[1];workspace=Path('/tmp/apollo-history-benchmark');workspace.mkdir(exist_ok=True)
sql='SELECT order_id FROM analytics.orders WHERE status=\'completed\''+' '*4000
state={'history':[dict(requestId=str(i),sql=sql,mode='sql',status='ok',rowCount=200,durationMs=5,timestamp='2026-10-27T00:00:00Z') for i in range(100)],'saved':[dict(id=f'00000000-0000-0000-0000-{i:012}',name=f'Analysis {i}',sql=sql,createdAt='2026-10-27T00:00:00Z') for i in range(100)]}
(workspace/'workspace.json').write_text(json.dumps(state));samples=[];expected=None
for turn in range(6):
 modes=['baseline','optimized'] if turn%2==0 else ['optimized','baseline']
 for mode in modes:
  build=Path('/tmp/apollo-'+mode+'-build');env={**os.environ,'ASPNETCORE_URLS':'http://127.0.0.1:8082','WorkspacePath':str(workspace),'ConnectionStrings__Analytics':'Host=127.0.0.1;Port=55441;Database=postgres;Username=askdb_reader;Password=local-demo-reader;SSL Mode=Disable','PlannerUrl':'http://127.0.0.1:8001','Logging__LogLevel__Default':'Warning'}
  log=open('/tmp/apollo-benchmark-server.log','a');proc=subprocess.Popen(['/tmp/apollo-dotnet/dotnet',str(build/'AskDb.Api.dll')],cwd=build,env=env,stdout=log,stderr=log)
  try:
   with httpx.Client(timeout=5,trust_env=False) as c:
    for _ in range(100):
     try:
      if c.get('http://127.0.0.1:8082/api/health').status_code==200:break
     except httpx.HTTPError:pass
     time.sleep(.05)
    else:raise RuntimeError('Application did not start')
    for _ in range(8):c.get('http://127.0.0.1:8082/api/history').raise_for_status()
    for i in range(40):
     start=time.perf_counter_ns();r=c.get('http://127.0.0.1:8082/api/history');elapsed=(time.perf_counter_ns()-start)/1e6;r.raise_for_status();digest=hashlib.sha256(r.content).hexdigest()
     expected=expected or digest;assert digest==expected
     assert len(r.json())==50
     samples.append(dict(round=turn,mode=mode,index=i,ms=elapsed,bytes=len(r.content),sha256=digest))
  finally:proc.terminate();proc.wait(timeout=10);log.close()
def stats(mode):
 x=sorted(p['ms'] for p in samples if p['mode']==mode);return dict(n=len(x),median_ms=statistics.median(x),p95_ms=x[int(.95*len(x))-1])
out={'scope':'localhost GET /api/history, warm sequential client, single process, 100 history + 100 saved entries, ~4KB SQL, not DB or production load','environment':platform.platform(),'state_bytes':(workspace/'workspace.json').stat().st_size,'stats':{m:stats(m) for m in ['baseline','optimized']},'samples':samples}
(root/'evidence/maintenance/history-benchmark.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='samples'},indent=2))
