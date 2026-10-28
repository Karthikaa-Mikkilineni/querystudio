import {Component,inject,signal} from '@angular/core';
import {bootstrapApplication} from '@angular/platform-browser';
import {provideHttpClient,HttpErrorResponse} from '@angular/common/http';
import {CommonModule} from '@angular/common';
import {FormsModule} from '@angular/forms';
import {Subscription} from 'rxjs';
import {WorkspaceApi,Schema,QueryResult,SavedQuery} from './api.service';
@Component({selector:'app-root',standalone:true,imports:[CommonModule,FormsModule],templateUrl:'./workspace.html'})
class App {
 api=inject(WorkspaceApi);schema=signal<Schema|null>(null);saved=signal<SavedQuery[]>([]);history=signal<import('./api.service').HistoryEntry[]>([]);
 view=signal<'studio'|'saved'|'history'>('studio');tab=signal<'sql'|'ai'>('sql');output=signal<'table'|'chart'>('table');busy=signal(false);planning=signal(false);error=signal('');notice=signal('');result=signal<QueryResult|null>(null);
 sql='';question='';saveName='';filter='';page=0;pageSize=10;sortIndex=-1;ascending=true;active?:Subscription;
 constructor(){this.api.schema().subscribe({next:s=>{this.schema.set(s);this.sql=s.templates[0]?.sql??''},error:()=>this.error.set('Unable to connect. Check that the API, planner and database are running.')});this.refresh()}
 refresh(){this.api.saved().subscribe({next:x=>this.saved.set(x),error:()=>{}});this.api.history().subscribe({next:x=>this.history.set(x),error:()=>{}})}
 message(e:HttpErrorResponse){return e.status===429?'Too many requests. Wait a minute and retry.':e.error?.error||'A service is unavailable. Please retry.'}
 load(sql:string){this.sql=sql;this.tab.set('sql');this.view.set('studio');this.error.set('');this.notice.set('Query loaded. Review the SQL, then run it.')}
 run(){if(this.busy()||this.planning()||!this.sql.trim())return;this.busy.set(true);this.error.set('');this.notice.set('');this.result.set(null);this.page=0;this.filter='';this.sortIndex=-1;
  this.active=this.api.run(this.sql).subscribe({next:r=>{this.result.set(r);this.busy.set(false);this.output.set('table');this.refresh()},error:(e:HttpErrorResponse)=>{this.error.set(this.message(e));this.busy.set(false);this.refresh()}})}
 cancel(){this.active?.unsubscribe();this.busy.set(false);this.notice.set('Request cancelled. The server receives cancellation when the connection closes.');this.refresh()}
 generate(){if(this.planning()||this.question.trim().length<3)return;this.planning.set(true);this.error.set('');this.api.plan(this.question).subscribe({next:r=>{this.sql=r.sql;this.planning.set(false);this.tab.set('sql');this.notice.set((r.mode==='demo'?'Demo template loaded.':'AI draft generated.')+' Review before running.')},error:(e:HttpErrorResponse)=>{this.error.set(this.message(e));this.planning.set(false)}})}
 save(){if(!this.saveName.trim()||!this.sql.trim())return;this.error.set('');this.api.save(this.saveName.trim(),this.sql).subscribe({next:()=>{this.saveName='';this.notice.set('Query saved to your local workspace.');this.refresh()},error:(e:HttpErrorResponse)=>this.error.set(this.message(e))})}
 remove(id:string){this.api.delete(id).subscribe({next:()=>this.refresh(),error:(e:HttpErrorResponse)=>this.error.set(this.message(e))})}
 clearHistory(){this.api.clear().subscribe({next:()=>this.refresh(),error:(e:HttpErrorResponse)=>this.error.set(this.message(e))})}
 sort(index:number){this.ascending=this.sortIndex===index?!this.ascending:true;this.sortIndex=index;this.page=0}
 rows(){const r=this.result();if(!r)return [];let rows=r.rows.filter(row=>row.some(x=>String(x??'').toLowerCase().includes(this.filter.toLowerCase())));if(this.sortIndex>=0){const i=this.sortIndex;rows=[...rows].sort((a,b)=>{const x=a[i],y=b[i];const diff=typeof x==='number'&&typeof y==='number'?x-y:String(x??'').localeCompare(String(y??''));return this.ascending?diff:-diff})}return rows}
 visible(){return this.rows().slice(this.page*this.pageSize,(this.page+1)*this.pageSize)}
 pages(){return Math.max(1,Math.ceil(this.rows().length/this.pageSize))}
 display(value:unknown){if(value===null)return 'NULL';return typeof value==='number'?value.toLocaleString(undefined,{maximumFractionDigits:2}):String(value)}
 chart(){const r=this.result();if(!r||r.columns.length<2||!r.rows.length||!r.rows.every(row=>typeof row[1]==='number'))return [];const rows=this.rows().slice(0,12);const max=Math.max(...rows.map(x=>Math.abs(Number(x[1]))),1);return rows.map(row=>({label:String(row[0]),value:Number(row[1]),width:100*Math.abs(Number(row[1]))/max}))}
 download(){const r=this.result();if(!r)return;const safe=(v:unknown)=>{let s=v===null?'':String(v);if(/^[=+\-@\t\r]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"'};const csv=[r.columns,...this.rows()].map(row=>row.map(safe).join(',')).join('\r\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='askdb-results.csv';a.click();URL.revokeObjectURL(url)}
}
bootstrapApplication(App,{providers:[provideHttpClient()]}).catch(console.error);
