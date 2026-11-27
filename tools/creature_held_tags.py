# SPDX-License-Identifier: GPL-3.0-only
"""The item tags of the armed creatures: the bones their weapon and shield hang on (CREATURE-COMBAT-WEAPON-54).

A creature whose record has the "weapon and shield" flag fights with the weapon and wears the shield its inventory
gives, as a person does, and the original draws them in its hands (rule from OpenMW
apps/openmw/mwrender/creatureanimation.cpp, CreatureWeaponAnimation: the items of the creature's inventory on its
weapon and shield bones; read, not copied). The engine draws an actor's held items on the two bones its model's tag
names (engine/aga/src/aw_items.c); which items is the actor's own record's (the actor table, tools/mwscript/actors.py:
ACTOR-HELD-ITEMS-NOT-LIVE-INVENTORY-69). People have a tag; no creature model had one, so no creature held anything.

One creature model serves every record of its mesh, and those records carry different weapons (the skeleton's mesh:
23 records, 12 weapons), so the tag written here names NO item: only the frames, the two bones and the model's scale.

Written beside the creature bake, outside its units, as the NPC library writes the people's tags
(tools/npc_library.py library_items): no model and no table is baked again for it. A creature on the shared humanoid
table has that table's bones, the weapon and shield bones among them (tools/creature_tables.py appended_table). A
creature on a table of its own keeps only the bones its animation moves, which leaves the two item bones out: it gets
no tag here and is listed (CREATURE-OWN-TABLE-NO-ITEM-BONES-69).
"""
from pathlib import Path

WEAPON_AND_SHIELD = 4           # CREA FLAG: fights with the weapon and shield of its inventory
MODEL_SCALE = (0.25, 0.25, 0.25)    # a creature model's scale (tools/creature_tables.py: Morrowind to engine units)


def flagged_meshes(planned, meshes):
    """{mesh: [record ids with the weapon and shield flag]} of MESHES ({mesh: [ids]}), by the plan's bases."""
    out = {}
    for mesh, ids in sorted(meshes.items()):
        armed = [i for i in ids if planned['bases'][i]['flags'] & WEAPON_AND_SHIELD]
        if armed:
            out[mesh] = armed
    return out


def tag_text(frames, bone_names):
    """The tag of a creature model of FRAMES table frames on a table whose bones are BONE_NAMES: no item, the weapon
    and shield bones, the creature model's scale."""
    import skeletal_actor
    return skeletal_actor.skeletal_tag(frames, {}, bone_names, MODEL_SCALE)


def write(data, planned, meshes, models, out_id1, humanoid_bones=None):
    """Write <model>.tag beside the skeletal model of every mesh of MESHES that a flagged record uses and whose table
    is appended to the shared humanoid table. MODELS: the creature library's records ({mesh: record}); HUMANOID_BONES:
    the shared table's bone names (None: read from the game data when the first tag needs them). Returns
    ({mesh: {'tag', 'frames', 'bones', 'records'}}, {mesh: why it has none})."""
    import actor_frames
    import creature_tables
    out_id1 = Path(out_id1)
    written, left = {}, {}
    for mesh, armed in flagged_meshes(planned, meshes).items():
        record = models.get(mesh)
        if not record:
            left[mesh] = 'no model in the library'
            continue
        if record.get('method') != 'skeletal' or not record.get('table'):
            left[mesh] = 'not a skeletal model (%s)' % record.get('method')
            continue
        model = out_id1 / record['model']
        try:
            creature_tables.from_appended((out_id1 / record['table']).read_bytes())
        except ValueError:
            left[mesh] = 'a table of its own: the weapon and shield bones are not in it'
            continue
        frames = actor_frames.skeletal_frames(model.read_bytes())
        if not frames:
            left[mesh] = 'its model names no table frames'
            continue
        if humanoid_bones is None:
            import creature_library
            humanoid_bones = creature_tables.humanoid_table(creature_library.layered_assets(data))[1]['bone_names']
        missing = [b for b in ('weapon bone', 'shield bone') if b not in humanoid_bones]
        if missing:
            raise ValueError('The shared humanoid table has no %s' % ' and no '.join(missing))
        text = tag_text(frames, humanoid_bones)
        model.with_suffix('.tag').write_text(text, encoding='ascii', newline='\n')
        written[mesh] = {'tag': record['model'][:-4] + '.tag', 'frames': frames,
                         'bones': [humanoid_bones.index('weapon bone'), humanoid_bones.index('shield bone')],
                         'records': armed}
    return written, left
