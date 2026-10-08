# HORIZON-FLORA-SPRITES-32: Horizon silhouetting: not yet perfect

## Status: 8 October 2026

Open: not yet perfect. Reported by the owner on v0.0.32-dev1 (8 October 2026), who notes it was
partly his own call. Not a v0.0.32 blocker. Default restored in source (v0.0.32-final-blockers):
the game config selects the land-outline horizon (`aw_skyline_fill 0`); the object silhouetting
method stays, selectable, as "experimental and buggy" (sprites need their shapes from the alpha
channel): "tested but subpar results; kept for future improvement".

Decisions (owner, 8 October 2026): the earlier horizon system is the default again. The
silhouetting stays as an alternative mode, documented as "tested but subpar results"; it is kept
because it has potential and must not be removed. The owner, after the A/B frames:
`aw_skyline_fill 0` "is way better"; a fog wall like the one below will not do.

## Symptom

Design intent (owner): the horizon is drawn from the highest topography, so the distant skyline is
the outline of the land. In dev1 the sprite trees break it (owner). Two dev1 screenshots from real
play, kept in private evidence:

1. Seyda Neen, global position -11037 -70598 317 (local 56 270 79), heading 165, pitch -14, game
   time 13:35: a large flat, fog-coloured, castle-like silhouette with a rounded, canopy-like
   outline stands behind the town buildings and disappears when walking closer.
2. Global position -11704 -67382 285, heading 332 (north-west), game time 14:51: a huge
   fog-coloured wall of vertical spikes and blocks above the ground.

## Where

World flora sprites (`tools/world_flora.py`, `progs/aw_flora/`), now built by default
([BUILD-FLORA-OPTIN-32](BUILD-FLORA-OPTIN-32.md)), and the fog and far drawing. The distant land
fill (`engine/aga/src/aw_horizon.c`) draws only retained LAND polygons in the fog colour and is
unchanged since v0.0.29. Related: [FOG-TOWN-HEAVY-32](FOG-TOWN-HEAVY-32.md) (heavy fog at the
Arena and in Balmora), [HORIZON-HOLES-31](HORIZON-HOLES-31.md) (distant buildings break up against
the sky), HORIZON-POP-29, LAND-HORIZON-GAPS-29, TREE-PILLAR-28.

## How it happened

Measured (8 October 2026, FS-UAE playtest profile, both poses, headlamp off): the skyline fill
(`aw_skyline_fill`, engine `AW_FogDraw` in `aw_fog.c`). In each screen column, once a pixel at fog
level 12 or more is drawn, every sky pixel below it takes the full fog colour. The fill was added in
v0.0.31-dev5 (d237561) to hide the cut-outs that the far cut-off leaves at short fog distances, and
v0.0.31 shipped it on; v0.0.30 has no fill. It applies to every fogged pixel: land, the Bitter
Coast's converted trees and town buildings, and sprites. Far trees near the fog distance, with the
ground behind them already cut away, therefore turn the sky below them into solid fog-colour
columns: the canopy-shaped "castle" and the wall of spikes. Closer, the trees are no longer at
level 12 and the columns go away.

It is not a v0.0.32 data or builder change at these poses: both are inside the recorded v0.0.31
Seyda Neen maps (sn043 and sn054, BUILD-SEYDA-REGEN-30), whose geometry and flora are byte-identical
to v0.0.31; the flora sprites, fog table, palette, fog and sky lookups and game configs are
identical too. The v0.0.31 engine binary, run on the same image at the same poses, draws the same
castle and the same wall (pixel differences only in the moving clouds). The engine defaults of
`aw_skyline_fill` (1), `aw_terrain_horizon` (0), `aw_fog` (1) and `aw_horizon_veil` (0) are the
same in v0.0.31 and now, and `aw_horizon.c` (the opt-in land fill) is unchanged.

| Variant at both poses | Result |
| --- | --- |
| dev1 engine, defaults | castle (pose 1), wall of fog columns (pose 2) |
| v0.0.31 engine, defaults, same data | the same castle and wall |
| `aw_skyline_fill 0` (either engine) | no columns: the far trees are fogged silhouettes against the sky |
| `aw_fog 0` | trees and hills drawn unfogged |

## Why it was not caught

No matched horizon view against v0.0.31 was taken before dev1 was delivered.

## Reproduction

dev1 in FS-UAE: `noclip`, then `aw_view 56 270 79 285 -14` with `aw_set_time 1335` (pose 1) and
`aw_view -110 1074 71 118 -15` with `aw_set_time 1451` (pose 2), after `dbg tp seydaneen` from
normal play (not from the intro docks); compare `aw_skyline_fill 1` and `0`.

## Repair

Default restored, no method removed (v0.0.32-final-blockers):

- `config/game.cfg` (installed by the builder as `default-game.cfg`) sets `aw_skyline_fill 0`: the
  land-outline horizon, as before the fill (v0.0.30).
- Saved configurations: `aw_skyline_fill` is an archived setting, so a save from v0.0.31 or a dev
  build still holds 1. The engine command `aw_horizon_migrate`, run once from `quake.rc` after
  `config.cfg` (the `aw_gallery_migrate` pattern), sets it to 0 once and records
  `aw_horizon_defaults 1`; a later explicit choice stays.
- The object silhouetting method is unchanged in the engine and selectable with
  `aw_skyline_fill 1` (`dbg skyline fill 1`): experimental and buggy (sprites need their shapes
  from the alpha channel); tested but subpar results; kept for future improvement. Examples of the
  subpar result: the fog-colour columns at the two poses above.

Still open: the planned improvements below.

## Planned improvements (owner, 8 October 2026)

1. The skyline fill must not let the topography show through.
2. Sprites must become silhouettes of their actual form, honouring their transparent (alpha)
   pixels, instead of solid blocks or columns.

## Verification

- FS-UAE A/B/C/D frames at both poses, headlamp off: dev1 engine and v0.0.31 engine with the fill
  on and off, and fog off (private evidence).
- `tests/test_horizon_method.py`: the game config selects 0, `aw_horizon_migrate` runs after
  `config.cfg`, the silhouetting method stays registered and documented.
- `tests/aga_horizon_test.c` (native): with the fill on, the sky below a far pixel takes the fog
  colour; with it off, the sky stays; the migration changes a saved 1 once and keeps a later one.
- Pending: the next image in FS-UAE at both poses (default land outline).

## Prevention

Matched horizon views on fixed exterior cameras (with and without flora) in the playtest checks.
The defaults and both methods are pinned by the tests above.
