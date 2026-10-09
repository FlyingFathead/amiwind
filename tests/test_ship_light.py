"""Prison ship light (OPENING-BRIGHT-31, OPENING-JIUB-LANTERN-32) and the actor
light grid (NPC-LIGHT-COHERENCE-32): per-cell profile, warm faces, grid keys,
and the unchanged bake of every other cell."""
import random, re, sys, unittest
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import interior_lighting as il

# The ship's light records as the original master has them (position in
# original units): the hanging lantern above Jiub and the deck lantern.
LANTERN = {'radius': 200, 'color': [245, 140, 40], 'flags': 81, 'position': [82.696, -36.900, 90.441]}
DECK = {'radius': 64, 'color': [245, 140, 40], 'flags': 83, 'position': [55.655, -110.403, 142.823]}
SHIP = {'name': 'Imperial Prison Ship', 'lighting': {'ambient': [80, 61, 41], 'sunlight': [66, 51, 34]},
        'refs': [{'light': LANTERN, 'position': LANTERN['position']}, {'light': DECK, 'position': DECK['position']}]}
SPAWN, JIUB = np.array([0., -35, -4]), np.array([4.5, -16.35, -25.86])
LANTERN_LOCAL = np.array(LANTERN['position']) * .25


def legacy_bake(polygon, axes, offset, rotation, origin, lighting):
    """The bake as it was before the per-cell profiles (v0.0.32), for the
    unchanged-output check."""
    uv = polygon @ axes + offset
    low = np.floor(uv.min(0) / 16) * 16; high = np.ceil(uv.max(0) / 16) * 16
    size = ((high - low) / 16).astype(int) + 1
    normal = np.cross(polygon[1] - polygon[0], polygon[2] - polygon[0]); normal /= np.linalg.norm(normal)
    matrix = np.vstack((axes.T, normal)); distance = normal @ polygon[0]
    inverse = np.linalg.inv(matrix) if abs(np.linalg.det(matrix)) > 1e-10 else None
    samples = []
    base = float(np.dot(lighting['ambient'], [.299, .587, .114]))
    original = lighting.get('falloff', 'linear') == 'original'; zones = lighting.get('zones', ())
    for t in range(size[1]):
        for s in range(size[0]):
            local = (inverse @ np.array([low[0] + s * 16 - offset[0], low[1] + t * 16 - offset[1], distance])
                     if inverse is not None else polygon.mean(axis=0))
            point = local @ rotation.T + origin; value = base
            for light in lighting['lights']:
                radius = light['radius'] * .25
                if radius <= 0 or light.get('flags', 0) & il.OFF_BY_DEFAULT: continue
                delta = np.array(light['position']) * .25 - point; dist = np.linalg.norm(delta)
                if original:
                    if dist < 2 * radius: value += np.dot(light['color'], [.299, .587, .114]) * il.original_weight(dist, radius)
                elif dist < radius:
                    value += np.dot(light['color'], [.299, .587, .114]) * (1 - dist / radius)
            if zones: value *= il.zone_scale(point, zones)
            samples.append(round(max(0, min(255, value))))
    return bytes(samples)


def parse_grid(entities):
    keys = dict(re.findall(r'"(_aw_lightgrid\d*)" "([^"]*)"', entities))
    step, nx, ny, nz, *origin = keys.pop('_aw_lightgrid').split()
    data = ''.join(keys['_aw_lightgrid%d' % i] for i in range(len(keys)))
    return int(step), (int(nx), int(ny), int(nz)), [float(v) for v in origin], bytes.fromhex(data), keys


class ShipLightTests(unittest.TestCase):
    def test_other_cells_keep_their_lighting_and_bake(self):
        cell = dict(SHIP, name='Seyda Neen, Census and Excise Office')
        lighting = il.cell_lighting(cell)
        self.assertEqual(lighting, {**cell['lighting'], 'lights': [dict(LANTERN, position=LANTERN['position']),
                                                                    dict(DECK, position=DECK['position'])]})
        rng = random.Random(33)
        for n in range(60):
            poly = np.array([[rng.uniform(-40, 40) for _ in range(3)] for _ in range(3)])
            if np.linalg.norm(np.cross(poly[1] - poly[0], poly[2] - poly[0])) < 1: continue
            axes = np.array([[1., 0], [0, 1], [0, 0]]) if n % 3 else np.array([[0., 1], [0, 0], [1, 0]])
            yaw = rng.uniform(0, 6.3); rot = np.array([[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]])
            origin = np.array([rng.uniform(-30, 30) for _ in range(3)])
            light = {'ambient': [rng.randint(0, 120)] * 3,
                     'lights': [{'radius': rng.randint(16, 400), 'color': [rng.randint(0, 255) for _ in range(3)],
                                 'flags': rng.choice([0, 0x20, 0x51]), 'position': [rng.uniform(-200, 200) for _ in range(3)]}
                                for _ in range(rng.randint(0, 4))]}
            if n % 4 == 1: light['falloff'] = 'original'
            if n % 5 == 2: light['zones'] = [{'box': [[-20, -20, -20], [20, 20, 20]], 'scale': .5, 'soft': 8}]
            self.assertEqual(il.bake_surface(poly, axes, np.zeros(2), rot, origin, light),
                             legacy_bake(poly, axes, np.zeros(2), rot, origin, light), n)
            self.assertEqual(il.surface_style(poly, rot, origin, light), 0)

    def test_ship_profile_halves_the_start_and_keeps_the_lantern(self):
        lighting = il.cell_lighting(SHIP)
        self.assertEqual(lighting['falloff'], 'original'); self.assertTrue(lighting['facing'])
        self.assertTrue(lighting['warm_style'])
        ambient = float(np.dot(SHIP['lighting']['ambient'], il.LUMA))
        far = {**lighting, 'lights': []}
        for point in (SPAWN, JIUB, np.array([0., -150, 0])):
            # ambient alone: 0.35 x 0.71 of v0.0.32 at the start end of the hold
            self.assertAlmostEqual(il.point_light(point, far), .35 * .71 * ambient, places=6)
        self.assertAlmostEqual(il.point_light(np.array([0., 200, 0]), far), ambient, places=6)
        # the lanterns keep 0.71 inside the zone: right under one the light is
        # far above the darkened ambient
        below = LANTERN_LOCAL - [0, 0, 8]
        self.assertGreater(il.point_light(below, lighting, normal=np.array([0., 0, 1])), .35 * .71 * ambient + 80)
        # the original falloff: a third at the radius, nothing beyond twice it
        self.assertAlmostEqual(il.light_weight(LANTERN, LANTERN_LOCAL + [50, 0, 0], lighting), 1 / 3)
        self.assertEqual(il.light_weight(LANTERN, LANTERN_LOCAL + [101, 0, 0], lighting), 0)
        # facing term: a face turned away from the lantern gets none of it
        self.assertEqual(il.light_weight(LANTERN, below, lighting, normal=np.array([0., 0, -1])), 0)

    def test_lantern_faces_are_warm_and_others_are_not(self):
        lighting = il.cell_lighting(SHIP); rot = np.eye(3)
        def face(centre, normal):
            normal = np.asarray(normal, float); u = np.cross(normal, [0.3, 0.5, 0.7]); u /= np.linalg.norm(u)
            v = np.cross(normal, u)
            return np.array([centre - 4 * u - 4 * v, centre + 4 * u - 4 * v, centre + 4 * v])
        under = face(LANTERN_LOCAL - [0, 0, 12], [0, 0, 1])
        self.assertEqual(il.surface_style(under, rot, np.zeros(3), lighting), il.WARM_STYLE)
        self.assertEqual(il.surface_style(under[::-1], rot, np.zeros(3), lighting), 0)  # facing away
        self.assertEqual(il.surface_style(face(np.array([0., 300, 0]), [0, 0, 1]), rot, np.zeros(3), lighting), 0)
        blue = {**lighting, 'lights': [dict(LANTERN, color=[0, 166, 255])]}
        self.assertEqual(il.surface_style(under, rot, np.zeros(3), blue), 0)
        self.assertEqual(il.surface_style(under, rot, np.zeros(3), {**lighting, 'warm_style': False}), 0)

    def test_lantern_glass_glows_in_the_ship_only(self):
        ship = il.cell_lighting(SHIP); other = il.cell_lighting(dict(SHIP, name='Balmora, Guild of Mages'))
        lantern = {'source': 'meshes/l/light_com_lantern_02.nif', 'flames': [[-2.384, 0.056, -19.361, 0.8, 2.5, 3.5, 0.368]]}
        glass = {'texture_source': 'Tx_window_pane.tga'}; frame = {'texture_source': 'Tx_metal_strip_01.tga'}
        self.assertEqual(il.glass_glow(lantern, glass, ship), 7)
        self.assertEqual(il.glass_glow(lantern, frame, ship), 0)
        self.assertEqual(il.glass_glow(dict(lantern, flames=[]), glass, ship), 0)  # no flame inside
        self.assertEqual(il.glass_glow(lantern, glass, other), 0)
        self.assertEqual(il.glass_glow(lantern, glass, None), 0)
        self.assertTrue(il.warm_light(LANTERN)); self.assertFalse(il.warm_light({'color': [0, 166, 255]}))

    def test_actor_light_grid_keys(self):
        lighting = il.cell_lighting(SHIP)
        grid = il.light_grid(lighting, [-85, -195, -42], [90, 412, 96])
        self.assertIsNotNone(grid)
        text = il.add_light_grid('{\n"classname" "worldspawn"\n}\n{\n"classname" "info_player_start"\n}', grid)
        self.assertTrue(text.startswith('{\n"classname" "worldspawn"\n"_aw_lightgrid" '))
        self.assertEqual(text.count('_aw_lightgrid'), len(il.light_grid_keys(grid)))
        step, dims, origin, values, chunks = parse_grid(text)
        self.assertEqual((step, list(dims), origin, values), (grid[0], grid[1], grid[2], grid[3]))
        self.assertEqual(len(values), dims[0] * dims[1] * dims[2]); self.assertLessEqual(len(values), il.GRID_MAX_CELLS)
        self.assertTrue(all(len(v) <= il.GRID_CHUNK and len(v) % 2 == 0 for v in chunks.values()))
        def at(p):
            i = np.round((np.asarray(p) - origin) / step).astype(int)
            return values[i[0] + dims[0] * (i[1] + dims[1] * i[2])]
        # Jiub's chest is lit by the lantern above him; the floor below is not
        chest = JIUB + [0, 0, 24]
        self.assertGreater(at(chest), at(JIUB + [0, 0, -16]))
        self.assertGreater(at(chest), il.point_light(np.array([0., -150, 0]), {**lighting, 'lights': []}) + 40)
        # no lights and no zones: no grid (the floor light already says it all)
        self.assertIsNone(il.light_grid({'ambient': [80, 80, 80], 'lights': []}, [0, 0, 0], [64, 64, 64]))
        self.assertEqual(il.add_light_grid('{\n}', None), '{\n}')

    def test_engine_and_converter_agree(self):
        src = ROOT / 'engine/aga/src'
        sky = (src / 'aw_sky.h').read_text(encoding='utf-8'); light = (src / 'r_light.c').read_text(encoding='utf-8')
        self.assertIn('#define AW_WARM_STYLE %d' % il.WARM_STYLE, sky)
        self.assertLess(il.WARM_STYLE, int(re.search(r'#define AW_LAMP_STYLE (\d+)', sky).group(1)))
        self.assertIn('#define LIGHT_GRID_CHUNK %d' % (il.GRID_CHUNK // 2), light)
        self.assertIn('#define LIGHT_GRID_KEY "_aw_lightgrid"', light)
        self.assertLess(il.GRID_CHUNK, 1024)  # Quake's entity token (common.c com_token)
        self.assertIn('R_ActorLight (currententity, 1)', (src / 'r_main.c').read_text(encoding='utf-8'))
        self.assertIn('surf->styles[k] == AW_WARM_STYLE', (src / 'r_surf.c').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
