#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Write a CHIM world onto a classic FFS partition, in pack order, read it back and gate its layout.

The same xdftool path as the legacy world partitions (world_volumes.pack:
create, format ffs, makedir, write, then amiga_fs.check_image and a readback
of every file). Files go on in the order the engine reads them: the index,
then per frame its frame file and its sector files in pack order, so each
file is written whole after the previous one (docs/chim/WORLD_FORMAT.md).

On the image the world is one more world volume (AW_WORLD<n>, partition
DW<n>) holding id1/chim/...: the engine adds AW_WORLD0..n-1:id1 to its search
path (world/volumes.awv), so `chim/world.cwi` opens like any game file.

The disk-layout gate (layout_gate) reads the written partition back and
checks the classic FFS rules: every name at most 30 characters, at most 72
entries per directory, every file under 1 GiB, and every file whole (no
block of another file inside its span) and in pack order.

    python3 tools/chim/disk.py OUT/chim PARTITION.hdf [--volume AW_CHIM] [--base chim] [--mib N]
"""
import argparse
import collections
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import format as F  # noqa: E402

MIB = 1024 * 1024
IMAGE_BASE = 'id1/chim'             # where the image keeps the world (engine: chim/ on the search path)


def pack_order(chim_root):
    """Paths below chim/ in the order they go on the disk: the index, then the index's file table order."""
    _, files, _, _ = F.read_index((Path(chim_root) / 'world.cwi').read_bytes())
    return ['world.cwi'] + [f['path'] for f in files]


def partition_mib(payload):
    """Partition size: the world partitions' rule (payload + 20 % + 16 MiB, in 128 MiB steps, at least 128)."""
    mib = max(128, ((payload * 6 // 5 + 16 * MIB + 127 * MIB) // (128 * MIB)) * 128)
    if mib >= 2048:
        raise ValueError('A CHIM partition must stay below 2 GiB')
    return mib


def directories(order, base='chim'):
    """Every directory the files need, parents first."""
    dirs = []
    for rel in [''] + order:
        parts = (base + '/' + rel).split('/')[:-1]
        for k in range(1, len(parts) + 1):
            d = '/'.join(parts[:k])
            if d not in dirs:
                dirs.append(d)
    return dirs


def partition_command(xdftool, part, chim_root, volume, mib, base='chim'):
    """The xdftool command: create, format, directories, then every file in pack order."""
    order = pack_order(chim_root)
    command = [str(xdftool), str(part), 'create', 'size=%dMi' % mib, '+', 'format', volume, 'ffs']
    for d in directories(order, base):
        command += ['+', 'makedir', d]
    for rel in order:
        command += ['+', 'write', str(Path(chim_root) / rel), base + '/' + rel]
    return command


def name_rules(paths):
    """Failures of the name and directory rules over volume paths (and the directories they imply)."""
    fails = []
    children = collections.defaultdict(set)
    for path in paths:
        parts = path.split('/')
        for k, part in enumerate(parts):
            if len(part.encode('latin-1', 'replace')) > F.FFS_NAME_CHARS:
                fails.append('name over %d characters: %s' % (F.FFS_NAME_CHARS, '/'.join(parts[:k + 1])))
            children['/'.join(parts[:k])].add(part.lower())
    for d, names in sorted(children.items()):
        if len(names) > F.FFS_MAX_DIRECTORY_ENTRIES:
            fails.append('directory %s holds %d entries (at most %d)' % (d or '/', len(names),
                                                                         F.FFS_MAX_DIRECTORY_ENTRIES))
    return sorted(set(fails))


def layout_gate(part, paths, partition=None):
    """The disk-layout gate over a written partition (or one partition of a combined hardfile).

    paths: the files in pack order, as volume paths. Positions are counted from
    the start of the packed region (right after the largest gap between file
    blocks, which is the free rest of the disk), wrapping at the end of the
    partition (FFS allocates from the root block in the middle), so a world
    that wraps is still in order. A file is whole when no block of another
    file lies inside its span (directory, root and bitmap blocks may)."""
    from amitools.fs.ADFSVolume import ADFSVolume
    from amitools.fs.FSString import FSString
    from amitools.fs.blkdev.BlkDevFactory import BlkDevFactory
    fails = name_rules(paths)
    device = BlkDevFactory().open(str(part), read_only=True, options={'part': partition} if partition else None)
    try:
        volume = ADFSVolume(device)
        volume.open()
        blocks, sizes = [], []
        for path in paths:
            node = volume.get_file_path_name(FSString(path))
            if node is None:
                fails.append('missing on the volume: ' + path)
                blocks.append([])
                sizes.append(0)
                continue
            blocks.append(list(node.get_block_nums()))
            sizes.append(node.get_size())
        total = device.num_blocks
    finally:
        device.close()
    # The packed files form one region of the cycle; the free rest of the disk is the largest gap
    # between file blocks, and the region starts right after it (independent of the listed order).
    used = sorted({b for bl in blocks for b in bl})
    start = 0
    if used:
        gaps = [((used[(k + 1) % len(used)] - used[k]) % total or total, used[(k + 1) % len(used)])
                for k in range(len(used))]
        start = max(gaps)[1]
    pos = [sorted((b - start) % total for b in bl) for bl in blocks]
    owner = {}
    for i, ps in enumerate(pos):
        for q in ps:
            owner[q] = i
    runs, spans = [], []
    for i, ps in enumerate(pos):
        if not ps:
            runs.append(0)
            spans.append(None)
            continue
        runs.append(1 + sum(1 for a, b in zip(ps, ps[1:]) if b != a + 1))
        spans.append((ps[0], ps[-1]))
        foreign = sorted({owner[q] for q in range(ps[0], ps[-1] + 1) if owner.get(q, i) != i})
        if foreign:
            fails.append('%s is not whole: blocks of %s inside it' % (paths[i], paths[foreign[0]]))
    for i in range(1, len(spans)):
        if spans[i] and spans[i - 1] and spans[i][0] <= spans[i - 1][1]:
            fails.append('%s is not after %s on the disk (pack order)' % (paths[i], paths[i - 1]))
    largest = max(sizes or [0])
    for path, size in zip(paths, sizes):
        if size >= F.FFS_MAX_PACK:
            fails.append('%s is %d bytes (files stay under 1 GiB)' % (path, size))
    names = [p.split('/') for p in paths]
    entries = collections.Counter('/'.join(n[:-1]) for n in names)
    return {'ok': not fails, 'failures': fails, 'files': len(paths), 'largest_file_bytes': largest,
            'longest_name_chars': max((len(part) for n in names for part in n), default=0),
            'most_directory_entries': max(entries.values(), default=0),
            'fragmented_files': sum(1 for r in runs if r > 1), 'most_runs': max(runs or [0]),
            'rules': {'name_chars': F.FFS_NAME_CHARS, 'directory_entries': F.FFS_MAX_DIRECTORY_ENTRIES,
                      'file_bytes_below': F.FFS_MAX_PACK}}


def pack_partition(chim_root, part, volume='AW_CHIM', mib=None, xdftool='xdftool', base='chim'):
    """Write, read back and gate; returns {file, volume, mib, bytes, sha256, files: [{path, bytes, sha256}],
    readback, layout}. Raises ValueError when the readback or the layout gate fails."""
    from amiga_fs import check_image
    from build_windows_xdftool import run_any
    chim_root, part = Path(chim_root), Path(part)
    if part.exists():
        raise ValueError('CHIM partitions are written once: ' + str(part))
    order = pack_order(chim_root)
    paths = [base + '/' + rel for rel in order]
    fails = name_rules(paths)
    if fails:
        raise ValueError('CHIM disk layout: ' + '; '.join(fails[:5]))
    payload = sum((chim_root / rel).stat().st_size for rel in order)
    mib = mib or partition_mib(payload)
    run_any(partition_command(xdftool, part, chim_root, volume, mib, base))
    check_image(part, normalize=True)
    from amitools.fs.ADFSVolume import ADFSVolume
    from amitools.fs.FSString import FSString
    from amitools.fs.blkdev.BlkDevFactory import BlkDevFactory
    files = []
    device = BlkDevFactory().open(str(part), read_only=True)
    try:
        mounted = ADFSVolume(device)
        mounted.open()
        for rel, path in zip(order, paths):
            data = (chim_root / rel).read_bytes()
            if mounted.read_file(FSString(path)) != data:
                raise ValueError('CHIM partition readback mismatch: ' + rel)
            files.append({'path': path, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    finally:
        device.close()
    layout = layout_gate(part, paths)
    if not layout['ok']:
        raise ValueError('CHIM disk layout: ' + '; '.join(layout['failures'][:5]))
    with part.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'file': part.name, 'volume': volume, 'mib': mib, 'bytes': part.stat().st_size, 'sha256': digest,
            'files': files, 'readback': 'passed', 'layout': layout}


def main(argv=None):
    import json
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('chim', type=Path, help='the chim/ folder of a builder output')
    ap.add_argument('partition', type=Path, help='partition image to create')
    ap.add_argument('--volume', default='AW_CHIM')
    ap.add_argument('--base', default='chim', help='folder on the volume (the image uses %s)' % IMAGE_BASE)
    ap.add_argument('--mib', type=int)
    ap.add_argument('--xdftool', default='xdftool')
    a = ap.parse_args(argv)
    receipt = pack_partition(a.chim, a.partition, a.volume, a.mib, a.xdftool, a.base)
    sys.stdout.write(json.dumps(receipt, indent=1) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
