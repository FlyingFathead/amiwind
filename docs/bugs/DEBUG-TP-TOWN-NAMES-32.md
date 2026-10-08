# DEBUG-TP-TOWN-NAMES-32: dbg tp help omits new towns and has no short town names

## Status: 8 October 2026

Fixed in source on v0.0.32-dev; not in the dev1 playtest build; not shipped at the time of writing. Found while
checking the v0.0.32-dev1 teleport presets.

## Symptom

`dbg tp vivec_arena` works (the town table marks the Arena as a teleport arrival, and the
`dbg tp` menu lists every installed map), but the help line still says only
"balmora/seydaneen/prisonship/<map name>", and `dbg tp vivec` says "Destination not found".

## Where

`engine/aga/src/aw_scene.c` (`scene_command` help text and name lookup).

## How it happened

Help text and names were written before the data-driven town table.

## Why it was not caught

No test compares the help text with the town table.

## Reproduction

In dev1: `dbg tp vivec`, then `dbg tp` with a wrong argument to see the help line.

## Repair

`scene_help()` builds the help line from the town table (every town marked for teleport
arrival); `dbg tp vivec` and `dbg tp arena` map to `vivec_arena` while the Arena is the only
Vivec town. README and the console command page say how to visit the Arena preview.

## Verification

`tests/test_debug_tp_names.py`; full gate 116 green (1,421 tests, engine with 0 warnings).
In-game check with the next engine build.

## Prevention

A test that every teleport town appears in the help text.
