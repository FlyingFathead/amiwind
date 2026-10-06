# NPC traversal across world boundaries

**Design requirement recorded 2026-10-06. Planned behavior; not shipped.** AmiWind currently preserves selected NPC reference, scene, pose, health and dialogue counters across scene changes. The current gameplay scripts do not implement hostile pursuit targets or a chase loop, so this persistence must not be described as cross-boundary pursuit.

| Boundary | Hostile pursuers | Followers, escorts and scripted actors |
| --- | --- | --- |
| Artificial subdivision within one logical interior | Continue along a valid route; the subdivision is transparent to pursuit. | Continue when their role and script permit; retain stable identity and state. |
| Successive walkable exterior cells | May continue across cells without an arbitrary home-cell leash or one-cell cap; path and AI rules still apply. | Eligible companions may continue under their package/quest/script rules; retain stable identity and state. |
| Original teleport/loading door out of a cave, tomb or other interior | Hostile chase normally stops at the original exit, preserving Morrowind behavior. | Eligible follower/escort or scripted actors may enter or leave through appropriate original loading doors when their rules allow. Do not assume every friendly NPC follows. |

Across any permitted handoff, keep one authoritative actor identified by its stable original reference. Preserve applicable health, equipment, target/aggression, position, movement intent, dialogue and combat timers. Reach the actual traversable connection and arrive at its corresponding point; do not teleport an actor beside the player or duplicate it across overlapping sections. A pursuit boundary does not itself clear hostility or reset health.


See [cell-changing and pursuit requirements](CELL_CHANGING.md#pursuit-across-section-and-cell-boundaries), [world mapping](WORLD_MAPPING_PLAN.md), and [door mapping](DOOR_MAPPING.md). Reference context: [OpenMW issue 5101](https://gitlab.com/OpenMW/openmw/-/issues/5101) distinguishes hostile followers at teleport doors; it does not establish AmiWind implementation.

### Deferred: minimal NPC state outside loaded cells

This is a post-release design task, after the initial combat work. Determine how
to exclude the full NPC model and active simulation outside loaded cells while
retaining a minimal persistent record for travel, pursuit and following. The
representation, update schedule and safe re-entry method are not yet decided.
See the [roadmap and acceptance questions](ROADMAP.md#deferred-minimal-npc-state-outside-loaded-cells).
