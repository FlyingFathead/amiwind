# FOG-TOWN-HEAVY-32: Heavy fog at the Vivec Arena and in Balmora in v0.0.32-dev1

## Status: 8 October 2026

Open. Found in the v0.0.32-dev1 smoke test (FS-UAE, playtest profile). Fog settings measured
identical to v0.0.31 (8 October 2026, below); the Seyda Neen silhouettes are the skyline fill
([HORIZON-FLORA-SPRITES-32](HORIZON-FLORA-SPRITES-32.md)).

## Symptom

From about 1,500 units the Vivec Arena shows only as a flat fog-coloured silhouette; even close up
its upper parts look patchy, with sky and fog showing through. Balmora's buildings also look hazy,
unlike the Balmora look of v0.0.31.

Owner evidence from real play of dev1 (8 October 2026, screenshot kept in private evidence):
Seyda Neen, global position -11037 -70598 317 (local 56 270 79), heading 165, pitch -14, game time
13:35. A large flat, fog-coloured "castle" silhouette with a rounded, canopy-like outline stands
behind the town buildings and disappears when walking closer. Cause not established; possibly the
same mechanism as [HORIZON-FLORA-SPRITES-32](HORIZON-FLORA-SPRITES-32.md) (distant flora sprites
drawn as flat fog silhouettes). That record ("Horizon silhouetting: not yet perfect") also holds a
second owner screenshot: a fog-coloured wall of vertical spikes and blocks north-west of Seyda Neen.

## Where

Exterior fog and far drawing: the location fog table (`fog-locations.txt`), the far clip and the
distance drawing (`aw_fog.c`, `aw_horizon.c`).

## How it happened

Measured 8 October 2026 (dev1 image readback against the v0.0.31 payload, engine sources at
v0.0.31 against now):

- `id1/world/fog-locations.txt` is byte-identical to v0.0.31 (181 bytes, one line, Balmora 300/250)
  and has no effect by default: location fog is off (`aw_fog_location 0`) and can only shorten the
  distance. The Arena having no line changes nothing.
- `default.cfg`, `default-game.cfg`, `gfx/palette.lmp`, `colormap.lmp`, `fog.lmp`,
  `aw_shared_sky.lmp` and `aw_night_sky.lmp` are byte-identical to v0.0.31.
- The fog and far distance is 540 local units in Balmora, Seyda Neen and the Arena (the town table's
  `draw_distance`; the player's larger setting is capped in converted towns, as in v0.0.31 for
  Seyda Neen and Balmora). The fog runs linearly from about 44 % of that distance to solid at 540.
  `AW_FogDraw`, the far plane and `aw_horizon.c` are unchanged since v0.0.31 apart from the town
  table lookup.
- The Seyda Neen silhouettes that the owner reported are the skyline fill, measured on the
  v0.0.31 engine too: [HORIZON-FLORA-SPRITES-32](HORIZON-FLORA-SPRITES-32.md). The new default
  (`aw_skyline_fill 0`) removes the fog-colour columns everywhere, including at the Arena.

So nothing in the fog settings is heavier than in v0.0.31. The Arena canton is far larger than any
Balmora building, so at the town distance of 540 most of it lies in the fog band and the far
cut-off removes pieces of its upper parts ([HORIZON-HOLES-31](HORIZON-HOLES-31.md)). A longer
Arena distance (its region overlap is 896) is an owner decision with a frame-time cost to measure.
Balmora's haze has not been compared at a matched pose and time against v0.0.31.

Earlier candidates:

- the fog table: v0.0.32 is the first image whose `fog-locations.txt` is written by the builder
  ([BUILD-NIGHT-TABLES-31](BUILD-NIGHT-TABLES-31.md)); v0.0.31's table reached the disks by hand,
  and the Arena is new and may have no entry or a default one;
- the far clip: large buildings near the limit lose pieces and keep others
  ([HORIZON-HOLES-31](HORIZON-HOLES-31.md)), which matches the patchy upper parts;
- distance detail.

## Why it was not caught

No fog or far-view comparison with the previous release in the image checks.

## Reproduction

dev1 in FS-UAE: `dbg tp vivec_arena`, step back to about 1,500 units; Balmora street views. Compare
the same poses (same time of day) with v0.0.31, and the dev1 `fog-locations.txt` with v0.0.31's.

## Repair

Fog tables and settings: nothing to repair (identical to v0.0.31). The skyline fill columns: the
land-outline default of HORIZON-FLORA-SPRITES-32. Open: the Arena distance (owner decision) and a
matched Balmora view.

## Verification

Pending: matched dev1 / v0.0.31 views at fixed poses, headlamp off.

## Prevention

The image step compares its fog table with the last release's and reports changed or missing
locations; matched far views on fixed cameras before a playtest is packaged.
