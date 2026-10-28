# AmiWind v0.0.44-dev1: Bitter Coast trees fit again (in development)

Development snapshot, 19 October 2026, in development. Running on CHIM Engine v0.2.1. Previous release:
[v0.0.43](RELEASE-v0.0.43.md).

Every exterior cell of Vvardenfell on CHIM, as in v0.0.43, with the fixes found while building its image.

## What changed since v0.0.43

- **Bitter Coast trees are lighter again.** The trunk shape guard that keeps Azura's Coast tree crowns on their
  trunks made the Bitter Coast trees about 60 % larger, and two Bitter Coast areas no longer fit in memory. The
  guard now tries a lighter copy first: these trees are 16 to 42 % smaller, and every trunk keeps at least 90 % of
  its height ([CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43](../../bugs/CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43.md)).

## Known in this build

- [CHIM-VIVEC-DOCK-WALKWAY-43](../../bugs/CHIM-VIVEC-DOCK-WALKWAY-43.md): the player still sinks into the Vivec dock
  walkways; the fix waits for a test build.

The rest is as in the [v0.0.43 notes](RELEASE-v0.0.43.md#known-in-this-build); everything else is in the
[bug register](../../BUGS.md).
