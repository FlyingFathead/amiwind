# SPDX-License-Identifier: GPL-3.0-only
"""Real shared-harvest state, renderer and runtime with synthetic inputs."""
import math
from pathlib import Path
import tempfile
import unittest

import test_aga_native_source as native


class SharedHarvestNativeTests(unittest.TestCase):
    def compile(self, fixture, names, arguments=()):
        native.NativeSourceTests().compile_run(fixture,
            [Path(native.SOURCE)/'src'/name for name in names],
            cflags=['-fsanitize=undefined,float-cast-overflow', '-fno-sanitize-recover=all'],
            arguments=arguments)

    def test_same_original_facts_across_brush_alias_save_and_return(self):
        self.compile('aga_harvest_mixed_test.c', ['aw_harvest.c', 'aw_state.c', 'aw_save_codec.c'])

    def test_shared_proxy_lifetime_capacity_failure_and_no_reroll(self):
        self.compile('aga_harvest_proxy_test.c', ['aw_harvest_proxy.c', 'aw_harvest.c', 'aw_state.c'])

    def test_real_model_slot_admission_preserves_active_cache_and_lru(self):
        native.NativeSourceTests().compile_run('aga_harvest_model_slots_test.c',
            [Path(native.SOURCE)/'src'/name for name in ('model.c','mathlib.c')],
            cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all', '-Wl,--wrap=malloc'])

    def test_actual_runtime_scaled_pick_occlusion_empty_and_inventory_retry(self):
        self.compile('aga_harvest_alias_runtime_test.c',
                     ['aw_harvest_runtime.c', 'aw_harvest.c', 'aw_state.c', 'mathlib.c'])

    def test_actual_alias_matrix_on_tilted_scaled_synthetic_placements(self):
        # Independent right-handed rotation composition: Rz(yaw) Ry(-pitch)
        # Rx(roll). The C fixture calls actual R_AliasSetUpTransform.
        lines=[]
        for pitch in (-70, 0, 50):
            for yaw in (0, 90, 233):
                for roll in (-40, 0, 65):
                    for scale in (.5, 1, 2.25):
                        for n in range(12):
                            point=(n*.125-1, (n%3)-1, (n%5)*.25)
                            origin=(20, -5, 13)
                            p,y,r=map(math.radians,(-pitch,yaw,roll))
                            a,b,c=point
                            b,c=b*math.cos(r)-c*math.sin(r),b*math.sin(r)+c*math.cos(r)
                            a,c=a*math.cos(p)+c*math.sin(p),-a*math.sin(p)+c*math.cos(p)
                            a,b=a*math.cos(y)-b*math.sin(y),a*math.sin(y)+b*math.cos(y)
                            expected=tuple(v*scale+o for v,o in zip((a,b,c),origin))
                            lines.append(' '.join('%.9g'%v for v in (*origin,pitch,yaw,roll,scale,*point,*expected)))
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'poses.txt';path.write_text('\n'.join(lines)+'\n')
            self.compile('aga_harvest_alias_pose_test.c', ['r_alias.c','r_sprite.c','mathlib.c'], [str(path)])


if __name__=='__main__':
    unittest.main()
