"""HTTP integration against the running ASP.NET API; real PGlite path plus isolated dependency-fault tests."""
import os,json,time,threading,subprocess
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import httpx,pytest
BASE=os.getenv('ASKDB_URL','http://127.0.0.1:8080')
@pytest.fixture
def client():
 with httpx.Client(base_url=BASE,trust_env=False,timeout=10) as c:yield c
@pytest.mark.parametrize('path,body,code',[
 ('/api/query',{},400),('/api/query',{'text':'x'},400),('/api/query',{'sql':'x'*12001},400),
 ('/api/query',{'sql':'DELETE FROM analytics.orders'},422),('/api/query',{'sql':'SELECT pg_sleep(5) FROM analytics.orders'},422),
 ('/api/query',{'sql':'SELECT missing_column FROM analytics.orders'},422),('/api/query',{'sql':'SELECT * FROM pg_catalog.pg_authid'},422),
 ('/api/plan',{'text':'x'},400),('/api/plan',{'text':'drop the database'},422),
 ('/api/saved',{'name':'','sql':'SELECT * FROM analytics.orders'},400),('/api/saved',{'name':'x'*81,'sql':'SELECT * FROM analytics.orders'},400),
 ('/api/saved',{'name':'unsafe','sql':'DELETE FROM analytics.orders'},422)])
def test_http_errors(client,path,body,code):
 r=client.post(path,json=body);assert r.status_code==code;assert isinstance(r.json()['error'],str)
def test_schema(client):
 r=client.get('/api/schema');assert r.status_code==200;assert len(r.json()['tables'])==3
def test_valid_query_history_and_cap(client):
 r=client.post('/api/query',json={'sql':'SELECT * FROM analytics.orders ORDER BY order_id'});assert r.status_code==200
 v=r.json();assert len(v['rows'])==200 and v['truncated'];assert v['columns'][0]=='order_id'
 h=client.get('/api/history').json();assert any(x['requestId']==v['requestId'] and x['rowCount']==200 and x['status']=='ok' for x in h)
def test_saved_lifecycle(client):
 r=client.post('/api/saved',json={'name':'HTTP integration query','sql':'SELECT * FROM analytics.customers'});assert r.status_code==201
 v=r.json();assert r.headers['location'].endswith(v['id']);assert any(x['id']==v['id'] for x in client.get('/api/saved').json())
 assert client.delete('/api/saved/'+v['id']).status_code==204
 assert client.delete('/api/saved/'+v['id']).status_code==404
def test_malformed_json(client):
 assert client.post('/api/query',content='{',headers={'Content-Type':'application/json'}).status_code==400
class FaultPlanner(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_POST(self):
  if self.headers.get('Transfer-Encoding','').lower()=='chunked':
   data=b''
   while True:
    n=int(self.rfile.readline().strip(),16)
    if not n:self.rfile.readline();break
    data+=self.rfile.read(n);self.rfile.read(2)
  else:data=self.rfile.read(int(self.headers.get('Content-Length','0')))
  body=json.loads(data)
  if 'timeout' in str(body):time.sleep(.6)
  else:self.send_response(502);self.end_headers();return
  try:self.send_response(200);self.end_headers();self.wfile.write(b'{}')
  except BrokenPipeError:pass
@pytest.fixture(scope='module')
def faulty_api(tmp_path_factory):
 server=ThreadingHTTPServer(('127.0.0.1',8003),FaultPlanner);threading.Thread(target=server.serve_forever,daemon=True).start()
 build=Path(os.getenv('ASKDB_BUILD','/tmp/apollo-optimized-build'));workspace=tmp_path_factory.mktemp('fault-workspace')
 env={**os.environ,'ASPNETCORE_URLS':'http://127.0.0.1:8083','PlannerUrl':'http://127.0.0.1:8003','PlannerTimeoutSeconds':'0.15','WorkspacePath':str(workspace),'ConnectionStrings__Analytics':'Host=127.0.0.1;Port=55441;Database=postgres;Username=askdb_reader;Password=local-demo-reader;SSL Mode=Disable','Logging__LogLevel__Default':'None'}
 proc=subprocess.Popen([os.getenv('ASKDB_DOTNET','/tmp/apollo-dotnet/dotnet'),str(build/'AskDb.Api.dll')],env=env,cwd=build,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 with httpx.Client(base_url='http://127.0.0.1:8083',trust_env=False,timeout=5) as c:
  try:
   for _ in range(100):
    try:
     if c.get('/api/health').status_code==200:break
    except httpx.HTTPError:pass
    time.sleep(.05)
   else:raise RuntimeError('Fault API startup failed')
   yield c
  finally:proc.terminate();proc.wait(timeout=5);server.shutdown();server.server_close()
@pytest.mark.parametrize('path,body',[
 ('/api/query',{'sql':'timeout'}),('/api/plan',{'text':'timeout'}),('/api/saved',{'name':'timeout','sql':'timeout'})])
def test_dependency_timeout(faulty_api,path,body):
 r=faulty_api.post(path,json=body);assert r.status_code==504;assert 'time' in r.json()['error']
@pytest.mark.parametrize('path,body',[
 ('/api/query',{'sql':'dependency unavailable'}),('/api/plan',{'text':'dependency unavailable'}),('/api/saved',{'name':'unavailable','sql':'dependency unavailable'})])
def test_dependency_unavailable(faulty_api,path,body):
 r=faulty_api.post(path,json=body);assert r.status_code==503;assert r.json()['error']
def test_failed_request_history(faulty_api):
 rows=faulty_api.get('/api/history').json();assert rows and all(x['status']=='failed' for x in rows)
