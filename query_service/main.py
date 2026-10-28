"""Internal SQL planner. Demo is deterministic; LLM mode is opt-in."""
import os, re
import httpx
import sqlglot
from sqlglot import exp
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app=FastAPI(title="AskDB query planner")
SCHEMA="""analytics.customers(customer_id integer, name text, region text);
analytics.orders(order_id integer, customer_id integer references customers, order_date date, status text);
analytics.order_items(order_id integer references orders, product text, quantity integer, unit_price numeric).
Revenue = SUM(quantity * unit_price); include only orders where status = 'completed'.
Use only these tables. Return exactly one PostgreSQL SELECT query. Do not use WITH, subqueries, comments, or system functions."""
TABLES={'customers','orders','order_items'}
FUNCTIONS={'sum','avg','count','min','max','round','date_trunc','coalesce','row_number','rank','dense_rank','lag','lead','abs','lower','upper'}
SAMPLES=[
 ('Revenue by region',"SELECT c.region, SUM(i.quantity*i.unit_price) AS revenue FROM analytics.orders o JOIN analytics.customers c ON c.customer_id=o.customer_id JOIN analytics.order_items i ON i.order_id=o.order_id WHERE o.status='completed' GROUP BY c.region ORDER BY revenue DESC"),
 ('Monthly revenue',"SELECT DATE_TRUNC('month',o.order_date)::date AS month, SUM(i.quantity*i.unit_price) AS revenue FROM analytics.orders o JOIN analytics.order_items i ON i.order_id=o.order_id WHERE o.status='completed' GROUP BY 1 ORDER BY 1"),
 ('Top products by revenue',"SELECT i.product, SUM(i.quantity*i.unit_price) AS revenue FROM analytics.orders o JOIN analytics.order_items i ON i.order_id=o.order_id WHERE o.status='completed' GROUP BY i.product ORDER BY revenue DESC LIMIT 5"),
 ('Order counts by status',"SELECT status, COUNT(*) AS orders FROM analytics.orders GROUP BY status ORDER BY status"),
 ('Top customers by revenue',"SELECT c.name, SUM(i.quantity*i.unit_price) AS revenue FROM analytics.customers c JOIN analytics.orders o ON o.customer_id=c.customer_id JOIN analytics.order_items i ON i.order_id=o.order_id WHERE o.status='completed' GROUP BY c.customer_id,c.name ORDER BY revenue DESC LIMIT 5"),
 ('Customer count by region',"SELECT region, COUNT(*) AS customers FROM analytics.customers GROUP BY region ORDER BY region")]
ALIASES={
 'revenue by region':0,'regional revenue':0,'sales by region':0,'show revenue by region':0,
 'monthly revenue':1,'revenue by month':1,'monthly sales':1,'show monthly revenue':1,
 'top products by revenue':2,'top products':2,'best selling products':2,
 'order counts by status':3,'orders by status':3,'order status counts':3,
 'top customers by revenue':4,'top customers':4,'highest spending customers':4,
 'customer count by region':5,'customers by region':5,'regional customer counts':5}

class Request(BaseModel):
 question:str=Field(min_length=3,max_length=500)
class ValidateRequest(BaseModel):
 sql:str=Field(min_length=1,max_length=12000)

def validate_sql(sql:str)->str:
 if len(sql)>12000 or any(s in sql for s in ('--','/*','*/')):
  raise ValueError('Comments and oversized queries are not supported.')
 statements=sqlglot.parse(sql,read='postgres')
 if len(statements)!=1 or not isinstance(statements[0],exp.Select):
  raise ValueError('Exactly one SELECT is required.')
 tree=statements[0]
 if tree.args.get('into') or tree.args.get('locks') or tree.args.get('with') or tree.find(exp.Subquery) or tree.find(exp.With):
  raise ValueError('SELECT INTO, locking, CTEs and subqueries are not supported.')
 if len(list(tree.find_all(exp.Select)))!=1:
  raise ValueError('Nested queries are not supported.')
 tables=list(tree.find_all(exp.Table))
 if not tables or len(tables)>3:
  raise ValueError('Use one to three approved analytics tables.')
 for table in tables:
  if table.name not in TABLES or table.db!='analytics' or table.catalog:
   raise ValueError('Only approved analytics tables are permitted.')
 for func in tree.find_all(exp.Func):
  # CAST is allowed only to DATE for the DATE_TRUNC month demo.
  if isinstance(func,exp.Cast):
   if func.args['to'].sql(dialect='postgres').upper()!='DATE':
    raise ValueError('Only DATE casts are supported.')
   continue
  name=func.name.lower() if isinstance(func,exp.Anonymous) else func.sql_name().lower()
  if name not in FUNCTIONS and name!='timestamp_trunc':
   raise ValueError('Unsupported SQL function: '+name)
 # An outer limit controls returned rows even if a generated query has no LIMIT.
 return tree.sql(dialect='postgres',pretty=True).rstrip(';')

@app.get('/health')
def health():return {'status':'ok'}
@app.get('/schema')
def schema():return {'schema':SCHEMA,'examples':[x[0] for x in SAMPLES],'templates':[{'name':name,'sql':validate_sql(sql)} for name,sql in SAMPLES], 'mode':os.getenv('QUERY_MODE','demo')}
@app.post('/validate')
def validate(body:ValidateRequest):
 try:return {'sql':validate_sql(body.sql)}
 except Exception as e:raise HTTPException(422,detail=str(e))
@app.post('/plan')
async def plan(body:Request):
 mode=os.getenv('QUERY_MODE','demo')
 if mode=='demo':
  key=re.sub(r'[?!.,]+$','',body.question.strip().lower())
  if key not in ALIASES:raise HTTPException(422,detail='Demo mode supports the six example questions. Enable LLM mode for other questions.')
  sql=SAMPLES[ALIASES[key]][1]
 elif mode=='llm':
  api_key=os.getenv('LLM_API_KEY','')
  if not api_key:raise HTTPException(503,detail='LLM mode is not configured.')
  # Configured by the server operator, never by user input.
  url=os.getenv('LLM_BASE_URL','https://api.openai.com/v1').rstrip('/')+'/chat/completions'
  try:
   async with httpx.AsyncClient(timeout=25) as client:
    result=await client.post(url,headers={'Authorization':'Bearer '+api_key},json={
      'model':os.getenv('LLM_MODEL','gpt-4.1-mini'),'temperature':0,
      'messages':[{'role':'system','content':SCHEMA},{'role':'user','content':body.question}]})
    result.raise_for_status()
    sql=result.json()['choices'][0]['message']['content'].strip()
    if sql.startswith('```'):sql=re.sub(r'^```(?:sql)?\s*|\s*```$','',sql)
  except Exception:raise HTTPException(502,detail='Model provider unavailable or returned an invalid response.')
 else:raise HTTPException(503,detail='Unsupported planner mode.')
 try:sql=validate_sql(sql)
 except Exception:raise HTTPException(422,detail='Generated query failed the SQL safety policy.')
 return {'sql':sql,'mode':mode}
