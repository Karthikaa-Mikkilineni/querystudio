"""Run against the Compose app: python3 scripts/smoke_test.py."""
import json,urllib.request,urllib.error
base='http://127.0.0.1:8080'
def request(path,body=None,method=None):
 data=None if body is None else json.dumps(body).encode()
 req=urllib.request.Request(base+path,data=data,method=method,headers={'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=35) as r:
   raw=r.read();return r.status,json.loads(raw) if raw else None
 except urllib.error.HTTPError as e:return e.code,json.loads(e.read())
assert request('/api/health')[0]==200
status,schema=request('/api/schema');assert status==200 and len(schema['tables'])==3
for example in schema['examples']:
 status,r=request('/api/query',{'text':example});assert status==200,(example,r)
 assert r['columns'] and r['rows'] and r['mode']=='demo'
status,r=request('/api/query',{'sql':'SELECT * FROM analytics.orders ORDER BY order_id'})
assert status==200 and len(r['rows'])==200 and r['truncated']
for sql in ['DELETE FROM analytics.orders','SELECT pg_sleep(5) FROM analytics.orders','SELECT * FROM pg_catalog.pg_authid']:
 assert request('/api/query',{'sql':sql})[0]==422
assert request('/api/query',{'text':''})[0]==400
assert request('/api/query',{'text':'Delete the database'})[0]==422
assert request('/api/plan',{'text':'revenue by region'})[0]==200
status,saved=request('/api/saved',{'name':'Smoke test query','sql':'SELECT name,region FROM analytics.customers'})
assert status==201
assert any(x['id']==saved['id'] for x in request('/api/saved')[1])
assert request('/api/saved/'+saved['id'],method='DELETE')[0]==204
assert request('/api/history')[0]==200
print('PASS: demo/custom queries, row cap, blocked SQL, draft preview, schema, saved-query create/list/delete, history')
