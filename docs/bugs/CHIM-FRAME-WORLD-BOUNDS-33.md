# CHIM-FRAME-WORLD-BOUNDS-33: A CHIM frame map must carry an empty world whose bounds cover the frame

## Status: 8 October 2026

Open. Found by the second CHIM engine slice (terrain in the world tree; branch v0.0.33-chim-engine).

## Symptom

The engine replaces a CHIM map's own world tree with the grafted frame world, but the server builds its
area nodes from the map's world bounds. A frame map with smaller bounds would misplace entities.

## Where

CHIM builder (frame map) and `sv_world.c` area nodes.

## How it happened

The world model is replaced after the server set up its areas.

## Why it was not caught

Host tests only so far; no emulator run on real data.

## Reproduction

A frame map whose world is smaller than the frame.

## Repair

Not yet: the builder writes the frame's map with an empty world covering the frame; the engine
checks the bounds and refuses a frame that does not fit.

Frame map entities (8 October 2026): a CHIM frame map carries only `worldspawn` (with
`_chim_frame`), the `aw_npc` entities and one `info_player_start`; any other entity class is
refused with an accounting report ([CHIM-PAYLOAD-PARITY-33](CHIM-PAYLOAD-PARITY-33.md)).

## Verification

Pending.

## Prevention

Builder and engine tests for the frame bounds.
