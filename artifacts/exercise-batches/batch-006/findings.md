# Batch 006 findings

These are source-bound authoring decisions and observed defects, not clinical validation or measured recruitment. Final source/export/browser acceptance is recorded separately.

## Rejected hand grasp in 1512

The user rejected the previous all-fours stretch specifically because of the hand and foot grasp. Actual saved-action inspection found a 60.65 degree wrist deviation at hold and a 109.70 degree airborne maximum. The hand quaternion moved independently of the forearm and foot. Contact appeared only near the hold, with no acquisition, close, unload or open sequence. A few nearby fingertip vertices did not establish an enclosed foot or opposed thumb.

The replacement stages approach, closure, foot-local hold, unloading, opening and retraction. Airborne wrist alignment follows the forearm. The first broad mid-foot fit put ring/little fingers 22–27 mm inside the foot and was rejected. The accepted heel/ankle-collar hold uses a declared five-degree thigh adjustment and a coherent C-shaped palm/thumb/finger brace. Active wrist deviation is at most 17.846 degrees; held minimum clearance is 0.572 mm, palm clearance 2.816 mm, and foot-local hand transform drift is below 4.77e-7. All 151 decoded samples have no confirmed arm/hand-to-leg triangle crossings. The 75.7-degree angle between object contact normals is descriptive, not an anatomical thumb-opposition or force-closure requirement. Body fairing cannot repair an incorrect grasp.

## Heel reaches and cross crunches

0006's ambiguous arms-to-sides cue is interpreted as arms hovering alongside the torso toward the feet. A repeated wide T-to-heel shoulder sweep is excluded. Correct active-side lateral flexion and a separate inactive-arm outer corridor matter: a shoulder-relative relaxed arm initially followed the trunk into the thigh. The palm-down active hand now approaches the actual outer heel within about 3.6 mm in the reviewed native peaks, with no changed-state whole-arm/leg intersections. A roughly 50 mm gap was rejected despite clearing collision tests.

4354 uses bent grounded feet and alternating cross-body upper-trunk rotation. It is distinct from the raised-tabletop 5266 and pedalling bicycle.

A source knee binding transitioned from roughly 20% to 80% thigh influence within 28–33 mm and produced a square cap under deep flexion. One pinned local harmonic thigh/shin collar restores rounded volume. The attempted capped knee pose warp is excluded; its uncapped smoothing requirement exceeded 60 mm. The axillary defect has separate mixed chest/shoulder/arm faces and is a real local concavity. One source-local shoulder component, capped at 40 mm, replaces the insufficient 25 mm version. Neither is a reason to erase genuine thigh/torso occlusion.

## Lying leg family

4826 and 3590 have compatible flat-head alternating straight-leg motion; 4001 keeps a slightly raised head. Compatible actions share a physical body, with separate catalogue identities and muscle emphasis. The low leg retains a positive floor clearance to satisfy 4001. The cyclic demo begins at a transfer pose; the floor setup is stated separately.

5106 keeps both straight legs near vertical. The declared interpretation combines a restrained 82–90 degree hip-elevation reach with ankle/toe extension toward the ceiling, with fixed pelvis and supported back. The text does not specify that exact joint mechanism. No scissors, imaginary ceiling contact or prop is introduced.

Old bicycle pose-space targets and their schedule are not reused blindly. New bounded support fields preserve source-profile criteria and raw metrics. A coupled spine/chest/neck solve did not remove a pinched posterior attachment. An exactly source-neutral chain has a 58.63 mm chest/occiput support mismatch; this does not prove all non-neutral placements impossible. The accepted compact cervical field is capped at 8 mm and preserves the protected head/back/lumbar/pelvic anchors. Its full amplitude flips triangles in the head-up action; that action uses the same field at an analytically bounded weight of 0.6218309238 instead. A small remaining contour crease is disclosed. No large body warp, new prop or pose grid is used.

## Standing combinations and cardio

3479 includes a side kick followed by a reachable same-side heel touch. A small inward recovery-foot change resolves the initial hand reach failure. Palm and middle-fingertip targeting still let the little-finger edge enter the ankle. The accepted relaxed-wrist path instead targets that actual outer fingertip edge about 3 mm from the heel, with whole-arm/hand clearance through approach and release. Global dual-quaternion skinning reduced an elbow crease but produced a new hip bulge and was rejected for this standing family. Bounded local shoulder and rear-knee fields retain some joint crease detail rather than applying the roughly 49–52 mm uncapped fairing demand. 3480's root descent follows the backward step, avoiding the initial 79 mm impossible ankle reach and planted-toe sliding. Limb lengths remain fixed.

4918 uses four alternating hops in a five-second demonstration, with explicit flight and soft landing. The driven knee remains high through the apex. A wider arm corridor prevents swinging forearm/hand penetration of the thigh. This tempo is authored, not a source numeric recommendation.

3531 keeps a staggered stance, closed fists, aligned wrists and alternating forward punches. Finger curls and thumb opposition use the actual hand-local palmar frame. A world-lateral axis left C-shaped hands and overfolded fingers. The local palm-depth tolerance is a proxy, not a certificate of globally absent finger self-intersections.

Cardiovascular system remains the source training target for 4918 and 3531. Visible muscle fields use explicitly declared proxies from source secondary labels: calves/quadriceps plus glutes for hops; shoulders/triceps plus core/obliques for punches.

## Integration and evidence

The batch adds ten catalogue records plus the separately repaired 1512. A shared source-domain atlas retains the accepted softened abdominal fields once, avoiding repeated per-exercise payloads. The compiler supports an optional atlas file; default behavior remains compatible. Both verifiers select the actual configured number of actions rather than assuming five.

Before any render review, saved Blender weights must be read back by stable names, normalized and limited to four influences. Bone/action and full-skin pre/post-render checks prevent inherited-action overrides. Actual decoded full-cycle mechanics, contact/clearance and native transport are distinct from static shape acceptance. Transparent canvas, neutral inactive skin, no body shadows/AO/color textures, recommended views and touch/orbit/pinch/reset remain required.

Blender 5.2.3 multi-action discovery exported both skeletal actions but omitted the inactive shape-key action in the floor crunch and standing families. Skeletal action inventory alone did not catch this: full source/export surface parity did. The floor-crunch export adds the missing standard glTF weights channel from its actual native schedule, preserving the existing binary prefix. The standing-family exporter uses a muted inactive KEY NLA association for native discovery. Both final exports verify the source schedules; neither introduces a runtime workaround.

Three.js LoopOnce with clampWhenFinished leaves an action paused at the final frame. Any later arbitrary-time traversal must resume/reset it before setTime. The affected local verifiers were corrected and their final receipts verify actual changing joint matrices across all 151 samples; valid unaffected receipts are reused. This is a verification-state problem, distinct from a broken authored motion.
