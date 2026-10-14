# SPDX-License-Identifier: GPL-3.0-only
"""Prune unreachable exterior BSP payloads using aw_world.c routing priority."""
import hashlib
import json
import math
import re
import struct
from pathlib import Path
from map_files import MAP_EXTS, map_file


def subtract(a, b):
    """Subtract half-open b from half-open a, matching the engine's inside()."""
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    if x0 >= x1 or y0 >= y1:
        return [a]
    return [q for q in ((a[0], a[1], x0, a[3]), (x1, a[1], a[2], a[3]),
                         (x0, a[1], x1, y0), (x0, y1, x1, a[3]))
            if q[0] < q[2] and q[1] < q[3]]


def bounds(origin, core):
    if not all(math.isfinite(v) for v in (*origin, *core)):
        raise ValueError('Nonfinite world bounds')
    if core[0] >= core[2] or core[1] >= core[3]:
        raise ValueError('Empty world bounds')
    return tuple(origin[i % 2] + v for i, v in enumerate(core))


def shadowed(id1, towns):
    """Return fully shadowed BSP names; never change directory indices or CHIM."""
    from map_files import is_chim_frame
    id1 = Path(id1)
    path = id1 / 'world/regions.awr'
    if not path.exists():
        return []
    raw = path.read_bytes()
    if len(raw) < 64 or raw[:4] != b'AWR2':
        raise ValueError('Invalid world directory')
    count = struct.unpack_from('<I', raw, 4)[0]
    if not 1 <= count <= 8192 or len(raw) != 64 + 52 * count:
        raise ValueError('Invalid world directory size')
    prior = []
    for town in towns:
        slot = town.get('world_slot', -1)
        if slot in (0, 1):
            values = struct.unpack_from('<7f', raw, 8 + slot * 28)
            prior.append(bounds(values[:3], values[3:]))
        elif town.get('handoff') and any(
                path.is_file() and path.stat().st_size >= 124
                for path in (map_file(id1 / 'maps', town['name']),
                             map_file(id1 / 'maps', town['name'] + '-chim'))):
            prior.append(bounds(town['origin'], sum(town['core'], [])))
    result = []
    for i in range(count):
        row = struct.unpack_from('<8s11f', raw, 64 + 52 * i)
        name = 'vf%04d' % i
        if row[0] != name.encode('ascii') + b'\0\0':
            raise ValueError('Invalid world directory name at %d' % i)
        area = bounds(row[1:4], row[4:8])
        parts = [area]
        for box in prior:
            parts = [piece for part in parts for piece in subtract(part, box)]
            if not parts:
                break
        path = id1 / 'maps' / (name + '.bsp')
        if not parts and path.is_file() and not is_chim_frame(path):
            result.append(name)
        prior.append(area)
    return result


def dependencies(id1, names):
    """Conservatively retain explicit metadata, entity and save references.

    Binary world directories describe coordinates, not direct map loads. Map
    entity lumps can contain changelevel targets. Never interpret texture bytes
    as entity text. Unknown map versions fail closed before any removal.
    """
    wanted = set(names)
    found = {name: [] for name in names}
    token = re.compile(rb'(?<![A-Za-z0-9_])vf[0-9]{4}(?![A-Za-z0-9_])')
    for path in sorted(Path(id1).rglob('*')):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in ('.txt', '.cfg', '.rc', '.sav', '.gip', '.aws', '.json'):
            data = path.read_bytes()
        elif suffix in MAP_EXTS:
            with path.open('rb') as stream:
                header = stream.read(124)
                if len(header) != 124 or struct.unpack_from('<i', header)[0] != 29:
                    raise ValueError('Unsupported map header: ' + path.name)
                offset, length = struct.unpack_from('<ii', header, 4)
                if offset < 124 or length < 0 or offset + length > path.stat().st_size:
                    raise ValueError('Invalid map entity lump: ' + path.name)
                stream.seek(offset)
                data = stream.read(length)
        else:
            continue
        for value in set(token.findall(data)):
            name = value.decode('ascii')
            if name in wanted:
                found[name].append(path.relative_to(id1).as_posix())
    return found


def prune(id1, report_path, towns=None):
    """Default image cleanup, only after frame generation; report every decision.

    Older external saves are not included in a fresh image and are not migrated
    here. Directory indices remain for coordinate conversion. Catalogues of
    retired maps leave with them; retained town-region dependencies stay intact.
    """
    from town_config import runtime_towns
    id1 = Path(id1)
    names = shadowed(id1, runtime_towns() if towns is None else towns)
    refs = dependencies(id1, names) if names else {}
    removed, retained = [], []
    # Finish dependency validation and hashing before deleting any staged file.
    for name in names:
        path = id1 / 'maps' / (name + '.bsp')
        if refs[name]:
            retained.append({'file': 'maps/' + path.name, 'references': refs[name]})
        else:
            data = path.read_bytes()
            removed.append({'file': 'maps/' + path.name, 'bytes': len(data),
                            'sha256': hashlib.sha256(data).hexdigest(),
                            'reason': 'routing core fully shadowed; no explicit payload dependency'})
            # AW_HarvestBegin loads by the active map name. These unreachable
            # legacy maps cannot use their catalogue; keeping it also makes the
            # heap/fingerprint validators reject the final payload. Town region
            # tables are explicit dependencies above, so their catalogues stay.
            catalogue = id1 / ('harvest-' + name + '.txt')
            if catalogue.is_file():
                data = catalogue.read_bytes()
                removed.append({'file': catalogue.name, 'bytes': len(data),
                                'sha256': hashlib.sha256(data).hexdigest(),
                                'reason': 'catalogue of a fully shadowed retired map'})
    report = {'removed': removed, 'retained_dependencies': retained,
              'removed_bytes': sum(row['bytes'] for row in removed),
              'scope': 'Fresh image routing and explicit payload references; external saves not migrated.'}
    Path(report_path).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    for row in removed:
        (id1 / row['file']).unlink()
    return removed
