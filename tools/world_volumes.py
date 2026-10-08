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


def hardfile_groups(boot_bytes, worlds, limit=4 * 1024**3):
    """Group complete partitions into safe RDB drives, retaining a boot-first layout."""
    if boot_bytes + 32768 >= limit:
        raise ValueError('Boot partition exceeds the legacy hardfile limit')
    groups, current, used = [], [], boot_bytes + 32768
    for world in worlds:
        if world['bytes'] + 32768 >= limit:
            raise ValueError('World partition exceeds the legacy hardfile limit')
        if used + world['bytes'] >= limit:
            groups.append(current)
            current, used = [], 32768
        current.append(world)
        used += world['bytes']
    groups.append(current)
    return groups


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def _pack_batch(task):
    """Worker: write, check and read back one world partition (independent)."""
    index, batch, out, xdftool = task
    batch = [Path(p) for p in batch]
    volume=f'AW_WORLD{index}';part=Path(out)/f'world{index}-partition.hdf'
    if part.exists():raise ValueError('World partitions are immutable')
    payload=sum(p.stat().st_size for p in batch)
    mib=max(128,((payload*6//5+16*1024*1024+127*1024*1024)//(128*1024*1024))*128)
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


def pack(id1, out, version, xdftool, rdbtool=None, jobs=1):
    """Verify each temporary partition before removing redundant staging maps.

    Partitions are independent FFS volumes: up to `jobs` are written and read
    back at once (shared pool); the receipt keeps partition order. Staging maps
    are removed only after every partition verified.
    """
    from build_parallel import ordered_map
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
    tasks=[(index,[str(p) for p in batch],str(out),str(xdftool)) for index,batch in enumerate(batches)]
    images=list(ordered_map(_pack_batch,tasks,max(1,min(jobs,len(tasks) or 1))))
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
