# HORIZON-HOLES-31: distant buildings break up against the sky

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 2 times; something has to be done

- Reported with v0.0.44 at 2026-10-19 18:28 +0300: maintainer: distant topology still breaks up (counted as a bug); idea: a very low-poly depth/silhouette model of the world for the distance, with the far-terrain and mold-shell layers; later to-do
- Reported with v0.0.46 at 2026-10-20 20:09 +0300: Listed under Known in this build in the v0.0.46 release notes (still open at the release).

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 7 October 2026, in v0.0.31-dev2 |
| Where | far culling and distant land fill (Balmora, Vivec Arena) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31-dev2, v0.0.32-dev1 (last seen) |
| Severity | medium: Distant buildings break up against the sky with holes; a visible fault with proposed silhouette fix. |
| Family | Distance drawing (horizon, fog, sky, far edges) (`distance-drawing`) |
| Playtest version | v0.0.31-dev2 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (20 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 2 times; something has to be done](#persisting-reported-2-times-something-has-to-be-done)
- [Status: 7 October 2026](#status-7-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Maintainer evidence reconciliation, 13 October 2026](#maintainer-evidence-reconciliation-13-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 7 October 2026

8 October 2026: not re-checked on v0.0.32. The maintainer's verdict on v0.0.32-dev3 covers the
horizon fill ([HORIZON-FLORA-SPRITES-32](HORIZON-FLORA-SPRITES-32.md)), not this view; the
v0.0.32-dev3 smoke frames of Balmora are close views. The across-the-river Balmora view at sunset
is needed on a v0.0.32 build before this can be closed.

Open. Needs work; cause understood in outline, not yet measured.

## Symptom

Looking across the river at Balmora at sunset, the far buildings are a flat
fog-brown silhouette with the sky showing through holes and jagged gaps
(maintainer screenshots at 17:59, 18:19 and 18:24, local about (284..319,
116..260, 62), facing east).

## Where

Far culling (`aw_cull`, forward far plane in `aw_fog.c`) and the distant land
fill (`aw_horizon.c`, `AW_HorizonDraw`).

## How it happened

Geometry beyond the draw distance is culled per node and surface, so a large
building near the limit loses some pieces and keeps others; the kept pieces
are fully fogged. The distant fill that closes the view behind the fog plane
draws only land polygons (flat fog colour), not buildings, so the gaps show
sky.

v0.0.32-dev1 (8 October 2026): the Vivec Arena shows the same break-up close up (upper parts
patchy, sky and fog showing through) and turns into a flat fog silhouette from about 1,500 units;
the heavier fog is recorded separately as [FOG-TOWN-HEAVY-32](FOG-TOWN-HEAVY-32.md).

## Why it was not caught

Distance views of towns against a bright sky were not part of the checks; the
land fill was designed and tested for terrain only.

## Reproduction

12 October 2026, additional maintainer evidence in v0.0.38-dev2: with `dbg fog off`,
a triangular sky-coloured opening appears in the terrain silhouette at global
25183,122620,1354, local -872,959,-557, cell 3,14, heading 257, pitch 1,
game time 12:40. This is a related symptom, not proof of the same cause as the
older building holes. Exact installed map identity and matched original/native
reproduction remain pending. Investigate missing terrain, culling and distant
fill separately; preserve the previously approved silhouette algorithm and
measure CPU/RAM costs before accepting any additional fill method.

A second fog-off maintainer image that day shows scattered dark silhouettes with
sky-coloured gaps at global 25389,127416,1560, local -820,110,-377, cell 3,15,
heading 27, pitch 5, time 16:19. The requested investigation is coherent horizon
coverage; filling arbitrary screen gaps would risk occluding legitimate sky.
Identify original terrain and object coverage before choosing a fill method.

Source inspection on 12 October found that `AW_FogDraw` calls the existing
`AW_HorizonDraw` LAND fill only when fog is enabled. Therefore `dbg fog off`
also suppresses this fill; that is a candidate explanation for the fog-off
evidence, not a diagnosis of every historical hole. Compare fog and terrain
occlusion independently before introducing another silhouette algorithm. The
maintainer reports the broader problem since the beginning of the project; the
earliest affected build remains unverified.

If this investigation produces an additional distant-terrain method, document
it as a separately named and versioned feature with its baseline, implementation
status, measured CPU/RAM cost and comparison evidence. No new terrain method has
been implemented or accepted by the observations above.

v0.0.31-dev2: from the west bank opposite Balmora (global about -19300 -11800),
`dbg set time 1800`, look east across the river.

## Repair

### Land Fill Independence v1 (candidate, 12 October 2026)

An additional maintainer sequence in v0.0.38-dev2 shows large distant terrain
openings in the Ashlands, cell 0,17. The visible failure pose is global
5312,141714,1125, heading 6, pitch 6, time 06:06. After moving forward, the
maintainer's next image shows continuous ground at 4637,143445,769, heading 352,
pitch -3, time 06:11. These are different poses, not a matched fix comparison.
The maintainer describes this as "GAPING HOLES IN DISTANT TERRAIN" and reports it
across terrain, not only at one location. Keep it under this existing issue.

Another fog-off image shows extensive sky exposure between terrain fragments
at global 3219,148875,1959, local -219,-669,105, cell 0,18, heading 261,
pitch 9, time 09:08. This remains a reproduction, not candidate acceptance.

The candidate separates geometric LAND fill from colour fog. Saved setting
`aw_land_fill 1` (default) allows the selected LAND passes with fog on or off;
`dbg land fill 0` disables them for A/B, and `dbg land fill 1` restores them.
It reuses AmiQuake's inverse-depth buffer and the existing resident LAND and
CHIM far-layer routines. There is no new heightfield, screen-sized buffer or
second fog-colour pass. The old skyline method is unchanged.

The legacy resident LAND rasterizer remains separately experimental and off
by default: `dbg land method 1` enables it; `dbg land method 0` restores its
prior selection. The master fill switch does not create absent terrain or
enable that separate method. Consequently this candidate does not establish
that the pictured legacy holes are repaired. A continuous original-heightfield
base remains an investigation, not an implemented replacement.

Verification must compare the four fog/fill combinations with fixed camera,
clock and renderer method in the same executable, on both legacy and CHIM
maps. Record native frame time, RAM, rasterized pixels and accepted image
differences; repeat against matched OpenMW views, including true valleys and
near foreground. Native cost and visual acceptance remain pending. Missing
palette data and interiors must skip the pass safely.

Not done. Also proposed: extend the distant fill with each placed object's
simplified collision hull (real geometry, a few dozen flat polygons per
building) drawn in the fog colour beyond the fog plane, and cull objects whole
rather than piece by piece near the limit. Cost to be measured with an FS-UAE
frame-time sweep before enabling.

Plan of 19 October 2026 (maintainer): no distance cut where the fog is still see-through, then a far shell of the
whole island drawn in one fog colour through the engine's existing solid-surface path, with the real world emerging
from it and grouped, overlapping switches so no transition leaves a hole ([distant terrain
notes](../DISTANT_TERRAIN.md#horizon-ponderings-the-island-cut-out-19-october-2026),
[roadmap](../ROADMAP.md#distant-views-without-pop-in-and-the-screen-the-amiga-need-not-redraw-19-october-2026)).
This bug is fixed on its own as well; the shell does not merely hide it.

20 October 2026, in source (not built yet): the inventory of every distance cut against the fog's opaque distance
is on [CHIM-BRIDGE-POP-PIECES-44](CHIM-BRIDGE-POP-PIECES-44.md#every-distance-cut-and-the-fogs-opaque-distance-20-october-2026).
The far detail presets Light and Strong (`aw_cull` 3, 4, 6; Strong the default since v0.0.42) leave out pieces at
40 to 85 % of the fog distance, where the fog is not yet opaque, and every building piece is cut on its own. Two
settings answer the "cull objects whole" proposal above: the fog rule (`dbg fog rule on`, no cut before the fog is
opaque) and whole-structure cuts (`dbg cut groups on`, structures found by the CHIM builder cut on one box); both
off until the maintainer's in-game A/B, including the across-the-river Balmora view at sunset of this report.

## Verification

Pending: the same views without holes, and the frame-time cost.

## Prevention

Distance views of every town against a bright sky in the capture set.


## Maintainer evidence reconciliation, 13 October 2026

The following maintainer screenshot evidence was visually reviewed. Original images
remain in the private evidence archive; identifiers bind this report to those
originals. This records reported symptoms and comparison controls, not a repair
or runtime acceptance. Missing build or pose information remains unknown.

- `OWNER-20261012-155033`: SHA-256 `01f1517b9d79178f907cae9869240c9071f29f5c21bfd480764ba9bc60ed70f2`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-155034`: SHA-256 `450b93baf8e4efeaa4fd7f48e819b8170ddf0091a0e1b2f3be04c86e623e55cb`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-180827`: SHA-256 `7ba093d4b913fa7dd3586b59dc3ffe47758fe50c7f962738c2193e53ecdc0597`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-181604`: SHA-256 `75ed20dc562285d9ab372163202553a6606c6509c63c724d17cd9d6c507d391b`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-181654`: SHA-256 `feec712f2873ec14e94ae79bae5ad085f3df7df7c2ddf6558ff10cf14ff20999`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-181817`: SHA-256 `8ae278dca8eb9522bbaaea1380c42afb02d3487e99043dd5fb8be7297cba01f4`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-182831`: SHA-256 `6f6d38c49c7a8efe4f467a7fa92a90a512c7bee5a9bd24c388b8740a2aa4ec3f`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-182842`: SHA-256 `6ecf6a01d7566a0a128e92b8d625bf555462aca6847045b353e255bd53787511`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-182850`: SHA-256 `1bab21bb868359d6f7c09b9c586ac9eadadaaf27ffe56dd7596433e92d3e0f31`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-183507`: SHA-256 `4f6b018534bbe0bdf4843473cc009e6300c34fe1acee6ab417d4c8b8cf3b5e48`. Screenshot association checked; no repair or behavioral acceptance inferred.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Distance drawing (horizon, fog, sky, far edges) (`distance-drawing`). Far-plane fog, the skyline fill, distant sprites and resident ground. See [families](README.md#families).

- [CHIM-BRIDGE-POP-PIECES-44](CHIM-BRIDGE-POP-PIECES-44.md): Bridges pop into view piece by piece as the player approaches (Balmora)
- [CHIM-TERRAIN-TEXTURE-BLOCKY-43](CHIM-TERRAIN-TEXTURE-BLOCKY-43.md): Roads and paths on the ground look blocky: each texture square is drawn with hard edges instead of blending into its neighbours
- [FOG-TOWN-HEAVY-32](FOG-TOWN-HEAVY-32.md): Heavy fog at the Vivec Arena and in Balmora in v0.0.32-dev1
- GEO-02 (no report page): Seyda Neen ground ends before the world terrain handoff
- [HORIZON-FLORA-SPRITES-32](HORIZON-FLORA-SPRITES-32.md): Horizon silhouetting: not yet perfect
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

- [CHIM-FAR-OBJECTS-33](CHIM-FAR-OBJECTS-33.md): Houses between the CHIM ring and the legacy overlap depth are missing from the fogged horizon
- [VIVEC-DISTANT-BRIDGES-32](VIVEC-DISTANT-BRIDGES-32.md): Distant bridges between the Vivec cantons are not drawn

<!-- END GENERATED CATEGORY -->
