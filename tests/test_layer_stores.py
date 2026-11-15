"""The expansions' CHIM stores in the image (tools/chim/layer_stores.py): one store per selected layer whose CHIM world
stage is in the plan; with --no-dlc, or without a layer stage, the steps and the image are exactly as before."""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import build  # noqa: E402
from chim import layer_stores as L  # noqa: E402


def tool(name, *parts):
    return ['python3', name, *[str(p) for p in parts]]


def tree_sha(folder):
    h = hashlib.sha256()
    for path in sorted(Path(folder).rglob('*')):
        if path.is_file():
            h.update(str(path.relative_to(folder)).encode() + b'\0' + hashlib.sha256(path.read_bytes()).digest())
    return h.hexdigest()


class Plan(unittest.TestCase):
    def steps(self, *layers):
        return ([('chim', tool('chim_build.py'))] + [(L.stage_name(x), tool('layer.py')) for x in layers]
                + [('image', tool('build_aga.py', 'image'))])

    def test_no_dlc_changes_nothing(self):
        for selected in ([], None):
            args = SimpleNamespace(expansion_layers={'selected': selected})
            self.assertEqual(build.chim_layer_image_commands(args, self.steps('Bloodmoon'), Path('/run')),
                             self.steps('Bloodmoon'))
        self.assertEqual(build.chim_layer_image_commands(SimpleNamespace(), self.steps(), Path('/run')), self.steps())

    def test_selected_without_its_stage_changes_nothing(self):
        args = SimpleNamespace(expansion_layers={'selected': ['Tribunal', 'Bloodmoon']})
        self.assertEqual(build.chim_layer_image_commands(args, self.steps(), Path('/run')), self.steps())

    def test_one_store_per_selected_layer_in_load_order(self):
        args = SimpleNamespace(expansion_layers={'selected': ['Bloodmoon', 'Tribunal']})
        steps = build.chim_layer_image_commands(args, self.steps('Bloodmoon', 'Tribunal'), Path('/run'))
        image = dict(steps)['image']
        self.assertEqual(image[-4:], ['--chim-layer-world', 'chimiti=' + str(Path('/run/chim-layer-tribunal')),
                                      '--chim-layer-world', 'chimsol=' + str(Path('/run/chim-layer-bloodmoon'))])
        self.assertNotIn('--chim-layer-world', dict(steps)['chim'])
        only_bm = build.chim_layer_image_commands(SimpleNamespace(expansion_layers={'selected': ['Bloodmoon']}),
                                                  self.steps('Bloodmoon', 'Tribunal'), Path('/run'))
        self.assertEqual(dict(only_bm)['image'][-2:],
                         ['--chim-layer-world', 'chimsol=' + str(Path('/run/chim-layer-bloodmoon'))])

    def test_stores_match_the_layout_plan(self):
        from layout_plan import STORE_UNITS
        for spec in L.LAYERS.values():
            self.assertIn('id1/%s/' % spec['store'], STORE_UNITS)

    def test_parse_refuses(self):
        for bad in (['chimsol'], ['chimx=/w'], ['chimsol=/a', 'chimsol=/b'], ['chimsol=']):
            with self.assertRaises(ValueError):
                L.parse(bad)
        self.assertEqual(L.parse(None), [])


class Install(unittest.TestCase):
    def test_none_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp) / 'id1'
            (id1 / 'chim').mkdir(parents=True)
            (id1 / 'chim' / 'world.cwi').write_bytes(b'base')
            before = tree_sha(id1)
            self.assertEqual(L.install([], id1, {}), [])
            self.assertEqual(tree_sha(id1), before)

    def test_room_store_copied_beside_the_island(self):
        with tempfile.TemporaryDirectory() as tmp:
            world = Path(tmp) / 'run/chim-layer-tribunal'
            (world / 'chim/s00').mkdir(parents=True)
            (world / 'chim/world.cwi').write_bytes(b'cwi')
            (world / 'chim/s00/s0001.ccs').write_bytes(b'pack')
            id1 = Path(tmp) / 'id1'
            (id1 / 'chim').mkdir(parents=True)
            (id1 / 'chim/world.cwi').write_bytes(b'base')
            records = L.install(['chimiti=' + str(world)], id1, {})
            self.assertEqual([(r['store'], r['files'], r['kind']) for r in records], [('chimiti', 2, 'rooms')])
            self.assertEqual((id1 / 'chimiti/s00/s0001.ccs').read_bytes(), b'pack')
            self.assertEqual((id1 / 'chim/world.cwi').read_bytes(), b'base')
            with self.assertRaises(ValueError):          # never over a store already there
                L.install(['chimiti=' + str(world)], id1, {})

    def test_store_without_a_world_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                L.install(['chimiti=' + tmp], Path(tmp) / 'id1', {})


class EngineWiring(unittest.TestCase):
    """The engine side: every store the image carries is selectable by its maps; a door or travel target whose map or
    store is not in the image is refused in game (tests/aga_travel_test.c and aga_chim_placement_light_test.c run
    the rules natively)."""
    SRC = ROOT / 'engine/aga/src'

    def test_guards_are_wired(self):
        world = (self.SRC / 'chim/chim_world.c').read_text(encoding='utf-8')
        self.assertIn('aw_chim_map_store_built = MapStoreBuilt;', world)
        begin = world[world.index('static void MapBeginWork ('):]
        self.assertLess(begin.index('!Chim_StoreInImage (store)'), begin.index('if (!Chim_StoreSelect (store))'))
        scene = (self.SRC / 'aw_scene.c').read_text(encoding='utf-8')
        use_link = scene[scene.index('static int use_link(int i) {'):]
        self.assertLess(use_link.index('!AW_SceneTargetBuilt(links[i].target)'), use_link.index('AW_SceneRoomRefuse('))
        self.assertIn('AW_TravelKeepBuilt(&travel_rows,travel_built,', scene)
        ride = scene[scene.index('static void travel_ride(int i) {'):]
        self.assertLess(ride.index('!AW_SceneTargetBuilt(row->map)'), ride.index('load_scene(&r,0)'))
        self.assertIn('int AW_SceneTargetBuilt(const char *name)', (self.SRC / 'aw_region.c').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
