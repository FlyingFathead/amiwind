#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Convert owned character records and bounded head previews; no game data here."""
import argparse
import json
import math
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.audit import BSA, records, subrecords, string, cell_data
from mwad.paths import ensure_external, resolve_data_files, child_ci
from prepare_quake import CENTRE


from build_jobs import add_jobs, resolve_jobs
from build_parallel import ordered_map
from known_inputs import input_sha256


def fixed(text, size):
    raw = text.encode('cp1252')
    if not raw or len(raw) >= size or b'\0' in raw:
        raise ValueError('Invalid bounded character string: ' + text)
    return raw.ljust(size, b'\0')


def catalogue(master, eye_base=None):
    kinds = {k: {} for k in ('RACE', 'BODY', 'CLAS', 'BSGN', 'SPEL', 'SKIL')}
    player = None
    for tag, flags, raw in records(Path(master).read_bytes()):
        if tag == 'NPC_' and eye_base is not None:
            f = dict(subrecords(raw))
            if string(f.get('NAME', b'')).casefold() == 'player':
                player = f
        if tag not in kinds or flags & 0x20:
            continue
        fields = list(subrecords(raw)); f = dict(fields)
        if 'DELE' in f:
            continue
        key = struct.unpack('<i', f['INDX'])[0] if tag == 'SKIL' else string(f['NAME']).casefold()
        kinds[tag][key] = fields
    races = sorted((k, dict(v)) for k, v in kinds['RACE'].items()
                   if struct.unpack_from('<I', dict(v)['RADT'], 136)[0] & 1)
    classes = sorted((k, dict(v)) for k, v in kinds['CLAS'].items()
                     if struct.unpack_from('<I', dict(v)['CLDT'], 52)[0] & 1)
    births = sorted((k, dict(v)) for k, v in kinds['BSGN'].items())
    race_index = {name: i for i, (name, _) in enumerate(races)}
    parts = []
    for name, fields in sorted(kinds['BODY'].items()):
        f = dict(fields); part, vampire, flags, kind = f['BYDT']
        race = string(f.get('FNAM', b'')).casefold()
        if race not in race_index or part > 1 or vampire or kind != 0 or flags & 2 or name.endswith('.1st'):
            continue
        parts.append({'id': name, 'race': race_index[race], 'female': flags & 1,
                      'kind': part, 'model': string(f['MODL'])})
    if not (0 < len(races) <= 16 and 0 < len(classes) <= 32 and
            0 < len(births) <= 16 and 0 < len(parts) <= 384):
        raise ValueError('Character catalogue exceeds runtime limits')
    for ri in range(len(races)):
        for sex in (0, 1):
            for part in (0, 1):
                if not any(p['race'] == ri and p['female'] == sex and p['kind'] == part for p in parts):
                    raise ValueError('Missing playable appearance choices')

    def bonuses(fields):
        attrs = [0] * 8; magicka = 0
        powers = [string(v).casefold() for tag, v in fields if tag == 'NPCS']
        if len(powers) > 16:
            raise ValueError('Power list limit exceeded')
        for power in powers:
            spell = kinds['SPEL'][power]
            if struct.unpack_from('<i', dict(spell)['SPDT'])[0] != 1:
                continue  # Only permanent abilities modify starting values.
            for tag, effect in spell:
                if tag != 'ENAM':
                    continue
                effect_id, skill, attribute, rang, area, duration, low, high = struct.unpack('<HBBiiiii', effect)
                if low != high and effect_id in (79, 84):
                    raise ValueError('Variable starting stat ability is unsupported')
                if effect_id == 79 and attribute < 8:
                    attrs[attribute] += low
                if effect_id == 84:
                    magicka += low
        return attrs, magicka, powers

    special = [struct.unpack_from('<i', dict(kinds['SKIL'][i])['SKDT'], 4)[0] for i in range(27)]
    raw = bytearray(struct.pack('<4s4H27B1x32s', b'AWC1', len(races), len(classes), len(births), len(parts),
                                *special, bytes.fromhex(input_sha256(master))))
    def powers_bytes(powers):
        return bytes([len(powers)]) + b''.join(fixed(p, 64) for p in powers)
    for identifier, f in races:
        data = f['RADT']; attrs = struct.unpack_from('<16i', data, 56); skills = [0] * 27
        for skill, bonus in struct.iter_unpack('<ii', data[:56]):
            if skill >= 0:
                skills[skill] = bonus
        extra, magicka, powers = bonuses(kinds['RACE'][identifier])
        raw += struct.pack('<64s48s16B27B8hH', fixed(identifier, 64), fixed(string(f['FNAM']), 48),
                           *attrs, *skills, *extra, magicka) + powers_bytes(powers)
    for identifier, f in classes:
        a, b, spec, *skills = struct.unpack('<13i', f['CLDT'][:52])
        raw += struct.pack('<64s48s13B', fixed(identifier, 64), fixed(string(f['FNAM']), 48), a, b, spec, *skills)
    for identifier, f in births:
        extra, magicka, powers = bonuses(kinds['BSGN'][identifier])
        raw += struct.pack('<64s48s8hH', fixed(identifier, 64), fixed(string(f['FNAM']), 48), *extra, magicka)
        raw += powers_bytes(powers)
    for part in parts:
        raw += struct.pack('<64s3Bx', fixed(part['id'], 64), part['race'], part['female'], part['kind'])
    eyes = {}
    if eye_base is not None:
        if player is None or not math.isfinite(eye_base) or not 8 <= eye_base <= 60:
            raise ValueError('Missing source player or invalid sampled camera height')
        default_race = race_index[string(player['RNAM']).casefold()]
        default_female = struct.unpack('<I', player['FLAG'])[0] & 1
        raw += struct.pack('<4sBB', b'AWE1', default_race, default_female)
        for identifier, f in races:
            heights = struct.unpack_from('<2f', f['RADT'], len(f['RADT']) - 20)
            values = [round(eye_base * h * 1000) for h in heights]
            if not all(math.isfinite(h) and .5 <= h <= 2 for h in heights) or not all(8000 <= v <= 60000 for v in values):
                raise ValueError('Invalid race eye height: ' + identifier)
            raw += struct.pack('<2H', *values)
            eyes[identifier] = [v / 1000 for v in values]
    return bytes(raw), parts, {'races': [x[0] for x in races], 'classes': [x[0] for x in classes],
                              'birthsigns': [x[0] for x in births], 'skill_specializations': special,
                              'eye_above_feet': eyes, 'camera_base': eye_base}


def barriers(master):
    import numpy as np
    boxes = []
    for tag, flags, raw in records(Path(master).read_bytes()):
        if tag != 'CELL':
            continue
        cell = cell_data(list(subrecords(raw)))
        if cell['flags'] & 1:
            continue
        for ref in cell['refs']:
            if ref['id'].casefold() != 'chargencollision - extra' or ref.get('deleted'):
                continue
            # EditorMarker_box_01 collision hull; its full source rotation is
            # required. The marker artwork is deliberately never exported.
            rx, ry, rz = [-v for v in ref['rotation_radians']]
            cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
            # TES3 placed objects apply Z, then Y, then X to column vectors.
            # OpenMW Misc::Convert::makeOsgQuat uses that order (OSG's
            # quaternion product is reversed relative to Hamilton products).
            # Rz @ Ry @ Rx turns the ship's angled side walls across the plank.
            rotation = (np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]]) @
                        np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]]) @
                        np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]]))
            pos = [(ref['position'][i] - (CENTRE[i] if i < 2 else 0)) * .25 for i in range(3)]
            half = [v * ref.get('scale', 1) for v in (32, 32, 8)]
            boxes.append((ref['number'], struct.pack('<15f', *pos, *rotation.T.flat, *half)))
    if not 0 < len(boxes) <= 32:
        raise ValueError('Unexpected chargen collision count')
    return struct.pack('<4sH', b'AWB1', len(boxes)) + b''.join(x[1] for x in boxes), [x[0] for x in boxes]


def exterior_navigation(master):
    grids = []
    for tag, flags, raw in records(Path(master).read_bytes()):
        if tag != 'PGRD':
            continue
        f = dict(subrecords(raw))
        if string(f.get('NAME', b'')).casefold() != 'seyda neen':
            continue
        x, y = struct.unpack_from('<ii', f['DATA'])
        points = list(struct.iter_unpack('<iiiBBH', f['PGRP']))
        edges = [v[0] for v in struct.iter_unpack('<i', f['PGRC'])]
        grids.append((x, y, points, edges))
    total = sum(len(g[2]) for g in grids)
    if not 0 < total <= 128:
        raise ValueError('Exterior path grid limit')
    out = bytearray(struct.pack('<4sH', b'AWN1', total)); base = 0
    for gx, gy, points, edges in grids:
        at = 0
        for x, y, z, auto, count, pad in points:
            out += struct.pack('<3fH', (x+gx*8192-CENTRE[0])*.25, (y+gy*8192-CENTRE[1])*.25, z*.25, count)
            for edge in edges[at:at+count]:
                if not 0 <= edge < len(points):
                    raise ValueError('Invalid exterior path edge')
                out += struct.pack('<H', base+edge)
            at += count
        if at != len(edges):
            raise ValueError('Exterior path edge count')
        base += len(points)
    # Source grids remain distinct: never invent inter-cell edges through walls.
    return bytes(out)


def head_preview(assets, skeleton, part, palette):
    import numpy as np
    from npc_geometry import assemble, bake
    time = float(skeleton.idle_times(1)[0][0])
    appearance = {'weight': 1., 'height': 1., 'parts': [
        {'mesh': part['model'], 'slot': part['kind'], 'filter': 'head' if not part['kind'] else 'hair', 'attach': 'Head'}]}
    shapes, materials, textures = assemble(assets, appearance, skeleton, [time])
    anchor = skeleton.pose(time)('Head')[3, :3] * .25
    for shape in shapes:
        shape['positions'] -= anchor
    frames, faces, uv, skin = bake(shapes, materials, textures, palette, budget=320)
    points = np.rint(frames[0] * 512)
    if not np.isfinite(points).all() or np.max(abs(points)) > 32767:
        raise ValueError('Preview vertex range')
    raw = bytearray(struct.pack('<4sH', b'AWH1', len(faces)))
    # Bake emits three unique vertices per face, and one 16x16 atlas tile.
    for i in range(len(faces)):
        triangle = points[i*3:i*3+3].astype('<i2')
        patch = skin.crop((i%32*16, i//32*16, i%32*16+16, i//32*16+16)).resize((8, 8), resample=0)
        raw += triangle.tobytes() + patch.tobytes()
    return bytes(raw)


_preview_context = None


def _head(task):
    global _preview_context
    data_files, part, palette = task
    from npc_geometry import Assets, Skeleton
    if _preview_context is None or _preview_context[0] != data_files:
        assets = Assets(data_files, BSA(child_ci(data_files, 'Morrowind.bsa')))
        _preview_context = (data_files, assets, Skeleton(assets))
    return head_preview(_preview_context[1], _preview_context[2], part, palette)


def prepare(data_files, scene, previews=True, jobs=None):
    from npc_geometry import Assets, Skeleton
    data_files = resolve_data_files(data_files); scene = ensure_external(scene, 'character conversion')
    master = child_ci(data_files, 'Morrowind.esm')
    dest = scene/'id1/character'; dest.mkdir(exist_ok=True)
    assets = Assets(data_files, BSA(child_ci(data_files, 'Morrowind.bsa')))
    first_person = Skeleton(assets, 'meshes/base_anim.1st.nif')
    # Ordinary standing idle, independent of the Nord hand-to-hand fixture.
    eye_base = float(first_person.pose(first_person.events['idle: start'])('Camera')[3, 2]) * .25
    raw, parts, report = catalogue(master, eye_base)
    (dest/'catalog.awc').write_bytes(raw)
    raw, refs = barriers(master); (scene/'id1/intro/barriers.awb').write_bytes(raw)
    (scene/'id1/intro/seyda.awn').write_bytes(exterior_navigation(master))
    if previews:
        palette = (scene/'id1/gfx/palette.lmp').read_bytes()
        workers=min(resolve_jobs(jobs),len(parts));print(f'Character preview workers: {workers}',flush=True)
        tasks=((data_files,part,palette) for part in parts)
        for i, raw in enumerate(ordered_map(_head,tasks,workers)):
            part=parts[i]
            (dest/f'h{i:03d}.awh').write_bytes(raw)
            print(f'Head preview {i+1}/{len(parts)}: {part["id"]}', flush=True)
    report.update(parts=parts, barriers=refs, master_sha256=input_sha256(master))
    (scene/'character-conversion.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-files', type=Path, required=True)
    parser.add_argument('--scene', type=Path, required=True)
    parser.add_argument('--no-previews', action='store_true')
    add_jobs(parser)
    args = parser.parse_args()
    prepare(args.data_files, args.scene, not args.no_previews, args.jobs)
