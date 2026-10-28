using System.Data;
using System.Text.Json;
using Npgsql;
public sealed class QueryRepository{
 private readonly string connection;
 public QueryRepository(IConfiguration config){connection=config.GetConnectionString("Analytics")??throw new InvalidOperationException("ConnectionStrings__Analytics is required.");}
 public async Task<List<TableInfo>> Schema(CancellationToken ct){
  await using var db=new NpgsqlConnection(connection);await db.OpenAsync(ct);
  const string sql="SELECT table_name,column_name,data_type,is_nullable FROM information_schema.columns WHERE table_schema='analytics' AND table_name IN ('customers','orders','order_items') ORDER BY table_name,ordinal_position";
  await using var command=new NpgsqlCommand(sql,db){CommandTimeout=3};await using var reader=await command.ExecuteReaderAsync(ct);
  var tables=new List<TableInfo>();
  while(await reader.ReadAsync(ct)){
   var name=reader.GetString(0);var table=tables.FirstOrDefault(t=>t.Name==name);
   if(table is null){table=new(name,[]);tables.Add(table);}
   table.Columns.Add(new(reader.GetString(1),reader.GetString(2),reader.GetString(3)=="YES"));
  }return tables;
 }
 public async Task<(string[] Columns,List<object?[]> Rows,bool Truncated,double Cost)> Execute(string sql,CancellationToken ct){
  await using var db=new NpgsqlConnection(connection);await db.OpenAsync(ct);
  await using var tx=await db.BeginTransactionAsync(IsolationLevel.ReadCommitted,ct);
  await using(var settings=new NpgsqlCommand("SET TRANSACTION READ ONLY; SET LOCAL statement_timeout='2000ms'; SET LOCAL lock_timeout='500ms';",db,tx))await settings.ExecuteNonQueryAsync(ct);
  var limited=$"SELECT * FROM ({sql}) AS result LIMIT 201";double cost;
  await using(var explain=new NpgsqlCommand("EXPLAIN (FORMAT JSON) "+limited,db,tx){CommandTimeout=3}){
   var json=Convert.ToString(await explain.ExecuteScalarAsync(ct))??throw new QueryPolicyException("No query plan returned.");
   using var doc=JsonDocument.Parse(json);cost=doc.RootElement[0].GetProperty("Plan").GetProperty("Total Cost").GetDouble();
   if(cost>100000)throw new QueryPolicyException("Estimated query cost exceeds the local budget. Narrow the dataset or joins.");
  }
  await using var command=new NpgsqlCommand(limited,db,tx){CommandTimeout=3};
  await using var reader=await command.ExecuteReaderAsync(ct);
  var columns=Enumerable.Range(0,reader.FieldCount).Select(reader.GetName).ToArray();var rows=new List<object?[]>();
  while(await reader.ReadAsync(ct)){
   var row=new object?[reader.FieldCount];
   for(var i=0;i<row.Length;i++)row[i]=await reader.IsDBNullAsync(i,ct)?null:reader.GetValue(i);
   rows.Add(row);
  }
  var truncated=rows.Count>200;if(truncated)rows.RemoveAt(200);
  await reader.CloseAsync();await tx.CommitAsync(ct);return(columns,rows,truncated,cost);
 }
}
