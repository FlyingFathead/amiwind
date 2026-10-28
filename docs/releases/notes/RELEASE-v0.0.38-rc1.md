# AmiWind v0.0.38-rc1 - Lava Is All You Need (And A Hint Of Tel Uvirith)

Release candidate preparation for the complete current game, with normal
startup, supported interiors, NPC assets and the updated AmiWind Toolkit.
This source snapshot is not a verified playable package yet.

## Changes under validation

- Integrated lava and CHIM conversion work from the development branch.
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

- [BUILD-LAVA-TERRAIN-BUDGET-38](../../bugs/BUILD-LAVA-TERRAIN-BUDGET-38.md): the previous full build failed a region storage gate; a corrected full build is required.
- [CHIM-MOLAG-MEMORY-38](../../bugs/CHIM-MOLAG-MEMORY-38.md): optimized Tel Uvirith remains a diagnostic candidate pending full-world integration and runtime validation.
- [STAIRS-MOLAG-ACCESS-38](../../bugs/STAIRS-MOLAG-ACCESS-38.md): owner-reported walkway and door stair obstructions need normal-walking comparison and repair.
- [CHIM-TERRAIN-ROCK-EXEMPT-38](../../bugs/CHIM-TERRAIN-ROCK-EXEMPT-38.md): native terrain-contact and matched original comparison remain pending.
- [CHIM-COAST-OBJECTS-MISSING-36](../../bugs/CHIM-COAST-OBJECTS-MISSING-36.md): source-reference and packaged coverage remain incomplete.
- [CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](../../bugs/CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md): converted geometry does not imply implemented actors or gameplay.
- [CHIM-FERN-NCO-SOLID-38](../../bugs/CHIM-FERN-NCO-SOLID-38.md): scoped fern checks do not close every collision hold.
- [ENGINE-SYNC-IO-MAIN-LOOP-36](../../bugs/ENGINE-SYNC-IO-MAIN-LOOP-36.md): streaming and measured performance work remain open.

Complete refers to the full-game package scope, not complete CHIM coverage or
the absence of known issues. No full-traversal acceptance is claimed.
