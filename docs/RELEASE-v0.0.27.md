# AmiWind v0.0.27 — Rocks, Mushrooms, and Then Some

> **Published stable release — 3 October 2026.**
> [AmiWind v0.0.27 — Rocks, Mushrooms, and Then Some](https://github.com/FlyingFathead/amiwind/releases/tag/v0.0.27)
> builds on the repaired rc5 candidate. Publication, hosted CI and release-asset
> download verification are complete. The runtime limits below remain open.

## Scope and changes

### Rocks, giant mushrooms and terrain handoffs

The v0.0.27 work adds authored exterior rock formations and giant mushrooms to
the world build while excluding small collectible mushrooms. The current source
inventory records 37,960 exterior rock placements and 816 giant mushrooms across
2,526 world regions. Placement transforms, source textures and required collision
are retained. Rc2 corrected the reduced giant-mushroom caps by preserving their
joined material sections and original UVs; the owner accepted those closed caps
in WinUAE. Rc3 added a LAND apron around the Seyda Neen handoff and preserves held
controls during automatic cell/sub-cell changes. See [What are rocks?](WHAT_ARE_ROCKS.md)
and [cell-changing behavior](CELL_CHANGING.md).

The current normal conversion has generated a bounded 64-region Seyda Neen map
set; its 67 saved-ABI map estimates pass, with a smallest post-reserve margin of
406,512 bytes. A separate bounded Balmora layout also passes its 65-entry saved-
ABI estimate and covers 1,488 of 1,488 source placements. Its worst entry has
135,952 bytes of post-reserve margin. These are static estimates, not measured
runtime allocation or proof of the complete image. The 5 MiB figure is a planning
target; the 6 MiB modeled BSP ceiling, 3 MiB non-map allowance and 2 MiB safety
reserve remain unchanged. Transition, seam, collision, content and target-playtest
acceptance are still pending. The final stable private image is assembled and both HDF files passed filesystem readback; runtime and target acceptance remain open.

### Loading diagnostics and memory policy

The rc3 playtest exposed a Seyda Neen heap allocation failure. Rc4 source work
uses direct input-to-resident loading for visibility, lighting, entities and
clipnodes, avoiding avoidable temporary copies while preserving collision data.
The build reports target-ABI estimates and the remaining growth margin in its
`build.json` receipt; target runtime measurements remain pending. More HDF capacity
does not increase engine heap. See the [memory allocation policy](MEMORY_ALLOCATION.md),
[heap watcher receipts and lifecycle requirements](HEAP_WATCHER.md), and the
[bug journal](BUG_JOURNAL.md). The original crash remains open until the exact
packaged route passes owner target lifecycle playtesting. The host-side candidate repair and static build gates passed; the original crash is not yet target-verified.

Rc4 also adds versioned FS-UAE and WinUAE configuration generation from the
verified build HDF list. Windows configuration tests pass 11/11. Earlier native
Windows runner tests recorded platform-specific symlink and POSIX-stub errors;
native Windows C-fixture execution is now explicitly skipped under the
interpreter-first policy, not counted as a pass. The full Linux Docker suite and
asset-free compile gate passed for the repaired source state (see the dated
validation record below). Exact-commit hosted CI has since passed for published
v0.0.27. Actual FS-UAE multi-drive gameplay remains a separate pending check.

The rc4 fatal-error report includes the version, error cause, log path/result and
restart guidance. Source behavior and logging checks are documented separately;
a successful engine build alone does not establish target fatal-exit acceptance.

### Rc5 repairs and remaining target validation

The rc5 source restores settlement markers in both Debug and In-Game modes and
uses a readable selected-button treatment. Nine focused source checks passed; the matching engine compiled and the private
HDFs passed readback. The repaired Linux world-UI fixture subsequently passed in
the complete 558-test Docker suite. Target
confirmation of marker visibility, button states and the In-Game heading arrow
remains pending. In-Game is still a terrain-overview prototype, not the complete
original-game map.

Automatic region crossings now support the archived aw_region_loading_delay
setting: two seconds by default and zero for immediate presentation. Startup and
explicit travel remain immediate. The delay begins at the next safe loading
checkpoint after blocking reads; it does not interrupt disk operations or claim
a performance improvement.

The private playable package includes all 18 catalogued OST tracks and 124 alias rows. The new
manual dbg ost play command accepts numeric IDs or original filename stems.
Existing playback and mixer routines are unchanged. Target playback verification
remains open.
Conversion and runtime integration of the complete 17-video catalogue remain
later work; the existing opening logo and intro clips remain supported. See the
[bug journal](BUG_JOURNAL.md) for the two corrected retry-helper incidents and
their preserved safety behavior.
## Known limitations and deferred work

- The repaired rc5 candidate passed optimizer, actor/contact and static heap
  gates for all 2,717 maps. Stable v0.0.27 private assembly retained those maps,
  replaced the engine/boot checker and passed both HDF filesystem readbacks.
  Cold/warm lifecycle and gameplay measurements remain open follow-up work;
  publication does not establish target acceptance.
- No target heap lifecycle trace, FPS improvement or complete playthrough is
  claimed. Static map estimates are not runtime measurements.
- Town transitions, seams, collision, held input and player/actor/equipment state
  require verification on the exact final package, including both directions and
  cold/warm loads.
- The rc5 map-panel correction is compiled and packaged, but target verification
  remains pending. In-Game still uses a terrain overview; complete world/local map
  content and full interaction parity remain future work.
- Full condition-aware voiced dialogue is not implemented. The generic HELLO
  audition is limited; original event conditions and ordered line selection
  remain required work. The private playable package includes all 18 catalogued OST tracks and
  124 alias rows, plus a manual number-or-filename-stem command. Target playback
  verification remains pending. The existing opening logo and intro clips remain supported; registration and
  playback for the 17 catalogued videos, including expansion content, remain
  future work. Preserve existing music playback and mixer behavior.
- Building-geometry A/B profiling, broader visual-coherence work, full-VIS
  comparison, LOD and later topology content remain follow-up work. Vivec stays
  inactive and is excluded from this playtest.

Original game assets, ROMs, converted proprietary media and playable HDFs are not
included in the public source package. Users supply their own legally obtained
game files and Kickstart ROM. This is a GPL-licensed source/tooling project.

## Publication and source validation — 3 October 2026

[Stable v0.0.27 is published](https://github.com/FlyingFathead/amiwind/releases/tag/v0.0.27)
at commit `8da838784efa619a12da39d29095be4c0fe6e44d`. Official `main` and the
peeled `v0.0.27` tag were independently verified at that commit. The annotated
tag object is `435ed2574c85128911999c08379a4650e9b1e471`.

The publisher recorded all four jobs passing in
[CI run 37113138642](https://github.com/FlyingFathead/amiwind/actions/runs/37113138642):
Docker builder, Linux launcher parity, Windows launcher parity, and the
source/asset-free build. The Linux publisher also completed release creation
and downloaded-asset verification. The published public source ZIP has SHA-256
`3b2b2ea9a9244e589cda11673027c7963bb565c29b7c5b9fc7dcf4152efab493`.
The tag and published archive are immutable; later documentation corrections
belong on the development branch.

Before publication, the exact repaired source package passed the full Linux
suite inside Docker: 558 tests reported OK with 3 skips. Its matching asset-free
Amiga build exited 0 and produced both emulator configurations. The corrected
world-UI and movie fixtures provide their required linked dependencies. Native
Windows C-fixture execution remains explicitly skipped under the interpreter-
first policy; a Linux pass is not a full native Windows suite pass.

Source/build, publication and asset-download checks are complete for that
release. They do not replace target playtesting, runtime memory measurements,
or the open gameplay checks above. Playtest packages remain private.
