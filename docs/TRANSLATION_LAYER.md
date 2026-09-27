# AmiWind: host conversion and native runtime

AmiWind is the working title. The repository identifier remains
`morrowind-amiga-demake`. The project is a GPL fan-made proof of concept requiring
the user's original Morrowind installation. It is not a complete game port.

## Two separate programs

The PC performs content loading, actor assembly, animation sampling, model
simplification, texture reduction, light baking and visibility preparation. An
OpenMW-derived exporter is a candidate for the full content-loader/actor stage.
OpenMW is not expected to run on the 68000 or to be linked into the Amiga runtime.

The Amiga consumes compact, versioned scene packages. A Quake-derived renderer
is a viable expanded-hardware experiment: projection, clipping, textured spans,
visibility traversal and surface caches are useful foundations. The existing
A500 terrain renderer remains a separate executable experiment. Neither route
currently implements Morrowind's quests, script VM, combat or full game mechanics.

Current executable progress: the host static-model exporter reads the owner's
base BSA using PyFFI, flattens visible unskinned NIF shapes, retains UVs/vertex
colours/materials, reduces textures and indexes shared geometry plus placements.
It is not yet an OpenMW exporter or Quake BSP compiler. The Amiga executable does
not consume this archive yet. This boundary keeps experimental assets usable
while the renderer decision is measured. See SCENERY_FORMAT.md.

## Engine options

| Route | Useful capability | Remaining conversion/runtime work |
| --- | --- | --- |
| Existing 68000 terrain renderer | Tested 1 MiB boot and stereo streaming | Occluded tree billboards, near building geometry, collision and bounded cache |
| Quake map/BSP route | Established visibility, collision hulls and surface renderer | Simplify terrain/buildings into sealed map geometry; compile BSP/PVS/lightmaps; split outdoors into zones |
| Quake renderer with a custom scene loader | Retain placed meshes/heightfield chunks | Replace assumptions about whole-level loading, visibility, collision and texture cache ownership |
| View-dependent impostors | Low transform cost for distant scenery | Bake views/sizes; depth-correct masks; avoid visible rotation/pop and near-building parallax errors |

A Quake `.pak` is an archive, not a world-streaming implementation. Quake normally
loads a map as a level. Draw-distance culling alone does not make its BSP, texture
or collision structures streamable. A fogged zone boundary/door load is a useful
first step before seamless multi-zone residency.

## Proposed expanded target

Start the full 3D experiment with a **68040 with FPU, 2 MiB Chip RAM, 32 MiB Fast
RAM, AGA and AmigaOS/Kickstart 3.1**, using HDD storage. This is a development
budget, not a measured minimum or a compatibility promise. An expanded A1200 or
appropriate A4000-class configuration can represent that class. Compare 68060
later; preserve a separate 68000 build. The bundled historical `src/amiga.readme`
requires Kickstart 3.0+, and the current Amiga code uses newer facilities such
as `ReadEClock`, `AllocVec` and `AllocBitMap`. It is not a KS1.3 port. Backporting
that platform layer would require replacements; 3D rendering itself does not
inherently require a 3.x ROM. No expanded-machine run is claimed by
checkpoint-005. AmiQuake's inspected build explicitly targets 040/060 and FPU.

Initial renderer goals: 320x200 or a smaller viewport, indexed textures with
small mip levels, baked lighting, no dynamic shadows, fog distance adjustable
at runtime. Measure transform/clip, visible spans, texture cache, display
conversion and disk-service costs separately. RAM capacity alone is not CPU
throughput. A larger HDF supplies more prepared variants; it does not increase
CPU speed or the controller's bandwidth.

## Scene and streaming sequence

1. One actual Seyda Neen building and tree, camera movement and valid depth
   ordering. Test near geometry before replacing distant trees with impostors.
2. Add collision proxies and Space activation on an original door reference.
   The parser now retains door destinations; no interior load is implemented.
3. Load one bounded zone with the existing music stream active. Keep pinned
   collision/near-geometry pages separate from evictable distant textures.
4. Predict movement across zone borders and issue low-priority asset reads while
   music has sufficient buffered time. Cancel stale requests on turns/teleports;
   retain a coarse fallback instead of blocking the frame on a missing texture.
5. Instrument bytes requested/resident/evicted, pending-read latency, audio
   underruns and frame percentiles. Adopt the raw-partition route only if measured
   filesystem overhead justifies it.

See LICENSING_AND_CREDITS.md before importing any renderer source. No Quake,
AmiQuake or OpenMW implementation is bundled by this checkpoint.
