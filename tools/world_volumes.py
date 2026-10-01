#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Prepare terrain partitions for one legacy-compatible RDB hardfile."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
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


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def pack(id1, out, version, xdftool, rdbtool=None):
    """Verify each temporary partition before removing redundant staging maps."""
    directory=id1/'world/regions.awr'
    if not directory.exists():return []
    raw=directory.read_bytes()
    if raw[:4]!=b'AWR2' or len(raw)<64:raise ValueError('Invalid region directory')
    count=struct.unpack_from('<I',raw,4)[0]
    if not 1<=count<=8192 or len(raw)!=64+count*52:raise ValueError('Invalid region directory count')
    paths=[id1/'maps'/f'vf{i:04d}.bsp' for i in range(count)]
    # Balance all content across exactly two partitions. Some terrain stays on
    # the boot volume; the remainder is found through one additional volume.
    terrain_bytes=sum(p.stat().st_size for p in paths)
    boot_bytes=sum(p.stat().st_size for p in id1.parent.rglob('*') if p.is_file())-terrain_bytes
    _,additional=balanced(paths,boot_bytes)
    batches=[additional]
    images=[]
    for index, batch in enumerate(batches):
        volume=f'AW_WORLD{index}';part=out/f'world{index}-partition.hdf'
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
        subprocess.run(command,check=True)
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
        images.append(dict(file=part.name,volume=volume,partition=f'DW{index}',bytes=part.stat().st_size,
                           sha256=digest(part),files=files,readback='passed'))
        for path in batch:path.unlink()
    (id1/'world/volumes.awv').write_bytes(b'AWV1'+bytes([len(images)]))
    (out/'world-partitions.json').write_text(json.dumps(
        dict(format='AmiWind terrain partitions 1',version=version,partitions=images),indent=2)+'\n')
    return images


def verify_combined(hdf, partitions):
    from amitools.fs.blkdev.BlkDevFactory import BlkDevFactory
    from amitools.fs.ADFSVolume import ADFSVolume
    from amitools.fs.FSString import FSString
    receipts=[]
    for partition in partitions:
        check_image(hdf,partition=partition['partition'])
        device=BlkDevFactory().open(str(hdf),read_only=True,options={'part':partition['partition']})
        try:
            volume=ADFSVolume(device);volume.open()
            highest=0;highest_file=None
            for entry in partition['files']:
                data=volume.read_file(FSString(entry['path']))
                if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:
                    raise ValueError('Final HDF readback mismatch: '+entry['path'])
                node=volume.get_file_path_name(FSString(entry['path']))
                end=(device.blk_off+max(node.get_block_nums())+1)*device.block_bytes
                if end>highest:highest=end;highest_file=entry['path']
            receipts.append(dict(partition=partition['partition'],volume=partition.get('volume'),
                offset_bytes=device.blk_off*device.block_bytes,bytes=device.num_blocks*device.block_bytes,
                payload_bytes=sum(e['bytes'] for e in partition['files']),files=len(partition['files']),
                free_bytes=volume.bitmap.get_num_free()*device.block_bytes,
                highest_used_end_offset=highest,highest_file=highest_file,readback='passed'))
        finally:device.close()
    return receipts
