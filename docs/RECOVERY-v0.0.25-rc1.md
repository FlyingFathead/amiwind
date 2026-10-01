# v0.0.25-rc1 recovery checkpoints

Historical checkpoint record. Current combined source status: [RECONCILE-v0.0.25-rc1.md](RECONCILE-v0.0.25-rc1.md).

Current handoff: **checkpoint 006**, incomplete source prerelease.
See [local apply/build/publication commands](LOCAL-CHECKPOINT-v0.0.25-rc1.md).
Earlier checkpoint sections below are historical status records.

## Checkpoint 001: source inventory and executable launchers

Recovery input: `amiwind-2026-10-01_165701.zip`, supplied 1 October 2026.
The archive contains 765 files, VERSION 0.0.25-dev1, no Git metadata,
no build outputs, and no rc1-labelled files. The recovered workspace started
empty except for supplied attachments. No stalled-session worktree was initially found in this workspace; a later
disk-usage investigation found a separate retained worktree (checkpoint 005). The uploaded source is preserved separately, byte for byte.
Reported native results from the stalled session are historical claims only;
they have not been reproduced here. VERSION now targets 0.0.25-rc1; this is an
incomplete source checkpoint, not a validated playable or final release.

| Item | Present in uploaded source | Recovery status |
| --- | --- | --- |
| Terrain directory and rebasing | AWR2 origins and town/terrain transition code | Partial; reported Seyda failure needs reproduction |
| Global coordinate mapping | AW_WorldToSource for terrain/towns | Partial; map uses a separate town path, HUD local only |
| M-map | Existing island panel, marker computed on opening | User reports marker failure; revalidation needed |
| Compass | None | TODO |
| Shoreline correction | Fixed 128-unit sampling; broad zero-height water brush | No reported rc1 correction survived |
| Shoreline diagnosis | Coarse reconstruction can miss source dry rises | Stalled-session finding preserved; independent audit pending |
| M/N screen protection | No input-device filter | TODO; OS interception hypothesis unvalidated |
| Separate keymap | No dedicated keymap config | TODO |
| Ctrl noclip boost | No requested 2x Shift path | TODO |
| Sea visibility switch | dbg sealevel accepts boolean forms; default on | Already implemented; visibility only, physics unchanged |
| Saves | One quicksave, four manual, 1-16 autosaves (default 3), two generations per slot | Inspect empty/incompatible distinctions and ordering |
| Executable Python launchers | Shebangs present; source packer forced 0644 | Fixed source modes and archive metadata; native run not claimed |
| Native tools | Not installed in this recovery environment | Native validation pending |

### Launcher regression

Affected: delivered source through v0.0.25-dev1. Symptom: direct execution may
fail with permission denied despite a Python shebang. Reproduction: extract a
source release and inspect tools/AmiWind-FS-UAE-launcher.py permissions.
Root cause: source packer only gave build.sh executable permissions; private
source bundling discarded ZIP member modes. Fix: preserve 0755 for both FS-UAE
Python entry points, validate permissions during public archive checks, preserve
member metadata in private source bundles, and retain executable metadata in the
legacy opening packer. Future private playable roots must include the identical
launcher with mode 0755. Native validation: none; this is host packaging behavior.

## Required rc1 work, preserved from the incident handoff

- Connect detailed Seyda Neen and Balmora to the complete base-island terrain.
  Test ordinary walking both ways, not only noclip.
- Use one coordinate transform for traversal, map marker and global/local HUD.
  Add a simple gameplay compass. Keep map occlusion as a future TODO only.
- Water/terrain regression: v0.0.25-dev1, local XYZ 9 484 102, DEG 298, P 50.
  The original scene/region must be recorded when reproducing. The stalled
  session found coarse sampling drowning dry source samples; preserve this
  diagnosis for independent verification. Audit source CELL water metadata,
  LAND height reconstruction, dry/wet sample classification and adjoining edges.
  Do not assume a global water plane is universally valid or alter sea height
  blindly. Record exact fix, native routes, BSP/memory/disk budgets and limits.
- Plain M must open the game map in debug/noclip. M/N must type normally in the
  console. Investigate AmigaOS interception/stuck modifiers; intentional desktop
  switching should be debug-only Alt+M. Keep key assignments in a separate file.
- Ctrl+WASD and vertical noclip motion should be 2x Shift speed in debug mode.
- Quicksave(s): investigate actual files and sequence ordering; expose available
  generations, distinguish absent from incompatible saves, never discard old
  files merely because a content fingerprint changed.
- Keep full/incremental source plus SHA-256 sidecars; export one logical change
  at a time before any lengthy conversion. Source first, private playable later.
- Keep development records in docs/. Preserve historical artifacts. The owner
  handles all commits/pushes/tags/GitHub releases. No publication is performed.

## Validation boundary

No native rc1 binary, corrected island rebuild, HDF or native walking claim has
been produced at checkpoint 001. Existing 23 strict contact findings remain
open. Do not relabel the supplied v0.0.15-dev2 private image as rc1. The initial
checkpoint records recovered source and packaging changes only.

## Checkpoint 002: Seyda Neen authored-ground handoff

Affected: v0.0.25-dev1. Symptom: detailed Seyda appears detached from the island;
walking leaves town ground for a terrain-free water belt before a world crossing.
Root cause established from the converter: `prepare_seyda_regions.BOUNDS` encloses
the sea/sky backdrop (+/-2079), but `prepare_quake` emits LAND only within
`config/seyda_area.json:bounds` (-1280,-1792 to 1664,1536). The world directory
used the backdrop extent minus 96, producing +/-1983 transition bounds.

Fix: derive Seyda's handoff from the authored LAND rectangle with the existing
96-unit inset: (-1184,-1696) to (1568,1440). The existing 32-unit outgoing
hysteresis and 24-unit hull clearance fit inside actual ground. Preserve town
BSPs, subcells, NPCs, interiors and the independent Balmora bounds. Reject a
mismatched conversion origin/scale. Host regression verifies all four borders
and source origins; runtime bidirectional rebasing checks remain applicable.

Checkpoint 001's version change lacked matching rc1 emulator templates; added
FS-UAE/WinUAE rc1 templates copied from dev1 with only version references changed.
The broader test run found that omission before any playable build.
Native walking validation and regenerated AWR2 installation are still pending.
No island BSP rebuild is required just to regenerate this directory, but the
separate shoreline geometry correction will require updated terrain BSPs.

## Checkpoint 003: coordinates, map marker and compass

Affected: v0.0.25-dev1. Symptoms: local-only debug coordinates; reported stale
map marker; no normal compass. The map had separate town/terrain transform paths
and captured player position only when opening. Its pause normally prevents
movement, so that alone does not establish the cause of the user's report.

Fix: map and HUD prefer the same AWR2 AW_WorldToSource transform, including the
region Z origin. The map refreshes its marker from simulated player coordinates
on each draw; legacy AWM1 town transforms remain a fallback for older payloads.
The debug footer shows Global XYZ in original Morrowind units and Local XYZ in
runtime units, using the console font and preserving the status bars. Interiors
explicitly have no exterior fix. A normal compass uses source +Y as north and
+X as east. Invalid/nonfinite coordinates are rejected. Map occlusion stays TODO.

Validation: host runtime tests exercise moving the player while the map remains
open without new disk reads, live simulated HUD positions and global/local
values. Native visual inspection and traversal remain pending. SDK, terrain and
QuakeC tools are now installed from pinned verified downloads; FS-UAE is installed.
The uploaded dev1 runtime compiled successfully as a warning-comparison baseline.

## Keyboard recovery (checkpoint 004 work)

Affected: v0.0.25-dev1. Reproduction from the owner: enable debug/noclip;
M/N send the game to AmigaDOS even while entering console text. The observed
pair matches Intuition screen shortcuts with an Amiga qualifier. Source inspection
also found Right Amiga incorrectly translated to game Ctrl. The precise source
of the held OS qualifier on the owner's machine is not established.

Fix: priority-51 input.device filter clears Amiga qualifiers only on M/N while
the game window is active; remove the Right-Amiga-to-Ctrl alias; clear input on
focus changes; explicit Alt+M desktop switch is debug-only. Keep defaults in
config/keymap.cfg and save user bindings separately. Ctrl noclip scales all three
movement axes to twice Shift, raises only the corresponding debug noclip cap,
and does not compound with Shift. See KEYMAP.md for contexts and configuration.

Native cross-compilation passed: 82 warnings, no new warning signatures compared
with freshly compiled uploaded dev1. Host tests cover debug/noclip/focus gates
and pitched plus vertical velocity doubling. Emulator keyboard validation remains
pending; successful compilation is not proof of OS input behavior.

## Checkpoint 005: recovered shoreline source, independently rechecked

A second retained work directory was discovered while tracing disk usage. Its
source and terrain outputs were inspected as untrusted recovery candidates. Only
the shoreline conversion, source textures, ocean enclosure and unused terrain
hull removal were recovered; checkpoint 004 runtime changes remain in place.

Affected: v0.0.25-dev1. Symptom: originally dry rises appear flooded/grey.
Reported camera: local (9,484,102), yaw 298, pitch 50; region was not recorded.
Established cause: stride-four reconstruction can place original dry samples
below water and wet samples above it. The supplied survey's exterior CELL water
levels are all zero. This is measured input, not a sea level inferred from Seyda.
Conversion rejects unsupported nonzero water levels; each region has a bounded
water brush, not an infinite world plane. Interior water is independent.

Fix: insert original height samples where coarse triangles change wet/dry
identity. Shared-edge decisions use the same globally aligned source samples.
The ocean enclosure now extends above the water surface even in deep sea, and
its temporary interior marker is removed after compilation. Source land-default
and water textures replace flat fallback colours. Unused large-actor hulls are
removed only from terrain-only maps; detailed town hulls remain unchanged.

Fresh audit: 330,752 tiles, 8,268,800 source sample comparisons (shared samples
are counted in each tile), 13,287 coarse dry-to-wet and 14,470 wet-to-dry errors;
zero rebuilt wet/dry mismatches. 25,742 neighbouring edges matched. These are
source-mesh checks, not proof of correct runtime water rendering.

The retained 2,526 region BSP hashes and budgets are being verified before
reuse. Native walking, visual shoreline and input validation remain pending.
The cloud filesystem has exhausted ordinary writable capacity; historical
artifacts were retained. Local build instructions will target an external
amiwind-tests directory and private download parts will be at most 150 MiB.

## Checkpoint 006: autosave default and local handoff

Request: configurable autosave history, five levels by default. The existing
aw_autosaves archived setting and Options > Autosave
history already support 0..16. Changed the engine fallback from three to five
and added editable config/game.cfg. Builds copy this to id1/default-game.cfg;
saved id1/config.cfg values load later, so existing preferences remain intact.
Changing Options is saved on normal game exit. Set aw_autosaves 5 in the console
to update an existing installation's setting. This option applies to autosave
slots, not the separate quicksave. Each slot still has two recovery generations.
Reducing retention prunes excess autosave slots only after a successful new
autosave, following the existing policy. Zero disables automatic saving.

The actual quicksave implementation has one slot with two generations, plus
four manual slots. The load menu currently labels absent, corrupt and incompatible
saves alike as empty. This is confirmed by code inspection, but changing the
menu and exposing quicksave generations is still TODO. The owner's ordering
report cannot be diagnosed without the affected saves. No existing save is removed
or migrated by this checkpoint.

All 2,526 recovered terrain BSP hashes match their conversion receipts. Maximum
BSP size 3,249,072 bytes, 9,790 faces and 26,286 clipnodes: within current limits.
Fresh FS-UAE boot loaded rc1 and its 2,526-entry world directory; native input,
walking and visual validation are not yet completed for this recovered source.
Do not import the earlier worktree's native pass claims as fresh validation.

Public source launchers have executable modes. The source packers preserve them
for private bundles. No matching new private HDF is delivered with this source
checkpoint: the cloud disk lacks ordinary free capacity for another full image.
Use LOCAL-CHECKPOINT-v0.0.25-rc1.md for checks, local test compilation and the
full private build path outside the source tree. The full build retains the
strict actor-placement gate; 23 known dev1 findings can stop final HDF assembly.
An asset-free --dry-run is a compiler/boot test only, not the playable demo.

Publish this as an explicitly incomplete checkpoint prerelease if desired.
Reserve v0.0.25-rc1 itself for the completed candidate; use the numbered
checkpoint tag in the supplied commands. Nothing has been committed or pushed.

### Critical console modifier report (part 7)

Affected: owner's dev1-to-rc1 testing, exact installed binary not yet identified.
Symptom: console always types capitals and shifted number symbols, preventing
commands such as dbg 1. Reproduction: enter console and type letters/numbers
without intentionally holding Shift; reported digits become parentheses/symbols.

Established source defects: modifier state was remembered from separate key
transitions, so losing a release leaves Shift latched; raw international key
0x30 was also incorrectly translated as Shift. The exact event that triggered
the owner's state is not established.

Fix: synchronize Shift/Ctrl/Alt from each Intuition RAWKEY qualifier before
dispatch; preserve either physical Shift/Alt while its other key is released.
Caps Lock affects letters only and combines with Shift conventionally. Correct
the international key mapping and clear cached Shift/Caps state on focus reset.
This follows Intuition's documented qualifier handling:
https://wiki.amigaos.net/wiki/Intuition_Keyboard

A compiled host test reproduces a lost Shift release and checks literal dbg 1,
Caps-only digits, Caps+Shift, both Shift keys, focus reset and absence of an
Amiga-to-Ctrl alias. It passes. Native acceptance remains separate. If FS-UAE
itself continues reporting Shift held, this fix cannot distinguish that from a
real held key; aw_input_trace 1 records raw events/qualifiers for diagnosis.

### Native input probe follow-up

A fresh native input.device event probe on the rebuilt executable verified
plain M retains the front game screen, N/M type literal nm in the console, and
debug Alt+M shows the desktop. It caught a new guard-scope issue: the system
screen-cycle shortcut did not return to the game. Root cause: ScreenToBack can
leave ActiveWindow pointing at the hidden game window. The guard now additionally
requires the game window's screen to be the front screen. The repeated probe on the final compiled executable passed all four checks,
including return to the game. The probe binary hash matches the current runtime
source receipt. An expanded probe that tried to synthesize a lost Shift release
timed out; no native stuck-Shift pass is claimed.

The complete host suite passes 333 tests (one optional test skipped). The native
build has 82 warnings, matching the dev1 warning count; no warning-free claim is
made. The original stuck-Shift incident still needs confirmation on the owner's
FS-UAE setup even though the synthesized lost-release host test passes.

### Checkpoint 006 final export validation

See validation/recovery-checkpoint-006.json. Final input probe: M-map screen
retained, console literal nm retained, Alt+M desktop and system return all pass.
Native config persisted aw_autosaves "5". The guarded source installer was
tested against the uploaded baseline: exact source bytes/modes after application,
unrelated files preserved, conflicting local edit rejected before any writes.
The standalone private launcher ZIP and public source both preserve mode 0755.
