# Development history

## v0.0.21-dev5 — GOG TTF preference and Steam font fallback, 28 September 2026

- Prefer the GOG GOTY `BookArt/*.ttf` font sources for host-side AmiWind
  rasterization when present. GOG GOTY remains the recommended source edition.
- Support Steam GOTY's normal lack of loose BookArt TTFs by falling back to the
  matching Bethesda `Fonts/*.fnt` + `.tex` pairs instead of aborting stage 13.
- Report every preferred TTF as found/not found, the selected source per font
  family, the GOG recommendation/link, and the possible quality difference.
- Convert Magic Cards, Century Gothic, Century Gothic Big and Daedric families at
  16/14/12 px. If a preferred TTF exceeds native AWF limits, fall back safely to
  its bitmap family rather than clipping or corrupting glyphs.
- Add Steam-style and GOG-style font-source regression tests. No gameplay change
  is claimed relative to dev4.

See RELEASE-v0.0.21-dev5.md for validation and the remaining real-install test.

## v0.0.21-dev4 — evening world-mapping checkpoint, 28 September 2026

- Record Horstator's optional polygonal POI-region fallback if cell streaming
  cannot meet the Amiga's measured budgets, starting with Seyda Neen.
- Preserve both conversion strategies, original cell semantics and stable
  reference state; plan concealed crossings, loading feedback and memory checks.
- Package the updated diary, world-mapping plan and roadmap with a native rebuild
  carrying the dev4 identity. Gameplay and converted assets remain as in dev3.
  Region swapping and doorway simplification are not implemented by this release.

See RELEASE-v0.0.21-dev4.md for validation and save compatibility.

## v0.0.21-dev3 — opening maintenance and interaction hints, 28 September 2026

- Two-line lower-right NPC hints: 12 px Morrowind name and current console-font
  action (`npc_interaction_layout_template_001`); matching opening aim/use query.
- Arrows/WASD menu choices; fighting unlocked by hall paper acceptance rather
  than final release; persistent courtyard ring depletion and atomic pickup.
- Compiled standing-hull room audit for support, connected steps and fall edges.


- Restore the scripted Census room floor/walls; correct dock proximity anchors.
- Use black/gray reading text on white and retain more Census wall-art detail.
- Record playtest bugs with fixed Y/N, version and verification status.

Highlight New Game when opening its confirmation dialog, so Enter starts the
intro immediately. Esc and explicit Cancel return to the menu. The hidden mouse
position starts over the selected button as well. See RELEASE-v0.0.21-dev3.md.

## v0.0.21-dev2 — opening barrier correction, 28 September 2026

Correct compound rotations of the 22 collision-only opening references. Preserve
the original positions, dimensions and CharGenState lifetime. Add converter and
state regression coverage, an indexed journal incident, and persistent opening
access/research priorities. See RELEASE-v0.0.21-dev2.md for exact validation
coverage and pending owner acceptance.

## Portable launcher helper — 28 September 2026

Add `tools/AmiWind-FS-UAE-launcher.py` for existing local images: numeric release
and development-version selection, date tie-breaking, saved ROM/settings,
non-blocking ROM checksum warnings and automatic FS-UAE configuration with
backups. Enter accepts the suggested image; `--yes` launches immediately.
This host-tool follow-up leaves runtime v0.0.20 unchanged. See FS-UAE-LAUNCHER.md.

## v0.0.20 — 28 September 2026

Prison-ship hull ambience reduced by 5 dB per static mixer channel; audio files
and other uses remain unchanged. Enabling debug overlays also enables coordinates.
Corrected the current FS-UAE 24-bit-addressing option and two compiler-detected
array-row bounds violations. Recorded intermittent ship-exit/menu freezes and
the persistent Silt Strider-port report; their causes remain unresolved.
See RELEASE-v0.0.20.md and BUGS.md.

## v0.0.19 — 28 September 2026

Public release of the accumulated 0.0.18 checkpoints: intro/movie, UI/menus,
loading screens, entrance prompts and parallel builds.
Routine soundtrack notices now obey the debug-overlay switch at their source.
Music events still log privately, and explicit status queries still work.
See RELEASE-v0.0.19.md.

## v0.0.18-dev5 — 28 September 2026

Original main-menu art with bottom-right version, centered Esc menu and New Game
confirmation, larger logo/movie frames and readable private title cards. Original
loading screens replace transition-console flashes by default; debug overlays
default off. Deck guard greeting/reminder, visible town entrance names and safe
missing-interior feedback, private source layout reference, automatic compiler
jobs with explicit overrides. See RELEASE-v0.0.18-dev5.md.

## v0.0.18-dev4 — 28 September 2026

Project-logo startup fade and upper-menu/README branding, main-menu title music,
reset of the selected New Game track,
optional streamed prophecy movie with Esc, mapped hatch activation bounds,
ship NPC body collision and escort waiting, default-off disk indicator,
actor-cache staging correction and three-line loading credits. See
RELEASE-v0.0.18-dev4.md for validation and unfinished work.

## v0.0.18-dev3 — 28 September 2026

Original main-menu background with a separate palette, distinct return-to-game
and main-menu flows, disabled Load, and New Game into the ship. Conservative
animated alias bounds permit rejecting off-screen actors before disk-cache
loads. See RELEASE-v0.0.18-dev3.md for verification and remaining work.

## v0.0.18-dev2 — 28 September 2026

First ship-script adapter, original introductory voices/name entry, talking and
blinking head poses, female appearances, path-grid escort movement, ship ambience
and darker hold lighting. Distinct HUD colors, optional outer frame off by default,
New Game entry and integrated private conversion. See RELEASE-v0.0.18-dev2.md for
verification and remaining dock/Census work. Journal filename corrected.

## v0.0.18-dev1 — 28 September 2026

Original proportional Magic Cards UI, private original border/bar conversion,
black lower-strip sliding subtitles, font selection with preserved console, and
native font/clipping validation. See RELEASE-v0.0.18-dev1.md for the exact scope;
this checkpoint does not claim the completed intro or gameplay resource systems.

## v0.0.17 — 28 September 2026

One-command confirmed dependency setup and continuation, isolated fresh tools,
bounded game-directory discovery, actionable download failures, corrected tool
probes, QuakeC preflight, and one authoritative VERSION file. CI exercises the
same installer with public tools and an asset-free image. Test-004 completed the
owner's full game-data build; the owner subsequently confirmed test-006 works.
See [validation scope](VALIDATION-v0.0.17.md) and [release notes](RELEASE-v0.0.17.md).

- Optional FS-UAE autorun checks the emulator and owned ROM before building,
  accepts a ROM file or directory and prompts if none is selected, and fills both paths in the documented preset.
- `early_game_demo_start_1` is enabled by default: town-center spawn in Seyda
  Neen, track 04 first, then the exploration shuffle. Ship-first startup remains
  selectable; interior transitions do not reset the demo opening.

## v0.0.16

- First consolidated repository release under FlyingFathead/amiwind.
- Unify source/runtime/image/archive versions and reject mismatched native strings.
- Add the requested boot credits and project address.
- Change ordinary underwater tint from the inherited brown shift to blue; preserve independent damage flashes.
- Set exterior fog/draw default and menu reset to 540; retain other distances.
- Carry forward guided dependency/input checks, WSL/GOG discovery, asset-free CI and documentation screenshots.
- Provide matching full source, incremental source and private playable packages.
- Opening sequence and original-font UI integration remain unfinished.

See RELEASE-v0.0.16.md for validation and patch-base details.

## 0.12.1.dev1 / runtime source still v0.0.15-dev2

- Consolidate the public checkout into one `amiwind/` root.
- Include the complete selected AGA engine under `engine/aga/`.
- Build the checked-in engine directly in an external work directory.
- Use bundled native source for host regression checks by default.
- Rename host distribution/release root to `amiwind`; retain legacy workspace compatibility.
- Record official project URL and accepted font/UI direction.
- Add confirmed host/optional SDK setup, version comparison and complete reference-file hashing.
- Detect WSL and offer a matching default GOG installation; accept any chosen install root.
- Default build output to ignored out/ and expand accidental-game-file ignore rules.
- Add asset-free GitHub Actions compilation and a versioned boot-notice HDF.
- Add a top-level project-state summary and five uniformly cropped documentation screenshots.
- No water, fog, gameplay or original-font integration is claimed.

See REPOSITORY_LAYOUT.md for migration and verification.

## 0.12.0.dev2 / runtime v0.0.15-dev2

- Preserve structural ship-interior source surfaces and UVs to repair hull intrusion.
- Add a scene-picker popup via `dbg scene change`, retaining direct commands.
- Add live fog/draw-distance commands and Options → Graphics slider; replace
  floating-point depth-table rebuilds with integer threshold bands.
- Add default-off FPS HUD using existing profiler timing.
- Add a private base-master NPC/door/container audit and synthetic deletion tests.
- Preserve exterior method_001 and record the complete owner follow-up list.
- Keep underwater tint, audio pops, exterior formation and performance reports open.

See CHECKPOINT_017_VALIDATION.md for measured scope and remaining limits.

## 0.12.0.dev1 / runtime v0.0.15-dev1

- Add the dim prison-ship interior and source-derived hatch links; one resident scene.
- Preserve music identity across map changes and validate arrival floors.
- Convert hollow shell collision as thin prisms; remove same-side recursive hull descent.
- Compact console default, fullscreen toggle, page scrollback, overlay alias.
- Calibrate Nord eye height independently of collision; add DEG and pitch to coordinates.
- Keep 3D hands and add an experimental compile-time sprite bake/draw path.
- Record repeatable conversion recipes and private input/tool/source fingerprints.

See CHECKPOINT_016_VALIDATION.md for evidence, failures and open reports.

## 0.11.0.dev1 / runtime v0.0.14-dev1

- Convert the complete arrival-ship assembly, including its ACTI hull.
- Reduce ship exterior geometry/material textures on the host; use separate
  authored collision geometry instead of visual detail for the physical hull.
- Add solid configurable console background and space-separated debug aliases.
- Add a readable original bitmap font and retain the previous font as `retro`.
- Record ship departure/source behavior, dim opening-interior priorities, NPC
  collision work, and a planned day/night/sky interface with frozen-time tests.

See CHECKPOINT_015_VALIDATION.md for measured scope and remaining limits.

## 0.10.0.dev1 / runtime v0.0.13-dev1

- Decode BSP face plane indices as unsigned and reject out-of-range indices.
- Increase preallocated render buffers after measuring dock-view overflow.
- Bake Nord hands and authored idle/draw/lower/punch clips locally.
- Add Escape menu, disabled future options and confirmed Exit.
- Add coordinate strip, debug master/aliases and default-off RAM indicator.
- Add pitch-directed noclip flight, numbered safe recall point 0 and exit restart hint.
- Extend the temporary sea backdrop; add its independent visibility toggle.
- Export ordered private voice records with original conditions and scripts.
- Preserve per-version user confirmations and remaining visibility reports.

See CHECKPOINT_014_VALIDATION.md for native scope and remaining limits.

## 0.9.0.dev2 / runtime v0.0.12-dev2

- Bound expanded architectural hulls to remove distant solid spikes.
- Add `aw_blockers` and NPC facing/greeting diagnostics.
- Turn nearby NPCs toward the player; add bounded proximity Hello/reset.
- Replace the compound E binding so console key releases cannot trigger speech.
- Preserve original ordered wander settings for the next walking milestone.
- Add the owner FS-UAE guide and versioned FS-UAE/WinUAE presets to both packages.
- Retain existing Quake bob, stairs, music and rendering implementation.

See CHECKPOINT_013_VALIDATION.md for evidence and remaining limits.

## 0.9.0.dev1 / runtime v0.0.12-dev1

- Bake dressed Fargoth and two guards, eight idle poses and original voice auditions.
- Add nearby E interaction with a cooldown; retain nonblocking actor placement.
- Match player/world collision to base humanoid bounds; fix ground support and stairs.
- Preserve Quake camera bob and existing music/door renderer fixes.
- Add native stair/actor evidence, host tests and a matching WinUAE preset.
- Track Nord first-person hands and punching separately from later combat logic.

See CHECKPOINT_012_VALIDATION.md for scope, limits and hashes.

## 0.8.3.dev4 / runtime v0.0.11-dev4

- Reproduce the fresh-boot movement lock before using diagnostic recovery.
- Find a grounded standing-hull spawn with short exits in all four directions.
- Share spawn validation with recovery; preserve the old pose on failure.
- Retain dev3 rendering, world assets, music and filesystem fixes unchanged.
- Save Fargoth/guard outfit, skeleton and dialogue research for the NPC milestone.

See CHECKPOINT_011_VALIDATION.md for the fresh native movement evidence.

## 0.8.3.dev3 / runtime v0.0.11-dev3

- Correct legacy root-block metadata that made filesystem revalidation fail.
- Rotate collision with buildings and preserve the nearest floor hit when
  another collider starts overlapped; fully blocked moves keep their original
  position. Use the standard standing hull width.
- Add F10/grave console, noclip/tcl, safe recovery and reproducible diagnostics.
- Consume mouse input safely while the console is open; copy event data before
  returning its OS message. Escape closes the console before quitting the game.
- Match far culling to fog depth, retain partial bounds and truncated PVS lists.
- Include window attachments previously omitted from the mesh conversion.
- Tighten nearby surface-depth ordering; keep old tolerance for comparison.

See CHECKPOINT_010_VALIDATION.md for verified scope and remaining limitations.


- Shared BSP meshes with source UVs, transform variants and separate multipart
  collision; 136 placements / 52 variants fit the existing 8 MiB hunk.
- Corrected surface pool exhaustion, depth-pair writes, rotated clipping and
  degenerate texture extents. Section-wise BSP input lowers temporary memory.
- Fixed native track00 filename regression, title filtering, shuffle/history
  controls and bounded PCM refills; full distinct native song completions logged.
- Fixed 32 KiB Chip leak on shutdown and false contiguous-memory rejection after
  quitting. `amiwind` relaunch and hardware checks passed twice.
- Guided Linux build, restored credits/notices and versioned presets under
  resources/emulators. 51 host tests, guided build and HDF readback passed.
- Startup audio deadlines, terrain/mesh joins and later gameplay remain open.
  See [checkpoint-009](CHECKPOINT_009_VALIDATION.md) for exact scope and counters.

# Development source 0.8.3.dev1 / runtime v0.0.11-dev1

- Guided Linux build, restored README credits/notices, versioned public WinUAE preset.
- Music title filtering, history controls, bounded prefetch and transition diagnostics.
- Renderer overflow counters; geometry repair still experimental.
- 47 host tests passed; full guided HDF build/readback passed. Native acceptance pending.
- See [development record](DEVELOPMENT_011.md); v0.0.10 remains the latest released playable checkpoint.

# Runtime v0.0.10 / source 0.8.2 — 27 September 2026

- Reproduced the reported 80000027 failure with 4 MiB Fast RAM.
- Added a small 68000 preflight before the engine: OS, CPU/FPU, AGA, free and contiguous memory checks.
- Replaced the large malloc request with checked, aligned Exec Fast-memory allocation and matching cleanup.
- Added current WinUAE setup guidance, corrected owner config and explicit 2 MiB Chip / 16 MiB Fast reference.
- Scene, textures and all 18 music streams remain byte-identical to checkpoint-007.
- Owner reports v0.0.9 boots in WinUAE after complete-ROM selection, and that selecting maximum CPU speed resolved the slow/glitching run; corrected config preserves that setting. No new hardware-performance claim.

# Runtime v0.0.9 / source 0.8.1 — 27 September 2026

- Fixed the missing icon.library requester on bare-ROM boot by removing unused
  Workbench tooltype/icon handling and desktop close/reopen code.
- Removed the explicit icon.library open from the experimental CLIB2 adapter too.
- Added a linked-Hunk executable gate at engine build and image assembly;
  icon.library/workbench.library references now fail packaging.
- Boot banner, HUD and Amiga executable version identify v0.0.9.
- Kept the checkpoint-006 world, textures and audio byte-identical. Only the
  native executable changes in the filesystem payload.
- Added startup regression tests and separate 3.1/3.1.4 ROM validation records.

# Runtime v0.0.8 / source 0.8.0 — 27 September 2026

- First AGA HDF checkpoint: bounded walkable Seyda Neen, static BSP proxies,
  baked facade textures, foliage sprites, palette fog and distance controls.
- Independent C2P, GPL C spans, standalone content initialization and original HUD.
- Full installed OST on disk, stereo streaming, natural song transitions and
  no-adjacent-repeat bags; three late mixer updates remain a known test issue.
- Native frame/stage/memory/music profiles and matched-run regression comparison.
- Pinned reproducible runtime patch plus complete separate corresponding source.
- README credits and community thanks; optimization history preserves failed trials.

Earlier checkpoint notes follow unchanged.

---

# Changelog

## 0.7.0 source / AmiWind v0.0.6 checkpoint-005

- Adopt AmiWind as the working title; generate the versioned loading banner.
- Deduplicate identical title/exploration music by converted PCM hash. Add
  exploration/battle shuffled bags with no immediate repeat, ordered F6/F7
  audition, F8 group audition and bounded native track-open diagnostics.
- Preserve complete songs, stereo DMA buffers and the tested async4k scheduler.
- Export static NIF geometry/materials/textures and placed bounds into a private
  indexed archive; add host turntables, cache accounting and packet validation.
- Retain door names/destinations for later activation/interior work.
- Document a separate expanded-Amiga renderer option, OpenMW/Quake translation
  boundaries, GPL requirements and credits. No external engine code is bundled.
- Native scenery and game mechanics remain pending; this build still renders
  the existing A500 terrain scene.


## 0.6.0 source / demo v0.0.5 checkpoint-004

- Add native frame/refill histograms, reproducible fixed-scene benchmarks,
  provenance checks and profile decoding/comparison tools.
- Compare blocking 16 KiB, async 16 KiB, async 8 KiB and async 4 KiB reads;
  choose async4k with cooperative audio service during long render passes,
  retaining the same 48 KiB queue.
- Pack full music files into three 32 MiB OFS partitions in one RDB HDF, with
  volume-qualified music paths and persistent native profile output.
- Verify native write/readback, missing/truncated-file recovery, movement,
  playlist transitions and return to DOS on the 1 MiB KS 1.3 baseline.
- Adopt GPL-3.0-only for project source. Retain external game/ROM separation,
  original purchase links and an explicit licence-compliant OpenMW baker option.
- Add storage/API limits, source studies for Doom/DoomAttack/AmiQuake, and
  measured next-step decisions. Renderer/scenery still matches checkpoint-002.

## 0.5.0 source / demo v0.0.4 checkpoint-003

- Convert all installed base-game music files, preserving complete tracks.
- Stream stereo PCM from a 64 MiB HDD image through 48 KiB of Chip buffers.
- Keep OS input/disk/audio services active; queue audio.device requests.
- Add automatic playlist advance/wrap and F6/F7 track selection.
- Report disk read count, maximum latency, starvations and read errors.
- Save the measured 7.1429 fps streaming baseline before refill optimization.
- Document storage tiers, raw-archive options and the capacity/performance distinction.
- Preserve separate, checked public source and private runtime packages.

## 0.4.0 source / demo v0.0.3 checkpoint-002

- Add a filled 97x97 heightfield with near-to-far column occlusion.
- Bake coarse surface colours from 19 original terrain textures.
- Add projection/row lookup tables; record 10.6857 fps on a short dense-fog route.
- Default to dense fog; keys 1/2/3 select distance and Tab retains wireframe.
- Use the blitter for long vertical spans and avoid a second frame wait.
- Start the terrain camera ashore; retain WASD, mouse and the original audio.
- Print presented-frame counts/timing on exit for performance comparisons.
- Rename boot images to MorrowindDemo-v0.0.3.hdf/adf and the executable to
  MorrowindDemo. Keep prior checkpoint packages immutable.

## 0.3.0 source / opening and terrain walk v0.0.2

- Add a bounded 33x33 wireframe view of original Seyda Neen terrain on the 68000.
- Add keyboard decoding, WASD, left Shift, mouse yaw/pitch, Enter and Escape.
- Use fixed-point projection, time-based movement and a blitter HUD copy into
  double-buffered one-plane screens; retain the opening stills and PCM playback.
- Record 1 MiB A500 emulator validation, ROM hashes and WinUAE setup guidance.
- Keep HDF as the development default and ADF as a boot fallback. No textures,
  NPC gameplay, collision or disk streaming are implemented in the walk.

## 0.2.0 source / opening v0.0.1

- Add a native 68000/OCS opening vignette, stereo PCM loop and centred voice cue.
- Add external OpenMW still capture and 16-colour planar/PCM build tools.
- Generate and read back bootable OFS ADF and 4 MiB HDF images.
- Validate A500/1 MiB/KS1.3 boot, scene change and DOS restoration; record ROM SHA-256.
- Keep all game-derived assets and the optional private ROM out of source releases.
- Free movement is the next requested renderer milestone, not part of this vignette.

## 0.1.3 — 27 September 2026

- Specified OpenMW itself as the intended host character-rendering backend.
- Documented capture integration work and the verified engine licence reference.

## 0.1.2 — 27 September 2026

- Documented the host-side reduce/bake/map/pack pipeline and final image assembly.
- Distinguished implemented terrain conversion from the planned native build.

## 0.1.1 — 27 September 2026

- Added humanoid body/appearance template design configuration.
- Separated body rig, equipment, combat style and animation state in the design.
- Kept the previously packaged source version immutable.

## 0.1.0 — 27 September 2026

- Created the named proof-of-concept repository from the initial extraction tools.
- Added the user-supplied game-folder setup and external-workspace conversion flow.
- Added input inventory, terrain audit, packet verification and optional PC previews.
- Added an allocation-free portable C terrain reader and cross-language checks.
- Enforced external original/derived-data paths and explicit source packaging.
- Added synthetic workflow tests and immutable, validated source archives.
- Documented fan-tribute status, original-game requirement and GOG/Steam links.
- Added a separate owner-only development bundle with external game data.
- Recorded stereo music/channel-sharing and character sprite pipeline proposals.
