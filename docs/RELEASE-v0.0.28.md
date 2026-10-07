# v0.0.28 — Trees and Grass, Day and Night

**Stable v0.0.28 locally accepted within the declared image015 WinUAE scope — 4 October 2026. Hosted CI, tag and public publication remain pending.**
v0.0.27 remains the latest published release. VERSION is the maintained identity;
old rc1 images and captures retain their historical attribution.

## Prepared scope

- 19,984 unique original foliage placements: 19,787 sprite placements across 76
  shared types and 197 mesh placements, including 192 in Balmora. Retained scenery
  includes 37,960 rock placements and 816 joined giant mushrooms. Overlap copies
  are not extra unique placements.
- Default V3 ("extra stronk") red/gold sunset, purple twilight and blue hour,
  two original-cloud-derived layers and a moving sun. A subtle exterior world
  tone uses the existing fog lookup; interiors and overlays remain separate.
- One persistent clock, default-on automatic cycle, Boolean pause/resume aliases,
  exact/named time controls and T waits. Sun and clouds default on, with independent
  Boolean toggles; adjustable cloud speed defaults to `0.00333333333`.
- Eight-stage `dbg daycycle gallery` and four-stage `dbg nightgallery` tours.
  The night tour previews the current view, Masser, Secunda and overhead stars at
  23:00 on the saved date, keeping the current eye position. Both support `here`
  for a fixed view and `off`/Escape to leave, preserving saved time and player state.
- Compact locally converted original stars/nebula and Masser/Secunda phase tiles.
  AWN2 limits source-derived stars to one native pixel in dark gaps behind the
  nebula, clouds and complete moon discs. `dbg starsky` and `dbg nightsky` default
  on, with gentle cool-blue twinkle. Regional weather and precise lunar parity are deferred.
- Guard-torch runtime and original equipment/third-person pose conversion for
  supported Imperial/Hlaalu guards, default-on `guards_torch_cycle` and
  `dbg guardtorch on/off/auto`. Host checks and scoped image015 native guard, lighting and model-cache behavior passed. The measured reserve warning remains open.
- Bounded canonical Seyda terrain, actor support and inspection tools; wider-world
  terrain certification and unrestricted gameplay remain outside these checks.

## Current evidence and acceptance

The latest source gate, finalization011, passed at 17:45 EEST on 4 October 2026.
It ran 824 tests per host: Linux 820 passed / 4 skipped and Windows 732 passed /
92 skipped, with no failures or errors. Fresh actual Amiga cross-compiles on
Windows and Linux Docker used the same 206 runtime sources and produced identical
744,860-byte executables (SHA-256
`a5aa451e297b517cd0d2e072c4e5ccc4eb39bf09e93c67eed72586b55265955b`). The 1,096
frozen source files match across hosts, with no source drift. The target ABI was
measured in Linux Docker, not with a Windows size probe.

These gates include the full upper-sky star conversion, `dbg nightgallery`,
the ceiling-start arrival correction, the latest cloud-speed change and
64 KiB of music-only source read-ahead. Shared mixer timing, speech and
guard voices are unchanged. The current WinUAE listening report still notes
intermittent artifacts, mostly at load-ins and in heavy scenes. The audio issue
remains open; publication proceeds with this known limitation, with further
audio investigation deferred until after publication. See [WIN-05](journals/BUG_JOURNAL-v0.0.29.md#win-05-intermittent-winuae-background-music-snapping---investigation-open).
The compiler retains 86 warnings; these are successful builds, not warning-free
builds. The earlier 816-test/739,156-byte result is
superseded for this source. Compilation and host fixtures do not establish
native image appearance, gameplay or performance acceptance.

Image015 assembly uses the exact matching engine and passes 10,766 payload
readbacks plus three partition-ownership checks. The audit records 59 modeled
reserve warnings and no modeled hard allocation-ceiling failures. These are
estimates and file-verification results, not a production-memory pass. Earlier
native startup, restored town ground and clock checks apply to a preceding image.

Independent actual WinUAE acceptance of engine011/image015 passed within its
declared scope. Two fresh cold-cache sessions exercised Imperial and Hlaalu
guards: each admitted all three eligible actors with no frame/model skips or
evictions, and boundary checks showed torches on at 20:01/05:59 and off at
06:00/20:00. Bounded close captures confirmed subtle moving gold/ember particles.
Five pressure maps completed without crashes or renderer overflow. All eight day
and four night gallery stages were captured, independently caption-reviewed and
restored. The 137 fresh native captures were preserved, alongside image014's
historical captures and saves. All 10,766 image files and three partition
ownership checks passed. This is a scoped native pass, not all-map, unrestricted
world, or physical-hardware certification. The minimum logged peak clearance
was 1,812,304 bytes at sn012, 284,848 bytes below the unchanged 2 MiB safety
reference. That remains a reserve warning; the production memory gate did not
pass. Intermittent music artifacts remain an owner-deferred known issue, and no
clean-audio pass is claimed. Stable v0.0.28 is accepted locally within this
scope; hosted CI, tag and public publication remain pending the owner's Linux
publication step.

| Gate | Current status |
|---|---|
| Coherent 64-map Seyda terrain and actor host gates | Bounded 049/050/051 checks pass; complete target routes/contacts pending |
| Serialized canonical repeat | 2,129,800 placed polygons; zero further cuts, winding-preservation failures or area loss |
| Visible-ground winding repair | 442,861 LAND loops reversed across 64 maps; matched-camera WinUAE check restores textured ground |
| Actor identity/support | Bounded host results retained; independent native owner-map contacts pending |
| Combined source: full host suites and matching Amiga builds | Pass: finalization011 ran 824 tests per host (Linux 820/4 skipped; Windows 732/92 skipped) and produced identical 744,860-byte executables; target ABI gate passed in Linux Docker |
| Combined image assembly/readback/ownership | Image015 passes 10,766 payload readbacks and three partition checks; 59 modeled reserve warnings and no modeled hard-ceiling failures |
| Native startup, controls, travel, ground contacts, night/torch cost and lifecycle | Scoped image015 WinUAE native acceptance passed: cold guard admission/boundaries, visible particles, five pressure maps and session-stability checks; 1,812,304-byte minimum peak is below the 2 MiB safety reference, so the production memory gate did not pass |
| Fresh native V3/night captures and gallery GIF | 137 image015 native captures; all eight day and four night gallery stages caption-reviewed with restoration; 16 selected native stills and two GIFs prepared |
| Exact hosted CI, tag and publication | Pending owner Linux publication step; stable v0.0.28 is accepted locally within declared scope |

The pale ground in the earlier native test came from canonical LAND edge loops
ordered opposite to the renderer's convention. The 051 repair changes only the
signed surfedge ordering, retaining collision, materials and other BSP lumps.
A matched-camera diagnostic and the initial combined-engine town replay both
show restored textured ground. These bounded views do not certify every map or
route. See [the bug journal](BUG_JOURNAL.md).

The 050 correction re-clips actual float32 serialized coordinates in seven maps:
13 replacement faces add 1,776 bytes while collision, PVS and actor bindings remain
unchanged. The maximum measured standing-height error is 0.00015736 compiled
units. The 29 earlier boundary diagnostic probes outside mapped town coverage
remain historical diagnostics, not a demonstrated current shipping defect or a
target pass. No complete global-terrain certification follows from this batch.

## Stable emulator templates

The source kit includes [FS-UAE](../resources/emulators/AmiWind-v0.0.28-FS-UAE.fs-uae)
and [WinUAE](../resources/emulators/AmiWind-v0.0.28-WinUAE.uae) templates.
They preserve the accelerated reference hardware profile. Source templates do
not establish native image acceptance; historical rc1 templates remain intact.

## Output scope

Public output contains source, documentation and explicitly selected development
captures. Original/converted runtime assets and playable images are not distributed.
The reference profile remains A1200/AGA/PAL, 68040/FPU/JIT, 2 MiB Chip and 16 MiB Z3
Fast RAM. Physical-hardware performance, smooth frame rate and unrestricted
playthrough are not claimed.

See [historical rc1 evidence](RELEASE-v0.0.28-rc1.md), [project state](PROJECT_STATE.md),
[sky guide](DAY_NIGHT_AND_SKY.md), [capture attribution](GAMEPLAY_MEDIA.md) and
[canonical terrain status](CANONICAL_TERRAIN_CULLING.md).
