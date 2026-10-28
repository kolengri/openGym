"""Freeze the first review batch without overwriting its previous evidence."""

import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "bodyweight-five"
BATCH = ROOT / "batch-001"
baseline = json.loads((BATCH / "baseline.json").read_text())
ids = baseline["ids"]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


for identifier in baseline["retained_ids"]:
    for suffix in [".webm", ".mp4", "-preview.webm"]:
        name = identifier + suffix
        assert sha256(SOURCE / name) == baseline["previous_media_sha256"][name], name

previous = json.loads((BATCH / "previous-pose-samples.json").read_text())
current = json.loads((SOURCE / "pose-samples.json").read_text())
for identifier in baseline["retained_ids"]:
    assert ([row for row in previous if row["id"] == identifier]
            == [row for row in current if row["id"] == identifier]), identifier

names = [identifier + suffix for identifier in ids
         for suffix in [".webm", ".mp4", "-preview.webm"]]
names += ["bodyweight-five.glb", "runtime-muscles.json", "camera-presets.json", "clips.json",
          "threejs-viewer.html"]
names += [f"web-textures/{identifier}.png" for identifier in ["neutral", *ids]]
names += ["pose-verification.json", "runtime-verification.json", "render-report.json",
          "encoding-report.json", "video-review.json", "transparency-verification.json",
          "review-page-verification.json", "runtime-export.json", "runtime-asset-qa.json"]
names += [str(path.relative_to(SOURCE)) for path in sorted((SOURCE / "situp-repair").glob("*.json"))]
for name in names:
    target = BATCH / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE / name, target)

html = (SOURCE / "viewer.html").read_text().replace("select(0);", "select(3);")
html = html.replace("<title>Пять упражнений · анатомический манекен</title>",
                    "<title>Пачка 1 · пять упражнений</title>")
assert len(html.encode()) < 512_000
(BATCH / "viewer.html").write_text(html)

readme = """# Review batch 001

Five bodyweight pilot animations, frozen for user review. This is not production approval.

| ID | Exercise |
| --- | --- |
| 5965 | Lateral shuffle |
| 5915 | Three-leg chaturanga |
| 5887 | Three-leg downward dog |
| 0001 | Three-quarter sit-up: repaired candidate |
| 9066 | Four-way single-leg hop |

Open `viewer.html` for the offline video player or `threejs-viewer.html` to orbit
the animated model. WebM masters have transparent
backgrounds; MP4 fallbacks use white. Both contain two synchronized views.
The GLB contains the same five actions for Three.js, plus camera presets and
companion activation textures. Source geometry has no genital anatomy or shorts.

Only 0001 was re-rendered in this batch. The other four videos and sampled poses
are identical to the published baseline; `baseline.json` binds their earlier
verification receipts. Original generation inputs are preserved under `contexts/`
at that baseline revision. Updated candidate context is under `review-contexts/`.
Open contract issues remain blocked until the corrected candidate is reviewed.
Muscle colors are illustrative selections, not measurements of recruitment.
Native renders include subdivision/corrective smoothing; the GLB uses the
original linear-skinned cage. Their contact surfaces are checked separately.
Physical mobile-device and actual application integration are not verified here.

Native QA accepts14 hidden back-to-back skin-fold pairs:7 inherited mouth pairs,
2 inherited toe pairs and5 right upper-arm/axillary fold pairs. Their locations
and rationale are recorded in `situp-repair/warning-correspondence.json`. Both
native and linear checks have zero errors; the checked linear cage has none of
these pairs. The raw material warning is resolved by delivery atlas assignment.

Geometry: Blender Studio Human Base Meshes v1.4.1, CC0, original realistic male
mesh normalized to 1.8 m. Official source archive:
<https://mirror.blender.org/demo/asset-bundles/human-base-meshes/human-base-meshes-bundle-v1.4.1.zip>.
The five actions are authored for this pilot; the source preparation action is
removed before authoring. No Gym Visual media or paid generation was used.
The full build pipeline is in `../../bodyweight-five/README.md` in the repository.
"""
(BATCH / "README.md").write_text(readme)
files = [*names, "viewer.html", "README.md", "baseline.json"]
files += [str(path.relative_to(BATCH)) for directory in ['contexts', 'review-contexts']
          for path in sorted((BATCH / directory).glob('*.json'))]
files += [str(path.relative_to(BATCH)) for path in sorted(BATCH.glob('previous-*.json'))]
manifest = {
    "batch": "001", "status": "awaiting_user_review", "ids": ids,
    "previous_revision": baseline["previous_revision"], "repaired_candidate_ids": ["0001"],
    "retained_media_and_sampled_poses_identical": baseline["retained_ids"],
    "files_sha256": {name: sha256(BATCH / name) for name in files},
}
(BATCH / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
archive_files = files + ["manifest.json"]
with zipfile.ZipFile(BATCH / "batch-001.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for name in archive_files:
        info = zipfile.ZipInfo(name, date_time=(2026, 10, 28, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, (BATCH / name).read_bytes())
print(json.dumps({"batch": "001", "ids": ids, "html_bytes": len(html.encode()),
                  "archive_bytes": (BATCH / "batch-001.zip").stat().st_size,
                  "retained_media_and_poses_identical": baseline["retained_ids"]}))
