# AmiWind v0.0.21-dev2 — opening barrier correction

Follow-up to [v0.0.21-dev1](RELEASE-v0.0.21-dev1.md); all its implementation
limits still apply. Owner confirmation of this correction is pending.

## Change

The invisible opening walls used the wrong compound rotation order. This put
collision across the plank. Correct the converter to preserve the original
reference orientation; retain all 22 collision-only boxes, positions, dimensions
and their CharGenState lifetime. Do not release the enclosure on hatch exit or
race confirmation. No source models or textures are changed.

The implementation journal now has an index and a symptom/cause/change/evidence
record (J015). CHARACTER_CREATION.md records the persistent access conditions.
REFERENCES.md and ROADMAP.md retain UESP research, fundamental-mechanics priority
and future lower-screen status/control planning. Attribute effects are deferred.

## Validation

- Native 68040 build: 93 warnings; no new or removed diagnostic messages versus
  dev1. The unresolved warning baseline remains follow-up work.
- Host suite: 210 tests passed. The new compound-rotation converter test fails
  against the dev1 converter and passes against this version. Runtime checks
  retain barriers through dock/race/office/courtyard/captain states and remove
  them only on the global release condition.
- Actual privately converted references and standing player hull: the old data
  blocks two segments along the plank; corrected data passes the same route.
- Clean HDF: all 477 payload files read back and matched their expected hashes.
- FS-UAE 3.1.66: debug placement at the exterior hatch arrival, then ordinary
  walking down the deck and plank, sideways pushes against both plank bounds,
  and approach to the dock guard triggered original speech and appearance
  selection. Noclip was off throughout the walking/containment checks.
- Separate demo-map geometry check: both central pier rails stopped sustained
  sideways input, and ordinary walking continued toward the office. Host hull
  inspection found side collision bands on all five dock pieces. This separate
  check does not validate the story escort or every courtyard escape route.

This is focused local verification, not a completed natural New Game-to-release
playthrough or owner acceptance. Retain the wider opening acceptance checklist,
all escape-route checks and both unrelated intermittent freeze reports.
