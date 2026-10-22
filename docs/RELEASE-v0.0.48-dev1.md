# AmiWind v0.0.48-dev1: interiors plan and register updates (in development)

Development snapshot, 22 October 2026, in development. Running on CHIM Engine v0.2.1. Previous release:
[v0.0.47](RELEASE-v0.0.47.md).

A small snapshot right after v0.0.47: no game or builder change, only the plan for the next step and the bug
register. It is the base the v0.0.48 work starts from.

## New since v0.0.47

- **Interiors: the plan of record.** A room is two kinds of content. The shell (walls, floors, stairs, fixed
  furniture) stays baked into the map. Everything that can be taken, moved or opened (items on tables and shelves,
  books, bottles, weapons on racks, containers and their contents, ingredients) becomes its own object with its own
  state, kept in the save. The first step is a measurement of how many such objects each room holds
  ([INTERIOR-PLACED-ITEMS-47](bugs/INTERIOR-PLACED-ITEMS-47.md); [ROADMAP](ROADMAP.md)).
- **Bug register.** A slow step of the image build, the CHIM world frame read, is registered
  ([BUILD-IMAGE-WORLD-READ-FRAMES-47](bugs/BUILD-IMAGE-WORLD-READ-FRAMES-47.md)).
- **Release records.** The previous-release record and the size baseline now describe v0.0.47; its payload is
  2.36 GiB, down from 2.60 GiB in v0.0.46.

## Known in this build

- Everything in [v0.0.47's known items](RELEASE-v0.0.47.md#known-in-this-build) still applies; there is no new image
  for this snapshot.
- Placed items in interiors are not yet live objects
  ([INTERIOR-PLACED-ITEMS-47](bugs/INTERIOR-PLACED-ITEMS-47.md)).
- Everything else is in the [bug register](BUGS.md).
