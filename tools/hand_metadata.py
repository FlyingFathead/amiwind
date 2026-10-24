# SPDX-License-Identifier: GPL-3.0-only
"""Bind every staged map to its converted first-person animation metadata."""
import hashlib
import math
from pathlib import Path
import re
import struct

from player_hull import lumps, pack_lumps

CLIPS = (('idle', 0, 8), ('draw', 8, 6), ('lower', 14, 4), ('punch', 18, 10))


def hand_fields(report):
    """Use source-derived timings, never guessed replacement animation times."""
    if report.get('model') != 'progs/v_nord.mdl' or report.get('frames') != 28:
        raise ValueError('First-person hand report has an incompatible frame contract')
    result = {}
    for name, first, count in CLIPS:
        clip = report.get('clips', {}).get(name, {})
        duration = clip.get('duration', 0)
        if (clip.get('first'), clip.get('count')) != (first, count):
            raise ValueError('First-person hand frame range differs: ' + name)
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or not 0 < duration <= 60:
            raise ValueError('Invalid first-person hand duration: ' + name)
        result['aw_hand_' + name] = str(duration)
    eye = report.get('eye_above_origin', 0)
    if isinstance(eye, bool) or not isinstance(eye, (int, float)) or not math.isfinite(eye) or not 0 < eye <= 128:
        raise ValueError('Invalid first-person eye height')
    result['aw_eye_height'] = str(eye)
    return result


def timing_lines(fields):
    """The worldspawn lines of FIELDS (hand_fields), one "<field>" "<value>" pair a line in hand_fields order (a
    placeholder, not a map key: the spawn contract scan reads entity text in tools/): the text every
    converted map's worldspawn carries (the order stamp() appends them in, so a map written from these lines has the
    bytes it had when they were read back out of the stamped seyda.bsp)."""
    return '\n'.join('"%s" "%s"' % (key, value) for key, value in fields.items())


def scene_report(scene):
    """The hands stage's report of a scene folder: scene-ready.json["hands"], else hands-report.json (both written by
    tools/prepare_hands.py and copied down the scene chain). BUILD-SEYDA-BSP-CARRIER-48: stages read the hand timings
    from here, never from seyda.bsp's entity lump."""
    import json
    scene = Path(scene)
    ready = scene / 'scene-ready.json'
    report = json.loads(ready.read_text()).get('hands') if ready.is_file() else None
    if not report and (scene / 'hands-report.json').is_file():
        report = json.loads((scene / 'hands-report.json').read_text())
    if not report:
        raise ValueError('The scene %s has no hands report (scene-ready.json "hands" or hands-report.json): '
                         'run the hands stage first' % scene)
    return report


def scene_timings(scene):
    """The hand timing and eye height lines (timing_lines) of a scene folder's hands report (scene_report)."""
    return timing_lines(hand_fields(scene_report(scene)))


def stamp(raw, fields):
    """Change only the first entity's five metadata fields; keep other lumps."""
    return stamp_lump(raw, lumps(raw)[0], fields)


def stamp_lump(raw, entity_lump, fields):
    """stamp() with the entity lump given (the hands stage: Seyda Neen's scene entity list, seyda_entities,
    BUILD-SEYDA-ENTITY-BUS-48): RAW's other lumps are kept, its lump 0 becomes ENTITY_LUMP stamped (RAW itself
    when that is RAW's own lump 0 already)."""
    data = lumps(raw)
    text = bytes(entity_lump)
    block = re.match(rb'\s*\{([^{}]*)\}', text)
    if not block or not re.search(rb'"classname"\s+"worldspawn"', block[1]):
        raise ValueError('Map must begin with worldspawn')
    body = block[1]
    for key, value in fields.items():
        pattern = rb'"' + key.encode('ascii') + rb'"\s+"[^"\r\n]*"'
        old = re.findall(pattern, body)
        if len(old) > 1:
            raise ValueError('Duplicate worldspawn metadata: ' + key)
        replacement = ('"' + key + '" "' + value + '"').encode('ascii')
        if old:
            body = re.sub(pattern, lambda match: replacement, body)
        else:
            body += replacement + b'\n'
    changed = text[:block.start(1)] + body + text[block.end(1):]
    if changed == bytes(data[0]):
        return raw
    data[0] = changed
    return pack_lumps(data)


def _plan_stamp(task):
    """Worker: (input hash, needs a change) for one map; writes nothing."""
    path, fields = task
    raw = Path(path).read_bytes()
    return hashlib.sha256(raw).hexdigest(), stamp(raw, fields) != raw


def _write_stamp(task):
    """Worker: re-check one planned map, stamp it and verify the write."""
    path, fields, original_hash = task
    path = Path(path)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != original_hash:
        raise ValueError('Map changed during hand metadata staging: ' + path.name)
    corrected = stamp(raw, fields)
    path.write_bytes(corrected)
    if path.read_bytes() != corrected:
        raise ValueError('Hand metadata write verification failed: ' + path.name)
    return path.name


def stamp_staged_hands(id1, report, map_names=None, jobs=1):
    """Call after all map replacements, before content/heap/package gates."""
    id1 = Path(id1)
    fields = hand_fields(report)
    model = id1 / report['model']
    model_raw = model.read_bytes()
    # Staging can remap skin palette bytes after conversion. Validate the
    # animation shape here; record both hashes without demanding identical skins.
    if (len(model_raw) < 84 or model_raw[:8] != b'IDPO\x06\x00\x00\x00' or
            struct.unpack_from('<3i', model_raw, 60) !=
            (report.get('vertices'), report.get('triangles'), report['frames'])):
        raise ValueError('Staged first-person hand model does not match its frame report')
    model_hash = hashlib.sha256(model_raw).hexdigest()
    if map_names is None:
        maps = sorted((id1 / 'maps').glob('*.bsp'))
    else:
        names = sorted(set(map_names))
        if any(not re.fullmatch(r'[A-Za-z0-9_]+', name) for name in names):
            raise ValueError('Invalid map name for first-person metadata')
        maps = [id1/'maps'/(name+'.bsp') for name in names]
    if not maps and map_names is not None:
        # a pure CHIM image without any legacy map (a MiniWind sandbox of a town on CHIM): the frame maps carry
        # the hand fields from their own worldspawn (chim_town entities), nothing to stamp here
        return {'status': 'no legacy maps', 'map_count': 0, 'changed_maps': [], 'model_sha256': model_hash,
                'source_model_sha256': report.get('sha256'), 'worldspawn_fields': fields,
                'scope': 'hand animation timing and eye height; geometry and collision unchanged'}
    if not maps:
        raise ValueError('No staged maps for first-person metadata')
    # Validate all inputs before the first write. Holding every world's bytes
    # would need gigabytes; retain only hashes and reread one bounded map at a time.
    # Maps are independent: both passes run in up to `jobs` workers, in map order.
    from build_parallel import ordered_map
    workers = max(1, min(jobs, len(maps)))
    planned = list(ordered_map(_plan_stamp, [(str(path), fields) for path in maps], workers))
    changed = [name for name in ordered_map(_write_stamp,
               [(str(path), fields, original_hash) for path, (original_hash, needs_change)
                in zip(maps, planned) if needs_change], workers)]
    return {'status': 'passed', 'map_count': len(maps), 'changed_maps': changed,
            'model_sha256': model_hash, 'source_model_sha256': report.get('sha256'),
            'worldspawn_fields': fields,
            'scope': 'hand animation timing and eye height; geometry and collision unchanged'}
