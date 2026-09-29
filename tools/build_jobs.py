"""Shared job limit for the native and BSP compilers."""
import argparse
import math
import os
from pathlib import Path


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
                       metavar='N', help='Total compiler/conversion worker budget (default: auto, available CPU threads)')
    group.add_argument('--single-thread', dest='jobs', action='store_const', const=1,
                       help='Alias for --jobs 1; serialize compilation and conversion')
