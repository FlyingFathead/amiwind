# SPDX-License-Identifier: GPL-3.0-only
"""The werewolf's look as player parts (WEREWOLF-BODY-63; docs/THIRD_PERSON.md "The werewolf").

How the original draws a werewolf (OpenMW 0.51, read for the logic only, nothing copied):
- apps/openmw/mwrender/npcanimation.cpp updateNpcBase (469-526): the skeleton is the werewolf's own model
  (getActorSkeleton with isWerewolf, apps/openmw/mwrender/actorutil.cpp: the [Models] settings wolfskin and
  wolfskin1st, meshes/wolf/skin.nif and meshes/wolf/skin.1st.nif in files/settings-default.cfg, the animated x... file
  beside it), its animation the werewolf's own keyframes only (no base_anim source), the head WerewolfHead and the hair
  WerewolfHair instead of the race's (476-477);
- getBodyParts (1160-1195): the race "werewolf" has no skin parts at all, so the body is what is worn;
- apps/openmw/mwmechanics/mechanicsmanagerimp.cpp setWerewolf (1880-1908): everything unequipped, the werewolf robe
  (CLOT werewolfrobe: its one part the chest's WerewolfSkin) added and equipped; apps/openmw/mwworld/class.cpp
  (291-294) keeps it out of the inventory and of taking;
- addPartGroup (865-910): in first person a part's '.1st' record (WerewolfSkin.1st);
- components/sceneutil/attach.cpp CopyRigVisitor (23-84, 115-143): a skinned part file gives only its skinned shapes
  whose name (less 'Tri ') starts with the slot's bone name, 'Chest'; a rigid file (the head) is attached whole;
- apps/openmw/mwrender/animation.cpp getModelInstance (1498-1524): the skeleton file's own shapes are not drawn.

So in the original a werewolf is the robe's skin (wolf/skin.nif: its ten 'Tri Chest' shapes, 2,998 triangles) and
the head part whole (wolf/head.nif: a 1,248-triangle head and two 4-triangle eyes), on the werewolf's skeleton; in
first person the skin's first-person file's two 'Tri Chest' shapes (2,562 triangles). The skin file carries a head
of its own as well (four rigid 'Tri B_N_Werewolf_Head' shapes, 660 triangles, the same head at a lower detail: its box
is the head part's own in the head node's frame), which the original does not draw.

The head (HEAD_FROM): 'skin' (W1, the default, decided for the project on 21 November 2026 with the werewolf's budget
sheet): the skin's chest shapes, the skin's own head and the head part's shapes other than its head (the eyes), 3,666
triangles; 'part' (W2, the original's shapes): the skin's chest shapes and the head part whole, 4,254. The empty hair
part (wolf/hair.nif: no shape) is skipped, as the original draws nothing for it.

Each view is ONE skeletal model (progs/parts/<12 hex>.mdl, prepare_player_parts.part_path on the werewolf's skeleton)
reduced by the shared-vertex route (needed_model, the seam work's reducer 'needed': the fewest faces from today's count
up at which the model as the engine draws it passes the outer-hull check by its own bones; tools/outer_reduce.py,
tools/outer_hull.py), on a table of its own:
  progs/werewolf.awsk       the werewolf's own keyframes (wolf/xskin.kf on the bones they move; creature_tables.table:
                            every group of the file, none chosen away)
  view/parts_wm.txt         the player's groups on that table's frames (the player body's profile,
                            prepare_player_parts.player_profile), the same file for both sexes
  progs/werewolf_1st.awsk   the first person's table in the first-person contract (prepare_player_fp_parts.fp_table:
                            28 frames a stance, the engine's stance order, the root carrying the view), every stance on
                            the werewolf's hand-to-hand frames: wolf/xskin.1st.kf has no weapon, light or spell group (a
                            werewolf fights with its claws only)
The recipes name them as the pseudo-race 'werewolf' on the skeleton letter 'w', both sexes, no head, hair or item
(prepare_player_parts.recipe_text, prepare_player_fp_parts.recipe_text). Each model is a unit of the player-parts or
player-fp-parts unit cache, its key carrying the code that bakes it (unit_code).
"""
import hashlib
import io
from pathlib import Path

ROBE = 'werewolfrobe'             # the original's robe record (mechanicsmanagerimp.cpp setWerewolf)
HEAD_PART = 'werewolfhead'        # npcanimation.cpp updateNpcBase: the werewolf's head and hair records
HAIR_PART = 'werewolfhair'
RACE = 'werewolf'                 # npcanimation.cpp updateParts: the werewolf's race id (no skin parts)
LETTER = 'w'                      # the recipes' skeleton letter (engine aw_player_parts.h)
SKELETON = 'meshes/wolf/skin.nif'          # the werewolf's skeleton in the original's settings (wolfskin)
SKELETON_1ST = 'meshes/wolf/skin.1st.nif'  # and in first person (wolfskin1st)
TABLE = 'progs/werewolf.awsk'
TABLE_1ST = 'progs/werewolf_1st.awsk'
LAYOUT = 'view/parts_wm.txt'
SLOT = 3                          # the robe's part: the chest (CLOT werewolfrobe INDX 3)
FP_SLOT = 6                       # the first-person recipe's arm slot the werewolf's arms are named in
FILTER = 'chest'                  # the chest slot's bone name: the skinned part file's shape filter (attach.cpp)
HEAD_FROM = 'skin'                # 'skin' (W1, the default) or 'part' (W2, the original's shapes)
HEAD_FROMS = ('skin', 'part')
REDUCER = 'needed'                # skeletal_actor.skeletal_from_shapes: the shared-vertex route at its least passing count
FP_CAP = 160                      # prepare_player_fp_parts.FP_CAP of the chest: the first person's count to start from

_assets = {}


# ---------------------------------------------------------------- the records

def werewolf_set(kinds):
    """The werewolf's records in the selected masters, or None when they lack the robe (the base game alone):
    {'robe', 'skin': (body id, mesh), 'skin_1st': (id, mesh) or None, 'head': (id, mesh) or None, 'hair': (id, mesh)
    or None}; ids case-folded as kinds holds them, meshes as the records name them."""
    from mwad.npc import string, text
    robe = kinds.get('CLOT', {}).get(ROBE)
    if robe is None:
        return None
    slot, body = None, None
    for tag, data in robe:
        if tag == 'INDX':
            slot = data[0] if len(data) == 1 else None
        elif tag == 'BNAM' and slot == SLOT and string(data):
            body = string(data).casefold()
            break
    bodies = kinds.get('BODY', {})

    def part(ident):
        record = bodies.get(ident) if ident else None
        mesh = text(record, 'MODL') if record is not None else ''
        return (ident, mesh) if mesh else None
    skin = part(body)
    if skin is None:
        return None
    return {'robe': ROBE, 'skin': skin, 'skin_1st': part(body + '.1st'), 'head': part(HEAD_PART),
            'hair': part(HAIR_PART)}


def robe_row(items, ww):
    """The werewolf robe's row of ITEMS (prepare_player_parts.item_rows), marked as worn on the werewolf's skeleton only
    (the original equips it only on a werewolf, setWerewolf): its parts are not baked on the humanoid or beast skeleton
    (the skin is posed by its tail bones, which the humanoid has not; nobody wears it there), and the parts coverage
    counts them on the werewolf's. Returns the row or None."""
    if not ww:
        return None
    for item in items:
        if item['id'] == ww['robe']:
            item['worn_on'] = (SKELETON, LETTER)
            return item
    return None


def race_rows(ww):
    """The recipe's werewolf rows (prepare_player_parts.recipe_text's race rows), both sexes: the werewolf's skeleton
    at the unit scale, its skin in the robe's slot, no head or hair."""
    if not ww:
        return []
    return [{'race': RACE, 'female': female, 'skeleton': SKELETON, 'letter': LETTER, 'weight': 1.0, 'height': 1.0,
             'skin': {SLOT: ww['skin'][0]}, 'heads': [], 'hairs': []} for female in (False, True)]


# ---------------------------------------------------------------- the shapes

def assets_of(data):
    """The game's files as the werewolf's bake reads them: loose files over the selected masters' archives
    (mwad.archives.layered_bsa: the werewolf's meshes are Bloodmoon's), once per process and data folder."""
    from mwad.archives import layered_bsa
    from npc_geometry import Assets
    key = str(Path(data).resolve())
    if key not in _assets:
        _assets[key] = Assets(Path(data), layered_bsa(Path(data)))
    return _assets[key]


class Rig:
    """A werewolf rig (creature_pose.CreatureRig of the mesh's animated model and its own keyframes only: not
    two-legged, so no base_anim source, as the original adds none for a werewolf) seen as an npc_geometry.Skeleton
    (halloween_cast.RigSkeleton) with the NIF reader attached (npc_geometry.assemble, export_actor and npc_anim.plan
    read .N)."""

    def __init__(self, N, assets, mesh):
        import creature_tables
        from halloween_cast import RigSkeleton
        self.N = N
        self.rig = creature_tables.open_rig(N, assets.read, mesh, False)
        sk = RigSkeleton(self.rig)
        self.parents, self.nodes, self.keys, self.events = sk.parents, sk.nodes, sk.keys, sk.events
        self.local, self.pose = sk.local, sk.pose


def mesh_has_shapes(raw):
    """False when a NIF holds no triangle shape at all (wolf/hair.nif: one node): it draws nothing."""
    return b'NiTriShape' in raw


def shape_kinds(N, raw):
    """[(name, skinned)] of a NIF's visible shapes with triangles, in the order halloween_cast.creature_shapes gives
    them (depth first, hidden nodes and collision left out)."""
    d = N.Data()
    d.read(io.BytesIO(raw))
    out = []

    def walk(node, hidden):
        if not isinstance(node, N.NiAVObject):
            return
        name = node.name.decode('cp1252')
        if isinstance(node, N.NiNode) and name.casefold() in ('rootcollisionnode', 'bounding box'):
            return
        hidden = hidden or bool(node.flags & 1)
        if isinstance(node, N.NiTriShape):
            if not hidden and node.data and node.data.num_triangles:
                out.append((name, bool(node.skin_instance)))
            return
        if isinstance(node, N.NiNode):
            for child in getattr(node, 'children', []) or []:
                if child:
                    walk(child, hidden)
    for root in d.roots:
        walk(root, False)
    return out


def _under(parents, name, ancestor):
    while name is not None:
        if name == ancestor:
            return True
        name = parents.get(name)
    return False


HEAD_BONE = 'bip01 head'          # the skeleton's head bone: the skin's own head hangs under it


def skin_shapes(N, assets, mesh, rig, times, own_head):
    """(shapes, materials, textures, sources, parents, rest_world) of the werewolf skin MESH posed on RIG (a Rig) at
    TIMES (halloween_cast.creature_shapes): its skinned shapes the chest's filter takes (attach.cpp's rule), and with
    OWN_HEAD its own head too (its rigid shapes under the head bone that carry a texture; the untextured 'Tri Head'
    marker box stays out). Returns also the names left out."""
    import halloween_cast
    raw = assets.read('meshes/' + mesh.replace('\\', '/'))
    shapes, materials, textures, sources, parents, rest_world = halloween_cast.creature_shapes(
        N, raw, rig.pose, times, assets)
    kinds = shape_kinds(N, raw)
    if [k[0] for k in kinds] != [s['name'] for s in shapes]:
        raise ValueError('%s: the shapes read differ from the bake\'s' % mesh)
    keep, left = [], []
    for i, ((name, skinned), src) in enumerate(zip(kinds, sources)):
        bare = name.casefold()[4:] if name.casefold().startswith('tri ') else name.casefold()
        textured = bool(materials[shapes[i]['material']].get('texture_index'))
        if skinned and bare.startswith(FILTER):
            keep.append(i)
        elif own_head and not skinned and textured and _under(parents, src['bones'][0], HEAD_BONE):
            keep.append(i)
        else:
            left.append(name)
    return [shapes[i] for i in keep], materials, textures, [sources[i] for i in keep], parents, rest_world, left


def head_shapes(assets, rig, times, head, whole):
    """(shapes, materials, textures, sources) of the head part HEAD (id, mesh) on RIG's 'Head' bone (npc_geometry
    .assemble and skeletal_actor.export_actor, as a player part's head): WHOLE, or without its largest shape (the head
    itself, which the skin's own head stands for: the eyes)."""
    from npc_geometry import assemble
    import skeletal_actor as sa
    from prepare_player_parts import part_dict
    appearance = {'id': 'werewolf head', 'skeleton': SKELETON, 'female': False, 'weight': 1.0, 'height': 1.0,
                  'parts': [part_dict(0, head[0], head[1])]}
    shapes, materials, textures = assemble(assets, appearance, rig, times)
    sources = sa.export_actor(assets, appearance, rig)
    if not whole and shapes:
        largest = max(range(len(shapes)), key=lambda i: len(shapes[i]['faces']))
        keep = [i for i in range(len(shapes)) if i != largest]
        shapes, sources = [shapes[i] for i in keep], [sources[i] for i in keep]
    return shapes, materials, textures, sources


def merged(a, b):
    """Two (shapes, materials, textures, sources) sets as one: B's materials after A's."""
    shapes, materials, textures, sources = a
    bs, bm, bt, bsrc = b
    off = len(materials)
    return (list(shapes) + [dict(s, material=s['material'] + off) for s in bs], list(materials) + list(bm),
            dict(textures, **bt), list(sources) + list(bsrc))


def body_shapes(N, assets, ww, rig, times, head_from=HEAD_FROM):
    """The third person's werewolf: (shapes, materials, textures, sources, parents, rest_world, facts) on RIG at TIMES
    by HEAD_FROM ('skin' W1 or 'part' W2); facts: the shapes kept and left out, the hair part skipped when empty."""
    if head_from not in HEAD_FROMS:
        raise ValueError('HEAD_FROM must be one of %s: %r' % (HEAD_FROMS, head_from))
    shapes, materials, textures, sources, parents, rest_world, left = skin_shapes(
        N, assets, ww['skin'][1], rig, times, own_head=head_from == 'skin')
    facts = {'skin': [s['name'] for s in shapes], 'skin_left_out': left}
    if ww.get('head'):
        head = head_shapes(assets, rig, times, ww['head'], whole=head_from == 'part')
        facts['head'] = [s['name'] for s in head[0]]
        shapes, materials, textures, sources = merged((shapes, materials, textures, sources), head)
    hair = ww.get('hair')
    if hair:
        raw = assets.read('meshes/' + hair[1].replace('\\', '/'))
        if mesh_has_shapes(raw):
            from npc_geometry import assemble
            import skeletal_actor as sa
            from prepare_player_parts import part_dict
            appearance = {'id': 'werewolf hair', 'skeleton': SKELETON, 'female': False, 'weight': 1.0, 'height': 1.0,
                          'parts': [part_dict(1, hair[0], hair[1])]}
            more = assemble(assets, appearance, rig, times) + (sa.export_actor(assets, appearance, rig),)
            shapes, materials, textures, sources = merged((shapes, materials, textures, sources), more)
            facts['hair'] = 'drawn'
        else:
            facts['hair'] = 'skipped: %s has no shape (the original draws nothing for it)' % hair[1]
    return shapes, materials, textures, sources, parents, rest_world, facts


# ---------------------------------------------------------------- the tables

def body_table(rig):
    """(table bytes, report) of the third person: the werewolf's own keyframes on the bones they move
    (creature_tables.table 'own': every group of the file)."""
    import creature_tables
    return creature_tables.table(rig.rig, 'own')


def body_layout(rig, table_bytes, report):
    """The player's groups (prepare_player_parts.player_profile) on the werewolf table's frames: the layout text
    (npc_anim.layout), the parts' view/parts_wm.txt."""
    import npc_anim
    import skeletal_actor as sa
    from prepare_player_parts import player_profile
    table = sa.read_table(report.get('own_table', table_bytes))
    _, groups = npc_anim.plan(rig, player_profile(), None, 1.0, player_block_hit=True)
    kit = npc_anim.table_groups(table, groups, None, report['times'])
    return npc_anim.layout(kit), kit


def hand_times(rig):
    """The hand-to-hand stance's 28 sample times of the first-person rig (prepare_hands.sample_clips 'hh')."""
    from prepare_hands import sample_clips
    return [float(t) for t in sample_clips(rig.events, 'hh')[0]]


def first_person_table(rig):
    """prepare_player_fp_parts.fp_table of the werewolf's first-person rig with every stance on its hand-to-hand
    frames (the weapon stances, the held light, the three spell stances): (table bytes, bones, view, times)."""
    import prepare_player_fp_parts as fp
    hh = hand_times(rig)
    return fp.fp_table(rig, stances=[(s, hh) for s in fp.STANCES], spells=[(s, hh) for s in fp.SPELL_STANCES],
                       light=hh)


def item_bones(bone_names):
    """(weapon bone, shield bone) table indices of BONE_NAMES, -1 where the table has none."""
    names = [b.casefold() for b in bone_names]
    return (names.index('weapon bone') if 'weapon bone' in names else -1,
            names.index('shield bone') if 'shield bone' in names else -1)


# ---------------------------------------------------------------- the reduction

def needed_model(shapes, materials, textures, palette, sources, rest_world, actor_scale, table_bytes, bone_names,
                 table_path, parents, **bake_args):
    """(MDL bytes, facts) of the shared-vertex route at its least passing count: skeletal_from_shapes' reducer
    'needed' with the outer-hull check by the source's own bones (hull_bones 'source'), step for step as the seam
    work's reducer hook makes it (tools/outer_reduce.py needed_bake; skeletal_actor._skeletal_finish), here for the
    werewolf only: the hook inside skeletal_from_shapes changes its code, and with it the unit keys of every resident,
    NPC appearance and creature the actor stages bake (measured: the npc-appearance, resident-bake,
    creature-tables-unit and creature-library caches), though no byte of theirs would change. Today's model is made
    first, for its face count only (where the search starts; when the bake's own body check refuses it, as it refuses
    the werewolf's skin at 480 faces for its open joints, the search starts from the ladder's first budget). A werewolf
    no count passes is refused (ValueError), never drawn unjudged or torn. facts['reducer'] says what was kept: the
    outer-hull row as drawn, the count searched from."""
    import numpy as np
    import skeletal_actor as sa
    from outer_reduce import drawn_row, needed_bake, summary
    try:
        model, facts = sa.skeletal_from_shapes(shapes, materials, textures, palette, sources, rest_world, actor_scale,
                                               table_bytes, bone_names, table_path=table_path, parents=parents,
                                               **bake_args)
        refused = None
    except ValueError as error:
        if not str(error).startswith('NPC body check'):
            raise
        start = int((bake_args.get('budgets') or sa.RESIDENT_BUDGETS)[0])
        model, facts, refused = None, {'faces': start, 'budget': start}, str(error)
    scale = np.asarray(actor_scale, float)
    tagged = [{**s, 'positions': np.concatenate((s['positions'], (s['positions'][0] + [(k + 1) * sa.SHAPE_TAG, 0, 0])
                                                 [None]))} for k, s in enumerate(shapes)]
    finished = {}

    def finish(found):
        # the model as the engine reads it (the pose box's byte grid) and its outer-hull row
        cand = sa._skeletal_finish(*found[:4], shapes, sources, rest_world, scale, table_bytes, bone_names,
                                   table_path, sa.BOX_EVERY, sa.SKEL_VERTEX_LIMIT, parents, False, facts['budget'],
                                   'reduced')
        drawn = np.clip(np.rint((cand[2] - cand[3]) / cand[4]), 0, 255) * cand[4] + cand[3]
        finished[id(found)] = (cand, drawn_row(tagged, sources, drawn, found[1]))
        return finished[id(found)]
    found = needed_bake(tagged, materials, textures, palette, sources, facts['faces'],
                        accept=lambda candidate: (finish(candidate)[1] or {}).get('problems') == [])
    if found is None:
        # the werewolf is drawn only by a model that passes the check: today's model is never shipped unjudged
        from outer_reduce import NEEDED_MAX
        raise ValueError('The werewolf passes the outer-hull check at no count up to %d faces%s' % (
            min(sum(len(s['faces']) for s in shapes), NEEDED_MAX),
            ' (today\'s model is refused too: %s)' % refused[:200] if refused else ''))
    today_faces = facts['faces']
    cand, row = finished.get(id(found)) or finish(found)
    model, facts = cand[0], cand[1]
    record = summary(row, REDUCER, **found[5]) if row is not None else dict(found[5], reducer=REDUCER)
    record['today_faces'] = today_faces
    if row is not None:
        record.update(row={k: row.get(k) for k in ('extent', 'girth', 'least_girth', 'lost', 'hull', 'open',
                                                   'seam_gap', 'seam_open', 'seam_gap_at', 'problems')})
    if refused:
        record.update(today_refused=refused[:300])
    return model, {'reducer': record, **{k: v for k, v in facts.items()
                                         if k not in ('shape_of', 'distance', 'nearest', 'rest_model')}}


# ---------------------------------------------------------------- the units

def body_part(ww):
    """The third person's part (prepare_player_parts.part_dict of the robe's skin in its slot)."""
    from prepare_player_parts import part_dict
    return part_dict(SLOT, ww['skin'][0], ww['skin'][1])


def first_person_part(ww):
    """The first person's part: the skin's '.1st' record in the recipe's arm slot, on the werewolf's own skeleton."""
    from prepare_player_parts import part_dict
    return dict(part_dict(FP_SLOT, ww['skin_1st'][0], ww['skin_1st'][1]), skeleton=SKELETON_1ST)


_codes = {}


def unit_code(function):
    """SHA-256 of the code a werewolf unit is baked by (pass_cache.source_digest of this module's FUNCTION and its
    reach), so the unit is baked again when that code changes (the player parts' own cache key holds only the import
    code of the modules it names)."""
    if function not in _codes:
        import pass_cache
        _codes[function] = pass_cache.source_digest((__file__, function))
    return _codes[function]


def bake_body(task):
    """Worker: the third person's werewolf. task = (data, palette, skeleton, part, cap) as the player parts' (SKELETON,
    body_part). Returns (model path, model bytes, report) with the table and the layout in report['_files']."""
    import time
    import numpy as np
    from prepare_player_parts import part_path
    from prepare_scenery import nif_reader
    data, palette, skeleton, part, cap = task
    t0 = time.time()
    kinds = _kinds(data)
    ww = werewolf_set(kinds)
    if not ww or ww['skin'][0] != part['id']:
        raise ValueError('The selected masters have no werewolf robe skin %s' % part['id'])
    N = nif_reader()
    assets = assets_of(data)
    rig = Rig(N, assets, ww['skin'][1])
    table, report = body_table(rig)
    layout, kit = body_layout(rig, table, report)
    idle = rig.rig.window('idle')
    if idle is None:
        raise ValueError('The werewolf\'s keyframes have no idle group')
    times = np.linspace(idle[1], idle[2], 8, endpoint=False)
    shapes, materials, textures, sources, parents, rest_world, facts = body_shapes(N, assets, ww, rig, times,
                                                                                   head_from=HEAD_FROM)
    own = report.get('own_table', table)
    raw, model = needed_model(shapes, materials, textures, palette, sources, rest_world, [.25, .25, .25], own,
                              report['bone_names'], TABLE, parents)
    out = part_path(skeleton, part)
    source_faces = sum(len(s['faces']) for s in shapes)
    source_vertices = sum(len(s['positions'][0]) for s in shapes)
    return out, raw, {'id': part['id'], 'slot': part['slot'], 'mesh': part['mesh'], 'skeleton': skeleton, 'model': out,
                      'bytes': len(raw), 'faces': model['faces'], 'vertices': model['vertices'],
                      'sha256': hashlib.sha256(raw).hexdigest(), 'cap': cap, 'head_from': HEAD_FROM,
                      'reducer': model.get('reducer'), 'source_faces': source_faces,
                      'source_vertices': source_vertices, 'shapes': facts, 'table': TABLE, 'table_bytes': len(table),
                      'table_sha256': hashlib.sha256(table).hexdigest(), 'table_frames': report['frames'],
                      'table_bones': report['bones'], 'table_groups': len(report['names']),
                      'bones_left_out': report.get('bones_left_out'), 'item_bones': item_bones(report['bone_names']),
                      'layout': LAYOUT, 'layout_groups': [g['name'] + (' (idle)' if g.get('source') == 'idle' else '')
                                                          for g in kit],
                      'seconds': round(time.time() - t0, 1),
                      '_files': {'table': table, 'layout': (layout + '\n').encode('ascii')}}


def bake_first_person(task):
    """Worker: the first person's werewolf arms. task = (data, palette, part, cap) as the first-person parts'
    (first_person_part). Returns (model path, model bytes, report) with the table in report['_files']."""
    import time
    import numpy as np
    from prepare_player_parts import part_path, quotas_for
    from prepare_scenery import nif_reader
    data, palette, part, cap = task
    t0 = time.time()
    kinds = _kinds(data)
    ww = werewolf_set(kinds)
    if not ww or not ww['skin_1st'] or ww['skin_1st'][0] != part['id']:
        raise ValueError('The selected masters have no werewolf first-person skin %s' % part['id'])
    N = nif_reader()
    assets = assets_of(data)
    rig = Rig(N, assets, ww['skin_1st'][1])
    table, bones, view, _ = first_person_table(rig)
    times = hand_times(rig)
    shapes, materials, textures, sources, parents, rest, left = skin_shapes(
        N, assets, ww['skin_1st'][1], rig, np.array(times), own_head=False)
    for shape in shapes:            # into the view space, as the first-person parts (prepare_player_fp_parts.bake_part)
        shape['positions'] = np.asarray(shape['positions'], float) @ view[:3, :3] + view[3, :3] * .25

    def rest_world(name):
        return np.asarray(rest(name), float) @ view
    raw, model = needed_model(shapes, materials, textures, palette, sources, rest_world, [.25, .25, .25], table, bones,
                              TABLE_1ST, parents, budgets=(cap,), quotas=quotas_for(shapes, cap), head_detail='budget',
                              body_skin_rows=480)
    out = part_path(SKELETON_1ST, part)
    return out, raw, {'id': part['id'], 'slot': part['slot'], 'mesh': part['mesh'], 'skeleton': SKELETON_1ST,
                      'model': out, 'bytes': len(raw), 'faces': model['faces'], 'vertices': model['vertices'],
                      'sha256': hashlib.sha256(raw).hexdigest(), 'cap': cap, 'reducer': model.get('reducer'),
                      'source_faces': sum(len(s['faces']) for s in shapes),
                      'source_vertices': sum(len(s['positions'][0]) for s in shapes),
                      'shapes': {'skin': [s['name'] for s in shapes], 'skin_left_out': left},
                      'table': TABLE_1ST, 'table_bytes': len(table), 'table_sha256': hashlib.sha256(table).hexdigest(),
                      'table_bones': len(bones), 'item_bones': item_bones(bones),
                      'stances': 'every stance on the hand-to-hand frames (the werewolf has no other group)',
                      'topology': model.get('topology'), 'skin_textures': {}, 'skin_tint': None,
                      'textures': sorted(str(t) for t in textures), 'seconds': round(time.time() - t0, 1),
                      '_files': {'table': table}}


def _kinds(data):
    """The merged masters' records, once per process (prepare_player_view._sources' kinds)."""
    import prepare_player_view as ppv
    return ppv._sources(data)[0]
