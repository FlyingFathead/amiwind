# NPC-FOLLOW-FLOORS-33: The test companion cannot find stairs to another floor of an interior; it is placed beside the player after 6 seconds

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | NPC companion test: flood fill of 8 x 8 step cells (128 units) around the follower |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | low: Debug feature; the follower catches up by the stuck teleport, as designed for the prototype. |
| Family | Actors and NPCs (`actors-npc`) |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open. A known limit of the first two stages of the companion's navigation; stage 3 is the repair.

## Symptom

With `dbg companion test` in a multi-floor interior, when the player goes to another floor the
companion walks against the nearest wall, pings, floods a small area and gives up. After 6 seconds
without progress it is placed beside the player (console: "Companion teleported (stuck)").

## Where

The NPC companion test (`dbg companion`, docs/DEBUG_OVERLAYS.md "NPC companion test"), navigation in
`engine/aga/src/aw_npcpath.c`.

## How it happened

Stage 1 walks straight at the player; stage 2 pings (short sweeps around the follower) and floods
8 x 8 step cells of 16 units (128 units square) around it. A staircase farther than that, or one
that turns back on itself, is outside what the follower can see, so the flood fill ends with no
cell nearer the player.

## Why it was not caught

It is the expected limit of the prototype; this is its first measurement in FS-UAE.

## Reproduction

FS-UAE, Balmora South Wall Cornerclub (`dbg scene bmsouthwall`), `dbg companion test`, then stand
on the upper floor or in the cellar. Measured 9 October 2026: per floor change 2 stuck events,
2 pings (15 sweeps each), 1-2 flood fills of 10-28 cells, then the stuck teleport.

## Repair

Not yet: stage 3, a local-patch A* on per-chunk walkable graphs (or Morrowind's own path grids
for interiors), within the same per-think trace budget.

## Verification

Pending stage 3: the same South Wall floor changes without a teleport.

## Prevention

The companion counters (`dbg companion`) report stuck events, flood fills, lost searches and
teleports, so a route that falls back to the teleport is visible in every test.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Actors and NPCs (`actors-npc`). Actor placement, models and behaviour; the actor placement gate. See [families](README.md#families).

- AW-20260928-05 (no report page): Dock guard misses approach interception
- AW-20260929-01 (no report page): Player passes through town NPCs
- AW25-10 (no report page): Actor-contact failures stopped image assembly only after terrain
- [NPC-BAKE-VERTEX-32](NPC-BAKE-VERTEX-32.md): NPC model bake exceeds the alias vertex budget for two Telvanni residents
- [NPC-IDLE-ONLY-ANIM-33](NPC-IDLE-ONLY-ANIM-33.md): NPCs play only their idle animation: no walking, running, turning or other animation groups
- [NPC-WEAPON-MESH-33](NPC-WEAPON-MESH-33.md): NPCs hold no weapons or shields; combat uses them unseen

<!-- END GENERATED CATEGORY -->
