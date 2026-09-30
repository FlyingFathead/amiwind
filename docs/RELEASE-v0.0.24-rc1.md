# AmiWind v0.0.24-rc1 — Welcome to Balmora candidate

This is the playable release candidate for owner testing. Stable v0.0.23 and
the published v0.0.24-dev5 prerelease remain unchanged. Final v0.0.24, titled
**Welcome to Balmora**, will follow only after the owner's green light.

| Balmora exterior | Guild of Mages interior |
| --- | --- |
| ![Balmora in the native RC1 runtime](images/amiwind-v0.0.24-rc1-balmora.png) | ![Balmora Mages Guild in the native RC1 runtime](images/amiwind-v0.0.24-rc1-mages.png) |

## What is included

- 43 original destination interiors: 42 Balmora rooms/buildings and Tharys
  Ancestral Tomb. All 3,408 selected geometry references are retained exactly
  once, including distant-origin towers and the previously dropped dressing.
- 93 interior NPC placements: 90 living residents and three authored corpses;
  83 distinct models and 80 living voice sets. Authored greeting audio and
  text use the bounded dialogue fixture. Full services, schedules, combat and
  quests are still outside this implementation.
- All 70 source exterior entrance links, plus their returns and two additional
  same-room Fighters Guild links. Source labels and placed reference IDs are
  retained. Labels include the owner's latest Razor Hole report.
- Corrected exact collision bevels/architectural openings and the shared ramp
  threshold (0.69 instead of 0.7). Native walking covers the reported stairs,
  bridge and arch approaches, except the unresolved positive-Y report below.
- Guarded ground-material repairs match inspected adjoining pavement; the
  western rock/scrub patch uses its actual neighbouring material. Duplicate
  camera reports remain individually documented.
- Clearer gold lowercase e and uppercase H. `dbg ui ink original` retains the
  former appearance; `dbg ui ink readable` restores the candidate default.
- Name, Talk hint and manual NPC greeting share one direct target. Native
  Caius/Galbedir greeting and Selvil travel checks pass. The intro guard's
  final post is left of the Census door, facing the docks.
- Short Amiga door-bank names, a complete payload name preflight, and a
  generated original-to-target naming ledger. New Balmora debug teleports
  select the right entrance bank. Quickload inserts its scene load ahead of
  later queued console commands, preventing a later teleport from overtaking
  a pending restore.

The accepted Balmora Strider, 90-degree FOV, base player dimensions, race/sex
view heights, Shift+V and frozen-frame Loading... presentation are preserved.
Balmora keeps 64 overlapping regions; Seyda Neen keeps 25 regular regions and
separate intro-pier/courtyard scenes. Map replacement remains synchronous.

## Verification and limits

The source suite ran 297 tests: 296 passed in the normal run; its optional
external-qbsp test was then run separately with the required compiler and
passed. Native production compilation retains the same 82 warning categories
and occurrences as dev5, with no added warnings. Existing warnings remain debt.

Native checks loaded all 43 interiors, exercised all 70 exterior entrance/return
pairs and both same-room links, and traversed the reported routes in ordinary
walking after diagnostic placement. Whole-room loading recorded 899 frames
with zero surface/edge overflow frames. The focused final stair run recorded
1,128 frames with no overflow. Placement does not certify the route from every
possible city approach. The whole natural intro and general city roaming still
need owner playtesting.

Packaged HDF validation is recorded in the private build receipt: all 980
payload files are independently read back and hashed; the production executable
is checked against the packaged source build. The final image test restores
Hors from a quicksave before travelling to Hlaalu Council Manor, loads the
shortened door bank, and exits cleanly: 434 frames, zero surface/edge overflow
frames. Native image testing uses a writable copy, keeping the deliverable
baseline unchanged.

Reference emulator: A1200/AGA/PAL, 68040/FPU/JIT, 2 MiB Chip and 16 MiB Z3,
11 MiB runtime heap. These are Linux FS-UAE results, not physical Amiga or
Windows/WSL validation. Null-audio runs verify selected samples and triggers,
not subjective voice/sound quality. The 768 MiB FFS partition is storage size,
not RAM residency.

## Known RC1 issues

- **stairs10: -685,+619,141, yaw130/pitch-29.** The positive-Y coordinate lies
  inside terrain in this conversion. Keep it unresolved; do not silently
  replace it with the earlier -687,-620 report, which passes walking checks.
- **wedge1: -225,348,131, yaw13/pitch78.** The exact reported trapped state
  needs reproduction by walking into it. Native setup requires lateral
  recovery; retreat works nearby, but that is not proof that the wedge is fixed.
- Every NPC's appearance/audio and every room's complete free-roaming collision
  have not been individually accepted by the owner. Converted presence and
  bounded greetings do not imply finished Morrowind gameplay systems.

Start a new character: changed content invalidates prior-build saves.
`dbg aw hors 0` creates Hors (male Nord, Barbarian, The Steed) after Census;
`dbg tp balmora` brings that character to Balmora and supplies it if absent.
`dbg tp` opens the destination picker. New room IDs are in
[the interior configuration](../config/balmora_interiors.json).

The [full coordinate checklist](INVESTIGATION-v0.0.24-rc1.md),
[Balmora conversion lessons](BALMORA_CONVERSION_LESSONS.md),
[interior-coordinate guide](INTERIOR_COORDINATE_CULLING.md),
[stair recurrence guide](STAIR_RAMP_WALKABILITY.md) and
[Amiga limitations](RELEASE_WORKFLOW.md#amiga-limitations) preserve the bug,
inspected cause, implications, fix and remaining acceptance boundary.
