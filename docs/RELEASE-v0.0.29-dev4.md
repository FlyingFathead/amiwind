# v0.0.29-dev4 — WIP: More Mushrooms! (...and fixes)

**Development preview only.** v0.0.28 remains the latest stable release. This
dev4 source snapshot is a development prerelease, not a release candidate
or the final v0.0.29 release. The More Mushrooms milestone remains planned until worldwide original placement and
picking, including interior coverage, and relevant release gates are complete.

## What's in this development snapshot

- The clean dev3 world and restored Indrele Rathryon shack are the baseline.
  Town BSP geometry is retained; rejected mushroom brush overlays are excluded.
- Six original mushroom placements retain their identity across overlapping maps.
  Town catalogues use shared models; nine world maps retain embedded brush
  geometry for the same pilot placements.
  Picking uses E and the existing item notification/sound path. Picked and empty
  states suppress targeting/rendering as implemented; only the bounded pickup
  result described below is natively accepted.
- Default-off walking-pitch centering, framed character-confirmation/travel
  actions and modal world-work controls are in the source candidate. Modal UI
  and soundtrack remain active while world work is frozen; broader native appearance
  and lifecycle acceptance remain incomplete.
- The conversion batch includes 6,447 voices, 717 effects, 18 music tracks and 17
  videos. Nine referenced original audio files were unavailable (seven voices,
  two effects). No available source-media conversion failed. The development image retains
  its higher-resolution intro, so 16 of 17 videos use the new batch output. Correct event
  mapping/listening and three source videos without embedded audio remain open.

For the complete changes-since-v0.0.28 hotlist, see the [README](../README.md).

## Verification

The frozen source suite ran **953 tests: 949 passed, 4 skipped, 0 failures and
0 errors**. The 68040 engine and boot checker compiled. Four bounded native
acceptance groups ran against the exact development archive. One Luminous
Russula was picked once, disappeared, resisted repeat pickup, and remained
picked across the tested return/save sequence; saved inventory readback retained
quantity 1. This is one tested pickup among six packaged placements, not
complete interaction or world coverage. The guest exited cleanly.

The package preflight examined **2,723 maps** and found zero hard allocation
ceiling failures, with **59 modeled reserve warnings**. `intro_docks` has only
1,972 bytes of modeled margin. This is an open memory risk, not a production
memory gate. The native run did not exercise empty outcomes, walked boundaries,
mixed world/town return, intro_docks memory, audio listening or Windows batch
launch.

## Known limitations and work in progress

- Mushroom scope is six original placements. Worldwide placement, dense-map
  admission and complete exterior/interior integration are not included.
- Quickload currently puts hands and torch away, although mushroom inventory
  and picked state survived the tested load. A save-format correction is not in
  this image.
- Torch/guard brightness and intermittent visibility, hand geometry/race
  coverage, distant horizon gaps/popping, and terrain
  collision/shoreline reports remain under investigation.
- Cell transitions remain a performance issue. Callback timing is not a proven
  first-world-frame time, and this build makes no overall speedup claim.
- Broader audio, orientation, UI/input, world traversal and save-state coverage
  remains incomplete. Generated Windows bindings were checked, but Windows
  batch execution was not.

## Next release milestone

The planned **AmiWind v0.0.29 — More Mushrooms** release requires compact,
identity-preserving original placements and picking across exterior and
interior maps, with relevant save, memory, appearance and native traversal gates
passed. Final release screenshots must come from that completed candidate.
This dev4 preview adds no screenshots; historic images retain their original
version labels.