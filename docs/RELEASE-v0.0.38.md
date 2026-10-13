# AmiWind v0.0.38 - Lava Is All You Need (And A Hint Of Tel Uvirith)

Release preparation for the complete current game, with normal
startup, supported interiors, NPC assets and the updated AmiWind Toolkit.
The full image passed build, performance and HDF readback checks. Native smoke
checks verified completed-stage Tel Uvirith arrival and lava contact damage;
sealed-package validation and delivery remain pending.

## Changes under validation

- Lava coverage and terrain repair: restore missing exterior lava conversion,
  preserve original lava elevation and retain LAND detail around pool footprints.
  [BUILD-LAVA-COVERAGE-38](bugs/BUILD-LAVA-COVERAGE-38.md) records
  208 exposed-pool and 467 buried-pool checks, plus native contact damage.
  The final image shows lava contact damage with god mode and noclip off;
  matched-reference and sound checks remain pending.
- CHIM conversion of exterior cells exceeding BSP storage limits.
- Original nonsolid mesh collision markers are preserved, including fire ferns.
  Empty point hulls receive an explicit empty node instead of being interpreted
  as solid. Scoped collision checks pass; remaining cell holds stay open.
- Quick-character startup audio scratch is included in CHIM memory accounting,
  and debug recovery reuses checked arrival placement.
- Third-person and vanity camera availability respects introductory permissions.
- LAND fill has a separate saved control, independent of fog.
- Noclip walking bob and movement roll default off, with saved
  `dbg noclipwobble` / `dbg noclipbob` controls. Photo mode temporarily disables
  this bob and restores the prior setting. Source regression checks pass;
  target-native validation of this addition remains pending.
- Toolkit map names toggle, resizable map view and per-panel inspection copy.
- Optional MiniWind map inspection startup for development builds. Regular
  gameplay defaults are unchanged; MiniWind remains unavailable in RC builds.
- Opt-in terrain-aware render clipping, with shared-placement and collision
  safeguards. Full-world enablement is not established by isolated tests.

## Known in this build

- [BUILD-LAVA-TERRAIN-BUDGET-38](bugs/BUILD-LAVA-TERRAIN-BUDGET-38.md): the full image contains all 349 original lava references across 27 CHIM cells. Scoped native shoreline and contact checks passed; wider traversal and sound remain open.
- [CHIM-MOLAG-MEMORY-38](bugs/CHIM-MOLAG-MEMORY-38.md): completed-stage Tel Uvirith is integrated in the full-world conversion. Its active-ring estimate is 5,596,320 bytes and load-ring estimate is 5,767,824 bytes against a 6,242,304-byte budget. Final HDF sprite readback and native arrival passed; normal staircase traversal remains open.
- [BUILD-SCRATCH-DISK-GROWTH-32](bugs/BUILD-SCRATCH-DISK-GROWTH-32.md): image assembly completed after the storage guard was resolved. Final delivery remains pending.
- [STAIRS-MOLAG-ACCESS-38](bugs/STAIRS-MOLAG-ACCESS-38.md): owner-reported walkway and door stair obstructions need normal-walking comparison and repair.
- [CHIM-TERRAIN-ROCK-EXEMPT-38](bugs/CHIM-TERRAIN-ROCK-EXEMPT-38.md): native terrain-contact and matched original comparison remain pending.
- [CHIM-COAST-OBJECTS-MISSING-36](bugs/CHIM-COAST-OBJECTS-MISSING-36.md): source-reference and packaged coverage remain incomplete.
- [CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](bugs/CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md): converted geometry does not imply implemented actors or gameplay.
- [CHIM-FERN-NCO-SOLID-38](bugs/CHIM-FERN-NCO-SOLID-38.md): scoped fern checks do not close every collision hold.
- [ENGINE-SYNC-IO-MAIN-LOOP-36](bugs/ENGINE-SYNC-IO-MAIN-LOOP-36.md): streaming and measured performance work remain open.

Complete refers to the full-game package scope, not complete CHIM coverage or
the absence of known issues. No full-traversal acceptance is claimed.

## Release completion checklist

- [x] Verify scoped lava shoreline and contact damage in the final image.
- [ ] Complete final-image lava sound and wider traversal checks.
- [x] Integrate optimized completed-stage Tel Uvirith into the full-world conversion.
- [x] Verify Tel Uvirith sprites, modeled memory use and arrival in the finished image.
- [x] Read back all 360 regional CHIM cells from the final image.
- [x] Separate six partially overlapping town cells from the 360 whole regional cells.
- [ ] Check native boundary routing for those six overlaps.
- [ ] Verify superseded unused exterior BSP maps are absent.
- [ ] Pass final-source gates and exact-package native smoke tests.
- [x] Capture HUD/crosshair-off lava views and finish release illustrations.
- [ ] Validate the Linux release kit and matching public source ZIP.
- [ ] Verify package delivery and provide the release kit and WinUAE runner.

Other owner-reported bugs remain in the roadmap and canonical fix index; this
release checklist does not mark them fixed or defer its own unfinished gates.
