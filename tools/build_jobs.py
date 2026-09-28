"""Shared job limit for the native and BSP compilers."""
import argparse
import math
import os
from pathlib import Path


def auto_jobs():
    counts = [os.cpu_count() or 1]
    if hasattr(os, 'process_cpu_count'):
        counts.append(os.process_cpu_count() or 1)
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
    return auto_jobs() if value is None else value


def add_jobs(parser):
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-j', '--jobs', '--j', type=job_value, default=None,
                       metavar='N', help='Compiler jobs (default: auto, available CPU threads)')
    group.add_argument('--single-thread', dest='jobs', action='store_const', const=1,
                       help='Alias for --jobs 1 for native and map compilation')
