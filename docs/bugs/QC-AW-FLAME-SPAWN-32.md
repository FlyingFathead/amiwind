# QC-AW-FLAME-SPAWN-32: Every aw_flame entity prints load errors: the game logic has no aw_flame spawn function or aw_flame_size/aw_flame_shape fields

## Status: 8 October 2026

Open; cause found, not repaired. Found in the console of the v0.0.32-dev3 smoke test (FS-UAE,
build from source 91a7eeb); the same lines are in dev2's console. Present since the scene converter
started writing `aw_flame` entities (static flames, v0.0.30-dev5); v0.0.31's console was not
checked.

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

Not yet. Options in the Quake way, to choose and test:

- declare `.float aw_flame_size; .vector aw_flame_shape;` and a `void() aw_flame = { remove(self); };`
  in the game logic, so the loader accepts and drops the entity silently;
- or write the keys with a leading underscore (`_aw_flame_size`, which Quake discards as a utility
  key) and use a classname the engine filters before spawning;
- and give `vf2485`'s `wad` key the same treatment (declare `.string wad;` as id's `defs.qc` does).

The engine's static-flame table must keep reading the same values (native test).

## Verification

Pending: a map load with flames prints no "not a field" or "No spawn function" lines, and the
static-flame count is unchanged.

## Prevention

Proposed: a build check that every classname and key written by the converters exists in the
game logic (or is engine-only and filtered), and a smoke-test check that counts entity load errors
with a limit of zero.
