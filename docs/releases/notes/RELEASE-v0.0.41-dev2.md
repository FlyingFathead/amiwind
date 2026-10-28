# AmiWind v0.0.41-dev2: Collisions And Boundaries

Development snapshot, 16 October 2026. Running on CHIM Engine v0.2.0. Previous snapshot:
[v0.0.41-dev1](RELEASE-v0.0.41-dev1.md).

This snapshot makes the rings 0, 1 and 2 world build end to end through the repository builder again.

## What changed since v0.0.41-dev1

- **Seyda Neen builds again.** Since v0.0.40 Seyda Neen's CHIM frame covers whole game cells, so it meets the
  surrounding ring cells on the cell borders. The builder still compiled that whole area as a classic Quake map,
  which no longer fits the format's limits. A CHIM-native Seyda Neen now skips that compile: the town's objects
  come from a source-only scene (`--seyda-scene-source`, default `auto`), and the build stops at once, naming the
  object and map, if the tutorial barrel is missing from the town frame, the Census courtyard or the docks
  ([BUILD-SEYDA-HULL2-32](../../bugs/BUILD-SEYDA-HULL2-32.md)). The compiled-town method stays selectable for A/B tests.

## Known in this build

- [BUILD-SEYDA-HULL2-32](../../bugs/BUILD-SEYDA-HULL2-32.md): the repair is checked on real data up to the opening
  objects; a complete playtest image has not yet been verified in the game.
- [BUILD-IDLE-STAGES-33](../../bugs/BUILD-IDLE-STAGES-33.md): early build stages still leave many cores idle.

See the [bug register](../../BUGS.md).
