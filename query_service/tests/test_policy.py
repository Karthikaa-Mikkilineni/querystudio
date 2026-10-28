import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from fastapi.testclient import TestClient
from main import app, validate_sql, SAMPLES, ALIASES
client=TestClient(app)
@pytest.mark.parametrize('question',list(ALIASES))
def test_demo_plans(question):
 r=client.post('/plan',json={'question':question})
 assert r.status_code==200
 assert r.json()['mode']=='demo'
 validate_sql(r.json()['sql'])
@pytest.mark.parametrize('sql',[
 'DELETE FROM analytics.orders',
 'SELECT * FROM analytics.orders; DROP TABLE analytics.orders',
 'SELECT * FROM pg_catalog.pg_authid',
 'SELECT * FROM orders',
 'SELECT pg_sleep(5) FROM analytics.orders',
 'SELECT * INTO analytics.copy FROM analytics.orders',
 'SELECT * FROM analytics.orders FOR UPDATE',
 'WITH x AS (DELETE FROM analytics.orders RETURNING *) SELECT * FROM x',
 'SELECT * FROM analytics.orders -- comment',
 'SELECT * FROM analytics.orders UNION SELECT * FROM analytics.customers',
 'SELECT (SELECT 1) FROM analytics.orders',
 "SELECT current_setting('server_version') FROM analytics.orders",
 "SELECT CAST(order_id AS TEXT) FROM analytics.orders",
 'SELECT * FROM analytics.orders CROSS JOIN generate_series(1,100000)',
 'SELECT * FROM analytics.orders o JOIN analytics.orders p ON true JOIN analytics.orders q ON true JOIN analytics.orders r ON true',
 'COPY analytics.orders TO STDOUT',
 'SELECT * FROM public.orders',
 'SELECT 1',
])
def test_policy_rejects(sql):
 with pytest.raises(Exception):validate_sql(sql)
def test_unknown_demo_question():
 assert client.post('/plan',json={'question':'delete everything'}).status_code==422
def test_request_bounds():
 assert client.post('/plan',json={'question':'x'}).status_code==422
 assert client.post('/plan',json={'question':'x'*501}).status_code==422
@pytest.mark.parametrize('_,sql',SAMPLES)
def test_examples_valid(_,sql):assert validate_sql(sql)

def test_missing_llm_key(monkeypatch):
 monkeypatch.setenv('QUERY_MODE','llm');monkeypatch.delenv('LLM_API_KEY',raising=False)
 assert client.post('/plan',json={'question':'Revenue by region'}).status_code==503

def test_invalid_mode(monkeypatch):
 monkeypatch.setenv('QUERY_MODE','invalid')
 assert client.post('/plan',json={'question':'Revenue by region'}).status_code==503

@pytest.mark.parametrize('generated,status',[
 (SAMPLES[0][1],200),
 ('```sql\n'+SAMPLES[0][1]+'\n```',200),
 ('DELETE FROM analytics.orders',422),
 ('SELECT pg_sleep(10) FROM analytics.orders',422),
])
def test_mocked_llm(monkeypatch,generated,status):
 import main
 monkeypatch.setenv('QUERY_MODE','llm');monkeypatch.setenv('LLM_API_KEY','test-only')
 class Response:
  def raise_for_status(self):pass
  def json(self):return {'choices':[{'message':{'content':generated}}]}
 class FakeClient:
  def __init__(self,**kwargs):pass
  async def __aenter__(self):return self
  async def __aexit__(self,*args):pass
  async def post(self,*args,**kwargs):return Response()
 monkeypatch.setattr(main.httpx,'AsyncClient',FakeClient)
 assert client.post('/plan',json={'question':'Revenue by region'}).status_code==status

@pytest.mark.parametrize('sql',[
 "SELECT order_id,ROW_NUMBER() OVER (ORDER BY order_date) AS row_num FROM analytics.orders",
 "SELECT c.region,COUNT(*) AS total FROM analytics.orders o JOIN analytics.customers c ON o.customer_id=c.customer_id WHERE o.order_date >= '2025-06-01' GROUP BY c.region HAVING COUNT(*) > 5 ORDER BY total DESC",
 "SELECT LOWER(name) AS customer_name FROM analytics.customers WHERE region='West' LIMIT 10",
 "SELECT product,AVG(unit_price) AS avg_price FROM analytics.order_items GROUP BY product",
])
def test_custom_analytics_queries(sql):assert validate_sql(sql)

def test_schema_describes_templates():
 r=client.get('/schema').json()
 assert len(r['templates'])==6 and r['mode']=='demo'
 assert all(set(t)=={'name','sql'} for t in r['templates'])
