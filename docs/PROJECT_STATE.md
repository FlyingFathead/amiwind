# Current project state — 28 September 2026

**Current development target: AmiWind v0.0.21-dev5.**

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
