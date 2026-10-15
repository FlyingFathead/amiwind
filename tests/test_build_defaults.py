# SPDX-License-Identifier: GPL-3.0-only
"""A default build makes everything the last release ships (BUILD-FLORA-OPTIN-32).

Trees and grass shipped in every release since v0.0.28 but stayed behind the
opt-in --tree-sprites, and the measured Balmora layout repair rode on the same
option, so a from-scratch build without it stopped at the image step. These
tests fail when a shipped feature becomes opt-in again or leaves the default
command list, and when a builder option is added without being classified
against what a release ships.
"""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]

import build  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests/ (env_guard) when run as a file
import env_guard  # noqa: E402

TOOLS = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
RUN = Path('/private/run')

# Every stage of a default AGA build and what of the v0.0.31 payload it makes.
SHIPPED_STAGES = {
    'setup': 'terrain workspace', 'terrain': 'terrain packets',
    'cell-progress': 'CHIM Progress Tracker data (toolkit/cell-progress.json; BUILD-CHIM-KEY-UNDERDECLARED-35)',
    'scenery': 'Seyda Neen scenery', 'scene': 'alias scene', 'bsp': 'Seyda Neen mesh maps',
    'npcs': 'NPC models and voices', 'hands': 'Nord first-person hands (v_nord, hands.aws)',
    'hand-catalog': 'per-race hands (progs/hands, hand-models.awh, hand-torch.awt)',
    'harvest': 'harvestable mushrooms (harvest-*.txt, progs/harvest/*.mdl)',
    'interior': 'interiors', 'dialogue-lookup': 'voice lookup', 'intro': 'opening, chargen captions',
    'census': 'census map', 'npc-gallery': 'gallery/*.mdl (7,102 files)',
    'area': 'area interiors', 'balmora-interiors': 'Balmora interiors',
    # CHIM-native areas by default (BUILD-LEGACY-CHAIN-DEFAULT-36): Balmora prepared CHIM-native, no legacy region maps (bm*).
    'chim-town-balmora': 'Balmora residents, frame entities, region table and door bank from the game data',
    # all of Vivec in one CHIM frame, CHIM-native (owner decision 2026-10-11 09:55; replaces the Arena-only frame)
    'chim-town-vivec_city': 'Vivec residents, frame entities, region table and door bank from the game data',
    # v0.0.36-dev5: Seyda Neen CHIM-native (no legacy region maps; BUILD-LEGACY-TOWN-MAPS-SHIPPED-36)
    'chim-town-seyda': 'Seyda Neen frame and opening-scene entities, activated objects and region table from the town',
    # The Arena's listed rooms (the Pit, vai000; shipped in v0.0.35 through the legacy chain): their own CHIM-native stage
    # (tools/chim_rooms.py, BUILD-MINIWIND-ARENA-PIT-REFUSED-36).
    'chim-rooms-vivec_city': 'the 130 Vivec rooms (the Arena Pit vai000 among them), their residents and linked door banks',
    'door-audio': 'door-sounds.txt', 'character': 'character/*.awh', 'reading': 'reading/*',
    'opening-references': 'opening references', 'world-survey': 'world/regions.awr, map.awm',
    'world-ui': 'world/journal.awj, quests.awq', 'actor-contact': 'actor ground gate',
    'world-terrain': 'world maps (vf*)', 'world-scenery-assets': 'rocks and giant mushrooms',
    'seam-audit': 'seam-tear gate over reduced meshes (seam-audit.json)',
    'world-scenery': 'rock and mushroom overlay',
    'world-flora-assets': 'progs/aw_flora/*.spr (76 files)', 'world-flora': 'trees and grass overlay',
    'media': 'media/catalogue.json, sound/*', 'music': 'music/*.mws', 'engine': 'AmiWind, AmiWindCheck',
    'image': 'the HDF images',
    # v0.0.33, the first CHIM release: Balmora and Seyda Neen as a CHIM world (config/build-defaults.json).
    'chim': 'CHIM world (chim/world.cwi, frame maps of Balmora and Seyda Neen)',
    # Towns after Seyda Neen and Balmora that the release ships (BUILD-EXTRA-TOWN-OPTIN-32).
    # The Vivec Arena preview (town-vivec_arena, v0.0.32) is withdrawn from v0.0.33 (WithdrawnTowns below).
}

# Image options a default build must pass, with the value v0.0.31 shipped.
SHIPPED_IMAGE_OPTIONS = {
    '--world-flora': str(RUN / 'world-flora'),
    '--town-flora-source-index': str(RUN / 'scenery/scenery-index.json'),
    '--town-flora-scene-report': str(RUN / 'alias-scene/scene-report.json'),
    '--gallery': str(RUN / 'npc-gallery'),
    '--hands': '3d',
    '--hand-catalog': str(RUN / 'hand-catalog'),
    '--harvest': str(RUN / 'harvest'),
    '--hidden-surface-cull': 'true',
    '--local-skybox': 'false',
    '--canonical-land-source': str(RUN / 'world-survey/terrain-source.npz'),
    '--town-scenery': str(RUN / 'scenery'),
}

# Every builder option, classified against what a release ships. A new option
# fails test_every_option_is_classified until it is added here.
OPTIONS = {
    # Shipped content: on by default; the only way out is a DEBUGGING ONLY opt-out.
    'no_npc_gallery': 'debug opt-out', 'no_tree_sprites': 'debug opt-out', 'no_harvest': 'debug opt-out',
    'no_extra_town': 'debug opt-out', 'no_cell_progress': 'debug opt-out', 'only_core_towns': 'debug opt-out',
    # Quick test builds: --exclude GROUP and its --exclude-* aliases (tools/build_exclusions.py, -devN only).
    'exclude': 'debug opt-out', 'exclude_unreferenced': 'debug opt-out', 'with_video': 'mode',
    # Quick test builds that start straight in the game (tools/direct_start.py) and MiniWind test spots.
    'direct_to_game_map': 'mode', 'quick_character': 'mode', 'miniwind_preset': 'mode', 'skip_census': 'mode',
    'tree_sprites': 'no-op alias',
    # Defaults that match what v0.0.31 shipped.
    'hands': 'shipped default', 'vis_mode': 'shipped default', 'npc_anim': 'shipped default', 'hidden_surface_cull': 'shipped default',
    'local_skybox': 'shipped default', 'map_budget_policy': 'shipped default',
    'texinfo_snap': 'shipped default', 'scenery_reduce': 'shipped default',
    'scenery_reduce_texels': 'shipped default', 'bitmap_paper_ink': 'shipped default',
    'build_config': 'shipped default', 'builder': 'shipped default', 'npc_root_rule': 'shipped default',
    # v0.0.33: --builder chim with CHIM areas Balmora and Seyda Neen (config/build-defaults.json).
    'chim_areas': 'shipped default',
    # CHIM texture effects (.chimfx, e.g. autumn_glitter_leaves): an opt-in look, none by default.
    'chim_texture_effects': 'opt-in, not shipped',
    # CHIM lighting type (config/build-defaults.json: hybrid, owner decision 2026-10-09; lamps = the v0.0.33 lighting,
    # none, and reserved types refused; tests/test_chim_light_types.py).
    'chim_lighting_type': 'shipped default',
    # Morrowind's stair/slope collision rules (config/build-defaults.json, true); --no-... is the debug way out.
    'follow_original_stair_rules': 'shipped default',
    # standing hulls as chains in v0.0.33 (config/build-defaults.json, chain: BUILD-ROUTED-FLORA-RESERVE-33);
    # --model-hull auto routes large models (selectable, tested)
    'model_hull': 'shipped default',
    # CHIM frame maps tag statics to stream with their chunks (the engine reads the tags); --no-... is the debug way out
    'chim_stream_statics': 'shipped default',
    # CHIM frame maps as maps/<name>.chim (tools/map_files.py, default chim); --chim-frame-ext bsp keeps the earlier names
    'chim_frame_ext': 'shipped default',
    'chim_region_rows': 'shipped default',
    # Lava pools as Quake liquid (config/build-defaults.json, quake; docs/LAVA.md); --lava static keeps the earlier rule
    'lava': 'shipped default',
    # In-game world map v2 with the lava pools (config/build-defaults.json, v2); --world-map v1 keeps the earlier map
    'world_map': 'shipped default',
    # World bounds (tools/world_bounds.py, docs/WORLD_BOUNDS.md): on by default, the image step gets --world-bounds;
    # --world-bounds off writes nothing (the game as before; tests/test_world_bounds.py)
    'world_bounds': 'shipped default',
    # The player's view (tools/prepare_player_view.py, docs/THIRD_PERSON.md): the bodies and the quick retry are on
    # by default (nothing added to the image step); off adds --no-player-body / --no-death-retry
    'player_body': 'shipped default',
    'death_retry': 'shipped default',
    # NPC heads (config/build-defaults.json auto = budget, the previous bake: NPC-HEAD-DECIMATION-33);
    # --npc-head-detail original is EXPERIMENTAL (docs/EXPERIMENTAL_FLAGS.md)
    'npc_head_detail': 'shipped default',
    # The game heap: the engine's 11 MiB unless --heap-mb / heap_mb asks otherwise (used as asked, warned above
    # the measured safe size; tests/test_heap_size.py).
    'heap_mb': 'shipped default',
    # Engine profile (docs/ENGINE_PROFILES.md, tests/test_engine_profile.py): c is what ships and adds nothing to the
    # engine command; upstream and the --engine-asm / --engine-opt overrides are EXPERIMENTAL.
    'engine_profile': 'shipped default', 'engine_asm': 'opt-in, not shipped', 'engine_opt': 'opt-in, not shipped',
    # NPC model levels of detail (docs/NPC_MODEL_CACHE.md; tests/test_npc_lod.py): on, 3 levels, the face
    # LOD policy and the level-file disk budget; --npc-lod off is the earlier single model (kept).
    'npc_lod': 'shipped default', 'npc_lod_levels': 'shipped default', 'npc_face_lod': 'shipped default',
    'npc_face_lod_list': 'input', 'npc_lod_disk_mib': 'shipped default',
    # Opt-in content no release ships (owner decisions, private inputs or experiments).
    # --extra-town adds towns not shipped yet; shipped towns are built by default.
    'extra_town': 'opt-in, not shipped', 'intro_captions': 'opt-in, not shipped',
    'amiga_libs': 'opt-in, not shipped', 'shared_sky_source': 'opt-in, not shipped',
    # Benchmark/diagnostic images: live diagnostic logs (BOOT-VOLUME-NOT-VALIDATED-33).
    'live_logs': 'opt-in, not shipped', 'live_tracker': 'opt-in, not shipped', 'tracker_declined': 'opt-in, not shipped',
    'keep_tracker': 'opt-in, not shipped',
    'allow_known_actor_ground_findings': 'private test waiver', 'accept_known_stair_findings': 'private test waiver',
    # The AmiWind "MiniWind" Playtester Build: a private -devN partial-area build type (tools/miniwind.py).
    'miniwind': 'opt-in, not shipped', 'miniwind_description': 'opt-in, not shipped',
    'miniwind_scope': 'opt-in, not shipped',
    'miniwind_town': 'opt-in, not shipped', 'miniwind_debug': 'opt-in, not shipped',
    'miniwind_map_inspection': 'opt-in, not shipped',
    'chim_detail_budget': 'opt-in, not shipped', 'chim_cut_models_over': 'opt-in, not shipped',
    # EXPERIMENTAL engine compile switches (docs/EXPERIMENTAL_FLAGS.md; widecoord: CHIM-FRAME-COORD-RANGE-33)
    'engine_experiment': 'opt-in, not shipped',
    # how the engine sends positions: wide by default since v0.0.36 (tools/coord_range.py)
    'coord_range': 'shipped default',
    'chim_draw_distance': 'opt-in, not shipped', 'chim_terrain_shoreline': 'shipped default',
    # the compiled terrain hull and terrain references: defaults from v0.0.36 (owner decision 2026-10-11)
    'chim_terrain_hull': 'shipped default', 'chim_terrain_refs': 'shipped default',
    'chim_model_hull_patch': 'shipped default',
    # how a CHIM model variant shares its vertices (base by default; placed = the earlier per-placement weld)
    'chim_model_weld': 'shipped default',
    # how CHIM meshes become faces (table by default: config/mesh-methods.json)
    'chim_mesh_method': 'shipped default',
    'stair_walk_cache': 'check', 'stair_walk_sample': 'check',
    # Entity tracker against the release baseline (BUILD-DRESSING-EXCLUDED-32).
    'no_entity_baseline': 'debug opt-out', 'accept_entity_loss': 'check',
    'skip_dressing': 'debug opt-out',
    # Optional recorded input (BUILD-SEYDA-REGEN-30, not needed from v0.0.34): the owner's own recorded
    # v0.0.31 Seyda Neen maps, kept byte for byte (tests/test_recorded_stage.py).
    'seyda_recorded': 'recorded-stage exception input',
    # Inputs, tools, modes and checks: no shipped content of their own.
    'help': 'tooling', 'data_files': 'input', 'workspace': 'tooling', 'stage': 'mode', 'check': 'mode',
    'plan': 'mode', 'install_dependencies': 'mode', 'autoinstall': 'mode', 'yes': 'mode',
    'install_sdk': 'mode', 'tools_dir': 'tooling', 'versions': 'mode', 'host_plan': 'mode',
    'fallback_font': 'input', 'palette': 'input', 'check_inputs': 'mode', 'layout_selftest': 'mode', 'dry_run': 'mode',
    'recover_image_from': 'mode',
    'autorun_fs_uae': 'mode', 'kickstart_file': 'input', 'amiga_libs_policy': 'check',
    'game_data_policy': 'check', 'check_hashes': 'check', 'allow_data_differences': 'check',
    'name': 'tooling', 'sdk': 'tooling', 'vasm': 'tooling', 'upstream_archive': 'check',
    'quake_tools': 'tooling', 'qcc': 'tooling', 'ffmpeg': 'tooling', 'xdftool': 'tooling',
    'rdbtool': 'tooling', 'gallery_cache': 'tooling', 'gallery_seed_run': 'tooling',
    'estimate_world': 'mode', 'estimate_sample': 'mode', 'jobs': 'tooling', 'serial_stages': 'tooling',
    # Build profile and development stage reuse (docs/BUILD_PROFILE.md): outputs unchanged.
    'no_profile': 'tooling', 'perf_guard': 'tooling', 'perf_guard_baselines': 'tooling', 'log_level': 'tooling', 'quiet': 'tooling', 'reuse_from': 'tooling', 'reuse_mode': 'tooling', 'rebuild_stage': 'tooling',
    'accept_rebuild': 'tooling', 'any_run_name': 'tooling', 'source_commit': 'tooling',
    'developer_mode': 'tooling', 'working_version': 'tooling', 'accept_version_mismatch': 'tooling',
    # Build recipes (tools/build_recipe.py, docs/BUILD_RECIPES.md): where the options come from and where they go.
    'recipe': 'tooling', 'save_recipe': 'tooling', 'recipe_inputs': 'tooling',
    'rebuild_unit': 'tooling',
    'allow_release_reuse': 'check',
    'fingerprint_scope': 'tooling', 'no_unit_cache': 'debug opt-out', 'no_media_cache': 'debug opt-out',
    'prerendered': 'tooling', 'prerendered_stages': 'tooling', 'storage_pool': 'tooling', 'anim_kit': 'shipped default', 'miniwind_boot': 'mode',
    # CHIM-native towns (CHIM-LEGACY-CHAIN-33): on by default since v0.0.36 (CHIM-native areas); 'off' and --legacy-area
    # are RETIRED since CHIM v0.1.0 (tools/retired_flags.py, BUILD-LEGACY-CHAIN-DEFAULT-36); --override lets one through.
    'chim_native_towns': 'shipped default', 'chim_regions': 'opt-in, not shipped', 'chim_regions_status': 'opt-in, not shipped',
    'legacy_areas': 'retired', 'override': 'tooling',
    # Night-lamp lightmaps (bm019 prototype, tools/lamp_lightmaps.py): EXPERIMENTAL, off by default
    'night_lamp_lightmaps': 'mode',
    # Modular NPCs (docs/MODULAR_NPCS.md): EXPERIMENTAL, whole by default
    'npc_models': 'mode', 'npc_parts_face_cap': 'tooling', 'npc_parts_policy': 'tooling', 'parts_cache': 'tooling', 'storage_pool_dir': 'tooling', 'stair_walk': 'check',
}


def steps(*extra):
    args = build.parser().parse_args(list(extra))
    args.data_files = Path('/owned/Data Files')
    args.sdk = Path('/sdk')
    # Automatic --jobs follows live free memory, so two plans could differ by
    # one worker; pin it so the comparisons see only the options under test.
    with patch('build_jobs.auto_jobs', return_value=4):
        return build.commands(args, TOOLS, RUN)


def legacy_steps(*extra):
    """The legacy builder's plan: extra towns go through import_town (a CHIM-native plan imports only
    towns on CHIM; the others never ship in a CHIM image, chim.frame_map.remove_towns_not_on_chim)."""
    return steps('--builder', 'legacy', *extra)


def option(command, flag):
    return command[command.index(flag) + 1] if flag in command else None


class DefaultBuildShipsTheRelease(unittest.TestCase):
    def test_default_build_runs_every_shipped_stage(self):
        names = [name for name, _ in steps()]
        self.assertEqual(sorted(names), sorted(SHIPPED_STAGES))
        self.assertEqual(len(names), len(set(names)))
        self.assertLess(names.index('world-flora'), names.index('image'))

    def test_default_image_gets_every_shipped_input(self):
        image = dict(steps())['image']
        for flag, value in SHIPPED_IMAGE_OPTIONS.items():
            with self.subTest(flag=flag):
                self.assertEqual(image.count(flag), 1)
                self.assertEqual(Path(option(image, flag)) if '/' in value else option(image, flag),
                                 Path(value) if '/' in value else value)
        # Defaults that v0.0.31 shipped with: no waiver, fast vis, no mesh reduction.
        self.assertEqual(option(image, '--map-budget-policy'), 'strict')
        for flag in ('--no-npc-gallery', '--vis-mode', '--allow-known-actor-ground-findings', '--intro-captions'):
            self.assertNotIn(flag, image)

    def test_night_lamp_lightmaps_are_off_by_default(self):
        # EXPERIMENTAL bm019 prototype (docs/EXPERIMENTAL_FLAGS.md): the default image is unchanged.
        self.assertNotIn('--night-lamp-lightmaps', dict(steps())['image'])
        self.assertIn('--night-lamp-lightmaps', dict(steps('--night-lamp-lightmaps', 'on'))['image'])

    def test_world_flora_is_the_default_and_tree_sprites_is_a_no_op(self):
        self.assertEqual(steps('--tree-sprites'), steps())
        commands = dict(steps())
        self.assertNotIn('--census', commands['world-flora-assets'])
        self.assertEqual(Path(option(commands['world-flora'], '--out')), RUN / 'world-flora')

    def test_no_tree_sprites_omits_only_flora(self):
        default, debug = dict(steps()), dict(steps('--no-tree-sprites'))
        self.assertEqual(set(default) - set(debug), {'world-flora-assets', 'world-flora'})
        for flag in ('--world-flora', '--town-flora-source-index', '--town-flora-scene-report'):
            self.assertNotIn(flag, debug['image'])
        # The Balmora layout repair no longer depends on flora; a CHIM-native image has no Balmora region maps.
        self.assertNotIn('--balmora-cache', debug['image'])
        self.assertEqual(Path(option(debug['image'], '--chim-town')), RUN / 'chim-town-balmora')

    def test_opt_outs_are_debugging_only(self):
        for action in build.parser()._actions:
            if OPTIONS.get(action.dest) == 'retired':
                continue  # RetiredFlags below: help starts with RETIRED
            if action.dest.startswith('no_') or OPTIONS.get(action.dest) == 'debug opt-out':
                with self.subTest(option=action.option_strings[0]):
                    self.assertFalse(action.default)
                    self.assertTrue(action.help.startswith('DEBUGGING ONLY'))

    def test_every_option_is_classified(self):
        dests = {action.dest for action in build.parser()._actions}
        self.assertEqual(sorted(dests - set(OPTIONS)), [], 'classify new builder options in OPTIONS')
        self.assertEqual(sorted(set(OPTIONS) - dests), [], 'remove stale OPTIONS rows')
        for action in build.parser()._actions:
            kind = OPTIONS[action.dest]
            if kind == 'opt-in, not shipped':
                self.assertIn(action.default, (None, [], False), action.dest)

    def test_engine_defaults_match_the_release(self):
        import argparse
        import build_aga
        captured = {}
        original = argparse.ArgumentParser.parse_args

        class Parsed(Exception):
            pass

        def capture(parser, args=None, namespace=None):
            captured['args'] = original(parser, ['engine', '--out', '/o', '--sdk', '/sdk'], namespace)
            raise Parsed

        with patch.object(argparse.ArgumentParser, 'parse_args', capture), self.assertRaises(Parsed):
            build_aga.main()
        engine_args = captured['args']
        # Shipped engine: 68040, brightness controls (dbg luma), 3D hands.
        self.assertEqual(engine_args.cpu, '68040')
        self.assertTrue(engine_args.debug_luma)
        self.assertEqual(engine_args.hands, '3d')
        # Engine profile c: the C paths at -O1 (docs/ENGINE_PROFILES.md); upstream stays experimental.
        self.assertEqual(engine_args.engine_profile, 'c')
        self.assertIsNone(engine_args.engine_asm)
        self.assertIsNone(engine_args.engine_opt)
        engine = dict(steps())['engine']
        for flag in ('--cpu', '--disallow-luma-controls', '--no-luma-controls', '--allow-compiler-warnings',
                     '--engine-profile', '--engine-asm', '--engine-opt', '--check-profiles'):
            self.assertNotIn(flag, engine)


def arena_shipped():
    """The town table with the Vivec Arena shipped again (its "withdrawn" field dropped):
    the shipped-town mechanism stays tested while v0.0.33 leaves the Arena out."""
    import town_config
    real = town_config.load_registry

    def load(root=None):
        registry = real(root)
        for row in registry['towns']:
            if row['id'] == 'vivec_arena':
                row.pop('withdrawn', None)
        return registry
    return patch.object(town_config, 'load_registry', load)


class WithdrawnTowns(unittest.TestCase):
    """v0.0.33 leaves the Vivec Arena out by owner decision (CHIM-ARENA-MEMORY-33): as data
    ("withdrawn" on its town row), not a deletion; --extra-town still builds it."""

    def test_the_arena_is_withdrawn_from_legacy_and_ships_on_chim(self):
        # withdrawn from legacy images in v0.0.33 (CHIM-ARENA-MEMORY-33); from v0.0.36 a default CHIM area,
        # CHIM-native (owner decision 2026-10-11, Vivec stage A): the CHIM plan converts it, the legacy plan does not
        from town_config import extra_towns, registry_row, shipped_extra_towns, withdrawn_towns
        self.assertEqual(shipped_extra_towns(), [])
        self.assertEqual(withdrawn_towns(), ['vivec_arena'])
        self.assertIn('CHIM-ARENA-MEMORY-33', registry_row('vivec_arena')['withdrawn'])
        self.assertEqual(registry_row('vivec_arena')['shipped_since'], 'v0.0.32')
        self.assertIn('vivec_arena', extra_towns())
        self.assertNotIn('town-vivec_arena', dict(legacy_steps()))
        self.assertIn('town-vivec_arena', dict(legacy_steps('--extra-town', 'vivec_arena')))
        # CHIM-native areas: Vivec (one frame, vivec_city) is a default CHIM area; no legacy town import in a CHIM image;
        # the Arena-only frame is a retired legacy area (tools/retired_flags.py vivec-districts)
        self.assertIn('chim-town-vivec_city', dict(steps()))
        self.assertNotIn('chim-town-vivec_arena', dict(steps()))
        self.assertNotIn('town-vivec_arena', dict(steps()))
        self.assertNotIn('town-vivec_arena', dict(steps('--extra-town', 'vivec_arena')))
        self.assertEqual({name for name in SHIPPED_STAGES if name.startswith('town-')}, set())

    def test_withdrawn_needs_a_reason(self):
        import json
        import shutil
        from town_config import runtime_towns, shipped_extra_towns
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'config'
            shutil.copytree(ROOT / 'config', config)
            original = json.loads((config / 'towns.json').read_text(encoding='utf-8'))
            ids = [row['id'] for row in original['towns']]
            for town, value in (('vivec_arena', ''), ('vivec_arena', '  '), ('vivec_arena', 1),
                                ('balmora', 'a reason')):
                data = json.loads(json.dumps(original))
                data['towns'][ids.index(town)]['withdrawn'] = value
                (config / 'towns.json').write_text(json.dumps(data), encoding='utf-8')
                with self.subTest(town=town, value=value):
                    with self.assertRaises(ValueError):
                        runtime_towns(tmp)
                    if town != 'balmora':
                        with self.assertRaises(ValueError):
                            shipped_extra_towns(tmp)


@env_guard.isolated  # build.main exports AMIWIND_* switches (TEST-ENV-LEAK-HULL-33)
class ShippedTowns(unittest.TestCase):
    """Towns the release ships are built by default (BUILD-EXTRA-TOWN-OPTIN-32).

    The Vivec Arena preview ships in v0.0.32 but was built only with the opt-in
    --extra-town vivec_arena, so a default build lacked 19 files of the payload.
    v0.0.33 withdraws the Arena; these tests run with it shipped again (arena_shipped).
    """

    def setUp(self):
        shipped = arena_shipped()
        shipped.start()
        self.addCleanup(shipped.stop)

    def test_the_town_table_ships_the_arena(self):
        from town_config import shipped_extra_towns
        self.assertEqual(shipped_extra_towns(), ['vivec_arena'])

    def test_default_build_imports_every_shipped_town(self):
        from build_parallel import stage_dependencies
        default = legacy_steps()
        names = [name for name, _ in default]
        self.assertEqual(names.index('town-vivec_arena'), names.index('balmora-interiors') + 1)
        command = dict(default)['town-vivec_arena']
        self.assertEqual(Path(command[1]).name, 'import_town.py')
        self.assertEqual(option(command, '--town'), 'vivec_arena')
        self.assertEqual(Path(option(command, '--out')), RUN / 'vivec_arena-work')
        self.assertEqual(stage_dependencies(default)['door-audio'], ('town-vivec_arena',))
        self.assertEqual(build.town_selection(build.parser().parse_args([]))['status'],
                         'vivec_arena (shipped by default)')

    def test_extra_town_of_a_shipped_town_is_a_no_op(self):
        self.assertEqual(legacy_steps('--extra-town', 'vivec_arena'), legacy_steps())

    def test_debug_opt_outs_remove_only_the_town(self):
        default = dict(legacy_steps())
        for extra in (('--no-extra-town', 'vivec_arena'), ('--only-core-towns',)):
            with self.subTest(option=extra[0]):
                debug = dict(legacy_steps(*extra))
                self.assertEqual(set(default) - set(debug), {'town-vivec_arena'})
                self.assertEqual(set(debug) - set(default), set())
                self.assertEqual(debug['image'], default['image'])
        selection = build.town_selection(build.parser().parse_args(['--only-core-towns']))
        self.assertEqual((selection['towns'], selection['left_out']), ([], ['vivec_arena']))
        self.assertIn('left out for debugging: vivec_arena (--only-core-towns)', selection['status'])

    def test_towns_not_shipped_stay_opt_in(self):
        names = [name for name, _ in legacy_steps('--extra-town', 'vivec_foreign')]
        start = names.index('balmora-interiors') + 1
        self.assertEqual(names[start:start + 2], ['town-vivec_arena', 'town-vivec_foreign'])
        self.assertNotIn('town-vivec_foreign', dict(legacy_steps()))
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            build.parser().parse_args(['--no-extra-town', 'vivec_foreign'])  # only shipped towns can be left out

    def test_contradictory_town_options_stop_the_build(self):
        for extra in (['--extra-town', 'vivec_arena', '--no-extra-town', 'vivec_arena'],
                      ['--only-core-towns', '--extra-town', 'vivec_foreign'],
                      ['--only-core-towns', '--no-extra-town', 'vivec_arena']):
            with self.subTest(extra=extra):
                with self.assertRaises(ValueError):
                    build.town_selection(build.parser().parse_args(extra))
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as stop:
                        build.main([*extra, '--host-plan'])
                self.assertEqual(stop.exception.code, 1)

    def test_asset_free_and_terrain_builds_import_no_town(self):
        for extra, status in ((['--dry-run'], 'asset-free'),
                              (['--stage', 'terrain'], 'not applicable (terrain stage)'),
                              (['--recover-image-from', '/old'], 'not part of the rc3 image recovery')):
            with self.subTest(extra=extra):
                selection = build.town_selection(build.parser().parse_args(extra))
                self.assertEqual((selection['towns'], selection['status']), ([], status))

    def test_receipt_and_summary_record_the_towns(self):
        args = build.parser().parse_args(['--dry-run'])
        args.font_options = {'synthetic': True}
        record = build.provenance(args, {})
        self.assertEqual(record['extra_towns'], [])
        self.assertEqual(record['extra_town_selection']['status'], 'asset-free')
        from build_summary import BuildSummary
        with tempfile.TemporaryDirectory() as tmp:
            summary = BuildSummary(Path(tmp), '0', 'test')
            summary.record_environment({'extra_town_selection': build.town_selection(build.parser().parse_args([]))})
            self.assertEqual(summary.environment['extra_towns'], 'vivec_arena (shipped by default)')

    def test_town_table_validates_shipped_since(self):
        import json
        import shutil
        from town_config import load_registry, runtime_towns, shipped_extra_towns
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'config'
            shutil.copytree(ROOT / 'config', config)
            original = json.loads((config / 'towns.json').read_text(encoding='utf-8'))
            ids = [row['id'] for row in original['towns']]
            blocked = next(i for i, row in enumerate(original['towns']) if row.get('blocked'))
            for index, value in ((ids.index('vivec_arena'), '0.0.32'), (ids.index('vivec_arena'), 32),
                                 (ids.index('balmora'), 'v0.0.32'), (blocked, 'v0.0.32')):
                data = json.loads(json.dumps(original))
                data['towns'][index]['shipped_since'] = value
                (config / 'towns.json').write_text(json.dumps(data), encoding='utf-8')
                with self.subTest(town=ids[index], value=value):
                    with self.assertRaises(ValueError):
                        runtime_towns(tmp)
                    with self.assertRaises(ValueError):
                        shipped_extra_towns(tmp) if index != ids.index('balmora') else shipped_since_of(data, index)
            data = json.loads(json.dumps(original))
            data['towns'][ids.index('vivec_foreign')]['shipped_since'] = 'v0.0.33'
            (config / 'towns.json').write_text(json.dumps(data), encoding='utf-8')
            self.assertEqual(shipped_extra_towns(tmp), ['vivec_arena', 'vivec_foreign'])
            self.assertEqual(len(load_registry(tmp)['towns']), len(ids))


def shipped_since_of(data, index):
    from town_config import shipped_since
    return shipped_since(data['towns'][index])


@env_guard.isolated  # build.main exports AMIWIND_* switches (TEST-ENV-LEAK-HULL-33)
class FloraModes(unittest.TestCase):
    def status(self, *extra):
        args = build.parser().parse_args(list(extra))
        return build.world_flora_status(args)

    def test_status_per_mode(self):
        self.assertEqual(self.status(), (True, 'enabled'))
        self.assertEqual(self.status('--tree-sprites'), (True, 'enabled'))
        self.assertEqual(self.status('--no-tree-sprites'), (False, 'disabled by --no-tree-sprites'))
        self.assertEqual(self.status('--dry-run'), (False, 'asset-free'))
        self.assertEqual(self.status('--stage', 'terrain'), (False, 'not applicable (terrain stage)'))
        self.assertFalse(self.status('--recover-image-from', '/old')[0])

    def test_terrain_and_dry_run_recipes_stay_flora_free(self):
        terrain = build.parser().parse_args(['--stage', 'terrain'])
        terrain.data_files = Path('/owned')
        self.assertEqual([name for name, _ in build.commands(terrain, {}, RUN)], ['setup', 'terrain'])
        dry = build.parser().parse_args(['--dry-run'])
        dry.sdk = Path('/sdk')
        self.assertEqual([name for name, _ in build.dry_run_commands(dry, RUN)], ['engine', 'dry-run-image'])

    def test_contradictory_flags_and_warnings(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as stop:
                build.main(['--tree-sprites', '--no-tree-sprites', '--host-plan'])
        self.assertEqual(stop.exception.code, 1)
        self.assertIn('WARNING: --no-tree-sprites is for debugging builds only', out.getvalue())

    def test_receipt_records_flora(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = build.parser().parse_args(['--dry-run'])
            args.font_options = {'synthetic': True}
            with patch.object(build, 'ROOT', Path(tmp)):
                self.assertEqual(build.provenance(args, {})['world_flora'],
                                 {'requested': False, 'status': 'asset-free', 'policy_sha256': None})
            args.dry_run = False
            args.data_files = Path(tmp)
            (Path(tmp) / 'config').mkdir()
            (Path(tmp) / 'config/world-flora.json').write_bytes((ROOT / 'config/world-flora.json').read_bytes())
            with patch.object(build, 'ROOT', Path(tmp)), patch.object(build, 'input_hashes', return_value={}):
                record = build.provenance(args, {})['world_flora']
            self.assertEqual((record['requested'], record['status']), (True, 'enabled'))
            self.assertEqual(record['policy_sha256'], build.sha256(ROOT / 'config/world-flora.json'))
        from build_summary import BuildSummary
        with tempfile.TemporaryDirectory() as tmp:
            summary = BuildSummary(Path(tmp), '0', 'test')
            summary.record_environment({'world_flora': record})
            self.assertEqual(summary.environment['world_flora'], 'enabled')


class FloraErrorNamesTheCause(unittest.TestCase):
    def test_missing_flora_sprites_name_world_flora(self):
        from sprite_heap import inspect_sprites
        entity = b'{"classname" "aw_flora" "aw_scale" "1" "model" "progs/aw_flora/f_0123456789abcdef.spr"}\n'
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, r'World flora was not built.*--no-tree-sprites') as caught:
                inspect_sprites(entity, Path(tmp), {})
        self.assertIn('progs/aw_flora/f_0123456789abcdef.spr', str(caught.exception))
        # Other missing sprites keep the general message.
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'Missing/unsafe sprite asset'):
                inspect_sprites(b'{"classname" "aw_static" "model" "progs/m001.spr"}\n', Path(tmp), {})


if __name__ == '__main__':
    unittest.main()
