"""Budget-head bakes reduce head and hair with the boundary-locked reducer (NPC-HEAD-DECIMATION-33, decided for
the project 18 October 2026): no new open edge in a face, about the same triangles; the previous reducer stays
selectable byte for byte. Synthetic meshes only (no game data in the suite)."""
import collections
import hashlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]

from test_npc_head_detail import grid, needs_numpy  # noqa: E402

# bake(budget=192, head_detail='budget') of the four-shape fixture below with the code before the locked reducer
# (v0.0.43-moragtong 46a05aa): SHA-256 of frames, faces, uv and skin bytes; 190 faces. Baked with the builder's
# pinned BLAS kernel family (tools/blas_kernel.py, Haswell): other kernel families round the bake's matrix
# products and pseudo-inverses differently in the last bit, and the skin's float-to-byte step turns that into
# other texels (TESTS-HEAD-REDUCER-BYTES-CI-45: 2e30b365... was this fixture under the SkylakeX kernel of an
# AVX-512 processor, 74719be5... under Nehalem/Sandybridge; 46a05aa gives the same three values per kernel).
PREVIOUS_BYTES = '1da14f60d4673a713aca3cae0f08c814399644f5d70977a69768354371923d34'
# The same fixture with the locked reducer (the shipped default), same kernel.
LOCKED_BYTES = '4357e33d0df5f045f1c700d80d69a84ff988ed523724bc79ce45a1913e067851'


def pinned_bake_digests(*modes):
    """{reducer mode: (digest, faces)} of the budget bake, baked in a child process that computes with the
    builder's pinned BLAS kernel family, whatever kernel this process loaded."""
    import json
    import subprocess
    import blas_kernel
    try:
        environ = blas_kernel.pinned_environment()
    except ValueError as exc:
        raise unittest.SkipTest(str(exc))
    environ['PYTHONPATH'] = os.pathsep.join(str(ROOT / name) for name in ('src', 'tools', 'tests'))
    code = ('import json, os, sys\n'
            'from unittest.mock import patch\n'
            'import test_npc_head_reducer as T\n'
            'from npc_geometry import bake\n'
            'case = T.HeadReducer()\n'
            'out = {}\n'
            'for mode in sys.argv[1:]:\n'
            # the previous hair share (NPC-HAIR-BACK-MISSING-53): these digests are of the v0.0.53 split
            '    with patch.dict(os.environ, {"AMIWIND_NPC_HEAD_REDUCER": mode, "AMIWIND_NPC_HAIR_SHARE": "plain"}):\n'
            '        r = bake(case.shapes(), case.materials, {}, case.palette, budget=192, head_detail="budget")\n'
            '    out[mode] = [T.digest(r), len(r[1])]\n'
            'print("DIGESTS " + json.dumps(out))\n')
    done = subprocess.run([sys.executable, '-c', code, *modes], env=environ, capture_output=True, text=True,
                          timeout=600)
    lines = [line for line in done.stdout.splitlines() if line.startswith('DIGESTS ')]
    if done.returncode or not lines:
        raise AssertionError('pinned bake failed (exit %d):\n%s%s' % (done.returncode, done.stdout, done.stderr))
    return {mode: tuple(value) for mode, value in json.loads(lines[-1][8:]).items()}


def open_edges(faces):
    count = collections.Counter(tuple(sorted((int(t[i]), int(t[(i + 1) % 3])))) for t in faces for i in range(3))
    return sum(1 for n in count.values() if n == 1)


def digest(result):
    import numpy as np
    h = hashlib.sha256()
    for part in result[:3]:
        h.update(np.ascontiguousarray(part).tobytes())
    h.update(result[3].tobytes())
    return h.hexdigest()


class HeadReducer(unittest.TestCase):
    palette = bytes(range(256)) * 3
    materials = [{'texture_index': None, 'diffuse': [1., 1., 1.], 'alpha': 1.}]

    def shapes(self):
        return [grid('tri head', 0, 8, 8, 30), grid('tri hair', 1, 6, 4, 33),
                grid('tri chest', 3, 12, 10, 15), grid('tri foot', 15, 6, 4, 0)]

    def test_switch_default_and_export(self):
        import mesh_geometry_env as E
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(E.NPC_HEAD_REDUCER_VARIABLE, None)
            self.assertEqual(E.npc_head_reducer(), 'locked')
            self.assertEqual(E.export_npc_head_reducer('default'), 'default')
            self.assertEqual(os.environ[E.NPC_HEAD_REDUCER_VARIABLE], 'default')
            with self.assertRaises(ValueError):
                E.npc_head_reducer('fast')

    def test_builder_option(self):
        import json
        import build
        from build_font_options import resolve_font_options
        self.assertEqual(build.parser().parse_args(['--npc-head-reducer', 'default']).npc_head_reducer, 'default')
        defaults = json.loads((ROOT / 'config/build-defaults.json').read_text(encoding='utf-8'))
        self.assertEqual(defaults['npc_head_reducer'], 'locked')
        args = build.parser().parse_args([])
        resolved = resolve_font_options(args)
        self.assertEqual((resolved['npc_head_reducer'], resolved['npc_head_reducer_selected_by']),
                         ('locked', 'shipped default'))

    @needs_numpy
    def test_locked_keeps_every_rim(self):
        import numpy as np
        from npc_geometry import simplify_head_locked, simplify_shape
        shape = grid('tri head', 0, 12, 10, 30)
        points, inverse = np.unique(np.round(shape['positions'][0], 5), axis=0, return_inverse=True)
        faces = inverse.reshape(-1)[shape['faces'].reshape(-1)].reshape(-1, 3)
        source = open_edges(faces)
        quota = len(faces) // 6
        p, f = simplify_head_locked(points, faces, quota)
        self.assertEqual(open_edges(f), source)
        self.assertLessEqual(len(f), quota + 8)
        kept = {tuple(x) for x in np.asarray(p)[np.unique(f)]}
        from static_lod import boundary_vertices
        for i in boundary_vertices(faces):
            self.assertIn(tuple(points[i]), kept)
        # the previous reducer moves the rim of the same grid (the gash of NPC-HEAD-DECIMATION-33)
        _, previous = simplify_shape(points, faces.astype(np.int32), quota)
        self.assertNotEqual(open_edges(previous), source)

    @needs_numpy
    def test_previous_reducer_reproduces_the_previous_bytes(self):
        # Exact bytes, under the one kernel family every build computes with (not this process's kernel).
        out = pinned_bake_digests('default', 'locked')
        self.assertEqual(out['default'], (PREVIOUS_BYTES, 190))
        self.assertEqual(out['locked'], (LOCKED_BYTES, 189))
        self.assertNotEqual(out['locked'][0], PREVIOUS_BYTES)
        self.assertLessEqual(abs(out['locked'][1] - out['default'][1]), 8)

    @needs_numpy
    def test_original_heads_are_unchanged(self):
        # original mode keeps heads exact; its bake does not depend on the reducer setting
        from npc_geometry import bake
        out = {}
        for mode in ('locked', 'default'):
            with patch.dict(os.environ, {'AMIWIND_NPC_HEAD_REDUCER': mode}):
                out[mode] = digest(bake(self.shapes(), self.materials, {}, self.palette, head_detail='original'))
        self.assertEqual(out['locked'], out['default'])

    def test_gallery_key_carries_the_reducer_for_budget_heads(self):
        try:
            import numpy  # noqa: F401
            import gallery_cache
        except ImportError:
            self.skipTest('Install optional NPC conversion dependencies')
        spec = {'kind': 'NPC_', 'appearance': {'parts': [], 'skeleton': 'meshes/base_anim.nif', 'height': 1, 'weight': 1}}
        keys = {}
        for reducer in ('locked', 'default'):
            with patch.dict(os.environ, {'AMIWIND_NPC_HEAD_DETAIL': 'budget', 'AMIWIND_NPC_HEAD_REDUCER': reducer}):
                keys[reducer] = gallery_cache.identity(spec, b'p', {}, {}, {})
        self.assertEqual(keys['locked']['npc_head_reducer'], 'locked')
        self.assertNotEqual(gallery_cache.token(keys['locked']), gallery_cache.token(keys['default']))
        with patch.dict(os.environ, {'AMIWIND_NPC_HEAD_DETAIL': 'original'}):
            self.assertIsNone(gallery_cache.identity(spec, b'p', {}, {}, {})['npc_head_reducer'])

class HeadReducerFallbackTests(unittest.TestCase):
    def test_over_budget_locked_head_falls_back_to_the_previous_reducer(self):
        # v0.0.43-dev4 build: the npcs stage stopped on 'Alias vertex budget exceeded' with the locked reducer.
        import npc_geometry as g
        seen = []
        def run(reducer):
            seen.append(reducer)
            if reducer == 'locked':
                raise g.AliasOverflow('Alias vertex budget exceeded', 3)
            return 'baked'
        self.assertEqual(g._retry_head_reducer(run, 'locked'), 'baked')
        self.assertEqual(seen, ['locked', None])

    def test_other_overflows_still_raise(self):
        import npc_geometry as g
        def run(reducer):
            raise g.AliasOverflow('Alias vertex budget exceeded', 1)
        with self.assertRaises(g.AliasOverflow):
            g._retry_head_reducer(run, None)


if __name__ == '__main__':
    unittest.main()
