# AmiWind v0.0.52-dev2 (in development)

Development snapshot, 26 October 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.52-dev1](RELEASE-v0.0.52-dev1.md); previous release: [v0.0.51](RELEASE-v0.0.51.md).

v0.0.52 is called "Skeletons Of Society, Vvardenfell Edition": every humanoid moves by one shared skeleton and one
shared animation table. dev1 was the first build with the skeletons in it; this second snapshot carries what was
fixed and added on the day after.

## New since v0.0.52-dev1

- **Dagoth Ur and the Heart of Lorkhan are in their rooms.** No build so far placed them: the room stages place only
  the creatures they list, and the list named only Vivec. Dagoth Ur now stands in the Facility Cavern and in
  Akulakhan's Chamber as his whole original model, every one of his 2,254 triangles, as in the NPC gallery; the
  Heart hangs where the game places it ([CREATURE-DAGOTH-UR-ABSENT-52](../../BUGS.md)). For now he plays his idle only.
- **No more Software Failures from a full memory.** The Amiga toolchain's `malloc` never returns "no memory": it
  stops the machine with a Software Failure (#80000027) instead. Every allocation of the engine now asks how much
  Fast RAM is free first, and a refused one is handled as the game always meant to. With 16 MB of Fast RAM the
  skeletal build stopped while loading Balmora; now it loads, and a table that does not fit leaves its characters
  standing in their rest pose ([SKEL-16MB-TRAP-52](../../BUGS.md), [SDK-MALLOC-TRAPS-52](../../BUGS.md)).
- **A warning box under 32 MB.** With less than 32 MB of Fast RAM a WARNING box says so before the AmiWind logo, for
  five seconds (ENTER goes on): "AmiWind requires at least 32MB of Fast RAM to run properly. Less than 32MB of Fast
  RAM was detected. This will mean that parts of the game will run incorrectly or not at all."
  ([RAM-WARNING-BOX-52](../../BUGS.md)).
- **Cheaper posing.** A skeletal character on a whole table frame is posed without blending, the bones that never
  move are prepared once per table, and the vertex loop is shorter ([SKEL-RUNTIME-COST-52](../../BUGS.md)).
- **Builds.** A stage that takes its results from a cache now counts the code those results come from, so a change to
  that code rebuilds it ([BUILD-KEY-UNIT-RESTORED-CODE-52](../../BUGS.md)); a reused stage no longer leaves empty folders
  for another stage to trip on ([BUILD-REUSE-FOREIGN-DIRS-52](../../BUGS.md)).

## Known in this build

- Dagoth Ur does not fight or speak yet: his attack from the start, his voice lines and his own skeleton with every
  motion come with the combat and script work of v0.0.53. Vivec keeps his reduced model for now.
- The posing cost on a slow 68040 is still being measured against the baked characters
  ([SKEL-RUNTIME-COST-52](../../BUGS.md)); the heads use the reduced detail ([SKEL-VERTEX-LIMIT-52](../../BUGS.md)); the NPC
  gallery and the player's own body are still baked.
- Everything else is in the [bug register](../../BUGS.md).
