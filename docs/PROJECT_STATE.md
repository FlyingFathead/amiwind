# Current project state — 28 September 2026

**Current target: AmiWind v0.0.16, one version for source and runtime.**

The consolidated release includes boot credits, a blue ordinary-water tint and
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
No new intro state machine, UI box implementation, converted original font,
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
