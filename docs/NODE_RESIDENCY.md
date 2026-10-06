# Renderer nodes and point-collision nodes

The v0.0.27-rc3 memory investigation identified another representation cost:
converted scenery's point-collision BSP nodes were expanded to renderer-sized
`mnode_t` records, then copied into compact hull0 collision records. The scenery
renderer uses its model's face range; it does not traverse those collision trees.

The loader introduced during rc4 and included in v0.0.27 keeps the complete
original-index hull0 representation,
but expands only a strictly verified world-render node prefix. It changes no
terrain, scenery faces, textures, collision planes, collision contents or model
root indices. Host checks, the complete static map gate and final private HDF
assembly/readback passed. Target gameplay acceptance remains pending; the rc3
crash incident is not closed by this
document. See [memory allocation](MEMORY_ALLOCATION.md) and
[heap lifecycle profiling](HEAP_WATCHER.md).

## Count first: actual rc3 inputs

`tools/audit_bsp_node_roles.py` classifies reachability from world model zero and
all inline point-hull roots. It does not infer roles merely from a zero face count.
World zero-face nodes remain renderer nodes. Shared world/inline nodes, orphans,
and inline-only nodes with faces are identified separately.

| Input | World nodes | Inline-only zero-face nodes | Avoidable target renderer bytes |
| --- | ---: | ---: | ---: |
| Original `sn012` | 9,982 | 13,642 | 545,680 |
| Original `bm027` | 1,644 | 18,275 | 731,000 |
| Bounded central Seyda, core 512 + apron 896 | 4,141 | 13,178 | 527,120 |
| `addamasartus` | 7 | 20,086 | 803,440 |
| `bmmages` | 6 | 6,235 | 249,400 |
| `bmtemple` | 6 | 11,854 | 474,160 |

These are 40-byte target `mnode_t` savings before hunk alignment and any change
in peak caused by load ordering. They are not a substitute for the revised final
allocator estimate. Every original 8-byte hull0 node remains. All six inputs
have contiguous world prefixes, no shared world/inline nodes, no orphans and no
face-bearing inline-only nodes. The node counting report and loader eligibility
are distinct: the loader additionally requires forward child order.

## Consumer review

The inspected engine consumers use the world node tree for rendering and brush
clipping, leaf/PVS queries, entity linking, ambient sound, world dynamic lighting,
and light-point sampling. Relevant source locations are `r_bsp.c`, `r_light.c`,
`r_efrag.c`, `r_main.c`, `sv_main.c`, `world.c`, `pr_cmds.c`, `r_misc.c` and
`snd_dma.c`.

`Mod_PointInLeaf()` callers pass the world model. `R_MarkBrushLights()` in
`r_light.c` explicitly uses a validated inline surface range; an inline collision
root is not a rendering tree. Collision consumers use `model->hulls[]`, with
`SV_HullForEntity()` selecting the appropriate compact hull. These contracts must
be reviewed when adding new consumers of `model->nodes` or `numnodes`.

## Loader contract and fallback

`Mod_LoadSubmodels()` runs once before node loading, so roots are available for
classification. `Mod_LoadNodes()` checks record bounds, plane/face indices,
children and model point roots before constructing pointers. The compact path
requires:

- World root zero, with reachable nodes forming a contiguous forward tree prefix.
- Every remaining node reachable from an inline root, outside the world prefix,
  with zero attached faces and forward node children.
- No inline root sharing a world node and no unreferenced tail nodes.

Unsupported layouts use the existing full node representation. Invalid ranges
fail before allocation or pointer construction. An allocation failure in the
optional classifier also falls back. Existing generic loader behavior for other
unsupported graph shapes is unchanged; the prototype is not a general malformed
BSP graph repair.

The classifier uses `ceil(disk_node_count/8)` temporary bytes from the OS allocator,
then frees them before either resident allocation. The six measured inputs need
781Ã¢â‚¬â€œ2,953 bytes. This is external OS memory, not hunk memory; it still matters to
Fast RAM availability and fragmentation. There is no second full node or model
copy, no new per-frame allocation, and no change to `model_t` or `mnode_t` layout.

`AW_MakeDiskHull0()` constructs all compact collision nodes directly from the disk
node table and original leaf contents. The optimized path bypasses the later
`Mod_MakeHull0()` copy. Disk node IDs and all model point roots remain unchanged.
Only `model->numnodes` and the renderer array size describe the shorter world
prefix; hull0 retains its full independent `lastclipnode` bound.

## Verification and remaining gates

The native fixture includes the actual loader source and compares optimized
hull0 bytes against the legacy loader. It covers water/empty/solid leaves, negative
inline roots, preserved world parents and surfaces, shared-root/noncontiguous/
face-bearing/orphan fallback, scratch allocation failure, and malformed ranges.
The same fixture compared all hull0 records on the six actual inputs above:
byte-identical output, with renderer child pointers inside the retained array.
Host `mnode_t` is larger than the Amiga ABI, so host saved-byte counts must not be
quoted as Amiga savings.

The matching rc4 estimator now models submodels before nodes, hull0 allocation
during node loading, the still-live raw node section, and the deferred-copy
bypass. It also reports the external classifier scratch and the full-node peak
bound if its optional OS allocation fails. Three focused allocation-order tests
and the existing estimator tests pass. Reports
created under the earlier estimator remain earlier-loader baselines even if
these source changes have since landed. Do not just subtract resident savings
from an old peak and declare a pass.

The rc4 target engine compilation succeeds; this is memory representation evidence,
not an FPS or crossing-latency improvement claim. Before packaging, bind the exact
engine receipt to the current source, audit every final runtime map and exercise the actual image
through intro/town travel, both-direction cell crossings, water and point traces,
standing collision, torch lighting, actor restoration, first frames and gameplay.
Keep the 3 MiB baseline plus 2 MiB safety reserve and the 5 MiB map planning target.

## Dev4 transition smoothness follow-up

Profile visible stalls before choosing low-level optimization. The existing
`aw_stream.c` records disk bytes/calls/time, decode time, world/actor preparation,
total load time and time to the first presented frame in separate TSV traces.
Method 2 is a bounded BSP-prefix read-ahead experiment (8 KiB per tick, configurable
128/256/512 KiB cache and 0.5-4 second lookahead), not concurrent scene construction
or a seamless cell swap. Method 1 remains the reference.

Compare identical routes and build/assets with read-ahead off/on, including cold
and warm runs, memory peaks and worst visible stalls. Then consider preloading
reused resources, incremental decode or fewer repeated allocations according to
the measured bottleneck. Assembly is a candidate only for a measured hot loop;
it does not itself eliminate blocking disk I/O or destructive scene teardown.
View angles, hands/torch state, active speech and the soundtrack must retain their
continuity throughout an optimized handoff. No new latency improvement is claimed.
