# SPDX-License-Identifier: GPL-3.0-only
"""The MiniWind Halloween scene (dbg halloween, docs/HALLOWEEN.md): its cast and the user's own soundtrack.

The scene is the animation stage (SKEL-ANIM-STAGE-52) with a beat clock: the engine (aw_halloween.c) puts a cast
before the camera on Balmora's stage roof and plays a choreography of the game's own animation groups on the beat.
This module writes what the engine needs into the image (--halloween: every full-world build by default, see
full_image_args and --halloween-cast; a MiniWind build with --halloween, as its preset --miniwind-halloween):

- the game's skeleton creature (r/skeleton.nif, every skeleton record uses it) as ONE skeletal model on the shared
  humanoid table (progs/humanoid.awsk): its rig is the humanoid biped (the creature is two-legged, so the original
  plays the shared xbase_anim keyframes on it; every bone of the table's stick figure is in it, no bone of it is
  missing from base_anim.nif), so every humanoid group plays on it by name, nothing baked;
- Dagoth Ur (r/dagothr.nif) on his OWN table (progs/dagothur.awsk) built from his own keyframes
  (meshes/r/xdagothr.kf: idle, idlespell, spellcast, attack1-3, hit1-2, knockdown, knockout, death1 ...), his
  model reduced as little as the skeletal reader allows;
- the three dancers of Desele's House of Earthly Delights (Suran) as skeletal residents on the female table;
- id1/halloween.txt, the cast list and the beat the engine dances to (CAST_FILE).

The custom OST slot (CUSTOM-OST-SLOT-53; --custom-ost FILE, alias --halloween-soundtrack, or the machine setting
AMIWIND_CUSTOM_OST): any audio or video file the user owns; ffmpeg takes its audio track, converts it to the game's
music stream (MWA1: 11,015 Hz stereo signed 8-bit, as tools/prepare_music.py) and adds it to that user's image as one
more special track (source name 'Special/custom.mp3', catalogued as 'custom'), which the engine's custom OST player
plays (aw music custom play; the Halloween scene). With a cast in the image its tempo is measured here (tempo()) and
written into the cast file, so the dance follows the user's own music. Without the setting the slot stays empty. Only
the image step packs it (it keys no other stage). The repository carries no audio: only this option, the conversion
and the default beat (DEFAULT_BPM, the tempo the scene was made to).
"""
import os
import hashlib
import io
import json
import subprocess
from pathlib import Path


class _NumPy:
    """numpy, imported when first used: tools/build.py imports this module for its options only."""

    def __getattr__(self, name):
        import numpy
        return getattr(numpy, name)


np = _NumPy()

CAST_FILE = 'halloween.txt'
MAGIC = 'AWHW1'
# The default beat in beats a minute (the engine's AW_HALLOWEEN_BPM10 is the same number x 10): the tempo the
# choreography was made to, used when the image has no soundtrack of its own.
DEFAULT_BPM = 132.0
SKELETON_MESH = 'r/skeleton.nif'
SKELETON_MODEL = 'progs/hw_skeleton.mdl'
DAGOTH_MESH = 'r/dagothr.nif'
DAGOTH_MODEL = 'progs/hw_dagothur.mdl'
DAGOTH_TABLE = 'progs/dagothur.awsk'
DANCERS = ('breton dancer girl', 'redguard dancer girl', 'nord dancer girl')
SOUNDTRACK_SOURCE = 'Special/custom.mp3'         # the music catalogue alias 'custom' (tools/music_catalogue.py)
CUSTOM_OST_SETTING = 'AMIWIND_CUSTOM_OST'
# Dagoth Ur's model: the largest vertex budget the skeletal reader takes first (SKEL_VERTEX_LIMIT 1,999; his whole
# model has 1,741 vertices), then smaller ones
DAGOTH_BUDGETS = (1000, 800, 640, 480)
# his gallery bake's face rules (config/gallery_model_quality.json, dagoth-mask-v1: the mask and crest kept) and the
# largest alias face limit
DAGOTH_BAKE = {'face_limit': 1024, 'minimum_faces': {'Tri neckpart': 30, 'Tri mask': 240, 'Tri maskpart': 47}}
TEMPO_RANGE = (90.0, 180.0)                      # a measured tempo is folded into this range (halves, doubles)
# A soundtrack's leading silence (its pre-roll, leading_silence): 10 ms windows, silent while their RMS stays at or
# under -40 dBFS (ffmpeg silencedetect's usual floor); at most the engine's AW_HALLOWEEN_MAX_PREROLL_MS.
SILENCE_DB = -40.0
SILENCE_WINDOW = 0.01
MAX_PREROLL_MS = 3500


# ---------------------------------------------------------------- the builder options (tools/build.py)

def add_options(p):
    p.add_argument('--halloween', action='store_true',
                   help='The Halloween scene\'s cast (dbg halloween, aw bench halloween; docs/HALLOWEEN.md): the '
                        'skeleton creature, Desele\'s dancers and Dagoth Ur on their animation tables (the preset '
                        '--miniwind-halloween sets it); a full-world build carries the cast by default')
    p.add_argument('--halloween-cast', choices=('on', 'off'), default='on',
                   help='The Halloween scene\'s cast in a full-world image (default on: about 1 MB, loaded only when '
                        'the scene starts, so aw bench halloween works in every full image); off leaves it out, and '
                        'dbg halloween and aw bench halloween then say the image has no cast. A MiniWind build '
                        'takes the cast with --halloween only (docs/HALLOWEEN.md)')
    p.add_argument('--custom-ost', '--halloween-soundtrack', dest='custom_ost', metavar='FILE',
                   help='The custom OST slot: your own audio or video file; its audio is converted into the game\'s '
                        'music format and put into this image only, played by the custom OST player (aw music custom '
                        'play) and the Halloween scene (also the machine setting %s; docs/HALLOWEEN.md)'
                        % CUSTOM_OST_SETTING)


def custom_ost(args):
    """The custom OST file: the option, else the machine setting, else None (the slot stays empty)."""
    return getattr(args, 'custom_ost', None) or os.environ.get(CUSTOM_OST_SETTING) or None


def check(args, p):
    """The options checked before any stage runs (p.exit on a mistake)."""
    track = custom_ost(args)
    if track and not Path(track).is_file():
        p.exit(1, 'Error: --custom-ost: no such file: %s\n' % track)


def image_args(args):
    """The image step's options of a MiniWind build (a full build's image step reads the machine setting)."""
    out = ['--halloween'] if getattr(args, 'halloween', False) else []
    if getattr(args, 'custom_ost', None):
        out += ['--custom-ost', str(args.custom_ost)]
    return out


def full_image_args(args):
    """The image step's cast option of a full-world build (not MiniWind: its presets choose with --halloween): the
    cast is in every full image by default (HALLOWEEN-SCENE-53, BENCH-NO-STANDARD-DEMO-48: aw bench halloween works
    in release images), --halloween-cast off leaves it out. Only the image step takes it: no other stage's command
    or key changes (imperative 19). No song: the custom OST slot stays empty unless the user fills it."""
    if getattr(args, 'miniwind', False) or getattr(args, 'halloween_cast', 'on') == 'off':
        return []
    return ['--halloween']


# ---------------------------------------------------------------- the skeletal creature models

class RigSkeleton:
    """A creature rig (creature_pose.CreatureRig) seen as an npc_geometry.Skeleton: nodes, parents, text keys,
    local(name, time) and pose(time), from one of its animation sources (its own KF file). For the table builder
    (skeletal_actor.build_table / KeptSkeleton)."""

    def __init__(self, rig, source=-1):
        self.rig, self.source = rig, source % len(rig.sources)
        self.index = {}
        self.parents = {}
        self.nodes = {}
        for i, (name, parent, _rest, _scale, bone) in enumerate(rig.nodes):
            if bone is None:
                continue
            self.index[name] = i
            self.nodes[name] = None
            self.parents[name] = rig.nodes[parent][0] if parent >= 0 else None
        src = rig.sources[self.source]
        self.keys = [(float(t), line.strip().casefold()) for t, line in src['keys']]
        self.events = {line: t for t, line in self.keys}

    def local(self, name, time):
        m = np.asarray(self.rig.local(self.index[name], self.source, float(time)), float).copy()
        # the table holds no scale: a bone's rest scale (1 in the game data) is taken out of its rotation
        s = np.linalg.norm(m[:3, :3], axis=1)
        if np.all(s > 1e-6):
            m[:3, :3] /= s[:, None]
        return m

    def pose(self, time):
        worlds = self.rig.worlds(self.source, float(time))
        by_name = {self.rig.nodes[i][0]: w for i, w in enumerate(worlds) if self.rig.nodes[i][4] is not None}
        return lambda name: by_name[name.casefold()]


def creature_shapes(N, raw, motion, times, assets):
    """(shapes, materials, textures, sources, parents, rest_world) of a creature NIF posed by MOTION: motion(time)
    gives name -> 4 x 4 world matrix for the bones it animates (a KeyError for any other node); every other node
    of the creature keeps its own rest transform under its parent. shapes as npc_geometry.assemble gives them
    (positions at each of TIMES, model units x 0.25), sources as skeletal_actor.export_actor (per shape its bones,
    bind and rest positions in bone space), in the same order. rest_world: the pose at times[0]."""
    from mwad.audit import normpath
    from skeletal_actor import bind_skinned
    d = N.Data()
    d.read(io.BytesIO(raw))
    nodes, parents, shapes_in = {}, {}, []

    def walk(node, parent, hidden):
        if not isinstance(node, N.NiAVObject):
            return
        name = node.name.decode('cp1252').casefold()
        if isinstance(node, N.NiNode) and name in ('rootcollisionnode', 'bounding box'):
            return
        hidden = hidden or bool(node.flags & 1)
        local = np.array(node.get_transform().as_list())
        if isinstance(node, N.NiTriShape):
            if not hidden and node.data and node.data.num_triangles:
                shapes_in.append((node, parent, local))
            return
        if isinstance(node, N.NiNode):
            if name not in nodes:           # a repeated node name keeps the first (the keyframes bind the first)
                nodes[name] = local
                parents[name] = parent
            for child in getattr(node, 'children', []) or []:
                if child:
                    walk(child, name, hidden)
    for root in d.roots:
        walk(root, None, False)
    order = list(nodes)

    def world_at(time):
        moved = motion(time)
        out = {}
        for name in order:
            try:
                out[name] = np.asarray(moved(name), float)
                continue
            except KeyError:
                pass
            p = parents[name]
            out[name] = nodes[name] if p is None else nodes[name] @ out[p]
        return out
    poses = [world_at(float(t)) for t in times]
    shapes, materials, textures, sources = [], [], {}, []
    for node, parent, local in shapes_in:
        g = node.data
        name = node.name.decode('cp1252')
        vertices = np.array([v.as_list() for v in g.vertices])
        hom = np.column_stack((vertices, np.ones(len(vertices))))
        if node.skin_instance:
            sk = node.skin_instance
            names = [b.name.decode('cp1252').casefold() for b in sk.bones]
            weights, inverse = {}, {}
            positions = np.zeros((len(times), len(vertices), 3))
            total = np.zeros(len(vertices))
            for i, info in enumerate(sk.data.bone_list):
                ids = np.array([w.index for w in info.vertex_weights], int)
                ws = np.array([w.weight for w in info.vertex_weights])
                inverse[i] = np.array(info.get_transform().as_list())
                if not len(ids) or not np.any(ws):
                    continue
                weights[i] = (list(ids), list(ws))
                total[ids] += ws
                for fi, pose in enumerate(poses):
                    positions[fi, ids] += (hom[ids] @ inverse[i] @ pose[names[i]])[:, :3] * ws[:, None]
            if np.any(np.abs(total - 1) > .02):
                raise ValueError('Invalid skin weights ' + name)
            positions /= total[None, :, None]
            bone, second, weight, rest, rest2 = bind_skinned(vertices, weights, inverse)
        else:
            names = [parent]
            rest = (hom @ local)[:, :3]
            positions = np.array([(hom @ local @ pose[parent])[:, :3] for pose in poses])
            bone = np.zeros(len(vertices), int)
            second = np.full(len(vertices), -1)
            weight = np.zeros(len(vertices))
            rest2 = np.zeros_like(rest)
        uv = np.array([[u.u, u.v] for u in g.uv_sets[0]]) if g.num_uv_sets else np.zeros((len(vertices), 2))
        colours = np.array([[c.r, c.g, c.b, c.a] for c in g.vertex_colors]) if g.has_vertex_colors \
            else np.ones((len(vertices), 4))
        diffuse, alpha, source = [1., 1., 1.], 1., None
        for prop in node.properties:
            if isinstance(prop, N.NiMaterialProperty):
                diffuse = [prop.diffuse_color.r, prop.diffuse_color.g, prop.diffuse_color.b]
                alpha = prop.alpha
            if isinstance(prop, N.NiTexturingProperty) and prop.has_base_texture and prop.base_texture.source:
                source = prop.base_texture.source.file_name.decode('cp1252')
        ti = None
        if source:
            ti = normpath(source)
            if ti not in textures:
                textures[ti] = assets.texture(source)
        materials.append({'texture_index': ti, 'diffuse': diffuse, 'alpha': alpha})
        faces = np.array(g.get_triangles(), int)
        shapes.append({'name': name, 'part': -1, 'positions': positions * .25, 'faces': faces, 'uv': uv,
                       'colours': colours, 'material': len(materials) - 1})
        sources.append({'name': name, 'part': -1, 'bones': names, 'bone': bone, 'second': second, 'weight': weight,
                        'rest': rest, 'rest2': rest2, 'faces': faces, 'uv': uv, 'texture': ti})
    if not shapes:
        raise ValueError('No visible geometry')
    rest = poses[0]
    return shapes, materials, textures, sources, parents, (lambda name: rest[name.casefold()])


def creature_model(N, raw, motion, times, assets, palette, table_bytes, bone_names, table_path, budgets,
                   **bake_args):
    """(MDL bytes, report) of a creature as one skeletal model on a shared table (skeletal_actor.skeletal_from_shapes:
    the resident bake's reduction, one rest frame, the AWSB block naming TABLE_PATH)."""
    from skeletal_actor import skeletal_from_shapes
    shapes, materials, textures, sources, parents, rest_world = creature_shapes(N, raw, motion, times, assets)
    for budget in budgets:
        # down the ladder also when the reduced model has more vertices than the skeletal reader takes
        try:
            return skeletal_from_shapes(shapes, materials, textures, palette, sources, rest_world, [.25, .25, .25],
                                        table_bytes, bone_names, table_path=table_path, budgets=(budget,),
                                        parents=parents, **bake_args)
        except ValueError as error:
            if not (str(error).startswith('A skeletal model takes at most') or
                    str(error) == 'Unsupported alias skin') or budget == budgets[-1]:
                raise


def skeleton_creature(assets, palette, skeleton_of):
    """The skeleton creature on the common humanoid table: (MDL bytes, report). skeleton_of(path) ->
    npc_geometry.Skeleton (base_anim.nif: the table's own motion, so the model's rest pose is the table's)."""
    import creature_pose
    import skeletal_actor
    from prepare_scenery import nif_reader
    N = nif_reader()
    data, report, _table, path, base, _over = skeletal_actor.game_table(
        'halloween', {'skeleton': 'meshes/base_anim.nif'}, skeleton_of)
    model_path, _kf = creature_pose.actor_files(assets.read, SKELETON_MESH)
    raw = assets.read(model_path)
    missing = [b for b in report['bone_names'] if b not in rig_names(N, raw)]
    if missing:
        raise ValueError('The skeleton creature lacks bones of the humanoid table: %s' % missing)
    times, _ = base.idle_times(8)

    def motion(t):
        world = base.pose(float(t))

        def call(name):
            if name not in base.nodes:
                raise KeyError(name)
            return world(name)
        return call
    model, facts = creature_model(N, raw, motion, times, assets, palette, data, report['bone_names'], path,
                                  skeletal_actor.RESIDENT_BUDGETS)
    return model, {'mesh': model_path, 'table': path, 'table_bytes': len(data), **_facts(facts)}


def rig_names(N, raw):
    d = N.Data()
    d.read(io.BytesIO(raw))
    out = set()

    def walk(node):
        if isinstance(node, N.NiNode):
            out.add(node.name.decode('cp1252').casefold())
            for c in getattr(node, 'children', []) or []:
                if c:
                    walk(c)
    for r in d.roots:
        walk(r)
    return out


def dagoth_ur(assets, palette):
    """Dagoth Ur on his own table: (table bytes, MDL bytes, report). The table: his own keyframes (xdagothr.kf) on
    the stick figure's bones he has (no weapon or shield bone) and his toes, every group of his text keys."""
    import creature_pose
    import skeletal_actor
    from prepare_scenery import nif_reader
    N = nif_reader()
    rig = creature_pose.CreatureRig(N, assets.read, DAGOTH_MESH, False)
    sk = RigSkeleton(rig)
    keep = tuple(b for b in skeletal_actor.STICK_BONES + skeletal_actor.BEAST_BONES if b in sk.parents)
    table, report = skeletal_actor.build_table(skeletal_actor.KeptSkeleton(sk, keep),
                                               tolerance=skeletal_actor.POSITION_TOLERANCE)
    if report['missing']:
        raise ValueError('Dagoth Ur table: groups without start or stop keys: %s' % report['missing'])
    idle = rig.window('idle')
    times = np.linspace(idle[1], idle[2], 8, endpoint=False)
    model, facts = creature_model(N, rig.raw, sk.pose, times, assets, palette, table, report['bone_names'],
                                  DAGOTH_TABLE, DAGOTH_BUDGETS, **DAGOTH_BAKE)
    return table, model, {'mesh': rig.model, 'table': DAGOTH_TABLE, 'table_bytes': len(table),
                          'table_groups': report['names'], 'table_frames': report['frames'],
                          'table_bones': report['bones'], **_facts(facts)}


def _facts(facts):
    return {k: v for k, v in facts.items() if k not in ('shape_of', 'distance', 'nearest', 'rest_model')}


# ---------------------------------------------------------------- the cast

def cast_text(rows, bpm, soundtrack, preroll_ms=0):
    """id1/halloween.txt: 'AWHW1 <bpm x 10> <1 with a soundtrack track, else 0> [<pre-roll ms>]', then one row a
    model: '<role> <model path> <name>' (role lead, dancer or skeleton; spaces in the name as '_'). The pre-roll (a
    soundtrack's leading silence, leading_silence) is written only when there is one, so a cast without it reads as
    before (the engine's aw_halloween_rules.c reader takes both)."""
    if not 30 <= bpm <= 300:
        raise ValueError('Halloween beat outside 30..300 BPM: %s' % bpm)
    if not 0 <= int(preroll_ms) <= MAX_PREROLL_MS:
        raise ValueError('Halloween pre-roll outside 0..%d ms: %s' % (MAX_PREROLL_MS, preroll_ms))
    lines = ['%s %d %d' % (MAGIC, int(round(bpm * 10)), 1 if soundtrack else 0) +
             (' %d' % int(preroll_ms) if soundtrack and int(preroll_ms) else '')]
    for role, model, name in rows:
        if role not in ('lead', 'dancer', 'skeleton'):
            raise ValueError('Unknown Halloween role ' + role)
        if len(model) >= 64 or ' ' in model or not model.startswith('progs/'):
            raise ValueError('Bad Halloween model path ' + model)
        lines.append('%s %s %s' % (role, model, name.replace(' ', '_')[:31] or '?'))
    return '\n'.join(lines) + '\n'


def read_cast(text):
    """(bpm, soundtrack, rows) of a cast file (the engine's reader, for the tests); read_preroll gives the pre-roll."""
    lines = text.splitlines()
    head = lines[0].split()
    if len(head) not in (3, 4) or head[0] != MAGIC:
        raise ValueError('Not a Halloween cast file')
    return int(head[1]) / 10, head[2] == '1', [tuple(line.split(' ', 2)) for line in lines[1:] if line]


def read_preroll(text):
    """The cast file's pre-roll in milliseconds (0 when it has none)."""
    head = text.splitlines()[0].split()
    return int(head[3]) if len(head) == 4 else 0


# The game's spell cast sounds (its SOUN records, the short cast "whoosh" of each school, and the bolt of a cast on
# target), converted from the user's game data as the combat sounds are (tools/prepare_combat.py): the engine plays
# one on each spellcast release key of a skeletal actor (aw_halloween.c AW_SkelCastSound).
CAST_SOUNDS = (('destruction', 'destruction cast'), ('alteration', 'alteration cast'), ('illusion', 'illusion cast'),
               ('conjuration', 'conjuration cast'), ('mysticism', 'mysticism cast'),
               ('restoration', 'restoration cast'), ('bolt', 'destruction bolt'))
CAST_SOUND_DIR = 'sound/aw/cast'


def cast_sounds(kinds, assets, id1):
    """Writes id1/sound/aw/cast/<name>.wav for each CAST_SOUNDS record the game data has; returns what it wrote."""
    from prepare_combat import convert_wav, first, string
    out = {}
    (Path(id1) / CAST_SOUND_DIR).mkdir(parents=True, exist_ok=True)
    for name, record in CAST_SOUNDS:
        fields = kinds.get('SOUN', {}).get(record)
        if not fields:
            continue
        source = 'sound/' + string(first(fields, 'FNAM')).replace('\\', '/').casefold()
        try:
            seconds = convert_wav(assets.read(source), Path(id1) / CAST_SOUND_DIR / (name + '.wav'))
        except Exception as error:  # noqa: BLE001 (a sound the data lacks is left out with its reason)
            out[name] = {'record': record, 'error': str(error)}
            continue
        out[name] = {'record': record, 'source': source, 'seconds': round(seconds, 3)}
    return out


def set_beat(id1, bpm, preroll_ms=0):
    """The cast file's beat set to a soundtrack's measured tempo, its soundtrack flag on and its pre-roll (the
    track's leading silence in ms: the engine starts the track that much before the dance)."""
    path = Path(id1) / CAST_FILE
    if not path.is_file():
        return                    # an image without the Halloween cast: the custom track alone
    _, _, rows = read_cast(path.read_text(encoding='ascii'))
    path.write_text(cast_text([(r, m, n) for r, m, n in rows], bpm, True, preroll_ms), encoding='utf-8',
                    newline='\n')


def leading_silence(pcm, rate, channels=2, threshold_db=SILENCE_DB, window=SILENCE_WINDOW):
    """Milliseconds of silence at the start of a converted track (signed 8-bit interleaved PCM, as the image plays
    it): the start of the first WINDOW-second stretch whose RMS over the channels is above THRESHOLD_DB (dBFS). The
    8-bit dither of silence stays well under -40 dB; the whole track silent gives its length."""
    x = np.frombuffer(pcm, np.int8).astype(np.float64) / 128.0
    frames = len(x) // channels
    x = x[:frames * channels].reshape(frames, channels)
    n = max(1, int(round(rate * window)))
    blocks = frames // n
    if not blocks:
        return 0
    rms = np.sqrt((x[:blocks * n] ** 2).reshape(blocks, n * channels).mean(axis=1))
    loud = np.flatnonzero(rms > 10 ** (threshold_db / 20))
    first = int(loud[0]) if len(loud) else blocks
    return int(round(1000 * first * n / rate))


def dancer_model(identifier):
    """A dancer's model path: the cast's own name (hw_...), never a resident's a_... name. A full image holds
    Desele's dancers as Suran residents under a_<hash>.mdl, from the room stages, and installs them after the cast
    is made: a cast model under that name would be replaced by (or would replace) the resident's own files."""
    return 'progs/hw_' + hashlib.sha256(identifier.encode()).hexdigest()[:12] + '.mdl'


def _assets(data):
    from mwad.audit import BSA
    from mwad.paths import child_ci
    from npc_geometry import Assets
    return Assets(Path(data), BSA(child_ci(Path(data), 'Morrowind.bsa')))


def _error(error):
    return '%s: %s' % (type(error).__name__, error)


def member(item):
    """One cast member, made in a worker of its own (prepare runs them side by side): (kind, result, error).
    The skeletons are required (an error is raised); any other member returns its error and is left out."""
    kind = item[0]
    if kind == 'skeleton':
        from npc_geometry import Skeleton
        _, data, palette = item
        assets = _assets(data)
        skeletons = {}

        def skeleton_of(path):
            if path not in skeletons:
                skeletons[path] = Skeleton(assets, path)
            return skeletons[path]
        return kind, skeleton_creature(assets, palette, skeleton_of), None
    try:
        if kind == 'dagoth':
            _, data, palette = item
            return kind, dagoth_ur(_assets(data), palette), None
        if kind == 'dancer':
            from prepare_area import build_resident
            identifier, raw, _voice, record = build_resident(item[1])
            return kind, (identifier, raw, record), None
        if kind == 'sounds':
            from mwad.paths import child_ci
            from prepare_combat import load as load_sounds
            _, data, stage = item
            return kind, cast_sounds(load_sounds(child_ci(Path(data), 'Morrowind.esm')), _assets(data), stage), None
    except Exception as error:  # noqa: BLE001 (left out with its reason: the skeletons-only version still plays)
        return kind, (item[1][2]['id'] if kind == 'dancer' else None), _error(error)
    raise ValueError('Unknown Halloween cast member ' + kind)


# the members' relative cost, the larger first (build_parallel: a long member never starts last)
MEMBER_COST = {'dagoth': 4, 'dancer': 3, 'skeleton': 3, 'sounds': 1}


def install(stage, id1):
    """The staged cast files into id1, each replaced whole (mwad.paths.replace_bytes: a read-only pool link in id1 is
    replaced, never written through). A shared file the image already holds (the humanoid table, an item model, a
    sound) is kept as it is: it is the same game file, made for the world by the stages before. Returns
    (written, kept)."""
    from mwad.paths import replace_bytes
    stage, id1 = Path(stage), Path(id1)
    written, kept = [], []
    for path in sorted(p for p in stage.rglob('*') if p.is_file()):
        relative = path.relative_to(stage).as_posix()
        target = id1 / relative
        raw = path.read_bytes()
        if target.is_file():
            if target.read_bytes() == raw or not owned(relative):
                kept.append(relative)
                continue
        target.parent.mkdir(parents=True, exist_ok=True)
        replace_bytes(target, raw)
        written.append(relative)
    return written, kept


def owned(relative):
    """True for the cast's own files (replaced when they differ); False for the files it shares with the world."""
    return relative == CAST_FILE or relative == DAGOTH_TABLE or relative.startswith(('progs/hw_', CAST_SOUND_DIR + '/'))


def prepare(data_files, id1, jobs=1, soundtrack_bpm=None):
    """Writes the cast models, Dagoth Ur's table and id1/halloween.txt. Returns the report. A cast member that
    cannot be made is left out with its reason (the scene dances with the rest); the skeletons are required.

    The members (the skeleton creature, Dagoth Ur, each dancer, the cast sounds) are made side by side in the
    builder's worker pool (build_parallel.in_order_map; one after the other at one job: about 2 minutes on one core
    in the v0.0.53 Halloween builds), into a staging folder, and installed into id1 at the end (install)."""
    from build_parallel import in_order_map
    from build_scratch import scratch_dir
    from mwad.npc import load_master, outfit, greeting_fixture
    from mwad.paths import child_ci, replace_bytes as replace

    def replace_bytes(path, raw):
        path.parent.mkdir(parents=True, exist_ok=True)
        replace(path, raw)
    from npc_anim import foot_class, publish as publish_anim, voices_of
    import npc_items
    import npc_lod
    data = Path(data_files)
    id1 = Path(id1)
    palette = (id1 / 'gfx/palette.lmp').read_bytes()
    rows, report = [], {'left_out': []}
    kinds, _cells, topics = load_master(child_ci(data, 'Morrowind.esm'))
    items = [('skeleton', data, palette), ('dagoth', data, palette)]
    for identifier in DANCERS:
        if identifier not in kinds['NPC_']:
            report['left_out'].append({'id': identifier, 'reason': 'no such NPC record'})
            continue
        appearance = npc_items.attach_items(kinds, identifier, outfit(kinds, identifier))
        appearance['foot'] = foot_class(kinds, appearance)
        appearance['voices'] = voices_of(topics, appearance)
        items.append(('dancer', (data, palette, appearance, greeting_fixture(topics, appearance), 'ffmpeg',
                                 npc_lod.task_settings())))
    # the staging folder beside the image step's output (out/.scratch), never /tmp and never in the boot folder
    with scratch_dir(prefix='halloween-cast-', near=id1.parent.parent, keep_on_failure=False) as stage:
        items.append(('sounds', data, stage))
        report['dancers'] = []
        lead = []
        for kind, result, error in in_order_map(member, items, max(1, min(int(jobs or 1), len(items))),
                                                cost=lambda item: MEMBER_COST[item[0]]):
            if kind == 'skeleton':
                model, facts = result
                replace_bytes(stage / SKELETON_MODEL, model)
                report['skeleton'] = {'model': SKELETON_MODEL, **facts}
            elif kind == 'dagoth':
                if error:
                    report['left_out'].append({'id': 'dagoth_ur', 'reason': error})
                    print('Halloween cast: Dagoth Ur left out:', error, flush=True)
                    continue
                table, model, facts = result
                replace_bytes(stage / DAGOTH_TABLE, table)
                replace_bytes(stage / DAGOTH_MODEL, model)
                lead.append(('lead', DAGOTH_MODEL, 'Dagoth Ur'))
                report['dagoth_ur'] = {'model': DAGOTH_MODEL, **facts}
            elif kind == 'dancer':
                if error:
                    report['left_out'].append({'id': result, 'reason': error})
                    continue
                identifier, raw, record = result
                record.update(model=dancer_model(identifier))
                replace_bytes(stage / record['model'], raw)
                publish_anim(stage, record)
                npc_items.publish(stage, record)
                rows.append(('dancer', record['model'], record['appearance']['name']))
                report['dancers'].append({'id': identifier, 'model': record['model'], 'bytes': len(raw)})
            elif kind == 'sounds':
                report['cast_sounds'] = result if not error else {'error': error}
        rows = lead + rows + [('skeleton', SKELETON_MODEL, 'Skeleton')]
        import skeletal_actor
        for path, table in skeletal_actor.table_files().items():
            replace_bytes(stage / path, table)
        bpm = soundtrack_bpm or DEFAULT_BPM
        text = cast_text(rows, bpm, soundtrack_bpm is not None)
        replace_bytes(stage / CAST_FILE, text.encode('ascii', 'replace'))
        written, kept = install(stage, id1)
    report.update(cast=rows, bpm=bpm, soundtrack=soundtrack_bpm is not None,
                  files={'written': len(written), 'kept': kept,
                         'bytes': sum((id1 / p).stat().st_size for p in written)})
    return report


# ---------------------------------------------------------------- the user's soundtrack

def decode(path, rate, ffmpeg='ffmpeg', channels=2, fmt='s8'):
    """The audio track of any audio or video file ffmpeg reads, as raw PCM bytes (no file written)."""
    af = ['-af', 'aresample=osf=u8:dither_method=triangular'] if fmt == 's8' else []
    return subprocess.check_output([ffmpeg, '-v', 'error', '-nostdin', '-threads', '1', '-i', str(path), '-vn',
                                    '-ac', str(channels), '-ar', str(rate), *af, '-f', fmt, 'pipe:1'])


def tempo(samples, rate):
    """The tempo of mono float samples in beats a minute: a spectral-flux onset envelope, its autocorrelation
    scored at one to four beats for every tenth of a BPM from 60 to 200, the best folded into TEMPO_RANGE."""
    n, hop = 1024, 128
    x = np.asarray(samples, float)
    frames = 1 + (len(x) - n) // hop
    if frames < 64:
        raise ValueError('Too little audio to measure a tempo')
    win = np.hanning(n)
    spec = np.empty((frames, n // 2 + 1))
    for i in range(0, frames, 2048):
        k = min(frames, i + 2048)
        block = np.stack([x[j * hop:j * hop + n] * win for j in range(i, k)])
        spec[i:k] = np.log1p(100 * np.abs(np.fft.rfft(block, axis=1)))
    flux = np.maximum(0, np.diff(spec, axis=0)).sum(axis=1)
    flux = np.maximum(flux - np.convolve(flux, np.ones(32) / 32, mode='same'), 0)
    env = flux - flux.mean()
    size = 1 << int(np.ceil(np.log2(2 * len(env))))
    f = np.fft.rfft(env, size)
    ac = np.fft.irfft(f * np.conj(f), size)[:len(env)]
    fps = rate / hop
    best, best_bpm = -np.inf, None
    for bpm10 in range(600, 2001):
        lag = 60 * fps / (bpm10 / 10)
        score = 0.0
        for k in (1, 2, 3, 4):
            at = lag * k
            i = int(at)
            if i + 1 >= len(ac):
                break
            score += (ac[i] * (1 - (at - i)) + ac[i + 1] * (at - i)) / k
        if score > best:
            best, best_bpm = score, bpm10 / 10
    while best_bpm < TEMPO_RANGE[0]:
        best_bpm *= 2
    while best_bpm > TEMPO_RANGE[1]:
        best_bpm /= 2
    return round(best_bpm, 1)


def soundtrack(path, music_dir, ffmpeg='ffmpeg'):
    """Adds the user's file to the image's music: its audio as one more MWA1 track (the next trackNN.mws), the
    image's soundtrack.json extended by it (source SOUNDTRACK_SOURCE). Returns (record, measured BPM)."""
    from prepare_music import RATE, BLOCK_FRAMES, pack_stream, unpack_stream
    music_dir = Path(music_dir)
    manifest_path = music_dir / 'soundtrack.json'
    manifest = json.loads(manifest_path.read_text())
    if any(t.get('source') == SOUNDTRACK_SOURCE for t in manifest['tracks']):
        raise ValueError('The image already has a Halloween soundtrack')
    number = len(manifest['tracks'])
    if number > 98:
        raise ValueError('No free music track number for the soundtrack')
    pcm = decode(path, RATE, ffmpeg)
    if not pcm:
        raise ValueError('No audio track in ' + Path(path).name)
    packed = pack_stream(pcm)
    if unpack_stream(packed) != pcm:
        raise ValueError('Soundtrack round-trip mismatch')
    name = 'track%02d.mws' % number
    (music_dir / name).write_bytes(packed)
    frames = len(pcm) // 2
    record = {'file': name, 'source': SOUNDTRACK_SOURCE, 'user_soundtrack': True, 'pcm_frames': frames,
              'seconds': frames / RATE, 'blocks': (frames + BLOCK_FRAMES - 1) // BLOCK_FRAMES,
              'bytes': len(packed), 'sha256': hashlib.sha256(packed).hexdigest()}
    manifest['tracks'].append(record)
    manifest['seconds'] = sum(t['seconds'] for t in manifest['tracks'])
    manifest['bytes'] = sum(t['bytes'] for t in manifest['tracks'])
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
    mono = np.frombuffer(decode(path, 11025, ffmpeg, channels=1, fmt='f32le'), np.float32)
    # the leading silence of the track as the image plays it: the scene's pre-roll (set_beat)
    return dict(record, leading_silence_ms=min(leading_silence(pcm, RATE), MAX_PREROLL_MS)), tempo(mono, 11025)
