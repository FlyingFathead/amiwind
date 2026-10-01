# Current project state — 1 October 2026

**Source reconciliation:** see [RECONCILE-v0.0.25-rc1.md](RECONCILE-v0.0.25-rc1.md). Earlier native results describe the original candidate, not the merged runtime.

**Current candidate: v0.0.25-rc2**, following the owner's v0.0.25-dev1 feedback.
The Seyda Neen boundary uses ground coverage, preserving detailed Seyda Neen AND
Balmora. The frozen survey still supplies 2,526 terrain/water regions. Shoreline
triangles retain original wet/dry samples; the water datum remains source Z=0.
Outside the two towns, other scenery, settlements and actors remain future work.

Universal source XYZ, local XYZ and the map cross use the live simulated player
position. The ordinary HUD has a compass. M/N typing is protected from the
Amiga screen shortcuts; intentional desktop access is debug Alt+M. Ctrl debug
noclip flight is twice Shift speed. Editable keymaps are separate from settings,
with a maintained [control reference](KEYMAPS.md). Unexplored-map masking is a
TODO and is explicitly outside rc1.

The 23 existing strict NPC contact findings remain unresolved and the ordinary
production image gate remains unchanged. This candidate is not production
acceptance. Inventory, general quest execution and complete playthrough
acceptance remain future work. See [candidate verification](RELEASE-v0.0.25-rc2.md)
and [terrain conversion](WORLD_TERRAIN.md). Published dev1 and v0.0.24 archives
remain immutable.

## RC3 recovery baseline (historical)

**AmiWind v0.0.24-rc3 — owner-requested recovery candidate.** All 2,935
base-master NPC/creature records map to 3,551 successfully converted assets.
There are 29 exact-model opt-in geometry allowances, bounded at 1,024 triangles.
Dagoth Ur retains the original mask/crest geometry and a larger texture atlas.
The gallery browser now owns its mouse cursor and supports paging and scrolling.
The old pale-face blotches traced to stale palette lookup columns; RC3 repairs
lighting/fog tables and adds a packaging consistency check.

Vivec and the cliff racer use selected authored idle poses and retain their
height above the gallery floor. These are static inspection poses, not a full
creature animation system. Conversion coverage does not certify every model's
appearance. Gallery return, greeting previews and search remain available.

Grounding still resolves residents in their owning sub-cell and preserves
copies. All reported Balmora floater references pass the mesh-contact check,
but 23 broader contact findings remain unresolved. The three new RC2 walking
stalls have a collision-trace correction; old positive-Y stairs10 and exact wedge
reports remain open. The candidate carries the failed contact audit; the normal
production image gate still requires a complete pass. Method 1 remains the
loading default. See [RC3 scope](RELEASE-v0.0.24-rc3.md).

## RC1 baseline (historical)

**AmiWind v0.0.24-rc1 — candidate for Welcome to Balmora.**

Balmora now includes 43 destination interiors (42 city interiors plus Tharys
Ancestral Tomb), 93 NPC placements (90 living and three authored corpses), and
80 living NPC voice sets. Original links cover 70 exterior entrances and two
additional same-room Fighters Guild links. All 43 maps passed native loading;
all 70 entrance/return routes and both internal links passed targeted native
checks. Ordinary walking checks cover the reported stairs/arches except the
unresolved positive-Y report. The exact stairs/rock wedge is also still open.

Full selected interior geometry is retained, including distant-origin towers
and previously omitted dressing. The checklist records stair collision and
slope classification, ground-material repairs, clearer gold e/H glyphs, shared
NPC targeting, the guard's final dock post and filename packaging corrections.
These are local checks, not owner acceptance of every route or the full game.

The accepted Strider, frozen-frame Loading... box, Shift+V, 90-degree FOV,
base player hull and race/sex eye heights remain. Balmora has 64 overlapping
regions; Seyda Neen has 25 regular regions plus the intro pier and ring
courtyard. Loading replaces a BSP synchronously. Background streaming,
whole-map polygon-density analysis, full NPC services, schedules, combat and
quest simulation remain future work. Greetings use a bounded authored fixture.

Stable v0.0.23 and the published dev5 prerelease remain unchanged. Final
v0.0.24 needs the owner's green light. See [RC scope](RELEASE-v0.0.24-rc1.md),
[complete checklist](INVESTIGATION-v0.0.24-rc1.md),
[conversion lessons](BALMORA_CONVERSION_LESSONS.md) and
[Amiga naming constraints](RELEASE_WORKFLOW.md#amiga-limitations).

## Previous checkpoint notes

**AmiWind v0.0.24-dev4: Seyda Neen subdivision, opening controls and teleport shortcuts.**

Seyda Neen now has 30 overlapping regular regions plus compact arrival-pier and
Census ring-courtyard BSPs. The first ship exit uses the compact pier. Shared
coordinates, overlap, hysteresis and state restoration extend the Balmora method;
frozen-frame Loading... presentation remains the default. Both exteriors cap
effective distance at 540 to stay within their certified overlap.

`dbg tp` opens the destination picker; direct shortcuts include `balmora`,
`seydaneen`, `prisonship` and the other converted scene names. Seyda Neen interior
lookup works from Balmora. Choose defaults highlighted, review has page numbers,
Shift+V replaces bare numeric distance presets, and the Census front exit stays
locked during registration. See [dev4 scope](RELEASE-v0.0.24-dev4.md) and
[investigation findings](INVESTIGATION-v0.0.24-dev4.md).

Seyda Neen, thirteen town interiors, Addamasartus, the prison ship and Balmora's
exterior are converted. Balmora uses 64 overlapping resident regions and return
Strider travel. Dev2 restores missing architectural facades, repairs two concave
underpass colliders, the guard's final approach and Talk hints. Race/sex now
selects eye height; the measured base player body and Quake 90-degree FOV remain.

Owner playtest: dev3 Balmora regions/sub-cells work surprisingly well and are a
promising basis for the wider world. The Strider is explicitly accepted: leave
its conversion unchanged. Balmora often feels faster than Seyda Neen; this
observation remains distinct from matched measurements. The loader replaces
one BSP synchronously and does not yet stream in the background.

See [earlier findings and evidence](INVESTIGATION-v0.0.24-dev2.md),
[mesh mapping notes](MESH_TIPS_AND_TRICKS.md), [race heights](PLAYER_MOVEMENT.md#original-race-based-heights)
and [roadmap](ROADMAP.md). Boat performance still needs optimization; the matched
v0.0.23/dev1 test did not reproduce a new slowdown. Boundary loading remains
synchronous. Balmora interiors, most services, combat, broader AI, day/night sky
and blight remain unfinished. Full natural-opening and citywide walking acceptance
are still open; focused checks do not close those items.

## Historical context

The following describes the preceding v0.0.22 release.

v0.0.22 promotes the reconciled v0.0.21-dev8 source checkpoint to the current
normal public release without adding gameplay features. The dev7 boot checker,
launcher, dry-run builder and version generator remain preserved. TTF paper output
stays preferred; bitmap-derived paper ink defaults to the approved filled candidate,
with JSON/CLI opt-out. The small character UI, other menus and dialogue retain their
existing fonts. CPU-job detection tolerates a failed process CPU-count query.
See [v0.0.22 scope](RELEASE-v0.0.22.md) and [paper settings](PAPER_FONT_OPTIONS.md).

Whole-pipeline parallel scheduling remains pending. This source merge does not
claim a new Amiga/HDF build or emulator playtest. The owner completed all 17
stages of the earlier dev5 Steam build; that is separate historical evidence.

Dev7 makes the native preflight visible long enough to diagnose startup: after a
successful check it counts down for five seconds, with Space or Enter as an immediate
skip. The asset-free dry-run image now runs `AmiWindCheck` before `AmiWindDryRun`,
then shows the existing dry-run notice. This avoids relying on Amiga console
scrollback and makes the dry-run HDF a useful preflight test image. See
[dev7 scope](RELEASE-v0.0.21-dev7.md).

Dev6 added a two-layer startup diagnostics path. The native `AmiWindCheck` prints
its exact AmiWind version at entry and exit and reports guest-observable CPU/FPU,
AGA, PAL timing, Exec API and memory state. JIT, fastest-possible CPU mode,
cycle-exact policy and exact ROM-file identity remain host-side facts; the portable
FS-UAE launcher now enforces the accelerated reference profile, prints a checklist,
and maps the known ROM SHA-256 to Kickstart 3.1 A1200 40.68. See
[dev6 scope](RELEASE-v0.0.21-dev6.md).

Dev5 preserves the dev4 gameplay/world-mapping checkpoint and fixes host-side
font-source portability. GOG GOTY remains the preferred source installation: its
loose BookArt TTFs are preferred for rasterization. Steam GOTY normally lacks
those TTFs, so the build reports the difference and falls back to Bethesda FNT+TEX
font data rather than failing at the reading stage. See [dev5 scope](RELEASE-v0.0.21-dev5.md).

Dev4 packages Horstator's 28 September evening notes and the optional polygonal
POI-region design in WORLD_MAPPING_PLAN.md and ROADMAP.md. Region swapping and
assisted doorway simplification remain planned, not shipped.

Dev3 corrects the omitted Census room and dock approach distance, improves paper
contrast and Census wall-art conversion, and selects New Game by default. The
fixed Y/N/version index is in BUGS.md. Full opening acceptance remains pending.

The dev2 correction preserves the original invisible enclosure while fixing its
compound rotations. Focused native plank passage/containment passed; owner
confirmation and full opening acceptance remain pending.

The opening/character/save prototype and UI changes are described in
[the checkpoint notes](RELEASE-v0.0.21-dev3.md). Native validation is recorded
separately from implemented source; incomplete acceptance items remain open.
Numeric journal indices, globals, item counts and NPC script locals are separate
state. The intro stage only coordinates this opening UI sequence.

The following v0.0.20 and earlier notes are historical.

The standalone [FS-UAE launcher](FS-UAE-LAUNCHER.md) now speeds up repeat
playtests: latest-image selection, remembered ROM and generated local config.
This host-tool addition does not change the runtime or resolve the open freeze.

Owner chose maintenance first. The next milestone includes [dock character
creation and Census Office interiors/NPCs](CHARACTER_CREATION.md), attributes set,
and working [save/load with adjustable autosave history](SAVEGAME_PLAN.md). These are not v0.0.20 features.

Ship wave/hull ambience is reduced by 5 dB relative to v0.0.19. This release
documents the intermittent freezes; it does not claim to fix them. See
[release notes](RELEASE-v0.0.20.md).

**Open stability reports (28 September):** intermittent prison-ship exit freeze
and a separate dock/menu freeze with looping music on FS-UAE 3.1.66. The hatch
worked on retry. Both remain unresolved; see [bug register](BUGS.md).

New Game enters the first ship introduction with original voices, name entry,
speech-driven facial poses and bounded guard navigation. UI bars have distinct
colors and the optional outer frame defaults off. See [scope and verification](RELEASE-v0.0.19.md).
Version 0.0.19 also silences routine track-change notices when the debug overlay is off.
Dev5 refines menus, increases movie/logo resolution, hides transition console/debug
overlays by default, restores deck-guard speech and exposes town entrance names.
Compiler jobs default to available CPU capacity. Dev4 added the project-logo fade before that menu, title music and the selected
New Game opening track, maps the hatch surface and adds ship NPC body collision.
The disk indicator is optional and off by default. Optional streamed movie playback
precedes Jiub and supports Esc; see INTRO_VIDEO.md for source availability and tests. Dock/Census creation and the complete opening remain unfinished. The historical
state below describes preceding releases, not the complete current feature set.

The owner completed all 12 full game-data build stages with test-004 and
confirmed test-006 works on 28 September 2026. That v0.0.17 release included FS-UAE
autorun and the default `early_game_demo_start_1` town-center opening with
track 04. Final ROM-directory prompting and documentation updates follow that
confirmation; the engine is unchanged from test-006. Hosted CI is checked by
the owner when pushing the release commit. See [validation](VALIDATION-v0.0.17.md)
and [demo opening](EARLY_GAME_DEMO_START.md).

The published v0.0.16 release includes boot credits, a blue ordinary-water tint and
the 540 fog/draw default. See RELEASE-v0.0.16.md for the completed validation
record. The sections below preserve checkpoint-017 and consolidation history.
Created by FlyingFathead a.k.a. Horstator. Thanks to ChaosWhisperer.

## Project identity and build access, 28 September 2026

The owner selected **amiwind** as the repository name and
**https://github.com/FlyingFathead/amiwind** as the official project home.
This records the intended publication location; remote creation/publication
remains with the owner. The working README now identifies this URL.

Source 0.12.1.dev1 consolidates both public source components under one
`amiwind/` repository root. `engine/aga/` now contains authoritative native source;
the builder compiles an external copy instead of extracting and patching upstream.
Existing runtime C/header/QuakeC/preflight sources retain checkpoint-017 bytes;
a separate asset-free dry-run notice program has been added. Earlier
release ZIPs remain immutable. See REPOSITORY_LAYOUT.md for validation and paths.

The build tools now provide confirmed Ubuntu/Debian dependency installation, a
pinned optional SDK download, reference-version reporting, WSL/GOG discovery and
size/SHA-256 input checks. Outputs default to ignored out/. The asset-free CI
workflow compiles an engine and a public boot-notice HDF; see CI_DRY_RUN.md.
113 host tests, native compilation and a local notice-screen boot passed. Hosted
CI, clean installation and Windows/WSL full conversion remain untested.

Font/UI steering: prefer 16px or 14px Magic Cards with three ink shades plus
transparency. Use 12px only where space demands it; reject the monochrome 12px
trial. Match original Morrowind message/subtitle/dialogue box designs. The host
font preview is not an accepted final layout or native implementation. Detailed
choices and original input hashes are in UI_FONT_VARIANTS.md.

Windows 11 build inquiry: current full-build instructions and toolchain are
Linux-oriented. WSL2 with Ubuntu is the proposed first Windows-host route, not
yet validated. Native Windows needs build/path/dependency work, including the
hard-coded Linux font check and external cross-toolchain provisioning. The
Windows Morrowind installation supplies data files; Morrowind.exe is not executed
by the conversion path. Do not claim a tested Windows/WSL full build yet.

Latest validated runtime: bounded Seyda Neen exterior and separate prison-ship
interior, streaming18-track music selection, three idle exterior NPCs, Nord
unarmed hands, menu/console, noclip, scene picker, live fog/cull distance and FPS.
Checkpoint-017 repairs the lower ship hull flattened by blanket reduction; it
preserves structural groups while retaining reduction elsewhere. Exterior map
is byte-identical to checkpoint-016. This remains a proof of concept.

At the archived checkpoint-017, 97 host tests passed against the final engine source. Native validation uses
FS-UAE3.1.66, A1200/AGA, 68040/FPU/JIT/max speed, 2MiB Chip +16MiB Z3 Fast,
Kickstart3.1 A1200 revision40.68. Heap reservation9MiB. No stock-A1200 or physical
hardware performance claim. Buildings are resident; music streams.

See CHECKPOINT_017_VALIDATION.md for exact hashes, checks and limitations.
Development source ZIP and private playable ZIP are immutable. Public source
contains no game/ROM data; private recovery packages contain owner-supplied data.

## Current priority

Owner requested complete development recovery before moving sessions. That recovery backup is complete. The v0.0.16 release
updates build access, versioning, ordinary-water tint and the fog default. Next milestone is an opt-in reconstruction of the
opening sequence: audit original scripts/voice completion timing; implement the
first playable beat and dark bordered UI/subtitle/message boxes; evaluate an
optional converted Morrowind font. Original Fonts/*.fnt and *.tex are present.
At the preceding release there was no intro state machine, UI box implementation, converted original font,
Jiub/intro-guard actor or Census interior has yet been implemented.

Preserve existing readable/retro fonts, debug free-roam, scene links, hand paths,
ship method_001 and old checkpoints. New variants must be selectable and have a
rollback path. Never destructively replace an existing feature during experiments.

## Open issues and measured findings

- Roof/beam spikes and position-specific disappearing structures remain open.
  Native distance-cull on/off tests at two report poses produce identical scene
  crops, so the added fog-distance cutoff does not explain those sampled lines.
  Frustum/backface/BSP clipping and span depth ordering remain to investigate.
- Source triangles versus merged/split host geometry match at one nearby pose;
  a bounded serialized-BSP audit found no broken edge loops or reversed windings.
  This does not prove the whole converter/render path correct.
- Localized slowdown remains unassigned. Ship-only face suppression improved one
  short view trial from10.52 to12.44FPS; closer fog700→400 improved a different
  short comparison from11.46 to17.21FPS. Preserve camera/settings and do not
  treat these accelerated-emulator numbers as hardware benchmarks.
- Occasional music clicks/late updates remain. Underwater tint, exterior formation,
  deck holes and Silt Strider coverage remain open. Continuous lower-to-upper
  ship walking route and hatch open/closed state are not certified/implemented.
- NPC inventory/activity/dialogue, containers, full character generation, sky/day
  cycle, torches, combat, Balmora, Census interior and saves remain roadmap work.
- New small requests: move FPS to the left; add `dbg show fps` alias. Current
  `dbg fps on/off` works, but those two changes have not been made.

All recent owner coordinates and reusable LOD ideas are in SEYDA_NEEN_NEXT_STEPS.md.
OPTIMIZATION_HISTORY.md and the implementation journals preserve causes, trials
and known limitations. Correctness must accompany performance measurements.

## Final recovery handover update, 27 September 23:32–23:35 Helsinki

The latest chosen NEXT-build fog/culling default is **540**, superseding the450
proposal above. Current frozen dev2 still starts at700; live command:
`dbg fog distance 540`. Update config/runtime/menu reset/tests/docs together in
the next build, preserving the old packages and selectable distances.

New persistent rock/Silt Strider-port report: XYZ337 643 34, DEG304, P-16,
v0.0.15-dev2, image(20260927-203433).png. Owner screenshot shows a projecting
terrain/rock section with missing-looking lower geometry; exact source identity
and cause still require comparison. HUD reads28.4FPS in that one screenshot,
not a benchmark. Do not conflate the already-known omitted Silt Strider ACTI
with proof of this formation's geometry cause. Backup first; keep this open.

## 28 September 15:50 owner follow-up

The Silt Strider-port defect persists in v0.0.19 at XYZ260/417/30, DEG11, P-19;
the strider and driver are still absent. Track as AW-20260928-03 in [BUGS.md](BUGS.md).
The v0.0.20 maintenance work does not close this scene-conversion issue.


Latest dev3 maintenance also adds the two-line interaction layout (name in 12 px
Morrowind font, action in the console font), arrows/WASD choices, separate
fighting permission after hall acceptance, and persisted courtyard ring depletion.
The room audit reproduces94 unsupported old-map samples and restores all94 with
the original room section. General loot/icons, Fargoth return dialogue and status
effects are roadmap work, not completed gameplay.
