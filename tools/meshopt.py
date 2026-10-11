# SPDX-License-Identifier: GPL-3.0-only
"""meshoptimizer's simplifier (third_party/meshoptimizer, MIT) for the CHIM mesh method `meshopt+merge`.

The vendored sources are compiled once per source hash with the build environment's C++ compiler
(`c++`, or AMIWIND_CXX) into a shared library in a cache folder (AMIWIND_MESHOPT_CACHE, default the
build's scratch folder, build_scratch.scratch_root): no download and no prebuilt binary. The library file name carries the
SHA-256 of the sources and the compiler command, so a changed source or flag builds a new one; a
finished library is written to a temporary name and renamed into place, so parallel workers never
load a half-written file.

simplify_locked: every connected part of every material separately (as static_lod.reduce_mesh reduces
them; parts of at most 12 triangles are kept whole), each to about ratio of its triangles, with
meshopt_SimplifyLockBorder; no collapse may move the surface more than ERROR_SHARE of the whole mesh's
diagonal, and a part whose result would no longer span its source part is kept whole. A vertex on
the material's open border keeps its exact position, so the rims where parts meet stay where the source
has them (the seam rule of MESH-LOD-OPEN-SEAMS-33). Vertices are welded by exact position and texture
coordinate first, so the simplifier sees one connected surface per material; texture seams inside a
material are borders too. The result references source vertices only (no new positions), so it is
deterministic: the same input gives the same output on every run and with any number of workers.
"""
import ctypes
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'third_party/meshoptimizer'
FILES = ('meshoptimizer.h', 'simplifier.cpp', 'allocator.cpp')
FLAGS = ('-O2', '-fPIC', '-shared', '-fno-fast-math', '-ffp-contract=off')
LOCK_BORDER = 1          # meshopt_SimplifyLockBorder
ERROR_ABSOLUTE = 4       # meshopt_SimplifyErrorAbsolute: target_error in mesh units
# the largest deviation a collapse may cause, as a share of the whole mesh's diagonal: thin parts (spars, rails)
# keep their shape instead of collapsing to a line to reach the ratio (measured on the arrival ship)
ERROR_SHARE = 0.0025
_LIB = None


def source_sha256():
    h = hashlib.sha256()
    for name in FILES:
        h.update(name.encode() + b'\0' + (SOURCE / name).read_bytes())
    return h.hexdigest()


def compiler():
    return os.environ.get('AMIWIND_CXX', 'c++')


def library_path():
    key = hashlib.sha256((source_sha256() + '|' + compiler() + '|' + ' '.join(FLAGS)).encode()).hexdigest()[:16]
    # never the system temp folder: in the build container /tmp is noexec, a library there cannot be loaded
    # (CHIM-ZONE-TMP-NOEXEC-33); the build's scratch (build_scratch.scratch_root) holds it for the run
    from build_scratch import scratch_root
    folder = Path(os.environ.get('AMIWIND_MESHOPT_CACHE') or scratch_root() / 'meshopt')
    return folder / ('amiwind-meshopt-%s.so' % key)


def build():
    """The compiled library (built once per source and flags)."""
    path = library_path()
    if path.is_file():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + '.', dir=str(path.parent))
    os.close(fd)
    try:
        subprocess.run([compiler(), *FLAGS, '-o', tmp, str(SOURCE / 'simplifier.cpp'), str(SOURCE / 'allocator.cpp')],
                       check=True, capture_output=True)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return path


def available():
    """True when the library can be built (a C++ compiler is present)."""
    try:
        build()
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def _lib():
    global _LIB
    if _LIB is None:
        lib = ctypes.CDLL(str(build()))
        lib.meshopt_simplify.restype = ctypes.c_size_t
        lib.meshopt_simplify.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p,
                                         ctypes.c_size_t, ctypes.c_size_t, ctypes.c_size_t, ctypes.c_float,
                                         ctypes.c_uint, ctypes.c_void_p]
        _LIB = lib
    return _LIB


def _keeps_extent(vertices, part, tri, share=0.9):
    """True when the simplified part still spans its source part: every axis of its box at least share of the
    source's (or within 0.5 units). A closed thin part (a mast pole, a rope: no open border to lock) can collapse
    to nothing or to a line to reach the ratio (measured on the arrival ship: four mast poles and a rope); such a
    part is kept whole instead."""
    if len(tri) == 0:
        return False
    a = np.ptp(vertices[part[:, :3].reshape(-1), :3], axis=0)
    b = np.ptp(vertices[tri.reshape(-1), :3], axis=0)
    return bool(np.all((b >= a * share) | (a - b <= 0.5)))


def simplify_locked(vertices, faces, ratio, preserve_materials=(), error_share=ERROR_SHARE):
    """(vertices, faces): faces (n, 4: a b c material) reduced per connected part of each material to about
    ratio, borders locked. vertices are returned unchanged (the output references them); materials in
    preserve_materials and parts of at most 12 triangles are kept whole, as static_lod.reduce_mesh does."""
    if not 0 < ratio <= 1:
        raise ValueError('Invalid meshopt ratio')
    lib = _lib()
    vertices = np.asarray(vertices, dtype=float)
    faces = np.asarray(faces, dtype=np.int64)
    from mesh_geometry import connected_components
    used_all = vertices[np.unique(faces[:, :3]), :3]
    max_error = float(np.linalg.norm(used_all.max(axis=0) - used_all.min(axis=0))) * error_share if len(used_all) else 0.0
    out = []
    groups = []
    for material in sorted(set(faces[:, 3].tolist())):
        mf = faces[faces[:, 3] == material]
        if ratio == 1 or material in set(preserve_materials):
            out.append(mf)
            continue
        # each connected part on its own, as static_lod.reduce_mesh: a small part (a spar, a rope) is never
        # collapsed away by a larger neighbour's budget
        groups += [mf[ids] for ids in connected_components(vertices, mf)]
    for mf in groups:
        material = int(mf[0, 3])
        if len(mf) <= 12:
            out.append(mf)
            continue
        # weld by exact position + texture coordinate: one connected surface per material
        used = np.unique(mf[:, :3].reshape(-1))
        keys, inverse = np.unique(vertices[used, :5], axis=0, return_inverse=True)
        first = np.full(len(keys), -1, dtype=np.int64)
        for k, g in zip(inverse.reshape(-1), used):
            if first[k] < 0:
                first[k] = g
        local = np.full(int(used.max()) + 1, -1, dtype=np.int64)
        local[used] = inverse.reshape(-1)
        idx = np.ascontiguousarray(local[mf[:, :3]].reshape(-1), dtype=np.uint32)
        pos = np.ascontiguousarray(keys[:, :3], dtype=np.float32)
        dest = np.zeros_like(idx)
        target = max(3, int(len(mf) * ratio) * 3)
        err = ctypes.c_float(0)
        n = lib.meshopt_simplify(dest.ctypes.data, idx.ctypes.data, len(idx), pos.ctypes.data, len(pos), 12,
                                 target, ctypes.c_float(max_error), LOCK_BORDER | ERROR_ABSOLUTE, ctypes.byref(err))
        tri = first[dest[:n].reshape(-1, 3).astype(np.int64)]
        if not _keeps_extent(vertices, mf, tri):
            out.append(mf)                  # a part the simplifier would remove or flatten stays whole
            continue
        out.append(np.column_stack((tri, np.full(len(tri), material))))
    return vertices, (np.vstack(out) if out else faces[:0])
