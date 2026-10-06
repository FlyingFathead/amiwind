# World tree sprites and the Balmora comparison zone

## Open sprite-root regression - 4 October 2026

An owner screenshot from the post-release v0.0.28 playtest shows an unintended
vertically striped pillar beneath a sprite-tree trunk on a slope. The exact
placement still needs target replay. A source reproduction found a scale and
authored-origin mismatch between projected geometry and sprite texture gradients.
The old rasterizer produced 90 incorrect pixels of 105 checked; the corrected
v0.0.29 candidate passes seven real projection/raster cases. Assets, transforms
and collision are unchanged. Native root/contact acceptance remains pending. Do not treat earlier sprite conversion
checks as acceptance of this root/contact defect; preserve original intended
roots when investigating. See
[TREE-PILLAR-28](BUG_JOURNAL.md#tree-pillar-28-unintended-pillar-beneath-sprite-tree-roots-open).

Development after v0.0.27; not yet an enabled world-wide runtime feature.

Use the original source placements, positions and scales. Bake one shared sprite
image per tree model rather than a fresh image for every placement or scale.
Billboard trees deliberately approximate the original three-dimensional view;
tilted trunks, collision and interactive stumps need explicit preservation checks.
Never silently omit non-unit scales or replace container state with decoration.
Generated sprites, original inputs and preview images remain private.

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

This is a standalone conversion stage. The normal image builder does not yet
install its output, and the scale-aware runtime path remains pending. A successful
bake is not permission to package unsupported instances or omit their collisions.

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
