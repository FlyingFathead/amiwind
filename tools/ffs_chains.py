#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The directory hash chains of a written FFS partition: how many header blocks each name lookup reads, the chain order
that puts the entries the game passes most at the head, and the buffers a partition needs so that a repeated lookup is
served from memory (IMAGE-LOADS-SLOWER-66, BUILD-HDF-BUFFERS-32).

The Fast File System finds a name in a directory by hashing it to one of the directory block's 72 chains and reading
the header block of every entry of that chain, head first, until the name matches; a path costs that at every level,
after the root block. The image writer (xdftool) adds each new entry at the HEAD of its chain, so a chain lists its
entries newest first, and the boot partition writer makes every folder before any file: the folders the game reads most
ended at the tail of their chains, behind the loose files of their parent (id1/sound was the 28th entry of 28 in its
chain in v0.0.66-dev2, the 20th of 20 in v0.0.66-dev1).

A partition keeps a few block buffers (30, the partition table's default, until v0.0.66-dev4). The engine opens a file
twice in a row (COM_FindFile for a handle: Sys_FileTime opens and closes it, then Sys_FileOpenRead opens it), so each
open looks the same name up twice. When the first lookup read no more blocks than there are buffers, the second one is
served from them, and the next file in the same folder finds the folder's own chain blocks there too; when it read more,
each walk throws out the blocks the next walk starts with and every block is read from the disk again.

order_partition relinks every chain of a written partition, busiest first: by the files beneath each entry (a folder
counts every file under it, a file counts 1), most first, the written order kept among equals. Only links change (the
next-in-chain word of the entries that move, the directory's table entry, their checksums): no block moves, every file
keeps its blocks and its data. 'as-written' keeps the writer's order (the method before; AMIWIND_CHAIN_ORDER=as-written
in the image step's environment selects it for an A/B build).

partition_buffers sizes a partition's buffers to its longest name lookup (every file of it), so the repeated lookup of
any file fits; AMIWIND_PARTITION_BUFFERS=N gives every partition N instead (30 = the buffers before, for an A/B build).

Command line (read only): ffs_chains.py IMAGE [--partition NAME] [--order ORDER] [--json] prints the lookup costs of a
partition image, or of one partition of an RDB drive.
"""
import argparse
import json
import os
import struct
import sys

BLOCK_BYTES = 512
HASH_SLOTS = BLOCK_BYTES // 4 - 56            # 72 chains in a directory block of 512 bytes
_HEADER = 2                                   # block type of root, folder and file header blocks
_ROOT, _FOLDER = 1, 2                         # their secondary types (a file is -3)
_CHECKSUM, _TABLE, _CHAIN, _PARENT, _SECONDARY = 5, 6, 124, 125, 127   # long word indexes in such a block
ORDERS = ('busiest-first', 'as-written')
DEFAULT_ORDER = 'busiest-first'
ORDER_ENV = 'AMIWIND_CHAIN_ORDER'
# Buffers (BUILD-HDF-BUFFERS-32): never fewer than the 30 every partition had (rdbtool's default); the longest lookup
# plus MARGIN blocks for what the file system reads between the two lookups of one open (the file's own header is part
# of the walk; the margin covers the bitmap and extension blocks), in steps of 10; at most CAP (about 0.5 KiB each).
BUFFERS_FLOOR = 30
BUFFERS_MARGIN = 10
BUFFERS_STEP = 10
BUFFERS_CAP = 500
BUFFERS_ENV = 'AMIWIND_PARTITION_BUFFERS'


def chain_order(order=None):
    """The chain order to write: ORDER, else AMIWIND_CHAIN_ORDER, else busiest-first."""
    order = order or os.environ.get(ORDER_ENV) or DEFAULT_ORDER
    if order not in ORDERS:
        raise ValueError('chain order must be one of %s, not %r' % (', '.join(ORDERS), order))
    return order


def _block(stream, offset, number, blocks):
    if not 0 <= number < blocks:
        raise ValueError('FFS block %d is outside the partition (%d blocks)' % (number, blocks))
    stream.seek(offset + number * BLOCK_BYTES)
    raw = stream.read(BLOCK_BYTES)
    if len(raw) != BLOCK_BYTES:
        raise ValueError('FFS block %d is past the end of the image' % number)
    return list(struct.unpack('>128I', raw)), raw


def read_tree(path, offset=0, size=None):
    """The directory tree of the FFS partition at OFFSET bytes of PATH (SIZE bytes, by default the rest of the file),
    read from its blocks: {'blocks', 'root', 'dirs': {block: {'path', 'chains': {slot: [entry blocks, head first]}}},
    'entries': {block: {'name', 'path', 'dir', 'parent', 'slot', 'next'}}}. The root block is the middle block (FFS's
    rule, amitools BootBlock.calc_root_blk). Raises ValueError for a block that is not what its link says."""
    with open(path, 'rb') as stream:
        if size is None:
            size = stream.seek(0, 2) - offset
        blocks = size // BLOCK_BYTES
        root = blocks // 2
        words, _ = _block(stream, offset, root, blocks)
        if words[0] != _HEADER or words[_SECONDARY] != _ROOT:
            raise ValueError('No FFS root block at block %d of %s' % (root, path))
        dirs, entries = {}, {}
        pending = [(root, '', words)]
        while pending:
            number, prefix, words = pending.pop()
            chains = {}
            for slot in range(HASH_SLOTS):
                link, chain = words[_TABLE + slot], []
                while link:
                    if link in entries:
                        raise ValueError('FFS block %d is linked twice (chain %d of /%s)' % (link, slot, prefix))
                    entry, raw = _block(stream, offset, link, blocks)
                    if entry[0] != _HEADER or entry[1] != link or entry[_PARENT] != number:
                        raise ValueError('FFS block %d in chain %d of /%s is not an entry of that folder'
                                         % (link, slot, prefix))
                    name = raw[433:433 + min(raw[432], 30)].decode('latin-1')
                    folder = entry[_SECONDARY] == _FOLDER
                    entries[link] = dict(name=name, path=prefix + name, dir=folder, parent=number, slot=slot,
                                         next=entry[_CHAIN])
                    chain.append(link)
                    if folder:
                        pending.append((link, prefix + name + '/', entry))
                    link = entry[_CHAIN]
                if chain:
                    chains[slot] = chain
            dirs[number] = dict(path=prefix.rstrip('/'), chains=chains)
    return dict(blocks=blocks, root=root, dirs=dirs, entries=entries)


def files_beneath(tree):
    """{entry block: files at or under it}: a file counts 1, a folder every file under it (0 when empty)."""
    entries = tree['entries']
    count = {block: (0 if entry['dir'] else 1) for block, entry in entries.items()}
    for block, entry in entries.items():
        if not entry['dir']:
            parent = entry['parent']
            while parent in entries:
                count[parent] += 1
                parent = entries[parent]['parent']
    return count


def ordered_chains(tree, order=None):
    """{directory block: {slot: [entry blocks, head first]}} in ORDER (chain_order): 'as-written' as on the disk,
    'busiest-first' by files_beneath, most first, the written order kept among equals."""
    order = chain_order(order)
    if order == 'as-written':
        return {d: {slot: list(chain) for slot, chain in info['chains'].items()} for d, info in tree['dirs'].items()}
    weight = files_beneath(tree)
    return {d: {slot: sorted(chain, key=lambda block: -weight[block]) for slot, chain in info['chains'].items()}
            for d, info in tree['dirs'].items()}


def lookup_blocks(tree, chains):
    """{file path: header blocks its name lookup reads}: the root block, and at every level of the path each entry of
    the name's chain up to and including the name, with the chains CHAINS (ordered_chains)."""
    position = {}
    for slots in chains.values():
        for chain in slots.values():
            for index, block in enumerate(chain, 1):
                position[block] = index
    entries, reach, costs = tree['entries'], {tree['root']: 1}, {}

    def blocks_to(block):
        if block not in reach:
            reach[block] = blocks_to(entries[block]['parent']) + position[block]
        return reach[block]

    for block in sorted(entries, key=lambda b: entries[b]['path'].count('/')):   # parents first: no deep recursion
        cost = blocks_to(block)
        if not entries[block]['dir']:
            costs[entries[block]['path']] = cost
    return costs


def summary(costs, buffers=BUFFERS_FLOOR):
    """Lookup costs in short: files, median, 95th percentile, longest (and its file), how many fit BUFFERS."""
    values = sorted(costs.values())
    if not values:
        return dict(files=0, median=0, p95=0, longest=0, longest_file=None, buffers=buffers, fit=0)
    longest_file = max(sorted(costs), key=lambda path: costs[path])
    return dict(files=len(values), median=values[len(values) // 2], p95=values[min(len(values) - 1,
                                                                                     len(values) * 95 // 100)],
                longest=values[-1], longest_file=longest_file, buffers=buffers,
                fit=sum(1 for v in values if v <= buffers))


def partition_buffers(longest):
    """The buffers of a partition whose longest name lookup reads LONGEST header blocks: LONGEST + BUFFERS_MARGIN in
    steps of BUFFERS_STEP, at least BUFFERS_FLOOR, at most BUFFERS_CAP."""
    want = -(-(int(longest) + BUFFERS_MARGIN) // BUFFERS_STEP) * BUFFERS_STEP
    return max(BUFFERS_FLOOR, min(BUFFERS_CAP, want))


def buffer_plan(path, offset=0, size=None):
    """{'buffers', 'sized', 'longest', 'median', 'p95', 'longest_file', 'files', 'fit'} of the partition at OFFSET of
    PATH as written: its buffers sized to its longest lookup (partition_buffers; sized 'the longest lookup'), or the
    whole number AMIWIND_PARTITION_BUFFERS gives (sized 'AMIWIND_PARTITION_BUFFERS'), and how many lookups fit them."""
    tree = read_tree(path, offset, size)
    costs = lookup_blocks(tree, ordered_chains(tree, 'as-written'))
    forced = os.environ.get(BUFFERS_ENV) or 'auto'
    if forced == 'auto':
        buffers, sized = partition_buffers(max(costs.values(), default=0)), 'the longest lookup'
    elif forced.isdigit() and 1 <= int(forced) <= BUFFERS_CAP:
        buffers, sized = int(forced), BUFFERS_ENV
    else:
        raise ValueError('%s must be auto or a whole number from 1 to %d, not %r' % (BUFFERS_ENV, BUFFERS_CAP, forced))
    return dict(summary(costs, buffers), sized=sized)


def order_partition(path, order=None, offset=0):
    """Relink every hash chain of the FFS partition image PATH (at OFFSET bytes) in ORDER (chain_order) and read it back.
    Only links change: the next-in-chain word of each entry whose successor changes, the directory table entry of each
    chain whose head changes, and those blocks' checksums. Returns {'order', 'directories', 'entries', 'chains',
    'chains_reordered', 'blocks_rewritten', 'before', 'after'} (before and after: summary of every file's lookup)."""
    order = chain_order(order)
    tree = read_tree(path, offset)
    before = lookup_blocks(tree, ordered_chains(tree, 'as-written'))
    chains = ordered_chains(tree, order)
    changes, reordered, total = {}, 0, 0
    for directory, slots in chains.items():
        for slot, chain in slots.items():
            total += 1
            if chain == tree['dirs'][directory]['chains'][slot]:
                continue
            reordered += 1
            changes.setdefault(directory, {})[_TABLE + slot] = chain[0]
            for block, successor in zip(chain, chain[1:] + [0]):
                if tree['entries'][block]['next'] != successor:
                    changes.setdefault(block, {})[_CHAIN] = successor
    if changes:
        with open(path, 'r+b') as stream:
            for block in sorted(changes):
                words, _ = _block(stream, offset, block, tree['blocks'])
                for word, value in changes[block].items():
                    words[word] = value
                words[_CHECKSUM] = 0
                words[_CHECKSUM] = -sum(words) & 0xFFFFFFFF
                stream.seek(offset + block * BLOCK_BYTES)
                stream.write(struct.pack('>128I', *words))
    # read back: the same entries under the same folders, every chain as ordered
    check = read_tree(path, offset)
    found = {block: (entry['path'], entry['dir'], entry['parent']) for block, entry in check['entries'].items()}
    if found != {block: (entry['path'], entry['dir'], entry['parent']) for block, entry in tree['entries'].items()}:
        raise ValueError('FFS chain order: %s holds other entries after the relink' % path)
    if {d: info['chains'] for d, info in check['dirs'].items()} != chains:
        raise ValueError('FFS chain order: %s reads back another chain order than written' % path)
    after = lookup_blocks(check, ordered_chains(check, 'as-written'))
    return dict(order=order, directories=len(tree['dirs']), entries=len(tree['entries']), chains=total,
                chains_reordered=reordered, blocks_rewritten=len(changes), before=summary(before),
                after=summary(after))


def describe(receipt, name):
    """One log line for an order_partition receipt."""
    b, a = receipt['before'], receipt['after']
    return ('Image: %s hash chains %s: %d of %d chains relinked, %d header blocks rewritten, no block moved; name '
            'lookups (%d files): median %d -> %d header blocks, longest %d -> %d (%s), within %d buffers %d -> %d'
            % (name, receipt['order'], receipt['chains_reordered'], receipt['chains'], receipt['blocks_rewritten'],
               a['files'], b['median'], a['median'], b['longest'], a['longest'], a['longest_file'], BUFFERS_FLOOR,
               b['fit'], a['fit']))


def partition_span(image, name):
    """(offset bytes, size bytes) of partition NAME of the RDB drive IMAGE (amitools)."""
    from amitools.fs.blkdev.BlkDevFactory import BlkDevFactory
    device = BlkDevFactory().open(str(image), read_only=True, options={'part': name})
    try:
        return device.blk_off * device.block_bytes, device.num_blocks * device.block_bytes
    finally:
        device.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('image', help='a partition image, or an RDB drive with --partition')
    ap.add_argument('--partition', help='partition name in an RDB drive (DH0, DW1, ...)')
    ap.add_argument('--order', choices=ORDERS, default='as-written',
                    help='the chain order to cost: as on the disk (default) or busiest-first (what a relink gives)')
    ap.add_argument('--buffers', type=int, default=BUFFERS_FLOOR, help='buffers to count fitting lookups against')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    offset, size = partition_span(a.image, a.partition) if a.partition else (0, None)
    tree = read_tree(a.image, offset, size)
    costs = lookup_blocks(tree, ordered_chains(tree, a.order))
    result = summary(costs, a.buffers)
    result.update(order=a.order, partition=a.partition, directories=len(tree['dirs']),
                  needed_buffers=partition_buffers(result['longest']))
    sys.stdout.write((json.dumps(result, indent=1) if a.json else
                      '%(files)d files, %(order)s: median %(median)d header blocks per lookup, 95 %% %(p95)d, longest '
                      '%(longest)d (%(longest_file)s); %(fit)d fit %(buffers)d buffers; needed %(needed_buffers)d'
                      % result) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
