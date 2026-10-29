"""Use the current family verifier, including frozen hand morph and normals."""
import sys,runpy
from pathlib import Path
P=Path(__file__).resolve().parent;args=sys.argv[sys.argv.index('--')+1:]if'--'in sys.argv else[]
sys.argv=[str(P.parents[1]/'upright-cardio-family/verify_native.py'),'--','3531',*args]
runpy.run_path(sys.argv[0],run_name='__main__')
