# Bounded world candidates

`tools/prepare_bounded_world.py` is an offline candidate compiler introduced during
the v0.0.27-rc3 memory repair. It addresses an identified cause of the Seyda Neen
regression: selected town scenery could retain the entire parent terrain BSP,
including 4,907 leaves and about 2.77 MB of visibility data. Selecting fewer
entities alone did not remove that parent world allocation.

The helper compiles a real bounded terrain world and composes its world model
with intersecting original scenery. It does not install an HDF, change the runtime
region table, or certify a playable release. See [memory allocation](MEMORY_ALLOCATION.md),
[the heap watcher](HEAP_WATCHER.md), and [cell changes](CELL_CHANGING.md).

## Inputs and preservation contract

Use the original generated `seyda.map`, the full converted town BSP, and its final
768-byte palette. The MAP and BSP must use the same coordinates and conversion
provenance. Supply the full town scenery BSP when creating arbitrary new cores;
an old selected derivative may already lack models needed by a different core.

The helper preserves complete original `g<number>` LAND triangle brushes that
intersect the required coverage. It does not simplify terrain or cut triangles.
It builds the WAD from the final BSP's original miptex bytes, preserving palette
indices and texture mappings. Approximate `clip` architecture boxes are excluded:
the retained inline models provide their original collision trees.

Original generated water, floor and sky boxes are recognized exactly before
allowing required coverage outside the LAND extent. This matters at the western
Seyda Neen edge: the existing core extends 31 units past LAND into sea. The new
enclosure stays at least 32 units outside both required coverage and selected
terrain. Unknown source world geometry or an unrecognized shell is rejected.

Scenery selection uses transformed model bounds, retaining whole intersecting
objects. Complete faces wholly outside required visual coverage may then be
removed; shared faces remain whenever any retained placement needs them. Actor
and gameplay records are retained for existing runtime restoration/filtering.
The standing collision trees of all retained models remain intact.

## Tool and build gate

```text
python tools/prepare_bounded_world.py \
  --source-map <original-generated.map> \
  --texture-bsp <final-full-town.bsp> \
  --source-bsp <final-full-town.bsp> \
  --palette <final-palette.lmp> \
  --coverage <x0> <y0> <x1> <y1> \
  --core <x0> <y0> <x1> <y1> \
  --ericw-bin <compiler-directory> --sdk <target-sdk> \
  --threads 24 --out <new-candidate-directory>
```

The output directory must be new. It contains `candidate.bsp`, compiler logs,
the generated bounded MAP/WAD, and `report.json` with source/output SHA-256 hashes,
coverage, preservation checks and the target-ABI heap estimate. A static heap
failure exits with status 2 and retains its report for diagnosis.

The callable API is `build_candidate(source_map, texture_bsp, source_bsp, palette,
coverage, out_dir, ericw_bin, target_sizes, core=None, threads=1)`, with the last two
arguments keyword-only. Its report exposes
`heap_estimate.peak_loader_bytes` for an adaptive subdivision evaluator.

Checks include exact paired collision-tree comparisons for all retained model
hulls and 8,092 deterministic original/candidate world contents samples across
the required rectangle. The samples cover point and standing hulls at multiple
heights, including water and terrain. They are a regression check, not an
exhaustive proof of all movement or an emulator playtest.

The reference gate remains an 11 MiB hunk with 3 MiB baseline reserve and 2 MiB
safety reserve: the modeled BSP peak must fit within 6 MiB. About 5 MiB remains a
planning target for growth. Required visual coverage, currently a 896-unit apron
around the core, belongs to the region planner and must not be reduced to force
acceptance. The helper does not infer or silently shrink it.

## Evidence and remaining acceptance

The prototype measurements below are historical. The later normal-converter
bounded layouts carried into v0.0.27 passed the complete static map gates and
private image assembly/readbacks. Target lifecycle checks remain open; see
[the current release record](RELEASE-v0.0.27.md).

The central 512-unit core with its 896-unit apron still required 6,929,680 bytes,
638,224 above the BSP ceiling, despite a genuine smaller world and removal of
complete distant models. A 128-unit central core narrowly passed by 24,112 bytes;
that is inadequate practical growth room and is not an accepted final layout.
Adaptive subdivision must account for the entire town, switching frequency and
the runtime limit of 64 regions, rather than apply a tiny uniform grid.

A private collision experiment removed standing hulls from 51 distant models
outside core+224 while keeping all point hulls. It saved only 122,784 bytes and
still failed by 515,440 bytes. That policy is not part of this tool: distant NPC
movement and swept projectile traces would also need a residency contract.

The western `sn010` prototype compiled with the certified sea strip intact and
passed all world collision samples, with a 1,111,184-byte modeled BSP peak. These
are candidate measurements, not a claim that rc3's playable image is repaired.

For each later changed layout, run the final complete runtime-map audit, verify new core
coverage/adjacency and actor state handovers, assemble the actual image pair,
then inspect target heap lifecycle logs from outgoing scene through unload,
new load, restoration and first presented frames. Traverse the reported Seyda
Neen boundary in both directions and retain the source/report/image hashes.
