# Roadmap and implementation options

_Last updated with AmiWind v0.0.51 (25 October 2026)._

<!-- contents start -->
## Contents

- [v0.0.52 (next), 25 October 2026](#v0052-next-25-october-2026)
- [v0.0.51: Let There Be More Inner Light, 25 October 2026](#v0051-let-there-be-more-inner-light-25-october-2026)
- [v0.0.50: The Doors: Riders On The CHIM, 24 October 2026](#v0050-the-doors-riders-on-the-chim-24-october-2026)
- [Build turnaround first, 24 October 2026](#build-turnaround-first-24-october-2026)
  - [Why the image is bigger than the original game](#why-the-image-is-bigger-than-the-original-game)
  - [A disk layout that cannot dead-end](#a-disk-layout-that-cannot-dead-end)
  - [The actors get the CHIM rule: store once, place many times](#the-actors-get-the-chim-rule-store-once-place-many-times)
  - [One standard timedemo for real Amigas (v0.0.49)](#one-standard-timedemo-for-real-amigas-v0049)
- [Test on Amiberry, 21 October 2026](#test-on-amiberry-21-october-2026)
- [30-minute rebuilds, 20 October 2026](#30-minute-rebuilds-20-october-2026)
- [Collision from what the game already knows, 20 October 2026](#collision-from-what-the-game-already-knows-20-october-2026)
- [Cell crossings: one continuous world, 19 October 2026](#cell-crossings-one-continuous-world-19-october-2026)
  - [Decisions of 20 October 2026](#decisions-of-20-october-2026)
- [The road after v0.0.44, 19 October 2026](#the-road-after-v0044-19-october-2026)
- [Interiors: shell baked, takeable things as objects](#interiors-shell-baked-takeable-things-as-objects)
- [Distant views without pop-in, and the screen the Amiga need not redraw, 19 October 2026](#distant-views-without-pop-in-and-the-screen-the-amiga-need-not-redraw-19-october-2026)
- [Colour: AGA ramps for the ash, the blight and Red Mountain, 19 October 2026](#colour-aga-ramps-for-the-ash-the-blight-and-red-mountain-19-october-2026)
- [Next: the outdoors complete, then every entrance and every interior, 18 October 2026](#next-the-outdoors-complete-then-every-entrance-and-every-interior-18-october-2026)
- [Near future: the baseline stays, extra RAM becomes speed, 16 October 2026](#near-future-the-baseline-stays-extra-ram-becomes-speed-16-october-2026)
- [Near future: one game for the 68040 and the 68060, 16 October 2026](#near-future-one-game-for-the-68040-and-the-68060-16-october-2026)
- [Goal: every exterior on CHIM, 16 October 2026](#goal-every-exterior-on-chim-16-october-2026)
- [v0.0.42: Complete Vivec (the city), 16 October 2026](#v0042-complete-vivec-the-city-16-october-2026)
- [Effects to investigate: Quake machinery first, 16 October 2026](#effects-to-investigate-quake-machinery-first-16-october-2026)
- [v0.0.41 "More Fixes" and v0.0.42, 16 October 2026](#v0041-more-fixes-and-v0042-16-october-2026)
- [v0.0.41 candidate - visibility aprons, 15 October 2026](#v0041-candidate---visibility-aprons-15-october-2026)
- [v0.0.41 candidate - window support, 15 October 2026](#v0041-candidate---window-support-15-october-2026)
- [v0.0.41 candidate - lava coverage, 15 October 2026](#v0041-candidate---lava-coverage-15-october-2026)
- [Compiled apron selection, 15 October 2026](#compiled-apron-selection-15-october-2026)
- [Paired boundary validation, 15 October 2026](#paired-boundary-validation-15-october-2026)
- [Owner apron follow-up, 15 October 2026](#owner-apron-follow-up-15-october-2026)
- [Combined-world gate update, 15 October 2026](#combined-world-gate-update-15-october-2026)
- [v0.0.41-dev1: ring3 feasibility after v0.0.40 delivery](#v0041-dev1-ring3-feasibility-after-v0040-delivery)
- [v0.0.40 release scope - 15 October 2026](#v0040-release-scope---15-october-2026)
- [v0.0.40-dev1 gameplay priority, 14 October 2026](#v0040-dev1-gameplay-priority-14-october-2026)
- [Additional RC1 inspection findings, 13 October 2026](#additional-rc1-inspection-findings-13-october-2026)
- [Release hold and RC2 request, 13 October 2026](#release-hold-and-rc2-request-13-october-2026)
- [v0.0.39 - Cell By Cell, Piece By Piece](#v0039---cell-by-cell-piece-by-piece)
- [Movement presets and all eight attributes, 13 October 2026](#movement-presets-and-all-eight-attributes-13-october-2026)
- [v0.0.40 - Unfinished work and new features](#v0040---unfinished-work-and-new-features)
- [v0.0.38 - Lava Is All You Need (And A Hint Of Tel Uvirith)](#v0038---lava-is-all-you-need-and-a-hint-of-tel-uvirith)
- [v0.0.37 - Proofreading the Cantons (fix release)](#v0037---proofreading-the-cantons-fix-release)
- [v0.0.36 - 36 Lessons of Vivec's Cantons (And Vvardenfell Shorelines) (released)](#v0036---36-lessons-of-vivecs-cantons-and-vvardenfell-shorelines-released)
- [v0.0.35 - CHIMporting It All: Gathering Up The Loose Branches From The Seashore (released)](#v0035---chimporting-it-all-gathering-up-the-loose-branches-from-the-seashore-released)
  - [Next: build system](#next-build-system)
  - [Build pipeline speed (very near term, after Vivec)](#build-pipeline-speed-very-near-term-after-vivec)
  - [Perf, profiler and optimizer (future)](#perf-profiler-and-optimizer-future)
  - [Next: CHIMport region by region, coast first](#next-chimport-region-by-region-coast-first)
  - [Gameplay](#gameplay)
  - [CHIM maps become their own format (approved 10 October 2026)](#chim-maps-become-their-own-format-approved-10-october-2026)
  - [Tiny squeezes: memory that stays resident](#tiny-squeezes-memory-that-stays-resident)
  - [Roadmap horizon: one partition with CHIM](#roadmap-horizon-one-partition-with-chim)
- [v0.0.34 - CHIM: Tightening the Bolts (released)](#v0034---chim-tightening-the-bolts-released)
- [v0.0.33 - Towards CHIM: Replacing the Engine Block (released)](#v0033---towards-chim-replacing-the-engine-block-released)
- [v0.0.32 - Last Stop on the Old Line: Window-Shopping in Vivec (released)](#v0032---last-stop-on-the-old-line-window-shopping-in-vivec-released)
  - [Decided: a world streamer with no duplicated assets - the whole game on one hard file](#decided-a-world-streamer-with-no-duplicated-assets---the-whole-game-on-one-hard-file)
  - [Near future: fires and lava across the world](#near-future-fires-and-lava-across-the-world)
- [Planned: heap size matched to the host machine, 7 October 2026](#planned-heap-size-matched-to-the-host-machine-7-october-2026)
  - [The cache plan: extra RAM spent on not doing work twice (16 October 2026)](#the-cache-plan-extra-ram-spent-on-not-doing-work-twice-16-october-2026)
- [Other ideas and wildcards](#other-ideas-and-wildcards)
  - [Sky fading into the horizon](#sky-fading-into-the-horizon)
  - [Sea skirt: the sea runs to the horizon](#sea-skirt-the-sea-runs-to-the-horizon)
  - [Weather: ash storms and blight winds](#weather-ash-storms-and-blight-winds)
  - [Long-term possibility: a reusable Amiga game engine](#long-term-possibility-a-reusable-amiga-game-engine)
  - [Long-term possibility: an RTG display path](#long-term-possibility-an-rtg-display-path)
  - [Research: hardware 3D through Warp3D (v0.0.50 study, 24 October 2026)](#research-hardware-3d-through-warp3d-v0050-study-24-october-2026)
  - [Long-term possibility: Lua scripting](#long-term-possibility-lua-scripting)
  - [From Quake Arena to Vivec Arena: two-Amiga 1v1 duels](#from-quake-arena-to-vivec-arena-two-amiga-1v1-duels)
- [Older history](#older-history)

<!-- contents end -->

[CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](bugs/CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md) — 15 October 2026, v0.0.41-dev1: full-build preparation rejected five explicitly selected ocean routing cells absent from the original CELL/LAND inventory, before legacy compilation. The source checklist now records additional ocean routing cells separately and allows their absence only before routing rows are appended. Final classification/stage verification still requires every row and CHIM routing flags; undeclared or unselected missing cells are rejected. All 98 targeted checks across five modules pass, including three new ocean checklist regressions. Exact production conversion, native ocean behavior, image/package and delivery checks remain pending; coverage states are unchanged.

[CHIM-FRAME-STATIC-SEAM-40](bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1: whole-world metadata binding failed because tutorial barrel reference 172851 lacked its original CELL, while the original audit records [-2,-9]. A narrow source correction restores only that missing field before capture, rejecting nonempty wrong cells and every other identity/transform mismatch. Fifty focused Seyda/ownership checks pass, including three new semantic regressions. The preceding 4,247-test full-suite pass remains historical; the repaired world is pending. The prepared Linux source kit is held and undelivered. Native, image/package and playtest acceptance remain pending; coverage states are unchanged.

[CHIM-FRAME-STATIC-SEAM-40](bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1 image integration follow-up: added Seyda dependency numbers and model digests are checked against the world-index-bound source manifest before source-carrier static parity includes them. Frames without supplements retain prior behavior. The focused ownership/apron module now passes 33 checks, including five new semantic regressions and missing/rebound-model rejection. The issue remains OPEN; exact world rebuild, held-boundary/native and image/package checks remain pending.

[CHIM-FRAME-STATIC-SEAM-40](bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1: a source repair supplements only missing Seyda apron dependencies using the included original-cell owner's exact compiled mesh and textures, preserving original identity and unique ownership while translating frame-local origins. It targets rock reference 251397 and shell reference 461804; 32 focused ownership/apron checks pass. The rebuilt world and held boundary/native checks remain pending. Separately, independent normal interior/actor/UI conversion completed 2,451 files with unchanged source and inputs; it is not image, native or package acceptance. CHIM coverage states are unchanged. Earlier full-suite and world results remain bound to their preceding source; changed apron acceptance is pending.

[CHIM-FRAME-STATIC-SEAM-40](bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1: exact source validation completed 4,242 tests (4,236 passed, three Windows-only skips and three Census expected failures), with zero failures/errors; the matching engine compiled. The completed 369-frame world passed structural/source, modeled heap, host zone-walk and scoped stair gates. Of 547 boundary comparisons, 544 measured agreement and three remain held (237, 241, 242). Of 36 sampled models, 22 have matching face counts and unique face correspondence; 14 differ in collision-only versus visual representation and require payload/sprite/native review. These measurements do not establish visual severity or universal equivalence. Native captures, independent interior conversion, image assembly/readback and package acceptance remain pending; coverage states are unchanged. Stair evidence retains 15,348 advisory findings despite zero blocking failures.

15 October 2026: active preparation now targets v0.0.41-dev1. The planned final release title is **v0.0.41: Collisions And Boundaries**. Earlier source snapshots, checks and findings retain their recorded version identities; they do not establish acceptance of this development candidate. Matching source validation, completed image assembly/readback, native checks, packaging and delivery remain separate gates. See the [current development candidate](RELEASE-v0.0.41-dev1.md).

[BUILD-INVENTORY-PALETTE-41](bugs/BUILD-INVENTORY-PALETTE-41.md) — 15 October 2026, v0.0.41 source candidate: image assembly prepares inventory before the sky palette pass, which rejected current AWIC icons and AWI2/AWST metadata as unknown images. The source repair validates each inventory format at its exact path, remaps only icon pixels and preserves metadata bytes. Scoped evidence contains 15 passing palette checks and 2 passing inventory-asset checks on matching unchanged source. Actual image assembly, native verification, packaging and shipment remain pending.

[CHIM-FRAME-STATIC-SEAM-40](bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41 source candidate: the 941 world stopped at the unchanged ownership guard because ten explicitly deferred Seyda references reappeared through a named-town apron. The candidate applies the existing exact owner dispositions to named and regional neighbours alike. All ten original deferred IDs are verified and 38 focused checks pass. Fresh affected-world conversion and renewed boundary/memory checks remain pending; no coverage, native, package or maintainer acceptance is promoted.

[CHIM-MODEL-ARENA-RESERVE-41](bugs/CHIM-MODEL-ARENA-RESERVE-41.md) — 15 October 2026: exact allocation and predecessor-world checks remain separately recorded. The later 941 world stopped at its ownership guard because named aprons bypassed ten existing deferred-owner dispositions. The source-only disposition repair passes 38 focused checks; fresh world, boundary/model review and native/package acceptance remain pending.

[CHIM-RECIPE-APRON-SCOPE-41](bugs/CHIM-RECIPE-APRON-SCOPE-41.md) — 15 October 2026, v0.0.41 candidate: recipe repair converted all four affected frames with structural PASS. Three still failed the unchanged memory gate (peaks 6,957,632; 6,939,952; 6,644,768 bytes for (10,0), (10,1), (9,2)); (11,0) passed at 5,875,568 bytes. The separate placed-model reserve repair passes all four on identical world bytes. A complete successor world and recipe/model/sprite equivalence and native checks remain pending.

15 October 2026: exact-source validation completed 4,231 tests: 4,225 passed, three Windows-only skips and three tracked Census expected failures. The 71 focused tests and original-data readback across nine frame positions passed, consistently hiding 33 of 158 original references at stronghold state 6 while preserving unknown scripts. All 243 player resources are reusable after exact producer, input and file verification. Complete combined-world conversion, native comparison, packaging and shipment remain pending; coverage counts are unchanged.

## v0.0.52 (next), 25 October 2026

Decided by the maintainer on 25 October 2026: v0.0.51 ships what its third development build holds, so one update
does not carry too much; everything else moves here. First: the coloured light of rooms such as the Heart Chamber,
which the bake takes as brightness only ([INTERIOR-SUNLIGHT-COLOUR-51](BUGS.md)); the census office's own judged
light ([CENSUS-OFFICE-BRIGHT-32](bugs/CENSUS-OFFICE-BRIGHT-32.md)); a larger CHIM model zone
([CHIM-ZONE-BUDGET-33](bugs/CHIM-ZONE-BUDGET-33.md)); a builder that reruns only the stages whose inputs changed
([BUILD-CUTOFF-WHOLE-ANCESTOR-51](bugs/BUILD-CUTOFF-WHOLE-ANCESTOR-51.md)). Then the rest of the v0.0.51 list below.

The light input audit, started for v0.0.51 ([interior lighting](INTERIOR_LIGHTING.md#what-this-taught-us-every-light-input-first-then-any-brightness-knob)),
goes on in v0.0.52: every light value the game data holds, against what the bake and the engine use. Found so far:
rooms have no fog, though their cells carry a fog colour and density (the haze of the Dwemer ruins;
[INTERIOR-FOG-UNUSED-51](BUGS.md)), and the fog distance could also cut drawing in heavy rooms; outdoors, each
weather's ambient and sun colours are never used, only its sky and fog, so the land under an ash or blight storm
at Red Mountain keeps a neutral light ([WEATHER-AMBIENT-SUN-UNUSED-51](BUGS.md)). Requested with it: characters
shielding their eyes in ash and blight storms, as in Ald'ruhn ([ACTOR-STORM-POSE-51](BUGS.md)). Outdoor lights
without a mesh come later ([CHIM-MESHLESS-LIGHTS-33](bugs/CHIM-MESHLESS-LIGHTS-33.md)).

## v0.0.51: Let There Be More Inner Light, 25 October 2026

v0.0.51 takes up what moved from v0.0.50. First the fixes that could not wait, then the game work.

Done in the v0.0.51 release ([release notes](RELEASE-v0.0.51.md)); the interiors also get the light the original
gives them from above ([INTERIOR-SUNLIGHT-UNBAKED-51](bugs/INTERIOR-SUNLIGHT-UNBAKED-51.md)), and the interior
brightness default goes back to 1.0:

- **Builds rebuild less.** An engine edit no longer rebuilds the CHIM world, and a helper added to a shared module no
  longer does either ([BUILD-ENGINE-SOURCE-KEY-BROAD-36](bugs/BUILD-ENGINE-SOURCE-KEY-BROAD-36.md)).
- **32 MB is a real 32 MB.** The extra CHIM cache now takes spare Fast RAM from 4 MiB up: Akulakhan's Chamber loads,
  and the three old towns load with no "zone full" retry ([CHIM-AUTO-BANK-CLIFF-51](bugs/CHIM-AUTO-BANK-CLIFF-51.md)).
- **The music through loads.** The CHIM world's reads feed the music between slices, and every load reports its
  longest pause ([AUDIO-LOAD-29](BUGS.md)); the opening is judged on WinUAE.
- **The game's scripts, object state.** Enable, Disable, locks, OnActivate and Activate run (doors first), kept in
  saved games; EXPERIMENTAL, off by default ([the game's scripts](MWSCRIPT_BYTECODE.md)).
- **The game's scripts, message boxes.** MessageBox shows its text with its numbers; a box with buttons waits for
  the player's choice, and GetButtonPressed reads it (the same experimental switch).
- **The bug register.** Bugs seen in three releases are listed with why they are not fixed yet, and a release does
  not ship while one has no reason of record ([register rules](bugs/README.md)).

Moved to v0.0.52, in order: the remaining long-persisting bugs (fixed, or deferred by the maintainer); doors into rooms
that read the game's locks once a lock can be opened ([DOOR-LOAD-LOCKS-MISSING-51](BUGS.md)); the actor
sizes; Bloodmoon; the Morrowind-style UI boxes; the old town frames as ordinary CHIM region frames.

## v0.0.50: The Doors: Riders On The CHIM, 24 October 2026

Decided by the maintainer on 24 October 2026: v0.0.50 is "The Doors: Riders On The CHIM". Every exterior entrance in the game is linked to
its interior, and every way back out is linked too. Everything planned before for v0.0.50 (actor sizes, the game's
scripts and logic, object state in rooms, Bloodmoon and the Morrowind-style UI work) moves to v0.0.51. The builder
fixes already made on v0.0.50-dev (no hidden version read in the build stages, so a version change rebuilds only the
engine and the image) stay in v0.0.50.

Door audit of the published v0.0.49 image against every load door of the base game's master file: 3,133 load doors,
3,027 lead where they should and 106 do not yet.

- 85 ways back out of rooms around Vivec and Ebonheart (among them Hawkmoth Towers, the Grand Council Chambers, the
  East Empire warehouses, several Vivec waistworks and Telvanni Plaza): the builder did not look up the town frames
  for cells a town holds.
- 15 entrances that no door list carries (among them in Pelagiad, Ebonheart, Wolverine Hall, Moonmoth and Buckmoth
  Legion Forts, and some tombs, grottos and a shipwreck around Seyda Neen).
- 6 to check by hand (doors of the opening sequence's census office).

The doors of Balmora, Seyda Neen and Vivec and all room-to-room doors (914) are linked. Tracked as
[CHIM-REGION-DOORS-NO-ROOMS-48](bugs/CHIM-REGION-DOORS-NO-ROOMS-48.md), marked as persisting in v0.0.49.

The plan:

1. One door table for the whole world, built from the game's own door data (no new content: only the links the
   original data has).
2. Every door looked up in that table.
3. A build check that fails the image when a door the game can reach is not linked.

Done in the v0.0.50 release ([release notes](RELEASE-v0.0.50.md), [door graph](chim/DOOR_GRAPH.md)): all three steps,
the jail markers kept as rows of the table for the jail system and the game's scripts, and the opening's maps (the
prison ship, the pier, the census office) left with the doors the opening scene gives them. Next on this line: the old
town frames' geometry as ordinary CHIM region frames (later; the doors already use one table).

## Build turnaround first, 24 October 2026

Decided by the maintainer on 24 October 2026, during the v0.0.48 release builds: v0.0.49 starts with build
turnaround, before game logic and MWScript. Slow builds hold back every fix and feature behind them, and MWScript
will bring hundreds of small fix-and-rebuild loops.

| What (measured on the v0.0.48 builds) | Took | Target |
| --- | --- | --- |
| A release candidate from the previous development build's caches | about 1 h 35 min (28 of 43 stages rebuilt) | minutes, when the candidate is that build plus its version |
| The image step | 20 to 30 min, parts of it on 2 or 3 of 24 cores | the cores it has |
| A bug register update with its tests | 5 to 6 min on one core | seconds (cached), under a minute (parallel) |
| A gate with one failing test | 4 min | seconds (fail-fast) |

### Why the image is bigger than the original game

The original game's Data Files (Morrowind, Tribunal and Bloodmoon, with every video, sound and music file) take
1,840 MB. The v0.0.48 release image takes about 4 GB unpacked:

| Part of the v0.0.48 image | Size | Why |
| --- | --- | --- |
| Actor models | about 1.5 GB | Bloat: every character stores its own animation frames and skin (next section) |
| CHIM world | about 2.0 GB | Mostly a trade: Morrowind computes lighting, collision and visibility while it runs, on a PC with a graphics card; a 68040 cannot, so the build computes them once and stores them (baked lighting, collision hulls, visibility, distant terrain) |
| Interior store | about 320 MB | The same trade for the interiors |
| Sound, intro video, music | about 390 MB | Converted for the Amiga |

The actors are the part to cut. The world's share has never been measured by kind, so v0.0.51 also measures
what each byte of the CHIM world is (geometry, lighting, collision, visibility, textures, distant terrain), to keep the
trade that is needed and find anything stored twice.

### A disk layout that cannot dead-end

The image's partitions are planned by a small packer (`tools/layout_plan.py`). The release candidate builds of v0.0.48
stopped three times on it: the plan was made before the image step had finished adding and sharing files, and the
packer and its minimality check used two different rules for "fits". v0.0.48 plans once more from the staged files with
one rule ([build output](BUILD_OUTPUT.md#disk-layout-the-fewest-partitions-each-with-headroom)). The next version makes
it a solver that:

- **never throws away finished work**: a layout problem leaves every built file valid, and a retry redoes the layout
  only, in seconds, never the image or anything before it;
- **treats the partition count as a result**: a MiniWind on a fraction of one partition, the whole island on two or
  three, a larger world on many; fewer or more partitions than before is never an error by itself;
- **always has a fallback**: the minimal layout first, then one more partition, then units moved by size, then a second
  drive; a layout that is valid but not minimal is a warning with the bytes it would save, and only a payload that no
  layout can hold within the Amiga's limits stops, before anything is written;
- **uses one rule** for packing, checking and the free space left on each partition, tested with real payloads from a
  MiniWind up to far beyond the island.

### The actors get the CHIM rule: store once, place many times

The world shrank when it moved to CHIM: a rock, a wall or a house is stored once and placed thousands of times. The
actors never got that treatment, and they now take more space than the whole original game:

| Measured on 24 October 2026 | Size |
| --- | --- |
| The original game's Data Files (Morrowind, Tribunal, Bloodmoon, with music, video and sound) | 1,840 MB |
| `Morrowind.bsa`, the base game's meshes and textures | 297 MB |
| AmiWind's actor models in the v0.0.48 release candidate image | about 1,500 MB |

The reason is the model format. Morrowind animates people with a skeleton: one animation file is shared by every
humanoid, and the body parts (head, hair, chest, hands) are separate meshes shared between characters and assembled
when the game runs. The Quake model format the engine draws stores every vertex of every animation frame. Every NPC
record with its own look is baked into its own model of 64 full frames of about 1,500 vertices, roughly 400 to 700 KB,
for about 1,769 records ([ROOM-RESIDENT-MODELS-SIZE-48](bugs/ROOM-RESIDENT-MODELS-SIZE-48.md)). That is fast to draw
on a 68040 and very large on disk, and on an Amiga every megabyte on disk is also loading time.

Inside those 1,468 MB (4,225 complete models): 992 MB of animation frames and 587 MB of skin textures, one skin stored
inside every model. Two design faults double it: each character has a standing model and a separate "mover" model
for walking and fighting, although every character can move, so every body is stored twice, each copy with its own
skin. Every character keeps all of its animation; the size comes from storing things once
([where the modular NPC plan stands](MODULAR_NPCS.md#where-it-stands-24-october-2026)).

The work, measured before and after each step:

0. **One model per character, not two**: all animation groups in one set of frames, one skin.

1. **Finish the modular NPCs.** The design has existed since 9 October 2026: [Modular NPCs: every body part stored
   once, assembled per actor](MODULAR_NPCS.md) (1,726 distinct parts serve 3,500 appearances, each part used about 39
   times; [NPC-BAKED-WHOLE-DUPLICATION-33](bugs/NPC-BAKED-WHOLE-DUPLICATION-33.md)). The builder half exists: the
   parts library (`tools/npc_parts.py`, `--npc-models parts`, its own cache) converts each part once and composes
   appearances from recipes, but it is not the default and is used for the gallery only, and it still writes one
   complete model per actor, which saves build time but not disk. Never built: the residents made from the library
   (stage 2) and the engine composing actors from the shared parts at load time (stage 3), the half that ships only
   the parts. The room residents of v0.0.48 were baked whole, every one with its own frames. Stages 2 and 3 come
   first; the disk then falls to the parts library.
2. **Frames per role.** A merchant behind a counter never runs; frames nobody will see are not stored.
3. **Compact frames**, and frames shared between characters wherever they come out the same.
4. **A size budget** for the actors in the build's size ledger, so the payload can never again grow unnoticed.

The work:

1. **The AmiWind version keys nothing that does not show it.** A version-only change (a release candidate becoming
   the final) rebuilt the whole CHIM world, because the world's records carried the version
   ([BUILD-CHIM-KEY-VERSION-48](bugs/BUILD-CHIM-KEY-VERSION-48.md)). The CHIM label already has this treatment: a
   label change keys only what shows the label, the rest counts its compatibility line
   (`config/chim-compatibility.json`). The AmiWind version gets the same: it moves out of the CHIM world's records into
   the image receipts, and a version-only change rebuilds only the stages whose outputs show it.
2. **Other over-broad keys**: engine sources in the keys of stages that never use them
   ([BUILD-ENGINE-SOURCE-KEY-BROAD-36](bugs/BUILD-ENGINE-SOURCE-KEY-BROAD-36.md)), and stages that read files their
   key leaves out and so rerun on every reuse
   ([BUILD-STAGE-READS-UNFINGERPRINTED-48](bugs/BUILD-STAGE-READS-UNFINGERPRINTED-48.md)).
3. **Development builds carry the NPC gallery from the cache**, so a release candidate never builds it fresh.
4. **The image step on its cores**
   ([BUILD-IMAGE-WORLD-READ-FRAMES-47](bugs/BUILD-IMAGE-WORLD-READ-FRAMES-47.md)).
5. **The bug register's own tools**: cached and parallel, with size warnings at the moment a bug is added.
6. **A realistic resource plan**: it plans with the measured overlap of stages, not every stage at full speed at once.

Each item is measured before and after on the same work and kept by a test. A release candidate is the last passing
development build plus its version and notes, and a final is that candidate plus its version. The final is rebuilt
from the finished candidate's caches: a test plans that build and fails if any stage but the engine and the image would
run again, so the image step (assembled and checked fresh for every release) is the whole cost of a final.

### One standard timedemo for real Amigas (v0.0.49)

Two real machines have now reported a frame rate: an A4000 with a 68060 at 100 MHz (AGA, an earlier build, about
0.2 frames per second) and an A3000 with a 68060 at 80 MHz through RTG (the tester's own RTG changes on a build from the public repository of
22 October 2026, the v0.0.48-dev1 pre-release, about 0.6 to 0.7 on a short timedemo). The two cannot be compared: each tester recorded their own walk with their own settings, and the
hardware page did not say how to show the frame rate (BENCH-NO-STANDARD-DEMO-48 in the [bug register](BUGS.md)).
For v0.0.49:

1. **A standard demo in every image**: one fixed walk in Balmora and one outdoors, recorded once on the shipped CHIM
   world and kept with the source, so every machine draws the same frames.
2. **One command to run it**: plays the standard demos with `timedemo`, and writes the machine (CPU, FPU, clock,
   Chip and Fast RAM, AGA or RTG), the settings that change the frame (screen size, detail, the CHIM caches), the
   frame rate and the renderer counters to one file to send back.
3. **The hardware page leads with it** ([AmiWind on real hardware](REAL_HARDWARE.md)), and the results go into one
   table there, machine by machine.
4. **The same demos in the emulator** on every development build, so a frame-cost change shows up before a release,
   and an emulator figure sits beside every real one.

Until then, the steps on the hardware page give a comparable number by hand.

## Test on Amiberry, 21 October 2026

Amiberry is an open-source Amiga emulator, and it is the emulator inside the upcoming THEA1200, an A1200 replica
with CPU JIT and FPU JIT options and adjustable RAM (one visitor's report saw 32 MB of Fast RAM). A reviewer reports that
it loads WHDLoad installs and floppy, hard drive and CD images from a USB stick, offers RTG and switchable chipsets
(OCS, ECS, AGA), and launches on 4 December 2026 (an earlier report said June; the launch was delayed). Games that
run well in it will be what many people try first, so AmiWind should be checked there.

- [ ] Build Amiberry from its source in a Docker image (a new image, so the maintainer's go comes first).
- [ ] Boot the AmiWind hard disk image directly, with no Workbench needed.
- [ ] Measure with 2 MB Chip, 32 MB Fast, the CPU JIT and the FPU JIT on, with the same scripted routes as the
  other emulators ([relative numbers](REAL_HARDWARE.md#first-measure-then-play) until a real figure exists).

Open questions: the most RAM the replica can have; whether the reported hard drive images from USB take the AmiWind image (to confirm); whether its JIT runs
the 68040 code the game uses correctly; and its real speed (a claimed 68060 at 70 MHz is not a measurement).

## 30-minute rebuilds, 20 October 2026

The goal, set by the maintainer on 20 October 2026: a build that can load what it already made from the cache takes
30 minutes at most, wherever the change was. A build is the tool every fix, test and release passes through, so
every hour it takes is an hour taken from the game.

Two reference times show how far off that is:

- The v0.0.46-dev1 rebuild (try 2) took 3 h 02 min after one function of the shared collision converter changed: the
  CHIM stage alone took 2 h 33 min, the NPC gallery 36 min and the image step 15 min 38 s.
- The v0.0.46 release build reused the dev1 build and took about 45 minutes (an estimate from its log while it was
  still running; the real total replaces this figure when the build has finished).

The work, in order:

1. **Stop needless rebuilds.** A rebuilt unit whose output is byte-identical (by SHA-256) must not rebuild what comes
   after it, and every key must cover exactly the inputs its unit reads.
   [BUILD-CHIM-CONVERTER-CHANGE-FULL-REBUILD-46](bugs/BUILD-CHIM-CONVERTER-CHANGE-FULL-REBUILD-46.md),
   [BUILD-CHIM-VIS-ROWS-KEY-BROAD-46](bugs/BUILD-CHIM-VIS-ROWS-KEY-BROAD-46.md),
   [BUILD-NPC-GALLERY-REBUILT-46](bugs/BUILD-NPC-GALLERY-REBUILT-46.md),
   [BUILD-CACHE-NO-CUTOFF-33](bugs/BUILD-CACHE-NO-CUTOFF-33.md),
   [BUILD-REUSE-SCHEDULER-TOP-45](bugs/BUILD-REUSE-SCHEDULER-TOP-45.md).
2. **Stair walks only where something changed.** Walk the flights, the reach around a changed piece and a watch
   list, not the island (BUILD-STAIR-WALK-SCOPE-KEY-46), and in the long run replace the walk by a check from the
   game's own collision data (the next section,
   [BUILD-STAIR-WALK-BRUTE-FORCE-46](bugs/BUILD-STAIR-WALK-BRUTE-FORCE-46.md)).
3. **Use the whole machine, in every stage.** The 20 October build left cores idle in these places, each tracked:
   - the CHIM areas side by side: 50 min at 14.1 of 24 cores, big frames last
     ([BUILD-CHIM-REGION-FRAMES-TAIL-43](bugs/BUILD-CHIM-REGION-FRAMES-TAIL-43.md));
   - queues that sit with units waiting and none running between CHIM phases, and the serial pack
     ([BUILD-CHIM-SERIAL-SECTIONS-44](bugs/BUILD-CHIM-SERIAL-SECTIONS-44.md));
   - validation, heap gate and zone walk made of many tiny units, to be batched per worker
     ([BUILD-CHIM-STAGE-SERIAL-TAIL-36](bugs/BUILD-CHIM-STAGE-SERIAL-TAIL-36.md));
   - the NPC gallery on 11 cores while CHIM ran beside it
     ([BUILD-NPC-GALLERY-REBUILT-46](bugs/BUILD-NPC-GALLERY-REBUILT-46.md));
   - the image step: 15 min 38 s at 8.9 of 24 cores, partitions written one after another, a 281 s stall
     ([BUILD-IMAGE-UNDERUSED-32](bugs/BUILD-IMAGE-UNDERUSED-32.md)), the stair-walk tail of two single rooms
     ([BUILD-IMAGE-STAIR-WALK-CORES-43](bugs/BUILD-IMAGE-STAIR-WALK-CORES-43.md)), the body bake
     ([BUILD-BODY-BAKE-SLOWER-44](bugs/BUILD-BODY-BAKE-SLOWER-44.md));
   - small stages under half their cores: chim-town-seyda, hand-catalog, interior, intro, census
     ([BUILD-IDLE-STAGES-33](bugs/BUILD-IDLE-STAGES-33.md));
   - the resident-map step 55 to 60 percent slower than its baseline
     ([BUILD-RESIDENT-MAP-SLOWER-46](bugs/BUILD-RESIDENT-MAP-SLOWER-46.md)).
4. **The build says it.** The build summary's "Needs attention" list gets an entry when a build that used its cache
   still takes more than 30 minutes, naming the stages that used the time.

## Collision from what the game already knows, 20 October 2026

Decided for the project, 20 October 2026. Today the converter cuts each drawn mesh into convex collision pieces as
well as it can, and the builder then walks every step and ramp of the island to find out whether the result can be
walked: about 1.5 million stair walks in a full build of the v0.0.46-dev1 line, and hours of build time. That is
brute force on an answer the game already holds: each Morrowind mesh says what the player collides with (its
collision node, or the drawn mesh when it has none), and the movement rules (the highest step, the steepest walkable
slope, the player's size) are known from the original game and OpenMW. The dock walkway repair of 20 October
showed the cost of the old way: keeping every point of each collision piece added 55 MB of stored planes and nodes
over the island and pushed six frames over the memory budget.

The plan, in order:

1. A second collision method beside today's, selected by a builder switch. It builds collision from the game's
   collision data and the movement rules, so stairs and walkways are walkable by construction: one plate per tread
   or an invisible ramp under a flight, while the steps are still drawn as steps.
2. A check that is arithmetic instead of a walk: no standing surface lower than drawn by more than a step, no step
   higher than the step limit. Seconds instead of hours; the stair walk stays as a sample.
3. Nothing is removed. Today's converter, stair rules, stair gate and walk records stay as the first method, and the
   results they have already recorded (every passed and failed walk, by the SHA-256 of the data walked) are kept as
   the reference the new method is compared against. Each kept result says how it was made: which method, which
   rules and which build (the stair records already carry that provenance), so a later comparison can always tell
   "this is what we did then, and with which workflow".
4. A/B of both methods on the same frames: memory (bytes, planes, nodes), build time, the stair walk sample and
   in-game clips at stairs, docks and ladders.
5. The first test set is the places where we already know the answer: every flight that passes today (Balmora,
   Seyda Neen, Vivec, the Temple) must give the same result, and every fixed stair or collision bug must stay fixed.
   The new method becomes the default only after that.

Tracked as [BUILD-STAIR-WALK-BRUTE-FORCE-46](bugs/BUILD-STAIR-WALK-BRUTE-FORCE-46.md); the walkway memory cost as
[CHIM-VIVEC-DOCK-WALKWAY-43](bugs/CHIM-VIVEC-DOCK-WALKWAY-43.md).

## Cell crossings: one continuous world, 19 October 2026

v0.0.45 reads the frames around the player into spare Fast RAM, which roughly halves a crossing on a 128 MiB
machine. What is left is mostly the engine restarting the game for every new frame: measured on the v0.0.44 data,
about 220 to 260 ms of every crossing, the same with 16 or 128 MiB, because today every CHIM frame is its own
Quake map and a crossing is a full level change (the game-logic half respawns everything, the display half
reconnects and reloads its model and sound lists).

The next method ("type 1") makes the outdoors one continuous world, with the frames as a sliding window:

(Status 20 October 2026: a prototype exists but creates no people, creatures, doors or plants in the frames it
joins, so it is not the default and its first timings are not comparable with the level change; see
[Cell crossings](chim/CELL_CROSSINGS.md).)

- **Nothing restarts.** The game-logic and display halves stay connected the whole time; a frame is only which part
  of the island is loaded, not a map.
- **The origin moves, rarely.** Since v0.0.36 the engine uses wide coordinates by default: ±32,768 units
  (`engine/aga/src/aw_coord.h`), instead of Quake's ±4,096. A cell is 2,048 units wide, so the island is larger than
  that range, but a rebase is a separate event from crossing a border: it is triggered by how far the loaded
  surroundings reach, with a margin, and many borders are crossed at one origin. A rebase moves the loaded
  geometry too (plane distances, vertices, bounds, texture offsets, as CHIM's terrain shift already does) and the
  entities, as one coherent step. The one-cell frames are not forced by the coordinate range.
- **Entities come and go by distance.** The next frame's NPCs and objects spawn a little before the border and the
  last frame's are removed a little after, with a margin so standing on the line does not flicker; the read-ahead
  already has their data in memory.
- **One composite world from several frames.** CHIM already grafts its streamed chunks into one world model for
  rendering, collision and visibility; it is extended so the active chunks can come from several frames, with one
  owner per physical chunk so overlapping terrain margins are never loaded twice.
- **Memory that does not depend on a level reset.** Today a level change also frees entity data in bulk (entity
  strings, for example, are freed only when the map's memory is reset). Entities that come and go need their own
  reclaimable or shared memory, checked by walking the same area again and again with memory staying bounded.
- **Model and sound lists that grow.** Quake fixes these lists per map, with a hard limit of 256 each; type 1 adds
  entries during play. Freeing an asset's loaded data and reusing its list slot are different things: an entity can
  still refer to a slot, so slots get stable identities and are reused only when nothing refers to them. CHIM
  scenery already needs no list slots; this concerns actors, animations, sounds and scripted entities.
- **Saves keep a stable place.** A save records the source cell and the position inside it plus the changed object
  state, so a game restores the same way whatever was loaded.
- **Spread over many frames.** Each step runs in small pieces over many rendered frames before the border, so no
  single frame pays for the switch.

Today's method ("type 0", the level change) stays selectable, and Quake's networking stays in the code: the Vivec
Arena duel idea is for the indoor Arena, an ordinary level. The order of work, each step measured: the restart
split by its parts to find what is thrown away and rebuilt although it is the same in neighbouring frames; a design
note reviewed for its weak points (the origin shift, the model-list limit, saved games); a prototype in a small
sandbox of 2×2 frames; an A/B against type 0 on the same crossing route; then the whole island
([plan section 1](PLAN-v0.0.45.md#1-cell-crossings); the full design: [Cell crossings](chim/CELL_CROSSINGS.md)).

### Decisions of 20 October 2026

Decided for the project on the evening of 20 October 2026, in plain words:

1. **One streamed world outdoors; Quake levels only behind doors.** The outdoors is one continuous world and a
   level change happens when the player goes through a door into an interior. This stands as decided at noon.
2. **The streamed crossing is not the default yet.** The prototype of type 1 (`chim crossing 1`, on the branch
   v0.0.46-stream-type1; its notes join [Cell crossings](chim/CELL_CROSSINGS.md) when it is merged) becomes the
   default only when it carries the world's entities. Until then the level change (type 0) stays the default.
3. **What it needs, in order:**
   1. One world-state change list, keyed by reference ID: moved, dead and following NPCs, picked plants, opened
      doors and the contents of containers. A frame that joins the window is its base data plus its changes; a frame
      that leaves writes its state back; saves write the same list. This is the object and container state item of
      [the road after v0.0.44](#the-road-after-v0044-19-october-2026), with machines that have little RAM keeping
      part of the list on disk.
   2. Entity windowing: the NPCs, creatures, doors and plants of every frame in the window exist, each with its
      state.
   3. Followers and escorts cross frame borders with the player. Some quests, the main quest included, cannot be
      finished otherwise, so the companion test must pass with the streamed crossing as it does with the level
      change, with behaviour following the original game and OpenMW's rules.
   4. NPC traversal across frame borders.
4. **Every comparison like for like.** Both methods must do the same work before a figure is reported. The first
   prototype figures compared a crossing that creates the new frame's people with one that creates none; they are
   marked as not comparable and are not used as a speed-up.
5. **The menu.** The old read-ahead experiment (the Load method and Read-ahead buffer lines, built for the region
   maps from before CHIM) leaves the menu; its code stays. One Options line shows the active crossing method.

## The road after v0.0.44, 19 October 2026

Decided for the project on 19 October 2026, in this order. Each step ends in a build that works and is shipped,
as with the outdoors: the world first, then what is in it, then what happens in it.

1. **v0.0.44: By Azura's Trees!** Published 19 October 2026: the patch release with the Bitter Coast tree fix
   ([CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43](bugs/CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43.md); [release notes](RELEASE-v0.0.44.md)).
2. **Bug fixes, cell crossings first.** Walking from one CHIM cell into the next still pauses the game, worst at
   cell corners ([CHIM-CROSSING-SLUGGISH-43](bugs/CHIM-CROSSING-SLUGGISH-43.md)). AmiWind uses the RAM an
   accelerator card has: 16 MB stays the baseline that must work, and memory past it holds the neighbouring frames
   ready, so a crossing becomes a copy in memory instead of a disk read. Loading is spread over many rendered
   frames before the border instead of one pause at it. Every change is an A/B/C run on a fixed route with edge and
   corner crossings, measured with the profiler at 16 MB and at 128 MB, and kept only when it wins. The cache
   adapts to the memory there is: 16 MB keeps what fits, 128 MB or 1 GiB keep more frames ready. It is designed
   for the load still to come: most of the open world has no NPC placements yet, and each crossing will also bring
   people, their models and their state, so those are prepared before the border too and measured on a busy town
   frame with its people in place. The open bugs
   from the v0.0.43 playtests follow, among them rocks that do not close up
   ([CHIM-ROCKS-OPEN-SHELLS-43](bugs/CHIM-ROCKS-OPEN-SHELLS-43.md)).
   **Then, before the interiors: one model at any angle.** Decided for the project, 19 October 2026: right after
   the cell crossings, a placement records its full rotation and scale, and the engine turns one shared model when
   it draws it, instead of storing a separate copy of the model for every tilt or scale. Measured on the v0.0.45
   world: 33,426 stored models made from only 1,400 distinct meshes, 26,477 of them tilted variants (550 MB), and
   91 % of the 713 MB of model data copies beyond one per mesh (barnacles alone in 2,022 variants)
   ([CHIM-TILT-VARIANTS-SPLIT-33](bugs/CHIM-TILT-VARIANTS-SPLIT-33.md)); the CHIM world is 1.32 GB of a 2.76 GB
   payload. One shared model per mesh could save up to about 650 MB, less what collision copies keep. The first step
   is a study, before any code: how the engine draws a turned model today (`R_RotateBmodel`: the viewer is moved
   into the model's frame once per model, with all three angles), how far its collision with turned models holds
   (the trace is turned into the model's frame but the player's box is not, so a tilted model is only approximated),
   what CHIM's placements do (yaw only), and what scale needs, which Quake does not have: the drawing transform,
   texture scale on scaled surfaces, the bounds used for culling, and collision sizes; then the cost per model on
   the 68040 and 68060, and the collision decision. The interiors need the
   same mechanism, so it comes first. Drawing a turned model is Quake's own path; collision is the open question,
   because Quake's movement code only collides with unturned models: either a small baked collision copy stays, or
   the collision code learns rotation, chosen by measurements on the 68040 and 68060 profiles. A world format and
   engine step, with the old storage kept selectable.
3. **Every interior of the base game, with an interior progress tracker, and interiors on CHIM too.** Measured on
   19 October 2026: the base game has 1,328 interiors; 176 are in the game today and 919 on Vvardenfell are not
   converted yet ([checklist](PLAN-v0.0.45.md#3-every-interior-of-the-base-game)). Today every interior is its own
   Quake map that carries its own copy of every mesh and texture it uses, about 2 MB a room. About 950 more rooms
   that way would add about 2 GB to an image of 3.62 GB, past the 4 GiB a drive image may hold. So the interiors go
   the way the outdoors went: each mesh and texture stored once in the shared CHIM store and placed by reference in
   every room that uses it. That comes first; then the entrance audit, the tracker and the conversion batches
   described [below](#next-the-outdoors-complete-then-every-entrance-and-every-interior-18-october-2026).
   Status, 22 October 2026: CHIM rooms are being built on the v0.0.48 line (design:
   [INTERIORS ON CHIM](chim/INTERIOR_STORE.md)). Measured so far: 55 test rooms on a store of 20.7 MB plus 0.59 MB of
   room maps, against 79.3 MB of today's room maps (about 3.7 times smaller); frame time, memory and door load time
   in game are not measured yet. Next goal: every interior and its exterior entrances in the game without bloating
   the image; then the game logic (MWScript) is measured.
   The rooms set aside (water, lava, over the size limit, Levitate-only, no entrance area) and how each comes back are in
   [the door graph page](chim/DOOR_GRAPH.md#rooms-set-aside-and-how-they-come-back).
4. **Object and container state.** The game remembers what the player changes: an object moved, taken or
   dropped, a door unlocked, a container's contents. As in the original game, only the changes are stored, each
   against the object's original record in the game data, so an untouched object or an unopened chest costs
   nothing. The changes are grouped by cell and applied as a cell loads. With 16 MB, only the cells around the
   player keep their changes in memory and the rest wait in a state file on disk; with more RAM they stay in
   memory. The saved game is that state.
5. **NPC placement.** The people and creatures of every town and interior in their places, with their inventories
   held in the object state of step 4.
6. **MWScript compiled by the builder.** The game's scripts become compact bytecode run as one state machine
   (details [below](#next-the-outdoors-complete-then-every-entrance-and-every-interior-18-october-2026)): the
   globals, journal indexes and each object's script values as small tables, scripts as checks that run only when
   their inputs change, the whole machine measured for its size and its cost per frame on the 68040 and 68060.
   Status, 23 October 2026: started with audio, at the maintainer's request ("all of the audio is already in the
   game so we should start utilizing it as per MWscript"); design and measurements in
   [MWSCRIPT_BYTECODE.md](MWSCRIPT_BYTECODE.md). Every script of the three masters is measured (1,207 scripts,
   942,627 bytes of source; 251 distinct functions); the builder compiles them into one file of typed bytecode
   (156,838 bytes of code, 39 % of the original editor's compiled form) with the sounds, voices and music they name
   mapped by index to the media catalogue's converted files. The engine's interpreter runs the audio, journal,
   globals, timers and distance tests (142 scripts whole, more in part); everything else is "not yet", logged once.
   EXPERIMENTAL: off by default (`dbg mwscript on`) until the in-game check. 55 % of the scripts also need AI packages,
   inventory, combat, spells or positioning, and most need object state (step 4) first.
7. **Tribunal and Bloodmoon included, the base game alone still buildable.** Decided for the project, 22 October
   2026. The expansions are part of AmiWind: Bloodmoon's Solstheim (its 144 exterior cells, then its interiors from
   the same shared interior store) and Tribunal's Mournhold, whose way in needs the scripts of step 6. A player who
   owns only the base game can still build it. The builder's first search of the game data reports which masters it
   found; if `Tribunal.esm` or `Bloodmoon.esm` is missing, it warns at once, names the missing expansion, and builds
   without it, and the summary at the end of the build repeats the warning: "Bloodmoon (and/or Tribunal) was not
   found and is not included in this build". Nothing that belongs to a missing expansion is referenced by the image.
   Bloodmoon comes first (the maintainer, 23 October 2026: "an essential part of Morrowind"): right after the
   base game's interiors and actors are in, Solstheim's 144 exterior cells go to CHIM the way Vvardenfell's did, then
   its 96 rooms by batch from the same door graph and room store, with its actors. Both expansions' audio and video
   are already converted into AmiWind by default, so what remains is the territory, not the media.

## Interiors: shell baked, takeable things as objects

Decided for the project, 21 October 2026. The maintainer: interiors cannot be fully pre-baked, because rooms are where
the things on tables and shelves are, things you can take. So an interior has two kinds of content:

- **The shell:** walls, floors, stairs, fixed furniture and fixtures. Baked into the map as today (lightmaps,
  visibility and collision compiled once).
- **Everything that can be taken, moved or opened:** items on tables and shelves, books, bottles, plates, weapons on
  racks, containers and their contents, ingredients. Never baked. At build time the builder splits each room's
  references; every such reference goes into a per-room object table, one shared model per item type placed by
  reference (the pattern of the outdoor actor table). In the engine each is a Quake entity, drawn with the light
  sampled from the baked lightmap at its spot. Its state (taken, moved, emptied) is kept per room in the save, on disk
  on machines with little RAM.

Measured first: a pass counts the takeable objects per room (entities, memory, draw cost on a 68040); a busy room may
group its untouched clutter into one object until the player touches it. Proven small in v0.0.47 with indoor mushroom
picking ([HARVEST-INTERIOR-PICK-47](bugs/HARVEST-INTERIOR-PICK-47.md)). Order: interiors next after v0.0.47, then
object and container state, then the game logic (MWScript compiled to bytecode). Report:
[INTERIOR-PLACED-ITEMS-47](bugs/INTERIOR-PLACED-ITEMS-47.md).

Status, 22 October 2026: CHIM rooms are being built on the v0.0.48 line (design:
[INTERIORS ON CHIM](chim/INTERIOR_STORE.md)). Measured so far: 55 test rooms on a store of 20.7 MB plus 0.59 MB of
room maps, against 79.3 MB of today's room maps (about 3.7 times smaller); speed and memory in game are not measured
yet. Next goal: every interior and its exterior entrances in the game without bloating the image; then the game logic
(MWScript) is measured.

## Distant views without pop-in, and the screen the Amiga need not redraw, 19 October 2026

Two engine items from the maintainer's playtest of v0.0.44, both measured before anything becomes a default.

**Nothing is cut where the fog is still see-through.** Bridges that appear piece by piece and hillsides seen
through before they turn solid ([CHIM-BRIDGE-POP-PIECES-44](bugs/CHIM-BRIDGE-POP-PIECES-44.md),
[HORIZON-POP-29](BUGS.md#fix-index), [HORIZON-HOLES-31](bugs/HORIZON-HOLES-31.md),
[VIVEC-DISTANT-BRIDGES-32](bugs/VIVEC-DISTANT-BRIDGES-32.md)) all come from a distance cut made while the fog in
front of it is not yet fully opaque. The maintainer's examples (19 October 2026): Vivec's walkways cut in the
middle at a distance, Balmora's walls, hillsides and the Ghostfence; all of them should stay solid. Proposed order,
cheapest first: (1) the fog rule below, a settings and builder change with no new drawing code; (2) long structures
(walkways, town walls, the Ghostfence) cut as one piece at one distance, so they fade into the fog together instead
of losing their middle; (3) the far shell in flat fog colour, measured in the sandbox; (4) as a fallback if the
68040 cannot afford (3), a painted horizon: a 360-degree silhouette strip per frame, rendered by the builder and
drawn like the sky with no 3D work, flat (no parallax) and so only for what lies far behind the fog. Games with fog
and little compute avoid this with one rule: the fog reaches
full opacity before anything is dropped, so an object only ever emerges from the haze. First step: every distance
cut (object draw distance, frame and chunk edges, the far band) at or beyond the fog's full-opacity distance, per
region, with its cost measured, and a builder check that refuses a cut closer than the fog end. Status, 20
October 2026: (1) and (2) are in source as the switches `dbg fog rule` and `dbg cut groups` (bits of the far detail setting `aw_cull`; structures found by the
CHIM builder, a `.cut` sidecar per frame map) with the builder's fog check; both off until the maintainer has seen
the in-game A/B; the inventory of every cut and the cost on paper are on
[CHIM-BRIDGE-POP-PIECES-44](bugs/CHIM-BRIDGE-POP-PIECES-44.md). Then the
[island cut-out](DISTANT_TERRAIN.md#horizon-ponderings-the-island-cut-out-19-october-2026) for the far skyline.
Its form, settled the same day: one opaque far shell of the whole island (terrain plus the silhouettes of
buildings, towers and bridges) in the fog's colour, drawn through the engine's existing solid-surface path
(`D_DrawSolidSurface` in our AmiQuake source) as its own surface class with real depth, built as one coherent
model, loaded before the detail it stands in for; its edge cost against the work it saves is measured on the
68040 and 68060 profiles first. The shell and the world streaming are designed as one system (one handover
distance tied to the fog, the shell split along the streamed chunks, a late chunk showing its silhouette instead of
a hole): [near and far as one system](chim/CELL_CROSSINGS.md#near-and-far-as-one-system-upcoming-direction). Once it
passes the sandbox measurement it becomes the default distant drawing; today's horizon methods stay selectable
(decided for the project, 19 October 2026).

**Only the 3D window goes through the conversion.** The engine converts its chunky picture to AGA's bitplanes
every frame, from the top row down to the lowest changed area (Quake's update rectangles), so the HUD's lines
below the 3D view are skipped only when nothing in the HUD changed. To measure: rows converted per frame next to
the conversion time, in a normal build and with the debug HUD. If the HUD is changed most frames, it moves to its
own planar screen area set up by the Copper, redrawn only where a value changes, and the conversion covers only
the 3D window. Hardware sprites take the small moving overlays (crosshair, pointer, text cursor); they cost Chip
RAM DMA and few colours, and a scanline holds at most eight, so they are not for whole HUD bars or particles.
Measured on the emulator first, and on a real accelerated Amiga before any claim.

## Colour: AGA ramps for the ash, the blight and Red Mountain, 19 October 2026

Decided for the project on 19 October 2026: AmiWind uses what AGA can show. AGA picks each of its 256 on-screen colours
from 16.7 million (24-bit), so smooth ramps are possible where the old 12-bit chipset banded them. Measured on the
v0.0.44-dev1 palette: of a 160-colour grey, ash, brown, rust and red chart (20 hues by 8 brightness steps), today's
single shared 256-colour palette has only 56 near matches; dark reds fall into brown, the darkest steps lose their
red, and the mid reds jump. A smooth grey to red ramp gets 11 colours.

The plan:

1. **A reserved ash and red ramp** of about 30 to 40 palette slots for the Ashlands, the Red Mountain region and
   blight storms, chosen from the original game's textures and fog colours of those regions.
2. **Colour grading per region:** fog, sky and light tinted toward that ramp where the original weather does it
   (ash storms, blight storms), measured for what it costs per frame.
3. **A palette per region,** if one shared palette cannot hold it: AGA can switch its 256 colours between areas, so
   the Ashlands can have more of their reds than the Bitter Coast needs. Decided the same day: a gradient, not a
   switch: the closer the player is to Red Mountain, the more of the palette goes to the ash and red ramp, in rings
   around the mountain, so the colours shift as the land does: the blue sky toward the mountain meets more and more
   grey, brown and red, so Red Mountain looks menacing before the player gets there. Measured first: what the switch costs at a
   region border and what the surface cache needs.

4. **Ash and blight storms with AmiQuake's own particles** (maintainer, 19 October 2026): windblown ash and blight
   dust from Quake's particle system (`r_part.c`: the pool, its ramps and per-particle velocity and gravity),
   blown along the storm's wind and coloured from the ash and red ramp, with the count set by what a frame can
   afford on the 68040 and 68060. No new engine feature first; measured for its cost per frame.

Every step is an A/B against the original game at the same place and time, with stills and a short clip.

## Next: the outdoors complete, then every entrance and every interior, 18 October 2026

**v0.0.43, published 19 October 2026: every exterior cell of Vvardenfell on CHIM** (1,409 cells: 1,348 in
one-cell region frames and 61 in town frames, [what these numbers count](chim/CELL_TRACKER.md#what-we-count); [release notes](RELEASE-v0.0.43.md)). **v0.0.44: By Azura's Trees!**, the patch
release that followed, was published on 19 October 2026: the trunk shape guard had made the Bitter Coast trees too
large for memory, and v0.0.44 fixes it ([CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43](bugs/CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43.md);
[release notes](RELEASE-v0.0.44.md)). After it come bug fixes, the pauses when crossing from cell to cell first, and
every interior missing from the base game (below; step by step in the [v0.0.45 plan](PLAN-v0.0.45.md)).

History, as written during v0.0.43 (all of it is done; v0.0.43 shipped the whole outdoors): after v0.0.43-dev2 the cells still classic
are the ones held by the stair walk (Ald-ruhn, Maar Gan, Suran and one rope bridge cell, with the town cells
around them), eight Balmora border cells and fourteen open-sea cells; the last two are fixed, the stair fix is
in the shared converter. v0.0.43-dev3 is meant to be the first build with the whole outdoors on CHIM
([progress tracker](chim/PROGRESS_TRACKER.md#current-state-24-october-2026)).

**Milestone, 18 October 2026: every exterior cell converted to CHIM.** The v0.0.43-dev3 build converted the
whole outdoors of Vvardenfell to CHIM in one run (1,351 frames: 1,348 region frames and 3 town frames; the stair gate passed every flight it walks, but it
does not catch everything: walkways where the player sinks into the planks, such as the Vivec docks, are still
broken, [CHIM-VIVEC-DOCK-WALKWAY-43](bugs/CHIM-VIVEC-DOCK-WALKWAY-43.md)).
Its image step then stopped on a check that had never seen a world with no classic maps left
([BUILD-IMAGE-ALL-CHIM-PREFLIGHT-43](bugs/BUILD-IMAGE-ALL-CHIM-PREFLIGHT-43.md)); the check now counts the CHIM
maps, and the whole outdoors shipped in v0.0.43.

**After the v0.0.44 patch, decided for the project on 18 October 2026: entrances and interiors.**

1. **An entrance audit, island-wide.** From the game data, every load door (outside to inside, inside to
   inside, inside to outside) is checked against the build: the destination interior is converted and in the
   image, the door shows its prompt, the player arrives standing inside the room and not in a wall, and a door
   leads back near the entrance. Doors to rooms left out on purpose are named with the reason. It is a data
   check, not a walk through every door.
2. **An interior progress tracker,** the interior twin of the exterior cell tracker: one row per interior cell
   with its entrances, whether it is converted and in which build, its limits (inline models, room memory,
   coordinate range), its audits (stairs, lighting, actors, harvestables) and a status colour with the reason
   for anything left out. It is shown in the Toolkit, linked from the doors on the exterior map, published as a
   reference with every build, and fed after every build like the cell tracker.
3. **Missing interiors become conversion batches,** through the interior procedure
   ([interiors over a limit](INTERIOR_SECTIONS.md)): numerous decorative meshes as sprites, per-mesh recipes,
   sections cut at hallways and doorways. Vivec's rooms left out so far come first.
4. **Ambient sound from the game's own sound markers, if it is cheap enough to fit, decided for the project on
   18 October 2026.** Morrowind places invisible marker objects that play a looping sound where they stand (boats
   creaking at a pier, a hull under the planks) or carry an effect (waterfall mist, steam, sprays): 2,565 sound
   markers and 778 effect markers across the game data. Since v0.0.43 the builder keeps them as invisible
   objects, never drawn and never solid, and writes a table of them with each build (position, sound file,
   volume and range from the original records). The sound markers then become looping ambient sounds through
   Quake's own static sounds, with their range from the original record (a fallback where the record stores
   none), measured for their cost in the mixer. The effect markers follow later, as Quake particle emitters.

**After the interiors and the fixes that come with them: the game logic.** With the world and its rooms in
place, the work turns to what happens in it: MWScript, the game's own script language, compiled by the builder
from the original scripts in the game data (below); dialogue conditions and quests; NPC and creature behaviour; combat, magic,
inventory and services. As everywhere else, the original game's records and behaviour are the reference for what
it should do, OpenMW the readable reference for how it fits together, and AmiQuake's machinery (QuakeC, entities,
the server loop) the means, measured for its cost on the 68040 and 68060.

**MWScript compiled at build time, decided for the project on 18 October 2026.** The Amiga does not interpret the
game's script text while it plays. The builder parses every script once into compact bytecode (or QuakeC), folds
constants, drops dead branches, and turns the scripts that run on every frame into cheap event checks. Behaviour
stays identical, quirks included: some of the original scripts depend on odd timing and corner cases, and quests
rely on them, so each optimization is checked side by side against the original game (and OpenMW) before it is
kept. Optimized, never changed. The one exception is the original's known script and engine bugs that OpenMW
fixes: AmiWind takes the same fixes, written in its own code and each named with the OpenMW issue or change it
follows, so a player sees the behaviour OpenMW players see. These fixes are on by default.

## Near future: the baseline stays, extra RAM becomes speed, 16 October 2026

The game keeps working on the current memory setup (the reference configuration and its budgets decide every
gate), and uses more RAM as caches when a machine has it: a larger surface cache, resident streamed chunks,
prefetch, visited interiors kept, read caching. Details: [the cache plan](#the-cache-plan-extra-ram-spent-on-not-doing-work-twice-16-october-2026).

## Near future: one game for the 68040 and the 68060, 16 October 2026

Project decision, 16 October 2026: one game binary that recognises the machine at start-up.
The 68060 plan, its rules and steps: [AmiWind on the 68060](68060.md).

- [ ] The engine reads the CPU and FPU type at start-up (the system's attention flags) and picks its 68040 or its
  68060-tuned version of each hot routine (span drawing, edge clipping, the surface cache builder) once, through
  a function pointer. The 68040 path stays the baseline; the 68060 path is our own measured code, pixel-identical
  at the same poses, and avoids the instructions the 68060 emulates in software.
- [ ] The CPU support library (`68040.library` or `68060.library`, the user's own, never shipped by us) either set
  when building or dropped into the game disk's library folder afterwards; the boot script loads the one
  matching the CPU. Default folder when building: `amiga-libs` next to the Morrowind `Data Files` folder, used
  when present; `--amiga-libs DIR` chooses another. The hardware guide keeps the
  [compatibility roadmap](REAL_HARDWARE.md#compatibility-roadmap).
- [ ] If the CPU needs a library that is not there, the game says so in plain words (which file, where to put it)
  instead of crashing on the first emulated instruction.

## Goal: every exterior on CHIM, 16 October 2026

Project decision, 16 October 2026: everything above ground (and the sea around it) is CHIM; interiors are each a
Quake map or CHIM, whichever suits the room. When every exterior cell is CHIM, the classic region maps leave the
game: no edges between CHIM and classic cells, no border copies of classic objects in CHIM frames, no object
stored many times over, one world format outdoors. The classic region builder stays in the code, selectable for
A/B regression tests, but no build ships it. The path: v0.0.41 (rings 0 to 4 with the Bitter Coast and Azura's
Coast whole), the batch import of the easy cells in v0.0.42, the remaining cells by weight, the seabed cells and
the open sea, then Solstheim ([v0.0.42 working plan](PLAN-v0.0.42.md)).

## v0.0.42: Complete Vivec (the city), 16 October 2026

Project decision, 16 October 2026: v0.0.41 ships the first regional build (More Fixes, Fewer Planes
(A Telvanni Root Story)); v0.0.42 completes the city of Vivec.

The step-by-step checklist, with what counts as done for each step, is the
[v0.0.42 working plan](PLAN-v0.0.42.md).

- [ ] `dbg orbit` (planned): an inspection camera that orbits the object under the crosshair, a world position or an
  original reference number, with the debug HUD, noclip and god mode on; mouse wheel for distance; orbit speed
  settable (a number of degrees per second, and + / - while orbiting, 0 to hold still); right click or Esc
  restores everything. A photo variant, planned as `dbg orbit photo`, hides the HUD and all interface for
  full-screen promo clips. Built on Quake's chase camera; the test harness records one orbit as a short clip.
- [ ] The stair gate only where something changed: each flight walked once, a pass kept by the SHA-256 of what it
  read, and known-good stair records (place, behaviour, hash; no game data) shipped in the repository so a build
  from unchanged data skips the walk ([plan 1.0b](PLAN-v0.0.42.md#10b-the-stair-gate-walk-each-flight-once-keep-every-pass-ship-the-known-results)).
- [ ] `dbg flyingcam` (planned): a fly-over camera that spirals across the whole island at a set speed and
  height above the ground, from the coast inwards like the CHIMport's own ring order, and slows to a stop over
  the highest terrain point, on Red Mountain (found from the land records). Flown in noclip and god mode by default;
  speed and height settable; `hud on` / `nohud` for the debug HUD; `photomode` for full screen without the
  player's stats interface; Esc ends it and restores every setting. Uses: a streaming and frame-time run over
  every CHIM cell (memory, load hitches, missing or broken cells seen in one pass) and a promo clip.
  A tracking-shot variant, planned as `dbg flyingcam mountain`, starts at eye height, climbs past the top of the
  Ghostfence and comes to rest on the summit of Red Mountain. Both fly smooth, steadicam-like shots: head bob and
  view sway off by default. Both go on the test list: a fly-over of every
  release candidate, and, as more of the island is on CHIM, the whole-island performance check against the
  previous release's fly-over.
- [ ] Seabed cells (land records entirely under water) planned and converted as their own CHIM cells
  ([CHIMPORT-OCEAN-LAND-41](bugs/CHIMPORT-OCEAN-LAND-41.md)); interior creatures placed, the demigod Vivec first
  ([INTERIOR-CREATURES-MISSING-41](bugs/INTERIOR-CREATURES-MISSING-41.md)).
- [ ] Every Vivec interior in the build. Today 14 of 144 rooms are left out: 11 over the 220 placed-model limit,
  4 over the room memory budget (one by 964 bytes), 1 past the coordinate range. In order: numerous plants as
  sprites, per-mesh reduction measured as an A/B, sections cut at hallways and doorways, recentring
  ([Interior sections](INTERIOR_SECTIONS.md#interiors-over-a-limit-the-order)).
- [ ] Vivec himself in his palace: the demigod floats above the floor, meditating in the lotus position, as in the
  original (his own idle pose and hover height; the actor ground check accepts a floating actor where the
  original places one).
- [ ] The city frame owns only the city's cells, on whole-cell borders
  ([CHIM-VIVEC-FRAME-WIDE-41](bugs/CHIM-VIVEC-FRAME-WIDE-41.md)); the two banner-draped giant mushroom caps closed
  ([MESH-VIVEC-CAP-GAP-38](bugs/MESH-VIVEC-CAP-GAP-38.md)).
- [ ] The open Vivec entries of the bug register reviewed: each one still real, fixed, or replaced by the whole-city
  frame, with evidence; the still-real ones fixed or scheduled.
- [ ] Vivec's interior plants that cost frame time drawn as sprites, measured in game.
- [ ] The batch import of the easy cells (maintainer, 16 October 2026), once Vivec is done: every converted cell with all
  audits passing and comfortable memory headroom joins CHIM in one step, whole regions where possible. Measured
  16 October: 524 such cells outside v0.0.41, 459 of them with at least 2 MB of headroom (Ashlands 157, Molag Amur
  91, West Gash 77, Ascadian Isles 58, Sheogorad 53, Grazelands 53, Red Mountain 35). Every CHIM edge removed is a
  frame that no longer carries copies of a classic neighbour's objects, and every classic region map retired is
  one of the old, overlapping maps gone. Order by weight (maintainer, 16 October 2026): the lightest cells first, then
  the heavier, the heaviest last, each step measured again with the current builder (CHIMport) and prechecked in
  the CHIM stage before one build. Converting the light cells first turns the heavy cells' classic neighbours into
  CHIM, which removes the border copies that push them over; the heaviest then go through the over-budget
  procedure.
- [ ] The builder names the neighbour overlap (maintainer, 16 October 2026): each frame's memory peak split into its own
  objects, border copies from CHIM neighbours and border copies from classic neighbours (a model used by the
  frame's own objects counts as its own). The heap gate's failure message, the heap report and the master
  builder's over-budget summary say how much of a peak is classic-neighbour overlap and from which cells, and warn
  on tight frames (over 90 %) where that share is large: those neighbours go first in the light-to-heavy order.
- [ ] An automatic cause overview for every frame over the budget or tight (maintainer, 16 October 2026: "show it in the
  logs or errors ... what exactly caused the heap excess"): in the log, the error, the heap report and the master
  builder's summary, the peak by kind (drawn, collision, terrain, textures; collision planes and nodes no longer
  counted as drawn), by source (own cell, classic and CHIM neighbours), the top models with their heavy part
  (planes, clipnodes or faces), tilted copies per mesh, collision fallbacks with their reasons, which top meshes a
  recipe covers, and a one-line hint per cause pointing at the CHIMport procedure. The Polycount inspector shows
  the same overview next to its heatmap.
- [ ] The remaining cells, by weight: a table generated from the tracker after every build (cell, place, region,
  memory headroom, placed faces, status), lightest first, in the CHIMport guide. Measured 16 October, after
  v0.0.41 and the easy batch 54 Vvardenfell cells would remain: the inland lava group (24 cells, light but one
  shared lava frame group with 175 KB headroom); settlements and heavy spots with 1-2 MB headroom (Zergonipal,
  Bal Isra, Zainab Camp, Dren Plantation, Erabenimsun Camp, Urshilaku Camp and eight more); tight cells under
  1 MB (Suran, Vos, three Red Mountain cells, one in Sheogorad); four over budget (Tel Vos 57 KB, cells in
  Sheogorad, Red Mountain and the Grazelands); four failing other audits (Ald-ruhn, Maar Gan and two more); and
  Caldera, never converted. Each group is worked through in that order, measured again first.
- [ ] The inland lava group as ordinary region cells, with the lava stored once: the lava surface a shared,
  content-keyed piece every lava cell references (as the shared ocean chunk and CHIM's terrain references), so
  no lava is stored twice on disk or in memory (maintainer, 16 October 2026: avoid duplicates). Measured first: each
  of the 24 cells built on its own against the memory budget. The other options stay open and selectable, as
  every method does: smaller lava frame groups split along natural breaks, the shared lava surface on its own,
  and ordinary cells with each cell's own lava; all three are measured, the default is the maintainer's choice.

## Effects to investigate: Quake machinery first, 16 October 2026

Maintainer request, 16 October 2026: future effects start from what AmiQuake already draws, mapped onto the Morrowind
data, before any new engine feature ([IDEAS](chim/IDEAS.md#the-ghostfence-as-a-quake-turbulent-surface)).

- [x] The Ghostfence and the Ghostgate: the upright shimmering curtain between the pylons (electricity and water
  at once) as a Quake turbulent surface (the default of a build from v0.0.47-dev1, commit 43abedc7; `dbg ghostfence
  off` draws it still). Textures named with a leading `*` are drawn by the warp that ripples
  water, slime, lava and Quake's upright teleporter fields; our lava already uses it. The fence's energy texture
  becomes such a texture on the fence walls, with no new engine feature.
- [ ] The electric pulse: a flickering light style (Quake's animated light patterns) on the fence's glow, so the
  light around it pulses like the original's shimmer.
- [ ] Smoke plumes rising from the lava pools (maintainer, 16 October 2026: "they can be massive, use AmiQuake cheap
  ones"): large animated Quake sprites over the pools the build already records. A sprite is one camera-facing
  picture, so a massive plume costs what a small one does (one quad, a few frames), with its outline kept like the
  tree sprites. The plumes can be intense: two or three overlapping, nearly opaque smoke sprites per pool at
  different sizes and animation phases give a thick, churning column for the cost of three quads. Quake's
  particles (`pt_fire`, 1-4 pixel squares) only as a few embers close by; a plume of particles would cost
  hundreds per frame.
- [ ] Each effect A/B'd against the original at the same pose, headlamp off, before it is adopted.

## v0.0.41 "More Fixes" and v0.0.42, 16 October 2026

v0.0.41 is a fix release, published once rings 0, 1 and 2 are complete. v0.0.42 brings rings 3 and 4
(149 and 138 cells, all converted) to CHIM. Planned:

- [ ] Builder: chim stage key only its own inputs; stair walks and units reused by hash; every worker used
  ([BUILD-REUSE-KEYS-TOO-BROAD-35](bugs/BUILD-REUSE-KEYS-TOO-BROAD-35.md)). Lava regions measured against the
  storage budget before a build.
- [ ] Town frames own only the town's cells, on whole-cell borders, Vivec first
  ([CHIM-VIVEC-FRAME-WIDE-41](bugs/CHIM-VIVEC-FRAME-WIDE-41.md)); closed giant mushroom caps in towns
  ([MESH-VIVEC-CAP-GAP-38](bugs/MESH-VIVEC-CAP-GAP-38.md)).
- [ ] Mesh optimizer threshold measured (50 to 400 faces); a Dwemer ruin by the lava pools (cells 8,0, 9,2).
- [ ] Interior map: each original interior cell, our maps and their format (BSP29 or CHIM), built or excluded
  with the reason, doors that reach it; exterior entrances first. Shown in the tracker's Interiors table.
- [ ] Planar merge and the mesh optimizer for interiors; the 14 excluded Vivec rooms measured again; a CHIM interior
  trial; the Arena Pit's polycount reduced.
- [ ] Inventory: the original posture per weapon type (A/B with the original game), the title plaque, picked
  mushrooms shown. A stats screen on O. A separate switch for combat speech gating.
- [ ] Quest journal indices as a small table, with a `dbg journal QUEST INDEX` command.
- [ ] Toolkit: a settlement list from your own game files. Done: the polycount inspector opens a build's world
  from its address (`toolkit_serve.py --chim-world`).
- [ ] Full rotation and scale in the CHIM placement record: one drawn model per mesh, collision kept per tilt;
  41-57 % less model data in the cells over budget ([IDEAS](chim/IDEAS.md#memory)).
- [ ] Telvanni towns (Vos, Sadrith Mora) fit with per-mesh recipes
  ([CHIMport](chim/CHIMPORT.md#when-a-cell-does-not-fit-the-memory-budget)).
- [ ] Whole-region CHIM for the lava regions; revisit Seyda Neen, Balmora and Vivec optimizations.
- [ ] Tracker: inclusion by release with a percentage, label fixes, world data size per build.
- [ ] Bug tracker: an "introduced in" commit for regressions; bugs filed from one validated input file.

## v0.0.41 candidate - visibility aprons, 15 October 2026

[CHIM-VISIBILITY-APRON-SCOPE-41](bugs/CHIM-VISIBILITY-APRON-SCOPE-41.md) - The combined world stopped at Tel Uvirith, original cell (10, 1), because
its approved fixed stronghold snapshot required a source radius of zero.
Regional frames now audit neighbouring cells for separate aprons. The repair
keeps visibility snapshots bound to each original cell across all frames that
audit it. Unknown scripts and unaudited references remain visible. Runtime
quest progression is still deferred; complete conversion and native/package
acceptance remain pending. Coverage counts are unchanged.

## v0.0.41 candidate - window support, 15 October 2026

[CHIM-WINDOW-TOWER-SUPPORT-41](bugs/CHIM-WINDOW-TOWER-SUPPORT-41.md) - The combined v0.0.41 world build stopped while mounting four Nordic windows
from original cell (7, 22) into the adjacent frame apron. Their supporting
thatched tower was present, but the facade search accepted only model names
containing "house". Exact source triangles support all four windows under the
existing distance and outward-normal checks.

The candidate recognizes the original thatched-tower model in both local and
neighbouring facade searches. It keeps original reference ownership, geometry,
collision, mounting range and clearance. Arbitrary props are still rejected.
The failing build is preserved; complete conversion, native comparison and
fresh package readback remain pending. Coverage counts are not promoted.


15 October 2026, v0.0.41 candidate: 50 focused lava/polygon/terrain checks
and 47 emulator preset/launcher checks pass. Both original failing chunks pass
coverage against the unchanged cached geometry. Full combined-world, exact
source suite, native, package and shipment checks remain pending.

## v0.0.41 candidate - lava coverage, 15 October 2026

[CHIM-LAVA-DUPLICATE-VERTEX-40](bugs/CHIM-LAVA-DUPLICATE-VERTEX-40.md) - The v0.0.40 combined-world build stopped on two chunks in cell (2, -2).
Readback of the exact cached units found five affected coverage samples:
each has one lava surface and lava contents (-5) at the required depth.
A tiny edge collapses to identical adjacent vertices when the chunk is
translated into float32 frame coordinates. The polygon test mistook this
zero-length edge for a boundary through every sample.

The v0.0.41 candidate skips only exactly identical adjacent XY vertices.
It preserves edge ambiguity, outside rejection and empty/degenerate rejection;
no geometry, collision, pool height, tolerance or engine format is changed.
Full-world validation, native checks, fresh package readback and delivery
remain separate and pending. No coverage count is promoted.

## Compiled apron selection, 15 October 2026

CHIM-FRAME-STATIC-SEAM-40 — The full combined conversion found a conservative
source box overlapping an apron although the compiled rock footprint ends
0.83 game units outside it. The selection now records and excludes only external
references whose compiled pieces all miss that apron. Owned originals, reaching
pieces and missing-piece failures remain protected. The original reference and
compiled boxes remain in the source receipt. All 68 focused checks pass.
The preceding source passed 4,218 tests: 4,212 passed, three Windows checks
skipped and three tracked Census cases were expected failures. The later source
requires its own full suite and combined validation. Native, package and shipment
acceptance remain pending; no converted or accepted coverage count is promoted.

[Canonical report](bugs/CHIM-FRAME-STATIC-SEAM-40.md).

## Paired boundary validation, 15 October 2026

CHIM-FRAME-STATIC-SEAM-40 — The latest v0.0.40 paired conversion passes structural, heap, zone-walk and
stair validation. The 3,836 tested steps and ramps pass; 610 advisory results
remain recorded. Across 2,816 paired positions, full-static support states agree
and the maximum supported-height difference is 0.000077 game units. Terrain,
water and common standing-hull controls agree. The complete 369-frame successor
is being built from the same converter source; its acceptance remains pending.
The exact source full suite is running. Native gameplay, other boundary segments,
fresh package readback and shipment remain separate unfinished gates.

[Canonical report](bugs/CHIM-FRAME-STATIC-SEAM-40.md).

Release preparation, 15 October 2026: all 369 combined candidate frames pass
conversion and structural, heap, zone-walk and stair validation. A later
combined ownership failure keeps the candidate held; corrected compiled-world,
native and package acceptance remain pending. Complete rings 0, 1 and 2, original
references, actors, horizons and visual/collision seams remain release gates.
See [release preparation](RELEASE-v0.0.40.md) and
[the static seam report](bugs/CHIM-FRAME-STATIC-SEAM-40.md).

## Owner apron follow-up, 15 October 2026

The source owner check found twelve additional references in the sampled
regional apron: four placements of the fourth kelp mesh, four objects already
deferred by Seyda, and four nonsolid grasses represented by existing sprites.
The successor retains all four original kelp models. Regional aprons now honor
the included town's exact declared deferrals; nonsolid grasses retain the same
hash-verified sprite bytes and original transforms instead of duplicate meshes.
Unrecorded missing owners, changed original identities and corrupt sprite assets
still fail. The existing ownership validator is unchanged. Forty-seven focused
checks pass, including serialized ownership and sprite corruption controls.

The earlier authored-collision source passed 4,213 tests: 4,207 passed, three
Windows-only checks skipped, and three tracked Census expected failures. This
does not certify the later source. Combined conversion, native seams, gameplay,
fresh packaging and delivery remain pending; no coverage acceptance is promoted.

[Canonical report](bugs/CHIM-FRAME-STATIC-SEAM-40.md).


## Combined-world gate update, 15 October 2026

All 369 frames in the combined candidate passed conversion, structural,
heap, zone-walk and stair validation on 15 October 2026. This establishes a
conversion result for that exact source, not native or packaged acceptance.
The initial comparison measured six of 547 original-cell boundary segments:
five agreed, while southern Seyda between (-2,-12) and (-2,-11) had 477
full-static support disagreements. Later scoped results are recorded below;
the remaining 541 segments are unmeasured.

The regional scenery apron first reduced the southern Seyda comparison from
477 to 69 support-status disagreements. Original reference 463188 had identical
63 rendered faces but 40 collision hit-presence disagreements in 588 rays:
the regional path retained the authored RootCollisionNode while the legacy
Seyda carrier omitted it. A CHIM-only supplement verifies the original NIF and
visual hashes, preserves carrier bytes and appends the original authored hulls.

The corrected Seyda frame now compiles with zero structural failures and passes
heap and zone-walk checks. Compared with the repaired regional frame, the same
boundary has zero full-static support-status disagreements across 2,816 samples
(5,632 queries); terrain and water controls also agree. Its complete stair gate
is unfinished: the parallel run exceeded its memory limit and was stopped by
out-of-memory termination. A passing boundary sample is not a complete stair,
combined-world, native or package pass.

The combined attempt then stopped at ownership validation before packing:
original kelp references, including 463098, were omitted from the Seyda frame.
These references are present in the original source carrier and absent from the
existing flora sprite receipt; a legacy dressing filter removed them. The next
source correction retains only the three known original kelp meshes 01/02/03,
binds additions to the original scenery index and leaves unrelated deferred
dressing unchanged. All 43 focused Seyda, town and ownership checks pass.
Compiled verification of this later correction, native checks and packaging
remain pending. The earlier source's running full suite does not certify it.
[Static seam](bugs/CHIM-FRAME-STATIC-SEAM-40.md) and
[boundary ownership](bugs/CHIM-FRAME-DEPENDENCY-OWNERSHIP-40.md).


## v0.0.41-dev1: ring3 feasibility after v0.0.40 delivery

Current work remains v0.0.40; no v0.0.41 version switch has begun.
Begin this expansion after the v0.0.40 playtest and matching source are delivered.
The 15 October tracker identifies 149 Vvardenfell ring3 cells. Seventeen already
lie within the current town ownership cores; none is an existing regional core.
The provisional extension therefore needs 132 regional frames: 129 currently
eligible by offline status and three held cells. Retaining the current frames
would give 501 frames before pocket and routing reconciliation. These are
feasibility counts, not new converted, native-checked or packaged coverage.

| Held ring3 cell | Retained failed checks |
| --- | --- |
| Ald Velothi (-11,15) | Hull-chain limit and memory fit; headroom -280,976 bytes |
| Ald Daedroth (11,20) | Hull-chain limit and memory fit; headroom -206,256 bytes |
| Tel Mora (13,14) | Memory fit; headroom -2,641,936 bytes |

Reassess those older per-cell findings on the next pinned source. Keep all holds
explicit; excluding a cell must also pass the enclosed-pocket check. Reuse the
existing original-cell selection, ownership/dependency records, palette, source
archives, compiled hulls, shared terrain and far horizon layer. Preserve separate
aprons and exclude replaced legacy terrain/scenery from compilation and payloads.
Resolve the current static seam before extending its boundary checks inward.

Across these 149 cells the original-reference accounting includes 8,430 statics,
4,511 flora, 63 activators, 1,308 containers, 62 doors, 16 items and 318 lights.
It separately defers 37 NPCs, 455 creature references and 280 meshless lights.
Flora placements do not by themselves establish their runtime conversion policy.
Retain original reference types, dependency copies and all unimplemented gameplay.
Solstheim is outside this ring3 scope. Revalidate compiled contact, memory,
stairs, horizons and both sides of each handover before native and package gates.

## v0.0.40 release scope - 15 October 2026

**v0.0.40: Rings 0, 1 and 2 of Vvardenfell in Full CHIM** is the selected title. Rings 0-2
are the complete planned CHIM conversion scope; other exterior cells retain the
legacy route except already converted CHIM towns. Door-entered interiors remain
independent. All 336 ring cells appear in the 435-cell spatial plan; that plan
is not a package manifest. The combined 369-frame world, preserved horizons,
original references, deferred features and adjacent visual/collision seams must
pass their gates before release. The combined conversion has passed; the later
source repair needs its own checks and compiled boundary verification. See
[coverage](chim/CELL_TRACKER.md) and
[ownership](bugs/CHIM-FRAME-DEPENDENCY-OWNERSHIP-40.md).

Public gameplay images must be actual AmiWind captures. Original-game reference
images remain private; the previous exception is removed and the export
regression passes. See [public image selection](bugs/PUBLIC-REFERENCE-SCREENSHOT-40.md).


Earlier source checkpoint, 15 October 2026: boundary ownership repair passed
37 focused checks and the source contract for all 369 frames. Combined-world
readback, split-model/sprite dependencies, seams, native gameplay and full
package gates remain pending. Converted, audited, native-checked and packaged
coverage retain their previous receipts.
[Ownership repair](bugs/CHIM-FRAME-DEPENDENCY-OWNERSHIP-40.md).


Scoped combat follow-up, 14 October 2026: Khajiit female physical ready movement
and stationary/strafe punches are positive controls. Keep the reported
[movement](bugs/PLAYER-READY-MOVEMENT-39.md) and
[attack](bugs/PLAYER-PUNCH-THIRDPERSON-39.md) cases open. Next acceptance work
must resolve the failing character/context and compare motion with the original;
these controls do not establish hit/damage or gait quality. Preserve the
[Seyda allocation retry](bugs/CHIM-CHUNK-LOAD-FAIL-33.md) separately from cell
conversion, inclusion and visual/collision coverage.

15 October 2026 terrain follow-up: original-spacing diamond topology and two
local LAND-detail repairs are integrated. Source coordinates and affected edges
agree; the dreamer contact issue remains open. The complete source gate now
passes with explicit skips and expected failures. Original ray measurements
are distinguished from rendered/contact triangles. Complete the original
foot-pose comparison, compiled contact and native cell/chunk
crossings before accepting rings 0-2 or packaging dev2. Existing conversion and
package counts remain separate and unchanged.
[Diagonals](bugs/CHIM-TERRAIN-DIAGONAL-40.md),
[contact](bugs/CHIM-SEYDA-ACTOR-CONTACT-33.md).


- BUILD-PLAYER-BODY-BUDGET-FALLBACK-39 — 15 October 2026, v0.0.40-dev2:
  continue past reduced animation fits to seek full action sampling under
  unchanged geometry and memory guards. The canonical Argonian diagnostic
  fits122 frames; production and native verification remain pending.
  [Report](bugs/BUILD-PLAYER-BODY-BUDGET-FALLBACK-39.md).


v0.0.40-dev2 candidate preparation, 15 October 2026: the animation correction
passes 115 shared converter checks. Regenerated assets, full release gates and
shipment remain pending. [Candidate notes](RELEASE-v0.0.40-dev2.md).


Animation follow-up, 15 October 2026: the
[rotating-offset converter correction](bugs/NPC-ANIMATION-OFFSET-40.md)
has nine focused checks. Rebuild affected player bodies and compare gait,
limb shape, ready movement and combat before the next v0.0.40-dev2 inspection
candidate. Keep original-asset, native, packaging and shipment gates separate.
CHIM cell ownership and coverage are unchanged by this converter work.



Original gait reference, 14 October2026: Nord male/Barbarian/Steed controls now
cover physical lowered/ready W and Shift+W. Correct camera-eye/actor labels
before measuring movement. Resolve the measured eye-height residual and compare
actual speed/phase with current and v0.0.38 motion before closing
[gait](bugs/PLAYER-MOVEMENT-FRAME-SKIP-39.md) or
[ready movement](bugs/PLAYER-READY-MOVEMENT-39.md). Head and scene differences
remain explicit; reference evidence is not repaired-game acceptance.


Nord gait follow-up, 14 October2026: physical ready walking and running have a
scoped positive control, with changing limb poses in retained original frames.
Complete the matched original and historical v0.0.38 motion comparison before
accepting [gait quality](bugs/PLAYER-MOVEMENT-FRAME-SKIP-39.md). Keep the
[reported ready-movement failure](bugs/PLAYER-READY-MOVEMENT-39.md) and
[terrain allocation retries](bugs/CHIM-CHUNK-LOAD-FAIL-33.md) open; initial
blocked-endpoint controls are excluded and no cell coverage is promoted.


## v0.0.40-dev1 gameplay priority, 14 October 2026

The unreleased dev2 documentation rotates selected older journal entries before
adding further findings; keep the existing size guards and preserve archive
links in the next source export. [Tracker maintenance](bugs/TRACKER-REGISTER-SIZE-33.md).

Selected actual item lookup/icons and physical sword/shield equip are observed in native diagnostics. The exact later target/FPU and full suite pass; actual Nord steel-weapon/shield blocking credits two incoming blocks. Normal HUD Guard text is absent with target names retained, and live no-dice health/fatigue readouts are correct. Selected legacy Argonian held/released shield and fists-readied movement are scoped positive controls; closer pose, anatomy, jump/death, matched gait and all-appearance acceptance remain pending. [Catalogue](bugs/INVENTORY-CATALOG-LOOKUP-40.md), [blocking](bugs/COMBAT-BLOCKING-36.md), [HUD](bugs/HUD-STATS-29.md).

The selected dev1 body payload retains the previously packaged 122-frame
Argonian male and matching tags alongside nineteen current bodies, preserving
hit/death/jump sampling. Its legacy block holds a sample about 67 ms before the
authored hit, and current anatomy/quality limits remain open. Selected-payload native held/released shield and movement are observed;
closer pose, anatomy and jump/death checks remain pending. Do not infer
complete Argonian acceptance from Nord controls. [Body fitting](bugs/BUILD-PLAYER-BODY-BUDGET-FALLBACK-39.md).

The bounded dev1 gameplay inspection candidate is delivered. Continue dev2.
Dev2's primary objective is CHIM mapping for rings 0, 1 and 2, with separate
conversion, audit, native, packaging and acceptance records. The inventory
requirements below remain planned follow-up work.

CHIM static-mesh performance remains a measured dev2 audit even in already
mapped areas. Playtesting reports occasional exterior Dwemer FPS drops; exact
site/build/cause and measurements remain unknown, with no reproduced repair.
After selecting an exact scene, profile static meshes, visibility, transforms,
clipping, surface-cache/overdraw, server/collision and streaming costs separately.
Compare fixed pose and route with warp off and controlled settings, then preserve
original geometry/gameplay through matched OpenMW and native before/after checks.
Mapping alone does not establish an FPS budget, and an optimizer is not assumed
to fix the report. Rings 0, 1 and 2 remain dev2's primary objective.
[CHIM-VIEW-FACES-33](bugs/CHIM-VIEW-FACES-33.md).


Plan compact lookup tables for all original item identities, properties and
effects, with explicit support states and bounded on-demand resources. Preserve
original typed effect, enchantment/charge, equip/use and save semantics; do not
substitute default values for unsupported records. Current basic AWI2 rows and
ten selected asset pairs are incomplete: actual picked Luminous Russula resolves
name/count/weight/value but has no converted icon/model or admitted action.
Keep authoritative carried IDs, counts, condition and equipped state reliable.
Quest logic must query actual AW_ITEM inventory, not a hot-swap list or the UI's
visible rows. A bounded hotbar/equipped asset cache may stay resident for fast
use; other descriptors, icons and models load on demand. Full-catalogue lookup
coverage does not require full-catalogue residency. This is a cache plan, not
an implemented optimization or measured speed/memory saving.

Original UI textures must be derived from the locally supplied owned game
during conversion and excluded from public source. The fixed right-hand corner
must mirror the left border pattern, with no movable-window or resize control.
Interim authored placeholders do not establish original artwork parity.

Require original golden title/tab frames and font, with no movable-window
top-right corner decoration in the full-screen modal. Add actual carried-weight/
capacity and Armor-rating readouts from game state, plus a mouse-operable
vertical scrollbar on the right and keyboard navigation. These readouts and
visual refinements remain planned. The dev2 scrollbar source follow-up below
has focused automated checks; native acceptance remains pending.

Reserve an inset, readable bottom control/status area in inventory, with
enough vertical margin and wrapping to keep hints away from the screen edge and
item details. A new supplied image confirms crowded bottom hints; its exact
running binary is unverified. This spacing refinement and the original-style UI
features above remain planned, with actual native/reference checks required.
[UI-INVENTORY-LAYOUT-40](bugs/UI-INVENTORY-LAYOUT-40.md).

14 October post-dev1 source follow-up: inset inventory status/control rows and
literal Inventory heading pass executable bounds/actions and map/journal
checks. Target/native visual comparison, original plaque/artwork/pose and the
remaining inventory requirements stay pending; delivered dev1 is unchanged.

Add a persistent View option for item list versus icon grid, reusing the same
actual carried selection, category/filter/sort, equip/use/drop admission and
keyboard/mouse actions. Persisting a view must not duplicate inventory state
or change item ownership. This list/grid option remains planned follow-up.

Plan E or a double-click on the actual selected carried item to open its
context actions: equip/unequip, consume/use and read books or papers as the item
supports. Share the existing action admission and authoritative ownership state;
unsupported effects or reading paths must be labelled unavailable rather than
simulated. These expanded shortcuts/use/read actions are planned, not dev1
implementation.

Equipped items also require a thin golden outline. Dedicated original inventory
poses, the original inset black name plaque and camera parity remain planned;
none of these additions is implemented by this roadmap update.

The inventory title must read the literal "Inventory" in the original inset
black plaque/golden border. The planned attributes/stats panel uses the actual
player name as its header. Keep title content distinct from player identity;
these refinements remain planned and must follow the supplied original UI.

The planned dev2 [inventory follow-up](INVENTORY.md#next-inventory-pass-v0040-dev2-14-october-2026)
requires the actual race/sex/head/hair/clothing/equipment appearance, full original
item icons and original equip/use/drop, ownership, save and effect rules.
Drag-to-character equip/use, category/value/weight/item-stat sorting and filters,
a black full-screen paused backdrop, original golden borders, the original inset black
title plaque within the gold top border reading "Inventory" and a readable F10 console-font hover-detail variant remain
required. The preview posture still needs original-reference refinement; neither
that posture nor the inset plaque is implemented by this plan. The dedicated
original inventory pose (fixed time zero), rather than a rotated live idle,
remains required; selected male-Nord modal pause evidence is scoped. Minimize RAM
through compact item lookup tables (LUTs), on-demand disk
assets and measured cache/preview choices. Give inventory preparation an explicit
master-builder phase, monitor build/runtime performance, and keep the producer,
consumer and public source export synchronized. Plan a controlled MiniWind
`--inventory-test` scene with explicitly tracked original test items. The linked
inventory page owns the detailed requirements and verification gates. These
additions and the planned ring/town/seam expansion are not included in dev1.

Reconcile the three experimental quick-character expected failures under
[TEST-CENSUS-CONTRACTS-40](bugs/TEST-CENSUS-CONTRACTS-40.md): meaningful source
routing checks, supported debug aliases and direct-start documentation. Keep
these open contracts separate from native menu/gameplay acceptance; remove each
decorator only after its replacement passes. This follows the urgent physical
combat and inventory gates.


Spell follow-up: magicka use, shield effects, destruction types and player
casting animations remain required gameplay work. Inspect existing AmiQuake
projectile movement/collision, damage, particles and lighting before designing
new effects; compare spell costs, eligibility, delivery and effects against the
original. Reusable projectile machinery is not complete spell-system parity.
No spell implementation is included in this roadmap update.

The v0.0.40 exterior target is CHIM coverage of rings 0, 1 and 2, with every failed, held, partial or excluded cell explicit. The shipped v0.0.40-dev1 gameplay inspection candidate omitted the town-boundary/seam expansion; dev2 requires the approved original-cell ownership and full rings 0, 1 and 2. For each included CHIM maintainer, exclude its replaced legacy BSP29 map before compilation and from the final payload. Preserve independently selected interior formats and required nonduplicate dependencies; conversion/audit alone does not prove runtime inclusion. Adjacent-cell acceptance must cover shared border heights/coordinates, water and surface continuity, collision crossings in both directions, and unique edge-object ownership.

Keep a per-reference entrance ledger for converted CHIM cells: original location/type/destination, visible geometry, activation bank, configured target, actual packaged destination and native entry/return states. Reuse the existing unavailable-interior handler for registered entrances with deferred destinations. Actual interior implementation follows in the next pass. Resolve the six partial town overlaps in dev2 through the approved original-cell-aligned town ownership and complete reference-band conversion, with separate terrain aprons.

Ring 0 needs five runtime core owners and a compatible shared ocean terrain path before inclusion. Preserve four original deferred LEVC references. Plan outward grid-aligned CHIM town frames at Vivec x=1..6, y=-14..-9 and Seyda Neen x=-3..0, y=-11..-8; audit overlap ownership and boundaries before conversion. No frame expansion or new native coverage is implemented by this plan.

Movement parity: use the [source speed study](MOVEMENT_SPEED_STUDY.md) and [PLAYER-MOVEMENT-STATS-PARITY-39](bugs/PLAYER-MOVEMENT-STATS-PARITY-39.md). Next quantify forward walk/run/level-swim in matched scenes with effective stats, load/effects, race/sex, original race-speed setting and simulation time recorded. Then verify direction, readied states and save/load. Keep faithful gameplay and convenient fast debug policy distinct; no tuning or proposed maximum-stat option is implemented by the study.

The inventory's current safe placement boundary is plain BSP. Active CHIM,
captured scenery and restricted story contexts refuse drops and retain the
item; full-game CHIM/scenery placement is required next under
[UI-INVENTORY-INTEGRATION-40](bugs/UI-INVENTORY-INTEGRATION-40.md). Keep the
distinct limits visible: 32 carried IDs, 32 persistent ground records and 16
distinct new inventory model precaches per loaded level. Repeated models reuse
a slot and scene changes reset that cache. Expanding the model limit requires
explicit table-budget validation. Target compilation and selected native lookup,
physical equip and first-person RMB raising are observed. The repaired complete
suite, full native modal, third-person block pose, plain-BSP transfer/save/load
and CHIM-refusal gates remain pending.


Maintainer-published v0.0.39 source is commit
`751e1efa6b28e7fc58453fc81c73100715b88195`; the maintainer reports the same gameplay
in inspected RC2 and final. The current bounded priority is the renewed
[physical-LMB punch](bugs/PLAYER-PUNCH-THIRDPERSON-39.md),
[ready-state inability to move](bugs/PLAYER-READY-MOVEMENT-39.md),
[both-view blocking presentation](bugs/COMBAT-BLOCKING-36.md) and
[sinking/upright swim body](bugs/WATER-GAMEPLAY-PARITY-38.md) failures.

For punch acceptance captures, drain diagnostic commands before physical input
and avoid a wait/readout burst ahead of that input. A later state-2-only capture
is inconclusive because its wait/readout burst can defer physical LMB execution;
exact guest timing and Preview-specific suppression are unproven. Keep original footage and actual
state transitions with event timing. This is a measurement correction, not a
gameplay fix. [Punch record](bugs/PLAYER-PUNCH-THIRDPERSON-39.md).

Reproduce maintainer input/state first, repair the diagnosed paths, then check the
exact target and package with ordinary physical input, matched original views
and maintainer inspection. A successful Nord ready-movement or input/damage control
is scoped evidence; it does not accept the maintainer failure. Preserve good ready
posture, original shield eligibility and earlier historical receipts.

The requested `dbg characterchange` testing command is implemented in source:
it reuses the existing pier race/gender/head/hair appearance menu by default;
`all` selects the full quick-character page sequence. Two focused C/console
checks pass. Native Nord-male to Orc-female menu/confirmation/reopen and exact
engine readback pass. Story-registration restrictions remain in place. Package
and maintainer acceptance remain pending; it is a diagnostic aid,
with no gameplay repair claimed.
The new source race-testing shortcut dbg set race/playerrace accepts a strict
zero-based loaded ID or normalized race name, with no-value/list output for
IDs/names/current selection. The refined contract preserves stats/level/current
health, gender/name/class/birth and equipment while changing only validated
race/head/hair and live eye height. It reuses the existing character builder on
a temporary copy, without reapplying racial stats. A same-race request preserves
head/hair; another race selects its first valid gender-compatible pair.
Invalid/context-restricted changes are refused. Fourteen final focused checks
pass; new target/native/package verification remains pending, with no gameplay
repair inferred.
[Contract](CHARACTER_CREATION.md#diagnostic-race-shortcut-14-october-2026).
The complete candidate gate rejects a direct resident registration at270 versus
269commands (+32B). Reuse existing on-demand AWDC1 dbg routing without raising
the budget. Twenty focused actual character/console/catalogue/registry checks
pass after correction; new target/full-gate/native/package remain pending under
[ENGINE-RESIDENT-REGISTRY-GROWTH-36](bugs/ENGINE-RESIDENT-REGISTRY-GROWTH-36.md).

CHIM remains 360 whole cells plus six excluded partial overlaps; no new cell
coverage is established by this follow-up.

## Additional RC1 inspection findings, 13 October 2026

Vivec mushroom seams and missing swimming remain open. The maintainer also reports
coarse Nord/Khajiit third-person gait and an Ordinator appearance mismatch.
Five original screenshots were inspected and retained privately. No new cell
conversion, native coverage or packaged coverage follows from these reports.

- [MESH-VIVEC-CAP-GAP-38](bugs/MESH-VIVEC-CAP-GAP-38.md): Vivec giant mushroom cap has a visible opening.
- [NPC-ORDINATOR-APPEARANCE-39](bugs/NPC-ORDINATOR-APPEARANCE-39.md): Vivec Hlaalu Ordinator has an unhelmeted Fargoth-like appearance.
- [PLAYER-MOVEMENT-FRAME-SKIP-39](bugs/PLAYER-MOVEMENT-FRAME-SKIP-39.md): Third-person Nord and Khajiit fast movement loses smooth foot animation.
- [WATER-GAMEPLAY-PARITY-38](bugs/WATER-GAMEPLAY-PARITY-38.md): Water gameplay lacks complete original behavior verification.

## Release hold and RC2 request, 13 October 2026

Post-pin evidence, 14 October: exact RC2 package/readback and scoped Nord
punch/torch/water inspection passed; inspection artifacts were finalized at
2026-10-13T22:15:44Z. Final source packaging was authorized on 14 October; individual gameplay acceptance remains separate. Leg/seam,
fast-gait, actor/equipment, memory/streaming and wider gameplay acceptance remain
open in the [register](BUGS.md#fix-index). This continuation records observations
after the immutable RC2 source/package pin; it does not rewrite those artifacts.

The [spear-resident candidate](bugs/NPC-SPEAR-ATTACK-REGRESSION-39.md) now selects the authored attack from equipped weapon type; affected asset/native/package checks are pending.

RC2 update, 14 October: [third-person torch](bugs/PLAYER-TORCH-THIRDPERSON-38.md) has scoped native holding/movement evidence. All 20 [swim companions](bugs/WATER-GAMEPLAY-PARITY-38.md) are built and select in water; inherited idle sinking is repaired in source with target/reference checks pending. RC2 package/readback and scoped water checks have passed. Final packaging is authorized; CHIM coverage and individual maintainer acceptance are unchanged.

The maintainer stopped final preparation after RC1 playtest reports. RC2 must
address the third-person punch animation, reported Nord leg shape, recurring
NPC chase animation and guard spear-attack regression before final delivery.
Earlier RC1 release approval does not clear these newly reported blockers.
The canonical reports and corrected fatigue observation are linked below.

All 20 candidate body model/layout pairs now pass offline binary checks within
the unchanged 512 KiB limit, superseding the earlier incomplete bake set.
Possible knee/calf section gaps remain under
[PLAYER-BODY-LEG-SHAPE-39](bugs/PLAYER-BODY-LEG-SHAPE-39.md); numeric fitting does
not establish visible seams, gait, punch, memory or maintainer acceptance. Complete RC2 package readback and scoped native checks passed; wider visual acceptance remains open.

- [PLAYER-PUNCH-THIRDPERSON-39](bugs/PLAYER-PUNCH-THIRDPERSON-39.md): Third-person punches have no visible player-body attack animation.
- [PLAYER-BODY-LEG-SHAPE-39](bugs/PLAYER-BODY-LEG-SHAPE-39.md): Nord player legs appear abnormally thin in RC1.
- [NPC-SPEAR-ATTACK-REGRESSION-39](bugs/NPC-SPEAR-ATTACK-REGRESSION-39.md): Seyda Neen guard spear attack animation is missing in first-person view.
- [COMBAT-FATIGUE-HEALTH-DAMAGE-39](bugs/COMBAT-FATIGUE-HEALTH-DAMAGE-39.md): Clarify Eldafire bare-fist fatigue damage versus armed guard health damage.
- [NPC-NO-RUN-ANIM-35](bugs/NPC-NO-RUN-ANIM-35.md): Companions and hostile NPCs walk but never run, and the walk looks wrong: release residents had only idle frames.
- [ANIMKIT-COVERAGE-35](bugs/ANIMKIT-COVERAGE-35.md): NPCs that move or fight have no walk, run or attack animation: Fargoth and other Seyda Neen villagers glitch toward the player.

## v0.0.39 - Cell By Cell, Piece By Piece

v0.0.39 keeps the implemented RC1 scope: safer automatic checkpoints and death
UI, third-person jump and bare-hand ready/draw/lower source work, body budget
fallback, current help, sound cancellation and exclusive exterior ownership.
The maintainer initially approved RC1 on 13 October 2026, then stopped final
preparation and requested RC2 after the additional playtest reports above.
On 14 October the maintainer authorized the final release package from RC2.
Exact-source checks, image readback, native acceptance and publication remain
separate gates; only the agreed repair/diagnostic scope enters RC2.

The README map uses the sanitized 13 October 2026 reference snapshot.
Converted, audited, native-checked and packaged coverage remain separate;
planned or converted cells do not count as included. The [bug register](BUGS.md#fix-index)
retains all unresolved findings.

## Movement presets and all eight attributes, 13 October 2026

The maintainer requests faithful normal-game movement using original Speed, Athletics,
encumbrance and running-fatigue rules. Keep convenient fast, less strict debug
builds distinct: this report does not authorize silently slowing the current
debug preset. A proposed maxstats option would accept on/off, true/false and1/0.
The requested future maxstats/godmode speed extension would provide maximum debug
walking/running while enabled; disabling both would restore normal effective
values without destroying real character stats. These movement extensions are
not implemented; the existing godmode immunity toggle is separate. See
[PLAYER-MOVEMENT-STATS-PARITY-39](bugs/PLAYER-MOVEMENT-STATS-PARITY-39.md).
Movement and the [speed-linked body animation](bugs/PLAYER-MOVEMENT-FRAME-SKIP-39.md)
need separate original/native comparisons and actual baked pose checks.

All eight attributes must eventually have their original gameplay effects:
Strength, Intelligence, Willpower, Agility, Speed, Endurance, Personality and Luck.
Require matched original shield-block balance/stagger/knockdown/recovery checks,
including return to control and distinct incoming weapon cases. A successful
block or raised shield alone does not establish those reactions. The applicable
original rule/formula still needs audit; this requirement adds no implementation
or native acceptance. See [COMBAT-BLOCKING-36](bugs/COMBAT-BLOCKING-36.md).

Maintain a mechanics matrix with original formula/settings, implemented consumers,
remaining unsupported rules, automated checks and native evidence for each.
Required coverage includes Strength for melee/carrying/fatigue; Intelligence
for magicka; Willpower for spell checks/fatigue; Agility for combat/balance/fatigue;
Speed for movement; Endurance for health progression/fatigue recovery; Personality
for disposition/persuasion; and Luck for the original skill-check modifiers.
Verify the original consumers and exceptions rather than applying one universal
bonus. Displaying or saving a stat is not proof that its gameplay effects are complete.
Reuse existing combat/stat consumers and Quake physics before adding new work;
this roadmap requirement does not claim new attribute implementation in RC2.

The requested [raw identity inspector](bugs/DBG-ENTITY-INSPECT-39.md) is a source
candidate to bind reports to entities/references. Its ordinary overlays remain
separate from click interception. Torch equipment and both-view swimming repeats
remain open; no broader mechanics acceptance follows from the RC1 inspection.

The latest maintainer instruction makes
[third-person torch holding](bugs/PLAYER-TORCH-THIRDPERSON-38.md) required for RC2.
Its source candidate is implemented; all 20 isolated companion bake/readbacks,
35 converter and 36 runtime focused checks pass. Fresh target/native, matched
original, complete image/package and maintainer checks remain pending. This supersedes
the earlier player-torch deferral.

## v0.0.40 - Unfinished work and new features

The maintainer's reported swimming/diving, gait and combat repairs are required for
RC2. Their source, matched original reference, native/package and maintainer gates
remain open; this future-feature milestone does not defer them. v0.0.40 retains
new extensions such as optional cloud/lava effects and terrain texture fidelity.
Existing open issues retain their IDs/evidence and require scoped acceptance;
no broad closure or new gameplay completion is claimed here.

## v0.0.38 - Lava Is All You Need (And A Hint Of Tel Uvirith)

v0.0.38 is published. Its full-world conversion includes both lava paths, all
27 lava-bearing exterior cells and the optimized completed-stage Tel Uvirith
stronghold in cell (10,1). The compact replacement passed exact RC1 HDF/package
readback, scoped native inspection and delivery. Final v0.0.39 retains that
implemented scope and requires its own final-source and image checks. See the
[release checklist](RELEASE-v0.0.38.md) for acceptance requirements and the
[bug register](BUGS.md) for current issue status.

The Toolkit's Included counts must come from verified package contents.
Conversion plans, passing offline checks and packaged coverage remain distinct.
Further coast coverage, gameplay repairs and measured streaming/cache work
continue after this release; they are not implied to be shipped in v0.0.38.

## v0.0.37 - Proofreading the Cantons (fix release)

The v0.0.36 release notes and README brought in line with the released code, and the logo images fixed. No
game change. Its earlier roadmap assigned a working title and broader feature
plans to v0.0.38; the release sections above supersede that assignment.
For real machines with lots of Fast RAM (first tester: A4000 with a 68060 accelerator),
adaptive cache sizing and non-blocking CHIM disk reads remain follow-up work;
the cache, prefetch and lookahead themselves exist already
([real hardware](REAL_HARDWARE.md)).
The proposed follow-up is adaptive CHIM caching and non-blocking world streaming: keep `-chimcache` as the manual
override; detect usable Fast RAM and grow the cache conservatively without touching the tested baseline heap (done
in v0.0.42-rc1: [memory guide](chim/build_guide/MEMORY.md#more-fast-ram-the-automatic-chim-cache)); count
cache hits, misses and evictions; and turn CHIM's blocking pack reads (`Chim_PackRead`,
[ENGINE-SYNC-IO-MAIN-LOOP-36](bugs/ENGINE-SYNC-IO-MAIN-LOOP-36.md)) into reads that complete in the background,
starting from the asynchronous music reader (`aw_aread.c`). A cache only makes a hit faster; only asynchronous reads
stop a miss from stalling a frame. The 2 MiB Chip + 16 MiB Fast machine stays a supported, tested fallback.

## v0.0.36 - 36 Lessons of Vivec's Cantons (And Vvardenfell Shorelines) (released)

v0.0.36 starts moving the open world onto CHIM inside the game itself. Converted areas sit inside
the legacy island, the border between the two is measured and made seamless, and CHIM takes over
cell by cell, from the sea and the coast inward. Draft notes: [release notes](RELEASE-v0.0.36.md).

Historical target: v0.0.36 = the whole coastline on CHIM (every cell of the outer ring and every passing cell of the second ring),
the open ocean placed in the game (one shared ocean chunk), the whole city of Vivec by default, and Seyda Neen and
Balmora. The earlier plan assigned every green zone on the map to v0.0.38.
That was a target, not a record of shipped coverage; use the release's package
evidence and the current coverage explanation above for actual inclusion.

Steps, each one a playtest build:

1. One CHIM block inside the legacy island (a 3 x 3 Bitter Coast area): the handover between CHIM
   and legacy land, the border audit ([STITCH_AUDIT.md](chim/STITCH_AUDIT.md)) and its fixes
   (shoreline detail, a terrain margin around the frame). Measured after the fixes: no height
   step and no gap on any edge of the test area.
2. The sea and the shoreline ring: the seabed cells, the open sea (one shared ocean chunk stored
   once) and the coastal cells, chosen as cell lists (region names, a CSV or JSON list, or a
   selection exported from the Toolkit's World Map). Their legacy region maps leave the image.
3. Vivec, which closes the ring on the south coast: the existing canton split as CHIM areas, with
   very large models cut into chunk-sized pieces and the densest meshes simplified. If Vivec is
   not ready in time, it moves to the next release instead of holding this one.

Measured on the way (10 October 2026): with shared terrain stored once and referenced by each cell
(`--chim-terrain-refs on`, with `--chim-terrain-hull compiled`; experimental, off by default), CHIM cells
in the open world take 0.91 to 0.93 times the bytes of the legacy maps they replace, where each cell's
own terrain copy took about 3.5 times. Cells the legacy builder split over several maps cannot switch
yet (CHIM-REGION-DIVIDED-CELLS-36).

World bounds (on by default, `--world-bounds off` to turn off; `dbg worldbounds` in game): a player who
swims or sails out past the island meets a sea current along the edge of the world and is pushed back, instead
of the invisible wall at the end of the outer maps; out of the water the push back works the same way, and the
edge moves out by itself as more cells join the world. Quake's own current, applied by position. The original
game has no such limit; this is an AmiWind addition ([WORLD_BOUNDS.md](WORLD_BOUNDS.md)).

Still to do along the way: buildings of a CHIM area appear only when the player crosses into it
(seen from legacy land the area shows its ground and rocks); harvestable plants in extra CHIM
areas; collision for thin underwater plants; and rebuild cascades in the builder.

Next, v0.0.38: all green zones. Every cell shown green (finished) on the CHIM Progress Tracker map, about 670 cells,
moves onto CHIM in the game and is tested there, with bug fixes along the way. The first item is the lava
stale-source fix (CHIMPORT-RETRY-LAVA-STALE-SOURCE-36). The tracker already shows this plan in pale gold.
Also for v0.0.38, from the maintainer's dev5 playtest: the NPC you are fighting must stay visible in third person
(CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36), and, longer term, blocking: NPCs block by their Block skill with a block animation, and the player
blocks with the right mouse button, with the companion pick on another key (COMBAT-BLOCKING-36; the original rules are
researched first).
Then the rest of the island follows the conversion spiral, ring by ring from the coast inward. Each ring gets the
same border checks and a playtest.

## v0.0.35 - CHIMporting It All: Gathering Up The Loose Branches From The Seashore (released)

v0.0.35 gathers in the work that was finished over the last releases but left on side
branches: builder improvements (resumable image step, unit caches and output hashes, a
shared storage pool, a build preflight, tighter reuse keys), lava, the CHIMport tracker
and more. Unfinished or experimental work ships behind a switch that is off by default.
Release notes: [RELEASE-v0.0.35.md](RELEASE-v0.0.35.md).

After v0.0.35, with no dates promised:

### Next: build system

**Very near term: a fast build system (11 October 2026, top priority after the current fixes).**

- Fast and parallel everywhere it is safe: no phase runs on one core while the others wait; any phase over 30 s below
  half of its core budget is flagged by the build itself.
- No useless runs and no re-runs: every step is computed once, recorded by the SHA-256 of its inputs, and reused by
  every build and every developer job; only what changed is computed again.
- Checks that have passed stay passed: the stair walk becomes a lookup of recorded results (walked again only when a
  frame's collision changes, with a small random spot check); smoke tests run on fuller builds when they are needed,
  not on every build.
- Every phase shows what it is doing and how long it took.

Build speed (10-11 October 2026): a rebuild should cost only what changed, and a first build should keep every core busy.
Every step keyed by the SHA-256 of its inputs and reused (stair walks, CHIM statistics per frame, image passes per map);
CHIM region frames prepared side by side; the worker pool resizes while it runs; side jobs back off during a release
build; no silent phases (start and end lines with timings, progress counters, a heartbeat; quiet only as an option);
honest per-phase time estimates; the live stage timeline in the Toolkit Monitor. Engine side: the float-to-integer
conversion overhead, the edge and clip code, then hand-written 68k routines where measurements point.

- One build tool with the stages described as a table, so a stage's inputs and outputs are
  declared once and checked by the builder.
- Smaller units of work for the slow stages (rooms, regions, image parts), each with its own
  content hash, so a change or a failure rebuilds only what it touches.
- One shared content store for every cache, with clear cache keys, and a checked build
  environment.
- A test harness and continuous checks that run the same way locally and on a second machine.

### Build pipeline speed (very near term, after Vivec)

A build should spend time only on what changed, and the first build should keep the whole machine busy. In order:

1. A world map manifest first. One list decides, for every map, CHIM or legacy before the first stage runs; every stage
   reads it. The image step's replace-in-place becomes a check that must find no legacy map of a CHIM cell
   (a v0.0.36 development build converted and optimized 270 such maps, 194.7 MB, and threw them out at the end).
2. Dead weight out: legacy maps of CHIM cells are neither built nor processed (a development build built 335 of them,
   65 Seyda Neen maps and 270 CHIM region cells, and removed them again before packing; this saves build time, not
   image size).
3. Every phase parallel: the image step (maps, audio, video), the statistics step and the optimizer, through the shared
   worker pool, with results identical for 1 and for 24 workers.
4. Incremental rebuilds by hash for every unit, and the optimizer cache key fixed so a small change redoes only its units.
5. No silent phases: verbose by default with a heartbeat, quiet only as an option.
6. One profiler (`tools/build_profile.py`): the timeline and the optimize sweep in one tool.
7. The Toolkit Monitor shows the activity of each phase.
8. Honest estimates: a time estimate is based on measured earlier runs and says how reliable it is.
9. A measured build that proves it: cores used per section, what was reused, and the time against the earlier build.

These problems are persisting, not resolved: several were found and fixed in part since 8 October 2026 and came back. Tracker: BUILD-PIPELINE-UNDERUTILIZATION-36, whose page indexes these as the eight build rules with every earlier entry, and the bugs linked from it.

### Perf, profiler and optimizer (future)

A better pipeline for finding and removing slow or idle build sections:

- A perf database of every run (stage times, cores used, what was reused, host load).
- Automatic detection of sections that leave cores idle, with each one turned into a tracker item automatically.
- Per-section core use in every build summary.
- Comparison across runs, so a slower section shows up at once.
- A CI or gate check on a benchmark build that fails on new underutilization.

### Next: CHIMport region by region, coast first

- The open world converted to CHIM region by region, from the sea and the coast inward, with
  live cell status in [docs/chim/CELL_TRACKER.md](chim/CELL_TRACKER.md).
- CHIM lighting: the terrain light bake (the "hybrid" lighting type is partial until then).
- Heightmap terrain collision: a prototype, measured first.

### Gameplay

- Implemented in published v0.0.38 source: saved noclip-only walking bob and
  movement roll, `dbg noclipwobble [on|off]` with alias `dbg noclipbob`, default
  **off** (`0` / `false`). It reuses AmiQuake's view-bob and roll paths in
  `view.c`; ordinary walking retains its existing behavior. Photo mode
  temporarily disables it and restores the previous setting. Preserve the
  existing off/on, normal-walking and photo-restoration checks in later builds;
  source presence alone does not establish native acceptance for a new image.

- Combat and companion leftovers: hit chance, block, voices, death animation and sound,
  first-person weapons.
- Background music: the `dbg music on/off` / `aw_music` switch already exists.
  The audio settings menu, saved setting and builder option remain follow-up
  work ([ENGINE-MUSIC-NO-OFF-SWITCH-36](bugs/ENGINE-MUSIC-NO-OFF-SWITCH-36.md)).
- More of Morrowind's animation groups wired ([ANIMKIT.md](ANIMKIT.md) lists them).
- Modular NPCs: a shared parts library converted once, with per-character recipes.
- A third-person view, following the original game's camera (the original and OpenMW as the references),
  which also gives the death scene its original look: the view leaves the player and fades out.
  In v0.0.36-dev: Tab, the held orbit, the wheel zoom, the vanity camera and the death camera with a stand-in
  body per race and sex ([THIRD_PERSON.md](THIRD_PERSON.md)). Next: the character's own head and hair, the
  worn clothes and armour, a jump group and smoother walk/run cycles.
- After a lost fight: the original's choices (load a save, main menu) plus an optional quick retry (in
  v0.0.36-dev: `--death-retry`, default on).
- The original's on-screen display, bottom corners (planned for a later version, agreed 10 October 2026;
  OpenMW frames as the reference): bottom left the player's health, magicka and fatigue bars, the equipped weapon box and the
  selected spell box; bottom right the local map with the player's arrow and the active magic effect icons.
  The original draws its local map live from the world; here the builder pre-draws one small map picture per
  exterior cell and per interior, and the engine shows the current one and turns the arrow. If that proves too
  heavy, a simple compass in the same frame replaces it (both kept selectable). Drawn with Quake's own status
  bar pictures, converted at build time from the maintainer's game data; memory measured against the town limits
  first.
  Layout: sizes and positions from OpenMW's HUD files, scaled to the AmiWind screen, A/B'd at the same pose.
- Waiting and resting with the original's rules (planned, 10 October 2026). Today **T** only moves the clock
  forward ([DIALOGUE_AND_WAIT.md](DIALOGUE_AND_WAIT.md)); nothing is restored while waiting. To be taken from the
  original's own rules (OpenMW's source, the game settings in the master file and the original's documentation),
  never invented: rest versus wait (where sleeping is allowed, enemies nearby, owned beds), what each restores per
  hour (health, magicka, fatigue) and from which attributes, what blocks it (for example a birthsign that stops
  magicka returning), what does not heal with time (diseases, blight), timed spell effects running out, sleep
  interrupted by a creature in the wilderness, and levelling up when sleeping. Each rule records its source.
  The study with numbers and sources: [WAIT_AND_REST.md](WAIT_AND_REST.md).
  Memory: nothing about where sleeping is allowed stays in memory. The builder writes one bit per exterior cell into a
  small table indexed by the cell's coordinates; pressing T reads the one byte that holds the current cell's bit from
  disk. An interior carries its flag in its own map, which is loaded anyway. Rare rule lookups in general follow the
  same pattern: coordinates to an index, read on demand.
- Living towns: every NPC that can move or fight gets walk, run, swim and attack animations (checked by the
  builder for every NPC), and residents follow their original Wander packages - strolling within their
  authored radius along the cells' path grids and playing their idles, as in the original.

### CHIM maps become their own format (approved 10 October 2026)

CHIM frame maps are named `.chim`, separately from legacy `.bsp` maps. Their
current shell still uses the BSP29 binary layout and decoder; the streamed
world already has its separate container format. The next format step remains
planned: a `.chim` gets its own header
(CHIM magic, map version, world format) and its own loader in the engine, a CHIM major-version step; then its
contents leave BSP29 one measured step at a time: entities as a compact binary table, no dummy BSP parts, no BSP29
limits where CHIM needs more, precomputed tables. An interior's format is
independent of exterior replacement and may remain BSP29 or move to CHIM. Design and
measurements: [.chim map format](chim/CHIM_MAP_FORMAT.md).

### Tiny squeezes: memory that stays resident

Small savings that add up, and a guard so they cannot grow back (10 October 2026; candidates with numbers in
[MEMORY_ALLOCATION.md](MEMORY_ALLOCATION.md)):

- A ratchet test: every command, setting and permanent name table the engine registers is counted with its exact
  byte cost against a committed budget. Growing past it fails the gate; moving something to disk lowers the budget
  for good. In place (ENGINE-RESIDENT-REGISTRY-GROWTH-36, `tests/test_resident_registry.py`); budget of 10
  October 2026: 266 commands (32 bytes each, 8,512 bytes of hunk) and 321 settings (7,704 bytes of structures and
  10,496 bytes of zone for their values).
- Console commands behind on-disk routes: the `dbg` names, aliases and help are already read from disk only when a
  command is submitted; most of the commands behind them can follow, leaving a few dispatchers per module (keys
  that are held, such as Tab, keep real commands).
- Rare rule lookups from disk: coordinates to an index, one byte read when the question comes up (where sleeping is
  allowed first, then similar rules).
- Disk-backed console history instead of the resident 16 KiB output ring.
- About 13 KB in Balmora's CHIM ring, so that exact building collision can be switched on for every model.

### Roadmap horizon: one partition with CHIM

With the whole island on CHIM, the whole game on one disk image, with the world in a single
partition. This is a horizon, not a promise for a release: the image stays as it is until the
whole island runs on CHIM. Details and measurements: [IMAGE_SIZE.md](IMAGE_SIZE.md).

The goal is one image file, not two. v0.0.36-dev3 ships as two image files (4,026,564,608 and 1,610,645,504 bytes, 5.25 GiB
together) with three world partitions (the system partition and one world partition on the first disk, two world partitions
on the second). Every partition is under 2 GiB and starts below 2 GiB, so the platform limits hold, but the target is not
met. One image of about 3.75 GiB means the payload must shrink by about 1.5 GiB. The path: dead weight out (see the
build pipeline section above, which saves build time, not image size), store-once CHIM for the open world, and a payload breakdown by kind printed by every image
summary so each kind has a visible budget:

| Kind | dev3 today | Budget for one image |
| --- | --- | --- |
| World maps (CHIM and legacy) | not yet measured per kind | to be set from the breakdown |
| Audio: voices (6,447 files) | not yet measured per kind | to be set from the breakdown |
| Audio: effects (717) and music (18) | not yet measured per kind | to be set from the breakdown |
| Video (17 files) | not yet measured per kind | to be set from the breakdown |
| Interiors | not yet measured per kind | to be set from the breakdown |
| Total | 5,637,210,112 bytes | about 3.75 GiB (4,026,531,840 bytes) |

Tracker: IMAGE-ONE-HDF-TARGET-36 and BUILD-PARTITION-GROWTH-UNGATED-36 (nothing gates the number of world partitions or the image size yet).

## v0.0.34 - CHIM: Tightening the Bolts (released)

A fix release on top of v0.0.33: the silt strider's hull is closed and every Bitter Coast
mushroom can be picked, each with an island-wide check that runs in every build
([release notes](RELEASE-v0.0.34.md)).

## v0.0.33 - Towards CHIM: Replacing the Engine Block (released)

v0.0.33 is out: the first release on the CHIM engine, the world streamer, with
Balmora and Seyda Neen on CHIM and the CHIM builder as the default
([release notes](RELEASE-v0.0.33.md); plan below and [world streamer](WORLD_STREAMER.md)).
The release before it, v0.0.32, was the last on the legacy engine
([release notes](RELEASE-v0.0.32.md)).
What CHIM is, its versions and milestones: [CHIM](chim/README.md); every
idea that is designed, measured or held back, with its status:
[CHIM ideas](chim/IDEAS.md).

Next: the animation kit for all character types, Vivec on CHIM and the CHIM open
world (milestones M3 and M4), with no dates promised.

The open world on CHIM started with v0.0.35 (above); live cell status in
[docs/chim/CELL_TRACKER.md](chim/CELL_TRACKER.md) (generated from the conversion tracker). A cell is only complete
when it is lit like the original: the [CHIM lights roadmap](chim/LIGHTING_ROADMAP.md) lists the lighting milestones
for this release and later (light tracker done; shared light entities and lightstyles; terrain lightmaps; a light
level per placed model; dynamic lights of every class; per-plant glow; later per-placement lightmaps for an
increased-memory version, shadows and interiors).

## v0.0.32 - Last Stop on the Old Line: Window-Shopping in Vivec (released)

v0.0.31 (Lamps, Lanterns and Loading) was out. v0.0.32 started with Vivec, built
by the generic town importer with no hand-building, and with fixes found by
measuring the whole island on 8 October 2026
([world progress](trackers/WORLD_PROGRESS.md), [bug register](BUGS.md)):

1. **Vivec first.** The Arena and the cantons through the normal doors, after
   the limits that block them: texture mappings read unsigned (32,767 to
   65,535, [VIVEC-TEXINFO-31](bugs/VIVEC-TEXINFO-31.md)), leaf face lists read
   unsigned ([MODEL-MARKSURF-SIGNED-31](bugs/MODEL-MARKSURF-SIGNED-31.md)),
   surface extents ([MESH-EXTENT-GRID-31](bugs/MESH-EXTENT-GRID-31.md)), the
   lightmap overrun ([LIGHTMAP-TAIL-31](bugs/LIGHTMAP-TAIL-31.md)), the night
   lamp cache ([LAMPS-CACHE-31](bugs/LAMPS-CACHE-31.md)) and interior
   coordinates ([INTERIOR-COORDS-31](bugs/INTERIOR-COORDS-31.md)).
2. **Real 68040 compatibility and speed.** The engine reaches FPU instructions
   the 68040 does not implement, every frame, and the boot disk loads no FPU
   support library; the emulator hides both
   ([ENGINE-FPU-UNIMPL-31](bugs/ENGINE-FPU-UNIMPL-31.md),
   [ENGINE-FPSP-MISSING-31](bugs/ENGINE-FPSP-MISSING-31.md)). Fixes reuse
   Quake's own answers: no rotation for unrotated brush models, table
   sine and cosine, work done once per frame.
3. **Distant shells.** Buildings far away drawn as closed low-poly shells
   instead of full meshes, so the town stays visible without its full cost
   (prototype on Balmora first).
4. **Your own estimate.** A builder command that estimates every map of the
   island from your own Morrowind files, shown as a layer on the Toolkit's
   World Map.

Before the v0.0.32 release (fix-before-release list):

- Visiting Vivec: `dbg tp vivec` takes you to the Vivec Arena preview (outside only;
  its doors do not open yet), and the release notes say so
  ([DEBUG-TP-TOWN-NAMES-32](bugs/DEBUG-TP-TOWN-NAMES-32.md), fixed in source).
- A from-scratch build with the repository builder reproduces the release payload,
  file by file, with the recorded Seyda Neen exception
  ([BUILD-WORLD-LAYOUT-DRIFT-32](bugs/BUILD-WORLD-LAYOUT-DRIFT-32.md) byte check
  included).
- No private-test waiver: the Arena residents pass the actor check or are left out
  ([VIVEC-ARENA-ACTORS-32](bugs/VIVEC-ARENA-ACTORS-32.md)).

### Decided: a world streamer with no duplicated assets - the whole game on one hard file

Keep the AmiQuake engine (renderer, lighting, collision, QuakeC) and change how
the open world is stored: every asset stored once and placed by reference, as
Morrowind itself does (its base game holds all meshes and textures in about
310 MB and the whole world in an 80 MB file), streamed around the player.

**Why.** Today every exterior region is a self-contained Quake map holding
everything visible from it, so each exterior object is stored about ten times
([WORLD-REGION-DUPLICATION-31](bugs/WORLD-REGION-DUPLICATION-31.md); Seyda Neen
24 times per face, Balmora 7 times, [sub-cell redundancy](SUBCELL_REDUNDANCY.md)).
Two towns and the terrain already take 4.8 GB; with today's pipeline the whole
game would need about 24 GB (15 legacy partitions), and the oversized regions
cause most heap failures. Quake's `vis` gives little outdoors
([town visibility](performance/TOWN-VISIBILITY.md)), so the new layout gives up
nothing it was providing.

**Measured result (8 October 2026, estimate built from the game's own data:
every unique mesh, collision hull and texture counted, light per placement
checked against real bakes; [asset census](ASSET_CENSUS.md),
[streamer design](WORLD_STREAMER.md)):**

| | Today's pipeline | World streamer |
| --- | ---: | ---: |
| Whole game, all files | about 24 GB | **about 1.75 GB** (a leaner layout 1.61 GB) |
| Legacy-safe drive images (under 4 GiB) | 8 | **1** (estimated; see the note below the table) |
| Every texture of the game | about 1.4 GB (a copy in every map) | **19 MB** (each stored once) |
| Island terrain | about 1.8 GB compiled | **17 MB** as a heightfield |
| Exterior model variants | 33,076 | **1,405** meshes (scale and tilt applied at run time) |
| Worst memory around the player | regions over the heap budget | **4.9 MB** with 256-unit chunks |
| Largest load while walking Balmora | 4.6 MB per region crossing | **0.8-1.4 MB** per chunk |

The non-map part of these totals (sound, music, video, the NPC gallery) is still
v0.0.31's, which covers two towns: the whole game's actors and voices will add to
it, so expect the hard file to be well over half full, but still one hard file.

The target is the whole game on one legacy-safe drive image (under 4 GiB, with
partitions under 2 GiB); two images is the absolute limit. Every file follows
classic FFS: files well under 2 GiB (asset packs of about 1 GiB at most, split
by area), names of at most 30 characters, few files per directory, packs
written last and whole in map order. The builder will check this layout.

**How it works:**

- **Asset packs** (Quake PAK files, split by area and stored in map order): each
  mesh, collision hull and texture once, one shared texture pool.
- **Chunks** (grain still to be measured; 256 units looked best on memory, larger
  chunks need fewer disk reads): each holds terrain (compiled per chunk first; a
  quantized heightfield built at load is a later optimisation, because collision
  then needs a new path) and a list of placements: which mesh, where, which
  way, how large, and a lighting record.
- **Scale and tilt at run time** for drawing; collision hulls stored once and
  expanded per placement at load.
- **Three lighting tiers:** terrain keeps its lightmaps; buildings, furniture
  and rocks get lightmaps per placement on shared geometry; flora and clutter
  get one light level each (outdoor objects already have no lightmaps today).
- **Memory:** a ring of chunks around the player inside draw distance, loaded
  ahead of you and released through Quake's cache (made able to move brush
  models); a loader process reads the disk while the game keeps drawing;
  coordinates re-centred as you travel so they stay within Quake's range.
- **Distance tiers** for the frame rate: full detail nearby, closed low-poly
  shells further out, the horizon beyond.
- **Interiors** stay legacy Quake maps behind doors in the first CHIM releases.
  Moving their pieces to shared placements later removes the 220-model limit, but
  then they also need the per-sector visibility lists outdoors needs, because
  placements are not culled by Quake's `vis`.

**Plan:**

1. **v0.0.32 - Last Stop on the Old Line: Window-Shopping in Vivec** (released, the last
   release on the legacy engine and builder, built from scratch): Vivec with today's format; the measurements behind the
   streamer (census done; renderer counters and a cycle-approximate emulator
   profile in progress); real 68040 safety (no library sine and cosine per
   frame, Quake-style number parsing, your own FPU support library if you have
   one); a map loader without temporary copies; one shared face builder with a
   validator; builder types: today's region pipeline kept as the "legacy"
   builder, CHIM as the new one (named, not numbered; CHIM has its own version).
2. **v0.0.33 - Towards CHIM: Replacing the Engine Block** (released, the first CHIM engine release): the streamer (CHIM builder and engine 0.1.0) on Balmora, Seyda Neen and the cells
   between them, measured against v0.0.31 on the same routes: worst frame time,
   bytes per crossing, memory peak, saves mid-stream.
3. **Next:** the south-west corridor (Seyda Neen, Pelagiad, Balmora, Vivec,
   Ebonheart exteriors), then the rest of the island release by release. CHIM 1.0
   is the release in which the whole island runs; expect months, not weeks. We
   are aiming for the whole island by Morrowind's 25th anniversary, 1 May 2027:
   an aim, not a promise.

Repository layout from v0.0.33 (decided 8 October 2026). CHIM is the same AmiQuake
engine growing a streamer, not a second engine, so the engine stays one tree:

- `engine/aga/src/` remains the one engine; CHIM's own code (model library, chunk
  loader, world shift) lives in `engine/aga/src/chim/` with small hooks in the
  Quake files. "Legacy" is the old code path, used whenever no CHIM data is
  present, and the v0.0.32 tag.
- `tools/chim/` holds the CHIM builder. The parts both builders use (model and
  texture conversion, BSP writing) move step by step into one shared package, so
  the legacy builder and CHIM call the same code rather than copies.
- `docs/chim/` holds the CHIM format, design, measurements and release notes.
- Licences stay clear per folder: the engine is GPLv2 (from Quake), the builder
  GPLv3.
- Existing files move only after v0.0.32 ships, in one restructure commit with
  `git mv` (history follows) and the path tests and release file list updated
  in the same commit. Until then CHIM work only adds new folders.

The open question is speed on a real 68040: every figure so far comes from the
emulator ([BENCH-JIT-PROFILE-32](bugs/BENCH-JIT-PROFILE-32.md)), so a small
benchmark for real accelerated A1200s is being prepared. How data streams
today: [DATA_STREAMING.md](DATA_STREAMING.md).

### Near future: fires and lava across the world

- **Fires everywhere.** The new hearth fire (flames shaped by each Morrowind
  emitter, a hot colour ramp and rising embers) reaches every fireplace,
  brazier, campfire and firepit as maps are rebuilt; each keeps its baked
  light, and Morrowind's flicker and pulse light flags become Quake light
  styles so the firelight flickers (cost measured on the 68040 first).
- **Lava fields** (Molag Amur and Sheogorad outdoors, and 59 interiors such as
  the Dagoth Ur facility, [lava census](LAVA.md)): Morrowind's lava pools
  converted to Quake liquid surfaces, which the engine already draws with an
  animated warp and full brightness, with lava contents (blood-red view tint
  and Morrowind's damage when entered) and a few embers rising from the surface.

Before building more of the world at scale: the [trackers](trackers/README.md)
(world progress, entities, points of interest), so nothing is left behind.

After that: lighting follow-ups, a battle-arena test room, then inventory,
character statistics, a map that reveals as you travel, and the heap option
below.

## Planned: heap size matched to the host machine, 7 October 2026

The game heap is a fixed 11 MiB. On the reference configuration a fully loaded
Seyda Neen sub-cell leaves only about 2.6 MB of it for cached models, so each
crossing evicts and re-reads actor models
([Seyda Neen performance](SEYDA_NEEN_PERFORMANCE.md)). Accelerated Amigas such
as an A1200 with a PiStorm32 Lite or a full 68060 board have far more Fast RAM
([hardware FAQ](FAQ.md#can-todays-heavily-upgraded-amigas-realistically-run-amiwind)).

Plan, measured before it is built:

1. Emulator test: more Fast RAM and a larger heap on the same Seyda Neen route.
   Continue only if evictions and crossing times improve clearly.
2. [x] Startup check: when much more Fast RAM is available, the game uses it by itself
   (maintainer, 16 October 2026: the benefits come automatically): a short notice in plain
   words says how much extra RAM was found and that it is being used for caches, with a key
   (M) to skip it for this start (the game then runs on the baseline). An Options setting
   (Extra RAM) turns it off for good; the engine falls back to no extra caches if the larger
   allocation fails. Done in v0.0.42-rc1 for the CHIM cache, the chunks kept after leaving
   them and the look-ahead, with no upper limit but the machine (one bank per memory region,
   each under 2 GiB); measured 17 October 2026 in FS-UAE, 16 MiB against 128 MiB: zone
   failures 625-655 and 288-312 to none, evictions on a Seyda Neen flight 487-550 to none,
   frame time unchanged within drift; 16 MiB takes nothing
   ([memory guide](chim/build_guide/MEMORY.md#more-fast-ram-the-automatic-chim-cache)).
   The game heap stays at its built size: a larger heap only feeds Quake's actor and sound
   cache, and step 1 (does it help the Seyda Neen crossing?) is not measured yet, so it
   stays manual (`-heapmb`).

The baseline does not change: AmiWind must stay playable on the reference
configuration with the 11 MiB heap. Memory budgets, release gates and
acceptance stay measured there, and nothing may depend on the larger heap.

### The cache plan: extra RAM spent on not doing work twice (16 October 2026)

Project decision, 16 October 2026: the baseline game keeps working on today's memory setup, and the game uses more
RAM when a machine has it, as caches. This extends the 11 October plan (adaptive CHIM caching and non-blocking world
streaming). Step zero exists already: the start arguments `-chimcache KIB` (shared models and textures kept across
map changes) and `-heapmb N` ([hardware guide](REAL_HARDWARE.md#more-fast-ram-the-memory-settings-that-exist-today));
they stay as the manual override when the sizing becomes automatic. The memory budgets that must fit (the CHIM zone gate) stay the same; a
16 MB machine plays exactly as today, a 128 MB card or a PiStorm plays smoother. At start-up the engine asks how
much fast RAM is free and sizes the caches from it; each gain is measured in the emulator, then on real hardware,
in order of expected gain:

1. A larger surface cache: Quake's lit surfaces rebuilt less often, a direct frame-rate gain.
2. [x] Streamed CHIM chunks, models and textures kept resident in a larger LRU cache (Quake's `Cache_*`), so ground
   already seen costs no disk reads. v0.0.42-rc1: the automatic CHIM cache banks (step 2 above); measured: no
   evictions and no failed loads where 16 MiB had hundreds.
3. [x] Prefetch further ahead: the next frames' chunks loaded before the edge is reached, seamless crossings on slow
   disks. v0.0.42-rc1: the look-ahead doubles from 8 MiB of cache and triples from 32 MiB; first-time ground
   still reads in the frame (worst frames 0.19-0.29 s on a flight in FS-UAE, against 0.22-0.36 s on 16 MiB):
   that needs reads that finish in the background.
   [x] v0.0.43 (CHIM-CROSSING-SYNC-LOAD-43): outdoors every cell is its own frame map, so the pauses were the cell
   crossings themselves, a map change each. With extra RAM the files of the cells ahead are read into spare RAM in
   slices (the 2x2 block at the nearest corner first, the cell walked towards leading, then the 3x3 ring; the block
   moves only past a margin, so a corner or an edge does not load and drop the same cells), and the world index and
   each frame's placement count stay in RAM instead of being read on every crossing. Measured in FS-UAE (JIT,
   128 MiB, the same open-world route on the dev2 data): crossing median 452 ms to 223 ms, seconds with a frame of
   300 ms or more 11 to 2 of 178; a four-cell corner 426 ms to 146 ms. 16 MiB unchanged.
4. Visited interiors kept in RAM: going back through a door needs no loading pause.
5. Read caching for the hard file: recently read blocks stay in memory. (v0.0.43: the CHIM prefetch above is this
   for the world's files: read ahead, kept, served from RAM.)
6. [x] The game heap sized from the free Fast RAM (v0.0.43, ENGINE-HEAP-FIXED-SIZE-43): the built 11 MiB on 16 MiB
   machines, up to 24 MiB with plenty of RAM (128 MiB: 24 MiB heap, 82 MiB CHIM cache), so Quake's own cache keeps
   actors and sounds across map changes and the maps keep their 2 MiB safety gap; `-heapmb` stays the override.

## Other ideas and wildcards

Ideas worth keeping, not scheduled. They wait until the work they depend on
exists.

### Sky fading into the horizon

At its lowest points the sky should fade into a gradient, not end in a crude cut-out. This pairs with the sea skirt
being prototyped for the open ocean (off by default until the maintainer approves it): both fade into the same horizon colour.

### Sea skirt: the sea runs to the horizon

The sea runs to the horizon and fades into it: flat colour bands beyond the draw distance, going from the sea colour to
the horizon colour. Views over water from high places, such as Vivec's cantons, then show sea instead of a flat fog band.
Targeted at v0.0.36 if it is ready in time, otherwise first in v0.0.37.

### Weather: ash storms and blight winds

Morrowind's regions have their own weather, and two kinds define the land
around Red Mountain: ash storms and the red blight winds. Both belong in
AmiWind at some point, built from what the engine already has: the
[day and night sky](DAY_NIGHT_AND_SKY.md) layers with faster, darker clouds,
the distance fog pulled in close, a full-screen colour tint like the one Quake
uses under water and in lava (ash grey, blight red), and a capped stream of
wind-driven grit from Quake's particle system, plus the storm sound. Each
region keeps its Morrowind weather chances; the cost is measured on the 68040
before it ships.

### Long-term possibility: a reusable Amiga game engine

Underneath the Morrowind content, AmiWind is becoming a general open-world
toolkit for AGA Amigas, all GPL: streaming sub-cell worlds with bounded memory
and build-time memory budgets; a converter pipeline from large 3D scenes to
Quake BSP maps; glow, NPC floor lighting, emitter-shaped flames,
Quake-particle embers and warped liquids; menus, rebindable controls, a book
and journal reader, music streaming, saves, dialogue and first-person hands;
and headless emulator testing, a debugger harness and heap auditing.

Someone making their own Amiga RPG, dungeon crawler or adventure game could
start from this instead of from zero. The aim: document the engine and tools as
reusable on their own, separate from the Morrowind conversion, with a small
example project that uses no game data.

### Long-term possibility: an RTG display path

AGA stays the primary display, and the project's look is built around the Amiga's own OCS and AGA graphics
modes. On fast CPUs (a PiStorm, a Vampire, a quick 68060) the screen starts to take a real share of the frame,
and a graphics card screen could take the renderer's 8-bit chunky buffer as it is, without the chunky-to-planar
conversion AGA needs. Picasso96 also provides the CyberGraphX interface, so one path would serve both, and the
engine already carries an inherited, untested CyberGraphX path. The emulators' virtual graphics card (UAEgfx)
makes it testable without hardware. Possible scope: choose an RTG screen at startup when one is present (AGA
otherwise), the palette and double buffering, the HUD, menus and video, and a measured comparison with AGA. A
future path to look into, not a planned release item ([FAQ](FAQ.md#why-not-use-pistorm32-rtg-and-minigl)).

### Research: hardware 3D through Warp3D (v0.0.50 study, 24 October 2026)

An RTG screen alone does not make the 3D faster: the 68k still textures every pixel, and the finished frame then
crosses the expansion bus to the card. That is why a 68060 at 80 MHz on RTG stays at a few frames per second. A
number of graphics cards that reached the Amiga are 3D cards of Morrowind's own era (Permedia 2 on the
CyberVisionPPC and BlizzardVisionPPC, Voodoo 3/4/5 and Radeon cards through PCI busboards), and
[Warp3D](https://wiki.amigaos.net/wiki/UserDoc%3AWarp3D) lets a program hand its triangles to them. Warp3D
draws only: texture mapping, filtering, depth buffering and blending happen on the card, while visibility,
transforms and lighting stay with the program. That is the same split as Quake's own GL renderer. In Quake-style software renderers the drawing is
usually about half to two thirds of the frame; AmiWind's own split is not measured yet (study step 1). AmiWind would open `Warp3D.library` at run time when the player has it
installed and keep the software renderer otherwise; nothing from Warp3D is shipped. Other classic games have
already reached Amiga graphics cards, so the hardware is there.

The 3D chips that Warp3D's own documentation lists, with what it says about them:

| Chip (Warp3D driver) | Cards named | What the documentation says |
| --- | --- | --- |
| Permedia 2 | CyberVisionPPC, BlizzardVisionPPC (8 MB) | The oldest; 8 MB of card memory and a slow interface; no multitexturing, MIP mapping or stencil buffer |
| Voodoo 3 (Avenger), Voodoo 4/5 (Napalm) | PCI cards | Dithering settings; full-screen anti-aliasing on the Napalm |
| Radeon R100 | Radeon 7000 | Anisotropic filtering; a 16-bit depth buffer to save card memory |
| Radeon R200 | Radeon 9250 and others | Anisotropic filtering, per-program settings |

These are the AmigaOS 4 drivers (Warp3D version 5); which of them exist for a 68k Amiga on AmigaOS 3, and on which
busboards, is part of the study.

What a better RTG path alone would give, estimated (not measured): a 320 by 200 frame at 8 bits is 64 KB, which
crosses Zorro III in a few milliseconds. At 2 frames per second a frame takes 500 milliseconds, nearly all of it the
CPU drawing and walking the world, so even a perfect RTG path would gain little, perhaps 5 to 15 per cent. Moving only
the final drawing to the card would, by the usual split above, make the frame roughly two to three times faster, since
visibility, transforms, lighting and game logic stay on the CPU; handing whole models to the card could also drop the
clipping work below, which is why that design is the one to measure. These are estimates until the experiment below
measures them. Frame rates in the twenties need a hardware path together with a cheaper CPU side of the frame
([AmiWind on the 68060](68060.md)) and the faster 68k of the machines AmiWind aims at
([real hardware](REAL_HARDWARE.md#which-machines-amiwind-aims-at)).

**Three different things, three different gains.** "RTG" can mean any of them, and only the third moves the 3D
work off the CPU:

| Path | The CPU does | The card does |
| --- | --- | --- |
| Today's AGA renderer | everything: geometry, texturing, lighting, depth, fog, chunky-to-planar | shows the bitplanes |
| The software renderer with an RTG screen | the same, without the chunky-to-planar step | shows the chunky frame; may speed the copy |
| A hardware 3D renderer | game logic, streaming, visibility, transforms, handing triangles over | rasterising, texturing, depth tests, blending |

**Where today's frame goes.** The placed models (houses, rocks, props) were 60 to 79 % of the 3D view in the
v0.0.42-dev1 measurements, and walking the world's tree for them about half of that
([where a slow frame goes](performance/SLOW-FRAME-BREAKDOWN.md); emulator figures of an older build, so they show where
the cost sits, not today's exact share). Each model's polygons are clipped against the world's tree
(`R_RecursiveClipBPoly`, `engine/aga/src/r_bsp.c`) and then drawn as spans on the CPU. That clipping exists only to
feed the software renderer. So the choice of what a hardware renderer replaces decides the gain:

- Uploading the finished software frame to a card keeps all of that work.
- Keeping the clipping and only drawing the final spans on the card saves the pixel work, not the geometry work.
- Handing each visible model's triangles to a depth-buffered card skips the clipping and the edge lists as well. The
  visibility and collision structures stay; only the drawing changes. That is the case to investigate.

CHIM is a good starting point: its model store (`engine/aga/src/chim/chim_models.c`) already keeps each shared model
once, apart from its placements, and manages what is resident. A hardware path could build each loaded model's
triangles and texture coordinates once, reuse them for every placement, and keep a matching texture cache in the
card's memory.

**Two catches to design around.**

- **Fog.** The fog pass (`engine/aga/src/aw_fog.c`) reads the depth buffer and reads and rewrites the frame's pixels.
  Reading the card's frame and depth back every frame would eat much of the gain, so fog, the sky and the related
  effects move into the hardware path itself.
- **Palette and lighting.** The renderer lights through palette tables, and the game changes the palette. Indexed
  textures can be expanded for the card, but the look of the palette lighting, its changes and the fog take explicit
  work, and a true-colour screen alone cannot bring back colour the texture conversion already dropped.

**For an RTG screen alone** (the software renderer, no 3D card), the first design to measure keeps drawing in Fast RAM
and uploads the finished frame: drawing straight into the card's memory (`-directcgx`) can be slower on some cards,
because the fog pass reads and rewrites every pixel. The profiler times the AGA chunky-to-planar step but neither an
RTG upload nor the display swap; both timings come first, so the comparison is like for like.

**The first experiment, deliberately narrow.**

1. Add the missing timings: RTG upload and display swap beside the chunky-to-planar time.
2. Pick one card, driver and API that can be verified (classic Warp3D, or a GL layer over it), and the emulator setup
   that runs it (WinUAE emulates a Voodoo 3).
3. Textured triangles with hardware depth testing on that setup.
4. One representative CHIM scene through the new path: the same assets, camera and visibility, triangles and textures
   cached, the software clipping, edge and span path bypassed for it.
5. Measure the CPU's preparation, the submission, the texture uploads and the whole frame (waiting for the card
   included), against the software renderer on the same scene.
6. Only then fog, lighting, actors, sprites and the HUD.

That answers the useful question: how much of AmiWind's rendering this particular card can take over. No figure is
promised before it is measured.

**Use what the machine has (24 October 2026).** One game and one disk for every machine, as with the Fast RAM AmiWind
already puts to use by itself: the world, the assets and the game are shared, and the engine picks its drawing path at
start-up from what it finds.

1. Warp3D, a 3D card and a working driver: the hardware renderer, the card draws.
2. An RTG card without a usable 3D driver: the software renderer in Fast RAM, the finished frame uploaded to the card
   (no chunky-to-planar step).
3. Neither: today's AGA path, the software renderer and chunky-to-planar; the baseline, always there to fall back on.

The game says which path it took and why (the card, the driver and what it offers, or the reason it fell back), never
silently; a driver that fails to open or lacks a needed feature (depth buffer, texture format) drops it to the next
path instead of stopping the game; a setting or start-up option picks a path by hand for tests and for a misbehaving
driver, and the boot countdown offers it too: a key during the countdown opens a small options screen (renderer:
automatic, AGA, RTG or Warp3D), and with no key the countdown runs out on "automatic", so the unattended tests never
stop at a menu; saves and the world do not depend on the path; and each path gets its own boot smoke so none breaks unnoticed.
The engine already finds an RTG screen (`vid_amiga.c` opens `cybergraphics.library` and checks for an RTG mode); the
hardware path adds opening `Warp3D.library` and asking it what the card can do.

**Where to start in the engine (24 October 2026).** The first milestone is a small, real CHIM scene drawn by the card
inside AmiWind, measured before the whole renderer is converted.

1. **Display and renderer chosen separately**, three explicit combinations: AGA with the software renderer (the
   baseline), RTG with the software renderer (compatibility and comparison), RTG with Warp3D (the acceleration).
   `vid_amiga.c` gets the hardware path's screen, colour format, depth buffer and presentation; today it assumes an
   8-bit screen and a software frame. One verified target first (68k, Mediator, Voodoo 3, Warp3D); the game logs the
   driver and the capabilities it got, and a software fallback says so plainly.
2. **The branch before the software edge pipeline.** `R_RenderView_` (`engine/aga/src/r_main.c`) calls
   `R_EdgeDrawing`, then the entities, particles and the frame effects. The camera and visibility setup that both
   paths need is separated from the software-only buffer and edge bookkeeping, and the scene goes to one renderer or
   the other. A pointer, not a ready switch: the inherited `r_drawpolys` branch in `r_main.c` notes that depth-buffered
   drawing needs no clipping against the world tree, only against the view; its `D_DrawPoly` (`d_edge.c`) is empty.
3. **A cached CHIM-to-triangle adapter.** The models already carry vertices, edges, surface outlines and texture
   vectors; triangles and texture coordinates are made once when a model becomes resident, freed with it in
   `chim_models.c`'s eviction, and textures uploaded in a format the card takes. First a ground patch and a few opaque
   placed models, with their placements and the useful visibility rejection, without `R_RecursiveClipBPoly`, edge
   emission or span drawing. Classic Warp3D has no vertex buffers or instancing in the modern sense: the CPU still
   transforms and prepares. The card's texture memory gets its own budget; spare Fast RAM is not spare card memory.
4. **The card owns the finished 3D frame**: `screen.c` and the video code stop the software `VID_Update` from drawing
   over it. Simple fixed lighting and a small diagnostic overlay first; then actors, sprites, the HUD, lighting, fog,
   the sky and water, each measured. Fog is rebuilt inside the hardware path (no full-frame readback), and the culling
   that counts on fog hiding things is checked until the fog matches.
5. **Measured before it grows**: the same camera, geometry, resolution and effects on both renderers (what the
   prototype leaves out, its software comparison leaves out too): the CPU's preparation, submission, texture uploads,
   the waits for the card and the screen, and the whole frame; and a check that the software clipping and span code no
   longer touches the scene the card draws.

The first task: an optional Warp3D backend that draws one CHIM ground patch and several shared-model placements with
correct textures, near-plane clipping, hardware depth, presentation and cleanup. Accepted when the scene draws right,
its frame costs are measured, and the software drawing path is shown to be bypassed for it.

**Findings so far (24 October 2026).**

- The poor frame rate seen on an RTG screen does not show that the card is too weak: in that setup the CPU still draws
  the whole scene, and the card only shows the result. It measures the work a hardware path would hand over.
- The architecture to aim for: the AGA mode keeps the software renderer and its chunky-to-planar step; an accelerated
  RTG mode gets a separate drawing backend that shares the world, the assets and the gameplay. The CPU keeps the game,
  collision, CHIM streaming, visibility, animation and whatever transforms the card's interface leaves to it; the card
  draws the textured triangles, tests and writes depth, blends, and does the fog and lighting it supports, into its own
  display buffers.
- Visible CHIM geometry goes to the card before the software polygon splitting, edge and span work, so that work
  disappears instead of only the final pixel writes.
- The first target: a Voodoo card through a Mediator busboard with Warp3D on a 68k Amiga, for which the busboard's
  maker documents 68k as well as PowerPC Warp3D support for the Voodoo 3, 4 and 5 (to verify on the real setup). The
  Radeon cards come later: the maker lists them through Picasso96, and Radeon Warp3D support is documented for
  AmigaOS 4.1, which does not establish a 68k AmigaOS 3 driver.
- Card memory, as the busboard maker lists the boards (the usable amount under the Amiga driver to check): Voodoo 3
  2000/3000/3500 16 MB, Voodoo 4 4500 32 MB, Voodoo 5 5500 64 MB but split 32 MB per chip with the textures held twice
  (so at most 32 MB of texture room, less its buffers and the driver's share, not 64), Radeon 9200/9250 64 to 256 MB by board. 16 MB is a workable first budget: two
  640 by 480 frames and one depth buffer at 16 bits take about 1.76 MiB before alignment and the driver's own share;
  the rest is textures, so CHIM's texture residency decides how much of a scene fits. AmiWind's textures are small
  8-bit ones today; expanded to 16 bits for the card they take twice the room.
- Textures live on the card. Keeping them in the card's memory and letting the card map them is the basic thing these
  cards do: CHIM loads a shared texture, converts it to a format the card takes and uploads it once; it stays resident
  and serves every placement that uses it; the card fetches it, maps it, draws and depth-tests the pixels; textures
  leave the card when CHIM's streaming and the card's memory say so. No texture is uploaded every frame, and CHIM's
  shared texture numbers and residency already give the bookkeeping. The offload is both the texture storage and the
  per-pixel drawing; the CPU keeps preparing the visible geometry and running the game.
- The two budgets stay separate: 2 MB of Chip RAM (the chipset, the sound), 32 MB of Fast RAM (the CHIM world,
  geometry, collision, actors, game logic, the streaming caches and the CPU's share of the drawing) stays the minimum,
  and the card's memory is extra (its frames, depth buffer and resident textures). The game's working set is not
  copied to the card; a hardware path does not make 16 MB of Fast RAM enough again, and it must fit both budgets.
- Whether 16 MB on the card holds the texture working set is a measurement that needs no card: the build knows every
  texture each frame and room uses. The audit: the peak resident textures in the card's format (16 bits, mipmaps if
  used), the frame and depth buffers, the extra Fast RAM for cached triangles and submission data, and the texture
  uploads and evictions as the player moves.
- The slow expansion bus is not the limit it looks like: it carries the geometry, the drawing commands and each texture
  once, while the card's per-pixel work (texture reads, colour and depth writes) stays in the card's own memory. So a
  Zorro or busboard link can still feed worthwhile acceleration, as long as the design keeps textures resident, sends
  triangles in batches, tests depth on the card, and never reads the frame or the depth buffer back as a routine (fog
  and the overlays included). The remaining limits are the CPU's: scene preparation, transforms, visibility, driver
  calls and the transfers themselves.
- What it could be worth, as an engineering estimate (not a measurement): a complete hardware renderer could remove
  roughly half to two thirds of the drawing work in heavy scenes, because some of that work moves to the card and some
  disappears (the clipping of every visible building against the world's tree, done only to order the drawing).
  Roughly twice the speed overall is a credible first target, more where the software drawing dominates; keeping the
  clipping and edge work and accelerating only the final pixels would leave much of today's cost in place. How a cut
  in frame time reads as speed: 40 % less is 1.67 times, 50 % is 2 times, 67 % is about 3 times, 75 % is 4 times. Less
  CPU work per frame can still show the CPU fully busy: it is then making more frames.
- The first proof can be smaller than an outdoor scene: one existing CHIM room's opaque geometry, its textures resident
  on the card, hardware depth testing, measured against the software renderer on the same room.
- The limit: classic Warp3D draws but does not transform, so the CPU's share needs its own budget. The original game's
  500 MHz Pentium III-class requirement is not the yardstick for it: that was for the original's full assets (full
  detail meshes and skinned characters, a long view distance, lighting on everything), while AmiWind draws reduced
  assets made for the Amiga (budgeted models, merged statics, a short fogged view, simpler lighting). The CPU's share
  on AmiWind's own scenes is what the first experiment measures. Still open alongside: which Warp3D versions serve which cards on 68k AmigaOS 3 today,
on which buses and on what terms they are distributed, and the texture memory of the small cards (the Permedia 2 cards
have 8 MB). The AGA 68040 path stays the baseline and the primary target.

### Long-term possibility: Lua scripting

Game logic today runs in QuakeC (the engine's built-in script VM) plus C.
A small Lua interpreter could later carry quest, dialogue and event scripts
(Morrowind's own scripts translated at conversion time) and make AmiWind
moddable without recompiling. To be decided by measurement on the reference
Amiga: the interpreter's code and heap cost against the 11 MiB budget, script
speed on a 68040, and whether it replaces or complements QuakeC.

### From Quake Arena to Vivec Arena: two-Amiga 1v1 duels

Once the battle arena and its test fights work, two Amigas could fight each
other: a 1v1 player-versus-player arena under a new **Extras** entry in the
main menu.

- **Link options.** A null-modem serial cable between the two machines, or
  TCP/IP over a network: an A1200 can take a PCMCIA network card with a
  standard Amiga TCP/IP stack. A TCP/IP stack can also run over the same
  serial cable (SLIP/PPP), so one network layer could serve both; a raw
  serial path (through `serial.device`, or directly through the Amiga's UART)
  remains an option for the lowest latency.
- **Bandwidth is small.** A duel needs two players' positions, view angles and
  action events (attack, block, hit, dodge), sent 10-20 times a second: a few
  hundred bytes per second, well within a 19,200-baud serial link. Quake's own
  network protocol, which the engine source still carries, was designed for
  28.8k modems.
- **Fair results.** Combat follows the arena rules (Morrowind's hit chance,
  shown as dodges and parries). One machine decides each roll and sends the
  result, so both screens agree.
- **The venue.** Morrowind already has the right place: the Arena Pit in
  Vivec's Arena canton. Converted on its own, it makes a small, closed duel
  map: from Quake's arenas to Vivec's.
- **Scope.** Two players, the arena map, no world state. Both machines run the
  same AmiWind version and their own copy of the converted game data; only
  game state crosses the link.

## Older history

Roadmap entries from v0.0.29 and earlier (6 October 2026 and before) are in the
[roadmap history](ROADMAP_HISTORY.md).
