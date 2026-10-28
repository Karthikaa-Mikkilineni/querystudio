using System.Net.Http.Json;
using System.Text.Json;
public sealed class PlannerClient(HttpClient client){
 private static async Task<string> Detail(HttpResponseMessage response,CancellationToken ct){
  try{using var doc=JsonDocument.Parse(await response.Content.ReadAsStringAsync(ct));
   var detail=doc.RootElement.GetProperty("detail");if(detail.ValueKind==JsonValueKind.String)return detail.GetString()??"SQL validation failed.";
  }catch(JsonException){}catch(KeyNotFoundException){}
  return "The planner could not process this input.";
 }
 public async Task<Plan> Plan(string question,CancellationToken ct){
  using var response=await client.PostAsJsonAsync("/plan",new {question},ct);
  if((int)response.StatusCode==422||(int)response.StatusCode==503)throw new PlannerException(await Detail(response,ct));
  response.EnsureSuccessStatusCode();
  return await response.Content.ReadFromJsonAsync<Plan>(cancellationToken:ct)??throw new HttpRequestException("Invalid planner response.");
 }
 public async Task<string> Validate(string sql,CancellationToken ct){
  using var response=await client.PostAsJsonAsync("/validate",new {sql},ct);
  if((int)response.StatusCode==422)throw new PlannerException(await Detail(response,ct));
  response.EnsureSuccessStatusCode();
  using var doc=JsonDocument.Parse(await response.Content.ReadAsStringAsync(ct));
  return doc.RootElement.GetProperty("sql").GetString()??throw new PlannerException("Empty SQL.");
 }
 public async Task<SchemaInfo> Schema(CancellationToken ct)=>await client.GetFromJsonAsync<SchemaInfo>("/schema",ct)??throw new HttpRequestException("Schema unavailable.");
}
