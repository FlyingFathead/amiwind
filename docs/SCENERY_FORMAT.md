# Static scenery conversion experiment

Checkpoint-005 contains a working host exporter, not a native scene loader.
Output is derived Morrowind content and must stay outside the source repository.

```sh
python -m pip install '.[scenery]'
python tools/prepare_scenery.py --workspace ../morrowind-amiga-workspace --out ../morrowind-amiga-workspace/scenery-study
python tools/preview_scenery.py --area ../morrowind-amiga-workspace/scenery-study --out ../morrowind-amiga-workspace/static-turntables.png --model flora_bc_tree_08.nif --model ex_de_shack_02.nif
```

Run the normal setup/convert commands first. This reads the base master/archive;
loose replacement meshes, mod load orders, animated/skinned actors, special
controllers, collision meshes and dynamic lights are outside this experiment.
The preview is an orthographic software turntable on the PC, not an Amiga screen.
It uses alpha testing and the reduced original textures; it does not reproduce
all NIF render-state inheritance, lighting or transparency blending.

PyFFI 2.2.3 is an optional, separately installed dependency. Its generated
`num_uv_sets` member defaults to the newer byte type even for TES3, whose layout
requires a ushort. The adapter selects that field width and supplies the removed
`time.clock` alias. Only NIF 4.0.0.2 is accepted. No PyFFI source is bundled.

## Files

- `scenery.mwpak`: independently readable geometry/texture payloads, each starting
  at a 512-byte-aligned offset. There is no compression or shared decoder state.
- `scenery-index.json`: MWSC1 version 1, payload offsets/lengths/SHA-256 hashes,
  source hashes, materials, references, bounds and 2048-unit spatial buckets.
- `scenery-report.json`: counts and conservative camera-sphere residency costs.

MWG1 geometry: big-endian `4sHHII` header (magic, version 1, material count,
vertex count, triangle count). Each vertex is five float32 values (XYZ/UV) and
four unsigned colour bytes. Each face is four uint16 values (three indices and
material index). This 040-friendly intermediate retains original triangles;
it is not an optimized A500 representation or a Quake BSP/MDL.

MWT1 texture: big-endian `4sHH` (magic, width, height), followed by RGBA8888
pixels. Default maximum edge is 64 pixels. These are host intermediates; an
Amiga renderer still needs palette/mip conversion. Texture paths are resolved
against the original BSA, including a DDS alternative for NIF TGA names.

Models are shared across references. Flattened local model transforms include
NIF scale/rotation/translation, except the root node's rotation: like Morrowind,
the converter ignores the authored root rotation but keeps the root translation
and scale (see [BALMORA-TEMPLE-GEOMETRY-29](bugs/BALMORA-TEMPLE-GEOMETRY-29.md);
applying it turned Velothi kit pieces 90 degrees). TES3 placement position/rotation/scale is retained;
transformed bounds populate every intersected XY bucket, so a building crossing
a chunk edge is not lost. Camera-sphere queries test bounds rather than object
origins. Frustum and occlusion rejection are not implemented by this host query.

Every archive payload is independently read back and hash-checked. The reader
rejects invalid extents, short reads and changed payloads. Geometry validation
also checks sizes, finite coordinates and vertex/material indices.

## Original base-game study

The 4096-unit origin-selection region around (-11200, -71504) exported all
272 selected STAT/DOOR references: 74 distinct models, 62 textures, no conversion
errors. The aligned archive is 1,590,552 bytes. Selection by origin defines the
study boundary only; it is not a complete world visibility guarantee.

| Camera sphere radius | References | Placed triangles | Shared geometry bytes | Shared texture bytes |
| ---: | ---: | ---: | ---: | ---: |
| 768 | 22 | 9,738 | 307,800 | 256,208 |
| 1,536 | 88 | 25,291 | 528,592 | 495,968 |
| 2,304 | 150 | 38,147 | 626,848 | 594,352 |
| 3,840 | 253 | 60,251 | 813,696 | 717,296 |

These are full original static triangles and RGBA intermediates before view,
backface, occlusion or LOD reduction. They are not per-frame visible triangle
counts and do not include terrain, actors, OS or renderer working memory. They
show why local caching and explicit simplification are needed even with fog.
The sample tree has 1,359 triangles; the shack has 1,129. Native frame rate remains
unmeasured for this scenery.
