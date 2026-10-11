# CHIM reference models

A reference model is a model the project holds up as the good version of something: the one to measure
other conversions against, to take scale from, and to keep from regressing. AmiWind ships no game data,
so a reference model is never a file in this repository or in a release. It is a recipe: the source mesh
in your own copy of Morrowind, the SHA-256 of that file as the Game of the Year edition holds it, the
converter profile and reduction method with their exact parameters, and the SHA-256 the builder must get
at every step from that source. Anyone with the game rebuilds the same model and gets the same hashes.

The recipes live in `config/reference-models.json`; `tools/reference_models.py` rebuilds them from your
data files and checks each step. This page describes each reference model in words and numbers, and is
the place for every future one.

## How a reference model is checked

The builder's `seam-audit` stage (default on, before the image) rebuilds every reference model from
the data files it was given and compares five steps with the recorded SHA-256:

| Step | What is hashed |
| --- | --- |
| `source` | the mesh file's bytes as read from your data files (a loose file first, then the archives) |
| `geometry` | the decoded mesh: vertex positions and texture coordinates (rounded to 1e-6), triangles with materials |
| `visible` | the triangles the converter draws (exterior visibility rules applied) |
| `reduced` | the mesh after the profile's reduction |
| `faces` | the converter's faces: coplanar polygons, split at 240 texels; points rounded to 1e-4 units, texture vectors to 1e-6 |

The steps are canonical encodings (rounded as above), so the hashes do not depend on the number of
workers: the base silt strider gives the same five hashes with one and with four threads. A mismatch
never fails the build: the stage prints a loud warning naming the model and the first step that
differs, with what that usually means (another edition or a replacer mod at `source`; a changed
decoder, reducer or polygon step further on), and records it in `seam-audit.json`. To check by hand:

    python3 tools/reference_models.py check --data-files "<your Data Files>"
    python3 tools/reference_models.py compute --data-files "<your Data Files>"   (prints every hash)

## How its placed copies derive from it

CHIM bakes a placement's scale and tilt into a model variant (Quake entities have no scale): the silt
strider placed at 89 % size is the record `r/siltstrider@s0.89`, the one at full size
`r/siltstrider@s1` ([world format: model records](WORLD_FORMAT.md#model-records)). Every variant of a
mesh is the same reduced mesh, transformed after the reduction; nothing is reduced again per scale.
Since v0.0.36-dev3 each variant also shares its vertices exactly as the unscaled mesh does (build
setting `model_weld`, default `base`), so every variant has the same faces, vertices and edges as its
base: before, vertices were shared by their placed position rounded to 1e-5, which split a few
vertices at some scales and tilts and not at others
([CHIM-STRIDER-SCALED-SEAMS-36](../bugs/CHIM-STRIDER-SCALED-SEAMS-36.md)). The earlier sharing stays
selectable (`tools/build.py --chim-model-weld placed`).

The CHIM validator checks this for every baked variant in a world (`tools/chim/variant_audit.py`, run by
`chim_build.py --validate`): each variant against its mesh's base, face by face (edge lengths scaled by
the variant's scale) and by its shared vertices and open edges. A reference model's variants must all
be its base transformed, or the world fails validation; for other meshes the report lists any variant
from another reduction (another converter profile) and any whose topology differs. The seam audit
measures each base reduction against its source mesh, so a variant that passes the variant audit has
exactly its base's seams.

## The base silt strider

Owner decision, 10 October 2026: the silt strider at Balmora is the good one, the one whose polygons
are properly closed, and it is the base silt strider model: the reference for its scale and for every
other copy of it.

### What and where from

- The caravan silt strider, the giant insect the travel service rides: one mesh, placed in every
  caravan town (Seyda Neen, Balmora, Vivec, Suran, Molag Mar, Ald-ruhn, Maar Gan, Gnisis, Khuul).
- Source: `meshes/r/siltstrider.nif` in your own Morrowind data. In the Game of the Year edition it is in
  `Morrowind.bsa`; the GOG release also has the same file loose under `Data Files/Meshes`. Both editions
  (GOG and Steam) hold the same 270,437 bytes, SHA-256
  `78c624c580ba9927821d37b75c64a22347777fe386f521c16e4a268e5502ac88`.
- Converter profile: the scenery group `silt_strider` in `config/scenery_groups.json` (visual profile of
  `meshes/r/siltstrider.nif`). Every converter path reads that one profile: the town converters through
  `town_regions.visual_profile`, Seyda Neen's directly.

### How it is made

1. Decode the mesh (the converter's NIF reader, with its texture-coordinate repair): 5,600 visible
   triangles (the hidden collision shapes are read separately).
2. Reduce it, boundary-locked, to ratio 0.45 (`static_lod.reduce_mesh` with `lock_boundaries`, the method
   from [MESH-LOD-OPEN-SEAMS-33](../bugs/MESH-LOD-OPEN-SEAMS-33.md), shipped in v0.0.34): every rim vertex
   and every vertex shared with another part keeps its exact position, only interior edges collapse
   (quadric error), and no face turns more than 60 degrees from its source orientation. The reduction
   fails if a rim vertex moved. Result: 2,926 triangles.
3. Merge coplanar triangles with the same texture mapping into convex polygons and split any polygon
   wider than 240 texels (the engine's surface limit): 3,219 faces. The strider is organic: its 2,926
   triangles form 2,899 coplanar regions with one texture mapping, so almost every face is a triangle,
   and the 240-texel split makes the rest.
4. Texture size 64; collision from the mesh's own collision node.

### Numbers

| | |
| --- | ---: |
| Source triangles (visible) | 5,600 |
| After reduction | 2,926 |
| BSP faces | 3,219 |
| CHIM record `r/siltstrider@s1` (v0.0.36-dev3 world) | 354,592 B |
| Memory block in the CHIM zone (heap gate, v0.0.36-dev3) | 464,336 B |

The record and block sizes also depend on the collision hull form a build chooses; the face count and
the five hashes do not.

Expected SHA-256 per step:

| Step | SHA-256 |
| --- | --- |
| `source` | `78c624c580ba9927821d37b75c64a22347777fe386f521c16e4a268e5502ac88` |
| `geometry` | `87522167e941ba16c68c1c48e08c1baffe10f05219af8b434af9c9de4486335e` |
| `visible` | `87522167e941ba16c68c1c48e08c1baffe10f05219af8b434af9c9de4486335e` |
| `reduced` | `62f2929c41d71455fd81e9dd5a149e2bc3e20c36fece64794d718016c5829f5b` |
| `faces` | `4d8e73c7d1f5e712de5abdef33593319548022f4d41782774eb9c994b7826a08` |

### Audits

- Seam audit (`tools/seam_audit.py`): 968 seam edges (15,829 units) and 100 free-rim edges, none torn
  (0 %, tolerance 9.56 units). The strider is listed as a mesh that must stay closed
  (`config/seam-audit-known.json`): any torn seam or rim fails the build.
- Sky-through, 16 views around and below the model, one-sided rendering: about 2 %, all of it the
  slightly thinner legs, none through the shell ([MESH-LOD-OPEN-SEAMS-33](../bugs/MESH-LOD-OPEN-SEAMS-33.md)).
- Variant audit: the Seyda Neen copy (`@s0.89`) has the same 3,219 faces as the base, each the base face
  scaled by 0.89 (largest difference 0.00004 units). Built with the base vertex sharing it also has the
  base's 2,211 vertices and the same 898 open edges (with the earlier sharing: 2,218 and 926).

### Why this one

- Closed: the boundary-locked reduction keeps every seam and rim where the source has it; the earlier
  profile (ratio 0.5, free reduction) pulled the shell plates apart and showed the sky through them.
- It fits: the full-detail strider (no reduction of shell, arms and legs) does not fit Balmora's memory
  ring ([CHIM-STRIDER-RING-33](../bugs/CHIM-STRIDER-RING-33.md)); this one is smaller than the earlier
  profile's.
- One model for every town: each placed copy is this mesh scaled and turned, so a strider looks the same
  wherever it stands.

## Adding a reference model

1. Choose the profile (a scenery group in `config/scenery_groups.json` or a named profile) and check the
   model in game (headlamp off and on pairs at fixed poses) and with the seam audit.
2. Add a row to `config/reference-models.json`: name, source path, group, method parameters (they must
   equal the profile's; a test checks), and run `tools/reference_models.py compute` on your data to
   record the five hashes and counts. Check them with a second machine or edition where you can.
3. Describe it here: what it is, where it comes from, how it is made, its numbers, audits and why.
4. If every placed copy must be exactly this model, the variant audit enforces it from then on (reference
   models fail validation on any variant that is not the base transformed).
