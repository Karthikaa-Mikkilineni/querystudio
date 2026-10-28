// Browser-level behavior against the built Angular app. Fault cases intercept HTTP explicitly.
const {chromium}=require('../web/node_modules/playwright');const fs=require('fs');
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});const checks=[];
 try{
  const page=await browser.newPage();await page.goto(process.env.ASKDB_URL||'http://127.0.0.1:8080');await page.getByLabel('SQL query').waitFor();
  await page.getByLabel('SQL query').fill('SELECT customer_id,name,region FROM analytics.customers ORDER BY customer_id');
  await page.getByRole('button',{name:/Run query/}).click();await page.getByText('Executed in',{exact:false}).waitFor();
  if(!(await page.locator('tbody tr').first().innerText()).includes('Customer 1'))throw Error('Query edit not applied');checks.push('edited SQL reaches real endpoint');
  await page.getByLabel('Saved query name').fill('Reload regression');await page.getByRole('button',{name:/Save query/}).click();await page.getByRole('status').waitFor();await page.reload();await page.getByRole('button',{name:/Saved queries/}).click();await page.getByRole('heading',{name:'Reload regression',exact:true}).waitFor();checks.push('saved query survives page reload');
  await page.getByRole('button',{name:/Query studio/}).click();
  // Deterministic delayed response tests UI cancellation only, not database cancellation.
  let release;const unblock=new Promise(r=>release=r);let seen;const requested=new Promise(r=>seen=r);
  await page.route('**/api/query',async route=>{seen();await unblock;await route.fulfill({json:{columns:['value'],rows:[[999]],durationMs:1,estimatedCost:0,sql:'late',mode:'sql',requestId:'late',truncated:false}}).catch(()=>{});});
  await page.getByRole('button',{name:/Run query/}).click();await requested;await page.getByRole('button',{name:'Cancel',exact:true}).click();release();await page.getByRole('status').filter({hasText:'Request cancelled'}).waitFor();await page.waitForTimeout(100);
  if(await page.getByText('Executed in',{exact:false}).count())throw Error('Cancelled response overwritten state');checks.push('cancelled UI request ignores late response');await page.unroute('**/api/query');
  await page.route('**/api/query',r=>r.fulfill({status:504,json:{error:'Request timed out or was cancelled.'}}));await page.getByRole('button',{name:/Run query/}).click();await page.getByRole('alert').filter({hasText:'timed out'}).waitFor();checks.push('HTTP timeout shown accessibly');await page.unroute('**/api/query');
  await page.getByLabel('Dismiss error').click();
  await page.route('**/api/query',r=>r.fulfill({json:{columns:['label','value'],rows:[['=1+1',0],['a,b',2],['quote"value',3]],durationMs:1,estimatedCost:0,sql:'fixture',mode:'sql',requestId:'csv',truncated:false}}));await page.getByRole('button',{name:/Run query/}).click();await page.getByText('Executed in',{exact:false}).waitFor();
  const promise=page.waitForEvent('download');await page.getByRole('button',{name:/Export CSV/}).click();const dl=await promise;const text=fs.readFileSync(await dl.path(),'utf8');if(!text.includes('"\'=1+1","0"')||!text.includes('"a,b","2"')||!text.includes('"quote""value","3"'))throw Error('Unsafe or malformed CSV');checks.push('CSV formula neutralization, zero values, commas and quotes');await page.unroute('**/api/query');
  console.log(JSON.stringify({status:'passed',checks,scope:'Two real API flows; three deterministic HTTP-interception browser checks. Cancellation is UI behavior, not a database cancellation guarantee.'},null,2));fs.writeFileSync('evidence/maintenance/browser-regressions.json',JSON.stringify({status:'passed',checks},null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
