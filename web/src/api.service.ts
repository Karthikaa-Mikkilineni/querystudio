import {inject,Injectable} from '@angular/core';
import {HttpClient} from '@angular/common/http';
export interface Template {name:string;sql:string}
export interface Column {name:string;type:string;nullable:boolean}
export interface Table {name:string;columns:Column[]}
export interface Schema {schema:string;examples:string[];templates:Template[];mode:string;tables:Table[]}
export interface QueryResult {requestId:string;sql:string;mode:string;columns:string[];rows:unknown[][];truncated:boolean;durationMs:number;estimatedCost:number}
export interface SavedQuery {id:string;name:string;sql:string;createdAt:string}
export interface HistoryEntry {requestId:string;sql:string;mode:string;status:string;rowCount:number;durationMs:number;timestamp:string}
@Injectable({providedIn:'root'})
export class WorkspaceApi {
 private http=inject(HttpClient);
 schema(){return this.http.get<Schema>('/api/schema')}
 run(sql:string){return this.http.post<QueryResult>('/api/query',{sql})}
 plan(text:string){return this.http.post<{sql:string;mode:string}>('/api/plan',{text})}
 saved(){return this.http.get<SavedQuery[]>('/api/saved')}
 save(name:string,sql:string){return this.http.post<SavedQuery>('/api/saved',{name,sql})}
 delete(id:string){return this.http.delete('/api/saved/'+id)}
 history(){return this.http.get<HistoryEntry[]>('/api/history')}
 clear(){return this.http.delete('/api/history')}
}
