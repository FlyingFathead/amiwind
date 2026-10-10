#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Prepare terrain partitions for legacy-compatible RDB hardfiles."""
import hashlib
import json
import os
from pathlib import Path
import struct
from amiga_fs import check_image

PAYLOAD_LIMIT = 1536 * 1024 * 1024
RDB_BYTES = 32768
# Kickstart 3.1's ROM FastFileSystem does not mount a partition whose first byte lies at or
# beyond 2 GiB of its drive: the device mounts, the volume never appears ("Not a DOS disk",
# then "Please insert volume AW_WORLDn"). A partition may END beyond 2 GiB. Measured in FS-UAE
# 3.1.66 with the Kickstart 3.1 ROM (BUILD-WORLD-PARTITION-MOUNT-33).
PARTITION_START_LIMIT = 2 * 1024**3
# The other Amiga limits every drive image obeys (classic FFS, Kickstart 3.1): a partition below
# 2 GiB, every file well under the 2 GiB file limit (PAKs stay near 1 GiB), a drive below 4 GiB
# (BUILD-WORLD-PARTITION-MOUNT-33).
PARTITION_SIZE_LIMIT = 2 * 1024**3
FILE_SIZE_LIMIT = 1024**3
DRIVE_SIZE_LIMIT = 4 * 1024**3
MIB = 1024 * 1024


def partition_mib(payload_bytes):
    """Size in MiB of the partition the image step writes for PAYLOAD_BYTES of files (boot and world
    partitions alike): payload + 20 % + 16 MiB for filesystem metadata and saves, rounded up to
    128 MiB, at least 128 MiB."""
    return max(128, ((payload_bytes * 6 // 5 + 16 * MIB + 127 * MIB) // (128 * MIB)) * 128)


def balanced(paths, boot_bytes, limit=PAYLOAD_LIMIT):
    paths=sorted(paths)
    if not paths or boot_bytes<0:raise ValueError('Invalid partition inputs')
    target=(boot_bytes+sum(p.stat().st_size for p in paths)+1)//2
    keep=0;used=boot_bytes
    while keep<len(paths)-1 and used+paths[keep].stat().st_size<=target:
        used+=paths[keep].stat().st_size;keep+=1
    rest=paths[keep:]
    if used>limit or sum(p.stat().st_size for p in rest)>limit:
        raise ValueError('Payload exceeds the two-partition budget; optimize or revise the layout')
    return paths[:keep],rest


def partition_batches(paths, boot_bytes, limit=PAYLOAD_LIMIT):
    """Preserve the two-partition layout when it fits; otherwise use more volumes."""
    paths = sorted(paths)
    if not paths or not 0 <= boot_bytes <= limit:
        raise ValueError('Invalid or oversized boot payload')
    if any(p.stat().st_size > limit for p in paths):
        raise ValueError('Individual world map exceeds the partition budget')
    try:
        kept, additional = balanced(paths, boot_bytes, limit)
        return kept, [additional]
    except ValueError:
        pass
    kept, batches, current = [], [], []
    used = boot_bytes
    filling_boot = True
    for path in paths:
        size = path.stat().st_size
        if filling_boot and used + size <= limit:
            kept.append(path)
            used += size
            continue
        if filling_boot:
            filling_boot = False
            used = 0
        if current and used + size > limit:
            batches.append(current)
            current, used = [], 0
        current.append(path)
        used += size
    if current:
        batches.append(current)
    if len(batches) > 8:
        raise ValueError('World payload exceeds the eight-volume runtime limit')
    return kept, batches


def partition_starts(base, members):
    """Byte offset of each partition of a drive whose first world partition starts at `base`."""
    starts = []
    for member in members:
        starts.append(base)
        base += member['bytes']
    return starts


def drive_order(base, members, limit=4 * 1024**3, start_limit=PARTITION_START_LIMIT):
    """The members as one drive: in the given order when the drive stays below `limit` and
    every partition starts below `start_limit`; otherwise with the largest partition last
    (the order that keeps the last start lowest); None when neither fits."""
    if base + sum(m['bytes'] for m in members) >= limit:
        return None
    orders = [list(members)]
    if members:
        big = max(range(len(members)), key=lambda i: (members[i]['bytes'], i))
        orders.append(members[:big] + members[big + 1:] + [members[big]])
    for order in orders:
        if all(start < start_limit for start in partition_starts(base, order)):
            return order
    return None


def hardfile_groups(boot_bytes, worlds, limit=4 * 1024**3, start_limit=PARTITION_START_LIMIT):
    """Group complete partitions into safe RDB drives, retaining a boot-first layout: each
    drive stays below `limit` and every partition starts below `start_limit` (Kickstart 3.1
    FFS mount limit). A layout that already fits keeps its order byte for byte."""
    if boot_bytes + RDB_BYTES >= limit:
        raise ValueError('Boot partition exceeds the legacy hardfile limit')
    groups, current, base = [], [], boot_bytes + RDB_BYTES
    for world in worlds:
        if world['bytes'] + RDB_BYTES >= limit:
            raise ValueError('World partition exceeds the legacy hardfile limit')
        placed = drive_order(base, current + [world], limit, start_limit)
        if placed is None:
            groups.append(current)
            current, base = [world], RDB_BYTES
        else:
            current = placed
    groups.append(current)
    return groups


def require_mountable(receipts, start_limit=PARTITION_START_LIMIT):
    """Gate on the partition table as written (readback receipts): every partition must start
    below 2 GiB of its drive, or Kickstart 3.1 never mounts its volume."""
    late = [r for r in receipts if r['offset_bytes'] >= start_limit]
    if late:
        raise ValueError('Partition starts at or beyond 2 GiB of its drive (Kickstart 3.1 does not mount it): '
                         + ', '.join('%s %s at %d' % (r.get('hdf_file', '?'), r['partition'], r['offset_bytes'])
                                     for r in late))
    return dict(start_limit=start_limit, partitions=len(receipts), ok=True)


# One FFS directory block has 72 hash chains (the same figure as the CHIM layout gate, chim/format.py
# FFS_MAX_DIRECTORY_ENTRIES). More entries in one directory are legal but slow to open on a real disk
# (FFS-DIRECTORY-HASH-32): the layout gate measures every directory and reports the crowded ones.
DIRECTORY_HASH_CHAINS = 72


def directory_entries(paths):
    """{directory: number of entries} over volume PATHS (files and the directories they imply)."""
    children = {}
    for path in paths:
        parts = str(path).replace('\\', '/').strip('/').split('/')
        for k, part in enumerate(parts):
            children.setdefault('/'.join(parts[:k]) or '/', set()).add(part.lower())
    return {d: len(names) for d, names in children.items()}


def require_disk_layout(drive, drive_bytes, receipts, partitions=()):
    """The disk-layout gate on one drive as written (readback receipts; PARTITIONS: the partition
    payloads with their file lists): every partition starts below 2 GiB of its drive and is below
    2 GiB, every file is below FILE_SIZE_LIMIT (well under the 2 GiB file limit), the drive is below
    4 GiB. A violation names the drive, partition or file, the measured value and the limit. Returns
    the measured layout for the build receipt (BUILD-WORLD-PARTITION-MOUNT-33)."""
    largest, crowded = {}, {}
    for part in partitions:
        rows = [(f['bytes'], f.get('path') or f.get('name')) for f in part.get('files') or []]
        largest[part['partition']] = max(rows, default=(0, None))
        crowded[part['partition']] = directory_entries([path for _, path in rows if path])
    problems, rows = [], []
    if drive_bytes >= DRIVE_SIZE_LIMIT:
        problems.append('drive %s is %d bytes (limit below %d, 4 GiB)' % (drive, drive_bytes, DRIVE_SIZE_LIMIT))
    for r in receipts:
        size, path = largest.get(r['partition'], (0, None))
        entries = crowded.get(r['partition'], {})
        rows.append(dict(partition=r['partition'], start_bytes=r['offset_bytes'], bytes=r['bytes'],
                         largest_file=path, largest_file_bytes=size,
                         max_directory_entries=max(entries.values(), default=0),
                         crowded_directories={d: n for d, n in sorted(entries.items()) if n > DIRECTORY_HASH_CHAINS}))
        if r['offset_bytes'] >= PARTITION_START_LIMIT:
            problems.append('%s %s starts at %d (limit below %d, 2 GiB: Kickstart 3.1 does not mount it)'
                            % (drive, r['partition'], r['offset_bytes'], PARTITION_START_LIMIT))
        if r['bytes'] >= PARTITION_SIZE_LIMIT:
            problems.append('%s %s is %d bytes (limit below %d, 2 GiB)' % (drive, r['partition'], r['bytes'],
                                                                        PARTITION_SIZE_LIMIT))
        if size >= FILE_SIZE_LIMIT:
            problems.append('%s %s file %s is %d bytes (limit below %d, 1 GiB)' % (drive, r['partition'], path, size,
                                                                                FILE_SIZE_LIMIT))
    if problems:
        raise ValueError('Disk layout gate (Amiga limits): ' + '; '.join(problems))
    return dict(file=drive, bytes=drive_bytes, partitions=rows, ok=True,
                limits=dict(partition_start=PARTITION_START_LIMIT, partition=PARTITION_SIZE_LIMIT,
                            file=FILE_SIZE_LIMIT, drive=DRIVE_SIZE_LIMIT))


def planned_partition(partition, files, volume=None, **extra):
    """A partition as the image step will write it, before anything is written: FILES are dicts with
    path and bytes; bytes = the size its writer creates (partition_mib)."""
    files = list(files)
    return dict(extra, partition=partition, volume=volume, files=files,
                bytes=partition_mib(sum(f['bytes'] for f in files)) * MIB)


def require_partition_plans(planned):
    """Each planned world partition on its own, before its writer copies a byte (the drive grouping
    is not known yet): the partition below 2 GiB, every file below FILE_SIZE_LIMIT (the same gate)."""
    return [require_disk_layout('%s (planned)' % (p.get('volume') or p['partition']), p['bytes'] + RDB_BYTES,
                                [dict(partition=p['partition'], offset_bytes=RDB_BYTES, bytes=p['bytes'])], [p])
            for p in planned]


def plan_drives(boot, worlds, name=lambda index: 'drive-%02d.hdf' % index, groups=None):
    """Plan every drive and gate the plan before any drive is written. BOOT (the planned DH0) comes
    first on drive 0; WORLDS (planned or written partitions) are grouped by hardfile_groups. GROUPS
    replaces that grouping: only the layout self-test uses it, to prove the gate refuses layouts the
    grouping never makes. Partitions sit where rdbtool puts them (one 32 KiB RDB cylinder, then back
    to back); require_disk_layout runs on that plan, so a layout over an Amiga limit stops the build
    before an image is written and large or sparse inputs are never copied. NAME(index) gives the
    drive file. Returns one dict per drive: file, members, mib, bytes and the gated layout."""
    if groups is None:
        groups = hardfile_groups(boot['bytes'], worlds)
    plans = []
    for index, volumes in enumerate(groups):
        members = ([boot] if index == 0 else []) + list(volumes)
        mib = sum(m['bytes'] // MIB for m in members)
        drive_bytes = mib * MIB + RDB_BYTES
        receipts = [dict(partition=m['partition'], offset_bytes=start, bytes=m['bytes'])
                    for m, start in zip(members, partition_starts(RDB_BYTES, members))]
        layout = require_disk_layout('%s (planned)' % name(index), drive_bytes, receipts, members)
        plans.append(dict(file=name(index), members=members, mib=mib, bytes=drive_bytes, layout=layout))
    return plans


def write_boot_partition(xdftool, part, boot, mib, volume='AMIWIND'):
    """Write the bootable DH0 partition image: every folder and file under BOOT, boot block installed.
    Bounded xdftool batches on every host (one command with every boot file exceeds ARG_MAX)."""
    boot = Path(boot)
    command = [xdftool, part, 'create', f'size={mib}Mi', '+', 'format', volume, 'ffs', '+', 'boot', 'install']
    for path in sorted((p for p in boot.rglob('*') if p.is_dir()), key=lambda p: len(p.parts)):
        command += ['+', 'makedir', path.relative_to(boot).as_posix()]
    for path in sorted(p for p in boot.rglob('*') if p.is_file()):
        command += ['+', 'write', path, path.relative_to(boot).as_posix()]
    from build_windows_xdftool import run_any as run_xdftool
    run_xdftool(command)
    return check_image(part, normalize=True)


def assemble_drives(rdbtool, plans, out, boot_part, boot_files, jobs=1, images=None, run=None):
    """Write every planned drive with rdbtool from partitions already written (BOOT_PART for DH0 with
    its hashed BOOT_FILES; out/<file> for a world partition, IMAGES by partition name when the plan
    holds planned partitions), read it back (verify_combined) and gate it as written (require_mountable,
    require_disk_layout). A written partition whose size differs from its plan stops the build.
    Returns (partition receipts, drive receipts, disk_layout)."""
    import subprocess
    run = run or (lambda command: subprocess.run(list(map(str, command)), check=True))
    out = Path(out)
    layout, drive_receipts, disk_layout = [], [], []
    for plan in plans:
        drive = out / plan['file']
        if plan['mib'] * MIB + RDB_BYTES >= DRIVE_SIZE_LIMIT:
            raise ValueError('Legacy hardfile must remain below 4 GiB')
        command = [rdbtool, drive, 'create', 'chs=%d,1,64' % (plan['mib'] * 32 + 1), '+', 'init']
        partitions = []
        for member in plan['members']:
            if member['partition'] == 'DH0':
                source = Path(boot_part)
                written = dict(partition='DH0', volume=member.get('volume'), files=boot_files)
                command += ['+', 'addimg', source, 'name=DH0', 'bootable=1', 'pri=0']
            else:
                written = (images or {}).get(member['partition'], member)
                source = out / written['file']
                command += ['+', 'addimg', source, 'name=' + member['partition'], 'bootable=0']
            if source.stat().st_size != member['bytes']:
                raise ValueError('Partition %s is %d bytes, planned %d'
                                 % (member['partition'], source.stat().st_size, member['bytes']))
            partitions.append(written)
        run(command)
        checked = verify_combined(drive, partitions, jobs=jobs)
        for receipt in checked:
            receipt['hdf_file'] = drive.name
        # Kickstart 3.1 does not mount a partition starting at or beyond 2 GiB of its drive.
        require_mountable(checked)
        # Every drive passes the disk-layout gate as written too: partition start and size below 2 GiB,
        # files well under 2 GiB, the drive below 4 GiB (BUILD-WORLD-PARTITION-MOUNT-33).
        disk_layout.append(require_disk_layout(drive.name, drive.stat().st_size, checked, partitions))
        layout.extend(checked)
        drive_receipts.append(dict(file=drive.name, bytes=drive.stat().st_size, sha256=digest(drive),
                                   bootable=plan is plans[0], partitions=[p['partition'] for p in checked],
                                   readback='passed'))
    return layout, drive_receipts, disk_layout


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def _pack_batch(task):
    """Worker: write, check and read back one world partition (independent)."""
    index, batch, out, xdftool = task
    batch = [Path(p) for p in batch]
    volume=f'AW_WORLD{index}';part=Path(out)/f'world{index}-partition.hdf'
    if part.exists():raise ValueError('World partitions are immutable')
    payload=sum(p.stat().st_size for p in batch)
    mib=partition_mib(payload)
    if mib>=2048:raise ValueError('World partition must remain below 2 GiB')
    command=[str(xdftool),str(part),'create',f'size={mib}Mi','+','format',volume,'ffs',
             '+','makedir','id1','+','makedir','id1/maps']
    files=[]
    for path in batch:
        name='id1/maps/'+path.name
        command+=['+','write',str(path),name]
        files.append(dict(path=name,bytes=path.stat().st_size,sha256=digest(path)))
    from build_windows_xdftool import run_any as run_xdftool
    run_xdftool(command)
    check_image(part,normalize=True)
    from amitools.fs.blkdev.BlkDevFactory import BlkDevFactory
    from amitools.fs.ADFSVolume import ADFSVolume
    from amitools.fs.FSString import FSString
    device=BlkDevFactory().open(str(part),read_only=True)
    try:
        mounted=ADFSVolume(device);mounted.open()
        for entry in files:
            data=mounted.read_file(FSString(entry['path']))
            if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:
                raise ValueError('World disk readback mismatch: '+entry['path'])
    finally:device.close()
    return dict(file=part.name,volume=volume,partition=f'DW{index}',bytes=part.stat().st_size,
                sha256=digest(part),files=files,readback='passed')


def plan_partitions(batches):
    """The world partitions the writer will make of BATCHES (lists of map paths), before any write."""
    return [planned_partition(f'DW{index}', [dict(path='id1/maps/' + Path(p).name, bytes=Path(p).stat().st_size)
                                             for p in batch], f'AW_WORLD{index}')
            for index, batch in enumerate(batches)]


def write_partitions(batches, out, xdftool, jobs=1):
    """Write one world partition per batch (xdftool, checked and read back), up to JOBS at once; the
    plan of every partition passes the disk-layout gate before the first one is written."""
    from build_parallel import ordered_map
    require_partition_plans(plan_partitions(batches))
    tasks=[(index,[str(p) for p in batch],str(out),str(xdftool)) for index,batch in enumerate(batches)]
    return list(ordered_map(_pack_batch,tasks,max(1,min(jobs,len(tasks) or 1))))


def pack(id1, out, version, xdftool, rdbtool=None, jobs=1):
    """Verify each temporary partition before removing redundant staging maps.

    Partitions are independent FFS volumes: up to `jobs` are written and read
    back at once (shared pool); the receipt keeps partition order. Staging maps
    are removed only after every partition verified.
    """
    directory=id1/'world/regions.awr'
    if not directory.exists():return []
    raw=directory.read_bytes()
    if raw[:4]!=b'AWR2' or len(raw)<64:raise ValueError('Invalid region directory')
    count=struct.unpack_from('<I',raw,4)[0]
    if not 1<=count<=8192 or len(raw)!=64+count*52:raise ValueError('Invalid region directory count')
    paths=[id1/'maps'/f'vf{i:04d}.bsp' for i in range(count)]
    # Preserve the original two-partition layout when it fits. Larger worlds
    # use additional bounded partitions discovered through volumes.awv.
    terrain_bytes=sum(p.stat().st_size for p in paths)
    boot_bytes=sum(p.stat().st_size for p in id1.parent.rglob('*') if p.is_file())-terrain_bytes
    _,batches=partition_batches(paths,boot_bytes)
    images=write_partitions(batches,out,xdftool,jobs)
    for batch in batches:
        for path in batch:path.unlink()
    (id1/'world/volumes.awv').write_bytes(b'AWV1'+bytes([len(images)]))
    (out/'world-partitions.json').write_text(json.dumps(
        dict(format='AmiWind terrain partitions 1',version=version,partitions=images),indent=2)+'\n')
    return images


READBACK_CHUNK = 1024  # files per readback task


def _verify_task(task):
    """Worker: one partition's header check (files=None) or the readback of a
    slice of its files. Returns the partition geometry, or the first file with
    the highest end offset in the slice (files in order, strictly greater)."""
    hdf, name, files = task
    from amitools.fs.blkdev.BlkDevFactory import BlkDevFactory
    from amitools.fs.ADFSVolume import ADFSVolume
    from amitools.fs.FSString import FSString
    if files is None:
        check_image(hdf,partition=name)
    device=BlkDevFactory().open(str(hdf),read_only=True,options={'part':name})
    try:
        volume=ADFSVolume(device);volume.open()
        if files is None:
            return dict(offset_bytes=device.blk_off*device.block_bytes,bytes=device.num_blocks*device.block_bytes,
                        free_bytes=volume.bitmap.get_num_free()*device.block_bytes)
        highest=0;highest_file=None
        for entry in files:
            data=volume.read_file(FSString(entry['path']))
            if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:
                raise ValueError('Final HDF readback mismatch: '+entry['path'])
            node=volume.get_file_path_name(FSString(entry['path']))
            end=(device.blk_off+max(node.get_block_nums())+1)*device.block_bytes
            if end>highest:highest=end;highest_file=entry['path']
        return highest,highest_file
    finally:device.close()


def verify_combined(hdf, partitions, jobs=1):
    """Read back every partition of one hardfile: each partition's header check
    and slices of its files run in up to `jobs` workers (read-only opens of the
    same image); receipts keep partition order and the serial highest file."""
    from build_parallel import ordered_map
    tasks=[]
    for partition in partitions:
        tasks.append((str(hdf),partition['partition'],None))
        files=partition['files']
        tasks.extend((str(hdf),partition['partition'],files[i:i+READBACK_CHUNK]) for i in range(0,len(files),READBACK_CHUNK))
    results=iter(ordered_map(_verify_task,tasks,max(1,min(jobs,len(tasks)))))
    receipts=[]
    for partition in partitions:
        geometry=next(results);highest=0;highest_file=None
        for _ in range(0,len(partition['files']),READBACK_CHUNK):
            end,name=next(results)
            if end>highest:highest=end;highest_file=name
        receipts.append(dict(partition=partition['partition'],volume=partition.get('volume'),
            offset_bytes=geometry['offset_bytes'],bytes=geometry['bytes'],
            payload_bytes=sum(e['bytes'] for e in partition['files']),files=len(partition['files']),
            free_bytes=geometry['free_bytes'],highest_used_end_offset=highest,highest_file=highest_file,readback='passed'))
    return receipts
