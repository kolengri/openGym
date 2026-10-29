"""Consume a prepared actual Three/DQ exchange under the existing native physical checker."""
from pathlib import Path
import subprocess,sys
F=Path(__file__).resolve().parent
ID=sys.argv[1]
assert ID in['1987','1986']
P=F.parent/'assets'/ID
path=Path((P/'verification-exchange-path.txt').read_text().strip())
assert path.is_file()
subprocess.run(['/opt/homebrew/bin/blender','-b','-t','2','--python-exit-code','1','--python',str(F/'verify_native.py'),'--','--id',ID,'--decoded',str(path)],check=True)
