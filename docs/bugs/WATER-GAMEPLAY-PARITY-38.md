# WATER-GAMEPLAY-PARITY-38: Water gameplay completeness and original behavior audit

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 12 October 2026, in v0.0.38-dev2 |
| Where | Surface, swimming and submerged gameplay; screenshot in Grazelands cell 12,6 |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.38-dev2 (last seen) |
| Severity | medium: Missing state-transition coverage can conceal equipment and movement faults. |
| Family | Game logic (QuakeC) and saves (`game-logic`) |
| Playtest version | v0.0.38-dev2 |
| From commit | source c2eaa5a, engine c2eaa5a, CHIM world c2eaa5a |
| CHIM engine version | CHIM 0.2.0, engine c2eaa5a, world format unknown |
| Unknown because | Exact loaded cell format and spell state not captured. |
| Platform or emulator | unknown (Screenshot does not identify emulator.) |

<!-- END GENERATED FACTS -->

## Symptom

Water gameplay lacks a demonstrated comparison against original Morrowind/OpenMW
across surface, swimming and submerged states. Related owner reports identify
apparent water-walking while equipment is readied and lighting a torch underwater.
This is an audit gap; not every behavior below is established to be broken.

## Where

Full v0.0.38-dev2 exterior water. The supplied underwater torch screenshot shows
Grazelands cell 12,6, global position 99333,49260,-466, time 02:37.

## How it happened

Cause unknown. AmiQuake SV_CheckWater in sv_phys.c already samples feet, body
and view height to set waterlevel and watertype using SV_PointContents. Begin
with this existing mechanism and movement machinery before adding new checks.
The behavior of equipment, effects and damage across these states needs tracing.

## Why it was not caught

No complete matched reference/native state-transition matrix is attached.
Existing visual appearance checks do not establish gameplay equivalence.

## Reproduction

Compare identical original/OpenMW and target scenes while entering water,
wading, swimming at the surface, diving, remaining submerged and leaving water.
Record depth, position, movement type, waterlevel, health, fatigue, breath and
active effects where supported. Cover sheathed and readied fists/weapons, torch
equipping/lighting/extinguishing, attacks and casting. Check Water Walking and
Water Breathing separately, including expiry, transitions and save/load.
Record unsupported mechanics explicitly rather than assuming parity.
Investigate lava contact, damage cadence, protection and escape separately;
water behavior alone is not lava acceptance.

## Repair

Pending diagnosis and original-game comparison. Preserve the current underwater
visual effects: the owner explicitly approves their appearance and requests no
changes to them. Reuse existing contents and movement state, avoid redundant
per-frame work and allocations, and measure CPU/memory on the baseline target.

## Verification

Open. Owner screenshot preserved; independent reproduction, matched reference
matrix and measured candidate acceptance remain pending. The screenshot alone
does not establish movement physics, spell state or torch fuel behavior.

## Prevention

Keep a repeatable water/equipment/effect transition matrix for both legacy BSP
and CHIM worlds. Link failures to their specific issue records. Require measured
baseline resource costs for repairs and preserve visual controls.

## Related reports

- [Readied water movement](PLAYER-READY-WATER-MOVEMENT-38.md)
- [Torch pose and underwater lighting](PLAYER-TORCH-THIRDPERSON-38.md)
- [Lava coverage](BUILD-LAVA-COVERAGE-38.md)


## Owner follow-up, 12 October 2026

The owner reports walking poses at the water surface and underwater, missing
swim/dive animations, and no observed breath-exhaustion damage. Cover the player
and all relevant NPCs, including future companion following. Compare original
drowning damage, red-screen feedback and audio before choosing behavior; the
original torch-extinguish trigger also remains to be established. Study lava
entry and damage separately. Reuse AmiQuake SV_WaterMove (sv_user.c) and
SV_CheckWater (sv_phys.c) where suitable; existing machinery is not proof that
all integration or animation works, nor proof of zero additional CPU/RAM cost.


## Owner evidence reconciliation, 13 October 2026

The following owner screenshot evidence was visually reviewed. Original images
remain in the private evidence archive; identifiers bind this report to those
originals. This records reported symptoms and comparison controls, not a repair
or runtime acceptance. Missing build or pose information remains unknown.

- `OWNER-20261012-152017`: SHA-256 `e53bd537e39bdae534cd1a83ca7e5c3d3093ef284a94a760eaa18654becaea8e`. Underwater view shows a torch. Still frame cannot establish swimming animation.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Game logic (QuakeC) and saves (`game-logic`). QuakeC entities, saves and game state. See [families](README.md#families).

- AW-20260928-10 (no report page): Interior door animation and sound missing
- AW-20260928-12 (no report page): Downstairs interior doors cannot open
- AW-20260928-19 (no report page): Courtyard barrel incorrectly says empty
- AW25-06 (no report page): Quicksave shown as empty; save ordering confusing
- [CENSUS-DOOR-STUCK-29](CENSUS-DOOR-STUCK-29.md): Player stuck after opening Census Office hall door
- [CHIM-COURT-BARREL-USE-33](CHIM-COURT-BARREL-USE-33.md): Census courtyard on CHIM: Fargoth's ring barrel cannot be used, so the opening cannot proceed
- CLOCK-01 (no report page): Automatic clock dropped fractional milliseconds each frame
- [COMBAT-BLOCKING-36](COMBAT-BLOCKING-36.md): Requested: blocking in combat - NPCs block by their Block skill with a block animation, the player blocks with the right mouse button
- [COMBAT-FIST-BLOCK-33](COMBAT-FIST-BLOCK-33.md): A fighter with a shield blocks while fighting with fists
- [COMBAT-HIT-RECOVERY-33](COMBAT-HIT-RECOVERY-33.md): Fatigue hits did not stagger, and knockdowns lasted half a second too long
- [COMBAT-NO-CONDITION-33](COMBAT-NO-CONDITION-33.md): Weapon and shield condition were ignored in combat
- [COMBAT-NOT-SAVED-33](COMBAT-NOT-SAVED-33.md): Combat state and NPC deaths are not saved
- [COMBAT-PLAYER-ATTACK-TYPE-33](COMBAT-PLAYER-ATTACK-TYPE-33.md): The player's attack type and swing strength were random
- [COMBAT-PLAYER-DEATH-FALL-33](COMBAT-PLAYER-DEATH-FALL-33.md): The player does not collapse on death
- [COMBAT-PLAYER-KNOCKDOWN-33](COMBAT-PLAYER-KNOCKDOWN-33.md): The player's knockdown and knockout exist only in the combat rules
- [COMBAT-SETUP-DICE-BLOCK-33](COMBAT-SETUP-DICE-BLOCK-33.md): The Arena setup offers no dice/style choice before a fight, and there is no block button
- [DEBUG-MAP-SAVE-VALIDATION-32](DEBUG-MAP-SAVE-VALIDATION-32.md): After a debug map load of an open-world map the autosave fails validation; two of three also report Interior spawn blocked
- [ENGINE-ANGLEMOD-RANGE-35](ENGINE-ANGLEMOD-RANGE-35.md): anglemod returned 360 for -360 and passed NaN and out-of-range values on
- [ENGINE-QC-ARGS-SYSERROR-35](ENGINE-QC-ARGS-SYSERROR-35.md): Bad QuakeC sound arguments stopped the program; lightstyle had no range check
- [INTRO-CAMERA-GATING-38](INTRO-CAMERA-GATING-38.md): Opening vanity and third-person cameras expose an unselected default race
- [PHYSICS-GRAVITY-SCALE-36](PHYSICS-GRAVITY-SCALE-36.md): Gravity is Quake's 800 although the world is scaled 0.25: jumps and falls are several times faster than the original
- [PLAYER-DEATH-LIMBO-35](PLAYER-DEATH-LIMBO-35.md): After the player dies there is no way out: the game stays in a limbo with no reload or retry
- [PLAYER-JUMP-THIRDPERSON-38](PLAYER-JUMP-THIRDPERSON-38.md): Third-person player jump animation is missing
- [PLAYER-READY-WATER-MOVEMENT-38](PLAYER-READY-WATER-MOVEMENT-38.md): Readied weapon or torch appears to allow walking on water
- [QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md): Every aw_flame entity prints load errors: the game logic has no aw_flame spawn function or aw_flame_size/aw_flame_shape fields
- RENDER-METADATA-29 (no report page): Native renderer metadata warns as an unknown QuakeC field
- SAVE-EQUIPMENT-29 (no report page): Quickload returns with hands and torch put away
- [SERVER-FRAME-ARRIVAL-33](SERVER-FRAME-ARRIVAL-33.md): The server frame costs about 226 ms per frame at the Balmora arrival camera on a slow 68040
- [WAIT-DURING-COMBAT-36](WAIT-DURING-COMBAT-36.md): Waiting is allowed in the middle of a fight
- [WAIT-FEET-IN-WATER-36](WAIT-FEET-IN-WATER-36.md): Waiting is allowed with the feet in water (the original refuses it)

Related bugs in other categories:

- [PLAYER-TORCH-THIRDPERSON-38](PLAYER-TORCH-THIRDPERSON-38.md): Player torch and holding pose disappear in third person while light remains

<!-- END GENERATED CATEGORY -->
