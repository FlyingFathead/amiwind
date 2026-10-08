# FLAME-RANGE-NEAREST-32: A hearth fire shows only up close when many candles are nearer

## Status: 8 October 2026

Open: repaired in source (v0.0.32-fire-range), not yet in a built image. Reported by the owner
on v0.0.32-dev1. Present since static flames got their per-frame budget (v0.0.30-dev5), so
v0.0.31 behaves the same; not a v0.0.32 regression.

## Symptom

Seyda Neen, Census and Excise Office (local -25 -20 64, heading south, pitch 10, 10:40): the
fireplace a few metres ahead shows no fire. The fire appears only when the player walks right up
to it.

## Where

`engine/aga/src/aw_guard_torch.c`, `AW_StaticFlamesDraw`: the flames of placed fires, candles and
lanterns (`aw_flame` entities written by the scene converter), drawn as flame particles plus Quake
particle embers (`pt_awember`, `r_part.c`).

## How it happened

Each frame the engine draws at most 12 static flames (`STATIC_FLAME_DRAW`) within 640 units, and
chose the 12 nearest in any direction, without looking at the view or the flame size. The Census
office has 51 `aw_flame` entities: one hearth (size 8) and 50 candles (size 0.8), most of them in
fours on chandeliers. At the owner's pose 14 flames are nearer than the hearth (about 100 units
away), 10 of them behind the camera, so the hearth ranked 15th and was never drawn. Closer to the
fireplace it got into the nearest 12, which matches the report. The map's `aw_flame` entities are
identical in v0.0.31 and dev1, and the selection code is unchanged since v0.0.31.

## Why it was not caught

The flame budget was checked in rooms with few flames; no room with more than 12 nearer flames,
most of them behind the camera, was in the capture set.

## Reproduction

Census and Excise Office: `noclip`, `aw_view -25 -20 64 277 10`; the fireplace has no flame.
`aw_static_flames_nearest 1` restores the earlier rule in a fixed engine.

## Repair

Engine only (`AW_StaticFlamesPick`), the same budget of 12 flames:

- Default rule (`aw_static_flames_nearest 0`): only flames whose particles can reach the view
  rectangle (same projection as the flame particles, with their size, spread and rise as margin)
  compete for the budget, ranked by drawn size over distance, so a hearth outranks far candles and
  flames behind the camera never take a slot.
- The earlier rule (nearest within range, in any direction) is kept and selectable:
  `aw_static_flames_nearest 1`.

## Verification

- `tests/aga_static_flame_select_test.c` (native, `test_aga_native_source.py`): a room modelled on
  the Census office; the earlier rule leaves the hearth out (12 nearest, checked against an
  independent distance oracle), the default rule draws it first and only flames in front; turning
  around gives its slot away; never more than 12; nothing beyond the range.
- Pending: the Census office pose in FS-UAE with the next image.

## Prevention

The native test pins both rules and the budget; rooms with many candles (Census office) are in
the interior capture set.
