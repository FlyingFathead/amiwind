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
from prepare_hand_sprites import decode_mdl
from prepare_torch import source_nodes
import actor_frames

GUARD_CLASSES = frozenset(('guard', 'ordinator guard'))
MAX_RECORDS = 32
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
        raise ValueError('Guard registry exceeds bounded record count')
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

    def pose(self, time):
        index = int(time)
        if index != time or not 0 <= index < len(self.times):
            raise ValueError('Invalid guard pose sample')
        normal = self.normal.pose(float(self.times[index]))
        phase = index if index < 8 else index-13 if index >= 13 else 0
        torch_time = self.start + phase/8*(self.stop-self.start)
        matrices, left = {}, {}
        def is_left(name):
            if name not in left:
                parent = self.base.parents[name]
                left[name] = name == 'bip01 l clavicle' or bool(parent and is_left(parent))
            return left[name]
        def world(name):
            name = name.casefold()
            if name not in matrices:
                if is_left(name):
                    parent = self.base.parents[name]
                    up = world(parent) if parent else np.eye(4)
                    matrices[name] = self.base.local(name, torch_time) @ up
                else:
                    # Female walk override has a different file-root name.
                    # Unchanged bones use its complete original world pose.
                    matrices[name] = normal(name)
            return matrices[name]
        return world


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


def _guard_models(id1, kinds, lights, mesh):
    found = {}
    for path in sorted((id1 / 'maps').glob('*.bsp')):
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
            if source not in kinds['NPC_']:
                raise ValueError('Staged NPC lacks original source identity: ' + path.name)
            guard, eligible, inventory = guard_eligibility(kinds['NPC_'][source], lights, mesh)
            if guard:
                model = safe_model(ent['model'])
                found[(source, model)] = {'source_id': source, 'base_model': model,
                    'auto_inventory_eligible': eligible, 'inventory': inventory}
    if len(found) > MAX_RECORDS:
        raise ValueError('Too many distinct staged guard models')
    return [found[key] for key in sorted(found)]


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
    for budget in (480, 384, 320, 256, 192):
        positions, candidate_faces, candidate_uv, _ = bake(old_shapes, materials, textures, palette,
            budget=budget, reference_frames=count)
        if not np.array_equal(candidate_faces, faces) or not np.array_equal(candidate_uv, uv):
            continue
        rebaked = np.clip(np.rint((positions[:count]-origin)/scale), 0, 255)*scale+origin
        if rebaked.shape == original.shape and np.array_equal(rebaked, original):
            break
    else:
        raise ValueError('Guard source bake does not reproduce existing base geometry/UV exactly')
    held_skin = Image.fromarray(skin, 'P'); held_skin.putpalette(palette)
    held = animated_mdl(positions[count:], faces, uv, held_skin)
    return held, layer, samples, {'frames': count, 'triangles': len(faces), 'vertices': original.shape[1],
        'base_geometry_reproduced_exactly': True, 'base_file_changed': False, 'skin_indices_preserved_exactly': True,
        **extra}


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


def prepare(data_files, id1, output_id1=None):
    data_files = ensure_external(data_files, 'owned guard data')
    id1 = ensure_external(id1, 'guard source stage')
    output = ensure_external(output_id1 or id1, 'guard companion output')
    master = child_ci(data_files, 'Morrowind.esm')
    kinds, _, _ = load_master(master)
    lights = _source_records(master); mesh = text(lights['torch'], 'MODL')
    entries = _guard_models(id1, kinds, lights, mesh)
    palette = (id1 / 'gfx/palette.lmp').read_bytes()
    if len(palette) != 768: raise ValueError('Invalid guard palette')
    assets = AuditedAssets(data_files, BSA(child_ci(data_files, 'Morrowind.bsa')))
    skeletons = {}; files = {}; rows = []
    for entry in entries:
        appearance = outfit(kinds, entry['source_id'])
        rig = appearance['skeleton']
        if rig not in skeletons: skeletons[rig] = Skeleton(assets, rig)
        original = (id1 / entry['base_model']).read_bytes()
        body, layer, samples, proof = _body(assets, appearance, skeletons[rig], original, palette,
            actor_frames.layout_text(id1 / entry['base_model']))
        equipment, emitters = _equipment(assets, appearance, layer, samples, mesh, palette)
        body_path = 'progs/gt_b_'+sha(body)[:12]+'.mdl'
        equipment_path = 'progs/gt_t_'+sha(equipment)[:12]+'.mdl'
        files[body_path] = body; files[equipment_path] = equipment
        rows.append({**entry, **proof, 'body_model': body_path, 'torch_model': equipment_path,
            'base_sha256': sha(original), 'emitters': emitters,
            'body_bytes': len(body), 'torch_bytes': len(equipment), 'source_class': appearance['class'],
            'source_skeleton': rig, 'source_torch_key_seconds': [layer.start, layer.stop]})
        print('Guard torch prepared:', entry['source_id'], entry['base_model'], flush=True)
    files['gfx/guard-torches.awg'] = registry(rows)
    report = {'format': 'AmiWind original guard torch companions 1', 'registry': 'gfx/guard-torches.awg',
        'source_classes': sorted(GUARD_CLASSES), 'source_mesh': mesh, 'source_torch_triangles': 238,
        'source_master_sha256': sha(master.read_bytes()), 'source_assets': assets.inputs,
        'palette_sha256': sha(palette), 'records': rows, 'record_count': len(rows),
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
