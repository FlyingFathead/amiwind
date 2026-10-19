# VIVEC-ARENA-WATER-FALL-32: The sea ends at the Arena canton edge: sky below the horizon, and the player falls out of the area through the water

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 8 October 2026, in v0.0.32-dev3 |
| Where | Vivec Arena preview, east of the Arena canton: LOCAL 1374 165 -212 and LOCAL 1076 -150 65 |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev3, v0.0.32 (last seen) |
| Severity | medium: The player can fall out of the area. |
| Family | Vivec preview frame and its joins to the world (`vivec-frame-edge`) |
| Playtest version | v0.0.32-dev3 |
| From commit | source and engine 91a7eeb |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.43-dev3 (18 October 2026)._

## Status: 18 October 2026

Reported again by the maintainer in v0.0.43-dev2 from the St. Olms ledge (whole-city CHIM Vivec,
cell 4,-12, GLOBAL 39260 -91135 1859, LOCAL 1623 256 464, heading NE 037, pitch 18, time 00:00):
the sea no longer reached the horizon; sky and clouds showed below it. Cause: the day/night sky was
switched off in that session (`aw_daynight 0`, a saved setting, confirmed by the maintainer); the
build data is unchanged since v0.0.42. Repaired in the fog pass (branch v0.0.43-farsea): with the
day/night sky off, sky below the horizon takes the fog colour too, so the sea meets the horizon with
either setting. The fall out through the water (report 1 below, v0.0.32 Arena preview) still waits
for its recheck in whole-city CHIM Vivec, so the bug stays open.

## Status: 8 October 2026

Open; cause unknown. Project decision: fix later, not a v0.0.32 blocker; known in v0.0.32. Reported by
the maintainer while playing the v0.0.32-dev3 private test (8 October 2026). Present in every build with the
Vivec Arena preview (v0.0.32-dev1 to dev3, v0.0.32).

## Symptom

Two maintainer reports from the same area, east of the Arena canton towards the Telvanni canton:

1. Going into the water near the Telvanni canton: "the water connects nowhere and you fall off the
   area". Underwater blue tint; HUD GLOBAL 41849 -86377 -848, LOCAL 1374 165 -212 (inside the
   +-1536 frame), heading E 093, pitch -24, time 13:09; location label "Vivec, Telvanni".
2. Standing under an arch at the canton edge: LOCAL 1076 -150 65 (GLOBAL 40658 -87640 260),
   heading NE 044, pitch -14, time 13:31, label "Vivec, Arena". The water surface stops a short
   way out; sky and cloud texture are drawn below the horizon where open sea should be, with the
   underside of the canton structure overhead.

Both are one defect: past the canton edge there is no sea surface drawn and nothing to stand on or
swim in, so the view shows sky below the horizon and the player falls out of the area.

## Where

The Vivec Arena frame (`config/vivec_arena.json`, bounds +-1536 local units, draw distance 540), its
region maps `va*.bsp` written by `tools/import_town.py`, and the water and terrain the frame is
given. Seyda Neen, Balmora and the open world are not known to be affected.

## How it happened

Unknown. Candidates to measure: the frame has no sea bed or water volume (or no terrain under the
water) in part of the frame; the water surface is clipped to the converted canton pieces instead of
covering the frame; the bottom of the frame is open, so a swimming player sinks out of the map.

## Why it was not caught

The Arena checks covered the canton top, the stairs, the residents and the arrival point. Nothing
checks that the water surface and a sea bed cover the whole frame, and no test swims or looks out
from the canton edges.

## Reproduction

v0.0.32 (or dev3): `dbg tp vivec_arena`, walk east to the Telvanni side of the Arena canton.

- Pose 1: LOCAL 1374 165 -212, heading E 093, pitch -24: enter the water and keep swimming down
  or east.
- Pose 2: LOCAL 1076 -150 65, heading NE 044, pitch -14: look out under the arch.

## Repair

18 October 2026 (the sea below the horizon, branch v0.0.43-farsea): the CHIM far layer draws the sea
in the fog colour only up to `chim_far_reach` (896 local units, the legacy overlap depth). From a
ledge 464 units above the water, that is everything more than about 28 degrees below eye level;
between that and the horizon the view is sky. With the day/night sky on, that sky is painted in the
full fog colour (`R_DayNightSkyPixel` in `engine/aga/src/r_sky.c`: rays below the horizon take
gradient band 0, which is the fog colour at every time of day), so it joins the fogged sea: the
"water into eternity" look. With `aw_daynight 0` the fog pass used the static fog table and left
those sky pixels raw, so clouds showed below the horizon (dev2 frame: flat 102 119 136 = level 15 of
`gfx/fog.lmp`, the raw daytime sky at midnight). Now `AW_FogDraw` (`engine/aga/src/aw_fog.c`) paints
sky pixels whose ray points below the horizon in the static fog's level 15 when the day/night sky is
off: one comparison per sky pixel, only on that path. The day/night path, the horizon row and the
sky above it are unchanged; `aw_land_fill 0` keeps the previous picture. Regression test:
`tests/aga_daynight_test.c` (`fog_projection`), run by `tests/test_aga_native_source.py`.

8 October 2026: not yet (project decision: later). First measure what the frame map holds at both poses (water
brushes, terrain, sea bed, map bounds). Related:
[VIVEC-ARENA-FRAME-EDGE-32](VIVEC-ARENA-FRAME-EDGE-32.md) (the visual cut where neighbouring canton
bodies end at the frame edge), [VIVEC-ARENA-TP-ARRIVAL-32](VIVEC-ARENA-TP-ARRIVAL-32.md) (the
earlier arrival under the water) and [VIVEC-ARENA-FLOATING-NPC-32](VIVEC-ARENA-FLOATING-NPC-32.md)
(a resident at a walkway end with sky below him, same area).

## Verification

Pending.

## Prevention

Proposed: a frame check in the town import report that the water surface and a floor under it cover
every point of the frame below the water line, plus a swim and a look-out pose at each canton edge in
the Arena smoke test.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Vivec preview frame and its joins to the world (`vivec-frame-edge`). The Vivec Arena preview is one isolated frame: what lies at or beyond its edge (canton cuts, sea, bridges, the open-world maps around it) is missing, cut or wrong until the world streamer joins Vivec to the world. See [families](README.md#families).

- [DOCS-VIVEC-FRAME-PLAN-36](DOCS-VIVEC-FRAME-PLAN-36.md): The docs contradict each other on how Vivec goes onto CHIM (one frame vs eight district frames vs the coordinate range)
- [TOWN-EDGE-UNBUILT-32](TOWN-EDGE-UNBUILT-32.md): Leaving a town into an unbuilt neighbour drops the player into a bare world map
- [VIVEC-ARENA-FLOATING-NPC-32](VIVEC-ARENA-FLOATING-NPC-32.md): A Vivec resident stands at the end of a walkway by the Telvanni canton with sky drawn below his feet
- [VIVEC-ARENA-FRAME-EDGE-32](VIVEC-ARENA-FRAME-EDGE-32.md): Neighbouring canton bodies end at the Arena frame edge, in view
- [VIVEC-ARENA-HANDOFF-32](VIVEC-ARENA-HANDOFF-32.md): The Arena frame's handoff area reaches into neighbouring cantons; its frame edge can be in view
- [VIVEC-CANTON-SKY-HOLE-32](VIVEC-CANTON-SKY-HOLE-32.md): Sky shows through a Vivec canton wall seen from below
- [VIVEC-DISTANT-BRIDGES-32](VIVEC-DISTANT-BRIDGES-32.md): Distant bridges between the Vivec cantons are not drawn

<!-- END GENERATED CATEGORY -->
