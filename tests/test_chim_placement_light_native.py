"""World format 0.12 (docs/chim/INTERIOR_STORE.md): the placement light level in the record flags, the store
folder by name, and the real C lightmap and surface cache paths drawing a placement at its own level."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get('AMIWIND_RUNTIME_SOURCE', str(ROOT / 'engine/aga'))) / 'src'


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class PlacementLightNativeTests(unittest.TestCase):
    def test_levels_stores_and_surface_cache(self):
        with tempfile.TemporaryDirectory() as scratch:
            executable = Path(scratch) / 'placement-light-check'
            command = ['cc', '-std=gnu89', '-fsanitize=undefined,float-cast-overflow',
                       '-fno-sanitize-recover=all', '-ffunction-sections', '-fdata-sections',
                       '-Wl,--gc-sections', '-I' + str(SOURCE),
                       str(ROOT / 'tests/aga_chim_placement_light_test.c'),
                       *[str(SOURCE / name) for name in ('r_surf.c', 'r_light.c', 'd_surf.c', 'mathlib.c',
                                                         'chim/chim_format.c')],
                       '-lm', '-o', str(executable)]
            compiled = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            result = subprocess.run([str(executable)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('placement light:', result.stdout)


class PlacementLightSourceTests(unittest.TestCase):
    def test_the_level_is_appended_and_read_from_the_record(self):
        render = (SOURCE / 'render.h').read_text()
        body = render[render.index('typedef struct entity_s'):render.index('} entity_t;')]
        # appended: every earlier member keeps the offset the assembly uses
        self.assertRegex(body.rstrip(), r'(?s)int aw_light;\s*(/\*.*?\*/\s*)?int aw_tint;$', body[-300:])
        chunks = (SOURCE / 'chim/chim_chunks.c').read_text()
        self.assertIn('p->ent.aw_light = ChimFormat_RecordLight (chim_world.minor, r.flags);', chunks)
        self.assertIn('p->ent.aw_light = from->ent.aw_light;', chunks)
        # 0.13: the tint beside it, in the chunk records, their reach copies and the room records
        self.assertIn('p->ent.aw_tint = ChimFormat_RecordTint (chim_world.minor, r.flags);', chunks)
        self.assertIn('p->ent.aw_tint = from->ent.aw_tint;', chunks)
        self.assertIn('p->ent.aw_tint = ChimFormat_RecordTint (h.minor, rec.flags);',
                      (SOURCE / 'chim/chim_room.c').read_text())

    def test_the_cache_keeps_its_level(self):
        local = (SOURCE / 'd_local.h').read_text()
        cache = local[local.index('typedef struct surfcache_s'):local.index('} surfcache_t;')]
        # the variable-length pixels stay last; the level sits in the 64-bit host's padding after mip
        level = re.search(r'\bint\s+light;', cache).start()
        self.assertLess(re.search(r'\bint\s+mip;', cache).start(), level)
        self.assertLess(level, cache.index('data[4]'))
        surf = (SOURCE / 'd_surf.c').read_text()
        self.assertIn('cache->light == r_drawsurf.light', surf)
        self.assertIn('cache->light = r_drawsurf.light;', surf)
        self.assertIn('cache->tint == r_drawsurf.tint', surf)
        self.assertIn('cache->tint = r_drawsurf.tint;', surf)
        # the caller sets the level of the entity being drawn (the world and other entities: 0)
        edge = (SOURCE / 'd_edge.c').read_text()
        self.assertIn('r_drawsurf.light = currententity ? currententity->aw_light : 0;', edge)
        self.assertIn('r_drawsurf.tint = currententity ? currententity->aw_tint : 0;', edge)
        self.assertLess(edge.index('r_drawsurf.tint = currententity'), edge.index('D_CacheSurface (pface, miplevel)'))
        self.assertLess(edge.index('r_drawsurf.light = currententity'), edge.index('D_CacheSurface (pface, miplevel)'))

    def test_format_gate(self):
        header = (SOURCE / 'chim/chim_format.h').read_text()
        self.assertEqual(int(re.search(r'#define CHIM_LIGHT_MINOR\s+(\d+)', header).group(1)), 12)
        self.assertGreaterEqual(int(re.search(r'#define CHIM_FORMAT_MINOR\s+(\d+)', header).group(1)), 13)
        self.assertEqual(int(re.search(r'#define CHIM_TINT_MINOR\s+(\d+)', header).group(1)), 13)

    def test_tint_tables_are_built_on_first_use(self):
        # r_surf.c asks, r_sky.c builds the asked tables only and flushes the cache once they exist
        surf = (SOURCE / 'r_surf.c').read_text()
        self.assertIn('r_tint_wanted |= 1 << tint;', surf)
        self.assertIn('r_block_colormap = R_SurfaceTable (r_drawsurf.surf);', surf)
        sky = (SOURCE / 'r_sky.c').read_text()
        self.assertIn('if(r_tint_wanted)R_BuildTints();', sky)
        self.assertIn('r_tint_colormap[1]=warm_table;', sky)

    def test_packs_open_under_the_store(self):
        world = (SOURCE / 'chim/chim_world.c').read_text()
        self.assertIn('ChimFormat_StorePath (pack->path, sizeof(pack->path), store_name, relative)', world)
        self.assertNotIn('sprintf (pack->path, "chim/%s", relative);', world)


if __name__ == '__main__':
    unittest.main()
