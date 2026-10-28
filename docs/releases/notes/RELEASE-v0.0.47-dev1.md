# AmiWind v0.0.47-dev1: Development Snapshot (in development)

Development snapshot, 21 October 2026, in development. Running on CHIM Engine v0.2.1. Previous release:
[v0.0.46](RELEASE-v0.0.46.md).

The fixes and builder work since v0.0.46, gathered for a test build. Most of the new work (the smaller world
formats, the outdoor actors, the type 1 crossing) is in the source behind switches that are off in this build; see
[EXPERIMENTAL_FLAGS](../../EXPERIMENTAL_FLAGS.md).

## What changed since v0.0.46

- **The Ghostfence shimmers.** Shapes whose texture scrolls in the original (the Ghostfence curtain, the Vivec
  waterfalls, the ash mire) ripple as Quake turbulent textures by default. `dbg ghostfence off` draws them still
  ([GHOSTFENCE-NO-ANIMATION-46](../../bugs/GHOSTFENCE-NO-ANIMATION-46.md)).
- **A lighter image.** The 64 MB media catalogue, a build report nothing in the game reads, is no longer on the
  boot disk ([IMAGE-MEDIA-CATALOGUE-ON-DISK-46](../../bugs/IMAGE-MEDIA-CATALOGUE-ON-DISK-46.md)).
- **Pursuers keep up on slopes.** An actor's step now follows a walkable slope; ledges are still refused
  ([COMBAT-PURSUIT-SLOPE-STALL-46](../../bugs/COMBAT-PURSUIT-SLOPE-STALL-46.md)).
- **Spawned actors stand on the ground.** An actor spawned before the streamed ground was there no longer floats
  ([COMBAT-CHASE-CHIM-STUCK-46](../../bugs/COMBAT-CHASE-CHIM-STUCK-46.md)).
- **Weather changes gradually** between regions, as in OpenMW
  ([SKY-REDMOUNTAIN-BLUE-44](../../bugs/SKY-REDMOUNTAIN-BLUE-44.md)).
- **Faster flat planes.** Floors and walls that face straight along an axis take Quake's fast paths again
  ([CHIM-PLANE-TYPE-ALL-SLANTED-46](../../bugs/CHIM-PLANE-TYPE-ALL-SLANTED-46.md)).
- **Workbench icon.** The boot volume has an icon labelled with the version; a double-click starts the game.
- **Builder.** No stair walk by default; rebuilds reuse more (code keys of the functions a unit runs, and a unit
  whose output is unchanged does not rebuild what depends on it).
- **Emulator presets** start with 128 MB of Fast RAM.

## Known in this build

- [CHIM-EXTERIOR-ACTORS-MISSING-46](../../bugs/CHIM-EXTERIOR-ACTORS-MISSING-46.md): the open world outside the towns has
  almost no NPCs or creatures; the actor table and its models are in the source, off in this build.
- [CHIM-CROSSING-SLUGGISH-43](../../bugs/CHIM-CROSSING-SLUGGISH-43.md): crossings with 16 MB still pause; the streamed
  crossing (type 1) is in the source, off in this build.

The rest is as in the [v0.0.46 notes](RELEASE-v0.0.46.md#known-in-this-build); everything else is in the
[bug register](../../BUGS.md).
