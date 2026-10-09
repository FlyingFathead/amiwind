# HORIZON-HOLES-31: distant buildings break up against the sky

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
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

## Status: 7 October 2026

8 October 2026: not re-checked on v0.0.32. The owner's verdict on v0.0.32-dev3 covers the
horizon fill ([HORIZON-FLORA-SPRITES-32](HORIZON-FLORA-SPRITES-32.md)), not this view; the
v0.0.32-dev3 smoke frames of Balmora are close views. The across-the-river Balmora view at sunset
is needed on a v0.0.32 build before this can be closed.

Open. Needs work; cause understood in outline, not yet measured.

## Symptom

Looking across the river at Balmora at sunset, the far buildings are a flat
fog-brown silhouette with the sky showing through holes and jagged gaps
(owner screenshots at 17:59, 18:19 and 18:24, local about (284..319,
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

v0.0.31-dev2: from the west bank opposite Balmora (global about -19300 -11800),
`dbg set time 1800`, look east across the river.

## Repair

Not done. Proposed: extend the distant fill with each placed object's
simplified collision hull (real geometry, a few dozen flat polygons per
building) drawn in the fog colour beyond the fog plane, and cull objects whole
rather than piece by piece near the limit. Cost to be measured with an FS-UAE
frame-time sweep before enabling.

## Verification

Pending: the same views without holes, and the frame-time cost.

## Prevention

Distance views of every town against a bright sky in the capture set.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Distance drawing (horizon, fog, sky, far edges) (`distance-drawing`). Far-plane fog, the skyline fill, distant sprites and resident ground. See [families](README.md#families).

- [FOG-TOWN-HEAVY-32](FOG-TOWN-HEAVY-32.md): Heavy fog at the Vivec Arena and in Balmora in v0.0.32-dev1
- GEO-02 (no report page): Seyda Neen ground ends before the world terrain handoff
- [HORIZON-FLORA-SPRITES-32](HORIZON-FLORA-SPRITES-32.md): Horizon silhouetting: not yet perfect
- HORIZON-POP-29 (no report page): Ashlands horizon pops or breaks up while turning
- LAND-HORIZON-GAPS-29 (no report page): Sky visible through gaps in distant resident ground
- [SEYDA-WALL-SHAPE-31](SEYDA-WALL-SHAPE-31.md): Dark shape pokes out of a stone wall by the Seyda Neen shore
- [SHELL-TEXTURE-VOTE-32](SHELL-TEXTURE-VOTE-32.md): Distant shells: door and grille textures win over large sealed areas
- SKY-NIGHT-COVER-29 (no report page): Dense night clouds rarely reveal moons/stars
- SKY-STARS-28 (no report page): Enlarged stars cover original night artwork
- SKY-VISUAL-01 (no report page): Sky-only day/night remap clashed with gray distance fog
- TREE-PILLAR-28 (no report page): Sprite-tree roots extend into unintended striped pillars

Related bugs in other categories:

- [CHIM-FAR-OBJECTS-33](CHIM-FAR-OBJECTS-33.md): Houses between the CHIM ring and the legacy overlap depth are missing from the fogged horizon
- [VIVEC-DISTANT-BRIDGES-32](VIVEC-DISTANT-BRIDGES-32.md): Distant bridges between the Vivec cantons are not drawn

<!-- END GENERATED CATEGORY -->
