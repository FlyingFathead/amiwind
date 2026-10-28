# AmiWind v0.0.53-dev1 (in development)

Development snapshot, 26 October 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.52](RELEASE-v0.0.52.md).

The first snapshot of v0.0.53 (in development).

## New since v0.0.52

- **The doors of a region frame work after walking across a frame border.** The logical frame you stand in now uses its
  own door table. Before this, 830 of the 1,102 exterior entrances were dead after a walk-in
  ([DOOR-BANK-STREAMED-FRAME-51](../../bugs/DOOR-BANK-STREAMED-FRAME-51.md)).
- **A version-only build no longer rebuilds the CHIM world.** A cache hit now names only the code the stage key counts,
  so changing the version label alone keeps the finished world
  ([BUILD-STAGE-READS-UNFINGERPRINTED-48](../../bugs/BUILD-STAGE-READS-UNFINGERPRINTED-48.md)).

## Known in this build

- Some large interiors, in Vivec above all, are still loading in when you are already there
  ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).
- A script's Activate on a load door and the hinged doors have not yet been checked the same way.
- Everything else is in the [bug register](../../BUGS.md).
