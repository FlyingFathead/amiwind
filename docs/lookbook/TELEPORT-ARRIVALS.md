# Look book page TELEPORT-ARRIVALS

_Generated from tests/lookbook/pages.json with AmiWind v0.0.67._

A teleport to a settlement arrives on its ground, not under it, in a wall or in the air.

## What the maintainer confirmed

The teleport picker's places are arrived at standing on the ground: the player neither falls after the arrival nor is stuck in a solid.

- 2026-10-30, on v0.0.57: the maintainer used the teleport picker between settlements and asked for it in every beta and smoke test (the settlement sweep)

## How it is checked

A scripted session step of the look book (`tests/lookbook/teleport_arrivals.txt`), run with every other page in one emulator session on every development build before it is delivered. Its numbers are the check; its pictures are compared with their references where it has them.

- picture `arrive-balmora`: the arrival in Balmora
- picture `arrive-vivec`: the arrival in Vivec
- picture `arrive-aldruhn`: the arrival in Ald'ruhn
- picture `arrive-suran`: the arrival in Suran
- picture `arrive-khuul`: the arrival in Khuul

- after each arrival the player's height stays within 2 units over 4 seconds (no fall) and the standing box is not in a solid (aw_pos, aw_blockers)

Status: checked on every development build.

## The code it lives in

- `engine/aga/src/aw_scene.c`: `teleport_coordinate` (the teleport and its arrival point)
- `tools/tp_places_lut.py` (the picker's places and their arrival points)

## The code it guards

No code is marked yet: the marker goes on the code once the page passes.

## Feature pages

- [AMIWIND_CONSOLE_COMMANDS.md](../AMIWIND_CONSOLE_COMMANDS.md)

## Register entries

<!-- the register history below is rendered from docs/bugs/bugs.json when the page is rendered -->

### [DBG-TP-NO-FLOOR-FALLBACK-63](../bugs/DBG-TP-NO-FLOOR-FALLBACK-63.md)

dbg tp to a spot with no floor under it falls back to the frame centre. State: open; found in v0.0.63.

- 2026-11-10 06:01 +0200 seen again on v0.0.64-dev1: Seen again in the v0.0.64-dev1 in-game check, on lava: dbg tp with a height into the Red Mountain lava pool (dbg tp 21392 69020 10880 and dbg tp 20880 69020 10880) answers "no walkable floor below" and "water surface not standable" and places the player at 0 0 2842 (the frame centre), so lava damage cannot be checked there.
- 2026-11-18 Guarded by the look book page TELEPORT-ARRIVALS (docs/lookbook/TELEPORT-ARRIVALS.md): A teleport to a settlement arrives on its ground, not under it, in a wall or in the air; a change to the code it lives in must pass that page before it is merged (docs/LOOKBOOK.md).

### [TP-BEING-TRIBUNAL-FALLS-THROUGH-67](../bugs/TP-BEING-TRIBUNAL-FALLS-THROUGH-67.md)

Teleporting to a character in some Tribunal interiors drops the player through the floor (the pawnbroker Ten-Tongues Weerhat, the Assassin). State: open; found in v0.0.66.

- 2026-11-17 A second teleport to a Tribunal interior fell through the floor (the Assassin); a teleport into a Tribunal Dwemer ruin lands on the floor correctly.
- 2026-11-17 Cause found by number on the v0.0.67-dev1 image: the being teleport handed the character's feet as a room arrival, so the arrival search started inside the floor and took the floor under the room; 1,302 of 3,623 being arrivals were under their floor, every room and door arrival on its floor. Fixed in source by lifting the point to a door arrival's height; 0 under a floor after the fix (tools/tp_arrivals.py).
- 2026-11-17 19:52 +0200 seen again on v0.0.67-dev1: Teleporting to Ten-Tongues Weerhat and to the Assassin in Tribunal puts the player through the floor
- 2026-11-18 Guarded by the look book page TELEPORT-ARRIVALS (docs/lookbook/TELEPORT-ARRIVALS.md): A teleport to a settlement arrives on its ground, not under it, in a wall or in the air; a change to the code it lives in must pass that page before it is merged (docs/LOOKBOOK.md).
- 2026-11-18 seen again on v0.0.67-dev2: Seen again on the v0.0.67-dev2 image (the maintainer, 2026-11-18), in Bloodmoon interiors too: dbg tp into Skaal Village, The Greathall left the player under the hall's floor (local 15 -8 -121), looking up at the people above; Tribunal and Bloodmoon teleports land under the structures in many places. Decided direction: a teleport into an interior arrives where a door into that interior puts the player, as entering it does.
