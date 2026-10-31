# World tree sprites and the Balmora comparison zone

_Last updated with AmiWind v0.0.56 (30 October 2026)._

<!-- contents start -->
## Contents

- [Open sprite-root regression - 4 October 2026](#open-sprite-root-regression---4-october-2026)
- [Study: cheap trees with some depth (29 October 2026)](#study-cheap-trees-with-some-depth-29-october-2026)
- [Balmora mesh exclusion](#balmora-mesh-exclusion)
- [Reproducible shared sprite conversion](#reproducible-shared-sprite-conversion)
- [Scale and visibility investigation](#scale-and-visibility-investigation)
- [Acceptance](#acceptance)
- [Converter evidence after v0.0.27](#converter-evidence-after-v0027)
- [Current development checkpoint: Trees and Grass](#current-development-checkpoint-trees-and-grass)
- [Reserves fail fast (11 October 2026)](#reserves-fail-fast-11-october-2026)

<!-- contents end -->

## Open sprite-root regression - 4 October 2026

A maintainer screenshot from the post-release v0.0.28 playtest shows an unintended
vertically striped pillar beneath a sprite-tree trunk on a slope. The exact
placement still needs target replay. A source reproduction found a scale and
authored-origin mismatch between projected geometry and sprite texture gradients.
The old rasterizer produced 90 incorrect pixels of 105 checked; the corrected
v0.0.29 candidate passes seven real projection/raster cases. Assets, transforms
and collision are unchanged. Native root/contact acceptance remains pending. Do not treat earlier sprite conversion
checks as acceptance of this root/contact defect; preserve original intended
roots when investigating. See
[TREE-PILLAR-28](journals/BUG_JOURNAL-v0.0.29.md#tree-pillar-28-unintended-pillar-beneath-sprite-tree-roots-open).

Development after v0.0.27; not yet an enabled world-wide runtime feature.

Use the original source placements, positions and scales. Bake one shared sprite
image per tree model rather than a fresh image for every placement or scale.
Billboard trees deliberately approximate the original three-dimensional view;
tilted trunks, collision and interactive stumps need explicit preservation checks.
Never silently omit non-unit scales or replace container state with decoration.
Generated sprites, original inputs and preview images remain private.

## Study: cheap trees with some depth (29 October 2026)

The maintainer asked how trees could stay cheap and still have some dimensionality. Two classic bitmap
techniques, both drawing one baked tree image (branches and foliage in the picture, transparent around the outline)
instead of modelled geometry:

| Technique | Seen from above | Pieces | What it gives | What it costs |
| --- | --- | --- | --- | --- |
| Camera-facing billboard (what the sprite trees are today; Daggerfall-style) | One line turning around the trunk | 1 panel | The same full tree from every side; the cheapest fill | Flat: no parallax, the tree turns with the player; a slope shows its root edge |
| Crossed planes, 2 panels at 90 degrees | A cross | 4 half-panels | Fixed in the world: real parallax while walking past, no turning | Twice the panels; the edge-on panel shows as a thin line at 45 degree steps; more overdraw |
| Crossed planes, 4 panels at 45 degrees | An eight-spoked star | 8 half-panels | A rounder crown from every side, steadier silhouette | Four times the panels and the overdraw of one billboard |

Each full panel crosses the trunk, so N panels make 2N half-panels around it. The engine already has the pieces
for the star (the maintainer's pick, 29 October 2026: seen from above, two crossed planes that together make eight
half-planes): Quake's SPR_ORIENTED sprite keeps its own angle in the world (engine/aga/src/r_sprite.c), so a
tree becomes four oriented sprites at 0, 45, 90 and 135 degrees on the trunk, the same sprite pixels the billboard
uses, no new sprite format. The cost is four sprites drawn instead of one, which is why it belongs near the player
only. Still to check in our engine: that intersecting sprites sort per pixel (the depth test and write of the
sprite spans), so the planes cut each other cleanly. Crossed panels stay fixed in the world
(a placed model, like any static mesh), while a billboard turns to face the camera every frame.

A fourth kind, from the maintainer (29 October 2026): **directional sprites**, eight views of the tree baked at 45
degree steps, one camera-facing panel that shows the view for the angle the player looks from (the classic
eight-rotation sprite). It reads as solid from every side at a billboard's fill cost; the price is eight images per
tree model in memory instead of one; five with mirroring (the three mirrored views drawn from their opposites, as
the classic games did; a mirrored tree reads as natural). Daggerfall's own trees are single-image billboards; its
eight-direction sprites are its creatures and people. Two things to know: the draw cost per frame is the same as a
billboard (one panel, only the picture changes), and it is still a camera-facing panel, so on its own it does not
fix the pick (HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47): the pick trace must skip sprite panels either way. Quake's
sprite format has no view-angle frame choice; the engine needs that added.

**Distance levels (the maintainer, 29 October 2026: world streaming could have a level of detail where trees turn from
billboards into crossed planes or eight-sided sprites as they come nearer).** The tree's form
picked by distance in the streamer: crossed panels (or directional sprites) near the player and wherever a harvest
plant grows at the tree's foot, plain billboards far away. The switch distance is a measured number, with a margin
so trees do not flicker between forms at the boundary. And the nearest level can be the tree itself (the maintainer, 29 October 2026: with a streaming world, the tree can
simply be loaded in as the player gets closer): the original mesh streamed in
within a short radius, like any other cell content, and dropped again as the player moves on, so only the few trees
around the player cost mesh memory and drawing. Type 2's levels, nearest first: the mesh, crossed panels or
eight-direction sprites, the billboard. The Balmora mesh zone (below) gives the measured cost of a mesh tree to set
the radii from. Both stay selectable (the maintainer, 29 October 2026:
tree type 1 is the billboard and tree type 2 the new method), as a saved setting like the Arena Pit types: tree type 1
is the billboard of today, type 2 the new form with depth and the distance switch. This is the fix direction of
[HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47](bugs/HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47.md).

For AmiWind's budget, the cost that matters is fill (overdraw of the transparent pixels) and the panel count per
leaf, not the image: all three can share the one baked image per tree model this page already requires (crossed
panels can use side views baked at their angles). Candidates to measure, like for like at 32 MB Fast:
- billboards everywhere (today);
- two crossed panels near the player, billboards past a distance (the depth where it shows, the cheap path where
  it does not);
- four panels only for the few large landmark trees.

The checks under "Acceptance" apply unchanged: collision, roots on slopes (TREE-PILLAR-28), leaf membership of the
wider footprint, measured frame times and heap. Not started; a study item, nothing enabled.

### Bloodmoon: Solstheim's forests (29 October 2026)

The maintainer, on why this matters most for Bloodmoon: Solstheim has a very large number of spruce trees drawn in an
inefficient way, which makes it a real performance sink. Bloodmoon is not in the build yet: the builder
converts the base game only ([BUILD-EXPANSIONS-31](bugs/BUILD-EXPANSIONS-31.md); both expansions, exteriors and
interiors, are step 7 of the [roadmap](ROADMAP.md)), so this plan is ready before Solstheim's cells are. His direction: do them in the traditional rally
style, the way the rally games of the 1990s lined their tracks with whole forests of crossed-plane trees.

A spruce is close to the best case for that: tall, narrow and much the same from every side, so the eight-plane
star (four oriented sprites at 45 degrees) reads as a solid tree, and a cone of plain billboards reads well at a
distance. The plan for Solstheim, when its exteriors come in:
- tree type 2 from the start, with the distance levels above: the mesh only close up and only where needed (a
  harvest plant at its foot, a tree the player can bump into), the star in the middle, billboards far;
- one shared sprite set per spruce model, baked once (as this page requires for every tree);
- first step, before any design: a census of Solstheim's tree and shrub references (models, counts per cell,
  scales) from the builder's own inventory, and the frame time of a dense forest cell with meshes against
  billboards, like for like at 32 MB Fast. No Solstheim figure is measured yet.

## Balmora mesh exclusion

`config/world-flora.json` defines a staged compiler selection policy. Its source
XY rectangle is [-32768, -24576] to [-8192, 0], with Z unrestricted. It is derived
from the outer Balmora core in `config/balmora.json`, not from an expanded loading
apron. This is 24,576 source units per side, or 6,144 at the current 0.25 conversion
scale. A mismatch with the current town bounds must fail validation.

Use transformed whole-object bounds for intersection, including scale and tilt.
Objects touching the exclusion remain meshes across loading copies. The current
base-game audit identifies 68 existing Balmora tree references plus three
outside-origin footprints touching the boundary: 71 mesh-policy references,
9,002 sprite-policy references outside. The three extras require explicit
mesh coverage; the selection count alone does not establish their implementation.

The policy helper preserves source identity and exact transforms and rejects
invalid values and duplicate source keys. Its receipt states runtime activation
is false. Consumer integration, collision, bounded residency, heap auditing and
target crossings must pass before enabling the overlay or claiming completion.

## Reproducible shared sprite conversion

`tools/prepare_tree_sprites.py` accepts your owned game installation, a hashed
exterior tree census, a 768-byte palette and an output directory outside the
checkout. The census contains `master_sha256` (or `source_sha256`) and
`references` (or `placements`), each with model, source record type, cell,
reference number, position, rotation and scale. It must match your base master.

```sh
python tools/prepare_tree_sprites.py --data-files /path/to/owned/Data\ Files \
  --census /private/tree-census.json --palette /private/palette.lmp \
  --out /private/tree-sprites-001 --jobs 8
```

Quote paths containing spaces on your host. The same Python entry point works
on Windows and Linux. Repeated `--model` arguments select an explicitly marked
diagnostic subset. `--policy` selects another reviewed exclusion configuration.
The default consumes `config/world-flora.json` and writes each placement's
mesh/sprite decision, exact source transform and identity into `tree-sprites.json`.
Images are shared per model; their stable names do not depend on town-local indices.
The tool rejects source mismatches, missing models, invalid transforms and
incomplete export. Output creation refuses an existing directory.

The guided build runs this conversion as its `world-flora-assets` stage (without
`--census`: the stage takes its own inventory), then `prepare_world_flora.py` as
`world-flora`, and the image installs the overlay in the world and both towns.
Every normal AGA build does this; `--no-tree-sprites` leaves it out for debugging
only ([world flora default](LINUX_BUILD.md#world-flora-default)). The
scale-aware runtime path remains pending. A successful bake is not permission to
package unsupported instances or omit their collisions.

## Scale and visibility investigation

Observed 3 October 2026 in the v0.0.27 source: `prepare_quake.py` skips placements
whose scale differs from one by more than 0.02. The existing static sprite path
does not carry an instance scale. Extending the current path must scale quad
extents, leaf linkage and distance/culling bounds together, retain scale one for
legacy messages, validate finite positive scales, and account for added memory.

The loader's sprite bounds use header half-width/height, while frames may have
asymmetric origins. That can underestimate a frame footprint; its radius also
needs tracing. This is source evidence, not a reproduced target rendering bug.
Proposed repair: derive conservative bounds from actual frames (including grouped
frames), then use the same instance scale throughout rendering and visibility.
Do not enlarge geometry without updating leaf membership.

## Acceptance

Compare small and large instances, canopy clipping at leaf boundaries, camera
turning and vertical views, collision and both-direction map crossings. Compare
Balmora mesh performance with sprite regions using measured frame times and the
heap watcher/profiler. Audit exact final assets and packaged map payloads. Private
preview bakes and host tests do not establish Amiga gameplay acceptance.

## Converter evidence after v0.0.27

On 3 October 2026, the public converter baked all 51 base-game exterior
tree/stump model types privately and retained all 9,073 original references in
its selection receipt: 71 mesh-policy references, 9,002 sprite-policy references.
Eight Python workers completed the bake in 2.563 seconds; all SPR headers,
pixel lengths and recorded hashes passed independent readback. Ten focused
policy/converter tests passed on Windows Python. Generated images remain private.

The complete image set contains 3,642,006 pixel bytes. That is the sum across
all models, not a per-map loading estimate or permission to load every tree type.
Only required types should be resident, with per-map counts and bytes audited.
The normal image pipeline and scale-aware runtime remain unintegrated; no new
playtest, collision acceptance or performance gain is claimed by this result.

## Current development checkpoint: Trees and Grass

The next intended release is v0.0.28. Existing rocks and giant mushrooms,
including closed caps, remain. Original vegetation placements and sizes are
retained; Balmora remains a mesh-foliage comparison zone.

The automatic inventory/bake now covers 19,984 exterior references, 90 exported
geometries and 76 shared sprite images. Stateful containers remain mesh fallbacks;
2,062 ivy/lilypad references are explicitly deferred. This extends the earlier
51-model tree-only result, rather than replacing its historical evidence.

The scale-aware runtime is now applied in development source. Its first snapshot
passed 569 Linux tests (three skips), the native scale fixture and an asset-free
Amiga compile in Docker. Later float-pose and integration changes require fresh
validation. Normal builder installation and target acceptance remain incomplete;
the earlier statements that the runtime patch was unapplied are historical.

Four diagnostic retained-map overlays passed host content/reserve checks. A dense
grass region instead failed the entity reserve, as recorded in the bug journal.
An opt-in collision-packing comparison is implemented but not yet accepted.
No new playable image or FPS improvement is claimed. Final map and sprite memory
auditing, matching packaging and target lifecycle tests remain required.

## Reserves fail fast (11 October 2026)

The world flora stage reads every open-world map's scenery first (brush models against the 240 models + sprites
reserve, clipnodes against 32,767; in parallel, no compile) and converts the maps already at 70 % or more of a
reserve before all others, largest first. If one of those cannot be packed, the stage stops at once with the map
and the reserve it passes (`conversion-status.json` lists them under `budget_first`), instead of failing after
hundreds of maps. On the v0.0.36-dev5 coast build 31 of 2,201 maps go first, vf0779 among them (82 %); a collision
change that pushes it over its clipnode reserve is now seen in the first minute of the stage
(BUILD-FLORA-STAIR-PLATES-BUDGET-36).
