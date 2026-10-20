"""One BLAS/LAPACK kernel for every build and test process (TESTS-HEAD-REDUCER-BYTES-CI-45).

NumPy and SciPy wheels carry OpenBLAS built with DYNAMIC_ARCH: at load time it picks its kernels by the
processor (SkylakeX on a processor with AVX-512, Haswell or Zen on AVX2 processors, Sandybridge, Nehalem or
older ones below that). Kernels of different families round the last bit of a matrix product, a
pseudo-inverse or an SVD differently. The NPC bake carries such a last-bit difference into its skin
(a texel of 219.99999 is written as 219 instead of 220), so the same game data baked the same NPC with
different bytes on different processors: three families, three results, measured 20 October 2026 with
OPENBLAS_CORETYPE on one machine (the third is the digest a hosted CI runner produced).

pin() selects one kernel family, Haswell (AVX2 + FMA: every x86-64 processor since about 2013-2015,
including the hosted CI runners), through OPENBLAS_CORETYPE, which OpenBLAS reads once when NumPy or SciPy
is first imported. It therefore has to run before the first NumPy import of a process; child processes
inherit it. An explicit OPENBLAS_CORETYPE in the environment wins. A processor without AVX2 + FMA, or
another architecture, is left unpinned (its kernel may differ; key() records that so caches never mix it
with pinned results).
"""
import os
import platform
import sys

VARIABLE = 'OPENBLAS_CORETYPE'
PINNED = 'Haswell'
NEEDS = ('avx2', 'fma')


def _x86_64():
    return platform.machine().lower() in ('x86_64', 'amd64')


def cpu_supports_pinned():
    """True when this processor runs the PINNED kernel family (x86-64 with AVX2 and FMA)."""
    if not _x86_64():
        return False
    if sys.platform.startswith('linux'):
        try:
            with open('/proc/cpuinfo', encoding='utf-8', errors='replace') as cpuinfo:
                for line in cpuinfo:
                    if line.startswith('flags'):
                        flags = set(line.split(':', 1)[1].split())
                        return all(flag in flags for flag in NEEDS)
        except OSError:
            return False
        return False
    if sys.platform == 'win32':
        try:
            import ctypes
            # PF_AVX2_INSTRUCTIONS_AVAILABLE (40); every processor with AVX2 used by Windows has FMA3.
            return bool(ctypes.windll.kernel32.IsProcessorFeaturePresent(40))
        except (AttributeError, OSError):
            return False
    return False


def pin(environ=None):
    """Set OPENBLAS_CORETYPE to the pinned family unless it is already set. Returns the kernel family in the
    environment afterwards, or None when this processor cannot run it (left unpinned)."""
    environ = os.environ if environ is None else environ
    if environ.get(VARIABLE):
        return environ[VARIABLE]
    if not cpu_supports_pinned():
        return None
    environ[VARIABLE] = PINNED
    return PINNED


def pinned_environment(base=None):
    """A copy of BASE (default os.environ) with the PINNED family set, also over an explicit other choice (for
    reference results recorded with it), for a child process. Raises ValueError with the reason when this
    processor cannot run the pinned family."""
    environ = dict(os.environ if base is None else base)
    environ.pop(VARIABLE, None)
    if pin(environ) is None:
        raise ValueError('this processor (%s) cannot run the pinned OpenBLAS kernel %s (needs x86-64 with %s)'
                         % (platform.machine(), PINNED, ' + '.join(NEEDS).upper()))
    return environ


def key():
    """Cache-key text naming the BLAS library and kernel family this process computes with. Results baked
    with different kernels are different bytes, so they never share a key."""
    library = 'unknown'
    try:
        import numpy
        blas = numpy.__config__.CONFIG['Build Dependencies']['blas']
        library = '%s %s' % (blas.get('name'), blas.get('version'))
    except (ImportError, AttributeError, KeyError, TypeError):
        pass
    return 'blas=%s; %s=%s' % (library, VARIABLE, os.environ.get(VARIABLE) or 'unpinned-' + platform.machine())
