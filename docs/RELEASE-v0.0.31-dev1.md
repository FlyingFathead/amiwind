# AmiWind v0.0.31-dev1 - Revisiting Seyda Neen

Development build. It starts v0.0.31's new approach to how Seyda Neen is split
into sub-cells, and adds firelight effects. Everything else is as in
[v0.0.30](RELEASE-v0.0.30.md).

## Seyda Neen: lighter sub-cells, shorter crossing pauses

Each Seyda Neen sub-cell used to carry geometry up to 896 units past its own
area, while the game draws only 540 units ahead. The sub-cells now carry 700
units (draw distance, the region-switching margin and a safety margin), and
the ground is simplified within 2 units of height (seams between sub-cells
stay exact).

- The 64 Seyda Neen maps shrink from 247.5 MB to 185.6 MB (-25 %).
- Maps that exceeded the modeled memory reserve: 43 -> 6 (sn018-sn021, sn026,
  sn035).
- On the FS-UAE test route, region crossings take 16-44 % less time and read
  20-38 % less data (heaviest crossing: 0.81-0.96 s -> 0.57 s).
- Views across sub-cell borders match v0.0.30 within view range.

## Fire

- Fireplaces and braziers draw flames shaped like the original emitters (size,
  rise and spread), coloured from deep red to a near-white core, with embers
  rising from the fire. Rebuilt map in this build: the Census and Excise
  Office.
- Your torch and guard torches shed embers that flash white-hot and cool to red.
- `dbg torchgallery` opens the dark torch room (same as `dbg torchtest`).

## Known in this build

- Some Seyda Neen mushrooms are listed in a sub-cell whose area no longer
  reaches them; they are beyond view there and present in the neighbouring
  sub-cell. The lists are rebuilt before v0.0.31.
- The Seyda Neen build steps used for these maps are not yet in the public
  tools ([BUILD-SEYDA-REGEN-30](BUG_JOURNAL.md)).
- Everything listed in the [v0.0.30 notes](RELEASE-v0.0.30.md) and the
  [bug register](BUGS.md).
