"""Compile real patched engine routines with synthetic geometry on the host.

Uses engine/aga from this repository by default. AMIWIND_RUNTIME_SOURCE can
select another tree for an explicit comparison.
No proprietary data or Amiga SDK is needed for these collision/culling checks.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = os.environ.get('AMIWIND_RUNTIME_SOURCE', str(ROOT / 'engine/aga'))

@unittest.skipUnless(shutil.which('cc'), 'install a host C compiler')
class NativeSourceTests(unittest.TestCase):
    def test_movie_stream_clock_skip_and_bounds(self):
        self.compile_run("aga_movie_test.c", [ROOT/"engine/aga/src/aw_movie.c"])

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

    def test_ui_bounds_and_corrupt_fonts(self):
        self.compile_run("aga_ui_test.c", [ROOT/"engine/aga/src/aw_ui.c"])

    def test_underwater_palette_and_independent_damage(self):
        self.compile_run('aga_palette_test.c', [ROOT/'engine/aga/src/view.c', Path(SOURCE)/'src/mathlib.c'])

    def test_scene_links_preserve_state_and_find_hatch_floor(self):
        self.compile_run("aga_scene_test.c", [ROOT/"engine/aga/src/aw_scene.c", Path(SOURCE)/"src/mathlib.c"])

    def test_first_person_sprite_span_bounds(self):
        self.compile_run("aga_hand_sprites_test.c", [ROOT/"engine/aga/src/aw_hand_sprites.c"], ["AMIWIND_SPRITE_HANDS=1"])

    def test_console_reflow_and_scrolled_log_anchor(self):
        self.compile_run("aga_console_buffer_test.c", [Path(SOURCE)/"src/console.c"])

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

    def compile_run(self, fixture, sources, defines=()):
        tree = Path(SOURCE).resolve()
        with tempfile.TemporaryDirectory() as tmp:
            from project_version import generate_native
            generate_native(ROOT/'VERSION', Path(tmp))
            exe = Path(tmp) / 'check'
            cmd = ['cc', *['-D'+d for d in defines], '-std=gnu89', '-ffunction-sections', '-fdata-sections',
                   '-Wl,--gc-sections', '-I'+tmp, '-I'+str(tree/'src'), str(ROOT/'tests'/fixture),
                   *[str(p) for p in sources], '-lm', '-o', str(exe)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rotated_platform_and_vacated_space(self):
        self.compile_run('aga_collision_test.c', [Path(SOURCE)/'src/world.c', Path(SOURCE)/'src/mathlib.c'])

    def test_far_plane_matches_fog_depth(self):
        self.compile_run('aga_culling_test.c', [ROOT/'engine/aga/src/aw_fog.c'])

    def test_nearby_door_depth_order(self):
        self.compile_run('aga_depth_test.c', [Path(SOURCE)/'src/r_edge.c'])

    def test_standing_spawn_has_ground_and_exits(self):
        self.compile_run('aga_spawn_test.c', [ROOT/'engine/aga/src/aw_spawn.c', Path(SOURCE)/'src/mathlib.c'])

    def test_grounded_walk_drift_steps_and_jump(self):
        self.compile_run('aga_walk_test.c', [ROOT/'engine/aga/src/aw_walk.c', Path(SOURCE)/'src/mathlib.c'])
