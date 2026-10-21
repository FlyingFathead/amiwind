#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Disk layout planner: the fewest partitions the payload needs, each sized from its payload plus headroom.

The image step used to size every partition as payload + 20 % + 16 MiB in 128 MiB steps, and to split
the open-world maps from the boot partition by halving the payload (a rule from the legacy region maps,
which were half the game). On an all-CHIM build that left a 128 MiB partition holding only the 1.1 MB of
CHIM region frame maps, 98 % empty (BUILD-PARTITION-GROWTH-UNGATED-36). This planner replaces both rules
(layout "compact", the default; the previous rules stay selectable as layout "legacy"):

- units: the boot payload (DH0, everything the game reads from its own volume), the CHIM world (one
  volume, files under id1/chim/) and the open-world maps listed in the region directory (id1/maps/vfNNNN.*,
  movable: the engine finds a map on any world volume, world/volumes.awv);
- the maps go into the CHIM world volume first (they are CHIM world data), then into DH0, and only when
  neither has room a further world partition is opened;
- every partition is sized from its payload: the classic FFS blocks its files take (header, data and
  extension blocks, one block per directory, root and bitmap blocks) plus a fixed HEADROOM of free space
  (default 100 MiB, builder setting partition_headroom_mib; the boot partition can have its own,
  boot_partition_headroom_mib, for saves and settings), rounded up to whole MiB;
- the Amiga limits win: a partition stays below 2 GiB; if payload + headroom does not fit, another
  partition is opened, the headroom is never shrunk. Partition starts and drives below 4 GiB are the
  drive grouping's job (world_volumes.plan_drives), gated as before.

The plan is made by the payload preflight before the image step writes anything (seconds: file sizes
only), printed, and written to the run as layout-plan.json; the image step follows it (same partitions,
same maps in each) and refuses when a partition's payload moved by more than its headroom since the plan.
After writing, the gate refuses a partition with less free space than its headroom, one that is mostly
empty (over 16 MiB and more than headroom + half its size free), and a plan with a partition whose
maps would fit into another one (more partitions than the payload needs).

    python3 tools/layout_plan.py --boot DIR [--chim DIR] [--maps DIR] [--headroom-mib N] [--boot-headroom-mib N]
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

MIB = 1024 * 1024
BLOCK = 512                      # classic FFS block (xdftool format ... ffs): 512 data bytes per data block
POINTERS = 72                    # data block pointers in a file header or an extension block
BITS_PER_BITMAP_BLOCK = 127 * 32  # one bitmap block: a checksum long + 127 longs of bits
ROOT_BITMAP_POINTERS = 25
RESERVED_BLOCKS = 2              # boot blocks
LAYOUTS = ('compact', 'legacy')
DEFAULT_LAYOUT = 'compact'
DEFAULT_HEADROOM_MIB = 100
# Below 2 GiB (world_volumes.PARTITION_SIZE_LIMIT), partitions are whole MiB: the largest is 2 GiB - 1 MiB.
PARTITION_LIMIT = 2 * 1024 ** 3
SMALL_PARTITION = 16 * MIB       # the mostly-empty check applies above this size
VOLUMES_FILE = 'id1/world/volumes.awv'
VOLUMES_BYTES = 5
MAP_BASE = 'id1/maps/'


def file_blocks(size):
    """Blocks one file takes on classic FFS: its header, its data blocks and its extension blocks."""
    data = -(-int(size) // BLOCK)
    extension = -(-(data - POINTERS) // POINTERS) if data > POINTERS else 0
    return 1 + data + extension


def directories(paths):
    """The directories PATHS imply (the root not counted), lower case as FFS compares them."""
    found = set()
    for path in paths:
        parts = str(path).replace('\\', '/').strip('/').split('/')
        for k in range(1, len(parts)):
            found.add('/'.join(parts[:k]).lower())
    return found


def bitmap_blocks(total):
    """Bitmap blocks (and their extension blocks) of a volume of TOTAL blocks."""
    bitmap = -(-(total - RESERVED_BLOCKS) // BITS_PER_BITMAP_BLOCK)
    extension = -(-(bitmap - ROOT_BITMAP_POINTERS) // 127) if bitmap > ROOT_BITMAP_POINTERS else 0
    return bitmap + extension


def free_bytes(mib, used_blocks):
    """Free bytes of a MIB-MiB volume whose files and directories take USED_BLOCKS blocks."""
    total = mib * MIB // BLOCK
    return (total - RESERVED_BLOCKS - 1 - bitmap_blocks(total) - used_blocks) * BLOCK


def size_mib(used_blocks, headroom_bytes):
    """The smallest whole-MiB partition that leaves at least HEADROOM_BYTES free."""
    mib = max(1, -(-(used_blocks * BLOCK + int(headroom_bytes)) // MIB))
    while free_bytes(mib, used_blocks) < headroom_bytes:
        mib += 1
    return mib


class Part:
    """One planned partition: its files (path, bytes), the blocks they take and the size it needs."""

    def __init__(self, partition, volume, role, headroom_mib):
        self.partition, self.volume, self.role = partition, volume, role
        self.headroom_mib = int(headroom_mib)
        self.files, self.maps, self.dirs = [], [], set()
        self.blocks = 0

    @property
    def headroom(self):
        return self.headroom_mib * MIB

    def cost(self, files):
        """Blocks FILES add to this partition (their blocks and the directories new to it)."""
        return sum(file_blocks(size) for _, size in files) + len(directories([p for p, _ in files]) - self.dirs)

    def add(self, files, maps=()):
        files = list(files)
        self.blocks += self.cost(files)
        self.dirs |= directories([p for p, _ in files])
        self.files += files
        self.maps += list(maps)

    def mib_with(self, files=()):
        return size_mib(self.blocks + (self.cost(files) if files else 0), self.headroom)

    def record(self):
        mib = self.mib_with()
        entries = {}
        for path, _ in self.files:
            parent = path.rsplit('/', 1)[0] if '/' in path else '/'
            entries[parent] = entries.get(parent, 0) + 1
        crowded = max(entries.items(), key=lambda item: (item[1], item[0]), default=('/', 0))
        payload = sum(size for _, size in self.files)
        free = free_bytes(mib, self.blocks)
        return dict(partition=self.partition, volume=self.volume, role=self.role, files=len(self.files),
                    payload=payload, used_blocks=self.blocks, mib=mib, bytes=mib * MIB, free_bytes=free,
                    free_share=round(free / (mib * MIB), 4), headroom_mib=self.headroom_mib,
                    largest_file=max((size for _, size in self.files), default=0),
                    largest_directory=dict(path=crowded[0], entries=crowded[1]), maps=sorted(self.maps))


def fits(part, files, limit=PARTITION_LIMIT):
    return part.mib_with(files) * MIB < limit


def plan_compact(boot_files, maps=(), chim_files=None, headroom_mib=DEFAULT_HEADROOM_MIB, boot_headroom_mib=None,
                 limit=PARTITION_LIMIT):
    """The compact layout of a payload, before anything is written.

    BOOT_FILES: {boot-relative path: bytes} of DH0 without the movable maps; MAPS: [(boot-relative path, bytes)]
    of the open-world maps (id1/maps/...); CHIM_FILES: [(path below chim/, bytes)] of the CHIM world, or None.
    Returns the plan record (mode, headroom, partitions in order: DH0, the CHIM volume, map volumes). Raises
    ValueError naming the payload sizes when a unit cannot fit below LIMIT with its headroom."""
    headroom_mib = int(headroom_mib)
    boot_headroom_mib = headroom_mib if boot_headroom_mib is None else int(boot_headroom_mib)
    if headroom_mib < 0 or boot_headroom_mib < 0:
        raise ValueError('Partition headroom must be zero or more MiB')
    maps = sorted(((str(p), int(b)) for p, b in maps), key=lambda row: row[0])
    boot = Part('DH0', 'AMIWIND', 'boot', boot_headroom_mib)
    boot_rows = sorted((str(p), int(b)) for p, b in boot_files.items() if str(p) != VOLUMES_FILE)
    if chim_files is not None or maps:
        boot_rows.append((VOLUMES_FILE, VOLUMES_BYTES))   # written by the image step when a world volume exists
    boot.add(boot_rows)
    if not fits(boot, (), limit):
        raise ValueError('Boot payload %d bytes in %d files + %d MiB headroom needs a %d MiB partition (limit below '
                         '%d bytes, 2 GiB): it cannot be split' % (sum(b for _, b in boot_rows), len(boot_rows),
                                                                    boot_headroom_mib, boot.mib_with(), limit))
    worlds = []
    if chim_files is not None:
        chim = Part('DW0', 'AW_WORLD0', 'chim', headroom_mib)
        chim.add(sorted(('id1/chim/' + str(p), int(b)) for p, b in chim_files))
        if not fits(chim, (), limit):
            raise ValueError('CHIM world payload %d bytes in %d files + %d MiB headroom needs a %d MiB partition '
                             '(limit below %d bytes, 2 GiB)' % (sum(b for _, b in chim.files), len(chim.files),
                                                                headroom_mib, chim.mib_with(), limit))
        worlds.append(chim)
    order = worlds + [boot]
    for path, size in maps:
        row = [(path, size)]
        name = path.rsplit('/', 1)[-1]
        target = next((part for part in order if fits(part, row, limit)), None)
        if target is None:
            index = len(worlds)
            target = Part('DW%d' % index, 'AW_WORLD%d' % index, 'maps', headroom_mib)
            if not fits(target, row, limit):
                raise ValueError('World map %s is %d bytes: with %d MiB headroom it does not fit one partition '
                                 'below %d bytes' % (path, size, headroom_mib, limit))
            worlds.append(target)
            order.append(target)
        target.add(row, [name])
    if len(worlds) > 8:
        raise ValueError('World payload needs %d world volumes; the engine reads at most 8' % len(worlds))
    parts = [boot] + worlds
    return dict(format='AmiWind layout plan 1', mode='compact', headroom_mib=headroom_mib,
                boot_headroom_mib=boot_headroom_mib, partition_limit=limit, world_volumes=len(worlds),
                partitions=[part.record() for part in parts],
                payload=sum(sum(b for _, b in part.files) for part in parts))


def require_minimal(plan, limit=PARTITION_LIMIT):
    """Refuse a plan with more partitions than its payload needs: a partition holding only maps whose maps
    (with their directory) would fit into another partition below LIMIT with that partition's headroom."""
    rows = plan['partitions']
    for row in rows:
        if row['role'] != 'maps':
            continue
        for other in rows:
            if other is row:
                continue
            blocks = other['used_blocks'] + row['used_blocks']   # an upper bound: shared directories counted twice
            if size_mib(blocks, other['headroom_mib'] * MIB) * MIB < limit:
                raise ValueError('More partitions than the payload needs: %s (%d maps, payload %d bytes) fits into %s '
                                 '(payload %d bytes) below 2 GiB with its %d MiB headroom'
                                 % (row['partition'], len(row['maps']), row['payload'], other['partition'],
                                    other['payload'], other['headroom_mib']))
    return True


def require_headroom(receipts, plan):
    """The headroom gate on partitions as written (readback receipts: partition, bytes, payload_bytes, free_bytes):
    every partition keeps at least its headroom free, and none over 16 MiB is mostly empty (more free than its
    headroom plus half its size). A refusal names the partition, its payload and its free bytes."""
    headroom = {row['partition']: row['headroom_mib'] * MIB for row in plan['partitions']}
    problems = []
    for r in receipts:
        if r['partition'] not in headroom:
            problems.append('%s is not in the layout plan' % r['partition'])
            continue
        want, free, size = headroom[r['partition']], int(r['free_bytes']), int(r['bytes'])
        if free < want:
            problems.append('%s has %d bytes free, below its headroom of %d bytes (payload %d bytes, partition %d bytes)'
                            % (r['partition'], free, want, r.get('payload_bytes', 0), size))
        if size > SMALL_PARTITION and free > want + size // 2:
            problems.append('%s is mostly empty: %d of %d bytes free, over its headroom of %d bytes + half its size '
                            '(payload %d bytes)' % (r['partition'], free, size, want, r.get('payload_bytes', 0)))
    if problems:
        raise ValueError('Disk layout gate (headroom): ' + '; '.join(problems))
    return dict(ok=True, partitions=len(receipts))


def require_follows(planned, actual, shrink=None):
    """The image step follows the plan: the same partitions with the same roles and maps, and every partition's
    payload within its headroom of the planned payload. A refusal names the partition, both payloads and the
    headroom. SHRINK: {partition: bytes} the image step stored once after the plan was made (tools/payload_share.py),
    added back before the comparison, so a payload made smaller on purpose still follows its plan."""
    shrink = shrink or {}
    if planned.get('mode') != actual.get('mode'):
        raise ValueError('Layout plan is %s, the image step lays out %s' % (planned.get('mode'), actual.get('mode')))
    for key in ('headroom_mib', 'boot_headroom_mib'):
        if planned.get(key) != actual.get(key):
            raise ValueError('Layout plan %s is %s, the image step has %s' % (key, planned.get(key), actual.get(key)))
    want = [(r['partition'], r['role']) for r in planned['partitions']]
    have = [(r['partition'], r['role']) for r in actual['partitions']]
    if want != have:
        raise ValueError('Layout plan has partitions %s, the staged payload needs %s'
                         % (', '.join('%s (%s)' % row for row in want), ', '.join('%s (%s)' % row for row in have)))
    problems = []
    for p, a in zip(planned['partitions'], actual['partitions']):
        if p['maps'] != a['maps']:
            moved = sorted(set(p['maps']) ^ set(a['maps']))
            problems.append('%s holds other maps than planned (%d differ, first %s)'
                            % (p['partition'], len(moved), ', '.join(moved[:4])))
        delta = a['payload'] + int(shrink.get(p['partition'], 0)) - p['payload']
        if abs(delta) > p['headroom_mib'] * MIB:
            problems.append('%s payload %d bytes, planned %d bytes: %+d bytes, more than its %d MiB headroom'
                            % (p['partition'], a['payload'], p['payload'], delta, p['headroom_mib']))
    if problems:
        raise ValueError('The staged payload no longer matches the layout plan: ' + '; '.join(problems))
    return True


def assign(plan, maps):
    """{partition: [map paths]} of MAPS (boot-relative paths) as the plan places them; maps the plan does not
    name stay with DH0's files only if the plan put them there (else ValueError)."""
    where = {name: row['partition'] for row in plan['partitions'] for name in row['maps']}
    out = {row['partition']: [] for row in plan['partitions']}
    for path in maps:
        name = str(path).replace('\\', '/').rsplit('/', 1)[-1]
        if name not in where:
            raise ValueError('World map %s is not in the layout plan' % name)
        out[where[name]].append(path)
    return out


def lines(plan):
    """Printable plan: one summary line and one line per partition."""
    rows = plan['partitions']
    head = 'Layout plan (%s): %d partition%s, headroom %d MiB per partition%s' % (
        plan['mode'], len(rows), '' if len(rows) == 1 else 's', plan['headroom_mib'],
        '' if plan['boot_headroom_mib'] == plan['headroom_mib'] else ', DH0 %d MiB' % plan['boot_headroom_mib'])
    out = [head]
    for r in rows:
        out.append('  %s %s (%s): payload %d bytes in %d files + headroom -> %d MiB, %d bytes free (%.1f %%), '
                   'largest directory %s %d entries%s'
                   % (r['partition'], r['volume'], r['role'], r['payload'], r['files'], r['mib'], r['free_bytes'],
                      100 * r['free_share'], r['largest_directory']['path'], r['largest_directory']['entries'],
                      ', %d maps' % len(r['maps']) if r['maps'] else ''))
    return out


def resolve(layout=None, headroom_mib=None, boot_headroom_mib=None, config=None):
    """The layout settings: CLI values over the build config over config/build-defaults.json (disk_layout,
    partition_headroom_mib, boot_partition_headroom_mib)."""
    values = {}
    for path in (ROOT / 'config/build-defaults.json', config):
        if path and Path(path).is_file():
            values.update(json.loads(Path(path).read_text(encoding='utf-8')))
    out = dict(mode=layout or values.get('disk_layout', DEFAULT_LAYOUT),
               headroom_mib=values.get('partition_headroom_mib', DEFAULT_HEADROOM_MIB) if headroom_mib is None
               else headroom_mib,
               boot_headroom_mib=values.get('boot_partition_headroom_mib') if boot_headroom_mib is None
               else boot_headroom_mib)
    if out['mode'] not in LAYOUTS:
        raise ValueError('disk_layout must be compact or legacy, not %r' % (out['mode'],))
    for key in ('headroom_mib', 'boot_headroom_mib'):
        value = out[key]
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            raise ValueError('%s must be a whole number of MiB (0 or more), not %r' % (key, value))
    if out['boot_headroom_mib'] is None:
        out['boot_headroom_mib'] = out['headroom_mib']
    return out


def walk(folder, prefix=''):
    folder = Path(folder)
    return [(prefix + p.relative_to(folder).as_posix(), p.stat().st_size)
            for p in sorted(folder.rglob('*')) if p.is_file()]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--boot', type=Path, required=True, help='the staged boot payload (a run\'s image/boot)')
    ap.add_argument('--chim', type=Path, help='the CHIM world folder (chim-world/chim)')
    ap.add_argument('--maps', type=Path, action='append', default=[],
                    help='a folder of open-world maps to place (repeatable); maps under --boot/id1/maps are not moved')
    ap.add_argument('--headroom-mib', type=int)
    ap.add_argument('--boot-headroom-mib', type=int)
    ap.add_argument('--json', type=Path, help='write the plan here')
    a = ap.parse_args(argv)
    settings = resolve('compact', a.headroom_mib, a.boot_headroom_mib)
    maps = [(MAP_BASE + name, size) for folder in a.maps for name, size in walk(folder)]
    plan = plan_compact(dict(walk(a.boot)), maps, walk(a.chim) if a.chim else None,
                        settings['headroom_mib'], settings['boot_headroom_mib'])
    require_minimal(plan)
    from world_volumes import plan_drives
    drives = plan_drives(dict(partition='DH0', bytes=plan['partitions'][0]['bytes'], files=[]),
                         [dict(partition=r['partition'], bytes=r['bytes'], files=[]) for r in plan['partitions'][1:]])
    plan['drives'] = [dict(file=d['file'], bytes=d['bytes'], partitions=[m['partition'] for m in d['members']])
                      for d in drives]
    for line in lines(plan):
        print(line)
    print('Drives: ' + '; '.join('%s %d bytes (%s)' % (d['file'], d['bytes'], ', '.join(d['partitions']))
                                 for d in plan['drives']))
    if a.json:
        a.json.write_text(json.dumps(plan, indent=1) + '\n', encoding='utf-8', newline='\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
