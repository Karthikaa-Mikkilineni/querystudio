using Npgsql;
using Microsoft.AspNetCore.RateLimiting;
using System.Threading.RateLimiting;

var builder=WebApplication.CreateBuilder(args);
builder.Services.AddHttpClient<PlannerClient>(c=>{
 c.BaseAddress=new Uri(builder.Configuration["PlannerUrl"]??"http://127.0.0.1:8001");
 c.Timeout=TimeSpan.FromSeconds(Math.Clamp(builder.Configuration.GetValue<double?>("PlannerTimeoutSeconds")??30,0.1,120));
});
builder.Services.AddSingleton<WorkspaceStore>();
builder.Services.AddSingleton<QueryRepository>();
builder.Services.AddScoped<QueryService>();
builder.Services.AddRateLimiter(o=>{
 o.RejectionStatusCode=429;
 o.AddFixedWindowLimiter("queries",l=>{l.PermitLimit=60;l.Window=TimeSpan.FromMinutes(1);l.QueueLimit=0;});
});
var app=builder.Build();
app.UseRateLimiter();app.UseDefaultFiles();app.UseStaticFiles();
app.MapGet("/api/health",()=>Results.Ok(new {status="ok"}));
app.MapGet("/api/schema",async (PlannerClient planner,QueryRepository repo,CancellationToken ct)=>{
 var schema=await planner.Schema(ct);
 return Results.Ok(new {schema.Schema,schema.Examples,schema.Templates,schema.Mode,tables=await repo.Schema(ct)});
});
app.MapGet("/api/history",async(WorkspaceStore store,CancellationToken ct)=>Results.Ok(await store.History(ct)));
app.MapDelete("/api/history",async(WorkspaceStore store,CancellationToken ct)=>{await store.ClearHistory(ct);return Results.NoContent();});
app.MapGet("/api/saved",async(WorkspaceStore store,CancellationToken ct)=>Results.Ok(await store.Saved(ct)));
app.MapPost("/api/saved",async(SaveRequest body,PlannerClient planner,WorkspaceStore store,CancellationToken ct)=>{
 if(string.IsNullOrWhiteSpace(body.Name)||body.Name.Length>80||string.IsNullOrWhiteSpace(body.Sql)||body.Sql.Length>12000)
  return Results.BadRequest(new {error="A name (1–80 characters) and SQL (1–12000 characters) are required."});
 try{
  var sql=await planner.Validate(body.Sql,ct);
  var saved=await store.Save(body.Name.Trim(),sql,ct);
  return Results.Created($"/api/saved/{saved.Id}",saved);
 }catch(PlannerException e){return Results.UnprocessableEntity(new {error=e.Message});}
 catch(OperationCanceledException){return Results.Json(new {error="SQL validation timed out or was cancelled."},statusCode:504);}
 catch(HttpRequestException){return Results.Json(new {error="SQL validator is unavailable."},statusCode:503);}
 catch(InvalidOperationException){return Results.Conflict(new {error="The local workspace limit is reached. Delete a saved query first."});}
}).RequireRateLimiting("queries");
app.MapDelete("/api/saved/{id:guid}",async(Guid id,WorkspaceStore store,CancellationToken ct)=>{
 return await store.Delete(id,ct)?Results.NoContent():Results.NotFound();
});
app.MapPost("/api/plan",async(Question body,PlannerClient planner,CancellationToken ct)=>{
 if(string.IsNullOrWhiteSpace(body.Text)||body.Text.Length<3||body.Text.Length>500)return Results.BadRequest(new {error="Enter 3–500 characters."});
 try{return Results.Ok(await planner.Plan(body.Text.Trim(),ct));}
 catch(PlannerException e){return Results.UnprocessableEntity(new {error=e.Message});}
 catch(HttpRequestException){return Results.Json(new {error="AI planner is unavailable."},statusCode:503);}
 catch(OperationCanceledException){return Results.Json(new {error="AI planning timed out or was cancelled."},statusCode:504);}
}).RequireRateLimiting("queries");
app.MapPost("/api/query",async(QueryRequest body,QueryService service,HttpContext context,CancellationToken ct)=>{
 var hasSql=!string.IsNullOrWhiteSpace(body.Sql);
 if(hasSql ? body.Sql!.Length>12000 : string.IsNullOrWhiteSpace(body.Text)||body.Text!.Length<3||body.Text.Length>500)
  return Results.BadRequest(new {error="Provide SQL (up to 12000 characters) or a question (3–500 characters)."});
 var requestId=context.TraceIdentifier;
 try{return Results.Ok(await service.Run(body,requestId,ct));}
 catch(PlannerException e){return Results.UnprocessableEntity(new {error=e.Message,requestId});}
 catch(PostgresException e) when(e.SqlState=="57014") {return Results.UnprocessableEntity(new {error="Query exceeded its execution limit.",requestId});}
 catch(PostgresException){return Results.UnprocessableEntity(new {error="PostgreSQL could not execute this query. Check column names, joins and grouping.",requestId});}
 catch(QueryPolicyException e){return Results.UnprocessableEntity(new {error=e.Message,requestId});}
 catch(OperationCanceledException){return Results.Json(new {error="Request timed out or was cancelled.",requestId},statusCode:504);}
 catch(Exception e){app.Logger.LogError(e,"Query failed {RequestId}",requestId);return Results.Json(new {error="A required service is unavailable. Check the API, planner and database.",requestId},statusCode:503);}
}).RequireRateLimiting("queries");
app.MapFallbackToFile("index.html");app.Run();
