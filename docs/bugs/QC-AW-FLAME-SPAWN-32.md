# QC-AW-FLAME-SPAWN-32: Every aw_flame entity prints load errors: the game logic has no aw_flame spawn function or aw_flame_size/aw_flame_shape fields

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 8 October 2026, in v0.0.32-dev3 |
| Where | Map load of aw_flame entities (game logic, entity loader) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.30-dev5, v0.0.32-dev2, v0.0.32-dev3 (last seen) |
| Severity | medium: Every placed flame prints about 23 console errors per load; likely slows Census loads. |
| Family | Game logic (QuakeC) and saves (`game-logic`) |
| Playtest version | v0.0.32-dev3 |
| From commit | source and engine 91a7eeb |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

<!-- contents start -->
## Contents

- [Status: 8 October 2026](#status-8-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 8 October 2026

Open: repaired in source (v0.0.32-flame-spawn), not yet in a built image. Found in the console of
the v0.0.32-dev3 smoke test (FS-UAE, build from source 91a7eeb); the same lines are in dev2's
console. Present since the scene converter started writing `aw_flame` entities (static flames,
v0.0.30-dev5); v0.0.31's console was not checked.

## Symptom

Every load of a map with placed flames prints, for each flame:

```text
'aw_flame_size' is not a field
'aw_flame_shape' is not a field
No spawn function for:

EDICT 138:
origin         ' 54.1 356.7  62.8'
classname      aw_flame
```

The dev3 smoke session printed 126 such blocks: 51 per Census and Excise Office load (two loads)
and 8 per prison ship load (three loads). The flames themselves are drawn (the engine reads them
separately), so nothing is missing on screen.

## Where

- `tools/prepare_mesh_bsp.py` (`flame_entities`): writes one `aw_flame` entity per particle flame
  of a placed mesh, with the keys `origin`, `aw_flame_size` and, for shaped emitters,
  `aw_flame_shape`.
- `engine/aga/src/aw_guard_torch.c` (`static_flames_load`): the only reader; it parses the map's
  entity text itself into the static-flame table.
- `engine/aga/qc/defs.qc`, `world.qc`: the game logic defines no `aw_flame` function and no
  `aw_flame_size` or `aw_flame_shape` field.
- `engine/aga/src/pr_edict.c` (`ED_ParseEdict`, `ED_LoadFromFile`): Quake's entity loader, which
  reports unknown keys and classnames.

Same mechanism, one more instance: `maps/vf2485.bsp` printed "'wad' is not a field" (a worldspawn
`wad` key that the game logic does not declare); the other open-world maps loaded in the session
did not.

## How it happened

1. The flame entities were designed for the engine's own table, read straight from the entity
   text, like Quake's `light` entities are read by the light compiler.
2. Quake's server still spawns every entity in the map through the game logic. For each key
   without a matching field it prints "'<key>' is not a field"; for a classname without a spawn
   function it prints "No spawn function for:", dumps the edict with `ED_Print` and frees it.
3. `ED_Print` prints each field with several console calls (name, one call per padding space,
   value), so one flame costs about 23 console calls: about 1,170 per Census load.
4. Each console call is also written to the debug log file and, with the remote console on, appended
   to the session's console log (opened and closed per call). See
   [CENSUS-LOAD-SLOW-32](CENSUS-LOAD-SLOW-32.md) for the load-time cost this likely causes.

## Why it was not caught

The lines are console noise that does not stop the load, and the flames draw correctly. No check
counts load-time console errors; the noise also hides real entity errors.

## Reproduction

Any build with placed flames: load the Census and Excise Office (for example `dbg tp census` or
the Seyda Neen door) and read the console or the remote console log; count "No spawn function"
(51 per load in dev3).

## Repair

Game logic only (`engine/aga/qc/world.qc`, compiled into `progs.dat`); the map writer, the maps
and the engine are unchanged. The Quake way, as id's `info_null` does:

- `.float aw_flame_size; .vector aw_flame_shape;` declare the two keys, with the types their
  values parse as;
- `void() aw_flame = { remove(self); };` is the spawn function: the entity is freed at once
  (`remove` is builtin #15, `PF_Remove`, which calls `ED_Free`, the same call the loader made
  before), so edict numbers and counts do not change;
- `.string wad;` declares the worldspawn key as id's `defs.qc` does (the terrain, gallery and
  torch-room maps that keep it printed "'wad' is not a field").

The engine's static-flame table keeps reading the map's entity text, not the edicts, so the
flames are the same. The new fields come after every existing field: no field moves, the system
fields and the program CRC (5927) are unchanged, so the engine's `progdefs` headers need no change.
Cost: each edict grows by 5 words (20 bytes), 12,000 bytes of the 600-edict array on every map
(12,432 hunk bytes measured with the larger `progs.dat`).

The other option (keys with a leading underscore plus an engine filter) would have needed new
maps and an engine change; not taken.

## Verification

- `tests/test_entity_spawn_contract.py` (fails before the repair, passes after): every classname
  the converters write has a spawn function (compiler-only `light`, `func_detail`, `info_null`
  excepted), every key they write is a declared field, a utility key or one the engine's loader
  handles; the real `flame_entities` output loads silently and the engine's flame reader still
  reads the same key names; `aw_flame` removes itself through builtin #15 (`PF_Remove`); with the
  validated compiler, the compiled `progs.dat` has the fields and the function, the CRC check
  passes, and every other field keeps its offset.
- The static-flame tests (`aga_static_flame_offsets_test.c`, `aga_static_flame_select_test.c`)
  and the compiled hand-rules test pass unchanged.
- FS-UAE, 8 October 2026: the dev3 image with only `DH0:id1/progs.dat` replaced by the repaired
  one (engine, maps and every other file unchanged). Its console log shows no "is not a field" and
  no "No spawn function" line over ten logged loads with flames in two sessions (prison ship and
  Census office); the dev3 control sessions print 708 and 732 such lines. "Scene ready" with the remote console on: Census
  200-414 ms against 8.8-20.9 s (table in [CENSUS-LOAD-SLOW-32](CENSUS-LOAD-SLOW-32.md)). The
  Census fireplace and candles look the same at the same pose in both builds. Hunk use per map
  grows by 12,432 bytes (Census 4,806,880 to 4,819,312; same delta on prison and Balmora).

## Prevention

`tests/test_entity_spawn_contract.py` runs in the full suite: a new converter classname or key
without its game-logic declaration fails the gate. Proposed still: a smoke-test check that counts
entity load errors in the console log with a limit of zero.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Game logic (QuakeC) and saves (`game-logic`). QuakeC entities, saves and game state. See [families](README.md#families).

- AW-20260928-10 (no report page): Interior door animation and sound missing
- AW-20260928-12 (no report page): Downstairs interior doors cannot open
- AW-20260928-19 (no report page): Courtyard barrel incorrectly says empty
- AW25-06 (no report page): Quicksave shown as empty; save ordering confusing
- [CENSUS-DOOR-STUCK-29](CENSUS-DOOR-STUCK-29.md): Player stuck after opening Census Office hall door
- [CHIM-COURT-BARREL-USE-33](CHIM-COURT-BARREL-USE-33.md): Census courtyard on CHIM: Fargoth's ring barrel cannot be used, so the opening cannot proceed
- CLOCK-01 (no report page): Automatic clock dropped fractional milliseconds each frame
- [COMBAT-FIST-BLOCK-33](COMBAT-FIST-BLOCK-33.md): A fighter with a shield blocks while fighting with fists
- [COMBAT-HIT-RECOVERY-33](COMBAT-HIT-RECOVERY-33.md): Fatigue hits did not stagger, and knockdowns lasted half a second too long
- [COMBAT-NO-CONDITION-33](COMBAT-NO-CONDITION-33.md): Weapon and shield condition were ignored in combat
- [COMBAT-NOT-SAVED-33](COMBAT-NOT-SAVED-33.md): Combat state and NPC deaths are not saved
- [COMBAT-PLAYER-ATTACK-TYPE-33](COMBAT-PLAYER-ATTACK-TYPE-33.md): The player's attack type and swing strength were random
- [COMBAT-PLAYER-KNOCKDOWN-33](COMBAT-PLAYER-KNOCKDOWN-33.md): The player's knockdown and knockout exist only in the combat rules
- [DEBUG-MAP-SAVE-VALIDATION-32](DEBUG-MAP-SAVE-VALIDATION-32.md): After a debug map load of an open-world map the autosave fails validation; two of three also report Interior spawn blocked
- RENDER-METADATA-29 (no report page): Native renderer metadata warns as an unknown QuakeC field
- SAVE-EQUIPMENT-29 (no report page): Quickload returns with hands and torch put away

Related bugs in other categories:

- [CENSUS-LOAD-SLOW-32](CENSUS-LOAD-SLOW-32.md): The Census and Excise Office takes 8-10 s to load in FS-UAE; other scenes 0.2-1.5 s

<!-- END GENERATED CATEGORY -->
