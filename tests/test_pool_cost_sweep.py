# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-CHIM-REGION-FRAMES-TAIL-43: every caller of the shared worker pools hands its units out largest first, or
says why not.

The CHIM region frames were passed to build_parallel.ordered_map with no cost: the heavy frames late in the list
started last and finished alone on one worker. This sweep reads every call of ordered_map, completed_map,
governed_map and build_costs.costed_map under tools/ and requires one of:

- a cost (cost=...), a cost history (history=... with key=..., or costed_map), or
- a recorded reason in REASONS below, keyed 'file:enclosing function' (the reason says why the order of its units
  does not matter or what already orders them).

A new caller without either fails here: give it a cost or write its reason down."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
POOLS = {'ordered_map', 'completed_map', 'governed_map', 'costed_map'}

FEW = 'a handful of units (one per race, town, room kind or pass): no tail to speak of'
UNIFORM = 'many units of about the same cost (one file, one map stamp or one copy each)'
STREAM = 'a generator read as it comes: the order follows the input, which is already the work order'
SORTED = 'the caller sorts its units largest first before the call'
SMALL = 'the call runs on the units its parent already split evenly (balanced chunks or batches)'
NESTED = 'runs inside a pool worker or a per-unit step on one worker (serial by design)'
GATE = 'a check over the maps of a stage, each unit seconds or less; it finishes within the stage tail anyway'
LATER = ('no cost yet; the units are measured in the build profile and a cost follows when one shows as a tail '
         '(perf guard [underused] lines)')

REASONS = {
    'tools/actor_grounding.py:annotate': GATE,
    'tools/actor_grounding.py:bake_ground': LATER,
    'tools/actor_grounding_census.py:measure': LATER,
    'tools/asset_census.py:scan_meshes': UNIFORM,
    'tools/audit_gallery_budgets.py:main': GATE,
    'tools/build_gallery.py:prefetch_dependencies': UNIFORM,
    'tools/build_gallery.py:collect_models': SMALL,
    'tools/build_gallery.py:parts_models': SMALL,
    'tools/build_gallery.py:seam_gate': SMALL,
    'tools/build_parallel.py:hash_files': UNIFORM,
    'tools/build_parallel.py:hash_existing': UNIFORM,
    'tools/build_parallel.py:copy_files': UNIFORM,
    'tools/build_parallel.py:governed_map': 'the fallback of governed_map itself: it passes its caller\'s cost on',
    'tools/build_costs.py:costed_map': 'the cost history wrapper itself (passes cost=)',
    'tools/cell_numbers.py:stamp_staged_cells': UNIFORM,
    'tools/check_actor_ground.py:audit': GATE,
    'tools/check_world_map_heap.py:inspect_maps': LATER,
    'tools/chim/collision.py:stair_gate': SORTED,
    'tools/chim/heap.py:ring_peak': SORTED,
    'tools/chim/heap.py:_frame_ring': SMALL,
    'tools/chim/ownership.py:binary_failures': SMALL,
    'tools/chim/seyda.py:retain_authored_collision': FEW,
    'tools/chim/units.py:run_units': 'blocks of one frame cut to about the same size (PVS_BLOCKS)',
    'tools/chim/world.py:frame_visibility': ('a generator in largest-first order of the frames\' own size: each '
                                             'layout is made when the pool asks for it (STREAM)'),
    'tools/chim/world.py:frame_rows': ('a generator in largest-first order of the frames\' own size (placements and '
                                       'chunks); each task makes its frame\'s layout and rows on the worker (STREAM)'),
    'tools/chim/zone_sim.py:walk': SORTED,
    'tools/entity_tracker.py:refs_by_map': UNIFORM,
    'tools/exterior_sky_build.py:configure_staged_maps': SORTED,
    'tools/hand_metadata.py:stamp_staged_hands': UNIFORM,
    'tools/harvest_build.py:prepare': LATER,
    'tools/harvest_build.py:geometry_gate': GATE,
    'tools/harvest_build.py:clear_baked': UNIFORM,
    'tools/hull_chain_audit.py:main': GATE,
    'tools/import_town.py:residents': LATER,
    'tools/import_town.py:prepare': LATER,
    'tools/install_world_flora.py:install': UNIFORM,
    'tools/lava_census.py:run': UNIFORM,
    'tools/mesh_methods.py:main': 'a study tool, not a build stage',
    'tools/modular_npc_study.py:census_main': 'a study tool, not a build stage',
    'tools/npc_lod.py:survey': LATER,
    'tools/npc_parts.py:run': LATER,
    'tools/npc_seam_audit.py:audit': GATE,
    'tools/prepare_area.py:populate': LATER,
    'tools/prepare_character.py:prepare': FEW,
    'tools/prepare_combat.py:prepare': FEW,
    'tools/prepare_gallery.py:main': LATER,
    'tools/prepare_guard_torches.py:prepare': FEW,
    'tools/prepare_hand_catalog.py:prepare': FEW,
    'tools/prepare_intro.py:populate_intro_actors': FEW,
    'tools/prepare_media_assets.py:prepare': SORTED,
    'tools/prepare_media_assets.py:stage_catalogue': UNIFORM,
    'tools/prepare_mesh_bsp.py:_append_meshes': LATER,
    'tools/prepare_music.py:prepare_music': FEW,
    'tools/prepare_player_view.py:prepare': FEW,
    'tools/prepare_quake.py:prepare': STREAM,
    'tools/prepare_scenery.py:export_refs': LATER,
    'tools/prepare_seyda_regions.py:convert': 'the recorded Seyda Neen method (retired flag), kept as it was',
    'tools/prepare_seyda_source.py:seed': FEW,
    'tools/prepare_tree_sprites.py:prepare': STREAM,
    'tools/prepare_world_flora.py:budget_order': UNIFORM,
    'tools/prepare_world_flora.py:convert_budget_first': SORTED,
    'tools/prepare_world_regions.py:prepare': 'the skipped regions only, a few; the compiled ones go through costed_map',
    'tools/prepare_world_scenery.py:prepare': LATER,
    'tools/repair_balmora_maps.py:repair': FEW,
    'tools/seam_audit.py:audit': GATE,
    'tools/sky_palette_overlay.py:convert': 'batches cut to about the same size (_batches by sizes)',
    'tools/rock_shell_audit.py:audit': LATER,
    'tools/stage_gallery.py:greetings': UNIFORM,
    'tools/stair_records.py:_chim_part': SORTED,
    'tools/survey_vvardenfell.py:run': UNIFORM,
    'tools/world_estimate_data.py:scan_meshes': UNIFORM,
    'tools/world_estimate_sample.py:convert_frame': 'a study tool, not a build stage',
    'tools/world_volumes.py:write_partitions': FEW,
    'tools/world_volumes.py:verify_combined': FEW,
}


def calls():
    """[(site, has_cost)] of every pool call under tools/: site = 'file:outermost enclosing function'."""
    found = []
    for path in sorted((ROOT / 'tools').rglob('*.py')):
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'))
        except (SyntaxError, UnicodeDecodeError):
            continue
        relative = path.relative_to(ROOT).as_posix()

        def visit(node, outer):
            for child in ast.iter_child_nodes(node):
                name = outer
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and outer is None:
                    name = child.name
                if isinstance(child, ast.Call):
                    f = child.func
                    called = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else None
                    if called in POOLS:
                        words = {k.arg for k in child.keywords}
                        costed = called == 'costed_map' or 'cost' in words or {'history', 'key'} <= words
                        found.append(('%s:%s' % (relative, name or '<module>'), costed))
                visit(child, name)
        visit(tree, None)
    return found


class PoolCostSweep(unittest.TestCase):
    def test_every_pool_caller_has_a_cost_or_a_recorded_reason(self):
        missing = sorted({site for site, costed in calls() if not costed and site not in REASONS})
        self.assertEqual(missing, [], 'pool callers without a cost or a reason (give them cost=, history= with '
                                      'key=, or a line in REASONS): %s' % missing)

    def test_no_stale_reasons(self):
        sites = {site for site, _ in calls()}
        stale = sorted(site for site in REASONS if site not in sites)
        self.assertEqual(stale, [], 'REASONS rows for callers that are gone: %s' % stale)

    def test_the_region_frames_are_costed(self):
        costed = {site for site, has in calls() if has}
        self.assertIn('tools/chim/build.py:prepare_areas_parallel', costed)
        self.assertIn('tools/chim/frame_map.py:build_regions', costed)


if __name__ == '__main__':
    unittest.main()
