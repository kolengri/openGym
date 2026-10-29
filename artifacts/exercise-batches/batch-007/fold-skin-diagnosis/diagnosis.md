# Current fold skin diagnosis

The current carried8 asset is not visually acceptable. Neither global dual-quaternion skinning nor a coherent original-collar weight rollback fixes both poses. A remaining anatomical leg-frame mismatch is independent of the already-fixed global shortest-arc fault: parent-carried minimum swing does not align the source knee hinge plane with the actual hip–knee–ankle plane.

## Reviewed state and scope

- Source: `kneeling-family/carried8-source.blend`, SHA256 `827ca1f99dea4ebce6dad22739ce82ef24a5243b5c946d5044db51f8394e86bf`.
- Blender 5.2.3 LTS, identity mesh/rig object matrices, Armature enabled, Corrective Smooth and Multires disabled, no shape keys.
- Source topology: 10,582 vertices, 21,160 triangles, 51 rest bones. The supplied exact original/current source/FK witness packet was reused. Independently evaluated current LBS positions exactly matched its saved native positions.
- Required carried8 child side/oblique and half-kneel oblique images were actually inspected, as were both counterfactuals at those exact poses/cameras.
- All writes are confined to this diagnosis directory. No asset/source/Git mutations, exports, full-cycle QA, or paid calls.

## Controlled counterfactual results

These are diagnostic alternatives, not accepted assets. Frames are zero-based.

| Pose and skinning | Shoulder nonadjacent crosses | Hip crosses | Knee crosses | Whole-body minimum Z |
|---|---:|---:|---:|---:|
| 10058 f49 current LBS | 0 | 53 | 23 | +0.500 mm |
| 10058 f49 current DQ | 0 | 41 | 0 | −7.947 mm |
| 10058 f49 original collars, LBS | 0 | 5 | 23 | +0.500 mm |
| 4365 f75 current LBS | 120 | 96 | 90 | −12.305 mm |
| 4365 f75 current DQ | 0 | 99 | 73 | −22.556 mm |
| 4365 f75 original collars, LBS | 149 | 114 | 90 | −12.305 mm |

Current DQ fills the collapsed child axilla substantially and removes its measured shoulder crossings. It still has an unnatural shoulder band, does not remove the hip cut, and worsens the floor violation. It displaces some child vertices by 117.67 mm. This supports a localized shoulder volume-loss contribution, not a global DQ recommendation.

The second, separately authorized counterfactual restores exactly original weights across the complete inherited pelvis/thigh and shoulder envelopes plus all 297 height-transfer rows, preserving actual contact patches. There are 1,490 changed rows. The exact mask and before/after weights are in `original-collar-mask.json`. It improves the half-kneeling hip, but makes the child's diagonal torso/hip seam worse. Therefore neither the inherited repair nor original weights alone are a valid accepted answer for the child pose.

Both alternatives have zero whole-arm/hand-versus-leg BVH triangle crossings at the two sampled peaks. This is not a measured positive minimum clearance or a full-cycle claim. DQ keeps the child actual palms near +1 mm and head/feet near +0.5 mm, but violates knee/whole-body floors. Original collars preserve all measured contact patch minima exactly. Every diagnostic render independently preserved evaluated skin and actual bone matrices exactly across rendering.

## Remaining binding evidence

The 402-row rollback repaired particular collar cores; it did not undo the entire bad height transfer. Current child crossing triangle 16980 `[8579,8581,8537]` intersects triangle 17125 `[8588,8594,8593]`. In the source ring:

| Source ID | Original LeftUpLeg weight | Current weight |
|---|---:|---:|
| 8580 | 0.89103 | 0.89103 |
| 8579 | 0.79325 | 0.46022 |
| 8581 | 0.81207 | 0.46255 |
| 8537 | 0.64888 | 0.02477 |

The maximum adjacent L1 weight gradient at edge 8579–8580 is 29.46/m currently versus 6.69/m originally; at edge 8581–8582, 31.11/m versus 7.47/m. A finite per-vertex blend-matrix condition number does not bound these spatial weight derivatives or prevent a triangle from folding. Of child-crossed hip vertices, 107/114 still differ from original weights; for half-kneeling, 49/53. The coherent-rollback result establishes that this contributes materially to 10058; it does not establish that rollback can fix the child.

## Newly isolated leg-frame problem

Compute the source signed hinge normal from source joint centers:

`n_rest = normalize((knee_rest - hip_rest) × (ankle_rest - knee_rest))`.

Compute the actual hinge normal from the current FK joint centers similarly. Transport `n_rest` by the current deform rotation of each upper/lower leg, then compare with the actual plane. This uses all three joint centers, whereas minimum swing constrains only each segment's long axis.

At child f75 the source knee bend is 7.108 degrees and the posed bend is 157.72 degrees; the plane is not numerically degenerate. Current transported femur hinge normals miss the actual plane by 73.68 degrees on both sides. The lower-leg normals miss by 42.60 degrees. Half-kneeling f49 is much closer: upper-leg errors 6.19/10.11 degrees and lower-leg errors 5.32/9.05 degrees. Exact normals and signed corrections are in `hinge-plane-evidence.json`.

For example, child LeftUpLeg transports the source hinge normal to `[0.44990,-0.21214,0.86751]`, but the actual hip/knee/ankle plane normal is `[0.87181,0.48977,-0.00844]`. This is a large axial mismatch hidden by correct endpoints, fixed lengths, nonsingular skinning, and minimum-swing rotation. The rigid RightLeg vertex 3801 at Z=−12.305 mm is outside the old anterior-knee patch; no hip-weight change can move that rigid vertex.

## One bounded next remedy

Correct the leg orientation contract to use source and actual two-axis frames: the segment direction plus its signed knee hinge-plane normal. For each upper/lower leg, construct orthonormal source and target frames and use `R_target @ R_source.T`, then compose with the bone's original rest orientation. Both upper and lower legs must share the same target hinge normal. Keep the solved hip/knee/ankle endpoints and explicit Foot/ToeBase world frames initially unchanged. Handle a near-straight leg with the existing pole and previous-frame transport, rather than an arbitrary flip. Preserve action isolation and quaternion hemisphere continuity.

This is a source-derived geometric change with a measurable acceptance condition, not another arbitrary twist parameter. The child LeftUpLeg signed axial correction relative to current orientation is approximately −73.68 degrees; RightUpLeg is +73.68 degrees. Derive both shin frames independently from the shared hinge plane rather than applying those femur angles blindly to descendants.

Prediction: the patella/anterior-shin surface should face the actual bend/contact direction, removing the rotated-calf floor presentation and changing the child's femoral collar fold. This prediction is unverified: no third pose variant was generated. Do not claim it fixes the shoulder; the current DQ experiment separately establishes a shoulder volume contribution. After correcting leg frames, any compact shoulder target should be derived locally from the measured DQ volume target with exact exterior/contact protection, not by enabling DQ globally or reviving the rejected global Smooth20 target.

The leg remedy requires the same child f75 and half-kneel f49 images plus actual whole-body floor/skin-contact readback before a decision. If the rigid calf remains below the floor, resolve the full source skin support envelope; the old selected-knee patch is insufficient. Keep the shoulder/hip shape gate open. Source silhouette acceptance is not established by zero intersections alone.

## Final coupled candidate contract for the sole writer

This refines the next remedy into one rebuild, without declaring it accepted:

1. Apply the shared source/target knee hinge-plane frame contract to both leg bones. Preserve endpoints initially and explicit foot/toe frames. Then evaluate the complete calf/knee/foot skin envelope, including rigid source ID3801, against the floor. If support must be re-solved, use actual full supporting skin rather than the old anterior-knee-only proxy.
2. Use `hip-original-binding-contract.json`: exactly 586 original hip/pelvis/waist rows, a subset of the actually tested full original-collar counterfactual. Keep current shoulder binding. The original full-collar test reduced 10058 hip crossings from53 to5; it is supporting evidence, not proof that this subset plus new leg frames is accepted.
3. Use `shoulder-volume-target-contract.json` as a bounded local volume-target specification. The 135 core source IDs are precisely the vertices participating in current child shoulder crossings; the 584-vertex envelope is three source-topology rings, excluding actual contact patches. Its 150 boundary IDs must remain zero. Source bounds are X−0.2687..0.2744, Y−0.0750..0.1547, Z1.1449..1.5447 m. No current leg-bone influences occur in this envelope. Set the core target to the measured same-pose DQ shoulder surface; solve a harmonic feather between core1 and boundary0, then quintic-remap. This feathered local target has not yet been rendered or collision-checked.
4. Compose the final binding and final supported pose BEFORE deriving this component's DQ-minus-LBS displacement and its exact inverse-LBS source delta. Nine hip-rollback IDs overlap the shoulder envelope; none are in the core, and eight are zero-boundary IDs. The remaining overlap is ID3243. Do not blindly reuse the pre-integration inverse deltas supplied as numerical witnesses.
5. The measured full-DQ envelope displacement reaches78.55mm; the exact raw inverse-LBS source delta reaches159.75mm at ID8550, with maximum local condition3.56. These are not authoring caps or a claim of a good source shape. They quantify the actual volume-restoring target. Reject the target if the natural silhouette or transitions fail; do not hide that failure by choosing a small arbitrary source cap.
6. Author one child-only compact shoulder POSITION/NORMAL component, zero at neutral and throughout10058. Use the existing component/export contract. Drive it from the child shoulder elevation/fold state and inspect entry/peak/return, because exactness at the peak does not prove the interpolation. Normals must correspond to the final deformed surface and existing native/GPU transport, not merely copied from a mismatched pre-integration binding.

The mandatory first proof is the same child f75 side/oblique and half-kneel f49 side/oblique, plus source contact/whole-floor and whole-arm/hand-versus-leg readback. Child peak axilla should fill as in the observed DQ proof, while the hip/shin shape should reflect correct hinge alignment and the coherent hip ring. Whole-body floor and shoulder/hip silhouette remain open acceptance criteria. Only then is complete native/decoded-cycle and game QA justified.

This does not independently establish missing scapular motion as a cause. The shoulder bone is indeed only carried by Spine1; changing clavicle/scapular kinematics would require new endpoint/skin/contact evidence. The measured local DQ target is currently the narrower evidence-backed shoulder intervention.
