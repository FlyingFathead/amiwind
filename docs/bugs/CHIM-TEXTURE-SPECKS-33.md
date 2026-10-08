# CHIM-TEXTURE-SPECKS-33: CHIM-drawn surfaces show bright single-texel specks that legacy frames do not

## Status: 8 October 2026

Open. Found by the first FS-UAE comparison of Balmora drawn by CHIM and by the legacy maps. CHIM
builder.

## Symptom

Surfaces drawn from the CHIM world (placed models and terrain) show scattered bright single-texel
specks that the legacy frame at the same pose does not have.

## Where

CHIM shared textures (`tools/chim/`, the texture pack); the legacy maps' textures are the
reference.

## How it happened

Not established. Likely cause: the CHIM builder quantizes textures to the game palette by a
different path from the legacy converter.

Measured (8 October 2026):

- 38 of the textures in the legacy Balmora region map bm028 differ by 1 to 92 texels from the
  closest CHIM shared texture;
- isolated bright specks: 5 in the legacy textures against 333 in the CHIM ones for the same set;
  700 across all 176 CHIM textures.

The specks remain with `r_fullbright 1`, `aw_emissive 0` and `r_drawentities 0`, and grow into
blocks with `d_mipcap 3` (smaller mip levels), so they are in the texture data, not made by the
engine.

## Why it was not caught

The CHIM validator checks texture counts, sizes and sharing, not texel equality with the legacy
conversion of the same texture.

## Reproduction

The same Balmora pose under CHIM and legacy in FS-UAE; texel comparison of each CHIM shared
texture with the matching texture of the legacy region maps.

## Repair

Not yet: make CHIM textures with the legacy quantization path (one implementation), then compare.

## Verification

Pending: speck count in CHIM textures equal to legacy, and matched frames.

## Prevention

A builder check that every CHIM shared texture is texel-identical to the legacy conversion of the
same source texture (or every difference is documented).
