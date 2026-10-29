# Butterfly runtime hip repair

The one local harmonic weight extension passes the hip gate on all 151 decoded GLB frames. No hip corrective morph is required.

Integrate `runtime-weight-override.json` into the existing GLB writer. It supplies at most four normalized existing group indices for each of 547 hip-domain vertices. Native weights, P0, triangle indices, UVs and joint trajectories remain frozen. `domain.npz` records the exact active, protected, fixed-boundary and affected-face masks; `domain.json` explains their construction.

Actual artifact: `harmonic-glb/motion.glb`. Evidence: `actual-glb-verification.json` contains every sampled frame; `delivery-report.json` is the compact result. The decoded surface has zero exact hip-vs-all and affected-vs-all intersections, minimum orientation ratio 0.9456312057, and no zero-area triangles. All exterior/protected trajectories and floor/glute support match the baseline exactly. The validation union covers 1,932 faces, including every final-fairing affected face and generated cap.

The harmonic equation uses inverse current-P0 edge lengths and fixed exterior weights, followed by deterministic top-four selection and normalization. Maximum discarded weight mass is 0.0308237622; the actual emitted GLB, including this projection and float32 codec, passes. Maximum codec error is 45.995 nanometers. Maximum moving-hip difference from the failing binding is 13.155 mm; static geometry is unchanged and no source-space corrective was created.

This is a sampled hip-only result. Hand/arm targets and final integrated validation belong to the primary. Existing shape limitations from static review remain; this does not promote the model to full anatomy or catalogue acceptance. No extra render or geometry revision was made for this task.

`curated-files.json` lists SHA-256 values for the adapter, artifact, domain and evidence. The solve script refuses a second harmonic solve when an override already exists. The historical `harmonic-report.json` records the pre-export stage; final acceptance is in `actual-glb-verification.json`.
