#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Write a classic FFS partition image (BUILD-IMAGE-LAYOUT-WRITE-SLOWER-66): the boot partition, the CHIM world volume
and the open-world map volumes of the image step all go through write_volume.

THE METHOD BEFORE ('xdftool'): one xdftool command queue (create, format, every folder, every file), cut into batches
below the argument limit (tools/build_windows_xdftool.py, about 1,700 files a batch). xdftool finds the folder of each
file it writes by walking the path through amitools' ADFSDir.get_path, which compares the name with the entries of
every folder on the way one at a time, and each batch opens the image again, so a folder's entries come back in the
order of its hash table, not the order they were made. Every file therefore paid a scan of its folder and of the
folders above it: on the v0.0.66-dev11 boot partition (29,385 files; 7,757 entries directly in id1/progs, 7,086 in
id1/sound/pool, 3,865 in id1/maps, 1,971 in id1) those scans were about 9 tenths of the 114 s the file writes took,
and their cost grows with the square of a folder's entries, so the step grew faster than the payload.

THE DIRECT METHOD ('direct', the default): xdftool still creates and formats the image (and installs the boot block),
as before. Then, in this process, every folder and file is made in the same order by amitools' own ADFSDir calls, each
on the folder object it goes into (kept by its path: nothing is looked up by name), and the volume is closed once.
The same bitmap code allocates every block in the same order, so every block number, header, hash chain and the bitmap
are the ones the queue wrote (tests/test_ffs_write.py compares the two byte for byte with the clock held still; the
only bytes that differ between any two writes, of either method, are the dates of the moment they were written).
A file's data is not read while its blocks are allocated: its data block numbers are recorded, and once the volume is
closed the data of every file is written in one write per run of consecutive blocks (the data blocks of different
files never overlap, so the order does not matter). On one thread by default: measured on the v0.0.66-dev11 boot
partition (1,965,086,930 bytes of file data), the data took 4.9 s on 1 thread, 8.2 s on 4 and 13.0 s on 8, since the
writes all go into one image file, which the kernel writes one at a time (DATA_THREADS; write_volume THREADS).

Measured on the same partition (29,385 files, 2,019 MiB; 16 November 2026): the queue 115.5 s (file writes 114.4 s),
the direct writer 16.8 s with the chain relink and the check (format 0.4 s, folders and files 9.8 s, file data
4.9 s); the CHIM world volume (35,658 files) 12.5 s to write.

AMIWIND_PARTITION_WRITER=xdftool selects the method before for an A/B build; direct is the default.
"""
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

METHODS = ('direct', 'xdftool')
DEFAULT_METHOD = 'direct'
METHOD_ENV = 'AMIWIND_PARTITION_WRITER'
BLOCK_BYTES = 512
DATA_THREADS = 1             # threads writing file data: more were slower on one image file (measured, docstring)
DATA_CHUNK_BYTES = 64 << 20  # file data per thread task


def writer_method(method=None):
    """The partition writer to use: METHOD, else AMIWIND_PARTITION_WRITER, else direct."""
    method = method or os.environ.get(METHOD_ENV) or DEFAULT_METHOD
    if method not in METHODS:
        raise ValueError('%s must be one of %s, not %r' % (METHOD_ENV, ', '.join(METHODS), method))
    return method


def xdftool_command(xdftool, part, mib, volume, ops, boot=False):
    """The xdftool queue of a partition (the method before): create SIZE MiB, format VOLUME ffs, the boot block when
    BOOT, then every op of OPS in order: ('dir', volume path) makes a folder, ('file', source, volume path) writes a
    file. tools/build_windows_xdftool.run_any cuts it into batches below the argument limit."""
    command = [str(xdftool), str(part), 'create', 'size=%dMi' % mib, '+', 'format', volume, 'ffs']
    if boot:
        command += ['+', 'boot', 'install']
    for op in ops:
        if op[0] == 'dir':
            command += ['+', 'makedir', op[1]]
        elif op[0] == 'file':
            command += ['+', 'write', str(op[1]), op[2]]
        else:
            raise ValueError('Unknown partition op %r' % (op[0],))
    return command


class _Size:
    """A file's data while its blocks are allocated: amitools reads only its length then (ADFSFile.set_file_data,
    blocks_create_new); the bytes are written later by _write_data."""
    __slots__ = ('size',)

    def __init__(self, size):
        self.size = size

    def __len__(self):
        return self.size


_PLANNED = None


def _planned_file_class():
    """ADFSFile whose data blocks are recorded instead of written (one class per process, amitools imported late)."""
    global _PLANNED
    if _PLANNED is None:
        from amitools.fs.ADFSFile import ADFSFile

        class PlannedFile(ADFSFile):
            source = None
            plan = None

            def write(self):
                # called by blocks_create_new once the header and list blocks are written: the data comes later
                self.plan.append((self.source, self.data_size, list(self.data_blk_nums)))

        _PLANNED = PlannedFile
    return _PLANNED


def _key(path):
    """A volume path as the file system compares names (the classic FFS upper case of its bytes)."""
    from amitools.fs.FSString import FSString
    return FSString(path).get_ami_str().upper()


def _create_entries(part, ops):
    """Make every folder and file of OPS on the formatted partition PART, in order, each on its folder object.
    Returns the data plan [(source, bytes, data block numbers)] of every file with data, in write order."""
    from amitools.fs.ADFSVolume import ADFSVolume
    from amitools.fs.FSString import FSString
    from amitools.fs.blkdev.BlkDevFactory import BlkDevFactory
    planned = _planned_file_class()
    plan = []
    device = BlkDevFactory().open(str(part), read_only=False)
    try:
        volume = ADFSVolume(device)
        volume.open()
        folders = {_key(''): volume.root_dir}
        for op in ops:
            path = op[1] if op[0] == 'dir' else op[2]
            parent, _, name = str(path).rpartition('/')
            folder = folders.get(_key(parent))
            if folder is None:
                raise ValueError('Partition %s: %s goes into the folder %s, which is not made before it'
                                 % (part, path, parent or '/'))
            if _key(path) in folders:
                raise ValueError('Partition %s: %s is a folder already' % (part, path))
            if op[0] == 'dir':
                # what xdftool makedir does: ADFSVolume.create_dir -> the parent's ADFSDir.create_dir
                folders[_key(path)] = folder.create_dir(FSString(name))
                continue
            # what xdftool write does: ADFSVolume.write_file -> the parent's ADFSDir.create_file, then flush
            node = planned(volume, folder)
            node.source, node.plan = str(op[1]), plan
            node.set_file_data(_Size(os.stat(op[1]).st_size))
            folder._create_node(node, FSString(name), None, True)
            node.flush()
        volume.close()
    finally:
        device.close()
    return [row for row in plan if row[1]]


def _runs(blocks):
    """[(first block, count)] of the runs of consecutive block numbers in BLOCKS, in their order."""
    runs = []
    for block in blocks:
        if runs and runs[-1][0] + runs[-1][1] == block:
            runs[-1][1] += 1
        else:
            runs.append([block, 1])
    return runs


def _write_files(task):
    """Thread: write the data of TASK's files [(source, bytes, blocks)] into the partition; returns the bytes."""
    part, items = task
    total = 0
    with open(part, 'r+b') as stream:
        for source, size, blocks in items:
            with open(source, 'rb') as handle:
                data = handle.read()
            if len(data) != size:
                raise ValueError('%s is %d bytes; it was %d bytes when its blocks were allocated' % (source, len(data),
                                                                                                    size))
            if len(blocks) != -(-size // BLOCK_BYTES):
                raise ValueError('%s has %d data blocks for %d bytes' % (source, len(blocks), size))
            view, offset = memoryview(data), 0
            for first, count in _runs(blocks):
                piece = view[offset:offset + count * BLOCK_BYTES]
                stream.seek(first * BLOCK_BYTES)
                stream.write(piece)
                if len(piece) < count * BLOCK_BYTES:
                    stream.write(bytes(count * BLOCK_BYTES - len(piece)))   # the last block, padded as amitools does
                offset += count * BLOCK_BYTES
            total += size
    return total


def _write_data(part, plan, threads):
    """Write the data of every planned file into PART on THREADS threads, in chunks of about DATA_CHUNK_BYTES."""
    tasks, current, used = [], [], 0
    for row in plan:
        current.append(row)
        used += row[1]
        if used >= DATA_CHUNK_BYTES:
            tasks.append((str(part), current))
            current, used = [], 0
    if current:
        tasks.append((str(part), current))
    threads = max(1, min(int(threads or 1), len(tasks) or 1))
    if threads == 1:
        return sum(_write_files(task) for task in tasks)
    with ThreadPoolExecutor(max_workers=threads) as pool:
        return sum(pool.map(_write_files, tasks))


def write_volume(xdftool, part, mib, volume, ops, boot=False, method=None, threads=None, run=None):
    """Write the FFS partition image PART of MIB MiB, volume name VOLUME: the boot block when BOOT, then OPS in order
    (('dir', volume path) or ('file', source, volume path); a folder before anything in it). METHOD: writer_method.
    RUN runs an xdftool command (default build_windows_xdftool.run_any; the tests run xdftool in their process).
    Returns {'method', 'folders', 'files', 'bytes', 'seconds': {...}, 'threads'}."""
    method = writer_method(method)
    if run is None:
        from build_windows_xdftool import run_any as run
    ops = list(ops)
    folders = sum(1 for op in ops if op[0] == 'dir')
    started = time.monotonic()
    if method == 'xdftool':
        run(xdftool_command(xdftool, part, mib, volume, ops, boot))
        return dict(method=method, folders=folders, files=len(ops) - folders, bytes=None, threads=1,
                    seconds=dict(total=round(time.monotonic() - started, 3)))
    run(xdftool_command(xdftool, part, mib, volume, [], boot))
    formatted = time.monotonic()
    plan = _create_entries(part, ops)
    entries = time.monotonic()
    threads = DATA_THREADS if threads is None else threads
    written = _write_data(part, plan, threads)
    done = time.monotonic()
    return dict(method=method, folders=folders, files=len(ops) - folders, bytes=written,
                threads=max(1, min(int(threads or 1), len(plan) or 1)),
                seconds=dict(format=round(formatted - started, 3), entries=round(entries - formatted, 3),
                             data=round(done - entries, 3), total=round(done - started, 3)))


def describe(receipt, name):
    """One log line for a write_volume receipt: what was written how, and the cores it used."""
    s = receipt['seconds']
    if receipt['method'] == 'xdftool':
        return ('Image: %s written by the xdftool queue (%s=xdftool, the method before): %d folders, %d files in %.1fs, '
                '1 core' % (name, METHOD_ENV, receipt['folders'], receipt['files'], s['total']))
    return ('Image: %s written directly (BUILD-IMAGE-LAYOUT-WRITE-SLOWER-66): %d folders, %d files, %d bytes in %.1fs: '
            'format %.1fs (xdftool), folders and files %.1fs on 1 core (blocks allocated in write order), file data '
            '%.1fs on %d thread%s' % (name, receipt['folders'], receipt['files'], receipt['bytes'], s['total'],
                                      s['format'], s['entries'], s['data'], receipt['threads'],
                                      '' if receipt['threads'] == 1 else 's'))


def tree_ops(root, files=None):
    """The ops of a folder tree as the boot partition writes it: every folder under ROOT, shallowest first (within a
    depth in the order the file system lists them, as before), then every file in sorted order; FILES (sorted paths
    under ROOT) when already listed."""
    root = Path(root)
    folders = sorted((p for p in root.rglob('*') if p.is_dir()), key=lambda p: len(p.parts))
    if files is None:
        files = sorted(p for p in root.rglob('*') if p.is_file())
    return ([('dir', p.relative_to(root).as_posix()) for p in folders]
            + [('file', p, p.relative_to(root).as_posix()) for p in files])
