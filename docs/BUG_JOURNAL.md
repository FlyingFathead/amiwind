# Bug journal

<a id="win-03-windows-image-packing-command-exceeds-process-limit--validation-pending-2-october-2026"></a>
## WIN-03: Windows image-packing command exceeds process limit — fixed in working tree, 2 October 2026

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

## WIN-01: intermittent geometry worker queue failure — open, 2 October 2026

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

## WIN-02: cancelled Windows stage leaves worker descendants — open, 2 October 2026

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

## Torch grip and periodic fist disappearance — open, 2 October 2026

Owner screenshots show the placeholder torch beside the fist, and the owner
reports that the fists stay visible, blink completely off very briefly, and
return immediately. This brief blink repeats roughly every 1–2 seconds;
1–2 seconds is the interval between blinks, not the duration of invisibility.
The symptom has been present since hands were first implemented. This is a longstanding
bug, not a new torch regression; its period is not established as the
2.67-second animation loop. The rc7/rc8 torch overlay was positioned independently of the animated hand.
rc9 replaces it with the original torch mesh, authored grip and emitter-aligned
flame. Emulator acceptance of that replacement remains pending. The eight baked idle frames are
nonempty and a repeated actual QuakeC VM test retains the model across loop
boundaries; the reported 3D rendering disappearance remains unreproduced.
See [torch source findings and next checks](TORCH.md#original-model-replacement-and-reported-hand-flicker).
Neither the grip nor flicker is declared fixed by the rc8 crash correction.

## Scaled Seyda Neen flora omitted — open, 2 October 2026

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

## AW25-09: image rejects world/journal receipt after terrain — v0.0.25-rc3

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

## AW25-08: area build aborts on window mounting — v0.0.25-rc2

The full local build stopped in `prepare_area.py` with
`ValueError: No supporting façade geometry`. The same failure was reproduced
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

## Input preflight rejects personal transfer ZIPs — v0.0.25-rc1

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


## AW25-10 — actor contact blocks image assembly after terrain

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
