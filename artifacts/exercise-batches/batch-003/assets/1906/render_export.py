"""Render actual exported LBS and animated morph normals faithfully.

Blender5.2's glTF importer omits morph NORMAL; it cannot certify this asset's
corrected shading. The renderer decodes actual GLB data and the Three.js normal
equation, then creates temporary posed review meshes without changing the asset.
"""
import sys,runpy
from pathlib import Path
P=Path(__file__).resolve().parent
sys.argv=[str(P/'render_lbs.py'),'--final']
runpy.run_path(str(P/'render_lbs.py'),run_name='__main__')
