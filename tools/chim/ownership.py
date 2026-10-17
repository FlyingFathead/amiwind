# SPDX-License-Identifier: GPL-3.0-only
"""Original reference ownership, distinct from a frame's local streaming records.

AmiQuake loads one frame at a time. Whole scenery at a boundary must therefore
remain in both frames. Source identity and original position choose one logical
owner; compiled piece records retain their own local chunk owners. This sidecar
contract changes neither the engine nor CHIM's binary format.
"""
import copy
import hashlib
import math
import struct
from pathlib import Path

from chim import format as F
from chim.cut import source_ref


def original(ref):
    """Snapshot before mounting, visual offsets, cutting or model remapping."""
    if any(not isinstance(ref.get(k, 'Morrowind.esm' if k == 'master' else None), str)
           for k in ('master', 'id', 'type', 'model')):
        raise ValueError('Invalid original reference strings')
    value = {'master': ref.get('master', 'Morrowind.esm').casefold(), 'number': ref['number'],
             'cell': list(ref.get('cell') or []), 'id': ref['id'].casefold(), 'type': ref['type'],
             'model': ref['model'].replace(chr(92), '/').casefold(), 'position': list(ref['position']),
             'rotation_radians': list(ref.get('rotation_radians', [0., 0., 0.])),
             'scale': ref.get('scale', 1.)}
    if (not isinstance(value['master'], str) or not value['master'] or
            type(value['number']) is not int or not 0 < value['number'] < (1 << 24) or
            len(value['position']) != 3 or len(value['rotation_radians']) != 3 or
            any(not math.isfinite(v) for v in value['position'] + value['rotation_radians'] + [value['scale']])):
        raise ValueError('Invalid original reference identity or transform')
    return copy.deepcopy(value)


def capture(ref):
    return dict(ref, _chim_original=original(ref))


def model_digest(lumps):
    """Exact render/collision payload, independent of world texture-number remapping.

    Texture contents and references have their own complete validator. Ignore
    only the remapped texture table and the texture-number field of texinfo.
    Keep axes, geometry, light samples, nodes and every collision hull exact.
    """
    h = hashlib.sha256()
    for i in range(15):
        if i == 2:
            continue
        data = bytes(lumps[i])
        if i == 6:
            data = b''.join(data[j:j+32] + b'\0'*4 + data[j+36:j+40]
                            for j in range(0, len(data), 40))
        h.update(struct.pack('<II', i, len(data)));h.update(data)
    return h.hexdigest()


def contains(box, p):
    return box[0] <= p[0] < box[2] and box[1] <= p[1] < box[3]


def intersects(a, b):
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]



def select_compiled_apron(spec, references):
    """Remove only external apron selections with no actual compiled footprint.

    Source bounds conservatively transform the original box. A rotated compiled
    mesh can be smaller; keep every owned original and every piece reaching the
    apron, and record exact excluded originals and boxes for source accounting.
    The unchanged manifest guard still rejects missing pieces and bad ownership.
    """
    from chim.world import frame_box, f32, placed_box
    frame = spec['frame']; centre = frame['centre']
    core = list(frame_box(frame))
    coverage = [centre[k] + 4*frame['low'][k] for k in range(2)]
    coverage += [coverage[k] + 4*frame['span'][k] for k in range(2)]
    footprints = {}
    for p in spec['placements']:
        v = spec['variants'][p['variant']]
        if not all(math.isfinite(x) for x in [*p['origin'], p['yaw'], *v['lo'], *v['hi']]):
            raise ValueError('Nonfinite compiled apron transform or bounds')
        lo, hi = placed_box([f32(x) for x in p['origin']], f32(p['yaw']),
                            [f32(x) for x in v['lo']], [f32(x) for x in v['hi']])
        box = [centre[k] + 4*lo[k] for k in range(2)] + [centre[k] + 4*hi[k] for k in range(2)]
        if not all(math.isfinite(x) for x in box):
            raise ValueError('Nonfinite compiled apron footprint')
        footprints.setdefault(source_ref(p['ref']), []).append(box)
    selected, excluded, seen = [], [], set()
    for ref in references:
        src = original(ref['_chim_original']); number = src['number']
        if number in seen:
            raise ValueError('Repeated source reference in compiled apron selection')
        seen.add(number)
        boxes = footprints.get(number, [])
        if not contains(core, src['position']) and boxes and not any(intersects(coverage, b) for b in boxes):
            excluded.append({'original': src, 'compiled_footprints': boxes,
                             'coverage': coverage, 'reason': 'compiled footprint outside this apron'})
        else:
            selected.append(ref)
    removed = {r['original']['number'] for r in excluded}
    if removed:
        spec['placements'] = [p for p in spec['placements'] if source_ref(p['ref']) not in removed]
        used = {p['variant'] for p in spec['placements']}
        spec['variants'] = {k: v for k, v in spec['variants'].items() if k in used}
    return selected, excluded


def manifest(spec, references):
    """Bind each original to its exact converted pieces before packing."""
    from chim.world import frame_box, f32, placed_box
    frame = spec['frame'];centre = frame['centre']
    core = list(frame_box(frame))
    coverage = [centre[k] + 4*frame['low'][k] for k in range(2)]
    coverage += [coverage[k] + 4*frame['span'][k] for k in range(2)]
    rows = [];seen = set();footprints = {};pieces = []
    hashes = {k: model_digest(v['lumps']) for k, v in spec['variants'].items()}
    for p in spec['placements']:
        v = spec['variants'][p['variant']]
        origin = [f32(x) for x in p['origin']];yaw = f32(p['yaw'])
        lo, hi = placed_box(origin, yaw, [f32(x) for x in v['lo']], [f32(x) for x in v['hi']])
        box = [centre[k] + 4*lo[k] for k in range(2)] + [centre[k] + 4*hi[k] for k in range(2)]
        footprints.setdefault(source_ref(p['ref']), []).append(box)
        pieces.append({'ref': p['ref'], 'origin': origin, 'yaw': yaw, 'cell': list(p['cell']),
                       'model_sha256': hashes[p['variant']], 'story_hidden': bool(p.get('story_hidden'))})
    for ref in references:
        src = ref.get('_chim_original')
        if src is None:
            raise ValueError('Original ownership snapshot missing for %s' % ref['number'])
        src = original(src)
        n = src['number']
        if n in seen:
            raise ValueError('Repeated source reference in one frame: %s' % n)
        seen.add(n)
        role = 'owner' if contains(core, src['position']) else 'dependency'
        if role == 'dependency' and not any(intersects(coverage, b) for b in footprints.get(n, [])):
            raise ValueError('Dependency %s has no compiled footprint in frame coverage' % n)
        rows.append({'original': src, 'role': role})
    if seen != set(footprints):
        raise ValueError('Compiled pieces and original references differ')
    return {'schema': 1, 'core': core, 'coverage': coverage, 'references': rows, 'pieces': pieces}


def source_failures(sections):
    """Fail closed for conflicting origins/identities or missing included owners."""
    failures = [];by_number = {};cores = []
    for s in sections:
        m = s.get('frame_ownership')
        if not isinstance(m, dict) or m.get('schema') != 1:
            failures.append('ownership metadata missing or unsupported');continue
        core = m.get('core', []);cover = m.get('coverage', [])
        if (len(core) != 4 or len(cover) != 4 or
                any(not math.isfinite(x) for x in core + cover) or
                any(not cover[k] <= core[k] < core[k+2] <= cover[k+2] for k in range(2))):
            failures.append('invalid ownership core/coverage');continue
        for old in cores:
            if core[0] < old[2] and old[0] < core[2] and core[1] < old[3] and old[1] < core[3]:
                failures.append('logical ownership cores overlap')
        cores.append(core)
        seen = set()
        for row in m.get('references', []):
            try:
                src = original(row['original'])
                n = src['number']
                if n in seen:
                    failures.append('repeated source reference %s in frame' % n)
                seen.add(n)
                role = 'owner' if contains(core, src['position']) else 'dependency'
                if row.get('role') != role:
                    failures.append('reference %s ownership role disagrees with original position' % n)
                by_number.setdefault(n, []).append((src, role))
            except (KeyError, TypeError, ValueError, OverflowError):
                failures.append('invalid original ownership reference')
        wanted = [r['ref'] for r in s.get('placements', [])]
        if len(wanted) != len(set(wanted)) or set(wanted) != seen:
            failures.append('ownership references differ from frame source placements')
        piece_ids = [p['ref'] for p in m.get('pieces', [])]
        if len(piece_ids) != len(set(piece_ids)) or {source_ref(n) for n in piece_ids} != seen:
            failures.append('ownership pieces differ from original references')
    for n, copies in by_number.items():
        src = copies[0][0]
        if any(other != src for other, _ in copies):
            failures.append('reference %s original identity/transform differs between frames' % n)
        owners = sum(role == 'owner' for _, role in copies)
        included = any(contains(core, src['position']) for core in cores)
        if owners != int(included):
            failures.append('reference %s has %d logical owners; expected %d' % (n, owners, int(included)))
    return failures


def bind_index(out, source):
    source['ownership_index_sha256'] = hashlib.sha256((Path(out)/'chim/world.cwi').read_bytes()).hexdigest()


def _frame_binary_failures(task):
    """One frame's sidecar checks against its serialized pieces (binary_failures; worker or in its process):
    its failure lines in order. task: (path, frame, owned records in chunk order, frame_ownership, model count,
    {model: digest} of the frame's models)."""
    path, frame, owned, m, nmodels, digests = task
    failures = []
    centre = frame['centre']
    coverage = [centre[k]+4*frame['low'][k] for k in range(2)]
    coverage += [coverage[k]+4*frame[['nx', 'ny'][k]]*frame['grain'] for k in range(2)]
    if m['coverage'] != coverage:
        failures.append('%s: ownership coverage differs from binary frame' % path)
    actual = []
    footprint_refs = set()
    for p in owned:
        mi = p['model']
        if not 0 <= mi < nmodels:
            failures.append('%s: ownership piece has invalid model' % path);continue
        actual.append({'ref': p['ref'], 'origin': list(p['origin']), 'yaw': p['yaw'],
                       'cell': [frame['cell'][0]+p['cell_dx'], frame['cell'][1]+p['cell_dy']],
                       'model_sha256': digests[mi], 'story_hidden': bool(p['flags'] & F.FLAG_STORY_HIDDEN)})
        lo, hi = p['box']
        box = [centre[k]+4*lo[k] for k in range(2)] + [centre[k]+4*hi[k] for k in range(2)]
        if intersects(coverage, box):
            footprint_refs.add(source_ref(p['ref']))
    if sorted(actual, key=lambda p: p['ref']) != sorted(m.get('pieces', []), key=lambda p: p['ref']):
        failures.append('%s: ownership pieces differ from serialized render/collision/placement records' % path)
    for row in m.get('references', []):
        if row.get('role') == 'dependency' and row['original']['number'] not in footprint_refs:
            failures.append('%s: dependency has no footprint in frame coverage' % path)
    return failures


def _model_digests(images):
    """Worker: model_digest of each brush image."""
    return [model_digest(F.read_brush_image(image)) for image in images]


DIGEST_GROUP = 256          # model images per digest task on the worker pool


def binary_failures(out, source, sections, frames, models, jobs=1):
    """Validate sidecar against the serialized pieces, not just source intent. jobs > 1: the model digests and
    the frames' checks run on the worker pool (build_parallel.ordered_map), merged in frame order: the same
    failures in the same order as one process (BUILD-CHIM-STAGE-SERIAL-TAIL-36)."""
    failures = source_failures(list(sections.values()))
    actual_hash = hashlib.sha256((Path(out)/'chim/world.cwi').read_bytes()).hexdigest()
    if source.get('ownership_index_sha256') != actual_hash:
        failures.append('ownership metadata is not bound to this world index')
    work = []
    for path, frame, chunks in frames:
        m = sections.get(path, {}).get('frame_ownership')
        if not isinstance(m, dict) or m.get('schema') != 1:
            continue
        work.append((path, frame, [p for c in chunks for p in c['owned']], m))
    used = sorted({p['model'] for _, _, owned, _ in work for p in owned if 0 <= p['model'] < len(models)})
    jobs = max(1, int(jobs or 1))
    if jobs > 1 and len(work) > 1:
        from build_parallel import ordered_map
        groups = [used[k:k + DIGEST_GROUP] for k in range(0, len(used), DIGEST_GROUP)]
        hashes = {}
        for ids, found in zip(groups, ordered_map(_model_digests, [[models[i]['image'] for i in g] for g in groups],
                                                   min(jobs, len(groups) or 1))):
            hashes.update(zip(ids, found))
        tasks = [(path, frame, owned, m, len(models), {mi: hashes[mi] for mi in {p['model'] for p in owned}
                                                       if mi in hashes}) for path, frame, owned, m in work]
        done = ordered_map(_frame_binary_failures, tasks, min(jobs, len(tasks)), cost=lambda t: len(t[2]) + 1)
    else:
        hashes = {mi: model_digest(F.read_brush_image(models[mi]['image'])) for mi in used}
        done = map(_frame_binary_failures, ((path, frame, owned, m, len(models), hashes)
                                            for path, frame, owned, m in work))
    for found in done:
        failures += found
    return failures
