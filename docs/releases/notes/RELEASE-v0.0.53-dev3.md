# AmiWind v0.0.53-dev3 (in development)

Development snapshot, 26 October 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.53-dev2](RELEASE-v0.0.53-dev2.md). Previous release: [v0.0.52](RELEASE-v0.0.52.md).

The third snapshot of v0.0.53 (in development); the release [v0.0.53](RELEASE-v0.0.53.md) is this build with only its
version changed.

## New since v0.0.53-dev2

- **The door check in every build**, the engine's own door code over all 1,102 exterior entrances, and
  `dbg door roulette [SEED]` ([DOOR-ENTRANCE-AUDIT-51](../../BUGS.md)).
- **The doorway slack**: the use ray may meet an entrance's own doorway collision up to 16 units before the door; 1,067
  entrances usable with the wall traced, 31 more than before ([DOOR-USE-BLOCKED-53](../../BUGS.md)). The 35 left move to
  v0.0.54 ([DOOR-USE-COLLISION-FILLED-53](../../BUGS.md)).
- **The Suran dancers dance their own dance**, from the shared humanoid table
  ([DANCER-OWN-ANIM-IGNORED-53](../../BUGS.md)).
- **The Halloween scene**, `aw bench halloween` (aliases `aw halloweenbench`, `dbg halloween bench`) and the custom OST
  slot ([HALLOWEEN.md](../../HALLOWEEN.md), [HALLOWEEN-SCENE-53](../../BUGS.md), [CUSTOM-OST-SLOT-53](../../BUGS.md)).
- **The disk check** ([BUILD-DISK-NEED-UNKNOWN-52](../../BUGS.md)) and **maintainer deferrals that expire**
  ([REGISTER-DEFERRAL-EXPIRES-53](../../BUGS.md)).

## Known in this build

- The same as the release's: see [Known in this build](RELEASE-v0.0.53.md#known-in-this-build).
- Everything else is in the [bug register](../../BUGS.md).
