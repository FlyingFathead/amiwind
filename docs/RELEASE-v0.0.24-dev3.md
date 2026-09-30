# v0.0.24-dev3 — Balmora Strider and region loading

30 September 2026. Previous delivered archives remain immutable.

## Changes

- Balmora's Strider now shares Seyda Neen's inspected conversion profile:
  0.5 geometry ratio and 64 px textures. The 16 affected regions are rebuilt.
  The body/main legs are restored at the owner's reported view. More geometry
  costs memory and rendering time; this is not a general performance fix.
- Options → Area loading offers Freeze frame (default) and Black screen.
  Freeze holds the last displayed view/palette with a small top Loading box.
  It reuses the existing loading-art buffer, with no per-gameplay-frame copying
  or second resident BSP. Music servicing remains. Ordinary scene/intro load
  styles are unchanged; region swaps are still synchronous.
- Record the owner's positive dev2 exterior feedback and often faster Balmora
  frame rate versus Seyda Neen as observations. Prioritize Balmora interiors;
  investigate Seyda Neen subdivision and bounded prefetch/offloading from profiles.

The symptom, suspected/inspected cause, fix and evidence are retained in
[MESH_TIPS_AND_TRICKS.md](MESH_TIPS_AND_TRICKS.md). Default FOV is still Quake's
90 degrees; physical player dimensions and bob are unchanged.

## Validation

279 host tests pass, with no skips. Native GCC warning review remains 82,
with no added or removed diagnostic against delivered dev2 (same SDK/flags).
The tests cover shared Strider configuration, loading pixel bounds, repeated
plaques, palette hold/release, invalid snapshot fallback, options input, plus
existing map/audio/state/collision behavior.

All 16 rebuilt map collision-node/plane combinations and entity lumps match dev2;
all 48 unaffected maps are byte-identical. Largest BSP: 5,427,160 bytes.
At the reported Strider view, the profile change adds 389,824 hunk bytes. The
single sequential A/B observation is recorded in the mesh notes, including its
limitations; no general frame-rate gain or zero-cost visual correction is claimed.

The final native executable completes a freeze → black → freeze round trip near
the Strider, with restored rendering after each crossing, held-frame captures,
no surface/edge overflow and 10,277,856 peak hunk bytes within the 11 MiB heap.
Observed swaps in that run: 405, 438 and 477 ms. One audio late update / 274 missed
frames was entirely reported as startup warm-up, with no additional late update
in the crossing run. These measurements are specific to the emulator host.

Release packaging verifies the incremental source overlay against the full source
archive, independently reads/hashes the HDF payload, then boots a diagnostic copy
of the finished image with the exact packaged executable. Private evidence retains
the build/test logs, warning comparison and native captures.

## Limits and playtest

**Start a new game or Demo Game.** Rebuilt BSP bytes change the content fingerprint,
so dev2 saves do not match this content. Aim at Darvame and press E to travel from
Seyda Neen, or use `dbg scene balmora`; Selvil offers the return.

Please inspect the Strider around XYZ 96 -1445 71, yaw 204, pitch -27, then roam
across nearby region boundaries using both Options loading settings. The new
presentation does not make disk/decode work asynchronous. Blank/held frames
must not be confused with streaming already being implemented.

Balmora interiors, broader streaming and Seyda Neen subdivision remain planned.
Boat performance, full natural-opening acceptance and citywide collision checks
remain open. The Strider still uses reduced converted geometry. Keep private
playable/content/reference files outside the public source repository.
