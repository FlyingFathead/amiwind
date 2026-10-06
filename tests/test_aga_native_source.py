"""Compile real patched engine routines with synthetic geometry on the host.

Uses engine/aga from this repository by default. AMIWIND_RUNTIME_SOURCE can
select another tree for an explicit comparison.
No proprietary data or Amiga SDK is needed for these collision/culling checks.
"""
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = os.environ.get('AMIWIND_RUNTIME_SOURCE', str(ROOT / 'engine/aga'))

class GuardTorchRenderContractTests(unittest.TestCase):
    def test_world_flames_share_camera_depth_and_precede_hands_and_water_warp(self):
        renderer=(Path(SOURCE)/'src/r_main.c').read_text()
        start=renderer.index('AW_FogDraw();')
        self.assertLess(start,renderer.index('AW_GuardTorchDraw();',start))
        self.assertLess(renderer.index('AW_GuardTorchDraw();',start),renderer.index('R_DrawViewModel();',start))
        self.assertLess(renderer.index('R_DrawViewModel();',start),renderer.index('D_WarpScreen ();',start))
        self.assertNotIn('AW_GuardTorchDraw();',(Path(SOURCE)/'src/aw_torch.c').read_text())
        self.assertNotIn('AW_GuardTorchDraw();',(Path(SOURCE)/'src/view.c').read_text())
        entity_start=renderer.index('void R_DrawEntitiesOnList')
        self.assertLess(renderer.index('AW_GuardTorchEntity(',entity_start),renderer.index('R_AliasCheckBBox',entity_start))

@unittest.skipIf(os.name == 'nt', 'native helper fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'install a host C compiler')
class NativeSourceTests(unittest.TestCase):
    def test_harvest_original_loot_transaction_capacity_and_save_persistence(self):
        self.compile_run('aga_harvest_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_harvest.c', 'aw_state.c', 'aw_save_codec.c')],
            cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all'])

    def test_harvest_exact_brush_binding_occlusion_hide_and_crossings(self):
        self.compile_run('aga_harvest_runtime_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_harvest.c', 'aw_harvest_runtime.c', 'aw_state.c', 'mathlib.c')],
            cflags=['-fsanitize=undefined,float-cast-overflow', '-fno-sanitize-recover=all'])

    def test_named_headselection_scene_setup_and_registration_resume(self):
        self.compile_run('aga_debug_scene_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_opening.c', 'aw_story.c', 'aw_state.c', 'mathlib.c')],
            cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all'])

    def test_scene_voice_tail_survives_memory_clear_and_mixing(self):
        self.compile_run('aga_scene_voice_test.c', [Path(SOURCE)/'src'/n for n in
            ('snd_dma.c', 'snd_mix.c', 'aw_speech.c', 'mathlib.c')],
            cflags=['-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    '-Wl,--wrap=malloc'])

    def test_original_name_entry_and_follow_guard_prompt_keep_world_context(self):
        self.compile_run('aga_modal_intro_test.c', [Path(SOURCE)/'src/aw_ui.c'],
            cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all'])

    def test_modal_policy_host_services_and_client_clock(self):
        for client in (False, True):
            with self.subTest(client=client):
                self.compile_run('aga_modal_world_test.c', [Path(SOURCE)/'src'/n for n in
                    ('aw_ui.c', 'cl_main.c' if client else 'host.c', 'mathlib.c')],
                    defines=['MODAL_CLIENT'] if client else [],
                    cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all'])

    def test_guard_torches_source_registry_cycle_pose_lights_and_depth(self):
        self.compile_run('aga_guard_torch_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_guard_torch.c','mathlib.c')],
            cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'])

    def test_torch_brush_rendering_with_leaf_and_collision_only_roots(self):
        self.compile_run('aga_torch_brush_test.c', [Path(SOURCE)/'src'/n for n in
            ('r_main.c','r_light.c','r_surf.c','mathlib.c','aw_render_ranges.c')],
            cflags=['-fsanitize=address,undefined','-fno-sanitize-recover=all'])

    def test_compiled_hand_rules_extinguish_torch_and_preserve_fist_attack(self):
        compiler=os.environ.get('QCC_PATH') or shutil.which('qcc-host')
        if not compiler:
            self.skipTest('set QCC_PATH to the validated host QCC')
        from build_aga import validate_quakec
        # Bind the fixture from the engine table, not the QC declaration: a
        # mistaken QC index must exercise the wrong real ABI behavior and fail.
        builtin_source=(Path(SOURCE)/'src/pr_cmds.c').read_text()
        table=builtin_source.split('builtin_t pr_builtin[] =',1)[1].split('#ifdef QUAKE2',1)[0]
        table=re.sub(r'/\*.*?\*/|//[^\n]*','',table,flags=re.S)
        builtin_names=re.findall(r'\bPF_\w+\b',table)
        rint_index=builtin_names.index('PF_rint');floor_index=builtin_names.index('PF_floor')
        self.assertEqual((rint_index,floor_index),(36,37))
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);qc=directory/'qc';qc.mkdir()
            for name in ('defs.qc','world.qc','progs.src'):
                shutil.copyfile(Path(SOURCE)/'qc'/name,qc/name)
            result=subprocess.run([str(Path(compiler).resolve())],cwd=qc,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            validate_quakec(directory/'progs.dat')
            self.compile_run('aga_torch_qc_test.c',[Path(SOURCE)/'src/pr_exec.c', Path(SOURCE)/'src/aw_torch.c'],
                cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'],
                defines=[f'TEST_RINT_BUILTIN_INDEX={rint_index}',f'TEST_FLOOR_BUILTIN_INDEX={floor_index}'],
                arguments=[str(directory/'progs.dat')])
            # A control compiled with the historical wrong number must fail
            # against this same engine-derived fixture mapping.
            world=qc/'world.qc'
            world.write_text(world.read_text().replace('floor = #37;','floor = #36;'))
            result=subprocess.run([str(Path(compiler).resolve())],cwd=qc,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            with self.assertRaisesRegex(AssertionError,'Hand sequence 1 sample 2: frame 9 expected 8'):
                # Keep the expected failure out of the outer test's subTest collector.
                NativeSourceTests().compile_run('aga_torch_qc_test.c',[Path(SOURCE)/'src/pr_exec.c',Path(SOURCE)/'src/aw_torch.c'],
                    defines=[f'TEST_RINT_BUILTIN_INDEX={rint_index}',f'TEST_FLOOR_BUILTIN_INDEX={floor_index}'],
                    cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'],
                    arguments=[str(directory/'progs.dat')])


    def test_torch_controls_bounded_light_surface_illumination_and_overlay(self):
        self.compile_run('aga_torch_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_torch.c','cl_main.c','r_light.c','r_surf.c','r_bsp.c','mathlib.c')],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_exterior_background_uses_sky_with_infinite_depth_and_interior_resets(self):
        self.compile_run('aga_background_test.c', [Path(SOURCE)/'src/d_edge.c', Path(SOURCE)/'src/d_part.c'])
        self.compile_run('aga_sky_selection_test.c', [Path(SOURCE)/'src/r_sky.c'])
        self.compile_run('aga_sky_depth_test.c', [Path(SOURCE)/'src/d_scan.c'], cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_daynight_sky_phases_toggle_midnight_and_interior_isolation(self):
        self.compile_run('aga_daynight_test.c', [Path(SOURCE)/'src'/n for n in
            ('r_sky.c','aw_fog.c','aw_horizon.c','aw_clock.c','aw_state.c','r_part.c','mathlib.c','d_sky.c')],
            cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'])

    def test_night_source_stars_are_one_native_pixel_behind_art_world_and_moons(self):
        self.compile_run('aga_daynight_test.c', [Path(SOURCE)/'src'/n for n in
            ('r_sky.c','aw_fog.c','aw_horizon.c','aw_clock.c','aw_state.c','r_part.c','mathlib.c','d_sky.c')],
            cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'],
            arguments=['10'])
        self.compile_run('aga_daynight_test.c', [Path(SOURCE)/'src'/n for n in
            ('r_sky.c','aw_fog.c','aw_horizon.c','aw_clock.c','aw_state.c','r_part.c','mathlib.c','d_sky.c')],
            cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'],
            arguments=['11'])

    def test_cloud_veil_preserves_classic_and_invalidates_composer_cache(self):
        for mode in (12,13):
            with self.subTest(mode=mode):
                self.compile_run('aga_daynight_test.c', [Path(SOURCE)/'src'/n for n in
                    ('r_sky.c','aw_fog.c','aw_horizon.c','aw_clock.c','aw_state.c','r_part.c','mathlib.c','d_sky.c')],
                    cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'],
                    arguments=[str(mode)])

    def test_cloud_control_v2_legacy_rollback_protected_twilight_and_coverage(self):
        self.compile_run('aga_daynight_test.c', [Path(SOURCE)/'src'/n for n in
            ('r_sky.c','aw_fog.c','aw_horizon.c','aw_clock.c','aw_state.c','r_part.c','mathlib.c','d_sky.c')],
            cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'],
            arguments=['14'])

    def test_guard_lights_change_world_and_rotated_brush_final_pixels(self):
        self.compile_run('aga_guard_light_surface_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_guard_torch.c','r_light.c','r_surf.c','r_bsp.c','d_surf.c','mathlib.c')],
            cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'])

    def test_owned_night_atlas_moons_occlusion_twinkle_and_corruption(self):
        for mode in range(6,10):
            with self.subTest(mode=mode):
                self.compile_run('aga_daynight_test.c', [Path(SOURCE)/'src'/n for n in
                    ('r_sky.c','aw_fog.c','aw_horizon.c','aw_clock.c','aw_state.c','r_part.c','mathlib.c','d_sky.c')],
                    cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'],
                    arguments=[str(mode)])

    def test_sky_cloud_roles_palette_marker_and_procedural_particle_compatibility(self):
        for mode in range(1,6):
            with self.subTest(mode=mode):
                self.compile_run('aga_daynight_test.c', [Path(SOURCE)/'src'/n for n in
                    ('r_sky.c','aw_fog.c','aw_horizon.c','aw_clock.c','aw_state.c','r_part.c','mathlib.c','d_sky.c')],
                    cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'],
                    arguments=[str(mode)])

    def test_world_terrain_rebasing_and_bidirectional_town_crossings(self):
        self.compile_run('aga_world_regions_test.c', [Path(SOURCE)/'src/aw_world.c'],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_alias_near_quad_clips_every_screen_edge(self):
        self.compile_run('aga_alias_clip_test.c', [Path(SOURCE)/'src'/n for n in
            ('r_aclip.c','r_alias.c')],
            cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'])

    def test_torch_stride_depth_and_actual_alias_transform(self):
        self.compile_run('aga_viewmodel_bob_test.c', [Path(SOURCE)/'src'/n for n in
            ('view.c','r_alias.c','r_sprite.c','mathlib.c')],
            cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'])

    def test_world_map_journal_disk_bounds_navigation_and_modal_exit(self):
        self.compile_run('aga_worldui_test.c', [Path(SOURCE)/'src'/n for n in ('aw_worldui.c','aw_state.c','aw_save_codec.c')],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_mouse_event_order_accumulation_modal_reset_and_signed_deltas(self):
        cases = ('same_batch_tabs', 'sequential_clamp', 'game_accumulation',
                 'signed_game', 'filter', 'modal_reset', 'ui_routes', 'bounds')
        for standard, selected in (('gnu89', cases),
                                   ('gnu99', ('signed_game', 'filter', 'bounds'))):
            with self.subTest(standard=standard):
                self.compile_run('aga_mouse_event_test.c', [Path(SOURCE)/'src'/n for n in
                    ('in_amiga.c', 'cl_input.c', 'aw_worldui.c', 'aw_state.c', 'aw_save_codec.c')],
                    cflags=['-fsanitize=undefined,float-cast-overflow', '-fno-sanitize-recover=all'],
                    standard=standard, argument_sets=[(case,) for case in selected])

    def test_world_ui_drag_cancels_on_focus_loss_without_lost_release(self):
        # Compile the real shared native focus-case body without Amiga SDK I/O.
        # The fixture uses actual Key_ClearStates and IN_AWClearButtons routines.
        source = (Path(SOURCE)/'src/sys_amiga.c').read_text()
        branches = re.findall(
            r'case IDCMP_ACTIVEWINDOW:\s*case IDCMP_INACTIVEWINDOW:\s*(.*?)break;',
            source, re.S)
        self.assertEqual(len(branches), 1, 'native focus case must be unambiguous')
        cases = ('focus_left', 'focus_right', 'focus_middle', 'focus_journal',
                 'normal_left', 'normal_right', 'normal_middle', 'close_reopen',
                 'selection_preserved', 'cursor_preserved', 'game_motion_discarded')
        with tempfile.TemporaryDirectory() as tmp:
            adapter = Path(tmp)/'focus.c'
            adapter.write_text('#include "quakedef.h"\nvoid AW_TestFocusEvent(void){'
                               + branches[0].strip() + '}\n')
            self.compile_run('aga_map_focus_test.c',
                [*[Path(SOURCE)/'src'/n for n in
                   ('in_amiga.c', 'cl_input.c', 'keys.c', 'aw_worldui.c', 'aw_state.c')], adapter],
                cflags=['-fsanitize=undefined,float-cast-overflow', '-fno-sanitize-recover=all'],
                argument_sets=[(case,) for case in cases])

    def test_journal_history_dates_duplicates_and_capacity_transaction(self):
        self.compile_run('aga_journal_state_test.c', [Path(SOURCE)/'src/aw_state.c'],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_prefetch_byte_identity_cancellation_eviction_and_low_memory_fallback(self):
        self.compile_run('aga_stream_test.c', [Path(SOURCE)/'src/aw_stream.c'],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_sprite_scale_frame_bounds_leaf_membership_and_legacy_messages(self):
        self.compile_run('aga_sprite_scale_test.c', [Path(SOURCE)/'src'/n for n in ('r_sprite.c','r_efrag.c','model.c','cl_parse.c','mathlib.c')],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_sprite_scaled_authored_origins_match_pixels_and_occlusion(self):
        self.compile_run('aga_sprite_mapping_test.c',
            [Path(SOURCE)/'src'/n for n in ('r_sprite.c','d_sprite.c','mathlib.c')],
            cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'])

    def test_sprite_stream_matches_generic_pixels_groups_and_bounded_pack_member(self):
        self.compile_run('aga_sprite_stream_test.c', [Path(SOURCE)/'src/model.c'],
            cflags=['-fsanitize=address,undefined','-fno-sanitize-recover=all'])

    def test_sprite_stream_dispatch_precedes_full_file_staging(self):
        source=(Path(SOURCE)/'src/model.c').read_text(encoding='utf-8')
        self.assertIn('#define AW_STREAM_SPRITES 1',source)
        self.assertLess(source.index('if(Mod_TryStreamSprite(mod))return mod;'),
                        source.index('COM_LoadStackFile (mod->name'))

    def test_optional_alias_budget_default_cap_and_invalid_settings(self):
        self.compile_run('aga_alias_budget_test.c', [Path(SOURCE)/'src/model.c'])

    def test_gallery_lookup_variants_keys_bounds_and_return_scene(self):
        self.compile_run('aga_gallery_test.c', [Path(SOURCE)/'src'/n for n in ('aw_gallery.c','keys.c','in_amiga.c')],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_npc_visible_head_close_target_and_bounded_ground_contact(self):
        self.compile_run('aga_npc_contact_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_scene.c', 'mathlib.c')],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_modifier_qualifiers_lost_shift_caps_and_focus_reset(self):
        self.compile_run("aga_modifier_state_test.c", [Path(SOURCE)/"src/keys.c"])

    def test_configurable_map_desktop_flight_keys_and_literal_console_input(self):
        self.compile_run("aga_keymap_test.c", [Path(SOURCE)/"src/keys.c"])

    def test_legacy_numeric_view_binds_preserve_custom_slots(self):
        self.compile_run('aga_controls_migration_test.c', [Path(SOURCE)/'src/keys.c'])

    def test_console_half_full_closed_and_escape(self):
        self.compile_run('aga_console_cycle_test.c', [Path(SOURCE)/'src/console.c'])

    def test_sprite_background_depth_and_wall_occlusion(self):
        self.compile_run('aga_sprite_depth_test.c', [Path(SOURCE)/'src/d_sprite.c'])

    def test_brush_fragments_do_not_use_far_culled_leaf_keys(self):
        self.compile_run('aga_brush_culling_test.c', [Path(SOURCE)/'src'/n for n in
            ('r_bsp.c', 'r_efrag.c', 'mathlib.c')])

    def test_dialogue_modes_preserve_panel_and_transparent_names(self):
        self.compile_run('aga_dialogue_test.c', [Path(SOURCE)/'src/aw_ui.c'])

    def test_wait_cancel_bounds_calendar_and_debug_time(self):
        self.compile_run('aga_wait_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_wait.c','aw_clock.c','aw_state.c','view.c','r_sky.c')],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_scenery_cannot_displace_late_npcs_from_visible_list(self):
        self.compile_run('aga_visible_entities_test.c', [Path(SOURCE)/'src/r_efrag.c', Path(SOURCE)/'src/mathlib.c'],
            cflags=['-fsanitize=address,undefined','-fno-sanitize-recover=all'])

    def test_loading_services_music_without_clearing_dma_or_loading_sfx(self):
        self.compile_run('aga_loading_audio_test.c', [Path(SOURCE)/'src'/n for n in
            ('snd_dma.c', 'snd_mix.c')])

    def test_character_catalogue_and_preview_decoder_bounds(self):
        self.compile_run('aga_character_assets_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_character.c','aw_head.c')],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_character_stats_conditional_state_and_save_corruption(self):
        self.compile_run('aga_character_state_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_character.c','aw_story.c','aw_state.c','aw_save_codec.c','aw_clock.c')],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_authored_rotated_barriers_and_release_condition(self):
        self.compile_run('aga_barrier_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_barrier.c','aw_story.c','aw_state.c','mathlib.c')],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_fighting_permissions_survive_office_exit_and_release(self):
        self.compile_run("aga_controls_test.c", [Path(SOURCE)/"src"/n for n in
            ("aw_intro.c", "aw_story.c", "aw_state.c")],
            cflags=["-fsanitize=undefined", "-fno-sanitize-recover=all"])

    def test_dock_automatic_interception_and_speech_gates(self):
        self.compile_run("aga_opening_test.c", [Path(SOURCE)/"src"/n for n in
            ("aw_opening.c", "aw_story.c", "aw_state.c", "mathlib.c")],
            cflags=["-fsanitize=undefined", "-fno-sanitize-recover=all"])

    def test_two_dimensional_arrays_respect_row_bounds(self):
        for mode in ("texinfo", "particles"):
            with self.subTest(mode=mode):
                self.compile_run("aga_array_bounds_test.c",
                    [Path(SOURCE)/"src/model.c", Path(SOURCE)/"src/r_part.c", Path(SOURCE)/"src/mathlib.c"],
                    cflags=["-fsanitize=undefined", "-fno-sanitize-recover=all"], arguments=[mode])

    def test_ship_ambience_gain_is_local_to_static_prison_channels(self):
        self.compile_run("aga_ship_ambience_test.c", [Path(SOURCE)/"src/snd_dma.c", Path(SOURCE)/"src/mathlib.c"])

    def test_movie_stream_clock_skip_and_bounds(self):
        self.compile_run("aga_movie_test.c", [ROOT/"engine/aga/src/aw_movie.c"])

    def test_alias_decode_preserves_hot_cache_with_real_allocator(self):
        self.compile_run("aga_alias_residency_test.c", [Path(SOURCE)/"src/model.c", Path(SOURCE)/"src/mathlib.c"],
                         cflags=["-fsanitize=undefined", "-fno-sanitize-recover=all", "-Wl,--wrap=malloc"])

    def test_alias_staging_is_released_before_cache_allocation(self):
        self.compile_run("aga_alias_cache_test.c", [Path(SOURCE)/"src/model.c",Path(SOURCE)/"src/mathlib.c"])

    def test_alias_coarse_frustum_keeps_intersecting_bounds(self):
        self.compile_run("aga_alias_cull_test.c", [Path(SOURCE)/"src/r_alias.c"])

    def test_actor_step_matches_scaled_player_limit(self):
        self.compile_run("aga_actor_step_test.c", [Path(SOURCE)/"src/sv_move.c",Path(SOURCE)/"src/mathlib.c"])

    def test_speech_clock_end_interrupt_and_missing_envelope(self):
        self.compile_run("aga_speech_test.c", [ROOT/"engine/aga/src/aw_speech.c"])

    def test_path_grid_collision_stop_and_escort_wait(self):
        self.compile_run("aga_nav_test.c", [ROOT/"engine/aga/src/aw_nav.c",Path(SOURCE)/"src/mathlib.c"])

    def test_paper_font_isolated_from_small_ui_and_safe_fallback(self):
        for mode in ("valid", "missing", "corrupt", "wrong-size", "truncated", "oversized", "allocation"):
            with self.subTest(mode=mode):
                self.compile_run("aga_paper_font_test.c", [ROOT/"engine/aga/src/aw_ui.c"],
                    cflags=["-fsanitize=undefined", "-fno-sanitize-recover=all", "-Wl,--wrap=malloc"],
                    arguments=[mode])

    def test_ui_bounds_and_corrupt_fonts(self):
        self.compile_run("aga_ui_test.c", [ROOT/"engine/aga/src/aw_ui.c", ROOT/"engine/aga/src/aw_intro.c"])

    def test_underwater_palette_and_independent_damage(self):
        self.compile_run('aga_palette_test.c', [ROOT/'engine/aga/src/view.c', Path(SOURCE)/'src/mathlib.c'])

    def test_large_visibility_load_uses_one_allocation_and_preserves_bytes(self):
        self.compile_run("aga_bsp_byte_load_test.c", [],
                         cflags=["-O2", "-fwhole-program"])

    def test_scene_links_preserve_state_and_find_hatch_floor(self):
        self.compile_run("aga_scene_test.c", [ROOT/"engine/aga/src/aw_scene.c", ROOT/"engine/aga/src/aw_region.c", ROOT/"engine/aga/src/aw_story.c", ROOT/"engine/aga/src/aw_state.c", Path(SOURCE)/"src/mathlib.c", Path(SOURCE)/"src/cl_main.c", Path(SOURCE)/"src/view.c"])

    def test_first_person_sprite_span_bounds(self):
        self.compile_run("aga_hand_sprites_test.c", [ROOT/"engine/aga/src/aw_hand_sprites.c"], ["AMIWIND_SPRITE_HANDS=1"])

    def test_console_reflow_and_scrolled_log_anchor(self):
        self.compile_run("aga_console_buffer_test.c", [Path(SOURCE)/"src/console.c"])

    def test_authored_door_audio_setting_and_catalogue_bounds(self):
        self.compile_run("aga_door_audio_test.c", [ROOT/"engine/aga/src/aw_door_audio.c"])

    def test_mesh_depth_crossings_and_span_coverage(self):
        self.compile_run("aga_mesh_spans_test.c", [ROOT/"engine/aga/src/r_edge.c"])

    def test_console_dispatch_background_and_palette(self):
        self.compile_run("aga_console_test.c", [ROOT/"engine/aga/src/aw_console.c", ROOT/"engine/aga/src/aw_console_glyphs.c"])

    def test_noclip_pitch_vertical_stop_and_speed(self):
        self.compile_run("aga_noclip_test.c", [ROOT/"engine/aga/src/aw_walk.c", Path(SOURCE)/"src/mathlib.c"])

    def test_menu_disabled_options_cancel_and_confirm(self):
        self.compile_run("aga_menu_test.c", [ROOT/"engine/aga/src/aw_menu.c"])

    def test_coordinate_toggle_and_reserved_strip(self):
        self.compile_run("aga_hud_test.c", [ROOT/"engine/aga/src/aw_hud.c"])

    def test_unsigned_face_plane_indices_and_bounds(self):
        self.compile_run("aga_face_index_test.c", [Path(SOURCE)/"src/model.c"])

    def test_interaction_only_on_game_key_down(self):
        self.compile_run('aga_interact_test.c', [Path(SOURCE)/'src/cl_input.c'])

    def test_balmora_region_round_trip(self):
        self.compile_run('aga_region_test.c', [Path(SOURCE)/'src/aw_region.c'])

    def test_strider_available_destination_and_return(self):
        self.compile_run('aga_scene_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_scene.c', 'aw_region.c', 'aw_story.c', 'aw_state.c', 'mathlib.c', 'cl_main.c', 'view.c')], ['BALMORA_AVAILABLE'])

    def test_scenery_above_edict_limit_and_rotated_collision(self):
        self.compile_run('aga_scenery_test.c', [Path(SOURCE)/'src/world.c', Path(SOURCE)/'src/mathlib.c'])

    def test_entity_exhaustion_recovers_or_fails_as_configured(self):
        self.compile_run('aga_entity_exhaustion_test.c', [Path(SOURCE)/'src/pr_edict.c'])

    def test_dense_flora_signon_round_trip_at_buffer_capacity(self):
        self.compile_run('aga_flora_signon_test.c', [Path(SOURCE)/'src'/n for n in ('net_loop.c','common.c')])

    def compile_run(self, fixture, sources, defines=(), cflags=(), arguments=(),
                    standard='gnu89', argument_sets=None):
        tree = Path(SOURCE).resolve()
        if any(p.name == "aw_scene.c" for p in sources):
            sources = [*sources, tree/"src/aw_world.c"]
        if any(p.name == "world.c" for p in sources):
            sources = [*sources, tree/"src/aw_scenery.c"]
        if any(p.name in ("aw_scene.c", "aw_scenery.c") for p in sources):
            sources = [*sources, tree/"src/aw_harvest.c", tree/"src/aw_harvest_runtime.c"]
            if not any(p.name == "aw_state.c" for p in sources):
                sources.append(tree/"src/aw_state.c")
        if any(p.name == "aw_harvest_runtime.c" for p in sources):
            if not any(p.name == "aw_harvest_proxy.c" for p in sources):
                sources.append(tree/"src/aw_harvest_proxy.c")
        with tempfile.TemporaryDirectory() as tmp:
            from project_version import generate_native
            generate_native(ROOT/'VERSION', Path(tmp))
            exe = Path(tmp) / 'check'
            cmd = ['cc', *cflags, *['-D'+d for d in defines], '-std='+standard, '-ffunction-sections', '-fdata-sections',
                   '-include', str(ROOT/'tests/aga_test_files.h'),
                   '-Wl,--gc-sections', '-I'+tmp, '-I'+str(tree/'src'), str(ROOT/'tests'/fixture),
                   *[str(p) for p in sources], '-lm', '-o', str(exe)]
            if os.name == 'nt':
                target = subprocess.run(['cc', '-dumpmachine'], capture_output=True,
                                        text=True).stdout
                if 'cygwin' in target or 'msys' in target:
                    # GCC translates source paths, but cc1's -include/-I paths
                    # need MSYS mount syntax when invoked from native Python.
                    cmd = [re.sub(r'^(-I)?([A-Za-z]):/',
                                  lambda m: (m[1] or '') + '/' + m[2].lower() + '/',
                                  arg.replace('\\', '/')) for arg in cmd]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            for argv in argument_sets if argument_sets is not None else (arguments,):
                with self.subTest(arguments=argv):
                    result = subprocess.run([str(exe), *argv], cwd=tmp, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rotated_platform_and_vacated_space(self):
        self.compile_run('aga_collision_test.c', [Path(SOURCE)/'src/world.c', Path(SOURCE)/'src/mathlib.c'])

    def test_far_plane_matches_fog_depth(self):
        self.compile_run('aga_culling_test.c', [ROOT/'engine/aga/src/aw_fog.c',ROOT/'engine/aga/src/aw_horizon.c'])

    def test_nearby_door_depth_order(self):
        self.compile_run('aga_depth_test.c', [Path(SOURCE)/'src/r_edge.c'])

    def test_standing_spawn_has_ground_and_exits(self):
        self.compile_run('aga_spawn_test.c', [ROOT/'engine/aga/src/aw_spawn.c', Path(SOURCE)/'src/mathlib.c'])

    def test_grounded_walk_drift_steps_and_jump(self):
        self.compile_run('aga_walk_test.c', [ROOT/'engine/aga/src/aw_walk.c', Path(SOURCE)/'src/mathlib.c'])
