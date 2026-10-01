# Character presence, progression and placement

## Status

Source review and implementation requirements, 1 October 2026. AmiWind has
selected opening behavior and persistent quest/global facts, but does not yet
execute the general Morrowind character-script lifecycle. This document records
that missing behavior; it does not declare it implemented.

An NPC record describes a character, and a CELL reference supplies an authored
placement. Neither guarantees that the character should be visible at the start
of a new game, remain at that position, or remain present after a quest.
Original startup scripts, local scripts, externally targeted scripts, dialogue
results and authored AI packages must all be considered.

## Confirmed example: the Balmora Dreamer

The contact report's outdoor Dreamer is `Dreamer_Talker01`, placed reference
297839. Direct inspection of the base master establishes this sequence:

1. The original `Startup` script disables this actor.
2. Its attached `dreamer_talkerEnable` script checks journal `A2_2_6thHouse`.
3. If the actor is disabled and that journal index is exactly 50, it enables
   the actor. If already enabled, the script returns without disabling it.

This is a later progression-dependent appearance. It must not become an
unconditional new-game resident just because its reference exists in the master
or because a converter generated its model successfully.

Preserve the source transition semantics. Do not replace the sequence with
`visible = journal == 50`, which would incorrectly hide an already enabled actor
after the index changes. Do not silently widen `== 50` to `>= 50`. Loading a save
must restore the actor's enabled state and relevant script state, rather than
reconstructing them from one current journal value or rerunning new-game startup.

The current converted resident set includes this Dreamer, but its original
startup/enable behavior is not implemented. This remains a known progression
gap even if its ground-contact audit passes.

## Other confirmed cases among the contact findings

| Actor | Source behavior to preserve |
| --- | --- |
| Fargoth | `LocalState` alone does not describe his movement. The separate `lookoutScript` gates a sneak/travel route on quest, time and proximity, with dialogue able to end the sequence. |
| Character-creation dock guard | `CharGenRaceNPC` changes his destination during the opening. `CharGenClassNPC` later disables him alongside the boat objects. |
| Vodunius Nuccius | `voduniusScript` disables him on a cell change once `MS_Nuccius` reaches at least 100. Quest completion and the later cell-change event are distinct. |
| Banalz and Baadargo | Both attach `slaveScript`, which has owned, for-sale, player-owned and freed states, with follow/wander behavior and disappearance after a freed character changes cell. Reachability of each branch for each individual still needs checking. |
| Other affected residents and guards | Their NPC_ records have authored wander packages. No attached script does not establish that an external script or dialogue cannot affect them. |

The original 23 contact findings cover 15 placed references, with repeated cases
across converted scenes. These examples establish that their authored positions
are not a complete simulation of their lifetime behavior.

## Separate state responsibilities

| State | Required meaning |
| --- | --- |
| Identity | Original object ID plus placed reference ID; two guards sharing one NPC_ record remain distinct placements. |
| Presence | Enabled/disabled state and the source condition or event that changes it. |
| Life and pose | Living, dead or another explicitly supported source state; independent of visibility. |
| Movement | Current transform, AI package, destinations, local script variables and relevant timing. |
| Contact | Support appropriate to the current active pose and position; grounded, swimming, flying or another evidenced state. |
| Persistence | Changes survive scene unloading, overlap handoffs and save/restore without duplicating actors or resetting quests. |

Grounding corrects a supported active placement against converted geometry.
It must not enable an absent actor, replace a quest destination, reset movement
on every scene entry, or turn a deliberately airborne pose into a ground resident.
Conversely, later quest movement does not excuse visibly unsupported feet in a
converted standing pose. The [contact audit](NPC_GROUND_CONTACT.md) checks its
declared geometric scope; it does not validate quest or schedule behavior.

## Implementation and verification roadmap

- Retain source identity and activation/movement provenance during conversion,
  including externally targeted scripts and dialogue results. Record unsupported
  behavior explicitly rather than presenting a static resident as faithful.
- Add source-derived lifecycle transitions using runtime quest/global facts and
  persistent per-reference state. Keep authored placement separate from current
  position, enabled state and any bounded conversion correction.
- Resolve presence before spawning interactive scene entities. Apply transitions
  when their original conditions/events require them; keep overlap copies tied
  to the same canonical placed reference.
- Verify the Dreamer absent in a fresh game, enabled by the exact source branch,
  and retained correctly after subsequent progression, scene reload and save/load.
- Verify dock-guard stage changes, Fargoth's external controller, Vodunius's
  cell-change disappearance and the applicable slave-state branches separately.
- Recheck contact for supported new positions and poses. Passing initial idle
  contact must never be reported as completion of character behavior.

Evidence: direct inspection of NPC_, CELL, SCPT and relevant INFO result records
in the retained base master, SHA-256
`5c3c8c2cbd20e25901b59b3ece33d36b7ef0e3d60ad8d11828bcc61a5ead1647`.
The [contact findings and source review](NPC_GROUND_CONTACT.md#source-progression-review-1-october-2026)
identify the affected references. Expansion/mod overrides and saved-game state
are outside this source review. Original game scripts and assets are not copied
into this documentation package.
