"""Consume the temporary actual decoded DQ exchange; no runtime cache is delivered."""
from pathlib import Path
import subprocess
F=Path(__file__).resolve().parent;P=F.parent/'assets/1843';exchange=Path((P/'verification-exchange-path.txt').read_text().strip());assert exchange.is_file()
subprocess.run(['/opt/homebrew/bin/blender','-b','-t','2','--python-exit-code','1','--factory-startup','--python',str(F/'verify_native.py'),'--','--decoded',str(exchange)],check=True)
