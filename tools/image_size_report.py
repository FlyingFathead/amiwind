#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Where the bytes of a built image go, and which bytes are stored more than once (read only).

IMAGE-BIGGER-THAN-ORIGINAL-62: the image is larger than the original game data. This report reads a build run's
staged boot payload (image/boot) and its world partition manifest (image/world-partitions.json, which already
carries the bytes and SHA-256 of every world file) and prints:

- bytes by kind (models, skins, maps, sounds, textures, video, other) and by file extension; the skins of the
  actor models (progs/*.mdl) are counted under skins, the rest of each model under models;
- the largest groups of repeated bytes: whole files with the same SHA-256, and inside the models the same skin,
  ST + triangle block, frame or skeletal tail stored by more than one model (wasted = (copies - 1) x size);
- the 16 x 16 pixel tiles of the single inline actor skins: how many are distinct (the skin tile method).

Nothing is written except the --json file. Usage:

    image_size_report.py RUN [--top 20] [--jobs N] [--json OUT]

RUN is a build run folder (it holds image/boot and image/world-partitions.json).
"""
import argparse
import collections
import hashlib
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import struct
import sys

from map_files import FRAME_EXT  # the frame-map extension from its one helper (tools/ is on the path: run or imported)

MDL_HEADER = 84
KINDS = {
    'models': ('.mdl', '.aws1', '.spr', '.anm', '.awsk', '.aws', '.awh', '.awb', '.tag', '.hld'),
    'skins': ('.awk', '.awp'),
    'maps': ('.bsp', FRAME_EXT, '.far', '.cut', '.crm', '.ccs', '.ccf', '.cwi', '.awnb'),
    'sounds': ('.wav', '.mws', '.lip'),
    'textures': ('.lut', '.awf', '.awi', '.lmp', '.awt'),
    'video': ('.awv',),
}
KIND_OF = {ext: kind for kind, exts in KINDS.items() for ext in exts}
TILE = 16


def kind_of(rel):
    return KIND_OF.get(os.path.splitext(rel)[1].lower(), 'other')


def mdl_sections(raw):
    """[(section, bytes)] of a single-skin MDL v6 with inline skin and plain frames, or None. Sections: skin,
    shape (ST + triangles), frames, tail (what follows the frames: the skeletal block)."""
    if len(raw) < MDL_HEADER + 4 or raw[:4] != b'IDPO' or struct.unpack_from('<i', raw, 4)[0] != 6:
        return None
    ns, sw, sh, nv, nt, nf = struct.unpack_from('<6i', raw, 48)
    if ns != 1 or sw < 1 or sh < 1 or struct.unpack_from('<i', raw, MDL_HEADER)[0] != 0:
        return None
    p = MDL_HEADER + 4 + sw * sh
    out = [('skin', raw[MDL_HEADER + 4:p])]
    if raw[p:p + 4] in (b'AWSH',):                       # a shared shape (tools/payload_share.py): 28-byte reference
        out.append(('shape-ref', raw[p:p + 28])); p += 28
    else:
        out.append(('shape', raw[p:p + 12 * nv + 16 * nt])); p += 12 * nv + 16 * nt
    s = p
    for _ in range(nf):
        if p + 4 > len(raw) or struct.unpack_from('<i', raw, p)[0] != 0:
            return None
        p += 4 + 8 + 16 + 4 * nv
    if p > len(raw):
        return None
    out.append(('frames', raw[s:p]))
    out.append(('tail', raw[p:]))
    return out, sw, sh


def tile_digests(skin, w, h):
    if w % TILE or h % TILE:
        return []
    out = []
    for ty in range(0, h, TILE):
        for tx in range(0, w, TILE):
            out.append(hashlib.blake2b(b''.join(skin[(ty + r) * w + tx:(ty + r) * w + tx + TILE] for r in range(TILE)),
                                       digest_size=8).digest())
    return out


def read_one(args):
    path, rel = args
    raw = Path(path).read_bytes()
    row = {'rel': rel, 'bytes': len(raw), 'sha': hashlib.sha256(raw).hexdigest(), 'kind': kind_of(rel)}
    if rel.endswith('.mdl'):
        found = mdl_sections(raw)
        if found:
            secs, w, h = found
            row['sections'] = [(name, len(b), hashlib.sha256(b).hexdigest()) for name, b in secs if b]
            if rel.startswith('progs/') and rel.count('/') == 1 and os.path.basename(rel)[:2] in ('a_', 'n_'):
                row['tiles'] = tile_digests(secs[0][1], w, h)
    return row


def report(run, top=20, jobs=None):
    run = Path(run)
    boot = run / 'image' / 'boot'
    files = sorted(p for p in boot.rglob('*') if p.is_file())
    work = [(str(p), p.relative_to(boot / 'id1').as_posix() if (boot / 'id1') in p.parents else
             '../' + p.relative_to(boot).as_posix()) for p in files]
    print('=== PHASE 1/3: reading %d boot payload files on %d processes ===' % (len(work), jobs or os.cpu_count()),
          flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        for i, row in enumerate(pool.map(read_one, work, chunksize=64), 1):
            rows.append(row)
            if i % 4000 == 0:
                print('  %d / %d files' % (i, len(work)), flush=True)
    print('=== PHASE 2/3: world partition (chim-world/chim and the manifest\'s maps) ===', flush=True)
    world = []
    chim = run / 'chim-world' / 'chim'
    if chim.is_dir():
        wfiles = sorted(p for p in chim.rglob('*') if p.is_file())
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            for i, row in enumerate(pool.map(read_one, [(str(p), 'world:' + p.relative_to(chim).as_posix())
                                                        for p in wfiles], chunksize=256), 1):
                world.append(row)
                if i % 8000 == 0:
                    print('  %d / %d world files' % (i, len(wfiles)), flush=True)
    manifest = run / 'image' / 'world-partitions.json'
    if manifest.is_file():
        for part in json.loads(manifest.read_text(encoding='utf-8')).get('partitions', []):
            for f in part.get('files', []):
                world.append({'rel': 'world:' + f['path'], 'bytes': f['bytes'], 'sha': f['sha256'],
                              'kind': kind_of(f['path'])})
    print('=== PHASE 3/3: totals and repeated bytes ===', flush=True)
    by_kind = collections.defaultdict(lambda: [0, 0])
    by_ext = collections.defaultdict(lambda: [0, 0])
    for row in rows + world:
        ext = os.path.splitext(row['rel'])[1].lower() or '(none)'
        by_ext[ext][0] += 1; by_ext[ext][1] += row['bytes']
        if 'sections' in row:
            skin = sum(n for name, n, _ in row['sections'] if name == 'skin')
            by_kind['skins'][1] += skin
            by_kind['models'][0] += 1; by_kind['models'][1] += row['bytes'] - skin
        else:
            by_kind[row['kind']][0] += 1; by_kind[row['kind']][1] += row['bytes']
    groups = collections.defaultdict(list)       # (what, sha) -> [names], with size
    sizes = {}
    for row in rows + world:
        side = 'world' if row['rel'].startswith('world:') else 'boot'
        groups[('file:' + side, row['sha'])].append(row['rel']); sizes[('file:' + side, row['sha'])] = row['bytes']
        for name, n, digest in row.get('sections', ()):
            if name in ('shape-ref',):
                continue
            groups[('mdl-' + name, digest)].append(row['rel']); sizes[('mdl-' + name, digest)] = n
    repeated = []
    for key, names in groups.items():
        if len(names) > 1:
            repeated.append({'what': key[0], 'sha256': key[1][:16], 'copies': len(names), 'bytes_each': sizes[key],
                             'wasted': (len(names) - 1) * sizes[key], 'examples': sorted(names)[:3]})
    repeated.sort(key=lambda g: -g['wasted'])
    by_what = collections.defaultdict(lambda: [0, 0])
    for g in repeated:
        by_what[g['what']][0] += 1; by_what[g['what']][1] += g['wasted']
    tiles = collections.Counter()
    skins = 0
    for row in rows:
        if row.get('tiles'):
            skins += 1; tiles.update(row['tiles'])
    total_tiles = sum(tiles.values())
    out = {
        'run': str(run),
        'hdf_bytes': sum(p.stat().st_size for p in (run / 'image').glob('*.hdf')),
        'boot_payload_bytes': sum(r['bytes'] for r in rows), 'boot_files': len(rows),
        'world_payload_bytes': sum(r['bytes'] for r in world), 'world_files': len(world),
        'by_kind': {k: {'files': v[0], 'bytes': v[1]} for k, v in sorted(by_kind.items(), key=lambda kv: -kv[1][1])},
        'by_extension': {k: {'files': v[0], 'bytes': v[1]} for k, v in
                         sorted(by_ext.items(), key=lambda kv: -kv[1][1])[:30]},
        'repeated_by_what': {k: {'groups': v[0], 'wasted': v[1]} for k, v in by_what.items()},
        'repeated_top': repeated[:top],
        'skin_tiles': {'skins': skins, 'tiles': total_tiles, 'distinct': len(tiles),
                       'bytes': total_tiles * TILE * TILE, 'distinct_bytes': len(tiles) * TILE * TILE},
    }
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run', type=Path)
    parser.add_argument('--top', type=int, default=20)
    parser.add_argument('--jobs', type=int, default=None)
    parser.add_argument('--json', type=Path)
    args = parser.parse_args(argv)
    result = report(args.run, args.top, args.jobs)
    text = json.dumps(result, indent=1)
    if args.json:
        args.json.write_text(text + '\n', encoding='utf-8', newline='\n')
    print(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
