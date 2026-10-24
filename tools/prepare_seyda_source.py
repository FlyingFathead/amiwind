# SPDX-License-Identifier: GPL-3.0-only
"""Non-runtime Seyda entity/model-box transport; never compile owned town terrain.

The normal intro/area/opening passes edit a BSP entity lump. This transport
contains their source rows and model-local bounds only. CHIM owns all rendered
and standing geometry; chim_town consumes the rows and builds real frame maps.
"""
import hashlib
import json
import math
from pathlib import Path
import re
import struct

FORMAT = 'AmiWind Seyda source carrier 1'
MARKER = 'metadata-only-1'


def source_points(text):
    """Point rows and world fields from canonical MAP source, ignoring brushes.

    Quoted strings use the project's non-escaping MAP convention. Refuse an
    unfamiliar nested point entity rather than silently stripping its geometry.
    """
    from prepare_npcs import quote
    depth = 0
    rows = []
    row = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('//'):
            continue
        if line == '{':
            depth += 1
            if depth == 1:
                row = {}
            elif depth != 2:
                raise ValueError('Malformed source MAP nesting')
        elif line == '}':
            if depth == 2 and row.get('classname') != 'worldspawn':
                raise ValueError('Brush point entity in source-only MAP')
            depth -= 1
            if depth < 0:
                raise ValueError('Malformed source MAP nesting')
            if depth == 0:
                rows.append(row)
        elif depth == 1:
            match = re.fullmatch(r'"([^"\n]+)"\s+"([^"\n]*)"', line)
            if match is None or match[1] in row:
                raise ValueError('Malformed or duplicate source MAP field')
            quote(match[1]); quote(match[2])
            row[match[1]] = match[2]
        elif depth != 2:
            raise ValueError('Source MAP content outside entity')
    if depth or not rows or rows[0].get('classname') != 'worldspawn' or \
            sum(r.get('classname') == 'worldspawn' for r in rows) != 1:
        raise ValueError('Source MAP needs exactly one leading worldspawn')
    kept = []
    for row in rows:
        if row.get('classname') == 'aw_static':
            model = row.get('model', '')
            if model.endswith('.mdl'):
                continue  # same alias-mesh removal as prepare_mesh_bsp.prepare
            if not model.endswith('.spr'):
                raise ValueError('Unknown source alias representation')
        kept.append(row)
    kept[0].pop('wad', None)
    from player_hull import PROFILE
    if kept[0].get('aw_hull', PROFILE) != PROFILE:
        raise ValueError('Source MAP standing-hull profile differs')
    kept[0]['aw_hull'] = PROFILE  # same world field as the normal standing-hull writer
    kept[0]['aw_source_carrier'] = MARKER
    return kept


def checked_refs(index, selected):
    """Identity/transform validation before any source carrier output writes."""
    seen = set()
    for ref in selected:
        number = ref.get('number')
        if not isinstance(number, int) or isinstance(number, bool) or number <= 0 or number in seen:
            raise ValueError('Malformed or duplicate source reference')
        seen.add(number)
        mi = ref.get('model_index')
        if not isinstance(mi, int) or not 0 <= mi < len(index['models']):
            raise ValueError('Source reference model index out of range')
        for key in ('position', 'rotation_radians'):
            v = ref.get(key, ())
            if len(v) != 3 or not all(math.isfinite(float(x)) for x in v):
                raise ValueError('Malformed source placement transform')
        if not math.isfinite(float(ref.get('scale', 0))) or ref['scale'] <= 0:
            raise ValueError('Malformed source placement scale')
        if not ref.get('id') or not ref.get('type'):
            raise ValueError('Missing original source identity/type')


def model_row(low, high):
    """A model record used solely by existing selection and activation readers."""
    if len(low) != 3 or len(high) != 3 or not all(math.isfinite(float(v)) for v in (*low, *high)) or \
            any(a > b for a, b in zip(low, high)):
        raise ValueError('Malformed source model-local bounds')
    return struct.pack('<9f7i', *low, *high, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)


def seed(scene, scenery, barrel, opening_source=None, jobs=1):
    """Build source-only transport from actual fresh alias/scenery inputs.

    The optional opening source is the CHIM builder's canonical original barrel
    export. It is required when the normal scenery selection does not contain
    that reference; no old town or mesh-append fallback is permitted.
    """
    import numpy as np
    from chim.seyda import placements
    from chim.frame_map import empty_world, entity_text
    from compact_bsp import entities
    from prepare_mesh_bsp import (_prepare_model, placement_metadata, placement_entity, flame_entities)
    from prepare_quake import CENTRE, SCALE
    from player_hull import pack_lumps
    from static_lod import rock_profile
    from surface_flatten import mount_references
    from visual_offsets import apply_visual_offsets
    scene, scenery = Path(scene), Path(scenery)
    rows = source_points((scene / 'seyda.map').read_text(encoding='cp1252'))
    index = json.loads((scenery / 'scenery-index.json').read_text())
    if index.get('errors'):
        raise ValueError('Fresh source scenery has conversion errors')
    checked_refs(index, index['references'])
    selected, selection, profiles = placements(index)
    checked_refs(index, selected)
    sources = [(index, selected, profiles, scenery / 'scenery.mwpak')]
    input_paths = [scene / 'seyda.map', scenery / 'scenery-index.json', scenery / 'scenery.mwpak']
    if barrel['number'] not in {r['number'] for r in selected}:
        if opening_source is None:
            raise ValueError('Original tutorial barrel requires the CHIM opening source')
        root = Path(opening_source)
        extra = json.loads((root / 'scenery-index.json').read_text())
        refs = extra['references']
        checked_refs(extra, refs)
        if len(refs) != 1 or any(refs[0].get(k) != barrel.get(k) for k in
                                ('number', 'id', 'type', 'position', 'rotation_radians', 'scale')):
            raise ValueError('Opening source differs from original tutorial barrel')
        input_paths += [root / 'scenery-index.json', root / 'scenery.mwpak']
        sources.append((extra, refs, {m['source']: rock_profile(m['source'], m['triangles'])
                                     for m in extra['models']}, root / 'scenery.mwpak'))
    metadata, headers, world_lows, world_highs = [], [], [], []
    seen = set()
    for source, refs, source_profiles, archive in sources:
        # the models prepare side by side (the bsp stage's worker pool); jobs=1 runs them here
        from build_parallel import ordered_map
        tasks = [(mi, source['models'][mi], source_profiles.get(source['models'][mi]['source'], {}),
                  archive, source['textures']) for mi in dict.fromkeys(r['model_index'] for r in refs)]
        prepared = dict(ordered_map(_prepare_model, tasks, jobs)) if tasks else {}
        mount_references(source, refs, prepared, CENTRE, SCALE)
        apply_visual_offsets(source, refs)
        for ref in refs:
            if ref['number'] in seen:
                raise ValueError('Duplicate source reference across source archives')
            seen.add(ref['number'])
            mi = ref['model_index']; model = source['models'][mi]
            profile = source_profiles.get(model['source'], {})
            origin, yaw, low, high = placement_metadata(ref, prepared[mi], CENTRE,
                                                        profile.get('texture_size', 64))
            headers.append(model_row(low, high))
            rows += entities(placement_entity(len(headers), origin, yaw, ref['number']).encode('cp1252'))
            for flame in flame_entities(ref, model, CENTRE):
                rows += entities(flame.encode('cp1252'))
            # Bounds only describe this non-runtime source transport.
            angle = math.radians(yaw)
            rotate = np.array([[math.cos(angle), -math.sin(angle), 0],
                               [math.sin(angle), math.cos(angle), 0], [0, 0, 1]])
            from itertools import product
            corners = np.array(list(product(*zip(low, high)))) @ rotate.T + origin
            world_lows.append(corners.min(axis=0)); world_highs.append(corners.max(axis=0))
            metadata.append({k: ref[k] for k in ('number', 'id', 'type', 'position', 'rotation_radians', 'scale')}
                            | {'source_model': model['source'], 'source_sha256': model.get('source_sha256'),
                               'model': '*' + str(len(headers)), 'bounds': [list(low), list(high)]})
    if not headers:
        raise ValueError('Empty complete-source static carrier')
    low = np.min(world_lows, axis=0); high = np.max(world_highs, axis=0)
    if np.any(low < -32768) or np.any(high > 32767):
        raise ValueError('Source carrier bounds exceed BSP29 metadata range')
    parts = empty_world(low, high)
    parts[0] = entity_text(rows)
    parts[14] += b''.join(headers)
    raw = pack_lumps(parts)
    return raw, {'format': FORMAT, 'runtime_payload': False, 'terrain_compiled': False,
                 'rendered_faces': 0, 'selection': selection, 'references': metadata,
                 'source_inputs': {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in input_paths},
                 'opening_source': str(opening_source) if opening_source is not None else None}


def is_source_carrier(raw):
    """True when a BSP29 container is this source-only carrier (its worldspawn has the MARKER field)."""
    from player_hull import lumps
    return is_source_carrier_lump(lumps(raw)[0])


def is_source_carrier_lump(entity_lump):
    """is_source_carrier on a map's entity lump (Seyda Neen's scene entity list, BUILD-SEYDA-ENTITY-BUS-48)."""
    head = bytes(entity_lump).split(b'}', 1)[0]
    return re.search(rb'"aw_source_carrier"\s+"' + MARKER.encode('ascii') + rb'"', head) is not None


def check_activated_present(raw, exterior, map_name, inside=None):
    """Fail fast (seconds, before any later stage): every exterior reference the engine activates by aw_ref
    (aw_activated.h) whose original position lies in the town area (area_config.inside) must be a func_wall
    with a brush model in the carrier `raw`. `exterior`: prepare_opening_refs.opening_references' references.
    Refuses naming the reference and the map; returns {'expected': [...], 'present': [...]}."""
    from chim.frame_map import activated_missing, activated_refs
    from player_hull import lumps
    if inside is None:
        from area_config import inside
    refs = activated_refs()
    expected = sorted({r['number'] for r in exterior if r['number'] in refs and inside(r['position'])})
    parts = lumps(raw)
    count = len(parts[14]) // 64
    text = parts[0].rstrip(b'\0').decode('cp1252')
    blocks = [dict(re.findall(r'"([^"\n]*)"\s+"([^"\n]*)"', b)) for b in re.findall(r'\{[^{}]*\}', text)]
    rows = [e for e in blocks if e.get('classname') == 'func_wall'
            and re.fullmatch(r'\*[0-9]+', e.get('model', '')) and 0 < int(e['model'][1:]) < count]
    refused = activated_missing(map_name, expected, rows, refs)
    if refused:
        raise ValueError('; '.join(refused))
    return {'expected': expected, 'present': expected}
