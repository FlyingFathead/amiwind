# First-person geometry and sprite experiment

The existing 3D converter and model are retained. **3D remains the default.**
Select `build.sh --hands 3d` or `build.sh --hands sprites` at build time. The
engine and image builders accept the same flag and reject mismatched modes.
There is no in-game mode switch. The optional private `experimental/` HDF is
for comparison, not a replacement with complete equipment coverage.

Both routes use the same locally sampled Nord-male unarmed model: 311 triangles,
28 poses (8 idle, 6 draw, 4 lower, 10 punch). The 3D MDL is 252,612 bytes. The
sprite baker rasterizes each pose on the host at 160x100 and packs opaque row
spans into a 22,426-byte AWS1 file. Runtime checks bounds once and draws indexed
pixels without blending or world-depth tests; no per-frame disk read.

The compile-time sprite path uses the existing animation frame state, avoiding
the hand-model cache load. The 3D source asset remains on disk. Some sampled
draw/lower/punch poses move fully offscreen; those empty baked frames are recorded
in the report and need animation/framing refinement. This prototype is not a
complete fix for the owner's disappearance report.

First-person drawing now occurs after world fog; 3D hand ambient has a minimum
brightness floor. This prevents the world fog pass from obscuring the overlay,
but it does not prove the original flicker cause or eliminate all model/texture
issues. Native screenshots still warrant owner comparison. Sprite lighting is
a fixed neutral bake and does not yet follow the dim interior.

## Coverage gate before adopting sprites generally

Bake every required motion for the selected race/body, equipment, weapon/spell
and handedness before relying on a sprite set. Race stays fixed during play,
but armor/clothing/weapon appearance can change. Use a complete appearance key
for caching and invalidate affected frames on equipment change. Missing coverage
keeps that target on the 3D build until an explicit fallback policy exists.

Keep A/B cameras, heading, pitch, viewport, draw distance and emulator settings
identical. `hands_ms` is separately profiled; aggregate routes include hidden
hands and console time, so they are not per-visible-frame speedup measurements.
This checkpoint tests both builds functionally, not physical-Amiga performance.


## Race and sex catalogue candidate

The optional 3D catalogue selects owned skin BODY records for the player's race
and sex, rather than assigning Nord arms to every character. Selection prefers
first-person skin, then the same sex's third-person arm parts; female records
may fall back to the same race's male first/third-person arms. It never borrows
another race's records. This follows the arm fallback order in
[OpenMW's body-part selector](https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwrender/npcanimation.cpp).
Authored records can legitimately share a mesh: the Nord male hand record uses
an Imperial hand mesh, with Nord wrists and arms. Distinct race IDs do not imply
that every underlying mesh is unique.

`tools/prepare_hand_catalog.py` generates male/female pairs for every playable
RACE record from locally owned data, including matching carried-torch arms.
Run conversion inside the documented Linux Docker builder. The data directory,
palette and fresh output directory must be outside this source checkout:

```sh
python3 tools/prepare_hand_catalog.py --data-files /owned \
  --palette /assets/id1/gfx/palette.lmp --out /output/hand-catalogue \
  --topology reduced
```

The existing reduced profile remains the default. `--topology source` is an
explicit authored-topology candidate; it does not synthesize racial variants
by subdividing the Nord mesh. Converted models and textures remain local owned
assets and are never part of the public source export.

Install the paired `progs/hands/` models, `gfx/hand-models.awh` catalogue and
matching `gfx/hand-torch.awt` together. Keep the original `gfx/torch.awt` for
legacy models and guard emitters. Missing or malformed catalogue emitter data
disables the optional pairs; fallback always restores legacy model and emitter
timing/anchors together. AWH1 is bounded to 32 entries. The renderer
selects only the current pair, preserves the 28-fist/8-torch frame contract and
resets model pointers before map memory is released. Absent, malformed, missing
or wrong-frame-count pairs fall back together to `v_nord.mdl`/`v_torch.mdl`.
Keeping the catalogue absent retains the legacy path. Sprite hands still use
their existing baked appearance; this catalogue applies to 3D hands only.

Race selection, malformed-catalogue handling, frame preservation and paired
fallback have focused Linux Docker fixtures. Representative owned human/beast
conversion has been checked. All 20 playable race/sex pairs now complete with
matching fists and torch models. One bounded owned-data cache is shared during
catalogue generation; a representative cached conversion remains byte-identical
to its standalone output. A private native hand-only overlay selected visibly
distinct Argonian male fists through the actual character choice and ordinary
demo playback. The post-registration Nord character showed live punches and
torch on/off with matching arms. Live beast punching and torch use remain
unverified because that fresh character-creation scene correctly restricts
combat before registration. Source punch windup still moves below the viewport;
the general punch framing/self-occlusion report remains open. These candidates
do not change the default.

## Connected surfaces before a smaller triangle budget

Hands are the first implementation target. NPC conversion must later adopt the
same quality gates rather than generating another large asset set now.
`tools/hand_geometry.py` preserves authored face connectivity and sampled vertex
trajectories, baking repeated UV rectangles and any vertex colour gradients
without moving their geometry. Its automatic surface oracle ignores texture
vertex copies only when their complete animated trajectories coincide. It
rejects missing/reversed faces and seams that separate in any sampled pose.
Authored open sleeve ends are recorded, not filled with invented triangles.

`tools/hand_seam_reduction.py` is a conservative reduction prototype, separate
from the selectable conversion profiles. It locks all authored shape boundaries
(including material, UV and joint splits) and non-manifold edges. Interior edge
collapses must satisfy the manifold link condition; preserve boundary edges;
avoid duplicate faces; and preserve orientation, area, UV orientation and
bounded displacement across every exported animation sample. The surviving
endpoint keeps its exact source trajectory, UV and tint. No nearest-face motion
transfer, independent seam movement or hole filling is permitted. If the budget
cannot be reached safely, the report records the achieved count and refusal.

For the measured Nord fixture, the authored model has 1,092 triangles, 752
vertices and 245,736 bytes. The conservative 0.5-unit/0.125-UV trial retains
834 triangles, 623 vertices and 225,612 bytes; it does not meet the 480 goal.
Both retain the same 40 welded authored open boundary edges, with no new edges.
The 834-triangle trial subsequently failed the stricter all-pose coverage oracle:
several poses lost 2-7 interior pixels. It is rejected as a default candidate.
An optional projection-lock helper also protects sampled silhouette/near-plane
vertices and quantization extrema; its outputs still require the coverage gate.
The existing 311-triangle profile transforms 933 vertices because its texture
atlas duplicates vertices per face. Triangle count alone therefore does not
predict renderer cost.

Before adopting a reduced model, automatically compare all exported poses with
the authored reference: boundary trajectories, connected components, winding,
projected interior coverage, silhouette, texture seams and near-plane clipping.
Native idle/draw/lower/punch and torch toggles must then pass with a matching
engine, fixed camera and measured memory/rendering cost. Topology checks alone
do not prove absence of self-intersection or good appearance. Preserve the
legacy profile and reject any candidate with a newly visible opening, even if
its face-count target was met. Apply these same gates to future NPC reduction;
do not silently cap or stitch an intentional authored opening.


## Detailed-model depth arithmetic candidate

The authored-detail models exposed a thin-triangle inverse-depth gradient that
exceeds signed 32-bit range even when every covered pixel's depth is in range.
The C alias span path now converts and steps those intermediate values with
defined unsigned arithmetic, retaining its existing span layout and integer
pixel loop. This is supported by a wider-arithmetic reference, rather than
treating suppression of an overflow diagnostic as correctness.

The public synthetic fixture compares every framebuffer and depth-buffer byte
for 168 skinny-triangle and near/screen-clipping cases, including an occluding
surface. The owned catalogue check covers all 720 poses of the 40 models; the
reference reports no active pixel outside the representable depth range and
matches the candidate exactly. The original model's 28 outputs remain
byte-identical. The old span code fails the synthetic overflow regression.
AddressSanitizer, undefined-behavior and float-cast checks pass. The 68040/FPU
translation unit compiles without warnings; its object grows by 216 bytes.

On the unchanged earlier engine, a complete 4,447-frame replay completed at
49.1 emulated FPS with the authored Nord model and 49.9 with the original model,
with no surface or edge overflow. Session hand counters average 0.241 and
0.182 ms per frame respectively, but include differing console/live-map delays;
they are not isolated rendering costs. These capped emulator measurements do
not establish physical-Amiga performance. The corrected depth path subsequently
completed the same 4,447-frame demo from the title screen at 49.5 emulated FPS,
returned normally at EOF, and rendered the bounded race/punch/torch samples
above without surface or edge overflow. This is limited native acceptance,
not a complete integration or physical-Amiga performance claim. The reduction
and catalogue defaults remain unchanged; broader live beast and punch-quality
acceptance remains pending.
