# Cell-change continuity checklist - a growing list

A streaming boundary changes the resident map, not the player's ongoing game.
Seyda Neen and Balmora subdivisions are required to bound frame cost; preserving
continuity must not require loading the entire world at once.

## How this list grows

This is a living checklist, not a closed definition of gameplay state. Every
new system, stat, equipment mode, NPC behaviour or transient effect must add
its cell/sub-cell transition policy here and receive a regression or explicit
playtest case. Record what is preserved, rebased, expired or deliberately reset.
Do not mark a requirement complete merely because it is documented.

## Current evidence and remaining acceptance

| State | Current evidence | Remaining acceptance |
| --- | --- | --- |
| Held controls, Shift/Ctrl | Rc3 automatic loads no longer clear buttons; real scene harness checks no clear call | Held/released-during-load controls and focus-loss playtest |
| Noclip, position, view, velocity | Real transition harness passes both variants | Cross town/world and subdivision boundaries both directions |
| Health, hands raised, lit torch | Existing capture/restore verified by real transition harness | Raised/lowered hands and lit/unlit torch playtest |
| Magicka/fatigue values, level, inventory state | Harness retains character values and inventory state through spawn | Full character HUD/equipment review; no claim of all stat fields tested |
| Shared terrain and materials | Coverage and shared-world triangulation regressions pass; town compiled | Seyda Neen boundary playtest on the new image |
| Weapons, active effects, pursuit/combat | Transition requirements recorded | Implement and test when the corresponding gameplay systems exist |

## Required continuity

- Preserve world position, view direction, movement mode and velocity through
  coordinate rebasing. Noclip must remain enabled when it was enabled before.
- Preserve physically held movement keys and Ctrl/Shift speed modifiers across
  automatic transitions. Releases during loading must be honoured; focus loss
  must clear input to avoid stuck keys. Teleports and menus require explicit
  policies rather than blindly replaying all buttons or one-shot actions.
- Preserve stable NPC identity, health, death state, position, dialogue and
  interaction state. When pursuit/combat is implemented, preserve its target,
  aggression, active pursuit and relevant timers across residency changes.
  An NPC must not stop chasing solely because a map boundary was crossed.
  This is a requirement, not a claim that NPC pursuit/combat is implemented.
- Preserve character identity and stats: current/max health, magicka, fatigue,
  attributes, skills, active effects and relevant timers. Never reset them to
  spawn defaults merely because a different BSP became resident.
- Preserve quest/journal progress, inventory and equipment. Track equipped
  items separately from drawn state: sheathed weapon, drawn weapon, raised bare
  hands, lowered hands, carried torch and whether its flame is lit. Preserve
  the applicable weapon/torch state, attack mode and unfinished draw/holster
  transitions according to an explicit policy; avoid restoring incompatible
  combinations. The current scene loader explicitly carries health, hand goal
  and torch goal; that alone does not verify all character-state categories.
  Define which transient animations and effects
  resume, expire or restart, and prevent duplicate events on re-entry.
- Keep shared ground heights, shoreline geometry and texture placement aligned
  throughout visible overlap, with sufficient ground beyond every handoff.

## Rc2 reports and rc3 correction status

The owner reported Ctrl/Shift flight-speed modifiers resetting while held
across cell/sub-cell changes during noclip. Rc2 cleared all held buttons when
scheduling a map load, including automatic region crossings. Rc3 retains
held buttons on automatic region crossings while retaining
clearing at doors, teleports and focus loss. The real transition harness passes
in both test variants, including noclip, health, magicka/fatigue, level, inventory,
hands and torch restoration.
Owner held-Shift/Ctrl and focus/release playtesting remains pending; for rc2 the
temporary workaround: release and press the modifier again after the load. Do not treat
retained noclip mode or velocity alone as proof of complete input continuity.

The owner also reported Seyda Neen's landscape changing sharply at its town
boundary. The old ground ended only 64 units beyond the eastern exit against
540 units of draw distance. A surrounding-ground apron and shared world terrain
sampling are being rebuilt and require a separate owner boundary playtest.

The owner accepted the rc2 giant-mushroom cap correction. That acceptance does
not cover these transition defects. See [bug journal](BUG_JOURNAL.md).

## Visible overlap and terrain handoff policy

A core chooses which BSP owns the player. Coverage is the larger area that BSP
can render and collide with. Hysteresis keeps ownership from bouncing back and
forth near a boundary. These are different bounds: extending a core alone does
not create ground, and declaring overlap does not prove that geometry exists.

- Coverage records must enclose their cores and match the generated resident
  payload. Check the runtime directory format before packaging. Empty or clipped
  boundary strips must not be presented as verified visible landscape.
- At every reachable exit, retain real ground through the whole view range,
  including diagonal views, hysteresis and transition margin. Check the actual
  terrain footprint, not the sea backdrop or sky enclosure. Derive and test the
  required margin when draw distance or loading policy changes.
- Shared LAND must use the same source coordinates, world scale, height samples,
  coarse grid alignment, triangle/winding policy and shoreline refinements on
  both sides. Local origins may differ; rebasing must preserve global position.
- Ground materials, texture sources, UV placement, palette and lighting/fog
  policy must agree in shared coverage. Do not call a height-only comparison a
  complete visual-continuity test.
- Preserve complete intersecting rocks, mushroom parts, buildings and relevant
  collision through the overlap. Select by transformed bounds, not just an
  object's centre. Distinguish remaining scenery differences from ground gaps.
- Keep bounded residency and the town's FPS subdivisions. An overlap fix must
  stay within face, vertex, clipnode, memory and loading budgets; joining every
  cell into one resident map defeats the subdivision policy.

### Seyda Neen: town-to-world and internal town subdivisions

The rc2 owner screenshots near the eastern town exit show a missing landscape
followed by a sudden hillside after a few steps. The town remained resident to
local X=1600 while its ground stopped at X=1664: only 64 units ahead against a
540-unit draw distance. A sea/sky backdrop could not supply the missing LAND.

The candidate correction adds a 768-unit real-ground apron, uses the streamed
world sampler/triangulation/material choice outside the detailed port approach,
and extends subdivision coverage without moving town ownership cores. The sky
enclosure also follows measured surrounding hill height. The detailed Silt
Strider approach retains fine ground samples. Outer coverage records must still
enclose all subdivision cores, including the legacy outer edge strips.

Test town-to-world and world-to-town crossings at the reported eastern exit,
then other exits and diagonal views. Test internal town subdivisions and the
north bridge separately: an internal region change and leaving the town are
separate transitions. Confirm rocks, ground materials, collision, player height
and performance together. The corrected rc3 owner playtest remains pending.

### Balmora: FPS subdivisions and surrounding-world boundary

Balmora's configured profile uses a 768-unit core target, 896-unit overlap,
96-unit hysteresis and 540-unit draw distance. Keep its measured subdivisions
and detailed town payload. Audit each core edge and outer town handoff against
actual generated LAND and collision coverage, including bridges and riverbanks.
Do not assume configured overlap survives clamping at the town's outer bounds.

Use the same world-transform and material agreement checks as Seyda Neen, while
respecting Balmora's authored terrain-material repairs and its own geometry.
Recheck doors, NPC placement and character state across its internal regions.
The Seyda Neen correction is not evidence that Balmora's outer handoff has
passed the same audit or playtest; track that acceptance separately.

## Regression and playtest checklist

Cross the same boundary in both directions while holding movement and each
speed modifier, then release during loading and after loading. Repeat with
focus loss, noclip and ordinary walking. Verify world position and camera
orientation, and that no held key becomes stuck. Compare the landscape from
both sides without moving the view. Repeat while wounded or fatigued, with raised/lowered hands, an equipped but
sheathed weapon, a drawn weapon when supported, and a lit/unlit torch. Check
that stats, equipment and draw state survive each transition. Check persistent
NPC state after leaving
and returning; add pursuit/combat cases when those systems exist.

## Heap clearance: rc3 Seyda Neen incident

The rc3 real-ground apron fixed missing terrain at the town/world edge but
enlarged the central subdivision visibility table from 473407 to 2767103 bytes.
The loader held a temporary input table and allocated a second resident copy
inside the 11-MiB heap. A Hors restart from Jiub name entry exhausted the heap
loading sn012. Held-input/state preservation does not add BSP data and is not
the cause indicated by this failure. See CRASH-01 in [the bug journal](BUG_JOURNAL.md).

Byte-only sections now load into their final allocation. The host regression
and Amiga compile pass; total clearance and target playtesting remain separate
gates. Build checks must account for expanded target-ABI structures, each
loading-stage temporary allocation and reserved non-BSP headroom, before image
assembly. Report the failing map, stage, peak, reserve and budget. Changing
overlap requires measured clearance and both-direction seam playtesting; keep
FPS cores and visible coverage requirements distinct.

### Imperative: LEAVE HEADROOM

**Always leave headroom.** Do not accept a region because its allocations only
just fit. Reserve non-BSP engine/gameplay storage separately from an additional
positive safety margin for loading uncertainty and future state. A zero-margin
configuration is not release validation. Report the heap budget, target-ABI
resident bytes, worst temporary peak, non-BSP reserve, required safety headroom
and remaining clearance. The tool must fail before image assembly when either
the peak or reserved headroom cannot fit. Document the assumptions and refresh
the accounting whenever allocator structures, caches or gameplay systems change.

The default budget is the actual engine reservation (currently 11534336 bytes),
not the emulator total Fast RAM. The runtime, compiled ABI and checker must
agree; increasing RAM or lowering a reserve must never silently turn a failed
reference-target build into a pass. A passing estimate still needs a target
playtest; a failing estimate must not be overridden by a successful lucky load.

See [Memory allocation and heap clearance](MEMORY_ALLOCATION.md) for the
allocation model, rc3 incident, mandatory reserves, build audit and transition
reports. Keep both guides synchronized when changing residency or the loader.

## Complete lifecycle watcher and over-budget regions

See [the heap watcher](HEAP_WATCHER.md) for build-stage estimates and event-driven
runtime profiling across unload, BSP load, actor/player restoration and first
presentation, including cache, zone and external Fast/Chip memory. See
[the map memory profile](MAP_MEMORY_PROFILE.md) for the 28 over-headroom regions,
shortfalls and dominant allocations. Mark failures explicitly and prioritize
reduction/subdivision, preserving complete coverage and state continuity. A
smaller core that still retains an oversized parent tree/PVS is not a fix.
Every replacement must pass the same headroom gate and target crossing tests.


## Boundary placement is a measured choice, not an FPS guarantee

Owner clarification, 3 October 2026: the suggested off-centre cut near sn017 is illustrative, not a required coordinate. Candidates may move boundaries or use nonuniform subdivision where actual payload measurements support it. Record the layout and map identity: sn017 in the original 25-region directory is not the same region as sn017 in the adaptive 64-region proposal.

Evaluate both sides of every changed boundary. Preserve the coverage apron, collision continuity and gameplay state; avoid merely transferring a failure to the neighbour. Density heatmap bins guide investigation but do not predict resident visibility, collision or loader allocation costs.

Acceptance has two independent axes: (1) loading-cycle peak and useful growth headroom under unchanged reserves, and (2) measured gameplay frame time plus crossing stalls and frequency. Subdivision can reduce payload but increase reloads, repeated shared-data preparation or clipping work. It must not be advertised as a performance improvement without matched target tests. Include requested and effective view distance, fixed position/view and settings; measure steady gameplay and both-direction crossings separately. The Balmora longer-view observation remains a hypothesis to test, not proof of its cause.

## Automatic region-crossing presentation delay

The archived aw_region_loading_delay setting controls a presentation delay for
automatic region crossings only. The default is two seconds; zero shows the
loading screen immediately. Startup and explicit travel remain immediate.
Begin the delay at a safe loading-screen checkpoint after blocking reads; never
interrupt or time out a blocking read to satisfy the delay. This changes screen
presentation timing, not loader throughput, map residency or frame performance.
Nine source checks pass and the rc5 candidate was packaged/read back; target
crossing timing and owner playtesting remain pending.
