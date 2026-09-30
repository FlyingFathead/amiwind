"""Shared CPU and memory budget for native compilation and conversion."""
import argparse
import math
import os
from pathlib import Path


def available_memory():
    """Best available host/container headroom; unknown is not treated as zero."""
    candidates=[]
    try:
        rows=dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())
        candidates.append(int(rows['MemAvailable'].split()[0])*1024)
    except (OSError,ValueError,KeyError,IndexError):pass
    for limit_path,used_path in (
        ('/sys/fs/cgroup/memory.max','/sys/fs/cgroup/memory.current'),
        ('/sys/fs/cgroup/memory/memory.limit_in_bytes','/sys/fs/cgroup/memory/memory.usage_in_bytes')):
        try:
            limit=int(Path(limit_path).read_text());used=int(Path(used_path).read_text())
            if 0<limit<1<<60:candidates.append(max(0,limit-used))
        except (OSError,ValueError):pass
    return min(candidates) if candidates else None


def auto_jobs():
    counts = [os.cpu_count() or 1]
    if hasattr(os, 'process_cpu_count'):
        try:
            counts.append(os.process_cpu_count() or 1)
        except OSError:
            pass  # Continue with affinity/quota/fallback when this query is unavailable.
    if hasattr(os, 'sched_getaffinity'):
        try:
            counts.append(len(os.sched_getaffinity(0)))
        except OSError:
            pass
    # Containers may expose all host CPUs but grant only a smaller CPU quota.
    try:
        quota, period = Path('/sys/fs/cgroup/cpu.max').read_text().split()
        if quota != 'max' and int(quota) > 0 and int(period) > 0:
            counts.append(math.ceil(int(quota) / int(period)))
    except (OSError, ValueError):
        pass
    # Reserve a quarter of current headroom (at least 256 MiB), then budget
    # 512 MiB per worker. This is a conservative planning estimate, not an
    # assertion that arbitrary future NIFs have a fixed peak memory cost.
    memory=available_memory()
    if memory is not None:
        reserve=max(256*1024**2,memory//4)
        counts.append(max(1,(memory-reserve)//(512*1024**2)))
    return max(1, min(counts))


def job_value(value):
    if value == 'auto':
        return None
    try:
        count = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError('jobs must be a positive integer or auto') from None
    if count < 1:
        raise argparse.ArgumentTypeError('jobs must be at least 1')
    return count


def resolve_jobs(value=None):
    if value is not None:
        return value
    # A scheduled stage must not expand its allocation back to all host CPUs.
    inherited = os.environ.get('AMIWIND_BUILD_JOBS')
    if inherited is not None:
        try:
            count = int(inherited)
        except ValueError:
            raise ValueError('AMIWIND_BUILD_JOBS must be a positive integer') from None
        if count < 1:
            raise ValueError('AMIWIND_BUILD_JOBS must be a positive integer')
        return count
    return auto_jobs()


def add_jobs(parser):
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-j', '--jobs', '--j', type=job_value, default=None,
                       metavar='N', help='Total compiler/conversion worker budget (default: auto, CPU quota and RAM headroom)')
    group.add_argument('--single-thread', dest='jobs', action='store_const', const=1,
                       help='Alias for --jobs 1; serialize compilation and conversion')
