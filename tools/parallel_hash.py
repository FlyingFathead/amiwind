#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SHA-256 of many files at once, on every core the stage holds (BUILD-IMAGE-HASH-UNDERUSED-36).

The builder hashes whole payloads: the image step alone hashes ~35,000 staged files in 13 calls
(content fingerprint, optimizer checks, hidden-surface and flora checks, boot partition receipt).
Before this module every file was one task of a fresh spawned process pool: 24 Python processes
started per call, one pickled future per file, and the median file is ~22 KiB, so the work was
mostly process start-up and task traffic (3 of 24 cores in the dev5 full build).

Hashing does not need processes: reading a file and hashlib's SHA-256 update both release the
interpreter lock (updates of 2 KiB and more), so threads of the stage process hash in parallel.
Small files (most of a payload by count) are interpreter work, so they run in one lane; bigger
files are grouped into batches by size, largest first (one huge file never ends last on one
thread), each batch hashed by one thread with a reused read buffer; results come back in input
order. Lists too small to pay for threads are hashed in the caller. Measured on the dev5 payload
(10,258 files, 1.6 GB, busy host): 4.8 s and 10.6 CPU-s before, 0.7-0.9 s and 1.5 CPU-s now;
a process pool of size batches took 1.7-2.2 s (start-up of the spawned workers).

SHA-256 is the identity: every byte of every file is read and
hashed every time; nothing is reused by name, size or modification time. The digests are the
same as hashlib.sha256(file bytes).hexdigest() (tests/test_parallel_hash.py).

Profiling: each call is one section "parallel hash: sha256" with items = files and the bytes
hashed, so the perf guard judges it like a parallel map.
"""
import hashlib
import os
import threading

import build_profile

# Files up to this size are read with plain descriptor reads.
SMALL_BYTES = 256 << 10
# Read size per call: big reads keep the per-file Python work small next to the hashing.
BUFFER_BYTES = 4 << 20
# A batch closes at this many bytes or files (whichever first); a file at least this big is a batch
# of its own. Batches are also capped at total / (BATCHES_PER_WORKER x workers) so every worker
# gets several and the last ones are small.
BATCH_BYTES = 64 << 20
BATCH_FILES = 256
BATCHES_PER_WORKER = 4
# Threads that hash small files at the same time (see batches(); one measured fastest: dev5 payload,
# 10,258 files, 0.72 s with one lane, 0.75 with two, 1.06 with four, 0.93 with one lane per batch).
SMALL_LANES = 1
# Lists below both limits are hashed in the caller: starting threads would cost more than they save.
SERIAL_BYTES = 8 << 20
SERIAL_FILES = 32

_local = threading.local()


def _buffer():
    buffer = getattr(_local, 'buffer', None)
    if buffer is None:
        buffer = _local.buffer = bytearray(BUFFER_BYTES)
    return buffer


def sha256_file(path, size=None):
    """SHA-256 hex digest of one file. SIZE (a hint from stat, never trusted for identity): a file
    up to SMALL_BYTES is read with plain descriptor reads (less interpreter work per file), any
    other file is streamed through this thread's reused buffer. Either way every byte is read
    until end of file, whatever SIZE said."""
    digest = hashlib.sha256()
    if size is not None and size <= SMALL_BYTES:
        descriptor = os.open(path, os.O_RDONLY)
        try:
            request = size + 1            # one read for the whole file; small allocations only
            while True:
                block = os.read(descriptor, request)
                if not block:
                    break
                digest.update(block)
                request = SMALL_BYTES
        finally:
            os.close(descriptor)
        return digest.hexdigest()
    buffer = _buffer()
    view = memoryview(buffer)
    with open(path, 'rb', buffering=0) as stream:
        while True:
            count = stream.readinto(buffer)
            if not count:
                break
            digest.update(view[:count])
    return digest.hexdigest()


def batches(sizes, workers, batch_bytes=BATCH_BYTES, batch_files=BATCH_FILES, small_lanes=None):
    """Index lists in submission order.

    Small files (up to SMALL_BYTES) cost interpreter work, not hashing: threads doing them at the
    same time only queue for the interpreter lock (measured on the dev5 payload: 8,899 small files,
    0.34 s on one thread, 0.99 s on 24). They go into SMALL_LANES lanes (dealt round-robin in input
    order), submitted first. Bigger files hash with the lock released: sorted by size (largest first,
    ties in input order) and packed into batches of at most LIMIT bytes and BATCH_FILES files, a file
    at or over LIMIT alone; LIMIT = min(batch_bytes, big bytes / (BATCHES_PER_WORKER x workers))."""
    lanes = SMALL_LANES if small_lanes is None else small_lanes
    small = [index for index, size in enumerate(sizes) if size <= SMALL_BYTES]
    big = [index for index, size in enumerate(sizes) if size > SMALL_BYTES]
    lanes = max(1, min(lanes, workers, len(small)))
    result = [small[lane::lanes] for lane in range(lanes)] if small else []
    total = sum(sizes[index] for index in big)
    limit = max(1, min(batch_bytes, total // max(1, BATCHES_PER_WORKER * workers)))
    current, current_bytes = [], 0
    for index in sorted(big, key=lambda index: (-sizes[index], index)):
        size = sizes[index]
        if current and (current_bytes + size > limit or len(current) >= batch_files):
            result.append(current)
            current, current_bytes = [], 0
        current.append(index)
        current_bytes += size
    if current:
        result.append(current)
    return result


def _workers(jobs):
    from build_jobs import resolve_jobs
    return max(1, resolve_jobs(jobs))


def plan(sizes, jobs):
    """(threads, batches) for files of SIZES (None = not hashed): no more threads than batches, else
    exactly `jobs` (an explicit --jobs N is never capped by the CPU count); 1 thread = in the caller."""
    known = [size for size in sizes if size is not None]
    total = sum(known)
    workers = _workers(jobs)
    if workers <= 1 or not known or (total < SERIAL_BYTES and len(sizes) < SERIAL_FILES):
        return 1, None
    groups = batches(known, workers)
    return max(1, min(workers, len(groups))), groups


def _hash_all(paths, sizes, jobs, missing_ok):
    """Digests in input order; None for a missing path when missing_ok."""
    count = len(paths)
    results = [None] * count
    total = sum(size for size in sizes if size)
    timer = build_profile.section('parallel hash: sha256')
    with timer:
        workers, groups = plan(sizes, jobs)
        if groups is None:
            for index, path in enumerate(paths):
                if sizes[index] is not None or not missing_ok:
                    results[index] = sha256_file(path, sizes[index])
        else:
            from concurrent.futures import ThreadPoolExecutor
            known = [index for index in range(count) if sizes[index] is not None]

            def run(group):
                return [(known[local], sha256_file(paths[known[local]], sizes[known[local]])) for local in group]
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix='sha256') as pool:
                # submitted in batches() order: the small-file lane, then the largest batches first
                for done in [pool.submit(run, group) for group in groups]:
                    for index, value in done.result():
                        results[index] = value
        timer.note(items=count, bytes=total, workers=workers)
    return results


def _size(path, missing_ok):
    """The stat size (a scheduling hint only), or None for "not a regular file" when missing_ok
    (os.path.isfile, as the earlier hash_existing: also for paths it cannot stat)."""
    if missing_ok and not os.path.isfile(path):
        return None
    return os.stat(path).st_size


def hash_files(paths, jobs=None):
    """SHA-256 of every path, in input order; a missing file raises (FileNotFoundError)."""
    paths = [os.fspath(path) for path in paths]
    return _hash_all(paths, [_size(path, False) for path in paths], jobs, False)


def hash_existing(paths, jobs=None):
    """Like hash_files, with None for a path that is not a regular file."""
    paths = [os.fspath(path) for path in paths]
    return _hash_all(paths, [_size(path, True) for path in paths], jobs, True)
