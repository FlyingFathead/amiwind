# Mutable character equipment and shared assets

Fixed, complete outfits are an interim conversion representation, not the final
character architecture. A complete game must support taking clothing and armour
from a dead NPC, equipping and removing items, and restoring the resulting
appearance after scene changes and save/load. Producing every possible complete
outfit in advance is not a viable way to implement those requirements.

## Current boundary

The host resolver in `src/mwad/npc.py` reads NPC_, RACE, BODY, CLOT, ARMO and
inventory records into one deterministic appearance. The gallery provides
equipped and base-body inspection views. These are not a runtime inventory or
equipment system: switching between those two views cannot represent arbitrary
partial looting. rc10's cache reuses those existing complete models; it neither
implements equipment changes nor makes a fixed outfit the permanent format.

Pre-conversion itself remains useful. Shared meshes, skins, poses and attachment
data can be converted once into Amiga-ready assets. The important distinction is
retaining their identities and composition rules instead of baking away every
relationship into a permanently clothed actor.

## Required data and runtime behavior

- Preserve source IDs for body parts and equipment, skeleton attachments,
  race/sex variants and source-derived slot coverage/layering. The existing
  bounded host resolver is a starting point, not proof that every original
  equipment rule is already implemented correctly.
- Keep inventory/equipped state per placed actor, distinct from shared appearance
  assets. Removing one guard's shirt must not alter every guard using the same
  cached model. Death and pose are separate from equipment and visibility.
- Resolve newly exposed body parts when an item is removed, including clothing
  layers and hair previously covered by a helmet. Preserve the corpse's pose;
  changing equipment must not stand it up or reset its position or script state.
- Persist the changed inventory and equipment through streaming and save/load.
  Re-entering a cell must not regenerate an NPC's initial outfit or duplicate
  looted items. An equipment change must invalidate the affected appearance.
- Keep every required component available to the engine. On-demand loading is
  appropriate; keeping every model in RAM at once is unnecessary. Model sharing
  must never become a reason to omit an NPC, component or gallery entry.

## Implementation experiments, in order

1. Export a source-derived part/equipment catalogue and dependency table alongside
   current models. Measure repeated host work before changing conversion quality.
2. Cache compatible component conversion with full pose, scale, palette, material
   and simplification dependencies. Current per-part quotas depend on the whole
   outfit, so caching by NIF filename alone can change the result incorrectly.
3. Prototype load/equipment-change composition for one humanoid and one supported
   death pose. Compare a bounded assembled-model cache against separate attached
   part drawing. The existing alias renderer cannot acquire modular equipment
   merely by adding a lookup table: attachment, animation, skin handling and
   combined model limits need actual implementation and tests.
4. Measure load/change latency, peak RAM, skin storage, frame time and polygon
   limits on the target. Similar triangle counts do not guarantee similar frame
   cost: separate parts can repeat culling, transforms, lighting and draw setup.
   Prefer work on load/equipment changes where practical; do not assemble the
   whole outfit anew every frame. Bound and evict temporary assembled appearances
   independently of the complete on-disk asset catalogue.
5. Expand to all supported bodies, equipment layers and animation states only
   after the prototype passes. Keep the existing appearance path as a comparison
   while bringing up the replacement. Do not pre-bake a combinatorial outfit set.

## Acceptance cases

Remove only boots, only a shirt, armour over clothing, a robe, and a helmet;
verify the correct remaining layers and uncovered body/hair. Test partial and
complete corpse looting, equipping a different item, two actors sharing an initial
appearance, race/sex and beast-body variants, scene unload/reload and save/load.
Check item counts, corpse pose, appearance, contact and memory limits together.
The gallery must exercise these transitions through the same resolver as the
game when implemented, retaining its current complete coverage in the meantime.

This is a required gameplay roadmap, not an rc10 implementation claim. See
[character state](CHARACTER_STATES.md), [model cache](NPC_MODEL_CACHE.md) and
[gallery requirements](CHARACTER_MODEL_GALLERY.md).
