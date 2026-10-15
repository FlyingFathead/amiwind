#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Bake bounded first-person block arms and source Shield Bone view tags.

The equipment stays a separate actual inventory model. This tool grants no
items and never substitutes a shield for an unsupported equipped object.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import numpy as np
from mwad.audit import BSA
from mwad.npc import first, load_master
from mwad.paths import child_ci
from npc_anim import BoneLayer
from npc_geometry import Assets, Skeleton, animated_mdl
from npc_items import view_tags
from prepare_hands import appearance_parts
from prepare_hand_catalog import model_paths
from prepare_torch import camera_space, view_parts


BLOCK_FRAMES = 8

def block_times(events):
    a, h, b = (events['shield: block ' + k] for k in ('start', 'hit', 'stop'))
    if not np.isfinite((a, h, b)).all() or not a < h < b or not 0 < b-a <= 10:
        raise ValueError('Invalid original first-person block keys')
    # Preserve the exact guarding pose; the five later samples play recovery.
    return np.array([a, (a+h)/2, h, *np.linspace(h, b, 6)[1:]]), (a, h, b)


class BlockSkeleton:
    """The original left-arm block over a stable authored one-handed idle.

    A raw whole-skeleton block sample also changes Camera and the right arm.
    BoneLayer retains the idle hierarchy outside the source left-arm mask,
    following the original left-arm animation priority and the torch baker.
    """
    def __init__(self, base):
        self.N = base.N
        self.base = base
        self.normal = base.pose(base.events['idle1h: start'])
        self.layer = BoneLayer(base, ('bip01 l clavicle',))

    def pose(self, time):
        return self.layer.pose(self.normal, time)


def pack_metadata(entries, times, keys, tags):
    a, h, b = keys
    offsets = np.rint((np.asarray(times)-a)*1000).astype(int)
    duration, hit = round((b-a)*1000), round((h-a)*1000)
    tags = np.asarray(tags, float)
    if (len(entries) < 1 or len(entries) > 32 or tags.shape != (BLOCK_FRAMES, 6)
            or not np.isfinite(tags).all() or np.max(abs(tags[:, :3])) > 128
            or np.max(abs(tags[:, 3:])) > 720 or len(offsets) != BLOCK_FRAMES
            or offsets[0] != 0 or offsets[-1] != duration
            or not np.all(np.diff(offsets) > 0) or hit not in offsets):
        raise ValueError('Block metadata outside runtime bounds')
    raw = bytearray(struct.pack('>4sHHII', b'AWB1', len(entries), 132, duration, hit))
    for time, tag in zip(offsets, tags):
        raw.extend(struct.pack('>I6i', int(time), *np.rint(tag*65536).astype(int)))
    seen = set()
    for race, female, path in entries:
        if type(female) is not bool or race != race.casefold() or (race, female) in seen:
            raise ValueError('Duplicate or invalid block appearance')
        seen.add((race, female))
        expected = model_paths(race, female)[0][:-4] + '_b.mdl'
        if path != expected or len(race.encode('ascii')) > 63 or len(path) > 63:
            raise ValueError('Invalid block appearance path')
        raw.extend(race.encode('ascii').ljust(64, b'\0'))
        raw.extend(struct.pack('>I', int(female)))
        raw.extend(path.encode('ascii').ljust(64, b'\0'))
    return bytes(raw)


def prepare(data_files, id1, palette_path, races=()):
    from hand_geometry import bake_source_hands
    from prepare_hand_normals import normal_table, rewrite
    import npc_geometry
    data_files, id1 = Path(data_files), Path(id1)
    palette = Path(palette_path).read_bytes()
    if len(palette) != 768:
        raise ValueError('Expected installed 256-colour palette')
    kinds, _, _ = load_master(child_ci(data_files, 'Morrowind.esm'))
    assets = Assets(data_files, BSA(child_ci(data_files, 'Morrowind.bsa')))
    base = Skeleton(assets, 'meshes/base_anim.1st.nif')
    skeleton = BlockSkeleton(base)
    times, keys = block_times(base.events)
    camera = skeleton.pose(float(times[0]))('Camera')[3, :3] * .25
    tags = np.array(view_tags(skeleton, times, camera, {'weapon': None, 'shield': True}))[:, 6:]
    tags[:, 0] += 4  # Same whole-assembly near-plane adaptation as the torch.
    playable = sorted(name for name, row in kinds['RACE'].items()
                      if len(first(row, 'RADT')) >= 20 and
                      struct.unpack_from('<I', first(row, 'RADT'), len(first(row, 'RADT'))-4)[0] & 1)
    if races:
        if any(r not in playable for r in races):
            raise ValueError('Unknown playable block appearance')
        playable = [r for r in playable if r in races]
    table = normal_table(Path(npc_geometry.__file__).resolve().parents[1] / 'engine/aga/src/anorms.h')
    entries, reports = [], []
    for race in playable:
        for female in (False, True):
            parts = view_parts(appearance_parts(kinds, race, female), 'hidden')
            shapes, materials, textures = npc_geometry.assemble(
                assets, {'parts': parts, 'weight': 1, 'height': 1}, skeleton, times)
            for shape in shapes:
                shape['positions'] = camera_space(shape['positions'], camera)
            frames, faces, uv, skin = bake_source_hands(shapes, materials, textures, palette)
            raw = animated_mdl(frames, faces, uv, skin, vertex_limit=1999,
                               names=['block%02d' % i for i in range(BLOCK_FRAMES)])
            raw, normals = rewrite(raw, table)
            if len(raw) > 512*1024 or len(frames) != BLOCK_FRAMES:
                raise ValueError('Block arms exceed existing alias staging budget')
            path = model_paths(race, female)[0][:-4] + '_b.mdl'
            out = id1 / path
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(raw)
            entries.append((race, female, path))
            reports.append({'race': race, 'female': female, 'model': path,
                            'frames': BLOCK_FRAMES, 'vertices': len(frames[0]), 'triangles': len(faces),
                            'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                            'parts': parts, 'lighting_normals': normals})
    metadata = pack_metadata(entries, times, keys, tags)
    out = id1 / 'gfx/block-models.awb'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(metadata)
    return {'source': 'meshes/base_anim.1st.nif', 'source_keys': list(keys),
            'source_sha256': hashlib.sha256(assets.read('meshes/base_anim.1st.nif')).hexdigest(),
            'times': times.tolist(), 'camera': camera.tolist(), 'shield_tags': tags.tolist(),
            'appearances': reports, 'metadata_sha256': hashlib.sha256(metadata).hexdigest(),
            'palette_sha256': hashlib.sha256(palette).hexdigest(),
            'scope': 'Source conversion only; actual equipped shield is supplied by inventory; native verification pending'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--id1', type=Path, required=True)
    p.add_argument('--palette', type=Path, required=True)
    p.add_argument('--race', action='append', default=[])
    p.add_argument('--report', type=Path, required=True)
    a = p.parse_args()
    report = prepare(a.data_files, a.id1, a.palette, a.race)
    a.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
