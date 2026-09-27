# Seyda Neen implementation journal

27 September 2026. Area-specific findings and proposed tradeoffs; general
symptom/cause/fix records remain in [IMPLEMENTATION_JOURNAL.md](../IMPLEMENTATION_JOURNAL.md).

## Arrival ship: geometry, departure and where detail matters

### What the owned source data establishes

The exterior hull is an ACTI placement, with separate hatch, cabin-door and
gangplank placements. The hull's visible geometry contains **5908 triangles**.
It also contains an authored RootCollisionNode with **581 triangles**; these
hidden collision shapes must not become visible scenery. Visual and physical
representations should be converted separately.

There is an **Imperial Prison Ship** interior CELL, separate from the exterior
hull. The character-generation class NPC is placed in **Seyda Neen, Census and
Excise Office**. Its initial script state disables the boat, gangplank, doors,
related actors and other opening objects. This is scripted removal during the
Census-office part of character creation, not removal merely from stepping off
the boat, and not a script that animates a ship sailing away.

Evidence: private owned-master ship/reference/script audit and interior CELL
lookup. Do not copy the original script, dialogue or model data into public
documentation. The previous floating hatch was a conversion omission: its hull
type and location were excluded. It did not prove that departure logic ran.

### Conversion experiments for checkpoint-015

| Candidate | Visible ship output | Collision source / result |
| --- | --- | --- |
| Full-detail exterior, 64-pixel material textures | 5908 input triangles became 9976 BSP surfaces after merging and UV-bound splitting | Visual mesh generated 217 approximate convex pieces |
| Selected exterior LOD, 32-pixel material textures | 1954 reduced triangles became 3931 BSP surfaces | Original authored collision mesh generated 60 approximate convex pieces |

These are host conversion counts, not FPS measurements. A source triangle and
a runtime surface are different units; repeated textures can require splitting
a large face for the surface cache. The LOD keeps material/component membership
and projects UVs from the source approximately. It is not a new high-to-low
detail texture bake. Native dock/deck/gangplank and console/hands acceptance passed with a 9 MiB
heap on the unchanged 16 MiB Fast emulator profile; the 8 MiB trial failed cache
allocation. This does not certify the entire ship route. See
[checkpoint-015](../CHECKPOINT_015_VALIDATION.md) for counts, hashes and limits.

The ship assembly currently represents a **static arrival preview**. The full
opening scripts and the post-registration removal transition are not implemented.

### Can the opening look better without loading the whole town?

Yes, as a planned residency design: load the ship interior as its own scene,
with its local actors, interaction objects and a measured detail budget. On the
linked exit, replace it with the arrival exterior and its simplified ship hull.
On entering the Census office, load that separate interior. After the authored
opening-state transition, subsequent town loads omit the disabled ship assembly.
Retain compact quest/reference state and music across these scene changes.

This follows the source's separate spaces and removal behavior. Keeping the ship
permanently after character creation would be a deliberate deviation, not a
necessary optimization. A decorative low-detail ship should not remain merely
because we forgot the source disable state. A visible sailing animation would
also be a new presentation feature, not required source behavior.

The limited opening route can justify smaller resident/visible sets, but it
cannot excuse geometry popping into view on ordinary camera turns. If the deck
sees the shore, load the visible shore dependencies or a tested distant proxy.
Preserve door destinations and interaction reach; do not replace reachable
surfaces with non-colliding pictures. Keep noclip inspection separate from the
normal authored route when judging what must be visible.

### Detail priorities and future experiments

- First make the below-deck opening navigable and recognizable; then link its
  exit, gangplank route and Census-office entry. Test the actual loading handoffs.
- Keep exterior silhouette, cabin, deck, mast placement and gangplank. Flatten
  small mouldings and investigate baking fine detail into low-resolution textures.
- Use a separate interior budget instead of assuming that improving it raises
  exterior render cost. Measure both scenes and peak memory during transitions.
- Implement disabled state consistently across rendering, collision, activation
  and residency. Merely hiding pixels does not release the ship's allocations.
- Compare arrival and post-registration dock routes with the same machine/fog
  settings. Record memory, surface peaks, frame time, cache reloads and audio
  deadlines; do not invent a saving from source polygon count alone.

The next broader milestone remains the connected starting area in
[SEYDA_NEEN_SCOPE.md](../SEYDA_NEEN_SCOPE.md). Opening interiors begin with the
prison ship, followed by the Census office as the first town interior.

## Low light as an early rendering test

The opening ship should be an early dim-interior test, not merely a geometry
conversion milestone. Compare dark walls, NPC silhouettes, stairs/hatch edges,
doorways and nearby light sources at the actual output resolution and palette.
Check black crush, banding, fog interaction, readable controls and light falloff.
Keep UI brightness separate from world lighting. Profile stationary and moving
views and any moving-light experiment alongside uninterrupted music/voice.

The current exterior uses a simplified lighting path and is not proof of an
interior lighting solution. Evaluate baked lighting and indexed shading tables
before expensive per-frame alternatives; record their memory and visual limits.
Do not interpret simply darkening the complete image as faithful local lighting.

Day/night is a later world-system milestone: preserve game time and transition
exterior sky, fog and ambient illumination coherently. Interiors require their
own lighting treatment. Waiting, save/load and time-dependent rules must use
that same time state once supported. This is currently roadmap work.
Dawn/day/evening/dusk/night presets, exact-hour overrides, freeze controls and
a locally converted night-sky backdrop are specified in the
[day/night and sky plan](../DAY_NIGHT_AND_SKY.md). Aim for a coherent impression
through inexpensive shading/fog/sky changes, not global illumination.

## Re-entry and debug travel follow-up

The base-master audit on 27 September, 22:32 Helsinki confirms the Census class
NPC's initial script state disables the exterior boat and trapdoor. Ordinary
re-entry is therefore no longer available once that sequence runs. The separate
interior CELL still exists; debug scene travel must remain available regardless
of eventual story-state gates. Current AmiWind does not execute that opening
script and deliberately keeps both preview links accessible.

The current contents tint is inherited from Quake: water uses RGB (130,80,50)
at strength 128, separately from CSHIFT_DAMAGE. That warm brown tint is a
plausible cause of the owner's red-on-immersion report, not confirmed drowning.
Requested blueish water tint and damage-specific red/hurt audio remain TODO.
