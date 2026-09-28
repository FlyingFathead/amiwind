# AmiWind v0.0.21-dev4 — evening world-mapping checkpoint

This release packages Horstator's 28 September 2026 evening design notes with a
native rebuild carrying the dev4 version identity. Gameplay code and converted
scene content are unchanged from dev3; no new performance gain is claimed.

- [Horstator's journal](HORSTATORS_JOURNAL_2026-09-28.md): optional polygonal POI
  regions as a must-try fallback only if fog-assisted exterior streaming, with
  brief pauses where needed, cannot meet target budgets.
- [World mapping](WORLD_MAPPING_PLAN.md): retain the original cell approach,
  source-cell semantics, stable references and persistent state across overlapping
  runtime regions. Seyda Neen is the proposed first experiment.
  Clarify the format terminology: compiled BSP regions and associated resource
  packs; the earlier WAD shorthand is not AmiWind's map format.
- [Roadmap](ROADMAP.md): compare both strategies using memory, transition peaks,
  loading time, frame time, audio and seam checks; try bounded region swaps with
  inexpensive backdrops and a minimal upper-center Loading box for outdoor cell
  crossings. Preserve original-style loading screens at interior/exterior
  transitions that already use them.
- Record the open-world/topomap risk at elevated viewpoints and a proposed
  height-above-ground switch to broader terrain coverage. This remains an
  untested mitigation, not a new runtime mode.
- Preserve "the fog is our friend" as both a resource-budget principle and an
  atmospheric goal, retaining Morrowind's mystery at limited view distances.
- Prioritize an entire-world terrain topomesh and a separate observer scene for
  water-level, fog and LOD studies. This is a recorded next milestone, not a
  generated mesh or playable mode in dev4.
- Add "Tables, tables, we need more tables": a cross-system parameter/state
  catalogue requirement covering characters, effects, quests, NPCs, containers
  and persistence, with verified sources and explicit dependencies.

Polygonal region loading and the previously recorded default-on doorway
simplification remain design work. The latter may simplify only concealed wall
patches beneath the door/frame, preserving visible texture and actual openings.

## Included maintenance and remaining issues

All [dev3 maintenance](RELEASE-v0.0.21-dev3.md) remains included: Census room
restoration, dock interception, readable papers, interaction hints, WASD menu
choices, fighting-permission correction and courtyard ring depletion.
The complete natural opening, pier containment, intermittent freezes, separate
Census clipping report and exterior door/wall overlap remain open in BUGS.md.

## Validation

- 215 host tests pass.
- Native 68040/FPU build succeeds. All 87 compiler warnings match dev3's
  diagnostic set; none added or suppressed. Existing warnings remain follow-up
  work, including format/bounds and initialization diagnostics.
- All 477 HDF payload files pass independent readback. Only the rebuilt engine
  and preflight executable differ from dev3; scene data and save fingerprint match.
- FS-UAE 3.1.66 boots the normal main menu with the dev4 version displayed.
  Gameplay acceptance from dev3 is historical evidence, not a new full replay.

## Saves and package base

The dev3 scene-content fingerprint and save schema are retained. Dev3 saves are
expected to remain compatible; this does not claim a new native save/load test.
Older content saves rejected by dev3 remain incompatible. Preserve prior HDFs.
The incremental public source archive applies to the exact delivered dev3
public-source package. No earlier archive is overwritten.
