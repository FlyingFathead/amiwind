# Bug journal

Historical checkpoint record. Current combined source status: [RECONCILE-v0.0.25-rc1.md](RECONCILE-v0.0.25-rc1.md).

Record every reported regression here or in its linked version record. Include
affected version, symptom, reproduction, established cause (or explicitly unknown),
exact implementation, native validation and unresolved limits. Host tests,
cross-compilation and native playtesting are separate evidence. Preserve older
records when a diagnosis changes.

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
