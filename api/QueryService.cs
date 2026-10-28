using System.Diagnostics;
public sealed class QueryService(PlannerClient planner,QueryRepository repository,WorkspaceStore workspace,ILogger<QueryService> logger){
 public async Task<QueryResult> Run(QueryRequest request,string id,CancellationToken ct){
  var watch=Stopwatch.StartNew();var mode=string.IsNullOrWhiteSpace(request.Sql)?"demo":"sql";var sql="";var status="failed";var rowCount=0;
  try{
   if(mode=="sql")sql=await planner.Validate(request.Sql!,ct);
   else{var plan=await planner.Plan(request.Text!.Trim(),ct);sql=plan.Sql;mode=plan.Mode;}
   var data=await repository.Execute(sql,ct);rowCount=data.Rows.Count;status="ok";
   return new(id,sql,mode,data.Columns,data.Rows,data.Truncated,watch.ElapsedMilliseconds,data.Cost);
  }finally{
   try{await workspace.Record(new(id,sql,mode,status,rowCount,watch.ElapsedMilliseconds,DateTimeOffset.UtcNow),CancellationToken.None);}
   catch(Exception e){logger.LogError(e,"Unable to persist request history {RequestId}",id);}
   logger.LogInformation("Query {RequestId} {Status} {Mode} {DurationMs}ms",id,status,mode,watch.ElapsedMilliseconds);
  }
 }
}
