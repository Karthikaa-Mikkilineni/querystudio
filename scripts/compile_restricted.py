"""Fallback for hosts where dotnet CLI cannot read process metadata. SDK/reference assemblies required."""
import os,subprocess,sys,json,shutil
from pathlib import Path
sdk=Path(os.environ.get('DOTNET_ROOT','/tmp/apollo-dotnet'));out=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/apollo-build');out.mkdir(parents=True,exist_ok=True)
refs=list((sdk/'packs/Microsoft.NETCore.App.Ref').glob('*/ref/net8.0/*.dll'))+list((sdk/'packs/Microsoft.AspNetCore.App.Ref').glob('*/ref/net8.0/*.dll'))
np=Path(os.environ.get('NPGSQL_DLL','/tmp/apollo-npgsql/lib/net8.0/Npgsql.dll'))
globalfile=out/'GlobalUsings.cs';globalfile.write_text('\n'.join('global using '+x+';' for x in ['System','System.Collections.Generic','System.Linq','System.Threading','System.Threading.Tasks','System.Net.Http','Microsoft.AspNetCore.Builder','Microsoft.AspNetCore.Http','Microsoft.Extensions.Configuration','Microsoft.Extensions.DependencyInjection','Microsoft.Extensions.Hosting','Microsoft.Extensions.Logging']))
rsp=out/'compile.rsp';rsp.write_text('\n'.join(['-nologo','-target:exe','-nullable:enable','-langversion:12','-out:'+str(out/'AskDb.Api.dll')]+['-r:'+str(p) for p in refs+[np]]+[str(globalfile)]+[str(p) for p in Path(os.environ.get('SOURCE_API','api')).glob('*.cs')]))
subprocess.run([str(sdk/'dotnet'),str(next((sdk/'sdk').glob('*/Roslyn/bincore/csc.dll'))),'@'+str(rsp)],check=True)
shutil.copy2(np,out/'Npgsql.dll')
(out/'AskDb.Api.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net8.0','frameworks':[{'name':'Microsoft.NETCore.App','version':'8.0.0'},{'name':'Microsoft.AspNetCore.App','version':'8.0.0'}]}}))
web=Path('web/dist/askdb/browser')
if web.exists():shutil.copytree(web,out/'wwwroot',dirs_exist_ok=True)
print('Compiled application:',out)
