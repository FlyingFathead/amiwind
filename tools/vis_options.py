# SPDX-License-Identifier: GPL-3.0-only
"""Shared ericw vis options for every map converter.

vis computes each leaf's potentially visible set (PVS). '-fast' keeps only the
portal flood, which is what every converter has used so far; without it vis
runs the full portal flow. Full vis cannot hide much in today's towns because
buildings are func_wall models that never form leaf walls (see
docs/performance/TOWN-VISIBILITY.md), so fast stays the default until
structural occluders exist; the option lets a build measure full vis now.

Threads come from the existing --jobs budget: a map compiled alone gets the
whole budget, maps compiled side by side share it.
"""
VIS_MODES = ('fast', 'full')
DEFAULT_VIS_MODE = 'fast'


def map_threads(jobs, concurrent_maps=1):
    """vis threads for one of `concurrent_maps` maps compiled at the same time."""
    jobs, concurrent_maps = int(jobs), int(concurrent_maps)
    if jobs < 1:
        raise ValueError('vis needs at least one thread')
    return max(1, jobs // max(1, concurrent_maps))


def vis_args(target, threads, mode=DEFAULT_VIS_MODE, fast_first=False):
    """Arguments after the vis executable; the default matches the historical
    '-threads N -fast map.bsp' (fast_first: '-fast -threads N map.bsp')."""
    if mode not in VIS_MODES:
        raise ValueError('Unknown vis mode: ' + str(mode))
    threads = ['-threads', str(map_threads(threads))]
    fast = ['-fast'] if mode == 'fast' else []
    return [*(fast + threads if fast_first else threads + fast), str(target)]


def vis_kwargs(mode):
    """Keyword to pass on only when not the default, so existing call
    signatures and recorded command lines stay unchanged by default."""
    if mode not in VIS_MODES:
        raise ValueError('Unknown vis mode: ' + str(mode))
    return {} if mode == DEFAULT_VIS_MODE else {'vis_mode': mode}


def add_vis_option(parser, flag='--vis-mode'):
    parser.add_argument(flag, dest='vis_mode', choices=VIS_MODES, default=DEFAULT_VIS_MODE,
                        help='vis pass: fast (portal flood only, default; outputs unchanged) or full '
                             '(full portal flow; slower, see docs/performance/TOWN-VISIBILITY.md)')


# ericw light 0.18.1 writes faces and lightmaps in a thread-dependent order: the
# same map lit with more than one thread is not byte-reproducible (measured:
# two runs with 2-8 threads differ in the faces and lighting lumps; one thread
# is identical every time). Every map is therefore lit with one thread; builds
# get their speed from lighting maps side by side in the worker pool.
LIGHT_THREADS = 1


def light_args(*options):
    """Arguments after the light executable: one thread, then the options."""
    return ['-threads', str(LIGHT_THREADS), *map(str, options)]
