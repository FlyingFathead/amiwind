# Bug journal

## Required incident record

Always document every bug, issue and regression with:

1. **What and where:** symptoms, full affected version/build and environment, location or subsystem,
   reproduction steps and impact.
2. **Cause:** the established failure mechanism and introducing update/change.
   Record the introducing version/change when known. State explicitly when
   diagnosis or the first introducing version is unknown or suspected.
3. **Fix:** the actual correction, any temporary mitigation, regression coverage,
   validation results and remaining limits. Name the repair candidate version
   and verified fixed version separately. Unverified corrections remain open;
   use pending for the fixed version until acceptance is established.

Update the relevant subsystem guide and current release state when needed.
A passing retry or estimate alone does not close a confirmed incident.

## Producer's rule: mitigation is NOT a fix

Mitigation is a bandage. Record workarounds and partial corrections separately
from the actual verified fix. Do not close a bug because it can be avoided or
because one contributing allocation was removed. Every report must identify
(1) version, bug, location and circumstances; (2) how to replicate; (3) how to
fix, with evidence and verified fixed version. Unknown/pending facts stay explicit.

Current release blocker: [CRASH-01 full heap report](HEAP_CRASH_v0.0.27-rc3.md).
The assembled candidate below is historical build evidence; its later owner
playtest failed the Jiub-to-Seyda load. Rc3 is not release-ready.

## v0.0.27-rc3: terrain and held-input candidate assembled

Seyda Neen real-ground apron/shared world sampling and automatic-transition
held-input preservation are assembled. The rc3 engine, strict actor contact,
full gallery, filesystem readbacks, HDF checksums and emulator mount lists
passed. Actual outer subdivision core/coverage records were checked against
the runtime contract. Owner terrain/Shift/Ctrl/focus and character-state
playtesting remains pending. See [rc3 notes](RELEASE-v0.0.27-rc3.md) and the
[growing cell-change checklist](CELL_CHANGING.md).


## v0.0.27-rc2: Rocks and Mushrooms - mushroom correction accepted; town handoff open

This candidate separates the mushroom seam correction and `dbg map tp` alias
from the original rc1 playtest. All five mushroom models retain exact source
geometry and UVs on joined sections. All 2,526 corrected world regions passed
existing storage, face and collision limits in 303.469 seconds. New image assembly, strict actor contact (zero unresolved), full gallery,
filesystem readback, independent HDF hashes and both configuration disk lists
passed. The owner accepted the corrected mushroom caps in the rc2 WinUAE
playtest. The Seyda Neen terrain handover remains a release blocker.

## INPUT-01: held flight modifiers reset on cell changes - rc3 correction awaiting playtest

The owner reports held Ctrl/Shift noclip speed modifiers resetting when a cell
or sub-cell loads. Release and press again is a temporary workaround. Audit
held input and persistent gameplay state separately from coordinate rebasing;
future NPC pursuit must continue across residency boundaries. The rc3 scene loader retains held input at automatic crossings; doors and
teleports retain deliberate clearing. The real transition harness passes in
both variants and checks health, hands, torch, noclip, velocity and view state.
Owner Shift/Ctrl release/focus playtesting remains pending. Pursuit is not
implemented by this correction. See [cell changing](CELL_CHANGING.md).

## GEO-02: Seyda Neen ground disappears before the world handoff

The owner reproduced a sharp landscape change near the eastern town boundary
in rc2. The town remains resident to local X=1600, but its converted ground ends
at X=1664, leaving only 64 units of landscape ahead of a 540-unit draw distance.
The world map then supplies terrain that the town never rendered. The town and
world also used different coarse material selection and shoreline sampling.

Correction in progress: retain the town handoff and FPS subdivision cores,
provide a 768-unit authored LAND apron, and share world terrain sampling,
triangulation and material selection outside the detailed port approach.
Extend subdivision render coverage into the apron. Rebuild and boundary
playtest are required; no emulator acceptance is claimed yet.

## GEO-01: giant mushroom cap gaps after material-wise reduction - 2 October 2026

Symptoms: repeated open cap rims in Ascadian Isles during the local v0.0.27-rc1
playtest. All five giant-mushroom models were checked against exported original
geometry. Their material sections share source positions; independent reduction
moves or removes these joining vertices (parasol rim displacement up to roughly
199 source units). This is not evidence of a missing filler texture.

Correction: mushroom profiles preserve material sections that share source
vertices, including their original UVs. Rock reduction is unchanged. A synthetic
shared-rim regression checks exact geometry and UV retention. This conservative
correction increases mushroom triangles. Rebuilt BSP budget checks passed, and
the owner accepted the closed caps in the rc2 WinUAE playtest. Boundary-constrained
reduction remains a possible future optimization.

## v0.0.27-rc1: Rocks and Mushrooms - local playtest checkpoint

The complete world overlay covers 37,960 original exterior rock references and
816 giant-mushroom references across 2,526 retained world regions. Original
placements, transformed collision and original texture sources are used; visual
meshes and textures are reduced for the renderer. Small collectible mushrooms
are excluded. Town sub-cell divisions remain deliberate FPS controls.

Local assembly passed strict actor contact with zero unresolved cases, the
required 2,935-record / 3,551-model NPC gallery, complete filesystem readback,
and independent HDF checksum checks. Storage uses two simultaneously mounted
HDFs (approximately 3.75 GiB and 1 GiB); it is not disk swapping.

Owner playtesting reports rock geometry looks reasonable, Red Mountain gains
its missing formations, and giant mushrooms are visibly rendering in the
Ascadian Isles (owner screenshot confirmation). Rock texture
correctness is not yet accepted. This does not establish complete town coverage,
Linux/FS-UAE gameplay acceptance, real-hardware performance, or release readiness.
The original master places giant parasols northeast of Seyda Neen in Ascadian
Isles cells (0, -9) and (-1, -8), not just distant mushroom regions. Region vf1019
contains an original giant parasol close to its core centre for testing.

The builder now generates FS-UAE and WinUAE configuration files beside full and
asset-free images. Both FS-UAE launch paths read the complete verified HDF list;
missing world disks stop configuration. The terminal-width final footer lists
all HDFs and both runner paths, also retained in the build summary. Docker exports
receive separate host-local configurations rather than container filesystem paths.
Configuration, summary and Docker boundary regressions passed locally; the new
Docker export path still needs an actual container integration test.

## WIN-05: intermittent WinUAE background-music snapping - investigation open

1. **Symptoms, impact and cause.** During v0.0.27-rc1 WinUAE playtesting, the
   owner reported recurring background-music glitches, resembling underruns, in
   v0.0.27-rc1 and earlier WinUAE sessions. Earlier Linux FS-UAE runs did not
   exhibit the same reported symptom. The report concerns background music;
   sound-effect snapping has not been reported. Root cause is unknown; this observation
   does not isolate game streaming, emulator scheduling, backend buffering or
   the host audio driver.
2. **Reproduction.** Reported while playing the current image; no deterministic
   minimal reproduction yet. Compare the same scene and track, recording whether
   snaps coincide with map loading or occur during steady playback. Repeat with
   host conversion/build tasks stopped. Compare music streaming diagnostics
   (`music-profile.txt` after normal game shutdown: `read_errors` and
   `synchronous_fills`) alongside WinUAE buffering. Synchronous fills include
   expected startup/track changes, so their count alone does not prove underruns.
3. **Experiment, not a fix.** Keep the reference `sound_max_buff=16384` and test
   a separate private WinUAE configuration with `32768`. It mounts the same two
   HDFs and changes only the audio buffer. Crackle reduction and latency have not
   been verified. Linux presets and game audio code are unchanged by this test.

   Frame-rate distinction: the WinUAE status-bar ~49.9 value measures emulator
   display/vsync frames, not game renders. AmiWind `Host_FilterTime` already
   limits ordinary game frames to 72 per second. `dbg show fps on` exposes the
   game counter. `host_framerate` changes simulation timing and must not be used
   as an FPS-cap workaround. A 25/50 game-cap experiment needs a separate real
   limiter; do not change PAL chipset timing as a substitute. Inspect
   `frame-profile.txt` after normal shutdown for `audio_late_updates`,
   `missed_audio_frames` and the separately counted startup warmup; these
   counters can distinguish late guest mixing from a host-backend symptom.

## WIN-04: gallery allowance receipt differs after Windows staging

1. **Cause, symptoms and impact.** During v0.0.27-rc1 local assembly, the
   complete retained NPC gallery validated, but staging regenerated
   `model-budgets.txt` using the host default newline translation. Windows
   produced CRLF while the gallery receipt described LF bytes. The strict
   required-gallery check stopped assembly with a changed-payload error.
   This was a text-writer portability defect; converted models were intact.
2. **Reproduction.** Stage a gallery generated on Linux on a Windows host,
   then validate the staged allowance file against its original receipt.
3. **Correction and verification.** `write_allowances` now writes explicit
   UTF-8 and LF. A byte-level regression verifies the header, record separators,
   and absence of carriage returns. The fresh local assembly retry validated
   2,935 gallery records and 3,551 models, including the inspection map.
   Final disk readback and gameplay remain separate acceptance checks.

## CI-01: Windows short-path aliases fail host-discovery assertions

1. **Cause, symptoms and impact.** In AmiWind v0.0.26-rc1, the Windows 2022
   host-parity job failed two tests: managed-font discovery and SDK discovery.
   The runner supplied an 8.3 short alias in its temporary-directory path.
   Discovery correctly returned resolved long paths, while assertions compared
   unresolved fixture paths. Both names referred to the same files. Linux source
   checks, the asset-free Amiga build and Ubuntu host parity passed. The release
   gate stopped before tagging. This failure does not establish a compiler or
   asset-conversion defect.
2. **Reproduction.** On Windows, create a temporary directory with a distinct
   8.3 alias, set TEMP and TMP to that alias in a child process, then run
   unittest discovery for test_build_host.py. Both failures reproduced locally.
   An ordinary long-path temporary directory passed, masking this CI difference.
3. **Correction and verification.** Resolve expected SDK, map-tool, QCC and font
   paths before comparison. Keep short-path inputs in the fixtures to exercise
   discovery. This also exposed a later setup-preview fixture passing an invalid
   MSYS2 tools path containing a short alias or spaces. Preview now uses a unique
   nonexistent path on the same drive with supported characters; it creates no
   files there. No production or Linux launcher code changes. All four CI test
   groups passed locally with short-path TEMP/TMP after correction (30 tests,
   two POSIX-only skips). An explicit Windows 8.3 regression retains this case
   in the suite; it skips only where the volume supplies no distinct short alias.
   A new hosted Windows CI pass is still required before
   tagging; a local regression pass alone is not release acceptance.

<a id="win-03-windows-image-packing-command-exceeds-process-limit--validation-pending-2-october-2026"></a>
## WIN-03: Windows image-packing command exceeds process limit â€” fixed in working tree, 2 October 2026

1. **Type, cause, symptoms and impact.** Deterministic Windows host packaging
   defect in the v0.0.25 Windows port. All 25 pre-image stages passed, including
   all 3,551 NPC gallery models and 2,526 world regions. Image assembly reached
   `tools/world_volumes.py:pack` and failed launching `xdftool.exe` with
   `[WinError 206] The filename or extension is too long`. The generated terrain
   partition command contained 6,618 arguments / 165,293 UTF-16 code units,
   including its terminator, to write 1,651 files. This exceeds Windows'
   32,767-unit CreateProcess command-line limit; the message does not mean an
   individual game filename is too long. The boot-volume command has the same
   scaling problem. This is separate from WIN-01's intermittent queue handles.

2. **Reproduction and evidence.** A full native Windows build using normal game
   content reaches this oversized partition command. Capturing its argument list
   reproduced the size above; a harmless child-Python invocation with a 40,000
   character argument independently reproduced WinError 206. The failed run and
   completed conversions are retained. Its 1,925 instrumented worker lifecycles
   reported no invalid handles; that single run does not close WIN-01.

3. **Correction and validation.** `tools/build_windows_xdftool.py` splits the
   command queue only between complete `+`-delimited operations, preserving file
   order and paths. Each invocation is bounded to 24,000 UTF-16 units including
   Windows quoting and the terminator. A failed batch stops assembly immediately;
   an individually oversized operation is rejected before any image writes.
   Only Windows world/boot packaging selects this helper. Linux's original
   invocations, image contents and validation gates remain unchanged.
   A real 1,100-file image test passed all byte-for-byte readbacks across five
   commands; its original command was 116,774 units. Four regression tests cover
   queue preservation, quoting/UTF-16 length, oversize rejection and failure
   propagation. Full retained-conversion image assembly was retried into a
   fresh output directory with all normal gates. The image retry passed in
   433.078 seconds; both partitions passed complete readback, the actor gate had
   zero unresolved findings, and WinUAE entered the prison scene. WIN-03's
   correction is verified and included in v0.0.26-rc1.

The image-only retry is a bounded local recovery after checking source changes
and all retained terrain hashes. It is not general pipeline resume support and
does not rewrite the failed full-run receipt as successful.

## WIN-01: intermittent geometry worker queue failure â€” open, 2 October 2026

1. **Type, symptoms, cause and impact.** Host-side parallel asset conversion
   on Windows 11, official CPython 3.12.10, in the Windows port based on cloned
   v0.0.25 commit `3433922c40a48ffd20a0362ed58407298221686a`.
   Interior, Balmora and Census conversion have failed in geometry work
   dispatched by `tools/prepare_mesh_bsp.py` through
   `tools/build_parallel.py:ordered_map`. A worker raises
   `OSError: [WinError 6] The handle is invalid` inside Python's
   `multiprocessing/queues.py`, at `self._sem.release()` in `Queue.get`.
   The queue's semaphore handle is invalid when released; why it became invalid
   is **unknown**. The pool reports `BrokenProcessPool`, the stage fails, and
   the builder cancels sibling work. The Amiga engine compiler passed in these
   runs. This does not establish a compiler defect, memory exhaustion, or an
   excessive worker count. Windows cancellation also left orphan workers;
   process-tree cleanup needs a separate verified correction.

2. **Reproduction and evidence.** Complete native conversion via `build.cmd`
   with owned game inputs and `--jobs 24`. Three retained full-run attempts failed:
   interior with 17 effective pool workers under a 24-worker total budget,
   Balmora with 12 while the gallery had 12, and Census with 12 while a
   separate 12-worker gallery was active.
   Keep run receipts and the corresponding stage logs. Reproduction is
   intermittent: an isolated 24-worker interior pass, eight rounds of a
   24-worker synthetic geometry probe, and five repetitions of the first two
   Balmora regions with 12 workers passed. The complete 64-region Balmora diagnostic, ten instrumented Census geometry
   repetitions and three exact Census stage-command replays also passed.
   The independent gallery completed all 3,551 models and payload validation
   (790 reused, 2,761 freshly converted, zero failures). An instrumented full
   run then passed every conversion stage with 1,925 worker lifecycles and no bad
   handles, before failing separately at image packaging (WIN-03). Root cause
   remains open; this passing conversion does not establish full-build reliability.

3. **Fix or mitigation and validation.** No confirmed fix or reliable workaround
   yet. Retain validated conversion caches and diagnose with separate output
   directories. Close only identified orphan descendants of a failed build.
   These are recovery measures, **not a fix**. Do not disable required content,
   lower quality or waive validation gates. A future process-management fix
   must be scoped to Windows, preserve Linux worker behavior, and be validated
   under the failing workload and a complete build before closing this entry.

See [Windows build and known issues](WINDOWS_BUILD.md#windows-build-and-known-issues).

**Review findings.** The observed `Queue.get()` failure occurs after receiving
the next task's serialized bytes and before decoding that task. The earlier
tracebacks do not show whether the worker had already processed any tasks.
Each Windows worker owns a duplicated semaphore handle: ordinary parent-side
garbage collection, slow result consumption, or another pool closing its own
handles does not by itself explain an invalid worker-local handle. Code review
has not identified an executor-lifetime error in `ordered_map`.

Instrumented full-run diagnostics now record handle type during deserialization,
before/after worker standard-input cleanup, at worker entry, and on queue errors,
with the number and identity of previously received work items. These records
are private diagnostic artifacts, not release assets. Interpret a failure at
startup separately from a handle becoming invalid after geometry work. A handle
number reused for another kernel-object type would support a local close/reuse
problem; that has not yet been observed. Standard-input cleanup was considered,
but the tested interpreter's initial stdin uses `closefd=False`; it remains a
low-confidence hypothesis, not an established cause.

No automatic retry, alternate multiprocessing backend or reduced-content build
has been adopted as a fix. If the failing handle was initially valid, a scoped
[Windows native handle trace](https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/-htrace)
can identify handle-open/close/invalid-reference call stacks. A passing run with
different concurrency and cache state cannot alone identify the cause.

## WIN-02: cancelled Windows stage leaves worker descendants â€” open, 2 October 2026

1. **Type, cause, symptoms and impact.** Host process cleanup. Windows stage
   cancellation currently calls `Popen.terminate()`/`kill()` on the immediate
   process. Unlike the Linux process-group path, that does not terminate the
   entire descendant tree. A cancelled gallery left twelve Python workers alive
   after its parent exited, consuming resources or waiting indefinitely.
   This is separate from WIN-01; it is not evidence of the semaphore root cause.
2. **Reproduction.** Run independent conversion stages concurrently and cause
   one to fail while another owns a worker pool. Inspect the cancelled stage's
   descendants after its parent exits. A synthetic Windows parent/child fixture
   can test this without game data or disrupting an active build.
3. **Fix status.** A Windows-only process-tree termination candidate passed the
   isolated parent/child test, including the virtual-environment launcher. It is
   not integrated into the public scheduler. A separate candidate also passed a
   synthetic scheduler forced-failure test; production integration and a full
   failure-path build remain pending, so this issue remains unfixed. Linux process-group handling must remain unchanged.
   Until integration, explicitly close only verified orphan build descendants.



## Intermittent inability to ready hands: unknown state (open)

The owner reported F temporarily ceasing to raise/lower the hands. Debug mode
and the map were initial suspicions, but repeating both did not reproduce it.
Do not label either as the cause. No reliable trigger or state capture exists
yet. Track separately from the repeated visible-fist disappearance; the latter
is the persistent and more immediately distracting visual defect.

Historical checkpoint record. Current combined source status: [RECONCILE-v0.0.25-rc1.md](RECONCILE-v0.0.25-rc1.md).

Record every reported regression here or in its linked version record. Include
affected version, symptom, reproduction, established cause (or explicitly unknown),
exact implementation, native validation and unresolved limits. Host tests,
cross-compilation and native playtesting are separate evidence. Preserve older
records when a diagnosis changes.

## Torch grip and periodic fist disappearance â€” open, 2 October 2026

Owner screenshots show the placeholder torch beside the fist, and the owner
reports that the fists stay visible, blink completely off very briefly, and
return immediately. This brief blink repeats roughly every 1â€“2 seconds;
1â€“2 seconds is the interval between blinks, not the duration of invisibility.
The symptom has been present since hands were first implemented. This is a longstanding
bug, not a new torch regression; its period is not established as the
2.67-second animation loop. The rc7/rc8 torch overlay was positioned independently of the animated hand.
rc9 replaces it with the original torch mesh, authored grip and emitter-aligned
flame. Emulator acceptance of that replacement remains pending. The eight baked idle frames are
nonempty and a repeated actual QuakeC VM test retains the model across loop
boundaries; the reported 3D rendering disappearance remains unreproduced.
See [torch source findings and next checks](TORCH.md#original-model-replacement-and-reported-hand-flicker).
Neither the grip nor flicker is declared fixed by the rc8 crash correction.

## Scaled Seyda Neen flora omitted â€” open, 2 October 2026

The retained rc3 regional maps contain only five of sixteen large Bitter Coast
tree placements from the two named Seyda Neen cells. All sixteen reached the
scenery index and their sprite files exist. The other eleven have non-unit
source scales and are skipped by `prepare_quake.py`; that filter remains in rc8.
The Seyda brush pass excludes flora, so it supplies no replacement. This is a
placement omission, not merely delayed runtime loading. No fix is included in
the delivered rc8 torch package. See the evidence and planned repair in
[asset coverage](ASSET_CATALOGUE_AND_GALLERY.md#confirmed-omission-scaled-bitter-coast-trees).

## rc7 torch activation crash (rc8 source correction)

Reproduction reported by owner: raise fists with F, then press V; game crashes.
The successful rc7 native/image build and CI did not detect it. Host reproduction
calls the actual brush-render entry point with one active dynamic light and a
converted-style model whose collision root is -5. rc7 faults in R_MarkLights
while reading node contents before the node array. The retained bm015 fixture
contains 42 negative-root brush models; this is valid generated geometry.

Positive mesh collision trees can also contain no face references. rc8 therefore
lights the model's own visible surface range instead of following either kind
of collision root. Surface bounds, local light transforms, model-box rejection,
plane distance and tiled-surface exclusion are retained or checked explicitly.
The unsigned last-slot mask also avoids signed-shift undefined behavior.

The new address/undefined-sanitized regression fails on rc7 and passes on the
correction. It exercises R_DrawBEntitiesOnList, not just the standalone lighting
helper. Emulator retest remains open. No geometry regeneration, actor waiver,
water change or removal of the torch feature is used to bypass the fault.

## rc7: contact fitting, fog-off sky and cave lighting

The 23 rc3 contact findings cover 15 placed references, including one outdoor
Balmora Dreamer; they are not missing actors. Origin-only support differs from
contact of the quantized idle mesh. rc7 fits the mesh within bounded placement
constraints and preserves that certified point at runtime. The strict checker
is unchanged. See [contact method and evidence](NPC_GROUND_CONTACT.md).

The reported fog-off pale outdoor background matches the solid clear-colour
path where far-culling leaves uncovered pixels. rc7 uses the existing sky for
those pixels and restores normal solid background indoors. Native pixel tests
cover this path; the precise Red Mountain camera still needs replay, and terrain
holes are not declared fixed solely by changing their background.

The F/V temporary torch uses existing dynamic lighting. A related renderer
problem was exposed by translated/rotated cave models: light origins were in
world coordinates where surface calculations required model-local coordinates.
Both dynamic marking and accumulation now use the same model transform. Tests
exercise actual surface lighting. No water-rendering code is changed; cave
appearance and Amiga performance remain playtest tasks.

## AW25-09: image rejects world/journal receipt after terrain â€” v0.0.25-rc3

The reported workstation run completed world-terrain in 4232.5 seconds, then
image assembly failed with `Incomplete world/journal conversion receipt`.
The world-UI writer swept `regions.awr` into a receipt whose validator correctly
requires exactly four UI-owned files. rc6 enumerates only those four files;
the terrain directory is preserved and strict hash/palette validation remains.
A synthetic mixed-directory regression reproduces the condition and checks
repeat generation and corrupted-journal rejection.

New runs validate world UI before terrain. Checked rc3 image recovery verifies
the retained terrain and rebuilds only engine/image into new staging. This
does not waive actor-contact or filesystem gates, and no final game HDF has
passed here. See [image recovery](IMAGE_RECOVERY.md). The Daedric font fallback
warning preceding the error is separate from this receipt failure.

## AW25-08: area build aborts on window mounting â€” v0.0.25-rc2

The full local build stopped in `prepare_area.py` with
`ValueError: No supporting faÃ§ade geometry`. The same failure was reproduced
from the uploaded rc2 source using the original Census and Excise Warehouse
cell. The Tradehouse also contains affected Nord window assets without an
exterior house supporting mesh.

The flattening profiles were selected by model name alone. Those exterior-named
assets are reused inside rooms, where their exterior mounting plane and wall
normal test do not apply. Profiles now explicitly select scene kinds; the
shipped profiles approve exteriors only. The BSP converter uses the named-cell
metadata supplied by every interior exporter and retains original interior
window visuals and collision. The exterior support guard still rejects missing
or incorrectly facing walls. Archive handles close on both success and failure.

Regression coverage assembles a complete synthetic interior BSP with a window
and no house. Its output must equal the explicitly unflattened conversion,
including collision. The same unsupported exterior must still fail. The real
Warehouse conversion passes with the fix. Full checkpoint verification is
recorded separately; this result alone is not complete build acceptance.

## 1 October 2026: dev1 to rc1 recovery

Detailed records and chronological validation:
[v0.0.25-rc1 recovery journal](RECOVERY-v0.0.25-rc1.md).

| ID | Issue / reproduction | Cause and implementation | Current validation / limits |
| --- | --- | --- | --- |
| AW25-01 | Seyda walking reaches water before island handoff | Backdrop bounds exceeded authored ground; derive handoff from actual LAND bounds with clearance | Host bounds/rebasing checked; fresh native walking both ways pending |
| AW25-02 | Dry valleys/rises flooded; local 9,484,102, yaw 298, pitch 50, region unknown | Coarse terrain loses wet/dry identity; recover adaptive source samples and aligned shared edges | Zero mesh wet/dry errors in 8.27M comparisons; original camera and native visuals pending |
| AW25-03 | Map marker reported stale; HUD lacks universal/local positions | Unify exterior transform and refresh marker each draw; add global/local HUD and compass | Host live-position tests pass; original user cause not conclusively isolated |
| AW25-04 | M/N switch to desktop, including console, with debug/noclip | OS qualifier shortcut; front-game input filter, remove Amiga-to-Ctrl alias, debug Alt+M | Fresh native M/N console and intentional desktop pass; return-path regression found, corrected and repeated successfully |
| AW25-05 | Console always uppercase; digits become Shift symbols | Stale transition-based Shift can survive missed release; refresh event qualifiers, separate Caps Lock letters, correct raw 0x30 | Compiled regression types literal dbg 1 after lost release; owner reproduction still pending |
| AW25-06 | Quicksave shown empty / ordering confusing | One quick slot, two generations; menu conflates absent/corrupt/incompatible; exact ordering cause unknown | Inspected; menu/generation display TODO; original affected saves needed for incident diagnosis |
| AW25-07 | Python FS-UAE launcher cannot execute directly after extraction | Archive mode forced 0644; preserve/validate 0755 on public and private copies | Archive mode and extraction checked; private HDF packaging pending |

Requested changes tracked alongside regressions: Ctrl noclip at twice Shift
speed on all axes; separate keymap; autosave history configurable in Options and
game config, default five. Existing saved autosave choices override the default.
Map occlusion is a future TODO and is not implemented in rc1.

Checkpoint 006 is source for an incomplete prerelease. The strict actor-contact
gate still has 23 known findings; these remain in historical reports and may stop
local final HDF assembly. No private image is represented as production validated.

## Input preflight rejects personal transfer ZIPs â€” v0.0.25-rc1

Reproduction: put Morrowind_Video.zip and Morrowind_video.zip beside the normal
Data Files/Video directory. The scanner previously inventoried every loose file
and rejected the case-folded ZIP collision before distinguishing game assets.
These are transfer archives, not required game inputs.

Fix: positively select Morrowind.esm/Morrowind.bsa by name and supported asset
types inside known game folders before path checks, inventory and build hashes.
Ignore unrelated directories, root files and transfer archives. Audio inventory
counts WAV/MP3 files only. Reference checks use the same game-input selection.
Keep normal ESM/BSA checks and ambiguity checks for actual assets. Intro conversion
already reads loose Video/mw_intro.bik and never requires a ZIP. Do not modify or
rename the owner's archives. Synthetic regression covers both differently cased
ZIPs, an actual loose video, archive-free input receipts and a real video conflict.
No proprietary game files are needed for this host regression.


## AW25-10 â€” actor contact blocks image assembly after terrain

**Status: placement bugs unresolved; earlier detection and explicit private-test
acceptance implemented in rc6.** The receipt fix exposed the existing 23 strict
contact failures at the next image gate. Scheduling that gate only after the
reported 4232.5-second world-terrain pass wasted time before a deterministic
failure. A new actor-contact stage prepares an isolated copied payload and
checks it before world-terrain. The final image still repeats the audit.

The retained scene reproduces the same 23 findings, including one Balmora outdoor
Dreamer, two Balmora interior residents, four Addamasartus actors, and eight
Seyda references repeated across scenes. See [the contact record](NPC_GROUND_CONTACT.md).
The owner's earlier Balmora floating reports were unintended placement bugs,
which motivated this gate; intentional levitation is not their explanation.

A narrow optional reviewed-report acceptance permits diagnostic HDF assembly.
It compares the entire report and recorded geometry/model hashes, rejects
changed findings and invalid metadata, retains the failed raw audit, labels the
HDF `-private-test`, and records production_gate_passed=false. The owner reported
a successful rc3 diagnostic assembly in 144.664 seconds, 3,221,258,240 bytes.
This is not resolution of the 23 contact defects or proof of an rc6 game build.

## rc9: NPC gallery absent from normal images

Owner reported `Gallery catalogue missing` on rc8. The standalone conversion and
staging tools existed, but the normal builder never called them or compiled the
inspection map. This was a build integration omission, not evidence that the
original NPC records were absent. Add a default gallery stage and required payload
checks before image success; expose only the explicit `--no-npc-gallery` opt-out.
The full-world terrain remains reusable. Target gallery entry, browsing, selected
models and return-to-game remain part of the rc9 playtest.

## AUDIO-03: WinUAE video-to-Jiub loading spike

The owner reports repeatable audio glitches during the heaviest scene-loading
spike immediately after the intro movie, when entering the Jiub opening scene.
This is additional to intermittent background-music snapping; the exact audio
source and cause at this transition remain unverified. Reproduce a new game
with the movie enabled and listen across movie completion and ship entry.

Proposed rc4 investigation: finish video audio before blocking scene I/O, then
resume background music with about a one-second fade after loading completes.
A delay while the audio device continues consuming an empty buffer is not a
fix. Check natural movie completion and skipping, preserve Jiub speech timing,
and compare WinUAE with FS-UAE. No mitigation or fix is claimed yet.

## CRASH-01: rc3 Hors restart from Jiub name entry

- First observed / affected: **v0.0.27-rc3** local playtest, image-002 in WinUAE.
- Reproduction: start New Game, reach Jiub's name-entry scene and enter
  `dbg aw hors 0` to travel to Seyda Neen. The game returns to AmigaDOS while
  WinUAE remains open. The recovered detached-filesystem `ERROR.TXT` says:
  `Hunk_Alloc sn012: need 2767120 bytes, free 1682208 of 11534336`.
- Introducing content change: the rc3 terrain-handoff correction added a
  768-unit real-LAND apron without moving the existing FPS residency cores.
  sn012 grew from 5,507,736 to 8,395,232 BSP bytes and its visibility lump from
  473,407 to 2,767,103 bytes. The visibility double-buffer behavior predates
  rc3; its first introducing version is unverified.
- Established cause: the streaming loader held visibility in temporary high
  Hunk memory, then allocated a second full resident copy in low Hunk. The
  allocations overlapped and the next request failed. Held-input/state
  preservation did not cause this BSP allocation failure.
- Repair candidate: unreleased rc3/rc4 source reads byte-only visibility,
  lighting and entities directly into final storage. The real-loader regression
  passes byte-identity, temporary-copy, pack-member-offset and malformed-input
  checks. An Amiga compile and host tests are evidence for the source change,
  not a playable-map acceptance. The then-current unbounded sn012 candidate
  exceeded the unchanged 6 MiB map ceiling after 3 MiB non-map and 2 MiB safety
  reserves. A later normal bounded Seyda conversion passes static per-map
  estimates; see the dated follow-up below. Neither static result closes the
  target crash incident. Fatal-exit diagnostics are a separate improvement.
- Verified fixed version: **pending**. The original trip, final map gate,
  packaged loader route and target lifecycle must pass before closure.

This is a release blocker. Keep the original image as the reproduction target;
do not substitute a repaired candidate and call it a reproduction. Older minimal
images lack the AmigaDOS `Type` command; detach the HDF and inspect its files
with host tools. Mitigation is not a fix, and a passing loader regression does
not establish that later nodes, hulls, actors or renderer allocations fit.

### CRASH-01 diagnosis and exit diagnostics

The detached playtest image contains the fatal report: `Hunk_Alloc sn012:
need 2767120 bytes, free 1682208 of 11534336`. This is engine heap exhaustion
loading Seyda Neen visibility data, not termination of WinUAE. The expanded
terrain candidate increased this subdivision visibility lump to 2767103 bytes.
Basic lightmap/PVS byte deduplication alone does not recover enough memory;
the content/runtime repair is still pending.

Fatal exits now print their reason to AmigaDOS after closing the game screen,
as well as attempting the existing ERROR.TXT file. This adds no per-frame work.
The current playtest disk predates that diagnostic change. The minimal boot
image does not contain the AmigaDOS Type command; inspect ERROR.TXT using
filesystem tools with the disk detached when using older candidates.

### CRASH-01 bounded-world static follow-up — 3 October 2026

The normal bounded Seyda converter generated 67 BSP entries (64 cores plus
docks, court and fallback); all 67 pass the saved target-ABI estimate. The worst
modeled peak is 5,884,944 B, with 406,512 B minimum growth margin after the
unchanged 3 MiB non-map allowance and 2 MiB safety reserve. A separate Balmora
layout's 65-entry audit also passes statically and covers 1,488/1,488 source
placements; its worst fallback is 6,155,504 B with 135,952 B margin. Full details
and the 128-unit-core hysteresis caveat are in
[memory allocation](MEMORY_ALLOCATION.md#normal-converter-bounded-town-audit--3-october-2026).

These are candidate map estimates using saved ABI sizes, not runtime allocation
or a passing packaged image. Final actor/contact/fingerprint/heap checks, HDF
assembly/readback and target cold/warm transitions remain pending. The static
results do not prove the original `sn012` crash fixed and do not close CRASH-01.
No FPS or performance improvement is claimed.

## MEM-EXTRA-HDF — map search path bypasses section streaming

- Issue: direct com_gamedir fopen cannot find BSPs placed only on additional
  world-volume search paths; whole-file fallback can add an unexpected BSP-sized
  temporary allocation. A section-only memory estimate is then insufficient.
- Affected/observed: path confirmed by inspection of v0.0.27-rc3 loader and world
  volume wiring; no target crash reproduction claimed for this distinct issue.
  First introducing version: unverified.
- Cause: custom streaming loader bypassed the engine filesystem lookup; normal
  search paths include AW_WORLDn:id1 without changing com_gamedir.
- Repair candidate: unreleased rc3 source now opens through COM_FOpenFile, records
  the returned member base/length and seeks relative to it. This also respects
  pack-member offsets. No heap increase or reserve reduction.
- Verified fixed version: pending. Required proof: direct-byte/offset regression,
  target compile and multi-HDF playtest, with bounds/read failures checked.
- Prevention: audit the actual loader path for every storage layout and retain
  final-map estimates plus runtime load evidence. See
  [the separate loader trap](MEMORY_ALLOCATION.md#separate-loader-trap-extra-hdf-search-paths).


## CRASH-REPORT-02 — visible fatal-exit report

- Affected: v0.0.27-rc3 playtests returned to AmigaDOS after a fatal engine
  error with no visible reason. The first rc4 source diagnostic was terse,
  omitted the version/restart hint and did not verify whether logging succeeded.
- Reproduce: trigger an engine `Sys_Error`, such as the recorded rc3 sn012
  allocation failure; observe the shell after the game screen closes.
- Source change: v0.0.27-rc4 now prints a versioned crash banner, the supplied
  reason, the resolved ERROR.TXT path when saved, and the `amiwind` restart hint.
  DOS Open/Write/Close results and a byte-for-byte readback through EOF are
  checked; failed/partial writes or unverifiable contents instead request
  copying the displayed cause. No stdio file buffer is allocated for this write.
- Validation: source inspection only; fresh compilation and target fatal-exit
  checks are pending. Test both writable and full/read-only launch directories.
  This improves diagnostics, not the underlying crash cause. CPU traps, emulator
  termination and failures before this handler cannot be guaranteed a report.
- ERROR.TXT is a text error report, not a complete memory crash dump. Existing
  separate heap-audit telemetry remains separate. No per-frame polling is added.


## MEM-GEOMETRY-01: transactional geometry/light sharing candidates

- Scope: an exact-representation optimization trial for `bmmages`, `bmtemple`
  and `addamasartus`; it is separate from CRASH-01 and does not close that
  incident or establish that all over-budget maps are fixed.
- First failed candidate: Mages Guild face 285, light-data offset 11,723. The
  earlier light-range deduplicator used wide intermediate UV arithmetic and
  derived a 30-byte referenced span. Per-operation binary32 arithmetic derived
  36 bytes, so copying the shorter range would have changed the next 6 bytes.
  The actual Amiga target FPU intermediate precision has not been established.
- Safe handling: the first optimizer attempt failed before replacing any map;
  original maps and the failed receipt were retained. `deduplicate_bsp.py` now
  preserves the longest original referenced byte span required under both
  precision policies. It does not change UVs, extents or runtime geometry.
- Candidate and transaction: exact vertex/inline-edge/edge-reference sharing,
  followed by independent light/PVS byte deduplication. The normal build hook
  stages all candidates after actor annotation/baking and before independent
  actor contact, the final heap gate and content fingerprinting. Every candidate
  is checked before replacement; replacement failures roll back prior maps;
  output hashes are rechecked before the heap gate and fingerprint.
- Source/data evidence: all three geometry-only maps passed independent Python
  render-input checks. Vertex order/coordinates and face winding match; affected
  visible/render inputs, lighting samples and decoded visibility were checked;
  collision, models and other protected lumps remain unchanged. Five optimizer,
  five render-input oracle, two deduplication and ten engine-receipt regressions
  passed.
- Native C comparison: inside the owner-authorized Linux Docker environment,
  one synthetic before/after pair (3 faces) and three real map pairs passed
  (Mages 40,530; Temple 35,242; Addamasartus 23,426; 99,198 real faces total).
  This is Linux C loader evidence, not Amiga FPU/rendering or target gameplay
  evidence. The earlier Windows Application Control block remains historical;
  the local helper was removed and Windows runners skip native binary tests.
- Reused-ABI static estimates: Addamasartus peak 5,812,864 B, margin 478,592 B;
  Mages peak 5,688,464 B, margin 602,992 B; Temple peak 5,905,872 B, margin
  385,584 B. All three pass the current 6 MiB map ceiling with the unchanged
  3 MiB non-map reserve and 2 MiB safety margin. These are estimate-only values,
  not a fresh ABI probe or gameplay result.
- Status: staged optimizer hook and transactional protection are implemented;
  exact three-map candidates and host/native comparisons passed. Final whole-map
  packaging, a fresh matching engine/image, target renderer/FPU behavior,
  seams/state and lifecycle playtesting remain pending. No FPS improvement or
  release readiness is claimed. Mitigation is not a fix.


### WIN-04 follow-up: retained CRLF allowance receipt in rc4 assembly

- **Version and circumstances:** v0.0.27-rc4 image assembly rejected
  `model-budgets.txt` when reusing a complete retained gallery whose receipt
  authenticated CRLF bytes. No missing or changed NPC model was established.
- **Reproduction:** stage a valid CRLF gallery allowance table with the current
  explicit-LF writer, then validate staged bytes against the retained receipt.
- **Cause:** the earlier LF writer correction fixed future output but did not
  handle legacy CRLF receipts; regenerating LF changed the byte size and hash.
- **Repair:** authenticate the entire source package, regenerate/audit allowances,
  require identical contents after CRLF-to-LF comparison, then copy the verified
  original allowance bytes. Substantive differences remain fatal.
- **Verification:** seven gallery build tests pass on Windows, including retained
  CRLF acceptance and authenticated-but-inconsistent allowance rejection. The
  next image retry verified 2,935 records and 3,551 models. Linux execution and
  final packaged image/target acceptance remain separate checks.
## MEM-TOWN-02: Balmora bounded-layout estimate candidate

- **Scope and symptom:** earlier Balmora candidate maps exceeded the modeled BSP
  limit. This was a static heap-policy failure, not a separately reproduced
  Balmora crash. It is independent of the reproduced rc3 `sn012` crash in
  CRASH-01; neither static repair closes that target incident by itself.
- **Candidate change:** the normal Balmora layout path merges inexpensive outer
  regions to retain the 64-core format and divides the previous oversized area
  into three measured regions. It preserves the existing 896-unit visual
  coverage apron, 224-unit physical collision apron, 96-unit hysteresis,
  540-unit draw policy and unchanged 3 MiB non-map plus 2 MiB safety reserves.
- **Static evidence:** the whole audit covers 1,488/1,488 source placements with
  zero lost references and validates 64 non-overlapping cores; 65 map entries
  including the fallback pass using saved target-ABI sizes. Peaks: merged
  `bm000` 3,087,760 B; upper `bm001` 5,971,920 B; lower `bm027` 5,615,520 B;
  worst `bm019` / `balmora` fallback 6,155,504 B, leaving 135,952 B after both
  reserves. All are within the 6 MiB modeled ceiling; the 5 MiB figure remains a
  planning target, not a gate.
- **Transition caveat:** the 128-unit lower `bm027` core is shorter than the
  96-unit hysteresis band. The adjacent map can remain active through the core
  center within hysteresis; half-open core ownership remains unique and switch
  thresholds were not changed. Test seams, scenery and collision both ways at
  the split/merge, including rapid noclip and held controls.
- **Status:** static saved-ABI audit only. Normal image assembly, final actor and
  heap gates, target cold/warm lifecycle, both-direction crossing, collision and
  gameplay-state acceptance remain pending. No FPS improvement is claimed. This
  does not establish that the original `sn012` crash is fixed. See
  [bounded-town memory audit](MEMORY_ALLOCATION.md#normal-converter-bounded-town-audit--3-october-2026).

## BSP-LIGHT-01: pre-existing Vodunius lightmap range exceeds its lump

- **When discovered:** 3 October 2026, during the v0.0.27-rc4 image-005 continuation's whole-map optimizer pass. The pass failed at `vodunius.bsp` with `ValueError: Light sample range outside lump`. Its receipt records status `failed`, no committed maps, `rollback: originals preserved/restored`, and zero rollback errors. This is a build-data validation failure, not the earlier runtime heap crash.
- **Version provenance:** the offending map bytes were already present in retained v0.0.27-rc1 assembly/seam and v0.0.27-rc2 seam/town-handoff artifacts, and in rc4 image-001 through image-004. Their `vodunius.bsp` SHA-256 is `e92f82fb6793aa427f12fddd3901abfacb6ac984368ba6310f37fa5d074044a9`; the introducing version is not established, and the defect is known present by the retained rc1 artifact. The rc4 image-005 source copy has a different SHA-256 (`984639b9d02259504de9adde0fe7e2edabb0d1921d1e61a65958005326531f0e`); therefore this incident does not assert that every image-005 byte sequence is identical to the earlier retained map. The bad face/light-range condition was exposed by optimizing this map, not introduced by the optimizer.
- **Reproduction and cause:** run the receipt-bound v0.0.27-rc4 map optimizer over the staged image; it stops on `vodunius.bsp`. Face 4859 has `lightofs=64277`; the lighting lump is 64,355 bytes, leaving 78 bytes, while the final serialized face extents require 14×6 = 84 samples. The source lightmap was baked as 13×6 before final float32/canonical geometry values were used. Both narrow and wide extent policies identify the out-of-lump range. This is malformed/inconsistent baked map data, not a heap-budget failure.
- Repair applied as a verified candidate: regenerated only face 4859 from final serialized/canonical geometry and texinfo, retained lamp inputs, and inline transform. Narrow and wide arithmetic policies agreed on a 14×6 grid. The candidate appends 84 bytes and changes only that face's light offset; all other lumps, valid faces, and original light bytes were preserved.
- Verification and status: 15 focused tests passed, and an independent check covered all 4,860 faces under both narrow and wide policies. The initial whole-map optimizer attempt failed at this pre-existing defect after more than 2,700 of 2,717 map checks; it committed no maps and restored originals. After repair and manifest rebind, the complete optimizer verified 2,717/2,717 maps with no failures; the actor/contact gate passed with zero unresolved items; and the receipt-bound target-ABI heap estimate passed 2,717/2,717 maps. Worst modeled map is Balmora at 6,155,504 B, leaving 135,952 B after the unchanged 3 MiB non-map and 2 MiB safety reserves. These are static build gates, not target runtime validation. Both final HDFs now pass filesystem readback; target runtime acceptance is pending. The optimizer exposed this defect; it did not cause it. The one-face repair does not resolve broader narrow/wide precision differences or prove the producer is generally corrected.
- Long-term producer work: derive bake grids from canonical stored values and retain the minimum grid dimension of 16. This is separate from the verified single-face candidate.

## MAP-REG-01: rc4 In-Game selector hides retained settlement markers (BUG / REGRESSION)

- **When and affected version:** reported from owner playtesting of the v0.0.27-rc4 map-panel prototype. The screenshot shows the In-Game Map Prototype heading, a Debug button at left and an unreadable pale active button at right; the user sees Debug mode and no settlement names/markers.
- **Introducing change and reproduction:** the rc4 two-mode selector put settlement-landmark rendering behind a Debug-only mode condition. Open the map panel and choose In-Game to reproduce: the In-Game terrain view opens but converted town markers disappear, even though the retained map asset contains two town landmarks.
- **Cause:** the renderer incorrectly treated settlement landmarks as diagnostic overlays and skipped the full landmark loop in In-Game mode. The active-button fill was pale while console glyphs remained light, reducing the active label's contrast. This is a map UI rendering regression, not missing map records or evidence that a full original-game world map is implemented.
- **Source correction:** the v0.0.27-rc5 source removes the mode restriction for settlement landmarks so both views share those markers. The active selector uses a dark text interior with a contrasting gold border, keeping the light label readable. The rc4 HDF is unchanged.
- **Status and validation:** the v0.0.27-rc5 correction compiled in engine-002 and is included in the private candidate whose HDF files passed readback. Nine source checks pass; updated Linux native behavior fixtures have not been executed, and owner target validation remains pending. Confirm town-marker visibility and both button labels/states in both modes. Preserve the In-Game heading arrow and Debug teleport crosshair. In-Game remains a terrain-overview prototype; local map content and full-map parity are incomplete. See [world map and journal](WORLD_MAP_AND_JOURNAL.md).

## BUILD-REPAIR-01: ownership files omitted by rc5 retry extractor (BUG / BUILD TOOL)

- **When and affected version:** found during the v0.0.27-rc5 private image-repair retry. The helper extraction omitted authenticated numeric Seyda Neen and Balmora region-ownership text files; actor validation then reported 1,950 missing-owner-directory errors.
- **Cause and impact:** the retry extractor failed to copy the authenticated ownership table. This was a staging-helper defect, not a map ownership regression or a change in game data. It was detected before any HDF patch.
- **Correction and validation:** the helper now copies the authenticated ownership files, and the failed report/log are preserved. The retry was rerun through strict gates; the final rc5 candidate records actor/contact passed with zero unresolved items, all 2,717 map heap estimates passing, and successful HDF readbacks. The earlier failed extraction did not mutate the rc4 HDF or the retry clone.

## BUILD-REPAIR-02: retry assertion misread an empty failure list (BUG / BUILD TOOL)

- **When and affected version:** found during the same v0.0.27-rc5 retry, before HDF patching. The optimizer had verified all 2,717 maps, but a continuation assertion stopped.
- **Cause and impact:** the helper expected failing_maps to be numeric zero, while the receipt schema represents success with an empty list. This guard rejected a successful result; no map failed and no HDF was patched.
- **Correction and validation:** the assertion now checks the schema's empty-list representation. The final rc5 candidate was built after the correction; optimizer, actor/contact, static heap and HDF readback gates passed. These are build/package checks, not target gameplay acceptance.

## TEST-PORT-01: focused suite depends on repository root and Windows UTF-8 mode (TEST PORTABILITY ISSUE)

- **When and affected version:** discovered during final v0.0.27 release validation on Windows, 3 October 2026. Invoking the same 75 tests from the external working directory with default Windows cp1252 decoding produced nine missing-source-path failures in loading-delay tests and two UnicodeDecodeErrors in emulator-configuration tests.
- **Cause and impact:** running outside the repository selected an unrelated working-copy test module before the intended repository test, causing its source paths to resolve incorrectly. Separately, emulator-configuration tests used platform-default text decoding for UTF-8 configuration data. This is a test invocation/portability defect, not production behavior or an rc5 runtime regression.
- **What worked:** rerunning the exact 75 tests from the repository root with PYTHONUTF8=1 passed all 75. The first failure log is retained privately; no product or HDF change was needed for the rerun.
- **Correction/status:** explicitly decode UTF-8 in the emulator-configuration test and keep test invocation rooted/anchored to the repository. The test now explicitly decodes UTF-8; all 11 emulator-configuration checks passed under the default Windows encoding without PYTHONUTF8. Repository-root execution keeps the intended source tests selected. No runtime impact has been established; the owner-approved stable release is not reopened by this test-only issue.

## ACTOR-RECEIPT-01: Windows audit receipt hashed different line endings

- **Version, when and where:** discovered on 3 October 2026 during stable v0.0.27 private assembly preflight; present in retained rc4/rc5 actor reports. Introducing version is not established. No target gameplay regression is implied.
- **Reproduction:** on Windows, call `check_actor_ground.require`, then hash the saved output bytes and compare with `acceptance.report_sha256`. The former writer used implicit text-mode newline translation; its hash used the original LF string.
- **Cause:** the saved file gained CRLF endings, so its recorded SHA-256 did not describe the exact file. Stable assembly correctly refused it before cloning. Audit findings and payload hashes were unchanged.
- **Proposed and actual correction:** write explicit UTF-8 bytes, and hash those same bytes. A focused regression verifies LF output and equality between the saved-file hash and the acceptance receipt.
- **Legacy evidence:** the preserved rc5 report contains 5,915 CRLF sequences. Its actual SHA-256 is `ba619481de654d89d5cb6c5d99c7229c3c449b93c48d769ae5d7467afd47536c`; changing only CRLF to LF produces exactly the recorded `e691027c4fc7d50e3e6e5ae72391247b19ab14ac07938383fb5fde6e237c3adb`. Stable assembly preserves both hashes and the original receipt as provenance and normalizes its new copy only after that exact comparison.
- **Status:** writer correction in v0.0.27; all 15 interpreted actor-ground checks, including exact saved-file hash/LF validation, passed on Windows. Linux validation remains in the publisher gate. This fixes receipt serialization, not geometry or heap exhaustion. Legacy normalization is narrowly authenticated compatibility handling, not permission to rewrite mismatched content.

## LINUX-VALID-02: Linux test-fixture link failures repaired (VALIDATION ISSUE)

- **When/version/environment:** first reported 3 October 2026 during v0.0.27
  validation on Linux. The initial suite recorded 558 tests, 2 failures and
  5 skips. The first Docker rerun isolated a movie-fixture failure; the repaired
  full Docker rerun and matching asset-free compile are now verified.
- **Initial symptoms and cause:** `tests/aga_worldui_test.c` lacked stubs for
  `AW_DebugOverlaysEnabled`, `Cvar_SetValue` and `Cvar_RegisterVariable` used by
  linked world-UI code. `tests/aga_movie_test.c` lacked `CDAudio_Resume`,
  `Key_ClearStates` and `V_UpdatePalette` stubs used by movie code. These were
  test-fixture linkage omissions; they did not establish runtime/HDF defects.
  The cause of the second failure in the initial 2-failure result was not
  individually established from that run; the first Docker rerun identified the
  movie fixture issue. Do not retroactively claim a one-to-one match without the
  preserved failure logs.
- **Correction and verification:** both fixtures now provide the needed stubs;
  the world-UI fixture also exercises the relevant behavior. Native Windows C
  fixture execution is explicitly skipped under the interpreter-first policy.
  In the owner-reported Docker rerun, the complete Linux suite reported
  `558 tests, OK (skipped=3)`. The matching asset-free build exited 0 and emitted
  both emulator configurations. These checks repair/validate test linkage and
  compile configuration; they do not alter runtime or HDF content.
- **Status and limits:** Linux Docker suite and asset-free compile gates pass for
  this source state. The repaired source kit has not yet been regenerated or
  published; exact archive validation and owner-run Linux publication remain
  pending. This incident does not establish gameplay, target, or runtime
  acceptance. Keep Windows fixture skips distinct from Linux pass evidence.

## HANDOFF-WRAPPER-01: direct-unzip wrapper collided with an existing extraction (HANDOFF TOOL BUG)

- **When/version:** first observed 3 October 2026 in the v0.0.27 repair-001
  Linux handoff wrapper. This was a transfer-wrapper defect; no public source,
  runtime or HDF change is implicated.
- **Reproduction:** extract the single transfer archive directly into the
  established `~/NeuralNetwork` handoff root while an older generic extracted-kit
  directory is present, then run the included entry point. The wrapper reused
  that extraction location and stopped after finding modified `APPLY.py`.
  Repository source remained unchanged.
- **Cause:** extraction reused a generic kit-directory name instead of isolating
  each authenticated archive. Requiring a separate transfer directory would only
  avoid the collision by changing the owner's required workflow; that mitigation
  was not the correction.
- **Correction:** repair-002 derives an extraction namespace from the verified
  archive checksum, verifies the ZIP and every extracted member before apply,
  preserves old kits/backups, and keeps the apply target fixed at
  `~/NeuralNetwork/amiwind`. Delivery is one outer ZIP and one Bash entry point;
  the owner unzips directly into `~/NeuralNetwork` and runs it there.
- **Validation and status:** the exact-layout Docker test passed with the old
  extraction present: initial apply, repeat extraction/apply, unrelated-edit and
  kit-tamper refusal without mutation, and parent-shell errexit safety. This
  validates wrapper behavior, not archive delivery or publication. The inner
  source kit is unchanged from repair-001 and retains its separate Linux suite /
  asset-free compile results. The frozen public source ZIP was not regenerated.
  Owner handoff receipt, hosted CI and Linux publication remain pending; target
  gameplay acceptance is separate.
