# DEBUG-MAP-SAVE-VALIDATION-32: After a debug map load of an open-world map the autosave fails validation; two of three also report Interior spawn blocked

## Status: 8 October 2026

Open; cause unknown. Found in the v0.0.32-dev3 smoke test (FS-UAE, build from source 91a7eeb).
Seen on the debug path only.

## Symptom

In one session, after an autosave had just worked in Balmora ("Saved Autosave 2"), the console
command `map` was used to load three open-world maps:

| Map | Placement | Save |
| --- | --- | --- |
| `vf0291` | "Interior spawn blocked; use dbg noclip to inspect." | "Save state validation failed; previous saves retained." |
| `vf2386` | "Interior spawn: 0 0 -46" | "Save state validation failed; previous saves retained." |
| `vf2485` | "Interior spawn blocked; use dbg noclip to inspect." | "Save state validation failed; previous saves retained." |

The save code refused to write and kept the earlier saves, as designed; the fault is that the state
it was given did not pass validation.

## Where

- `engine/aga/src/aw_save.c` (`AW_SaveWrite`, autosave after a scene change) and
  `engine/aga/src/aw_save_codec.c` (`AW_SaveEncode`): the message comes from the encoder's
  validation.
- `engine/aga/src/aw_scene.c` (`AW_SceneSpawn`, `AW_InteriorPlace`): a map loaded with `map`
  rather than a scene change places the player with the interior standing-spot search around the
  map's start point.

## How it happened

Unknown. Open-world map names are valid save scenes (`AW_MapId` accepts `vfNNNN`), so the scene name
alone does not explain it. Candidates: a value outside the encoder's limits (position, actors
captured on the map, harvest state, story fields) after a load that bypasses the scene change; for
the blocked spawns, a start point more than the search's 88 units above the ground or inside
solid.

## Why it was not caught

The save tests cover saves after normal scene changes; debug map loads are not in the save tests,
and a refused save is only a console line.

## Reproduction

New game to release, then in the console: `map vf0291` (or `vf2386`, `vf2485`); wait for the
autosave a few seconds later and read the console.

## Repair

Not yet. First find which field fails (a debug print of the failing field in the encoder, or a
native test with a state captured after `map vf2386`). Then check whether a normal crossing into an
open-world map hits the same failure; if it does, this is not a debug-only fault.

## Verification

Pending.

## Prevention

Proposed: a save round trip after a debug map load and after an open-world crossing in the save
tests.
