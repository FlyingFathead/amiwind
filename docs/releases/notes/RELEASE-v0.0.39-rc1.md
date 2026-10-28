# AmiWind v0.0.39-rc1 - Cell By Cell, Piece By Piece

Running on CHIM Engine v0.2.0. This candidate gathers the changes made after
published v0.0.38, including the earlier dev1 source work. The published base is
`d40fa70b4787da09b8a6d5006f46ef6fb7e56c6f`.

The changes below are implemented in this source candidate. Exact-source tests,
the complete image and target gameplay checks are pending at preparation time.
The findings section records diagnosed gaps; those are not implemented fixes.
Current issue status remains in the [bug register](../../BUGS.md#fix-index).

The [maintained changelog](../../CHANGELOG.md) records the version history. Changelog,
bug records and CHIM conversion/audit/native/package coverage must be updated
together under the [mandatory workflow](../../RELEASE_WORKFLOW.md#mandatory-change-records).
[DOCS-CHANGELOG-STALE-39](../../bugs/DOCS-CHANGELOG-STALE-39.md).

## Build and handoff corrections

- Correct the actor-layout preflight ceiling for expanded player bodies: up to 256 total frames within the existing byte budget, at most 64 per group. [ANIMKIT-ACTOR-ABI-SITES-35](../../bugs/ANIMKIT-ACTOR-ABI-SITES-35.md).

- The exterior checklist accepts coordinates read back from JSON while still
  rejecting changed ownership. CHIM-owned exterior BSPs remain excluded before
  compilation. [BUILD-CHECKLIST-JSON-CELLS-39](../../bugs/BUILD-CHECKLIST-JSON-CELLS-39.md).
- The publication baseline declares its RC1 target version. A dry-run kit is
  not a publication-ready kit; strict validation remains required.
  [RELEASE-PATCH-TARGET-VERSION-39](../../bugs/RELEASE-PATCH-TARGET-VERSION-39.md).

## Save recovery and death screen

- Teleport autosaving now waits for a settled, grounded arrival. Loading,
  falling, damaging contents, combat and modal menus defer automatic saving.
  The previous safe checkpoint remains available while the new save waits.
  [SAVE-TELEPORT-CHECKPOINT-38](../../bugs/SAVE-TELEPORT-CHECKPOINT-38.md).
- Lava and slime are rejected as automatic-save locations, preventing the
  newly generated unsafe checkpoint that could reload into another death.
  Existing unsafe save files are not modified or repaired automatically.
  [SAVE-LAVA-DEATH-LOOP-38](../../bugs/SAVE-LAVA-DEATH-LOOP-38.md).
- The death-choice menu requests an untinted palette over the existing frozen
  world background. Damage and lava tint should no longer colour its choices.
  [UI-DEATH-DAMAGE-TINT-38](../../bugs/UI-DEATH-DAMAGE-TINT-38.md).
- Regression fixtures cover save eligibility, deferred arrival saving, modal
  world behavior and palette selection. A real character's death-choice menu
  and save/reload sequence remain required native checks.

## Third-person body and animation

- Player body baking now includes jump takeoff, airborne and landing groups;
  runtime selection connects those groups to the player's movement state.
  [PLAYER-JUMP-THIRDPERSON-38](../../bugs/PLAYER-JUMP-THIRDPERSON-38.md).
- Bare-handed ready poses and ready walk/run groups are added to the player
  body profiles, with runtime selection while the hands are readied.
  [PLAYER-READY-THIRDPERSON-38](../../bugs/PLAYER-READY-THIRDPERSON-38.md).
- Draw and lower animations use an offline upper-body layer combined with
  movement poses. The runtime uses authoritative action time and a separate
  leg phase, so changing camera or moving should not restart the action.
  [PLAYER-READY-THIRDPERSON-38](../../bugs/PLAYER-READY-THIRDPERSON-38.md).
- The shared offline bone-layer sampler preserves lower-body motion and
  female movement overrides. The guard torch preparer reuses the extracted
  sampler; identical guard assets are an explicit regression check.
  [PLAYER-READY-THIRDPERSON-38](../../bugs/PLAYER-READY-THIRDPERSON-38.md).
- Body generation retries within the existing mesh and animation budgets
  when extra animation frames overflow. It does not raise the runtime model
  staging limit, silently omit an appearance or substitute an old body.
  [BUILD-PLAYER-BODY-BUDGET-FALLBACK-39](../../bugs/BUILD-PLAYER-BODY-BUDGET-FALLBACK-39.md).
- Prepared tests cover group selection, timing, transition grids, motion
  layers and budget fallback. All ten races, both sexes, passed actual
  model/layout readback. Native inspection remains scoped to Nord male;
  universal motion coverage is not established.
- Carried player torches, complete punch/weapon coverage and swimming poses
  remain separate unfinished work.
  [PLAYER-TORCH-THIRDPERSON-38](../../bugs/PLAYER-TORCH-THIRDPERSON-38.md), [PLAYER-READY-THIRDPERSON-38](../../bugs/PLAYER-READY-THIRDPERSON-38.md), [WATER-GAMEPLAY-PARITY-38](../../bugs/WATER-GAMEPLAY-PARITY-38.md).

## Sound cancellation

- Stopping an entity sound now scans the same eight dynamic slots used by
  the sound allocator. The previous loop missed its last four slots.
  [AUDIO-STOP-CHANNEL-RANGE-39](../../bugs/AUDIO-STOP-CHANNEL-RANGE-39.md).
- Entity/channel matching remains selective; other entities, ambient/static
  channels and music remain controls in the expanded real-mixer regression.
- This repairs cancellation itself. Suppressing ambient greetings throughout
  combat is a separate policy change and is not implemented by this loop fix.
  [COMBAT-AMBIENT-SPEECH-GATING-38](../../bugs/COMBAT-AMBIENT-SPEECH-GATING-38.md).

## Keyboard help and controls

- Current control labels and the keyboard reference are reconciled with the
  source, including reserved shortcuts and the contexts in which they work.
  [UI-KEY-HELP-STALE-38](../../bugs/UI-KEY-HELP-STALE-38.md).
- Help page capacity follows the selected font and viewport dimensions.
  Paging is clamped again when the live layout changes.
  [UI-KEY-HELP-STALE-38](../../bugs/UI-KEY-HELP-STALE-38.md).
- Documentation separates available controls from proposals. This does not
  add an unimplemented control merely because it appears on the roadmap.

## Exterior conversion and compact images

- Sky, cull, hand-metadata and night-lighting passes follow the same validated
  omission checklist before CHIM frames are generated; unexpected missing maps
  still fail. [BUILD-SHADOWED-WORLD-MAPS-38](../../bugs/BUILD-SHADOWED-WORLD-MAPS-38.md).

- A prebuild checklist assigns each exterior cell to legacy BSP, regional
  CHIM or a named town owner before conversion starts.
  [BUILD-SHADOWED-WORLD-MAPS-38](../../bugs/BUILD-SHADOWED-WORLD-MAPS-38.md).
- The current selection identifies 135 redundant town-owned BSP cores and
  omits them before terrain, scenery and flora conversion. A partial core or
  required dependency is retained. Interiors keep independent format choices.
  [BUILD-SHADOWED-WORLD-MAPS-38](../../bugs/BUILD-SHADOWED-WORLD-MAPS-38.md).
- Retired exterior maps and their matching orphan catalogues are excluded
  from the payload. The same validated ownership/omission list reaches the
  image command, save fingerprint and world-disk packer.
  [BUILD-WORLD-FINGERPRINT-RETIRED-38](../../bugs/BUILD-WORLD-FINGERPRINT-RETIRED-38.md), [BUILD-WORLD-PACK-RETIRED-38](../../bugs/BUILD-WORLD-PACK-RETIRED-38.md).
- Explicitly retired or never-compiled maps no longer cause a false missing-
  map failure. Undeclared missing maps still fail, and the selected CHIM
  owners remain bound to the save namespace.
  [BUILD-WORLD-FINGERPRINT-RETIRED-38](../../bugs/BUILD-WORLD-FINGERPRINT-RETIRED-38.md).
- Exact RC1 HDF/package readback confirms 135 redundant BSPs and 77 orphan
  catalogues absent, with 142,235,493 payload bytes removed and required owners
  and dependencies retained. No map additions or unexpected map paths remain.
  The extracted RC1 ZIP is 2,060,379,345 bytes; compressed size and payload
  savings are separate. Final039 requires its own image/package receipt.
- Both FS-UAE and WinUAE presets are provided for this candidate.

## CHIM map, roadmap and release records

- The main-page CHIM map now uses the public snapshot from 13 October 2026,
  14:04 UTC. It replaces the stale 11 October picture and its old release-plan
  overlay; it does not pretend to be a live package inventory.
  [DOCS-CHIM-PROGRESS-STALE-38](../../bugs/DOCS-CHIM-PROGRESS-STALE-38.md).
- The snapshot distinguishes 1,190 converted cells (15 with failed audits),
  99 empty-sea cells and three not converted. The conversion/audit milestone
  is 1,274 of 1,292 land and empty-sea cells. Native and packaged counts remain
  separate; 865 open-ocean cells are outside that denominator.
  [DOCS-CHIM-PROGRESS-STALE-38](../../bugs/DOCS-CHIM-PROGRESS-STALE-38.md).
- The recorded v0.0.38 image had 360 regional cells. Named town frames and
  interiors are separate. RC1 inclusion must come from its own image receipt.
- Release notes now distinguish the published image, a candidate correction
  and a proposed feature. Known-issue links and historical image attribution
  are corrected. The working-version isolation failure is recorded.
  [RELEASE-WORKING-VERSION-ISOLATION-39](../../bugs/RELEASE-WORKING-VERSION-ISOLATION-39.md).
- The roadmap retains the complete bug register, all exterior cells in rings
  0, 1 and 2, failed/held/excluded cells, original reference types, deferred
  actors, missing gameplay and measured loading/cache performance.
  [CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](../../bugs/CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md), [ENGINE-SYNC-IO-MAIN-LOOP-36](../../bugs/ENGINE-SYNC-IO-MAIN-LOOP-36.md).
- The release ancestry pin now identifies published v0.0.38. No new external
  region is claimed merely because its conversion or investigation finished.

## Today's additional findings

- Water: player body profiles lack swim/swim-idle groups and currently fall
  back to walk/idle. Active player callbacks have no drowning update. The
  inherited water helper behind a disabled compatibility path does not supply
  it. These findings explain missing behavior, not a completed repair.
  [WATER-GAMEPLAY-PARITY-38](../../bugs/WATER-GAMEPLAY-PARITY-38.md).
- Torches: player toggle/equip/hand-state paths have no water restriction.
  Water extinguishing, fuel/inventory behavior and the third-person carried
  torch still require implementation and matched reference checks.
  [PLAYER-TORCH-THIRDPERSON-38](../../bugs/PLAYER-TORCH-THIRDPERSON-38.md), [WATER-GAMEPLAY-PARITY-38](../../bugs/WATER-GAMEPLAY-PARITY-38.md).
- Readied water movement: existing contents/movement sampling is independent
  of equipment. The physical cause of the reported water-walking remains
  unresolved; the absent swimming pose alone does not establish that cause.
  [PLAYER-READY-WATER-MOVEMENT-38](../../bugs/PLAYER-READY-WATER-MOVEMENT-38.md).
- Combat speech: idle, automatic and manual greetings lack a complete combat
  gate. Engaging an opponent stops that actor's idle polling, but bystanders
  can continue. Subtitles lack ambient-message ownership, so cancellation
  must distinguish greetings from combat barks, story text and pickup notices.
  [COMBAT-AMBIENT-SPEECH-GATING-38](../../bugs/COMBAT-AMBIENT-SPEECH-GATING-38.md).
- Original-game comparison is required for water, equipment and dialogue.
  Silencing unrelated bystanders during the player's combat is an additional
  requested behavior, not a claim about the original game's exact policy.
- Player pain/combat voice coverage, blocking, coast objects, stairs and
  geometry/collision, NPC animation, loading and streaming remain in the full
  backlog. This changelog does not replace that register or close those bugs.

## Preserved baseline and regression checks

RC1 continues from published v0.0.38 and retains its CHIM selection, BSP and
CHIM lava paths, completed-stage Tel Uvirith at (10,1), original horizon
silhouettes and existing interior formats. These are preservation targets to
verify in the exact new image, not acceptance borrowed from the old image.

The checks cover exact-source tests and Amiga compilation, all-appearance body
budgets, guard torch asset identity, map ownership and payload readback, fresh
save/teleport/lava/death-menu sessions, normal-speed animation/audio and matched
reference views. Game data and ROMs remain outside the public source package.

## Integration checks

The first RC1 gate found stale image-wrapper assertions and an incorrect cache
unit expectation. The corrected checks retain pass ordering and worker-count
forwarding, and verify that editing the shared animation layer changes the
guard conversion key. [TEST-RC1-INTEGRATION-CONTRACTS-39](../../bugs/TEST-RC1-INTEGRATION-CONTRACTS-39.md).

The progress image now has its individual export exception, the map table
retains its totals label, and affected document contents are regenerated.
[DOCS-RC1-PREFLIGHT-39](../../bugs/DOCS-RC1-PREFLIGHT-39.md).

The 4,030-test source suite had one documentation-contents failure and no
errors. The sole documentation change passed 27 affected checks; Amiga
compilation and the applicable source gates passed. Original failed evidence
is retained. Final-source/version/export checks remain required.

## Exact RC1 package and scoped inspection, 13 October 2026

The exact RC1 image and independently extracted package contain 360 verified
whole regional cells, including Tel Uvirith (10,1). Six selected cells
(-3,-11), (-2,-11), (-1,-11), (0,-11), (5,-14) and (6,-14) overlap packaged
town frames only partially and are excluded from that whole-cell count.
All 9,360 frame/chunk files for the 360 cells and all 9,774 CHIM payload files
remain byte-identical to the verified predecessor. The index and four named
town frame maps are present; town coverage and interiors are separate counts.
The 135 town-owned routing-only BSPs are absent under the validated checklist;
required map/dependency readback passed. Native boundary routing remains open.

The exact HDF comparison removes 142,235,493 payload bytes across 212 files:
135 redundant BSP maps and 77 orphan harvest catalogues. No map additions or
unexpected map removals are reported. The independently extracted RC1
playtest ZIP is 2,060,379,345 bytes. Payload savings and compressed archive
size are distinct measurements; these figures do not identify a final039 ZIP.

RC1 package and matching source delivery finalized on 13 October 2026 at
18:06:05 UTC (21:06 in Finland), with source `57a8699` and image `fbf9a6c`
kept distinct. The six partial overlaps remain outside the shipped whole-cell
count. Final v0.0.39 remains in preparation pending explicit owner inspection
approval; RC1 shipment does not supply owner or universal gameplay acceptance.

Conversion/audit data is the unchanged 13 October 2026, 14:04:49 UTC snapshot:
1,190 converted cells including 15 failed audits, 99 empty sea, three not
converted, and 1,274/1,292 audit milestones. The package layer was reconciled
at 17:45 UTC and its local served data was read back. The 865 ocean cells are
outside the denominator. Converted and packaged per-type actor/gameplay
counts remain unknown; the original reference census is preserved. Planned
cells are not included cells and package presence does not prove gameplay.

The exact RC1 package was independently extracted and read back. All 20 body
models and layouts passed their actual-format checks; 1,751 existing non-body
model/animation assets remained byte-identical. A Nord male session exercised
third-person ready/lower, movement, jump and camera changes. This is one
appearance and scene; matched original-game views, all-appearance motion,
loaded memory and performance acceptance remain separate.

A registered Hors save session wrote the settled vf1703 arrival checkpoint,
then entered lava, took damage and died without subsequent save messages.
The untinted death prompt was observed. Reload returned to the same checkpoint
at health 55 and subsequent observation retained health 55. Three AWS saves
decoded against the exact catalogue/content, with the highest sequence
selecting that arrival checkpoint. Guest-exit frames showed AmigaDOS and the
played disks read back. The immediate keyboard-selection screenshot was black;
highlight/selection acceptance is not claimed. Existing unsafe saves remain.

Hunk reserve warnings and repeated chunk20 allocation/repack warnings remain.
No complete cell-wide native, streaming, actor, lighting, gameplay or
performance acceptance is established. Owner approval and final-image checks
remain separate; RC1 evidence does not identify a final v0.0.39 executable.

[CHIM-SEYDA-HUNK-GAP-33](../../bugs/CHIM-SEYDA-HUNK-GAP-33.md),
[CHIM-ZONE-RESERVE-EARLY-33](../../bugs/CHIM-ZONE-RESERVE-EARLY-33.md),
[CHIM-CHUNK-LOAD-FAIL-33](../../bugs/CHIM-CHUNK-LOAD-FAIL-33.md),
[CHIM-GRAFT-REPACK-EMPTY-33](../../bugs/CHIM-GRAFT-REPACK-EMPTY-33.md).

## Known in this build

- [SAVE-TELEPORT-CHECKPOINT-38](../../bugs/SAVE-TELEPORT-CHECKPOINT-38.md): one registered arrival save/reload session passed; wider coverage and owner acceptance remain open.
- [SAVE-LAVA-DEATH-LOOP-38](../../bugs/SAVE-LAVA-DEATH-LOOP-38.md): unsafe old saves remain; one lava/death/reload session passed, wider liquid/fall coverage remains open.
- [UI-DEATH-DAMAGE-TINT-38](../../bugs/UI-DEATH-DAMAGE-TINT-38.md): one untinted prompt was observed; immediate selection frame was black and selection acceptance remains open.
- [PLAYER-JUMP-THIRDPERSON-38](../../bugs/PLAYER-JUMP-THIRDPERSON-38.md): implemented jump candidate needs all-appearance native checks.
- [PLAYER-READY-THIRDPERSON-38](../../bugs/PLAYER-READY-THIRDPERSON-38.md): ready/draw/lower candidates do not complete every combat animation.
- [PLAYER-TORCH-THIRDPERSON-38](../../bugs/PLAYER-TORCH-THIRDPERSON-38.md): carried player torch remains unfinished.
- [BUILD-PLAYER-BODY-BUDGET-FALLBACK-39](../../bugs/BUILD-PLAYER-BODY-BUDGET-FALLBACK-39.md): all twenty actual bakes/layout readbacks passed; native memory and all-appearance motion acceptance remain open.
- [AUDIO-STOP-CHANNEL-RANGE-39](../../bugs/AUDIO-STOP-CHANNEL-RANGE-39.md): sound-stop repair needs its exact regression and target audio checks.
- [COMBAT-AMBIENT-SPEECH-GATING-38](../../bugs/COMBAT-AMBIENT-SPEECH-GATING-38.md): full greeting/subtitle suppression during combat is unfinished.
- [WATER-GAMEPLAY-PARITY-38](../../bugs/WATER-GAMEPLAY-PARITY-38.md): swimming, drowning and water gameplay remain incomplete.
- [PLAYER-READY-WATER-MOVEMENT-38](../../bugs/PLAYER-READY-WATER-MOVEMENT-38.md): water-walking cause remains unresolved.
- [BUILD-SHADOWED-WORLD-MAPS-38](../../bugs/BUILD-SHADOWED-WORLD-MAPS-38.md): exact RC1 ownership/payload readback passed; native boundary routing remains open.
- [BUILD-WORLD-FINGERPRINT-RETIRED-38](../../bugs/BUILD-WORLD-FINGERPRINT-RETIRED-38.md): exact RC1 omission/fingerprint readback passed; final-image rebinding remains required.
- [BUILD-WORLD-PACK-RETIRED-38](../../bugs/BUILD-WORLD-PACK-RETIRED-38.md): exact RC1 packing and independent extraction passed; final-image checks remain required.
- [UI-KEY-HELP-STALE-38](../../bugs/UI-KEY-HELP-STALE-38.md): current font/viewport help needs native readability checks.
- [DOCS-CHIM-PROGRESS-STALE-38](../../bugs/DOCS-CHIM-PROGRESS-STALE-38.md): the refreshed map is a dated audit snapshot, not live packaged coverage.
- [CHIM-COAST-OBJECTS-MISSING-36](../../bugs/CHIM-COAST-OBJECTS-MISSING-36.md): coast object and collision coverage remains open.
- [CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](../../bugs/CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md): geometry does not establish actors or implemented gameplay.
- [ENGINE-SYNC-IO-MAIN-LOOP-36](../../bugs/ENGINE-SYNC-IO-MAIN-LOOP-36.md): heavy loading and blocking streaming remain open.

See the [full bug register](../../BUGS.md#fix-index), [roadmap](../../ROADMAP.md) and
[CHIM coverage guide](../../chim/CHIM_PROGRESS_MAP.md) for the complete remaining work.
