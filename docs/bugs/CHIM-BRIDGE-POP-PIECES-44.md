# CHIM-BRIDGE-POP-PIECES-44: bridges pop into view piece by piece as the player approaches (Balmora)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 19 October 2026, in v0.0.44 |
| Where | Balmora bridges over the Odai, approaching from a distance |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.44 (last seen) |
| Severity | medium: Visible pop-in of a landmark in the best-looking town |
| Family | Distance drawing (horizon, fog, sky, far edges) (`distance-drawing`) |
| CHIM | Rendering and visibility ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_19_v0.0.44_release-try2_c84f8506 |
| From commit | source c84f850, engine c84f850, CHIM world c84f850 |
| CHIM engine version | CHIM 0.2.1, engine c84f850, world format 0.7 |
| Platform or emulator | unknown (maintainer playtest report, emulator not stated) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (20 October 2026)._

<!-- contents start -->
## Contents

- [Status: 20 October 2026](#status-20-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Every distance cut, and the fog's opaque distance (20 October 2026)](#every-distance-cut-and-the-fogs-opaque-distance-20-october-2026)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 20 October 2026

Cause found in the source and measured on paper from the v0.0.45 release world; fix in source on the
v0.0.46-fog-cuts line, both parts selectable and off by default until the maintainer has seen the in-game A/B
(below). Not built, not seen in game yet.

19 October 2026: reported by the maintainer; cause suspected, not checked.

## Symptom

Walking toward Balmora, a bridge over the Odai appears one piece at a time: for a while it is visibly cut, with
gaps between the parts already drawn. The maintainer: a visual glitch that stands out because the rest of Balmora
holds up well at a distance.

## Where

Balmora's bridges, approached from a distance; likely every object built from several placements.

## How it happened

Suspected on 19 October: each bridge segment is its own placement with its own distance test, so the segments
cross the draw distance one at a time instead of the bridge as a whole.

Found on 20 October 2026, in two parts:

1. **Cuts made where the fog is still see-through.** The fog (`AW_FogDepths` in `aw_fog.c`) is a linear ramp:
   level 1 of 15 at 44 % of the fog distance D, level 15 (every colour the one fog colour) at D. The default far
   detail since v0.0.42, Strong (`aw_cull 4`), leaves out a placement whose near side lies past a share of D
   chosen by its size: 40 % for a radius under 32 units, 60 % under 128, 85 % under 512, 100 % from 512. At 40 %
   the fog is clear (level 0), at 60 % it is level 5, at 85 % level 11. So a small piece vanishes out of clear
   air, a hillside rock at level 5 to 11, and the bigger pieces of the same bridge stay.
2. **A structure is cut piece by piece.** Each placement is tested on its own sphere, so the pieces of one
   structure leave at different distances: the short gap pieces between Vivec's walkway spans first, the long
   spans later; one canton cut into tiles by the large-model cut loses tiles one by one; a town wall loses its
   gate pieces before its long sections. The far plane (at D + 16) does the same to the far end of a long
   structure while its near end is still drawn.

## Every distance cut, and the fog's opaque distance (20 October 2026)

D is the effective fog distance, `AW_DrawDistance()`: the setting (540 by default), limited by a CHIM world's
data (draw distance + hysteresis it was built with, 636 for the v0.0.45 world), a legacy exterior's town table
(540) and, with `aw_fog_location 1`, a place's own day and night distance (Balmora 300 and 250). Every cut
below is taken from that same D, so a shorter fog in one place moves the cuts with it. There is no weather in
the fog distance: the sky and fog colours follow the clock only (`r_sky.c`), so one table holds for every region
and weather. The fog is fully opaque at D.

| Cut | Where | Distance | Before the fog end? |
| --- | --- | --- | --- |
| Far plane, brush models (placements) | `aw_fog.c` `AW_ModelVisible`, every `aw_cull` but 0 | near side past D + 16, per placement | no (at it), but per piece: a long structure loses its far end |
| Far plane, world nodes (terrain, Quake world) | `AW_NodeVisible`, `r_bsp.c`, `r_efrag.c` | node box past D + 16 | no |
| Far plane, alias models and sprites (NPCs, flora) | `r_main.c` `R_DrawEntitiesOnList` | sphere past D + 16 | no |
| Fog-exact skip (`aw_cull` 2 and up) | `AW_BrushPassFar` | only where every covered pixel is already the one fog colour and hides only fog colour | no: no pixel changes |
| Size-scaled cut-off, Light (`aw_cull 3`) | `AW_BrushPassFar`, `size_cut_share` | 50 / 75 / 100 / 100 % of D by radius class | **yes**, fog level 2 and 8 |
| Size-scaled cut-off, Strong (`aw_cull 4`, the default since v0.0.42; also in 6) | same | 40 / 60 / 85 / 100 % of D | **yes**, fog level 0, 5 and 11 |
| Far detail step (`aw_cull 5`, 6) | `AW_BrushPassFar`, `r_bsp.c` | faces under 2 pixels, from 50 % of D | **yes**, level 2 |
| CHIM chunk ring (residency) | `chim_chunks.c` `ChimChunks_ActiveRadius` | chunk square past D + hysteresis (96) | no |
| CHIM placement visibility rows | `tools/chim/world.py` `chunk_visibility` | ring of draw distance + hysteresis, chunk square to square, then ground occlusion | no (occlusion is not a distance cut) |
| CHIM far terrain layer | `chim_far.c` | drawn only beyond D, to `chim_far_reach` 896 | no (it fills, it never cuts) |
| CHIM zone release under memory pressure | `chim_chunks.c` | chunks past the active radius first, then inside it | not a distance cut; can drop chunks inside D ([CHIM-ZONE-RELEASE-FLICKER-42](CHIM-ZONE-RELEASE-FLICKER-42.md)) |
| `chim_draw_distance` (debug override) | `chim_world.c` | any value; 0 = follows D | only when set by hand |
| NPC model levels | `aw_npc_lod.c` | bands 64 / 256 / 512 | no cut: a simpler model, never none |
| Legacy region maps (open world outside CHIM) | `tools/import_town.py`, town table | 540, maps hold their neighbours 896 out | no |
| Vivec Arena preview (legacy) | `config/vivec_arena.json` | bounds +-1536, draw 540 | the frame edge, not the fog ([VIVEC-ARENA-FRAME-EDGE-32](VIVEC-ARENA-FRAME-EDGE-32.md)) |

So the only cuts before the fog end are the far detail options (`aw_cull` 3 to 6), and the per-piece testing of
long structures. The builder-written configuration sets neither (it writes `aw_drawdistance 540`; `aw_cull` is
the player's setting, Strong by default).

## Why it was not caught

No check looks at objects made of several placements as they come into view.

## Reproduction

Always, as far as reported: approach a Balmora bridge from outside the draw distance.

## Repair

To do: confirm the cause with the entity inspector on a Balmora bridge. Fix candidates: one distance test for a
group of placements that form one object, or the island cut-out of the
[distant terrain notes](../DISTANT_TERRAIN.md#horizon-ponderings-the-island-cut-out-19-october-2026) standing in
until every piece is drawn.

Plan of 19 October 2026 (maintainer): no distance cut where the fog is still see-through, then a far shell of the
whole island drawn in one fog colour through the engine's existing solid-surface path, with the real world emerging
from it and grouped, overlapping switches so no transition leaves a hole ([distant terrain
notes](../DISTANT_TERRAIN.md#horizon-ponderings-the-island-cut-out-19-october-2026),
[roadmap](../ROADMAP.md#distant-views-without-pop-in-and-the-screen-the-amiga-need-not-redraw-19-october-2026)).
This bug is fixed on its own as well; the shell does not merely hide it.

### In source, 20 October 2026 (v0.0.46-fog-cuts; not built yet)

Steps (1) and (2) of the [proposed order](../ROADMAP.md#distant-views-without-pop-in-and-the-screen-the-amiga-need-not-redraw-19-october-2026),
each a saved switch, both off (the method up to v0.0.45) until the maintainer has seen the in-game A/B:

Both are switches in the saved far detail setting `aw_cull` (8 and 16 above its far test 0 to 7; `dbg fog rule
on`, `dbg cut groups on` set them and Options > Far detail keeps them), so they add no console variable or
command to the engine's resident registry.

- **The fog rule, `dbg fog rule on`** (`aw_cull` + 8): no share of the size-scaled cut-off is below the whole
  fog distance, and the far detail step starts only where a model's near side lies past it. The cuts then sit
  where the fog is opaque; for the Light and Strong presets that is the picture of Full (`aw_cull 1`). The
  fog-exact skip, which changes no pixel, stays.
- **Whole-structure cuts, `dbg cut groups on`** (`aw_cull` + 16): the CHIM builder finds the long structures in
  each frame's own data (`tools/chim/cuts.py`): placements of one mesh family (the model name without its variant
  suffixes and trailing index numbers; one name's stem a token prefix of the other's, so `ex_vivec_b`,
  `ex_vivec_b_wb` and `ex_vivec_b_wb_gap` are one family, and the tiles of one cut model are one) whose drawn
  boxes come within 64 units of each other (Vivec's walkway spans stand 51 apart), joined transitively, at least
  256 units long. No hand list. Each frame's structures go into a sidecar of its frame map, `maps/<frame
  map>.cut` (a box per structure, the placement ids of its members; like the far terrain's `.far`); the engine
  (`chim_cuts.c`) gives each piece its structure's box when its chunk becomes active, and the far plane and the
  size cut-off then test that box with the structure's size class, so the structure is drawn, fogged and left out
  as one piece. No sidecar, or a damaged one: every piece on its own, as before.
- **The builder check:** after writing the sidecars the CHIM world step runs the fog check on every frame
  (`chim.cuts.fog_cut_failures`): the chunk ring against the fog end, every structure's box against its
  members' boxes; a world with a cut nearer than its fog end is refused, naming the frame and the cut. The check
  also states the engine's presets: without the fog rule Strong cuts at 216 units of 540 (fog level 0), with it
  no preset cuts before 540.

Island-wide on the v0.0.45 release world (read only): 31,764 structures in 1,182 of 1,351 frames, 238,633 of
469,267 placements (most of them rock hillsides), 2.3 MB of sidecars, at most 23.8 KB for one frame (Vivec),
which is also about what that frame's tables take in the low Hunk at map start. The check found nothing nearer
than the fog end in the world data.

### Cost on paper, 20 October 2026

From the v0.0.45 release world (`tools/chim/cuts.py WORLD --faces --report=CX,CY`): placements and faces inside
the distance cuts at D = 540, averaged over viewpoints on a 128-unit grid over each frame less half a cell at its
edges, all around (no view frustum, no occlusion, no fog-exact skipping, horizontal distances; so the absolute
numbers are about four times what one view draws, the ratios are the point). A = today's default, Strong per
piece.

| Frame | A Strong, per piece | B fog rule | C structures | D fog rule + structures | E Full, per piece | F Full + structures |
| --- | --- | --- | --- | --- | --- | --- |
| Balmora (-3,-2), 1,473 placements, 82 structures | 29.0 placements, 4,759 faces | +85 %, +56 % faces | +50 %, +43 % | +115 %, +82 % | +94 %, +63 % | +122 %, +87 % |
| Vivec city (4,-12), 7,537 placements, 398 structures | 34.2, 6,350 | +68 %, +51 % | +17 %, +8 % | +77 %, +53 % | +75 %, +57 % | +84 %, +59 % |
| Ghostgate (2,5), 271 placements, 29 structures | 24.8, 5,494 | +37 %, +22 % | +45 %, +22 % | +63 %, +34 % | +42 %, +26 % | +66 %, +37 % |

Reading: the fog rule costs about what Strong saved (it is the Full picture for those presets; Strong was
measured at -17 to -27 % view time against Full at the Balmora benchmark cameras, docs/performance/FAR-TEST.md).
Whole structures on top of the fog rule add 2 to 18 % more faces in range (D against B). Much of the added
geometry lies past 85 % of D, where the fog-exact skip leaves out what is fully fogged below the horizon, so the
frame-time cost is smaller than the face count; it is measured in the build, not claimed here. If the 68040
cannot afford it, the fog distance comes down instead of the cut moving into clear air: the rule stays.

## Verification

Needs a build and an in-game A/B, at fixed poses with `dbg cam mark`, headlamp off, the clock held at noon, an mp4
per pose (one slow approach or turn, same motion for every variant) and the stills:

1. Vivec's walkways seen from the water between the cantons, approaching;
2. Balmora's walls and bridges from across the Odai, walking toward town;
3. a hillside of rocks (the West Gash around Balmora, or the Ashlands north of Vivec);
4. the Ghostfence from below, walking toward Ghostgate.

Variants at each pose: A `aw_cull 4` (today), B `aw_cull 12` (+ fog rule), C `aw_cull 20` (+ cut groups), D `aw_cull 28`
(both), E
`aw_cull 1` (drift control: today's Full), with `dbg rcount 1` frame time and brush faces per variant. Then the
maintainer decides the defaults.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Distance drawing (horizon, fog, sky, far edges) (`distance-drawing`). Far-plane fog, the skyline fill, distant sprites and resident ground. See [families](README.md#families).

- [CHIM-TERRAIN-TEXTURE-BLOCKY-43](CHIM-TERRAIN-TEXTURE-BLOCKY-43.md): Roads and paths on the ground look blocky: each texture square is drawn with hard edges instead of blending into its neighbours
- [FOG-TOWN-HEAVY-32](FOG-TOWN-HEAVY-32.md): Heavy fog at the Vivec Arena and in Balmora in v0.0.32-dev1
- GEO-02 (no report page): Seyda Neen ground ends before the world terrain handoff
- [HORIZON-FLORA-SPRITES-32](HORIZON-FLORA-SPRITES-32.md): Horizon silhouetting: not yet perfect
- [HORIZON-HOLES-31](HORIZON-HOLES-31.md): Distant buildings break up against the sky
- HORIZON-POP-29 (no report page): Ashlands horizon pops or breaks up while turning
- [LAND-HORIZON-GAPS-29](LAND-HORIZON-GAPS-29.md): Sky visible through gaps in distant resident ground
- [RENDER-FOG-PASS-COST-33](RENDER-FOG-PASS-COST-33.md): The per-pixel fog and day-night sky pass costs 150-210 ms per frame on a slow 68040
- [SEYDA-WALL-SHAPE-31](SEYDA-WALL-SHAPE-31.md): Dark shape pokes out of a stone wall by the Seyda Neen shore
- [SHELL-TEXTURE-VOTE-32](SHELL-TEXTURE-VOTE-32.md): Distant shells: door and grille textures win over large sealed areas
- SKY-NIGHT-COVER-29 (no report page): Dense night clouds rarely reveal moons/stars
- SKY-STARS-28 (no report page): Enlarged stars cover original night artwork
- SKY-VISUAL-01 (no report page): Sky-only day/night remap clashed with gray distance fog
- TREE-PILLAR-28 (no report page): Sprite-tree roots extend into unintended striped pillars
- [TREE-VIEW-FLOAT-38](TREE-VIEW-FLOAT-38.md): Sprite tree appears detached from terrain from particular viewing directions
- [WATER-UNDERWATER-SKY-44](WATER-UNDERWATER-SKY-44.md): Under water the distance shows the sky's clouds instead of blue water

Related bugs in other categories:

- [CHIM-ZONE-RELEASE-FLICKER-42](CHIM-ZONE-RELEASE-FLICKER-42.md): Full CHIM zone: distant buildings pop in and out while standing still, and the retry costs frames

<!-- END GENERATED CATEGORY -->
