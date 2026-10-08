# EXTENTS-FPU-RULE-31: surface extents and lightmap sizes depended on the FPU's arithmetic

## Status: 8 October 2026

Open. Repaired in source on the v0.0.32 Vivec fixes branch; not shipped.

## Symptom

A face whose texture coordinates end on, or within a few millionths of a
texel of, a 16-texel grid line can get a different surface extent, and so a
different lightmap size, depending on how the arithmetic is rounded. The
engine then reads the wrong number of lightmap bytes (light shifted by a row
or column, or read from the neighbouring face), or stops with "Bad surface
extents".

## Where

`engine/aga/src/model.c`, `CalcSurfaceExtents`, against the light compiler
(ericw light) and the map converter (`tools/interior_lighting.py`,
`tools/check_geometry_render_inputs.py`, `tools/deduplicate_bsp.py`).

## How it happened

`CalcSurfaceExtents` computed `x*s0 + y*s1 + z*s2 + s3` in `float`. GCC with
`-m68040` compiles that to `fsmul`/`fsadd`, which round every step to single
precision on a real 68040 (checked in the compiler output). Emulators may
compute the same instructions wider: the 272-texel stop reported for
MESH-EXTENT-GRID-31 matches wide arithmetic, while single precision gives 256.
ericw light computes the coordinates in double precision. The converter baked
from unrounded double values and its checks hedged between "single after
every step" and "wide, rounded on store". Four different rules for one
number.

## Why it was not caught

The rule was never written down; the gate's oracle modelled two plausible
rules instead of pinning one.

## Reproduction

`720 * float(1/3)` is 240.0000072 in double precision and 240.0 in single
precision: extent 256 by the double rule, 240 by the single rule
(`tests/aga_face_texinfo_test.c`, `tests/test_surface_grid.py`). The Vivec
dry run found 3,379 of 29,874 converted faces of St. Delyn Storage with a
lightmap shorter than the engine needs (LIGHTMAP-TAIL-31, LIGHTMAP-GRID-31).

Scope (face validator): 500,980 faces in 2,243 shipped maps have texture minima or extents that
differ between the FPU rules; see EXTENTS-RULE-OLD-INTERIORS-32 for the interiors this breaks.

## Repair

The Quake way (QuakeSpasm's `CalcSurfaceExtents`, ericw light): one rule,
double precision after every product and sum, in source order. The engine
computes it with a volatile double store after each step, so real 68040 code
and emulators agree; float*float products are exact in double. The converter
(`tools/surface_grid.py`) computes the same values from the stored
single-precision vertices and mappings and sizes every lightmap with it;
the render-input oracle and light deduplication use it as the strict rule.

## Verification

Native fixture `aga_face_texinfo_test.c` (extent 256 for the case above);
`tests/test_surface_grid.py`; the full Linux suite and the warning-free
68040 engine build. On target hardware: pending.

## Prevention

`tools/surface_grid.py` is the single definition; the converter checks every
converted face's extents under the engine, single-precision and 68040
extended rules.
