# CHIM-PAYLOAD-PARITY-33: The CHIM world misses the image step's edits to Balmora (harvest mushrooms, town flora)

## Status: 8 October 2026

Open: fixed in source on the CHIM branch (v0.0.33-chim-format, 6945b43), not merged, not shipped;
blocks CHIM milestone 1 until merged. Found by the CHIM builder's comparison of the Balmora frame
with the legacy image.

## Symptom

The CHIM Balmora statics match the pre-image region maps exactly (1,488 references, origins within
0.0001 units), but the image step then edits Balmora in two ways the CHIM world does not see:

1. 20 Bitter Coast mushroom statics (`flora_bc_mushroom_01`, `_04`, `_05`, `_06`, `_08`) are removed
   from the maps and placed at run time from the per-region harvest catalogues
   (BUILD-HARVEST-NOT-BUILT-32). Under CHIM they would show twice (static and harvestable) or be
   unpickable.
2. The town flora step adds 5 references (49320, 252872, 252890, 252891, 253335) that the CHIM world
   lacks.

## Where

CHIM builder source selection (`tools/chim/`); the legacy image step's harvest removal and town
flora staging, which run after the region maps the CHIM builder reads.

## How it happened

The CHIM builder takes its statics from the region maps before the image step, while the image
step's later passes change what a player sees in Balmora.

## Why it was not caught

The CHIM comparison checked statics against the pre-image region maps only, not against the final
maps of the image.

## Reproduction

Compare the CHIM Balmora statics, harvest references and town flora references with the final
Balmora region maps of an image.

## Repair

On the CHIM branch (6945b43): the `chim` stage takes the harvest step's source placements and the
shared town-flora selection (the same code the image step uses), and a two-way frame-map gate
checks CHIM statics + harvest references + town flora against the final region maps. Balmora:
1,488 - 20 harvest + 5 town flora = 1,473 statics; the gate passes.

Open requirements for the parity gate (8 October 2026):

- The frame origin equals the town's region-map origin: door arrivals, the region directory,
  harvest origins and saves rely on it.
- Harvest catalogues of CHIM towns use the external alias representation (4), or the frame map
  keeps the harvest `func_wall`s: brush plants (representation 0) bind to `func_wall` edicts by
  `aw_ref`, which a frame map without those entities does not have.

Frame map entities (8 October 2026): a CHIM frame map carries only `worldspawn` (with
`_chim_frame`), the `aw_npc` entities and one `info_player_start`. Any other entity class is refused
with an accounting report, so nothing the legacy maps carry can be dropped silently.

## Verification

Balmora on the CHIM branch: 1,473 statics, two-way frame-map gate passes. Tests on that branch
(`tests/test_chim_parity.py`) cover the shared selection (the harvest numbers are the image's removal set, town entries are the
image's, harvest and flora reach the `chim` stage by default, debugging opt-outs drop them).
Pending: merge, and the two requirements above.

## Prevention

The per-area parity gate in every CHIM build; the entity-class accounting report.
