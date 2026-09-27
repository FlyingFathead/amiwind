# Host validation (terrain pipeline)

Validated on Linux with Python 3.12 and a host C compiler. Windows-compatible
paths and Python 3.10 syntax are used, but this version has not been run on Windows.

Sixteen tests passed with no skips. Coverage includes malformed binary bounds,
height deltas, terrain-layer layout, signed big-endian packets, BSA offsets,
external path enforcement, symlink rejection, game-folder setup, synthetic
conversion, source-archive content validation, reproducible archive bytes and
refusal to overwrite an existing release.

The portable C reader was compiled with C99 and warnings treated as errors. It
read Python-generated packets at all four terrain strides, including unaligned
input and negative coordinates, and rejected truncation and corrupted padding.

The setup/convert workflow was also run against the supplied original game data
in the external workspace. All 144 generated packets matched their source
samples: 11,664 retained heights and 9,216 terrain material values, 36,864 bytes
in total. No original or derived game assets are part of the source package.

The new loose-folder input was combined with the previously supplied base
ESM/BSA. Inventory found 18 files under Music, 7,158 under Sound, and 6,448 under
Sound/Vo. This establishes available inputs, not completed audio conversion.

The later opening runtime has separate native validation in
OPENING_VALIDATION.md. Real-time world rendering and concurrent disk-streaming
performance remain unmeasured.
