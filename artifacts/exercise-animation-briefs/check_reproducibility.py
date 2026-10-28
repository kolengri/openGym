"""Compare durable generated outputs across two runs on the same runtime."""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import zlib

ROOT = Path(__file__).resolve().parent


def snapshot():
    files = [ROOT / name for name in (
        "aliases.json", "coverage-report.json", "review-queue.json",
        "selected-first-five.json", "selected-first-five.md", "briefs.jsonl.gz",
        "index.html", "README.md", "THIRD_PARTY_NOTICES.md")]
    files += sorted((ROOT / "details").glob("*.html"))
    files += sorted((ROOT / "details").glob("*.json.gz"))
    return {str(p.relative_to(ROOT)): (p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest())
            for p in files}


subprocess.run([sys.executable, str(ROOT / "generate.py")], check=True)
before = snapshot()
subprocess.run([sys.executable, str(ROOT / "generate.py")], check=True)
after = snapshot()
changed = sorted(key for key in before.keys() | after.keys() if before.get(key) != after.get(key))
receipt = dict(passed=not changed, generated_files_compared=len(after),
               bytes_compared=sum(value[0] for value in after.values()), changed_files=changed,
               python=platform.python_version(), zlib=zlib.ZLIB_VERSION,
               generator_sha256=hashlib.sha256((ROOT / "generate.py").read_bytes()).hexdigest(),
               method="SHA-256 of every generated durable output before and after a full rerun on the same runtime; gzip mtime=0 and no filename header.")
(ROOT / "reproducibility.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
if changed:
    raise SystemExit(1)
