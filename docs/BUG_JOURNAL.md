# Bug journal

Historical checkpoint record. Current combined source status: [RECONCILE-v0.0.25-rc1.md](RECONCILE-v0.0.25-rc1.md).

Record every reported regression here or in its linked version record. Include
affected version, symptom, reproduction, established cause (or explicitly unknown),
exact implementation, native validation and unresolved limits. Host tests,
cross-compilation and native playtesting are separate evidence. Preserve older
records when a diagnosis changes.

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
