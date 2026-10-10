# SPDX-License-Identifier: GPL-3.0-only
"""Every text writer in src/ and tools/ pins LF line endings and UTF-8.

Path.write_text, open(..., 'w') and NamedTemporaryFile(mode='w') without
newline="\\n" write CRLF on Windows hosts and the host locale encoding unless
told otherwise (the LF-only rule: a CR in a JSON/text output changes its hash).
src/ has none. tools/ is a ratchet: a file may not gain an unpinned writer; the
numbers below only go down (fix a site, lower its count, or delete the entry).
"""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

# Existing unpinned text writers in tools/, by file (MWAD-TEXT-WRITERS-35). Ratchet: lower, never raise.
LEGACY = {
    'tools/analyze_subcell_redundancy.py': 1,
    'tools/apply_source_update.py': 1,
    'tools/arrival_spot.py': 1,
    'tools/asset_progress.py': 2,
    'tools/audit_bsp_node_roles.py': 1,
    'tools/audit_gallery_budgets.py': 1,
    'tools/audit_shoreline.py': 1,
    'tools/audit_vicinity.py': 2,
    'tools/audit_walkability.py': 1,
    'tools/build.py': 3,
    'tools/build_aga.py': 19,
    'tools/build_cache.py': 7,
    'tools/build_costs.py': 1,
    'tools/build_dry_run.py': 4,
    'tools/build_gallery.py': 5,
    'tools/build_night_sky.py': 2,
    'tools/build_opening.py': 5,
    'tools/build_parallel.py': 4,
    'tools/build_profile.py': 2,
    'tools/build_shared_sky_clouds.py': 1,
    'tools/build_summary.py': 2,
    'tools/build_torchtest.py': 3,
    'tools/capture_opening.py': 5,
    'tools/check_geometry_render_inputs.py': 1,
    'tools/check_scene_actors.py': 2,
    'tools/chim/build.py': 1,
    'tools/collision_bsp.py': 1,
    'tools/cull_bsp_terrain.py': 1,
    'tools/dedup_bsp_planes.py': 1,
    'tools/export_world_terrain.py': 1,
    'tools/exterior_sky_build.py': 2,
    'tools/fetch_native.py': 1,
    'tools/fetch_toolchain.py': 1,
    'tools/file_cache.py': 2,
    'tools/fsuae_headless_probe.py': 4,
    'tools/import_town.py': 5,
    'tools/install_town_flora.py': 2,
    'tools/package_dry_run.py': 2,
    'tools/player_hull.py': 1,
    'tools/prepare_area.py': 4,
    'tools/prepare_bounded_world.py': 2,
    'tools/prepare_bsp.py': 2,
    'tools/prepare_census.py': 2,
    'tools/prepare_character.py': 1,
    'tools/prepare_dialogue_lookup.py': 1,
    'tools/prepare_door_audio.py': 2,
    'tools/prepare_doors.py': 5,
    'tools/prepare_gallery.py': 6,
    'tools/prepare_hand_catalog.py': 2,
    'tools/prepare_hand_sprites.py': 1,
    'tools/prepare_hands.py': 2,
    'tools/prepare_harvest.py': 1,
    'tools/prepare_harvest_alias.py': 2,
    'tools/prepare_harvest_room.py': 4,
    'tools/prepare_interior.py': 4,
    'tools/prepare_interior_sections.py': 2,
    'tools/prepare_intro.py': 2,
    'tools/prepare_intro_docks.py': 1,
    'tools/prepare_media_assets.py': 4,
    'tools/prepare_mesh_bsp.py': 2,
    'tools/prepare_music.py': 1,
    'tools/prepare_npcs.py': 2,
    'tools/prepare_opening_refs.py': 1,
    'tools/prepare_original_door_overlay.py': 2,
    'tools/prepare_quake.py': 5,
    'tools/prepare_seyda_regions.py': 2,
    'tools/prepare_shared_sky_assets.py': 3,
    'tools/prepare_town.py': 2,
    'tools/prepare_ui.py': 1,
    'tools/prepare_video.py': 2,
    'tools/prepare_walk.py': 1,
    'tools/prepare_world_flora.py': 9,
    'tools/prepare_world_regions.py': 8,
    'tools/prepare_world_scenery.py': 4,
    'tools/prepare_world_ui.py': 2,
    'tools/prerendered.py': 6,
    'tools/profile_demo.py': 4,
    'tools/project_version.py': 3,
    'tools/rebuild_balmora_region.py': 3,
    'tools/render_world_survey.py': 1,
    'tools/repair_balmora_maps.py': 2,
    'tools/setup_windows.py': 3,
    'tools/share_bsp_geometry.py': 1,
    'tools/sky_palette_overlay.py': 2,
    'tools/stage_gallery.py': 1,
    'tools/stair_walk.py': 2,
    'tools/survey_vvardenfell.py': 1,
    'tools/town_interiors.py': 1,
    'tools/world_asset_coverage.py': 1,
    'tools/world_estimate_sample.py': 4,
    'tools/world_scenery.py': 1,
    'tools/world_volumes.py': 1,
}


def unpinned_writers(path):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else None
        keywords = {k.arg for k in node.keywords}
        if name == 'write_text':
            text_mode = True
        elif name in ('open', 'NamedTemporaryFile', 'TemporaryFile'):
            modes = [a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
            modes += [k.value.value for k in node.keywords
                      if k.arg == 'mode' and isinstance(k.value, ast.Constant) and isinstance(k.value.value, str)]
            mode = next((m for m in modes if m and set(m) <= set('rwxabt+') and any(c in m for c in 'wxa')), None)
            text_mode = mode is not None and 'b' not in mode
        else:
            continue
        if text_mode and not {'newline', 'encoding'} <= keywords:
            found.append(node.lineno)
    return found


class TextWriterTests(unittest.TestCase):
    def scan(self, folder):
        result = {}
        for path in sorted((ROOT / folder).rglob('*.py')):
            lines = unpinned_writers(path)
            if lines:
                result[path.relative_to(ROOT).as_posix()] = lines
        return result

    def test_src_writers_pin_lf_and_utf8(self):
        self.assertEqual(self.scan('src'), {})

    def test_tools_do_not_gain_unpinned_writers(self):
        for name, lines in self.scan('tools').items():
            allowed = LEGACY.get(name, 0)
            self.assertLessEqual(len(lines), allowed,
                                 f'{name}: {len(lines)} text writers without newline="\\n" and encoding="utf-8" '
                                 f'(allowed {allowed}); lines {lines}')

    def test_scanner_finds_the_unpinned_forms(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / 'sample.py'
            sample.write_text(
                "p.write_text('x')\n"                                   # 1 bad
                "p.write_text('x', encoding='utf-8')\n"                 # 2 bad
                "p.write_text('x', encoding='utf-8', newline='\\n')\n"  # ok
                "open(p, 'w')\n"                                        # 4 bad
                "p.open('w', encoding='utf-8', newline='\\n')\n"        # ok
                "open(p, 'wb')\n"                                       # ok (binary)
                "open(p)\n"                                             # ok (read)
                "tempfile.NamedTemporaryFile(mode='w', dir=d)\n",       # 8 bad
                encoding='utf-8', newline='\n')
            self.assertEqual(unpinned_writers(sample), [1, 2, 4, 8])


if __name__ == '__main__':
    unittest.main()
