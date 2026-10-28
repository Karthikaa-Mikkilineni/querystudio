"""Prepare restricted-host baseline and optimized builds without editing working sources."""
import os,shutil,subprocess,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1];os.chdir(root)
with tempfile.TemporaryDirectory(prefix='askdb-baseline-') as d:
 source=Path(d)/'api';shutil.copytree('api',source)
 for name in ['WorkspaceStore.cs','Program.cs']:shutil.copy2(root/'baseline'/(name+'.txt'),source/name)
 subprocess.run(['python3','scripts/compile_restricted.py','/tmp/apollo-baseline-build'],env={**os.environ,'SOURCE_API':str(source)},check=True)
subprocess.run(['python3','scripts/compile_restricted.py','/tmp/apollo-optimized-build'],check=True)
