# Implementation ideas and research queue

_Last updated with AmiWind v0.0.59-dev6 (3 November 2026)._

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

## Speed: techniques under consideration (3 November 2026)

Ideas for a faster frame on the 68040 and the 68060, and for a smaller memory and disk footprint. None of them may
change how the game looks: each is checked with stills at fixed cameras against the current path. Each one is A/B
testable: a console and config switch (on/off, 1/0), and an entry in the graphics options once it is built, so the
old and new paths can be compared in the same session. Each is measured first and kept only if the measurement shows
a gain; one that does not help is taken out again.

1. **Early off-screen rejection of objects and actors.** A cheap bounding-sphere test against the view before an
   object's model is set up, so objects behind or beside the camera cost almost nothing. In towns nearly every object
   is handed to the drawing setup today; the first step is to measure where the existing checks drop them, and whether
   one sphere around a whole chunk or block of objects rejects them together. Planned switches: an on/off setting for
   the test, and a debug view that draws each object's sphere, to see what is rejected.
2. **Doorway culling in interiors.** Each doorway of a room's sections gets an on-screen rectangle; sections seen
   only through a doorway outside the view, or behind another doorway's rectangle, are skipped with everything placed
   in them. Biggest in large interiors such as the Vivec cantons and the guild halls. Needs doorway data from the
   builder in the CHIM room format.
3. **Integer maths for actor models (doubtful, measure first).** Transforming actor models with fixed-point arithmetic
   and small lookup tables (reciprocals, sine and cosine) instead of the floating-point unit. On a real 68040 the
   floating-point multiply is fast and a 32-bit integer multiply is not, so this may not gain anything there; where it
   can help is in avoiding floating-point instructions the 68040 has to emulate in software. Heavy actor models cost
   mostly through their number of vertices and triangles, so fewer of them for distant actors is likely the bigger
   win. Profiled on the 68040 preset and the Raspberry Pi 4 before any code; the current path stays selectable and the
   two are compared pixel for pixel.
4. **Compressed music and voice (4-bit ADPCM).** About half the size of today's 8-bit audio on disk and in memory,
   decoded while playing. Lower priority: the format is lossy, so it is only an option if a blind listening comparison
   on WinUAE cannot tell it from today's audio, and only if audio is what strains the 32 MB budget or load times.

## Combat: make dice-roll outcomes visible

Maintainer suggestion: a Morrowind mod reportedly preserves dice-roll combat while
showing an opponent dodge or block when an attack roll fails, making the miss
understandable instead of leaving an apparently connected swing unexplained.
**The mod's name, URL, implementation and license are not verified.** Find it on
[Nexus Mods](https://www.nexusmods.com/morrowind) during the later combat research
stage; do not attribute these claims to a guessed mod or copy its material.

The design goal is to retain the RPG hit calculation and improve feedback. Study
how the mod selects/times defensive poses and distinguishes misses from actual
blocks, what animation data it needs, and its collision/gameplay side effects.
Record the eventual exact link/version and findings here. Project decision: study
the behavior as inspiration and implement AmiWind's version independently.
Do not copy the mod's code or redistribute its assets. Use our own implementation
and the existing local conversion pipeline for user-owned animation data.

Found (9 October 2026): "Can't Touch This - Combat Miss Feedback (OpenMW)",
version 1.0.3 (6 June 2026), by MrArrean and Dubiousnpc,
<https://www.nexusmods.com/morrowind/mods/59155>; the miss-feedback part of their
N'Garde combat mod, as an OpenMW Lua script. From its public description only
(nothing downloaded): when the player's attack misses a humanoid NPC, the NPC
plays one of 11 short "bob and weave" dodge animations, authored for the mod (8
by Dubiousnpc), loaded as additional animation sources; the hit chance itself
is the original's (no re-roll), only the feedback is added; creatures are not
covered. The description does not say how the pose is timed against the swing
or how a miss is told from a block. What AmiWind takes from it: a miss deserves
its own visible reaction distinct from a block. Our version uses only the
player's own game data: `dodgel`/`dodger` (3 in-place frames of the original
walkleft/walkright) and the original shield block group, chosen by the combat
layer from the swing's result at its contact time ([ANIMATION.md](ANIMATION.md)
"Block and dodge"). A recoil from the start of hit2 or hit3 (3 frames, about
16 to 22 KB) is a possible lean-back alternative to the sidestep.

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

Project priority: the prison ship's interior is the meaningful opening space.
Treat it as a separate interior scene and validate movement from below deck to
the exterior before the Census-office handoff. The exterior can be simplified
aggressively while retaining its silhouette, deck, cabin and gangplank.
Investigate baking high-detail surfaces onto simpler geometry; do not spend
polygons on every exterior moulding. Current ship LOD uses original material
textures with approximate UV projection, not a new high-to-low detail bake.

Console direction: solid configurable background; opacity postponed in favor
of the cheaper fill. Preserve the existing retro font as an optional backup
while adding a readable diagnostic atlas and space-separated debug commands.
