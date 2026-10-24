# SPDX-License-Identifier: GPL-3.0-only
"""Owned third-person guard torch companions. Base models and BSPs stay unchanged."""
from pathlib import Path
import hashlib
import json
import re
import struct
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.audit import BSA, records, subrecords, normpath
from mwad.npc import load_master, outfit, text, first
from mwad.paths import child_ci, ensure_external
from npc_geometry import Assets, Skeleton, assemble, bake, animated_mdl, rigid_attachment
from npc_faces import ActorSkeleton, actor_samples
from npc_anim import BoneLayer
from prepare_hand_sprites import decode_mdl
from prepare_torch import source_nodes
import actor_frames
from map_files import map_files

GUARD_CLASSES = frozenset(('guard', 'ordinator guard'))
# Registry records, one per staged (guard source id, base model): the engine's table holds the same number
# (engine/aga/src/aw_torch.h AW_GUARD_TORCH_TYPES; tests/test_guard_torch_assets.py keeps them equal). 32 until
# v0.0.48: with every interior on CHIM rooms dev2 try12 staged 51 records over 49 base models, two models shared by
# two guards of different appearance, so sharing records by model saves nothing (GUARD-TORCH-TYPES-LIMIT-48).
MAX_RECORDS = 128
sha = lambda value: hashlib.sha256(value).hexdigest()


def guard_eligibility(fields, lights, torch_mesh):
    """Class identity and carried original inventory, never actor display names."""
    guard = text(fields, 'CNAM').casefold() in GUARD_CLASSES
    inventory = []
    if not guard:
        return False, False, inventory
    for tag, raw in fields:
        if tag != 'NPCO':
            continue
        if len(raw) != 36:
            raise ValueError('Malformed guard inventory entry')
        count = struct.unpack_from('<i', raw)[0]
        identifier = raw[4:].split(b'\0', 1)[0].decode('cp1252').casefold()
        if not count or identifier not in lights:
            continue
        light = lights[identifier]
        data = first(light, 'LHDT')
        if len(data) != 24:
            raise ValueError('Malformed guard inventory light')
        if not struct.unpack_from('<I', data, 20)[0] & 2:
            continue  # Only original carryable lights can be equipped.
        if normpath(text(light, 'MODL')) != normpath(torch_mesh):
            raise ValueError('Guard carries a different unsupported light mesh: ' + identifier)
        inventory.append({'id': identifier, 'count': count})
    return True, bool(inventory), inventory


def safe_model(name):
    if not re.fullmatch(r'progs/[A-Za-z0-9_/-]+\.mdl', name) or len(name) > 63 or '..' in name:
        raise ValueError('Unsafe guard model path')
    return name


def registry(records_):
    if len(records_) > MAX_RECORDS:
        raise ValueError('Guard registry exceeds bounded record count: %d of %d' % (len(records_), MAX_RECORDS))
    raw = bytearray(struct.pack('>4sHH', b'AWG1', len(records_), 0))
    seen = set()
    for item in records_:
        key = (item['source_id'], item['base_model'])
        if key in seen:
            raise ValueError('Duplicate guard model identity')
        seen.add(key)
        for name in ('source_id', 'base_model', 'body_model', 'torch_model'):
            value = item[name]
            encoded = value.encode('cp1252')
            if not encoded or len(encoded) > 63 or any(c in encoded for c in (0, 10, 13, 34)):
                raise ValueError('Invalid guard identity string')
            if name != 'source_id':
                safe_model(value)
            raw.extend(encoded.ljust(64, b'\0'))
        anchors = np.asarray(item['emitters'], dtype=float)
        count = item['frames']
        if count not in actor_frames.LEGACY_FRAME_COUNTS or anchors.shape != (count, 3) or not np.isfinite(anchors).all() or np.max(abs(anchors)) > 128:
            raise ValueError('Invalid guard frame/anchor bounds')
        raw.extend(struct.pack('>HH', count, int(bool(item['auto_inventory_eligible']))))
        raw.extend(np.rint(anchors*65536).astype('>i4').tobytes())
    return bytes(raw)


class TorchLayer:
    """Overlay authored torch keys only below the original left clavicle."""
    def __init__(self, base, normal, times):
        self.base, self.normal, self.times = base, normal, times
        self.N = base.N
        self.start = base.events['torch: start']
        self.stop = base.events['torch: stop']
        if not np.isfinite([self.start, self.stop]).all() or not 0 < self.stop-self.start < 60:
            raise ValueError('Invalid third-person torch key range')
        if 'bip01 l clavicle' not in base.nodes:
            raise ValueError('Missing authored left arm root')
        self.layer = BoneLayer(base, ('bip01 l clavicle',))

    def pose(self, time):
        index = int(time)
        if index != time or not 0 <= index < len(self.times):
            raise ValueError('Invalid guard pose sample')
        normal = self.normal.pose(float(self.times[index]))
        phase = index if index < 8 else index-13 if index >= 13 else 0
        torch_time = self.start + phase/8*(self.stop-self.start)
        return self.layer.pose(normal, torch_time)


SKIPPABLE_PREFIX = 'progs/np_'


class BaseNotReproduced(ValueError):
    """A guard model this tool cannot rebake exactly. An intro actor's model (SKIPPABLE_PREFIX, baked by
    tools/prepare_intro.py with its own settings) then gets no torch companion and is named in the receipt; any other
    guard still fails the step (GUARD-TORCH-CHIM-FRAMES-44)."""


# Guards first staged in v0.0.48 (every interior on CHIM rooms) whose base model this tool does not rebake exactly
# yet, by source id, with the register entry that tracks them (dev2 try12: six orc guards and one nord: positions
# 26..33 quantisation steps off in 916..2194 coordinates; todd: every candidate bake over the alias vertex budget).
# They never had a torch; they get none, named in the receipt, until GUARD-TORCH-REBAKE-MISMATCH-48 is fixed. Any
# other guard that does not rebake still fails the step.
KNOWN_NOT_REPRODUCED = {source: 'GUARD-TORCH-REBAKE-MISMATCH-48' for source in (
    'bagamul gro-dumul', 'largakh gro-bulfim', 'nash gro-khazor', 'thalestris', 'todd', 'ughash gro-batul',
    'yambul gro-bogrol', 'yashnarz gro-ufthamph')}


def check_skips(skipped, known=None):
    """Only the intro actors' own models (tools/prepare_intro.py bakes progs/np_*.mdl with its own settings) and the
    listed known guards (KNOWN_NOT_REPRODUCED; known={} is the earlier rule, intro models only) may be skipped; any
    other guard that does not rebake exactly still fails the step, so torches are never lost silently."""
    known = KNOWN_NOT_REPRODUCED if known is None else known
    strict = [row for row in skipped if not row['base_model'].startswith(SKIPPABLE_PREFIX)
              and row['source_id'] not in known]
    if strict:
        raise ValueError('; '.join(row['reason'] for row in strict))


def _source_records(master):
    lights = {}
    for kind, flags, payload in records(master.read_bytes()):
        if kind != 'LIGH':
            continue
        fields = list(subrecords(payload)); identifier = text(fields, 'NAME').casefold()
        if flags & 0x20 or any(tag == 'DELE' for tag, _ in fields):
            lights.pop(identifier, None)
        else:
            lights[identifier] = fields
    if 'torch' not in lights:
        raise ValueError('Original torch light record missing')
    return lights


def _creature_ids(master):
    """Creature record IDs of the master: creatures placed as residents (Vivec) carry no torches."""
    found = set()
    for kind, flags, payload in records(master.read_bytes()):
        if kind == 'CREA':
            found.add(text(list(subrecords(payload)), 'NAME').casefold())
    return found


def _guard_models(id1, kinds, lights, mesh, creatures=frozenset()):
    # every map, CHIM frame maps (x.chim) included: town and region frames hold the exterior guards
    # (GUARD-TORCH-CHIM-FRAMES-44: a *.bsp-only scan found only interior guards since v0.0.36)
    found = _scan_guards(map_files(id1 / 'maps'), kinds, lights, mesh, creatures)
    check_record_count(len(found))
    return [found[key] for key in sorted(found)]


def check_record_count(count, when=''):
    """The engine's guard torch table holds MAX_RECORDS (AW_GUARD_TORCH_TYPES) records; more stops the build."""
    if count > MAX_RECORDS:
        raise ValueError('Too many distinct staged guard models: %d (guard source, model) records%s, the engine '
                         'holds %d' % (count, when, MAX_RECORDS))


def staged_guard_records(map_paths, data_files, unstamped=None):
    """{(source, model)} of the guards in MAP_PATHS, read only: the payload preflight counts them in the image step's
    first seconds (tools/payload_preflight.py check_guard_records, GUARD-TORCH-TYPES-LIMIT-48). UNSTAMPED, a list:
    NPCs with no aw_source_id yet are appended as (map, aw_ref) and skipped instead of refused; the image step stamps
    the scene maps' NPCs later (PREFLIGHT-GUARD-UNSTAMPED-NPCS-48: the census NPCs in v0.0.48-rc1)."""
    master = child_ci(Path(data_files), 'Morrowind.esm')
    kinds, _, _ = load_master(master)
    lights = _source_records(master)
    return set(_scan_guards(map_paths, kinds, lights, text(lights['torch'], 'MODL'), _creature_ids(master),
                            unstamped))


def _scan_guards(paths, kinds, lights, mesh, creatures=frozenset(), unstamped=None):
    found = {}
    for path in paths:
        with path.open('rb') as stream:
            header = stream.read(124)
            if len(header) != 124 or struct.unpack_from('<i', header)[0] != 29:
                raise ValueError('Invalid staged BSP: ' + path.name)
            start, size = struct.unpack_from('<2i', header, 4)
            if not 124 <= start <= path.stat().st_size or not 0 <= size <= path.stat().st_size-start:
                raise ValueError('Invalid staged BSP entities')
            stream.seek(start); entities = stream.read(size).decode('cp1252')
        for block in re.findall(r'\{[^{}]*\}', entities):
            ent = dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', block))
            if ent.get('classname') != 'aw_npc':
                continue
            source = ent.get('aw_source_id', '').casefold()
            # interior creature residents (tools/creature_residents.py, e.g. vivec_god) are aw_npc entities from
            # creature records: never guards, no torch (BUILD-TORCH-CREATURE-RESIDENT-42)
            if source not in kinds['NPC_'] and source in creatures:
                continue
            if not source and unstamped is not None:
                unstamped.append((path.name, ent.get('aw_ref', '')))
                continue
            if source not in kinds['NPC_']:
                raise ValueError('Staged NPC lacks original source identity: ' + path.name)
            guard, eligible, inventory = guard_eligibility(kinds['NPC_'][source], lights, mesh)
            if guard:
                model = safe_model(ent['model'])
                found[(source, model)] = {'source_id': source, 'base_model': model,
                    'auto_inventory_eligible': eligible, 'inventory': inventory}
    return found


class AuditedAssets(Assets):
    def __init__(self, data_files, archive):
        super().__init__(data_files, archive)
        self.inputs = {}
    def read(self, name):
        raw = super().read(name)
        self.inputs[normpath(name)] = sha(raw)
        return raw


def _body(assets, appearance, base, raw, palette, layout=None):
    """The held-torch body companion of a guard model. layout: the model's animation kit layout
    (<model>.anm) or None. The frame layout comes from tools/actor_frames.py: the previous 8 idle and
    21 town actor models get a companion of every frame; an animation kit model gets a companion of its
    idle group (frames 0..7: the engine draws the companion for those frames and the guard's own model,
    without the torch, for its other groups; ANIMKIT-ACTOR-ABI-SITES-35)."""
    original, faces, uv, skin = decode_mdl(raw)
    frame_layout = actor_frames.of_model(len(original), layout)
    extra = {}
    if frame_layout.kind == 'kit':
        # Kit idle poses are the base skeleton's idle cycle (npc_anim.plan: idle first, in place, no
        # override), exactly the previous 8-frame poses; the registry indexes the guard's own frames.
        idle_base, idle_count = frame_layout.idle
        if idle_base != 0 or idle_count != actor_frames.IDLE_FRAMES:
            raise ValueError('Guard animation kit layout must start with the 8-frame idle group')
        extra = {'base_frames': len(original), 'base_layout': 'kit idle %d:%d' % (idle_base, idle_count)}
        original = original[idle_base:idle_base+idle_count]
    count = len(original)
    if count == actor_frames.IDLE_FRAMES:
        normal = base; times, _ = base.idle_times(count); samples = None
    else:  # actor_frames.ACTOR_FRAMES (of_model refuses every other undeclared layout)
        override = Skeleton(assets, 'meshes/base_anim_female.nif') if appearance['female'] else None
        normal = ActorSkeleton(base, override)
        times, samples, _, _ = actor_samples(normal)
    layer = TorchLayer(base, normal, times)
    old_shapes, materials, textures = assemble(assets, appearance, normal, times, samples)
    held_shapes, _, _ = assemble(assets, appearance, layer, np.arange(count), samples)
    if len(old_shapes) != len(held_shapes):
        raise ValueError('Guard pose changed shape inventory')
    for old, held in zip(old_shapes, held_shapes):
        if (old['name'], old['part']) != (held['name'], held['part']) or not np.array_equal(old['faces'], held['faces']):
            raise ValueError('Guard pose changed original topology')
        old['positions'] = np.concatenate((old['positions'], held['positions']))
    header = struct.unpack_from('<4si3f3ff3f8if', raw)
    scale = np.array(header[2:5]); origin = np.array(header[5:8])
    positions, reproduction = _reproduce_base(old_shapes, materials, textures, palette, count, faces, uv, original,
                                              scale, origin, appearance)
    held_skin = Image.fromarray(skin, 'P'); held_skin.putpalette(palette)
    held = animated_mdl(positions[count:], faces, uv, held_skin)
    return held, layer, samples, {'frames': count, 'triangles': len(faces), 'vertices': original.shape[1],
        'base_geometry_reproduced_exactly': reproduction['coordinates_off'] == 0, 'base_reproduction': reproduction,
        'base_file_changed': False, 'skin_indices_preserved_exactly': True,
        **extra}


# A rebuilt base pose counts as the existing model when every coordinate is within MAX_STEP_OFF quantisation steps
# and at most MAX_SHARE_OFF of them differ at all: the boundary-locked head reducer reproduces a guard to within
# floating-point rounding (v0.0.44-dev1: chargen boat guard 2, 8 of 85,050 coordinates one step off in one frame).
MAX_STEP_OFF = 1
MAX_SHARE_OFF = 0.001


def _quantised_steps_off(positions, original, scale, origin):
    """(largest difference in quantisation steps, number of coordinates that differ) between the rebuilt positions
    and the existing model, or None when the shapes differ."""
    if positions.shape != original.shape:
        return None
    rebuilt = np.clip(np.rint((positions-origin)/scale), 0, 255)
    existing = np.rint((original-origin)/scale)
    off = np.abs(rebuilt-existing)
    return int(off.max()) if off.size else 0, int((off > 0).sum())


def _reproduce_base(shapes, materials, textures, palette, count, faces, uv, original, scale, origin, appearance):
    """The bake of the guard's held pose that reproduces its existing base model exactly. The base model may have
    been baked with either head reducer (npc_geometry._retry_head_reducer falls back to the previous one for an
    appearance the locked reducer leaves over budget), so both are tried, the configured one first; a budget too
    small for the guard's shapes is skipped, not fatal (v0.0.44-dev1 image step: 'Too many separate shapes for
    budget' stopped the guard torches; NPC-HEAD-DECIMATION-33). The error names the guard."""
    import os
    from mesh_geometry_env import NPC_HEAD_REDUCER_VARIABLE, npc_head_reducer
    from npc_geometry import bake, AliasOverflow
    configured = npc_head_reducer()
    saved = os.environ.get(NPC_HEAD_REDUCER_VARIABLE)
    tried = []
    try:
        for reducer in dict.fromkeys((configured, 'default')):
            os.environ[NPC_HEAD_REDUCER_VARIABLE] = reducer
            for budget in (480, 384, 320, 256, 192):
                try:
                    positions, candidate_faces, candidate_uv, _ = bake(shapes, materials, textures, palette,
                        budget=budget, reference_frames=count)
                except AliasOverflow:
                    # a candidate over the alias vertex budget is not the existing model either (v0.0.48-dev2 try12:
                    # this stopped the whole step for one guard; GUARD-TORCH-REBAKE-MISMATCH-48)
                    tried.append('%s/%d: over the alias vertex budget' % (reducer, budget))
                    continue
                except ValueError as error:
                    if str(error) != 'Too many separate shapes for budget':
                        raise
                    tried.append('%s/%d: too many shapes' % (reducer, budget))
                    continue
                if not np.array_equal(candidate_faces, faces) or not np.array_equal(candidate_uv, uv):
                    tried.append('%s/%d: faces or UV differ' % (reducer, budget))
                    continue
                steps = _quantised_steps_off(positions[:count], original, scale, origin)
                if steps is not None and steps[0] <= MAX_STEP_OFF and steps[1] <= MAX_SHARE_OFF * original.size:
                    if reducer != configured:
                        print('guard torches %s: base model reproduced with the previous head reducer'
                              % appearance.get('id', '?'), flush=True)
                    if steps[1]:
                        print('guard torches %s: base model reproduced within %d quantisation step(s): %d of %d '
                              'coordinates off (floating-point rounding)' % (appearance.get('id', '?'), steps[0],
                              steps[1], original.size), flush=True)
                    return positions, {'max_quant_steps_off': int(steps[0]), 'coordinates_off': int(steps[1])}
                tried.append('%s/%d: positions differ (%s)' % (reducer, budget,
                             'shape' if steps is None else 'max %d steps, %d coordinates' % steps))
    finally:
        if saved is None:
            os.environ.pop(NPC_HEAD_REDUCER_VARIABLE, None)
        else:
            os.environ[NPC_HEAD_REDUCER_VARIABLE] = saved
    raise BaseNotReproduced('Guard %s: source bake does not reproduce existing base geometry/UV exactly (%s)'
                     % (appearance.get('id', '?'), '; '.join(tried)))


def _equipment(assets, appearance, layer, samples, mesh, palette):
    part = {'slot': 10, 'attach': 'Shield Bone', 'filter': '', 'id': 'torch', 'mesh': mesh, 'carried_light': True}
    count = len(layer.times)
    shapes, materials, textures = assemble(assets, {**appearance, 'parts': [part]}, layer, np.arange(count), samples)
    shapes = [shape for shape in shapes if 'shadowbox' not in shape['name'].casefold()]
    protected = {shape['name']: len(shape['faces']) for shape in shapes}
    if sum(protected.values()) != 238:
        raise ValueError('Expected all 238 original visible torch triangles')
    # The vivid bank belongs to sky outputs, not newly converted world equipment.
    from sky_palette_overlay import BANK
    quant_palette = bytearray(palette)
    vivid = all(tuple(palette[index*3:index*3+3]) == target for index, (_, target) in BANK.items())
    if vivid:
        for index, (replacement, _) in BANK.items():
            quant_palette[index*3:index*3+3] = palette[replacement*3:replacement*3+3]
    positions, faces, uv, skin = bake(shapes, materials, textures, bytes(quant_palette), budget=sum(max(4,n) for n in protected.values()), minimum_faces=protected)
    if vivid:
        table = list(range(256))
        for index, (replacement, _) in BANK.items(): table[index] = replacement
        skin = skin.point(table)
    skin = skin.crop((0, 0, skin.width, ((len(faces)+31)//32)*16))
    equipment = animated_mdl(positions, faces, uv, skin)
    model = assets.models[normpath('meshes/'+mesh)]
    nodes = source_nodes(model, layer.N)
    offset = rigid_attachment(part, nodes['boneoffset'][0].translation.as_list())
    emitters = []
    first_root = layer.pose(0)('bip01')[3, :2]
    for index in range(count):
        pose = layer.pose(index)
        point = (nodes['fire emitter'][1] @ offset @ pose('Shield Bone'))[3, :3].copy()
        if samples is not None and index >= 13:
            point[:2] -= pose('bip01')[3, :2]-first_root
        emitters.append((point*np.array([appearance['weight'], appearance['weight'], appearance['height']])*.25).tolist())
    return equipment, emitters


GUARD_CACHE = 'guard-torch'


def _guard_cache():
    """The guard models' share of the image pass cache (tools/pass_cache.py), or None (cache off, or no input lock
    naming the game data by SHA-256: then the inputs are not known exactly and nothing is reused)."""
    from pass_cache import PassCache, game_data_digest
    game = game_data_digest()
    if game is None:
        return None
    return PassCache.open(GUARD_CACHE, {'game_data': game}, (__file__, '_convert_guard'))


def _convert_guard(task):
    """Pool worker: the held-torch body and torch companions of one guard model (prepare). Reads only.
    Returns bytes and the receipt fields; with a cache, a result recorded for the same inputs (SHA-256 of the
    base model, the palette, the appearance and the torch mesh name, the game data by the cache's options, the
    worker's code by its key) is taken from it, byte for byte."""
    data_files, id1, entry, appearance, mesh, palette, cache = task
    original = (Path(id1) / entry['base_model']).read_bytes()
    layout = actor_frames.layout_text(Path(id1) / entry['base_model'])
    key = None
    if cache is not None:
        from pass_cache import input_digest
        key = input_digest({'base': sha(original), 'layout': layout, 'palette': sha(palette), 'entry': entry,
                            'appearance': json.loads(json.dumps(appearance, default=str)), 'mesh': mesh})
        found = cache.load(key)
        if found is not None and found[1] is not None and isinstance(found[0], dict):
            row, blob = found
            cut = row['body_bytes']
            return dict(row, body=blob[:cut], equipment=blob[cut:], inputs=[tuple(i) for i in row['inputs']],
                        reused=True)
    assets = AuditedAssets(Path(data_files), BSA(child_ci(Path(data_files), 'Morrowind.bsa')))
    skeleton = Skeleton(assets, appearance['skeleton'])
    try:
        body, layer, samples, proof = _body(assets, appearance, skeleton, original, palette, layout)
    except BaseNotReproduced as error:
        return {'skipped': str(error), 'reused': False}
    equipment, emitters = _equipment(assets, appearance, layer, samples, mesh, palette)
    row = json.loads(json.dumps({'proof': proof, 'emitters': emitters, 'layer': [layer.start, layer.stop],
                                 'base_sha256': sha(original), 'inputs': list(assets.inputs.items()),
                                 'body_bytes': len(body)}))
    if cache is not None:
        cache.store(key, row, body + equipment)
    return dict(row, body=body, equipment=equipment, inputs=[tuple(i) for i in row['inputs']], reused=False)


def prepare(data_files, id1, output_id1=None, jobs=None):
    data_files = ensure_external(data_files, 'owned guard data')
    id1 = ensure_external(id1, 'guard source stage')
    output = ensure_external(output_id1 or id1, 'guard companion output')
    master = child_ci(data_files, 'Morrowind.esm')
    kinds, _, _ = load_master(master)
    lights = _source_records(master); mesh = text(lights['torch'], 'MODL')
    entries = _guard_models(id1, kinds, lights, mesh, _creature_ids(master))
    palette = (id1 / 'gfx/palette.lmp').read_bytes()
    if len(palette) != 768: raise ValueError('Invalid guard palette')
    # One guard model per worker of the shared pool, results in entry order (the image step's guard torches ran one
    # by one on one core); each kept in the image pass cache by the SHA-256 of its inputs.
    from build_parallel import ordered_map
    from build_jobs import resolve_jobs
    import build_profile
    import progress_line
    cache = _guard_cache()
    tasks = [(str(data_files), str(id1), entry, outfit(kinds, entry['source_id']), mesh, palette, cache)
             for entry in entries]
    jobs = max(1, min(resolve_jobs(jobs), len(tasks) or 1))
    files = {}; rows = []; inputs = {}; reused = 0; skipped = []
    with build_profile.phase('Guard torches', detail='%d models, %d workers' % (len(tasks), jobs),
                             total=len(tasks), unit='models') as timer:
        for (_, _, entry, appearance, *_), result in zip(tasks, ordered_map(_convert_guard, tasks, jobs)):
            if 'skipped' in result:
                skipped.append({'source_id': entry['source_id'], 'base_model': entry['base_model'],
                                'reason': result['skipped']})
                timer.step(label=entry['base_model'])
                print('WARNING: guard torch skipped (no torch for this guard):', entry['source_id'],
                      entry['base_model'], '-', result['skipped'], flush=True)
                continue
            body, equipment = result['body'], result['equipment']
            body_path = 'progs/gt_b_'+sha(body)[:12]+'.mdl'
            equipment_path = 'progs/gt_t_'+sha(equipment)[:12]+'.mdl'
            files[body_path] = body; files[equipment_path] = equipment
            for name, value in result['inputs']:
                inputs.setdefault(name, value)
            rows.append({**entry, **result['proof'], 'body_model': body_path, 'torch_model': equipment_path,
                'base_sha256': result['base_sha256'], 'emitters': result['emitters'],
                'body_bytes': len(body), 'torch_bytes': len(equipment), 'source_class': appearance['class'],
                'source_skeleton': appearance['skeleton'], 'source_torch_key_seconds': result['layer']})
            reused += result['reused']
            timer.step(label=entry['base_model'])
            print('Guard torch prepared:', entry['source_id'], entry['base_model'], flush=True)
            build_profile.progress(progress_line.line('Guard torches', entry['base_model'],
                                                      'reused' if result['reused'] else 'made',
                                                      (timer.count, timer.total, 'models')))
        timer.done('Guard torches: %d models (%d from the pass cache, %d skipped)' % (len(rows), reused, len(skipped)))
    check_skips(skipped)
    files['gfx/guard-torches.awg'] = registry(rows)
    report = {'format': 'AmiWind original guard torch companions 1', 'registry': 'gfx/guard-torches.awg',
        'source_classes': sorted(GUARD_CLASSES), 'source_mesh': mesh, 'source_torch_triangles': 238,
        'source_master_sha256': sha(master.read_bytes()), 'source_assets': inputs,
        'palette_sha256': sha(palette), 'records': rows, 'record_count': len(rows), 'skipped': skipped,
        'unique_body_models': len({row['body_model'] for row in rows}),
        'unique_torch_models': len({row['torch_model'] for row in rows}),
        'unique_asset_bytes': sum(map(len, files.values())),
        'max_one_guard_companion_file_bytes': max((row['body_bytes']+row['torch_bytes'] for row in rows), default=0),
        'memory_note': 'File bytes only; native alias cache allocations require matching loader accounting. Assets are loaded on demand.',
        'frame_abi': 'Same 8 idle or 21 idle/talk/blink/walk frames as each source model',
        'pose': 'Original third-person left clavicle descendants only; Shield Bone, -90X carried-light convention, no camera offset',
        'base_models_and_maps_unchanged': True, 'native_acceptance': False,
        'files': {name: {'bytes': len(raw), 'sha256': sha(raw)} for name, raw in sorted(files.items())}}
    # Validate all conversions before installing any companion. Existing mismatched
    # content is an error; preserve prior assets and receipts for explicit review.
    report_path = output / 'gfx/guard-torches.json'
    report_raw = (json.dumps(report, indent=2)+'\n').encode('utf-8')
    files['gfx/guard-torches.json'] = report_raw
    for name, raw in files.items():
        path = output / name
        if path.exists() and path.read_bytes() != raw:
            raise ValueError('Existing guard asset differs; preserved: '+name)
    for name, raw in files.items():
        path = output / name; path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists(): path.write_bytes(raw)
    return report


def fingerprint_entries(read_optional):
    """Append optional presentation identities after the legacy save namespace.

    read_optional(relative_name) returns bytes or None. Both the normal image
    pipeline and sparse immutable-image assembly use this identical ordering.
    """
    result = []
    night = read_optional('gfx/aw_night_sky.lmp')
    if night is not None:
        result.append(('gfx/aw_night_sky.lmp', sha(night)))
    packet = read_optional('gfx/guard-torches.awg')
    manifest = read_optional('gfx/guard-torches.json')
    if packet is None and manifest is None:
        return result
    if packet is None or manifest is None:
        raise ValueError('Guard fingerprint requires registry and manifest together')
    report = json.loads(manifest)
    if report.get('format') != 'AmiWind original guard torch companions 1':
        raise ValueError('Unsupported guard fingerprint manifest')
    rows = report['records']
    if registry(rows) != packet:
        raise ValueError('Guard registry differs from its manifest')
    models = sorted({safe_model(row[key]) for row in rows for key in ('body_model', 'torch_model')})
    if set(report['files']) != {'gfx/guard-torches.awg', *models}:
        raise ValueError('Guard manifest has unexpected or missing declared assets')
    result.append(('gfx/guard-torches.json', sha(manifest)))
    for name in ['gfx/guard-torches.awg', *models]:
        raw = packet if name == 'gfx/guard-torches.awg' else read_optional(name)
        expected = report['files'][name]
        if raw is None or len(raw) != expected['bytes'] or sha(raw) != expected['sha256']:
            raise ValueError('Guard fingerprint asset mismatch: '+name)
        result.append((name, sha(raw)))
    for row in rows:
        original = read_optional(safe_model(row['base_model']))
        if original is None or sha(original) != row['base_sha256']:
            raise ValueError('Guard companion does not match its base model')
    return result
