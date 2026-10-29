# 1512 grasp repair

The repaired same-side heel/ankle-collar grasp was visually accepted by root. The hand approaches with a coherent forearm/wrist line, closes before the pull, remains in the foot frame through pull/hold/unload, then opens before retracting. Batch-005 motion is user-rejected history. No new body fairing, binding edit or corrective target was added for this repair.

The source description asks for a foot pull toward the glutes; the instruction combines “straight back” with a bent knee. This demonstration interprets the backward motion as the thigh trajectory, retaining a flexed knee and a restrained level-pelvis lower. Exact grasp, joint angles and timing are authored choices. Anatomical left is shown; mirror the complete action and highlights for the other side. The 2 s entry / 1 s hold / 2 s return demonstration is separate from the source 20–30 s workout hold.

Native frames 1–151 map to runtime 0–150 at 30 fps. Digits close at 1.1–1.3 s; the foot-local grasp stays fixed at 1.3–3.7 s through pull, hold and unloading. Opening at 3.7–3.9 s precedes retraction. The single authorized 5° leg adjustment improves wrist reach by 24.654 mm while retaining 130° hold knee flexion, neutral trunk and actual right palm/knee/foot support. Numeric angles are not source facts.

The saved source and actual GLB use the original 10,582-ID / 21,160-triangle / 51-bone Blender Studio CC0 body. Basis, rest skeleton, UVs, topology and source IDs remain exact. The recorded 239-ID binding and three compact body keys are reused unchanged as technical inputs; the old motion supplies no visual approval. All non-Armature modifiers are disabled, and the unchanged shared DQ adapter is required. POSITION and NORMAL key transport is independently checked.

Final local checks pass:

- All 151 native and decoded samples retain support, floor tolerance, positive triangle areas and all native joint positions. Native skin loop error is zero; decoded loop error is 0.354 µm.
- Active airborne wrist deviation is at most 17.846°. Bone scale deviation is below 1.20e-6, length error below 0.269 µm, and connected arm/digit chain gaps below 0.341 µm.
- The held native hand has at least 59 vertices within 5 mm of the collar. Minimum recorded part clearance is 0.572 mm and palm clearance is 2.816 mm. Local signed diagnostics record no penetration across all 151 samples. Distinct palm, thumb and all four digit contacts are recorded with coordinates in `grasp-trajectory-report.json`.
- Actual decoded whole-arm/hand/finger versus both whole-leg triangles have zero confirmed crossings across all 151 samples. The test retains one domain boundary ring. This is sampled surface evidence, not a continuous-time or enclosed-volume certificate.
- Maximum full-source native/decoded DQ position error is 20.970 µm; all-151 joint error is 0.943 µm. Mandatory game QA at start, approach, grasp, hold and release has zero errors.
- Actual saved weights are normalized within 1.602e-7 with at most four influences. Outside the declared binding/key domains and protected posterior waist, the reported changes are exactly zero.

The game checker retains one close folded ankle pair and an additional thumb/collar proximity pair during grasp/hold. Their exact original IDs are in `qa-warning-locations.json`; decoded crossing checks pass. The approximately 75.7° thumb/finger object-normal angle is descriptive, not an invented force-closure gate. The residual angular bent-knee silhouette of the preserved body remains visible.

The staged neutral proofs are `early-start-side.png`, `early-approach-oblique.png`, `early-grasp-detail.png`, `early-hold-side.png`, `early-release-detail.png`, and `early-return-side.png`. Two wire inspections cover start and hold. Native bone/full-surface readback before and after rendering is identical. Camera 1 preserves the whole body; camera 2 frames 1,816 unique hand/foot IDs through the full cycle at 1.59× the whole-body view's zoom. Full hand travel limits a tighter static detail crop; the complete model is retained.

Reproduction uses Blender 5.2.3 LTS with two threads and `--python-exit-code 1`. Run `build_motion.py`, `inspect_grasp.py`, `prepare_cameras.py`, `verify_asset.py -- --game-qa`, `verify_source.py`, `export_motion.py`, `diagnose_warnings.py`, and `render_qa.py` through the Blender CLI, then `node verify_export.mjs --triangles` and `python3 finalize_packet.py`. Scripts use existing local helpers and tools. The verifier explicitly resumes the Three.js LoopOnce action before each random-access sample, preventing endpoint pause from contaminating a later traversal.

`curated-files.json` is the delivery boundary and excludes trials, logs, backups, caches and environments. Primary-owned actual GPU appearance, heat fields, camera-width integration and final user acceptance remain pending. No video or runtime frame/vertex cache was generated.
