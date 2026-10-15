# AmiWind v0.0.39 - Cell By Cell, Piece By Piece

14 October 2026. Running on CHIM Engine v0.2.0.

This final source release combines the RC1 changes and RC2 repairs. The release
was authorized on 14 October after RC2 delivery. This decision does not close
individual gameplay issues or claim new visual acceptance. The owner published public source at commit
`751e1efa6b28e7fc58453fc81c73100715b88195`; neither RC1 nor RC2 needs to be
installed or published first when updating public v0.0.38 source.

The exact RC2 source passed 4,043 tests with four skips and three expected
failures, Amiga compilation, package extraction and full disk readback. Scoped
native observations below belong to that RC2 package. The final source carries
the same runtime implementation with final version metadata and reconciled
documentation; final-source validation is recorded separately from RC2 evidence.

RC1 contributes safer grounded teleport checkpoints, avoidance of new lava/slime
autosaves, untinted death-menu rendering, ready/jump animation work, keyboard
help, sound cancellation and exclusive CHIM exterior ownership. Existing unsafe
saves are not repaired automatically. See the [changelog](CHANGELOG.md) and
[RC1 history](RELEASE-v0.0.39-rc1.md).

## Renewed gameplay findings, 14 October 2026

The owner reports the same gameplay in inspected RC2 and final: physical LMB
still lacks a third-person punch, movement fails with fists drawn, block
presentation is missing in both views, and swimming still sinks with an upright
submerged body. See [punch](bugs/PLAYER-PUNCH-THIRDPERSON-39.md),
[ready movement](bugs/PLAYER-READY-MOVEMENT-39.md),
[blocking](bugs/COMBAT-BLOCKING-36.md) and
[water](bugs/WATER-GAMEPLAY-PARITY-38.md). All remain open. Earlier scoped native
controls, successful input/damage or model presence do not accept these owner
scenarios. Follow-up repair and package acceptance remain pending.

The mutable follow-up source also adds `dbg characterchange` as a testing aid
using the existing pier appearance menu. Two focused C/console checks pass;
target/native menu and package checks remain pending. This command is not part
of the sealed source history and does not establish a gameplay repair.

## Repairs carried forward from RC2

- [Third-person torch holding](bugs/PLAYER-TORCH-THIRDPERSON-38.md): Target compilation and scoped Nord native F-then-V, hold/walk/run, torch-off and first-person control pass; an unaltered game/audio clip shows the carried mesh and raised arm. All 20 companions pass bake/readback. All appearances, matched original visual comparison and owner acceptance remain pending; complete RC2 package readback is verified.
- [Third-person punches](bugs/PLAYER-PUNCH-THIRDPERSON-39.md): connect the body
  punch poses to the existing attack clock and ready movement groups. RC1
  attack input and damage could work while its body did not show the punch.
  Scoped Nord male and Orc female candidate footage now shows torso/arm punch
  motion. The exact package also shows scoped Nord punch changes. Damage, physical LMB
  input, matched A/B, seams and owner acceptance remain separate checks.
- [Fast gait regression](bugs/PLAYER-MOVEMENT-FRAME-SKIP-39.md): retain eight
  walk and six run samples for normal and ready movement. Compact temporary
  arm-action grids avoid cutting the ordinary gait to two poses. The owner
  identifies v0.0.38 as the last good fast-gait comparison; speed-linked
  playback still needs an in-game comparison.
- [Thin legs](bugs/PLAYER-BODY-LEG-SHAPE-39.md): keep the first suitable body
  mesh, compact the player skin atlas and check combined leg sections before
  accepting a lower geometry budget. All 20 candidate model/layout pairs now
  pass binary checks within the unchanged 512 KiB limit: 16 exact prior pairs
  reused and four female bodies newly baked. The leg guard excludes tail
  geometry at its unchanged 75% threshold; 33 focused checks pass. Knee/calf
  section audits still flag possible gaps, mostly from simplification. Numeric
  widths and binary checks do not establish visual or owner acceptance.
  Complete package readback now verifies all 20 sets; visible leg/seam quality
  remains open.
- [NPC chase animation](bugs/NPC-NO-RUN-ANIM-35.md): reset mover registration
  on every server scene spawn, including same-map reloads. A reused world-model
  pointer previously left registrations out of step with reset model slots.
  The [guard spear pose](bugs/NPC-SPEAR-ATTACK-REGRESSION-39.md) has an
  authored two-hand-wide conversion correction. Exact-source staged guard
  footage shows chase/strike changes and health 995 to 882.3; 24 played-file
  hashes pass. This is separate from final-package asset readback;
  attachment alignment, damage balance and owner acceptance remain pending.

## Click-to-pin inspection HUD

[DBG-ENTITY-INSPECT-39](bugs/DBG-ENTITY-INSPECT-39.md) adds `dbg hud on`: aim
at an actor or object and click to pin its runtime entity, source record ID
and reference when retained, model, scene and coordinates. The same details
are printed in the console. A bounds pick is labelled explicitly; merged
scenery without individual reference data says unavailable.

The snapshot stays fixed until another click or scene load. Attack clicks
select while this mode is on. `dbg hud off` restores attacks after releasing
any held button. Inspection defaults off and is not saved. `dbg ent` makes a
one-shot selection; `dbg overlay` and photo-mode Ctrl+H keep their ordinary
overlay-only behavior. The mode uses the rendered camera in either perspective.

Seventeen focused automated checks cover the inspector and associated HUD,
console and registry behavior. Body/animation changes passed 83 affected checks;
NPC registration has separate animation/combat checks. Exact Amiga compilation and complete package readback passed; scoped package
native observations are recorded above. Inspector identity, all-appearance
visual behavior and owner acceptance remain separate gates.

## Controls and remaining work

Preserve the [RC1 fight-ready posture](bugs/PLAYER-READY-THIRDPERSON-38.md)
that the owner likes while comparing the repaired legs, gait and punches.
The [third-person torch](bugs/PLAYER-TORCH-THIRDPERSON-38.md) now has scoped native holding/movement evidence. [Swimming and diving](bugs/WATER-GAMEPLAY-PARITY-38.md) have implemented RC2 companion and idle-water changes with scoped package checks; broader parity and acceptance remain open. The extracted RC2 package holds origin (704, -320, -25) for a four-second no-input water control after noclip is disabled. Pitch45 with forward movement descends to origin (832.7, -320, -153.7) at waterlevel 3 and shows changing swim poses. Both readied first-person fists remain visible at default horizontal FOV 90/viewsize 100. Actual OpenMW0.48 reference holds depth and retains first-person fists; no dedicated first-person stroke or blanket body pitch is established. Broader drowning, fatigue, combat, all appearances and owner acceptance remain pending.

[Stat-based movement and running fatigue](bugs/PLAYER-MOVEMENT-STATS-PARITY-39.md)
are separate mechanics work. The roadmap preserves a convenient fast debug
preset alongside future original-stat gameplay and all eight attribute effects.
Vivec [mushroom cap seams](bugs/MESH-VIVEC-CAP-GAP-38.md) remain open. The
[Ordinator appearance report](bugs/NPC-ORDINATOR-APPEARANCE-39.md) has verified
original and packaged cast mappings; the exact actor in the screenshot still
needs an in-game selection at the recorded viewpoint.

## Known in this build

Final packaging retains these current open issues and
verification limits from the canonical register. The delivered inspection
package does not supply completed owner acceptance. See the register for the complete backlog.

- [PLAYER-PUNCH-THIRDPERSON-39](bugs/PLAYER-PUNCH-THIRDPERSON-39.md): The independently extracted RC2 package shows Nord third-person torso/arm punch changes in an unaltered native clip. Post-exit readback preserves exact assets. Console attack control does not prove physical LMB input or damage; all appearances, matched original comparison, seams and owner acceptance remain pending.
- [PLAYER-MOVEMENT-FRAME-SKIP-39](bugs/PLAYER-MOVEMENT-FRAME-SKIP-39.md): Full gait samples are present in the read-back RC2 body assets, but package presence and scoped punch/water footage do not establish normal-speed fast-gait timing, original speed-linked playback or owner acceptance. Preserve the owner-reported v0.0.38 comparison and good RC1 ready posture.
- [PLAYER-BODY-LEG-SHAPE-39](bugs/PLAYER-BODY-LEG-SHAPE-39.md): All 20 body and companion sets are present in the exact RC2 package. The scoped Nord package footage does not establish knee/calf continuity or fix the owner-reported thin legs. Prior section metrics and possible simplification gaps remain diagnostic; matched original/v0.0.38, all-appearance and owner acceptance remain pending.
- [BUILD-PLAYER-BODY-BUDGET-FALLBACK-39](bugs/BUILD-PLAYER-BODY-BUDGET-FALLBACK-39.md): Full RC2 disk readback and independent package extraction verify all 20 declared base bodies and140 torch/held/swim companion files within the unchanged 512 KiB model cap. Exact played readback preserves186 engine/metadata/body files. Binary coverage does not certify all 20 visual appearances, native memory, leg seams or owner acceptance.
- [PLAYER-READY-THIRDPERSON-38](bugs/PLAYER-READY-THIRDPERSON-38.md): Preserve the approved RC1 fists-ready posture; this does not complete all weapon/equipment poses.
- [PLAYER-JUMP-THIRDPERSON-38](bugs/PLAYER-JUMP-THIRDPERSON-38.md): All-appearance native jump acceptance remains separate from body binary coverage.
- [NPC-NO-RUN-ANIM-35](bugs/NPC-NO-RUN-ANIM-35.md): Exact-source 690 staged diagnostic footage shows guard pursuit and multiple strike poses, with health 995 to 899 then 882.3. Guest exit reaches AmigaDOS and 24 played-file hashes pass. This extends scoped mover evidence after the same-map reset; all-NPC, matched original, final-package guard and owner acceptance remain separate.
- [NPC-SPEAR-ATTACK-REGRESSION-39](bugs/NPC-SPEAR-ATTACK-REGRESSION-39.md): Exact-source 690 staged diagnostic footage shows guard pursuit and changing strike poses, with hits reducing health 995 to 899 then 882.3. Post-exit readback verifies 21 movers plus engine, bootcheck and catalogue (24 files). This supports scoped chase/attack and preserved damage, not damage balance or complete spear attachment alignment. Final RC2 disk readback separately verifies the 21 equipped-resident files and palette binding; it does not turn the staged diagnostic into final-package guard native acceptance. Matched OpenMW and owner acceptance remain pending.
- [ANIMKIT-COVERAGE-35](bugs/ANIMKIT-COVERAGE-35.md): Exact RC2 package readback covers all 20 player appearances and their torch/held/swim companions. Scoped Nord package native footage verifies punch changes, carried torch, swim poses and underwater first-person fists. Original group availability and binary declarations still do not establish every actor/equipment animation or all-appearance acceptance.
- [DBG-ENTITY-INSPECT-39](bugs/DBG-ENTITY-INSPECT-39.md): Corrected rendered-frame selection has focused C checks; exact target/native identity verification remains pending and grouped bounds are approximate.
- [NPC-ORDINATOR-APPEARANCE-39](bugs/NPC-ORDINATOR-APPEARANCE-39.md): Original/package cast mapping agrees; the foreground unhelmeted actor's identity and visible appearance repair remain unverified.
- [PLAYER-TORCH-THIRDPERSON-38](bugs/PLAYER-TORCH-THIRDPERSON-38.md): The independently extracted RC2 package shows a raised left arm and carried torch on Nord, then torch-off and water/land model selection. Full disk readback verifies all 20 body/held-torch companions. Scoped native evidence is not all-appearance or matched-original visual acceptance; owner acceptance remains pending.
- [WATER-GAMEPLAY-PARITY-38](bugs/WATER-GAMEPLAY-PARITY-38.md): The extracted RC2 package holds origin (704, -320, -25) for a four-second no-input water control after noclip is disabled. Pitch45 with forward movement descends to origin (832.7, -320, -153.7) at waterlevel 3 and shows changing swim poses. Both readied first-person fists remain visible at default horizontal FOV 90/viewsize 100. Actual OpenMW0.48 reference holds depth and retains first-person fists; no dedicated first-person stroke or blanket body pitch is established. Broader drowning, fatigue, combat, all appearances and owner acceptance remain pending.
- [PLAYER-READY-WATER-MOVEMENT-38](bugs/PLAYER-READY-WATER-MOVEMENT-38.md): RC2 package native water/land selection and changing swim poses are verified in the scoped Nord control, with both default-camera first-person fists visible. This does not close the historical water-walking report or establish all states, appearances and original behavior parity.
- [PLAYER-MOVEMENT-STATS-PARITY-39](bugs/PLAYER-MOVEMENT-STATS-PARITY-39.md): Original stat/encumbrance movement and running-fatigue debit are future mechanics work; proposed maxstats controls are not implemented.
- [MESH-VIVEC-CAP-GAP-38](bugs/MESH-VIVEC-CAP-GAP-38.md): Owner inspection still shows a giant mushroom cap opening.
- [CHIM-SEYDA-HUNK-GAP-33](bugs/CHIM-SEYDA-HUNK-GAP-33.md): Exact RC2 package native inspection repeats startup hunk-reserve warnings and zone-full chunks 100/107 retries after water and land return. A playable scene and successful guest exit do not prove complete chunk recovery, memory headroom or performance acceptance. This remains an existing open finding.
- [DEBUG-MAP-SAVE-VALIDATION-32](bugs/DEBUG-MAP-SAVE-VALIDATION-32.md): Direct diagnostic interior loading can refuse save validation while retaining previous saves; ordinary transitions need separate checks.
- [SAVE-TELEPORT-CHECKPOINT-38](bugs/SAVE-TELEPORT-CHECKPOINT-38.md): Historical RC1 scoped arrival/reload evidence does not establish wider RC2 checkpoint acceptance.
- [SAVE-LAVA-DEATH-LOOP-38](bugs/SAVE-LAVA-DEATH-LOOP-38.md): Historical RC1 lava/death/reload evidence does not clear unsafe old saves or wider RC2 liquid/fall coverage.
- [UI-DEATH-DAMAGE-TINT-38](bugs/UI-DEATH-DAMAGE-TINT-38.md): Historical scoped prompt evidence leaves immediate selection-frame and wider RC2 UI acceptance separate.
- [COMBAT-AMBIENT-SPEECH-GATING-38](bugs/COMBAT-AMBIENT-SPEECH-GATING-38.md): Complete greeting/subtitle suppression during combat remains unfinished.
- [CHIM-COAST-OBJECTS-MISSING-36](bugs/CHIM-COAST-OBJECTS-MISSING-36.md): Coast object and collision coverage remains incomplete.
- [CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](bugs/CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md): Geometry coverage does not establish deferred actors or unimplemented gameplay.
- [ENGINE-SYNC-IO-MAIN-LOOP-36](bugs/ENGINE-SYNC-IO-MAIN-LOOP-36.md): Exact RC2 package native inspection repeats zone-full chunks 100/107 retries after water and land return. Scoped gameplay and successful AmigaDOS exit do not clear blocking streaming, heavy loading, memory/performance or all-cell traversal issues.

## Coverage

RC2 full disk readback and independent extraction verify360 whole regional CHIM cells; six partial town overlaps remain excluded. The exact inspection package and matching source artifacts were finalized at 2026-10-13T22:15:44Z. Conversion/audit/native-cell coverage and owner acceptance are unchanged. Historical empty RC1 plan remains incorrectly selected as next by the existing selector; no supported historical flag permits a truthful metadata-only correction.

Packaging does not certify every light, actor, gameplay mechanic or traversal.
The [cell tracker](chim/CELL_TRACKER.md) keeps converted, audited, native-checked
and packaged coverage separate. No new package inherits owner acceptance from
RC1 or v0.0.38.
