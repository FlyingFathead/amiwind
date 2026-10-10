# SPDX-License-Identifier: GPL-3.0-only
"""Final shared exterior sky policy for explicitly classified staged BSP maps.

Reserved ``sky*`` materials belong to the converter's generated enclosure.
This pass changes no collision topology, PVS, textures, or surviving polygons.
"""
import hashlib
import json
from pathlib import Path
import re
import struct

from compact_bsp import entities, entity_bytes
from player_hull import lumps, pack_lumps
from replace_bsp_world import rows, texture_blobs

SHARED_SKY_PATH = 'gfx/aw_shared_sky.lmp'
SHARED_SKY_BYTES = 256 * 128


def add_options(parser):
    parser.add_argument('--local-skybox', choices=('true', 'false'), default='false',
                        help='Keep converter local sky enclosure render faces for debugging (default: false, shared exterior sky)')
    parser.add_argument('--shared-sky-source', type=Path,
                        help='Optional 256x128 indexed shared sky resource; otherwise use consistent staged reserved sky pixels')


def boolean(value):
    if type(value) is bool:
        return value
    if value in ('true', 'false'):
        return value == 'true'
    raise ValueError('local-skybox must be true or false')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _checked(raw):
    if len(raw) < 124 or struct.unpack_from('<i', raw)[0] != 29:
        raise ValueError('Shared sky requires BSP29')
    for i in range(15):
        offset, size = struct.unpack_from('<ii', raw, 4 + i * 8)
        if offset < 124 or size < 0 or offset + size > len(raw):
            raise ValueError('Invalid BSP lump bounds')
    data = lumps(raw)
    sizes = {1: 20, 3: 12, 5: 24, 6: 40, 7: 20, 9: 8,
             10: 28, 11: 2, 12: 4, 13: 4, 14: 64}
    if any(len(data[i]) % size for i, size in sizes.items()):
        raise ValueError('Invalid BSP record stride')
    return data


def _sky_indices(data):
    blobs = texture_blobs(data[2])
    return {i for i, blob in enumerate(blobs) if blob is not None and
            blob[:16].split(b'\0')[0].startswith(b'sky')}


def sky_pixels(raw):
    """Return distinct valid reserved sky mip0 resources; never invent pixels."""
    data = _checked(raw)
    blobs = texture_blobs(data[2])
    output = []
    for i in sorted(_sky_indices(data)):
        blob = blobs[i]
        if len(blob) < 40:
            raise ValueError('Truncated reserved sky texture')
        _, width, height, start, *_ = struct.unpack_from('<16s6I', blob)
        if (width, height) != (256, 128) or start < 40 or start + SHARED_SKY_BYTES > len(blob):
            raise ValueError('Reserved sky must contain 256x128 mip0 pixels')
        pixels = bytes(blob[start:start + SHARED_SKY_BYTES])
        if pixels not in output:
            output.append(pixels)
    return output


def transform(raw, *, scene_kind, local_skybox=False):
    """Remove reserved sky polygons only for explicit exterior scenes.

    Debug true retains local geometry but still declares the exterior shared
    background. Interior mode explicitly disables that background; its geometry
    remains untouched. Unknown maps must be skipped by the caller.
    """
    local_skybox = boolean(local_skybox)
    if scene_kind not in ('exterior', 'interior'):
        raise ValueError('Explicit exterior or interior scene kind required')
    data = _checked(raw)
    original = [bytes(x) for x in data]
    r = rows(data)
    es = entities(data[0])
    if not es or es[0].get('classname') != 'worldspawn':
        raise ValueError('First entity must be worldspawn')
    sky = _sky_indices(data)
    texture_count = len(texture_blobs(data[2]))
    remove = set()
    for fid, face in enumerate(r[7]):
        if not 0 <= face[4] < len(r[6]):
            raise ValueError('Invalid face texinfo index')
        index = r[6][face[4]][8]
        if not 0 <= index < texture_count:
            raise ValueError('Invalid miptex index')
        if scene_kind == 'exterior' and not local_skybox and index in sky:
            remove.add(fid)
    prefix = [0]
    for fid in range(len(r[7])):
        prefix.append(prefix[-1] + int(fid not in remove))

    def span(first, count):
        if first < 0 or count < 0 or first + count > len(r[7]):
            raise ValueError('Invalid surface span')
        return prefix[first], prefix[first + count] - prefix[first]

    pool = es[0].get('aw_render_pool')
    pool_first = pool_count = 0
    if pool is not None:
        if not re.fullmatch(r'\*[0-9]+', pool) or not 0 < int(pool[1:]) < len(r[14]):
            raise ValueError('Invalid render pool model')
        pool_first, pool_count = r[14][int(pool[1:])][14:16]
        span(pool_first, pool_count)
    for entity in es:
        if 'aw_render_ranges' not in entity:
            continue
        if pool is None:
            raise ValueError('Render range without pool')
        rebuilt = []
        for field in entity['aw_render_ranges'].split(','):
            if not re.fullmatch(r'[0-9]+:[0-9]+', field):
                raise ValueError('Invalid render range')
            start, count = map(int, field.split(':'))
            if count <= 0 or start + count > pool_count:
                raise ValueError('Render range exceeds pool')
            first, count = span(pool_first + start, count)
            if count:
                rebuilt.append(f'{first - prefix[pool_first]}:{count}')
        if rebuilt:
            entity['aw_render_ranges'] = ','.join(rebuilt)
        else:
            entity.pop('aw_render_ranges')
    if remove:
        faces = bytearray()
        for fid in range(len(r[7])):
            if fid not in remove:
                faces.extend(original[7][fid * 20:(fid + 1) * 20])
        data[7] = faces
        for i, record in enumerate(r[5]):
            struct.pack_into('<HH', data[5], i * 24 + 20, *span(*record[9:11]))
        for i, record in enumerate(r[14]):
            struct.pack_into('<ii', data[14], i * 64 + 56, *span(*record[14:16]))
        marks = bytearray()
        for i, leaf in enumerate(r[10]):
            first, count = leaf[8:10]
            if first + count > len(r[11]):
                raise ValueError('Invalid leaf marksurface span')
            kept = []
            for mark in r[11][first:first + count]:
                fid = mark[0]
                if not 0 <= fid < len(r[7]):
                    raise ValueError('Invalid marksurface face')
                if fid not in remove:
                    kept.append(prefix[fid])
            if len(marks) // 2 > 65535 or len(kept) > 65535:
                raise ValueError('Marksurface range exceeds BSP29 limit')
            struct.pack_into('<HH', data[10], i * 28 + 20, len(marks) // 2, len(kept))
            marks.extend(struct.pack('<' + 'H' * len(kept), *kept))
        data[11] = marks
    es[0]['_aw_sky_mode'] = scene_kind
    es[0]['_aw_sky_asset'] = SHARED_SKY_PATH
    data[0] = bytearray(entity_bytes(es))
    # Exact non-render fields certify collision topology without renumbering.
    for i in (1, 2, 3, 4, 6, 8, 9, 12, 13):
        if bytes(data[i]) != original[i]:
            raise ValueError('Unrelated BSP lump changed')
    for i in range(len(r[5])):
        if data[5][i * 24:i * 24 + 20] != original[5][i * 24:i * 24 + 20]:
            raise ValueError('Node collision data changed')
    for i in range(len(r[14])):
        if data[14][i * 64:i * 64 + 56] != original[14][i * 64:i * 64 + 56]:
            raise ValueError('Model collision or bounds changed')
    for i in range(len(r[10])):
        if data[10][i * 28:i * 28 + 20] != original[10][i * 28:i * 28 + 20] or data[10][i * 28 + 24:i * 28 + 28] != original[10][i * 28 + 24:i * 28 + 28]:
            raise ValueError('Leaf contents or PVS data changed')
    output = pack_lumps(data)
    return output, {'scene_kind': scene_kind, 'local_skybox': local_skybox,
                    'stored_faces_before': len(r[7]), 'stored_faces_after': len(data[7]) // 20,
                    'removed_face_ids': sorted(remove), 'removed_sky_faces': len(remove),
                    'remaining_sky_faces': sum(r[6][f[4]][8] in sky for i, f in enumerate(r[7]) if i not in remove),
                    'input_bytes': len(raw), 'output_bytes': len(output),
                    'collision_topology_exact': True, 'PVS_exact': True,
                    'surviving_face_records_exact': True, 'textures_exact': True,
                    'shared_sky_asset': SHARED_SKY_PATH,
                    'input_sha256': digest(raw), 'output_sha256': digest(output)}


def _sky_map(task):
    """Worker: transform one staged map; write its original/candidate pair only.

    The parent installs nothing until every map is prepared and re-verified.
    """
    path, kind, local_skybox, work, *rest = task
    cache = rest[0] if rest else None
    path, work = Path(path), Path(work)
    raw = path.read_bytes()
    found = None
    if kind is not None and cache is not None:
        # The per-map pass cache (tools/pass_cache.py): same bytes and scene kind, same result.
        key = digest(raw) + ':' + kind
        found = cache.load(key)
    if found is not None:
        detail, cached = found
        output = raw if cached is None else cached
    elif kind is not None:
        output, detail = transform(raw, scene_kind=kind, local_skybox=local_skybox)
        if cache is not None:
            detail = json.loads(json.dumps(detail))  # the form a cached detail has
            cache.store(key, detail, None if output == raw else output)
    else:
        output, detail = raw, {'scene_kind': 'unknown', 'unchanged': True, 'not_claimed_complete': True}
    if output != raw:
        from build_parallel import keep_original  # installed by rename, never rewritten
        keep_original(path, work / 'originals' / path.name, raw)
        (work / 'candidates' / path.name).write_bytes(output)
    return path.stem, detail, digest(raw), digest(output)


def configure_staged_maps(id1, *, exterior_maps, interior_maps=(), local_skybox=False,
                          shared_sky_source=None, work_dir, jobs=1):
    """Prepare/validate every result, then replace derived staging maps only.

    Maps are independent: up to `jobs` workers transform them (shared pool,
    tools/build_parallel.py); results, receipt order and bytes equal jobs=1.
    """
    from build_parallel import completed_map, hash_files
    local_skybox = boolean(local_skybox)
    id1, work = Path(id1).resolve(), Path(work_dir).resolve()
    if id1 == work or id1 in work.parents or work in id1.parents:
        raise ValueError('Sky receipts must be outside id1 staging')
    exterior, interior = set(exterior_maps), set(interior_maps)
    if exterior & interior or any(not isinstance(n, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', n) for n in exterior | interior):
        raise ValueError('Explicit disjoint scene manifests required')
    inputs = sorted((id1 / 'maps').glob('*.bsp'))
    names = {p.stem for p in inputs}
    if not inputs or (exterior | interior) - names:
        raise ValueError('Missing staged maps in scene manifest')
    for path in inputs:
        if path.is_symlink() or path.resolve().parent != id1 / 'maps':
            raise ValueError('Staged maps must be regular local files')
    resource = None
    source = 'none: no exterior maps'
    if exterior:
        if shared_sky_source is not None:
            resource = Path(shared_sky_source).read_bytes()
            source = str(Path(shared_sky_source).resolve())
        else:
            existing = id1 / SHARED_SKY_PATH
            if existing.exists():
                resource = existing.read_bytes()
                source = 'existing staged shared resource'
            else:
                resources = {digest(p): p for n in sorted(exterior)
                             for p in sky_pixels((id1 / 'maps' / (n + '.bsp')).read_bytes())}
                if len(resources) != 1:
                    raise ValueError('Require one consistent reserved sky resource or explicit shared-sky-source')
                resource = next(iter(resources.values()))
                source = 'consistent staged reserved sky mip0'
        if len(resource) != SHARED_SKY_BYTES:
            raise ValueError('Shared sky resource must be exactly 32768 indexed bytes')
    work.mkdir(parents=True, exist_ok=False)
    (work / 'originals').mkdir()
    (work / 'candidates').mkdir()
    report = {'local_skybox': local_skybox, 'status': 'preparing', 'maps': [],
              'shared_resource_source': source, 'shared_resource_sha256': digest(resource) if resource is not None else None,
              'unknown_maps_preserved': sorted(names - exterior - interior)}
    # Development builds, and release builds with --allow-release-reuse, reuse results for unchanged map
    # bytes (tools/pass_cache.py; BUILD-IMAGE-NO-RESUME-33).
    from pass_cache import PassCache
    cache = PassCache.open('exterior-sky', {'local_skybox': local_skybox}, __file__)
    tasks = [(str(path), 'exterior' if path.stem in exterior else 'interior' if path.stem in interior else None,
              local_skybox, str(work), cache) for path in inputs]
    # Largest maps first, results as they finish (no wait behind one slow map);
    # the receipt and the log keep map order.
    expected, details = {}, {}
    biggest = sorted(tasks, key=lambda task: (-Path(task[0]).stat().st_size, task[0]))
    for n, detail, input_sha, output_sha in completed_map(_sky_map, biggest, max(1, min(jobs, len(tasks)))):
        expected[n], details[n] = (input_sha, output_sha), detail
    for n in (Path(task[0]).stem for task in tasks):
        detail = details[n]
        report['maps'].append({'map': n, **detail})
        print('[exterior-sky] {}: {}; local enclosure {}; removed {} faces; {}'.format(
            n, detail['scene_kind'], ('retained (debug)' if local_skybox else 'removed')
            if detail['scene_kind'] == 'exterior' else 'unchanged',
            detail.get('removed_sky_faces', 0),
            'unknown preserved; not claimed complete' if detail['scene_kind'] == 'unknown'
            else 'shared background ON' if detail['scene_kind'] == 'exterior'
            else 'shared background OFF'), flush=True)
    report_path = work / 'exterior-sky.json'
    report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    for path, actual in zip(inputs, hash_files(inputs, jobs)):
        if actual != expected[path.stem][0]:
            raise ValueError('Staged map changed during sky preparation')
    asset = id1 / SHARED_SKY_PATH
    if resource is not None:
        if asset.exists():
            (work / 'originals' / 'aw_shared_sky.lmp').write_bytes(asset.read_bytes())
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_bytes(resource)
    for path in inputs:
        candidate = work / 'candidates' / path.name
        if candidate.exists():
            candidate.replace(path)
    for path, actual in zip(inputs, hash_files(inputs, jobs)):
        if actual != expected[path.stem][1]:
            raise ValueError('Installed sky map differs from validated result')
    report['status'] = 'completed'
    report['removed_sky_faces'] = sum(r.get('removed_sky_faces', 0) for r in report['maps'])
    report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report
