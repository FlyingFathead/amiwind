# SPDX-License-Identifier: GPL-3.0-only
"""Same-lit placements share one model (prepare_mesh_bsp.unlit_placement, v0.0.42 plan 2.1)."""
import math
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import prepare_mesh_bsp as pmb


def quad_model(size=8.):
    """One square face in map units, mapped 1 texel per unit at texture size 16 (axes / 16)."""
    p = np.array([[0., 0, 0], [size, 0, 0], [size, size, 0], [0, size, 0]])
    axes = np.array([[1., 0], [0, 1], [0, 0]]) / 16
    v = np.column_stack((p * 4, np.zeros((4, 2))))
    return (v, np.array([[0, 1, 2, 0], [0, 2, 3, 0]]), [(p, 0, axes, np.zeros(2), np.array([0., 0, 1]))], [], {})


def ref_at(x, y, z=0., number=1, yaw=0.):
    return {'model_index': 0, 'scale': 1., 'number': number, 'position': [x, y, z], 'rotation_radians': [0, 0, yaw]}


LIGHTING = {'ambient': [40, 40, 40], 'lights': [{'position': [0, 0, 64], 'radius': 256, 'color': [255, 200, 100]}]}


class SharedAmbientTests(unittest.TestCase):
    def test_key_drops_the_reference_only_when_unlit(self):
        a, b = ref_at(0, 0, number=1), ref_at(0, 0, number=2)
        self.assertNotEqual(pmb._instance_key(a, LIGHTING), pmb._instance_key(b, LIGHTING))
        self.assertEqual(pmb._instance_key(a, LIGHTING, True), pmb._instance_key(b, LIGHTING, True))
        self.assertEqual(pmb._instance_key(a, None), pmb._instance_key(b, None))

    def test_near_light_is_lit_far_is_unlit(self):
        model = quad_model()
        # light at (0, 0, 16) map units with radius 64 map units (linear falloff)
        self.assertFalse(pmb.unlit_placement(ref_at(0, 0), model, LIGHTING, (0, 0), 16))
        self.assertTrue(pmb.unlit_placement(ref_at(4000, 0), model, LIGHTING, (0, 0), 16))
        original = {**LIGHTING, 'falloff': 'original'}
        # 100 map units away: outside the linear reach (64) but inside the original one (128)
        far = ref_at(400 + 0, 0)
        self.assertTrue(pmb.unlit_placement(far, model, LIGHTING, (0, 0), 16))
        self.assertFalse(pmb.unlit_placement(far, model, original, (0, 0), 16))

    def test_never_unlit_with_zones_off_lights_kept(self):
        model = quad_model()
        zoned = {**LIGHTING, 'zones': [{'box': [[0, 0, 0], [1, 1, 1]], 'scale': .5}]}
        self.assertFalse(pmb.unlit_placement(ref_at(4000, 0), model, zoned, (0, 0), 16))
        self.assertFalse(pmb.unlit_placement({**ref_at(4000, 0), 'light': {'radius': 0}}, model, LIGHTING, (0, 0), 16))
        off = {**LIGHTING, 'lights': [{**LIGHTING['lights'][0], 'flags': 0x20}]}
        self.assertTrue(pmb.unlit_placement(ref_at(0, 0), model, off, (0, 0), 16))

    def test_an_unlit_placement_bakes_only_the_ambient(self):
        """The rule is exact: wherever the predicate says unlit, every baked sample is the ambient value, so a
        shared model draws what each placement's own model drew."""
        model = quad_model(24.)
        ambient = round(float(np.dot(LIGHTING['ambient'], [.299, .587, .114])))
        rng = np.random.default_rng(7)
        unlit = lit = 0
        for n in range(160):
            x, y = rng.uniform(-500, 500, 2)
            ref = ref_at(x, y, rng.uniform(-50, 50), n, rng.uniform(0, math.tau))
            surfaces, _, _, _ = pmb._prepare_placement((ref, model, 16, (0, 0), LIGHTING))
            samples = b''.join(s[5] for s in surfaces)
            if pmb.unlit_placement(ref, model, LIGHTING, (0, 0), 16):
                unlit += 1
                self.assertEqual(set(samples), {ambient})
            else:
                lit += 1
        self.assertGreater(unlit, 20)
        self.assertGreater(lit, 5)

    def test_mode_switch(self):
        with mock.patch.dict(os.environ, {pmb.SHARED_AMBIENT_ENV: ''}):
            self.assertEqual(pmb.shared_ambient_mode(), 'unlit')
        with mock.patch.dict(os.environ, {pmb.SHARED_AMBIENT_ENV: 'off'}):
            self.assertEqual(pmb.shared_ambient_mode(), 'off')
        with mock.patch.dict(os.environ, {pmb.SHARED_AMBIENT_ENV: 'sometimes'}):
            with self.assertRaises(ValueError):
                pmb.shared_ambient_mode()


if __name__ == '__main__':
    unittest.main()
