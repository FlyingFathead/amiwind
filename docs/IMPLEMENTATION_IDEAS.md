# Implementation ideas and research queue

Proposals recorded 27 September 2026, after checkpoint-014. These are not
implemented features. Verified mappings, causes and accepted fixes belong in
[IMPLEMENTATION_JOURNAL.md](IMPLEMENTATION_JOURNAL.md); priority is governed by
[ROADMAP.md](ROADMAP.md).

## Host conversion and runtime working sets

1. Generate a coverage/dependency report for the agreed starting area before
   increasing the resident scene. Classify omissions as unsupported record type,
   missing asset, selection bounds, or scripted/disabled state.
2. Share immutable assets by content/recipe hash while keeping distinct placed
   reference IDs. Select connected structures by transformed bounds, with one
   owner per cross-chunk reference to avoid duplicate collision and mutable state.
3. Trial material/UV-aware reduction and distance variants at fixed cameras.
   Compare silhouettes, doorway gaps and collision as well as render cost.
4. Choose chunks/cache sizes from measured geometry, textures, collision and
   audio deadlines. Current world geometry is resident; music is streamed.
5. Separate mutable world/inventory state from disposable render data before
   interior transitions and container interaction. Round trips must not reset
   looted containers or duplicate items. See [CONTAINERS.md](CONTAINERS.md).

## Combat: make dice-roll outcomes visible

Owner suggestion: a Morrowind mod reportedly preserves dice-roll combat while
showing an opponent dodge or block when an attack roll fails, making the miss
understandable instead of leaving an apparently connected swing unexplained.
**The mod's name, URL, implementation and license are not verified.** Find it on
[Nexus Mods](https://www.nexusmods.com/morrowind) during the later combat research
stage; do not attribute these claims to a guessed mod or copy its material.

The design goal is to retain the RPG hit calculation and improve feedback. Study
how the mod selects/times defensive poses and distinguishes misses from actual
blocks, what animation data it needs, and its collision/gameplay side effects.
Record the eventual exact link/version and findings here. Owner decision: study
the behavior as inspiration and implement AmiWind's version independently.
Do not copy the mod's code or redistribute its assets. Use our own implementation
and the existing local conversion pipeline for user-owned animation data.

Possible AmiWind experiment after basic actors and combat outcomes work:

- Resolve the attack once at its defined contact time, then select an appropriate
  visual response from that result. Animation must not reroll or alter hit odds.
- Distinguish an out-of-reach swing, failed hit roll, actual block and landed hit.
  A cosmetic defensive pose must not silently grant block skill progression,
  shield effects or extra gameplay rules.
- Test short baked evade/deflection/recoil poses appropriate to actor equipment;
  choose a readable fallback when a pose is unavailable. Avoid forced root motion
  through walls, off piers or into other actors.
- Align sound, impact and damage feedback with the outcome; a miss should not
  play successful damage effects. Preserve deliberate character stats and fatigue
  effects when the underlying combat rules are implemented.
- Compare identical seeded outcomes with presentation enabled/disabled. Measure
  pose/skin memory, frame cost and nearby actor limits on the target hardware.

This is later presentation research, not a promise to replace the current visual
hand punch with full combat in the next exterior checkpoint.

## Opening ship: spend detail where play begins

Owner priority: the prison ship's interior is the meaningful opening space.
Treat it as a separate interior scene and validate movement from below deck to
the exterior before the Census-office handoff. The exterior can be simplified
aggressively while retaining its silhouette, deck, cabin and gangplank.
Investigate baking high-detail surfaces onto simpler geometry; do not spend
polygons on every exterior moulding. Current ship LOD uses original material
textures with approximate UV projection, not a new high-to-low detail bake.

Console direction: solid configurable background; opacity postponed in favor
of the cheaper fill. Preserve the existing retro font as an optional backup
while adding a readable diagnostic atlas and space-separated debug commands.
