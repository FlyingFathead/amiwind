# AmiWind v0.0.46-dev1: Red Mountain Getting Red, Fixes, Optimizations (in development)

Development snapshot, 20 October 2026, in development. Running on CHIM Engine v0.2.1. Previous release:
[v0.0.45](RELEASE-v0.0.45.md).

The fixes and builder work since v0.0.45, gathered for a test build before the release.

## What changed since v0.0.45

- **Red Mountain is red.** Every region drew the clear sky, because nothing ever chose a weather. Each region now
  picks its weather from its own chances, as the original game does, and draws that weather's sky, horizon and
  fog colours; Red Mountain gets its blight sky ([SKY-REDMOUNTAIN-BLUE-44](bugs/SKY-REDMOUNTAIN-BLUE-44.md)).
  Weather clouds, rain and ash, storm sounds and storm light are not in yet.
- **The Ebonheart dragon statue stands on its plinth.** The converter kept an offset that the game throws away, so
  the statue floated over the plaza. The rule now matches the game for every model: 25 models move, among them the
  Daedric ruins and the anvils ([MESH-EBONHEART-DRAGON-PEDESTAL-42](bugs/MESH-EBONHEART-DRAGON-PEDESTAL-42.md)).
- **The torch shows in third person and in the inventory picture.** The held torch was dropped from memory and never
  loaded again ([PLAYER-TORCH-THIRDPERSON-38](bugs/PLAYER-TORCH-THIRDPERSON-38.md)).
- **Walkways no longer split in the distance (test switch).** Two new far-detail switches, both off for this test:
  no cut before the fog is opaque, and the pieces of one structure cut together
  ([CHIM-BRIDGE-POP-PIECES-44](bugs/CHIM-BRIDGE-POP-PIECES-44.md)).
- **Vivec dock walkways.** The player no longer sinks into the planks
  ([CHIM-VIVEC-DOCK-WALKWAY-43](bugs/CHIM-VIVEC-DOCK-WALKWAY-43.md)).
- **The Dreamers greet you.** A talk opens with the NPC's conversation greeting
  ([NPC-DREAMER-GREETING-DEFAULT-42](bugs/NPC-DREAMER-GREETING-DEFAULT-42.md)).
- **Builder.** Rebuilds reuse more: stair walks are keyed by the data they walk, the reuse check refuses rebuilds
  explained only by scheduling, the version or docs, and its standalone form now says the same as the build
  ([BUILD-REUSE-SCHEDULER-TOP-45](bugs/BUILD-REUSE-SCHEDULER-TOP-45.md),
  [BUILD-REUSE-PLAN-ENV-36](bugs/BUILD-REUSE-PLAN-ENV-36.md)). A stand-in sky, font or video now stops the build.
- **Cell crossings measured.** With 128 MB a crossing takes about a third of the v0.0.44 time; with 16 MB it is only
  slightly faster ([CROSSING_BASELINE](performance/CROSSING_BASELINE.md)).

## Known in this build

- [CHIM-CROSSING-SLUGGISH-43](bugs/CHIM-CROSSING-SLUGGISH-43.md): crossings with 16 MB still pause; the streamed
  crossing is in development.

The rest is as in the [v0.0.45 notes](RELEASE-v0.0.45.md#known-in-this-build); everything else is in the
[bug register](BUGS.md).
