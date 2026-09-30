# Initial NPC placement and ground-contact workflow

Ground residents must stand on the converted walkable surface, including stairs,
bridges, platforms and interior floors. Original placement Z is an input, not
proof of foot contact after geometry conversion.

## Classify the intended initial state first

The question is whether the actor is meant to have ground support at game/scene
initialization. It is not whether they are humanoid, tall, in a particular faction,
or capable of levitation later. The conversion writes original `aw_source_id` and
placed `aw_ref`. The versioned policy in `config/actor_grounding.json` explicitly
lists the ground residents currently converted and the other initial states.
An unclassified source ID stops conversion; it never silently defaults to ground.
Add classification during source/content intake, then automate the geometry work.

`aw_ground_mode=0` means an initially grounded resident. Mode 1 preserves a
documented flying, levitating, swimming, scripted airborne or authored dead state.
Tarhiel's original ID is `agronian guy`; the controller `fallingScript` enables him
in the sky and invokes Fall. Cliff racers and `vivec_god` are explicit airborne
examples. Do not classify all Telvanni as levitating. Keep source evidence and the
reason for every exception; none counts as a passed ground-contact test.

Authored corpses keep their death pose and placement. Their pose/contact checks,
swimming depth, flight clearance and later scripted movement are separate
contracts. A future placement-specific override must use the placed reference,
not change every instance of a source actor to hide one bad placement.

## Main gate: host build, before packaging

1. Finish visible geometry and collision, including stairs, platforms and floors.
   Resolve each resident in its owning sub-cell, with that scene's full support
   geometry. Use the bounded placement pass to propose its initial Z. Preserve
   source reference, authored Z, support reference and any adjustment in evidence.
2. Write the canonical result into every overlap copy. Missing owners, inconsistent
   copies, unknown initial states and excessive or unsupported drops are errors.
   Do not repair a missing platform by snapping its occupant to terrain below.
3. Run the independent `tools/check_actor_ground.py` check on the final BSP and
   MDL files. It decodes actual quantized mesh vertices and samples the low mesh
   contact band across the declared initial idle poses, at the placed rotation.
   It measures support and gaps against packaged point collision. This catches a
   visually floating model even when its origin or collision box touches ground.
4. Stop image creation on every unresolved result. `build_aga.py image` writes the
   private `actor-initial-contact.json` receipt and requires a pass before creating
   the content fingerprint or HDF. The checker never edits placement.
5. Retain content hashes and exact scope/tolerances in that receipt. Re-run after
   geometry, hull, model, pose, scale, placement or classification changes. Validate
   the HDF read-back against the same payload hashes.

Manual invocation against an owned converted payload:

```sh
python3 tools/check_actor_ground.py /path/to/id1/maps --out /path/to/actor-initial-contact.json
```

The current geometric contract permits -0.5 to +1 converted unit at sampled low
mesh vertices; the contact band is the lowest 0.5 unit of each initial idle pose.
This is a finite, stated contract, not a claim of perfect foot IK or every future
animation. New stance/pose layouts must be declared. Semantic sole markers, swept
body clearance and moving-support attachment should extend this gate when those
features enter the runtime, rather than silently broadening its acceptance.

All mesh decoding, multi-point traces and reporting run on the build host. The
Amiga receives the final placement. There is no continuous multi-point grounding
scan and no need to keep the build reports or a second collision world in RAM.

## Runtime correction

Once architectural brushes are linked, a ground NPC tests its feet point from
8 units above the source position to 32 below. Accept only a non-solid starting
point and walkable support. Keep a quarter-unit clearance. Apply the same check
after restored NPC positions are loaded. A missing, steep, blocked or excessively
distant floor keeps the original position for diagnosis. This limit is a safety
bound, not evidence that the unresolved position is acceptable.

Balmora's distant render overlap contains some architecture with collision
intentionally removed. Conversion therefore measures each resident against its
owning sub-cell and writes that same resolved origin to all overlap copies,
retaining `aw_authored_z`. The same owning-core rule applies to Seyda Neen's
regular subdivisions. Runtime correction and ground acceptance for these towns
are restricted to that owning core. An audit row outside it says
`deferred-owner-core`, never `grounded`: visit the owner core and collect its
actual result. This prevents an overlap copy from being dropped through a visual
platform whose physical hull belongs to the neighbour. Interior scenes retain
their complete collision and are measured directly.

## Native integration checks

1. Use a fresh character and visit every converted map and relevant sub-cell.
   Let at least two simulation frames run after loading.
2. Run `dbg npcfloors`. It appends a read-only `npc-ground.tsv` report from live
   entities. Columns are map, placed reference, source ID, display name, status,
   X, Y, lowest model Z, support Z, and gap, in converted units.
3. Investigate every `floating`, `embedded`, `unsupported`, `blocked` or `steep`
   result. The default accepted foot gap is -0.5 through 1 unit, accommodating
   quantized model bounds, idle poses and the intentional clearance. `exempt`
   means a documented authored exception, not a pass.
4. Leave and return across sub-cell boundaries and doors; repeat the audit.
   Quicksave/quickload and repeat. A good initial spawn alone does not pass.
5. Inspect feet visually for every reported defect and representative races,
   footwear, slopes and platforms. Test the full idle cycle where feet move.
   Bounding-box contact alone cannot certify both feet on an uneven surface.
6. Keep the report and native captures in private release evidence. Summarize
   checked maps, remaining exceptions and owner acceptance in public notes.

The audit never moves actors. Automatic correction and independent measurement
are separate steps. Do not hide a failure by removing the NPC from the report or
marking it airborne without source evidence.

The guarantee is that every packaged, classified initial ground placement passes
the declared checks, or the build fails. It does not certify unknown scripts,
arbitrary later movement or future animation. Initialization, save restoration
and sub-cell copying must preserve the accepted placement; runtime movement
systems need their own support rules when implemented.

## Diagnostic RC2 exception

The owner requested an interim RC2 while placement and model-budget investigations
remain open. Its separate snapshot package retains the failed audit, exact payload
hashes and all 23 unresolved contacts. This is a diagnostic distribution exception,
not a successful placement gate. The normal `build_aga.py image` gate remains
unchanged and rejects this payload until those findings are resolved. The stated
all-placements guarantee applies to a passed production build, not this snapshot.
