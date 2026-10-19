# v0.0.45 working plan: crossings, then every interior

_Last updated with AmiWind v0.0.44-dev1 (19 October 2026)._

The step-by-step checklist behind the [roadmap's road after v0.0.44](ROADMAP.md#the-road-after-v0044-19-october-2026).
Written 19 October 2026 from the maintainer's decisions of that day. A step is ticked only with its evidence (a
commit, a gate, a build run, a measurement or a clip); a step that turns out wrong is struck through with the reason,
never deleted. Every speed change is an A/B/C run with the profiler and kept only when it wins; every builder change
comes with a test and a gate; every failure found becomes a bug page.

## 1. Cell crossings

[CHIM-CROSSING-SLUGGISH-43](bugs/CHIM-CROSSING-SLUGGISH-43.md): crossing between CHIM cells pauses the game, worst at
corners, even with 128 MB of RAM.

- [ ] 1.1 A fixed route with edge and corner crossings, scripted; crossing time per section (read, parse, link,
  recentre, surface cache) at 16 MB and at 128 MB: the A of every comparison.
- [ ] 1.2 Merge the prefetch into spare RAM (branch `v0.0.43-prefetch`, measured about 450 ms down to about 230 ms
  per crossing at 128 MB) and measure it on the route.
- [ ] 1.3 RAM past 16 MB as a frame cache: every neighbouring frame resident, frames just left kept until memory is
  needed; a heap that grows with RAM ([ENGINE-HEAP-FIXED-SIZE-43](bugs/ENGINE-HEAP-FIXED-SIZE-43.md)).
- [ ] 1.4 Loading spread over many rendered frames before the border, no blocking read at the crossing.
- [ ] 1.5 Corners: all three other frames queued, the one ahead first; hysteresis so a border is never loaded twice.
- [ ] 1.6 The switch itself, chosen by the 1.1 numbers: frames stored ready to use, the next frame prepared before the
  border, chunk-by-chunk streaming, the surface cache kept.

## 2. Bugs from the v0.0.43 playtests

- [ ] 2.1 [CHIM-ROCKS-OPEN-SHELLS-43](bugs/CHIM-ROCKS-OPEN-SHELLS-43.md): an island-wide open-edge sweep of rock meshes
  against their source, OpenMW A/B, face winding and rotation checked.
- [ ] 2.2 [CHIM-VIVEC-DOCK-WALKWAY-43](bugs/CHIM-VIVEC-DOCK-WALKWAY-43.md): the fix on its branch, verified in a few-frame
  build.
- [ ] 2.3 The other open playtest bugs: Daedric ruin pillars, the muckspunge seam, blocky roads, the Seyda Neen to
  Balmora load hang, the Ebonheart dragon pedestal.
- [ ] 2.4 Builder: [BUILD-CHIM-SERIAL-SECTIONS-44](bugs/BUILD-CHIM-SERIAL-SECTIONS-44.md) and
  [BUILD-IMAGE-STAIR-WALK-CORES-43](bugs/BUILD-IMAGE-STAIR-WALK-CORES-43.md): every pool follows the live allowance.

## 3. Every interior of the base game

Measured 19 October 2026 on the v0.0.43-dev3 build. The base game (Morrowind, Tribunal and Bloodmoon) has 1,328
interior cells: 1,134 on Vvardenfell (8 of them developer test cells), 98 on Solstheim and 96 in Mournhold. On
Vvardenfell, 176 rooms are converted and reachable (Balmora 42, Seyda Neen 14, two tombs, Vivec 118), 23 are converted
but cut off behind left-out hub rooms, 8 are left out (Vivec, over the model limits) and 919 are not converted yet,
about 420 of them caves, tombs, ruins and shipwrecks in the wilderness. Of the doors from outdoors, 746 show
"Interior unavailable" and 11 show no prompt at all.

- [ ] 3.1 Interiors on CHIM, then convert (decided for the project, 19 October 2026): rooms average about 2 MB, so about 950 more rooms would add about 2 GB to an
  image of 3.62 GB against the 4 GiB limit. Rooms store each mesh and texture once and reference them, as CHIM does
  outdoors, or get a per-room size budget, before the big batches.
  Everything already converted is reused, never made again: a mesh or texture the outdoors or another room already
  has in the store is placed by reference, by its SHA-256, and only the pieces no room or cell has yet are converted.
- [ ] 3.2 The interior progress tracker: one row per interior (name, town or region, its outdoor doors, state, size,
  last build), fed after every build like the cell tracker, shown in the Toolkit and as counts in the docs.
- [ ] 3.3 The entrance audit, island-wide: every load door checked against the build; a door to a room left out on
  purpose names the reason.
- [ ] 3.4 The room list made from the game's door graph instead of hand lists (today: Balmora, Seyda Neen, Vivec).
- [ ] 3.5 The 11 doors with no prompt (near Seyda Neen, three Pelagiad houses, Wolverine Hall): cause found and fixed.
- [ ] 3.6 Vivec's left-out rooms through the [over-limit procedure](INTERIOR_SECTIONS.md): the four Waistworks and Plaza
  hubs and the Prison Keep first (28 rooms reachable again), then the rest.
- [ ] 3.7 Conversion batches, towns first (Ald-ruhn 56, Sadrith Mora 31, Caldera 20, Gnisis 20, ...), then the
  wilderness; each batch measured for build time, image size and memory.
- [ ] 3.8 Solstheim and Mournhold, planned once Vvardenfell's rooms are in.

## 4. After the interiors

The [roadmap](ROADMAP.md#the-road-after-v0044-19-october-2026) order: object and container state, NPC placement,
then MWScript compiled by the builder. Each gets its own checklist when it starts.
