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
  drive grouping's job (world_volumes.plan_drives), gated as before;
- a boot payload over the limit is split (IMAGE-BOOT-PAYLOAD-OVER-2GIB-48): the files the engine opens through
  its search path (common.c COM_FindFile: the boot volume's id1, then AW_WORLD0..7:id1) can live on a world
  volume. They move as units (movable_unit: the CHIM interior store id1/chimi/ as one unit, a map with its
  sidecars, an actor's model with its mover, layout and tag files), the largest first, only as many as DH0
  needs to fit with its headroom; they go into the world volumes first (the CHIM world volume first) and
  only when none has room into a further partition (role "store"). What moves is decided from the measured
  sizes, never from a list; a payload that still cannot fit is refused naming its largest folders. The
  plan records the units each partition takes (moved); the image step follows the plan's placement.

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
# Boot files the engine opens only through its search path, so they may live on any world volume
# (IMAGE-BOOT-PAYLOAD-OVER-2GIB-48): the CHIM interior store (chim_world.c Chim_PackOpen -> COM_FOpenFile), the
# maps and their sidecars (aw_mappath.c, model.c, chim_cuts.c, chim_far.c: COM_FOpenFile) and the actor models
# (model.c, aw_anim.c .anm, aw_items.c .tag: COM_FOpenFile / COM_Load*File). Music (aw_music.c opens
# <gamedir>/music directly), saves, configs and everything else stay on DH0.
STORE_UNITS = ('id1/chimi/',)
ACTOR_PREFIX = 'id1/progs/a_'


def movable_unit(path):
    """The unit a boot-relative PATH moves with to a world volume, or None when it stays on DH0: a whole store
    folder (id1/chimi/), a map with its sidecars (id1/maps/<stem>), an actor model with its mover, layout and tag
    files (id1/progs/a_<id>, the mover a_<id>_m)."""
    path = str(path).replace('\\', '/')
    for store in STORE_UNITS:
        if path.startswith(store) and len(path) > len(store):
            return store
    if path == VOLUMES_FILE:
        return None
    for base in (MAP_BASE, ACTOR_PREFIX[:len('id1/progs/')]):
        if path.startswith(base) and '/' not in path[len(base):]:
            name = path[len(base):]
            if base == MAP_BASE:
                return MAP_BASE + name.split('.', 1)[0]
            if path.startswith(ACTOR_PREFIX):
                stem = name.split('.', 1)[0]
                return base + (stem[:-2] if stem.endswith('_m') else stem)
    return None


def folder_sizes(rows, depth=2):
    """[(folder, bytes, files)] of ROWS (path, bytes) by their first DEPTH path parts, largest first."""
    out = {}
    for path, size in rows:
        parts = str(path).split('/')
        key = '/'.join(parts[:depth]) if len(parts) > depth else (parts[0] if len(parts) > 1 else '/')
        bytes_, files = out.get(key, (0, 0))
        out[key] = (bytes_ + int(size), files + 1)
    return sorted(((k, b, n) for k, (b, n) in out.items()), key=lambda row: (-row[1], row[0]))


def unit_kind(key):
    return 'store' if key in STORE_UNITS else 'map' if key.startswith(MAP_BASE) else 'actor'


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
        self.moved = {}                  # unit key -> bytes of the boot units this partition takes
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
                    largest_directory=dict(path=crowded[0], entries=crowded[1]), maps=sorted(self.maps),
                    moved=sorted(self.moved), moved_bytes=sum(self.moved.values()))


def fits(part, files, limit=PARTITION_LIMIT):
    return part.mib_with(files) * MIB < limit


def unit_rows(rows):
    """{unit key: [(path, bytes)]} of the movable boot ROWS (movable_unit)."""
    units = {}
    for path, size in rows:
        key = movable_unit(path)
        if key is not None:
            units.setdefault(key, []).append((path, size))
    return units


def unit_blocks(rows):
    return sum(file_blocks(size) for _, size in rows)


def plan_compact(boot_files, maps=(), chim_files=None, headroom_mib=DEFAULT_HEADROOM_MIB, boot_headroom_mib=None,
                 limit=PARTITION_LIMIT, follow=None, margin=2):
    """The compact layout of a payload, before anything is written.

    BOOT_FILES: {boot-relative path: bytes} of DH0 without the movable maps; MAPS: [(boot-relative path, bytes)]
    of the open-world maps (id1/maps/...); CHIM_FILES: [(path below chim/, bytes)] of the CHIM world, or None.
    A boot payload over LIMIT moves units of its search-path files (movable_unit) to world volumes, the largest
    first, until DH0 fits; FOLLOW (a plan made earlier, the payload preflight's) puts the units it moved where it
    put them instead of choosing again. Returns the plan record (mode, headroom, partitions in order: DH0, the
    CHIM volume, further world volumes). Raises ValueError naming the payload sizes and the largest boot folders
    when a part cannot fit below LIMIT with its headroom."""
    headroom_mib = int(headroom_mib)
    boot_headroom_mib = headroom_mib if boot_headroom_mib is None else int(boot_headroom_mib)
    if headroom_mib < 0 or boot_headroom_mib < 0:
        raise ValueError('Partition headroom must be zero or more MiB')
    maps = sorted(((str(p), int(b)) for p, b in maps), key=lambda row: row[0])
    boot = Part('DH0', 'AMIWIND', 'boot', boot_headroom_mib)
    boot_rows = sorted((str(p), int(b)) for p, b in boot_files.items() if str(p) != VOLUMES_FILE)
    units = unit_rows(boot_rows)
    probe = Part('DH0', 'AMIWIND', 'boot', boot_headroom_mib)
    probe.add(boot_rows + [(VOLUMES_FILE, VOLUMES_BYTES)])
    largest_first = sorted(units, key=lambda k: (-unit_blocks(units[k]), k))
    planned, chosen = {}, []
    if follow is not None:
        planned = {key: row['partition'] for row in follow.get('partitions', [])[1:] for key in row.get('moved', ())}
        chosen = [k for k in largest_first if k in planned]
    elif not fits(probe, (), limit):
        # the largest units first, until DH0 fits with MARGIN times its headroom: the payload preflight's early plan
        # keeps two (the image step may find DH0 up to one headroom larger than planned, require_follows); a plan made
        # from the finished staging folder keeps one, the same rule require_minimal checks, or the two disagree
        # (IMAGE-LAYOUT-PLAN-ACTOR-LIBRARY-48, rc1-try5: a third partition require_minimal then refused). The blocks of
        # the directories a move empties are still counted here: an upper bound; DH0 is measured exactly below.
        chosen, blocks = [], probe.blocks
        for key in largest_first:
            if size_mib(blocks, margin * boot.headroom) * MIB < limit:
                break
            blocks -= unit_blocks(units[key])
            chosen.append(key)
    moving = set(chosen)
    if chim_files is not None or maps or moving:
        boot_rows.append((VOLUMES_FILE, VOLUMES_BYTES))   # written by the image step when a world volume exists
    boot.add([row for row in boot_rows if movable_unit(row[0]) not in moving])
    if not fits(boot, (), limit):
        total = sum(b for _, b in boot_rows)
        moved = sum(b for k in moving for _, b in units[k])
        detail = 'it cannot be split' if not units else (
            'moving %d of the %d units a world volume can hold (%d bytes: the interior store, maps, actor models) '
            'leaves %d bytes on it, a %d MiB partition' % (len(moving), len(units), moved, total - moved,
                                                         boot.mib_with()))
        raise ValueError('Boot payload %d bytes in %d files + %d MiB headroom needs a %d MiB partition (limit below '
                         '%d bytes, 2 GiB): %s; largest boot folders: %s'
                         % (total, len(boot_rows), boot_headroom_mib, probe.mib_with(), limit, detail,
                            ', '.join('%s %d bytes in %d files' % row for row in folder_sizes(boot.files)[:6])))
    worlds = []
    if chim_files is not None:
        chim = Part('DW0', 'AW_WORLD0', 'chim', headroom_mib)
        chim.add(sorted(('id1/chim/' + str(p), int(b)) for p, b in chim_files))
        if not fits(chim, (), limit):
            raise ValueError('CHIM world payload %d bytes in %d files + %d MiB headroom needs a %d MiB partition '
                             '(limit below %d bytes, 2 GiB)' % (sum(b for _, b in chim.files), len(chim.files),
                                                                headroom_mib, chim.mib_with(), limit))
        worlds.append(chim)
    for key in chosen:
        rows = units[key]
        want = next((part for part in worlds if part.partition == planned.get(key)), None)
        target = want if want is not None and fits(want, rows, limit) else \
            next((part for part in worlds if fits(part, rows, limit)), None)
        if target is None:
            index = len(worlds)
            target = Part('DW%d' % index, 'AW_WORLD%d' % index, 'store', headroom_mib)
            if not fits(target, rows, limit):
                raise ValueError('Boot unit %s is %d bytes in %d files: with %d MiB headroom it does not fit one '
                                 'partition below %d bytes' % (key, sum(b for _, b in rows), len(rows), headroom_mib,
                                                               limit))
            worlds.append(target)
        target.add(rows)
        target.moved[key] = sum(b for _, b in rows)
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
    kinds = {}
    for key in chosen:
        count, size = kinds.get(unit_kind(key), (0, 0))
        kinds[unit_kind(key)] = (count + 1, size + sum(b for _, b in units[key]))
    return dict(format='AmiWind layout plan 1', mode='compact', headroom_mib=headroom_mib,
                boot_headroom_mib=boot_headroom_mib, partition_limit=limit, world_volumes=len(worlds),
                partitions=[part.record() for part in parts],
                payload=sum(sum(b for _, b in part.files) for part in parts),
                split=dict(units=len(chosen), bytes=sum(n for _, n in kinds.values()),
                           kinds={k: dict(units=c, bytes=b) for k, (c, b) in sorted(kinds.items())},
                           boot_payload_before=sum(b for p, b in boot_rows if p != VOLUMES_FILE),
                           boot_folders=[dict(folder=f, bytes=b, files=n)
                                         for f, b, n in folder_sizes(boot_rows)[:12]]))


def require_minimal(plan, limit=PARTITION_LIMIT):
    """Refuse a plan with more partitions than its payload needs: a partition holding only maps whose maps
    (with their directory) would fit into another partition below LIMIT with that partition's headroom."""
    rows = plan['partitions']
    for row in rows:
        if row['role'] not in ('maps', 'store'):
            continue
        for other in rows:
            if other is row:
                continue
            blocks = other['used_blocks'] + row['used_blocks']   # an upper bound: shared directories counted twice
            if size_mib(blocks, other['headroom_mib'] * MIB) * MIB < limit:
                units = ', %d moved units' % len(row.get('moved') or ()) if row['role'] == 'store' else ''
                raise ValueError('More partitions than the payload needs: %s (%d maps%s, payload %d bytes) fits into '
                                 '%s (payload %d bytes) below 2 GiB with its %d MiB headroom'
                                 % (row['partition'], len(row['maps']), units, row['payload'], other['partition'],
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
    payload within its headroom of the planned payload, and no boot unit on another partition than planned. A refusal
    names the partition, both payloads and the headroom. SHRINK: {partition: bytes} the image step stored once after
    the plan was made (tools/payload_share.py), added back before the comparison, so a payload made smaller on purpose
    still follows its plan; the bytes are added back to the partitions that came out smaller than planned, DH0
    first (a file stored once may be one a world volume took from DH0)."""
    pool = sum(int(v) for v in (shrink or {}).values())
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
        # a unit planned elsewhere is a moved unit; a planned unit the payload no longer has is not (stored once)
        stray = sorted(set(a.get('moved') or ()) - set(p.get('moved') or ()))
        if stray:
            problems.append('%s holds boot units not planned there (%d, first %s)'
                            % (p['partition'], len(stray), ', '.join(stray[:4])))
        delta = a['payload'] - p['payload']
        if delta < 0 and pool:
            back = min(-delta, pool)
            delta, pool = delta + back, pool - back
        if abs(delta) > p['headroom_mib'] * MIB:
            problems.append('%s payload %d bytes, planned %d bytes: %+d bytes, more than its %d MiB headroom'
                            % (p['partition'], a['payload'], p['payload'], delta, p['headroom_mib']))
    if problems:
        raise ValueError('The staged payload no longer matches the layout plan: ' + '; '.join(problems))
    return True


def follows_or_grew(planned, actual, shrink=None):
    """None when ACTUAL follows PLANNED (require_follows); (bytes grown, the mismatch) when it does not only because the
    payload grew after the plan was made; any other mismatch raises. IMAGE-LAYOUT-PLAN-ACTOR-LIBRARY-48: the payload
    preflight plans before the image step writes the room actors; the v0.0.48-rc1 boot payload grew from 2.45 to
    3.01 GB inside the step and needed a third partition, and the image stopped on a plan that could not see it. Then
    rc1-try4, planned at 3 partitions, stopped the other way: the image's payload sharing (shared skins, file aliases)
    took 156 MB off after the plan and the maps moved between DW0 and DW1. A payload that CHANGED after the plan, in
    either direction, is laid out from the staged files: require_minimal and the headroom gate on the written
    partitions still decide whether it fits. Still refused: another mode or headroom, a partition role the plan had
    and the payload lost, and a mismatch with no change of payload at all (a planning bug, not a later step)."""
    try:
        require_follows(planned, actual, shrink=shrink)
        return None
    except ValueError as exc:
        changed = sum(r['payload'] for r in actual['partitions']) - sum(r['payload'] for r in planned['partitions'])
        lost = {r['role'] for r in planned['partitions']} - {r['role'] for r in actual['partitions']}
        if not changed or lost or planned.get('mode') != actual.get('mode') or any(
                planned.get(key) != actual.get(key) for key in ('headroom_mib', 'boot_headroom_mib')):
            raise
        return changed, str(exc)


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


def assign_units(plan, paths):
    """{partition: [(path, boot-relative path)]} of the boot PATHS (boot-relative path strings or (path, rel) pairs)
    whose unit (movable_unit) the plan moved to a world volume; the other paths are not listed."""
    where = {key: row['partition'] for row in plan['partitions'][1:] for key in row.get('moved') or ()}
    out = {row['partition']: [] for row in plan['partitions'][1:]}
    for item in paths:
        path, rel = item if isinstance(item, tuple) else (item, item)
        key = movable_unit(rel)
        if key in where:
            out[where[key]].append((path, rel))
    return out


def lines(plan):
    """Printable plan: one summary line, the boot split when there is one, and one line per partition."""
    rows = plan['partitions']
    head = 'Layout plan (%s): %d partition%s, headroom %d MiB per partition%s' % (
        plan['mode'], len(rows), '' if len(rows) == 1 else 's', plan['headroom_mib'],
        '' if plan['boot_headroom_mib'] == plan['headroom_mib'] else ', DH0 %d MiB' % plan['boot_headroom_mib'])
    out = [head]
    split = plan.get('split') or {}
    if split.get('units'):
        out.append('  Boot payload %d bytes is over one partition: %d units (%d bytes) moved to world volumes: %s; '
                   'largest boot folders: %s'
                   % (split['boot_payload_before'], split['units'], split['bytes'],
                      ', '.join('%s %d (%d bytes)' % (k, v['units'], v['bytes']) for k, v in split['kinds'].items()),
                      ', '.join('%s %d bytes' % (f['folder'], f['bytes']) for f in split['boot_folders'][:6])))
    for r in rows:
        out.append('  %s %s (%s): payload %d bytes in %d files + headroom -> %d MiB, %d bytes free (%.1f %%), '
                   'largest directory %s %d entries%s%s'
                   % (r['partition'], r['volume'], r['role'], r['payload'], r['files'], r['mib'], r['free_bytes'],
                      100 * r['free_share'], r['largest_directory']['path'], r['largest_directory']['entries'],
                      ', %d maps' % len(r['maps']) if r['maps'] else '',
                      ', %d boot units (%d bytes)' % (len(r['moved']), r['moved_bytes']) if r.get('moved') else ''))
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
    """[(PREFIX + relative posix path, bytes)] of every file under FOLDER, in path order (by path parts, as sorted
    Path objects order). One os.walk with string paths (BUILD-IMAGE-UNDERUSED-32: the pathlib walk of the CHIM
    world's 37,000 files took 4 s on one core in each payload preflight); AMIWIND_LAYOUT_WALK=pathlib keeps the
    method before. The same list either way."""
    import os
    if os.environ.get('AMIWIND_LAYOUT_WALK', 'os') == 'pathlib':
        return _walk_pathlib(folder, prefix)
    root = os.fspath(folder)
    found = []
    for top, _, names in os.walk(root):
        rel = os.path.relpath(top, root).replace(os.sep, '/')
        base = '' if rel == '.' else rel + '/'
        for name in names:
            path = os.path.join(top, name)
            if os.path.isfile(path):
                found.append((base + name, path))
    found.sort(key=lambda row: row[0].split('/'))
    return [(prefix + rel, os.stat(path).st_size) for rel, path in found]


def _walk_pathlib(folder, prefix=''):
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
