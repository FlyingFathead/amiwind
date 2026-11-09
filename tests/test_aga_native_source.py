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
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = os.environ.get('AMIWIND_RUNTIME_SOURCE', str(ROOT / 'engine/aga'))
# model.c with what its alias stream calls for skeletal models (aw_skel.c, aw_skel_load.c; docs/MODULAR_NPCS.md method C)
SKEL_MODEL = ('model.c', 'aw_skel.c', 'aw_skel_load.c')


def tree_project_version():
    """This tree's tools/project_version.py, loaded from its file: compile_run generates the
    version headers with it, never with an older copy elsewhere on sys.path (a builder image
    ships one), and sys.path stays as it is (TEST-NATIVE-STALE-IMPORT-33)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('amiwind_tree_project_version', ROOT / 'tools/project_version.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def area_fixture(id1):
    """AREA-TABLES-59: a synthetic id1 (focus.awf AWF3 with owners and contents, inventory/items.awi, the icon pack)
    with three rooms, its areas.awa from tools/prepare_area_tables.py, and expect.txt: the answers it was made with.
    Each room's items are its own (so an item of another room needs a narrow load)."""
    import struct
    sys.path.insert(0, str(ROOT / 'tools'))
    try:
        from prepare_focus import owner_list, contents_list, record_id, clean, NAME
        import prepare_area_tables
    finally:
        sys.path.pop(0)
    owners_of = {0: ('arrille', 0), 1: ('fighters_guild', 1)}
    rooms, owners, containers, items, expect, icons = {}, {}, {}, {}, [], {}
    for r, room in enumerate((10, 11, 12)):
        rows = []
        for c in range(2):
            ref = 1000 + 10 * r + c
            entries = [('r%d_%s' % (room, x), 1 + c + k) for k, x in enumerate('ab'[:c + 1])]
            owner = owners_of.get(c) if not (room == 12 and c == 1) else None
            rows.append((ord('C'), int(bool(owner)), 1 | (4 if owner else 0), 10 * c, ref, ('Chest %d' % c), b''))
            containers[ref] = (entries, 1 if c else 0)
            if owner:
                owners[ref] = owner
            expect.append('C %d %d %s %d %d %s' % (room, ref, owner[0] if owner else '-', owner[1] if owner else 0,
                                                 len(entries), ' '.join('%s %d' % e for e in entries)))
            for ident, _ in entries:
                items[ident] = 'Item %s' % ident
        pref = 2000 + r
        pid = 'r%d_p' % room
        items[pid] = 'Placed %s' % pid
        rows.append((ord('I'), 0, 1, 0, pref, 'Placed', pid))
        expect.append('P %d %d %s' % (room, pref, pid))
        rooms[room] = rows
        icons['big:r%d_a' % room] = (4, 3, 40 + r)
    index, body = [], []
    for room in sorted(rooms):
        index.append(struct.pack('<III', room, len(body), len(rooms[room])))
        for kind, owned, action, lock, ref, name, ident in rooms[room]:
            raw = clean(name)
            body.append(struct.pack('<BBBBIiiifi', kind, owned, action, lock, ref, 8 * ref % 97, 0, 16, 1.0, 5) +
                        raw + b'\0' * (NAME - len(raw)) + record_id(ident if isinstance(ident, str) else ''))
    focus = (b'AWF3' + struct.pack('<I', len(index)) + b''.join(index) + b''.join(body) + owner_list(owners) +
             contents_list({ref: (entries, flags) for ref, (entries, flags) in containers.items()}))
    rows = []
    for ident in sorted(items):
        row = bytearray(512)
        row[0:len(ident)] = ident.encode(); row[64:64 + len(items[ident])] = items[ident].encode()
        struct.pack_into('<IiIfII', row, 160, 7, 0, 3, 0.5, 0, 0)
        rows.append(bytes(row))
        expect.append('I %s %s' % (ident, items[ident]))
    pack, table = bytearray(b'AWP1' + struct.pack('<I', len(icons))), []
    for key in sorted(icons):
        w, h, first = icons[key]
        pic = b'AWI1' + struct.pack('<HH', w, h) + bytes([first] + [1] * (w * h - 1))
        row = bytearray(160); row[0:len(key)] = key.encode()
        struct.pack_into('<II', row, 120, len(pack), len(pic))
        table.append(bytes(row)); pack += pic
        expect.append('K %s %d %d %d' % (key[4:], w, h, first))   # after "big:" (ITEM-ICONS-MISSING-62)
    (id1 / 'inventory').mkdir(parents=True); (id1 / 'gfx').mkdir()
    (id1 / 'focus.awf').write_bytes(focus)
    (id1 / 'inventory/items.awi').write_bytes(b'AWI2' + struct.pack('<I', len(rows)) + b''.join(rows))
    (id1 / 'gfx/icons.awl').write_bytes(b'AWL2' + struct.pack('<I', len(table)) + b''.join(table))
    (id1 / 'gfx/icons.awp').write_bytes(bytes(pack))
    payload, report = prepare_area_tables.build(id1)
    (id1 / 'areas.awa').write_bytes(payload)
    (id1 / 'expect.txt').write_text('\n'.join(expect) + '\n', encoding='ascii')
    return report


def levelled_fixture(id1):
    """CONTAINER-LEVELLED-CONTENTS-60 / CORPSE-LOOT-60: a synthetic id1 with one room (10): container 1000 (an item of
    its own and three levelled entries), container 1001 (two levelled entries, one a list inside a list) and an actor
    1002 with an inventory (an item and a levelled entry); focus.awf with its AWL1 lists, items.awi, areas.awa from
    tools/prepare_area_tables.py. The answers are in tests/aga_levelled_contents_test.c. Returns the build report."""
    import struct
    sys.path.insert(0, str(ROOT / 'tools'))
    try:
        from prepare_focus import contents_list, record_id, clean, NAME, levelled_section, owner_list
        import prepare_area_tables
    finally:
        sys.path.pop(0)
    lists = {'l_low_high': (0, 0, [('lev_low', 1), ('lev_high', 5)]),
             'l_each': (1, 0, [('gem', 1)]),
             'l_nested': (2, 0, [('l_each', 1)]),
             'l_none': (0, 100, [('gem', 1)])}
    containers = {1000: ([('base_item', 2), ('l_low_high', 1), ('l_each', 3), ('l_none', 5)], 0),
                  1001: ([('l_low_high', 2), ('l_nested', 1)], 0),
                  1002: ([('npc_shirt', 1), ('l_each', 2)], 8)}
    rows = [(ord('C'), 1000, 'Sack'), (ord('C'), 1001, 'Basket'), (ord('A'), 1002, 'Arrille')]
    body = []
    for kind, ref, name in rows:
        raw = clean(name)
        body.append(struct.pack('<BBBBIiiifi', kind, 0, 1 if kind == ord('C') else 3, 0, ref, 0, 0, 16, 0.0, 0) +
                    raw + b'\0' * (NAME - len(raw)) + record_id(''))
    focus = (b'AWF3' + struct.pack('<I', 1) + struct.pack('<III', 10, 0, len(body)) + b''.join(body) +
             owner_list({}) + contents_list(containers) + levelled_section(lists))
    items = []
    for ident in sorted(('base_item', 'lev_low', 'lev_high', 'gem', 'npc_shirt')):
        row = bytearray(512)
        row[0:len(ident)] = ident.encode(); row[64:64 + len(ident)] = ident.title().encode()
        struct.pack_into('<IiIfII', row, 160, 7, 0, 3, 0.5, 0, 0)
        items.append(bytes(row))
    (id1 / 'inventory').mkdir(parents=True)
    (id1 / 'focus.awf').write_bytes(focus)
    (id1 / 'inventory/items.awi').write_bytes(b'AWI2' + struct.pack('<I', len(items)) + b''.join(items))
    payload, report = prepare_area_tables.build(id1)
    (id1 / 'areas.awa').write_bytes(payload)
    return report


# Engine files that build map paths through aw_mappath.c (AW_MapPath).
MAP_PATH_USERS = ('aw_region.c', 'aw_section.c', 'aw_scene.c', 'aw_gallery.c', 'aw_arena.c', 'aw_wait.c',
                  'sv_main.c', 'chim_world.c')

class VersionHeaderSourceTests(unittest.TestCase):
    def test_version_headers_come_from_this_tree(self):
        module = tree_project_version()
        self.assertEqual(Path(module.__file__).resolve(), (ROOT / 'tools/project_version.py').resolve())
        with tempfile.TemporaryDirectory() as tmp:
            module.generate_native(ROOT / 'VERSION', Path(tmp))
            self.assertTrue((Path(tmp) / 'amiwind_version.h').is_file())
            if (ROOT / 'CHIM_VERSION').is_file():
                self.assertTrue((Path(tmp) / 'chim_version.h').is_file())
        source = Path(__file__).read_text(encoding='utf-8')
        self.assertNotIn('from project_version ' + 'import generate_native', source)

    def test_unchanged_headers_are_not_rewritten(self):
        # BUILD-VERSION-HEADER-RACE-61: the heap header's make rule runs the generator on every make, beside the
        # compiles; an unchanged header must keep its bytes and its time stamp, so no compile reads it half written
        module = tree_project_version()
        with tempfile.TemporaryDirectory() as tmp:
            module.generate_native(ROOT / 'VERSION', Path(tmp))
            files = sorted(Path(tmp).iterdir())
            for path in files:
                os.utime(path, ns=(1_000_000_000, 1_000_000_000))
            module.generate_native(ROOT / 'VERSION', Path(tmp))
            for path in files:
                self.assertEqual(path.stat().st_mtime_ns, 1_000_000_000, path.name)

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

class VisibleEntityDropContractTests(unittest.TestCase):
    """Every place that refuses an entity for a full cl_visedicts counts it
    (R_StoreEfrags is covered natively by aga_visible_entities_test.c)."""

    def test_dynamic_and_temporary_entities_count_their_drops(self):
        main = (Path(SOURCE)/'src/cl_main.c').read_text()
        relink = main[main.index('void CL_RelinkEntities'):main.index('CL_ReadFromServer')]
        self.assertIn('aw_visedicts_dropped_frame = 0;', relink)
        self.assertRegex(relink, r'if \(cl_numvisedicts < MAX_VISEDICTS\)\s*\{[^}]*\}\s*else\s*AW_VisedictDropped \(\);')
        tent = (Path(SOURCE)/'src/cl_tent.c').read_text()
        new = tent[tent.index('entity_t *CL_NewTempEntity'):]
        self.assertRegex(new, r'if \(cl_numvisedicts == MAX_VISEDICTS\)\s*\{\s*AW_VisedictDropped \(\);\s*return NULL;')


# Engine sources that write diagnostic logs through aw_log.c.
LOG_USERS = {"aw_music.c", "keys.c", "aw_stream.c", "model.c", "zone.c", "aw_profile.c",
             "sys_amiga.c", "aw_debug.c"}


def includes_aw_log(fixture, seen=None):
    """True when a fixture includes aw_log.c itself or through another test fixture."""
    seen = set() if seen is None else seen
    if fixture in seen or not fixture.is_file():
        return False
    seen.add(fixture)
    text = fixture.read_text(encoding='utf-8')
    if 'aw_log.c' in text:
        return True
    return any(includes_aw_log(fixture.parent / name, seen)
               for name in re.findall(r'#include "([^"/]+\.c)"', text))


@unittest.skipIf(os.name == 'nt', 'native helper fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'install a host C compiler')
class NativeSourceTests(unittest.TestCase):
    def test_swimming_idle_and_pitch_directed_motion(self):
        self.compile_run('aga_water_move_test.c', [Path(SOURCE)/'src'/n for n in
            ('sv_user.c', 'mathlib.c')],
            cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all'])

    def test_brightness_controls_six_steps_independent_sliders_and_return(self):
        self.compile_run('aga_brightness_menu_test.c', [Path(SOURCE)/'src/aw_menu.c'],
            defines=['AMIWIND_DEBUG_LUMA=1'],
            cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'])

    def test_luma_disabled_commands_explain_build(self):
        self.compile_run('aga_luma_disabled_test.c', [Path(SOURCE)/'src/r_light.c'])

    def test_audio_options_keyboard_mouse_and_return_selection(self):
        self.compile_run('aga_audio_menu_test.c', [Path(SOURCE)/'src/aw_menu.c'],
            cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'])

    def test_audio_bus_levels_actual_pcm_and_archived_settings(self):
        self.compile_run('aga_audio_levels_test.c', [Path(SOURCE)/'src'/n for n in
            ('snd_dma.c','snd_mix.c','aw_speech.c','aw_music.c','cvar.c','mathlib.c')],
            cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all','-Wl,--wrap=malloc'])

    def test_head_preview_reads_service_real_mixer_and_preserve_failures(self):
        self.compile_run('aga_head_audio_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_head.c','snd_dma.c','snd_mix.c')],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all','-Wl,--wrap=fread'],
            arguments=['sliced'])

    def test_first_save_description_loads_character_catalogue(self):
        self.compile_run('aga_save_frontmenu_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_save.c', 'aw_save_codec.c', 'aw_ledger.c', 'aw_jhist.c')])

    def test_autosave_preserves_safe_checkpoint_through_lava_and_arrival(self):
        self.compile_run('aga_autosave_safety_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_save.c', 'aw_save_codec.c', 'aw_ledger.c', 'aw_jhist.c', 'mathlib.c')],
            cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all'])

    def test_harvest_original_loot_transaction_capacity_and_save_persistence(self):
        self.compile_run('aga_harvest_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_harvest.c', 'aw_state.c', 'aw_save_codec.c')],
            cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all'])

    def test_harvest_exact_brush_binding_occlusion_hide_and_crossings(self):
        self.compile_run('aga_harvest_runtime_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_harvest.c', 'aw_harvest_runtime.c', 'aw_state.c', 'mathlib.c')],
            cflags=['-fsanitize=undefined,float-cast-overflow', '-fno-sanitize-recover=all'])

    def test_chim_town_harvest_follows_the_region(self):
        # CHIM: per-region harvest catalogues follow the player within a town's frame map.
        self.compile_run('aga_chim_harvest_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_region.c', 'aw_harvest.c', 'aw_harvest_runtime.c', 'aw_state.c', 'mathlib.c')],
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

    def test_static_flame_offsets_match_golden_angle_formula(self):
        self.compile_run('aga_static_flame_offsets_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_guard_torch.c','mathlib.c')])

    def test_static_flame_budget_keeps_flames_in_view(self):
        # FLAME-RANGE-NEAREST-32: on-screen, size-ranked default; nearest-first kept.
        self.compile_run('aga_static_flame_select_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_guard_torch.c','mathlib.c')],
            cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'])

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
            # the hands' state machine is the engine's now (aw_hands.c, FIRST-PERSON-HANDS-IN-C-54): the fixture runs it
            # on the compiled QC's player fields with the carried torch; the clips come from the image's table, so the
            # old control (a wrong QC floor builtin number) has nothing left to break in the hands
            self.compile_run('aga_torch_qc_test.c',[Path(SOURCE)/'src/pr_exec.c', Path(SOURCE)/'src/aw_torch.c',
                                                    Path(SOURCE)/'src/aw_hands.c'],
                cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'],
                defines=[f'TEST_RINT_BUILTIN_INDEX={rint_index}',f'TEST_FLOOR_BUILTIN_INDEX={floor_index}'],
                arguments=[str(directory/'progs.dat')])


    def test_torch_controls_bounded_light_surface_illumination_and_overlay(self):
        self.compile_run('aga_torch_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_torch.c','cl_main.c','r_light.c','r_surf.c','r_bsp.c','cvar.c','mathlib.c')],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_exterior_background_uses_sky_with_infinite_depth_and_interior_resets(self):
        self.compile_run('aga_background_test.c', [Path(SOURCE)/'src/d_edge.c', Path(SOURCE)/'src/d_part.c'])
        self.compile_run('aga_sky_selection_test.c', [Path(SOURCE)/'src/r_sky.c', Path(SOURCE)/'src/mathlib.c'])
        self.compile_run('aga_sky_depth_test.c', [Path(SOURCE)/'src/d_scan.c'], cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_daynight_sky_phases_toggle_midnight_and_interior_isolation(self):
        self.compile_run('aga_daynight_test.c', [Path(SOURCE)/'src'/n for n in
            ('r_sky.c','aw_fog.c','aw_horizon.c','aw_clock.c','aw_state.c','r_part.c','mathlib.c','d_sky.c')],
            cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'])

    def test_light_space_night_dims_light_keeps_hue_and_shades_unlit(self):
        self.compile_run('aga_daynight_test.c', [Path(SOURCE)/'src'/n for n in
            ('r_sky.c','aw_fog.c','aw_horizon.c','aw_clock.c','aw_state.c','r_part.c','mathlib.c','d_sky.c')],
            cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'],
            arguments=['--night-light'])

    def test_night_tint_keeps_dark_near_greys_from_turning_rust(self):
        self.compile_run('aga_daynight_test.c', [Path(SOURCE)/'src'/n for n in
            ('r_sky.c','aw_fog.c','aw_horizon.c','aw_clock.c','aw_state.c','r_part.c','mathlib.c','d_sky.c')],
            cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'],
            arguments=['--night-rust'])

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

    def test_coordinate_teleport_inside_the_loaded_map_without_the_region_table(self):
        # DEBUG-TP-MINIWIND-36: a MiniWind disk ships no open-world region table; dbg tp X Y resolves a point inside
        # the loaded map (its CHIM frame) and only that, and a refusal names the maps the disk holds
        self.compile_run('aga_world_regions_test.c', [Path(SOURCE)/'src/aw_world.c'],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'], arguments=['no-directory'])
        scene = (ROOT/'engine/aga/src/aw_scene.c').read_text(encoding='utf-8')
        command = re.search(r'static void teleport_command\(void\) \{(.*?)\n\}', scene, re.S).group(1)
        self.assertEqual(command.count('map_teleport(source,'), 2)
        self.assertEqual(command.count('disk_maps_note();'), 2)
        self.assertIn('loaded_map && AW_WorldLoadedTarget(sv.name,source_position,r.target,r.arrival)', scene)
        self.assertIn('return map_teleport(source_position,use_height,0);', scene)

    def test_alias_near_quad_clips_every_screen_edge(self):
        self.compile_run('aga_alias_clip_test.c', [Path(SOURCE)/'src'/n for n in
            ('r_aclip.c','r_alias.c','aw_skel.c')],
            cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'])

    def test_torch_stride_depth_and_actual_alias_transform(self):
        self.compile_run('aga_viewmodel_bob_test.c', [Path(SOURCE)/'src'/n for n in
            ('view.c','r_alias.c','r_sprite.c','mathlib.c','aw_skel.c')],
            cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'])

    def test_inventory_atomic_ownership_equipment_and_condition_save(self):
        for fixture, extra in (('aga_inventory_test.c', ()), ('aga_inventory_save_test.c', ('aw_save_codec.c','aw_story.c'))):
            self.compile_run(fixture, [Path(SOURCE)/'src'/n for n in ('aw_inventory.c','aw_state.c',*extra)],
                defines=['AW_INVENTORY_RULES_ONLY'],
                cflags=['-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-parameter',
                        '-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_hud_icon_table_boxes_bars_and_single_load(self):
        # HUD-STATS-29: the original weapon/magic boxes from the one icon table.
        self.compile_run('aga_hud_icons_test.c', [Path(SOURCE)/'src/aw_icons.c'],
            cflags=['-Wall','-Werror=implicit-function-declaration','-fsanitize=address,undefined','-fno-sanitize-recover=all'])

    def test_placed_item_pickup_through_the_use_path(self):
        # PICKUP-PLACED-58: the real focus and item tables, aim, reach and take (AW_InventoryUse)
        self.compile_run('aga_focus_pickup_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_inventory.c','aw_state.c','aw_ledger.c','aw_ledger_drops.c','mathlib.c')],
            cflags=['-fsanitize=address,undefined','-fno-sanitize-recover=all'])

    def test_container_strip_prompt_locks_take_and_put(self):
        # CONTAINER-WINDOW-59: the real focus table (AWF3, owners and contents), prompt, lock, E, take and put through
        # the container deltas (owned: stolen), and the strip's pure rules
        self.compile_run('aga_container_strip_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_inventory.c','aw_cstrip_rules.c','aw_state.c','aw_ledger.c','aw_ledger_drops.c','mathlib.c')],
            cflags=['-fsanitize=address,undefined','-fno-sanitize-recover=all'])

    def test_container_strip_open_both_ways_take_reads_once(self):
        # CONTAINER-STRIP-TAKE-STALL-59: the real strip opened by E and by the console (aw_placed container REF open):
        # the same open, takes, put, Take All and Esc; the container's data read once while open; the whole-screen
        # copy only after a change (CONTAINER-STRIP-REDRAW-COST-59)
        self.compile_run('aga_container_strip_open_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_inventory.c','aw_cstrip.c','aw_cstrip_rules.c','aw_state.c','aw_ledger.c','aw_ledger_drops.c','mathlib.c')],
            cflags=['-fsanitize=address,undefined','-fno-sanitize-recover=all'])

    def test_area_tables_answer_as_the_files_load_unload_and_narrow(self):
        # AREA-TABLES-59: the per-area tables built by tools/prepare_area_tables.py over a synthetic focus.awf, item
        # table and icon pack give every container's contents and owner, the item names, the placed items' records and
        # the strip's pictures exactly as the island-wide files do, with no file opened and no fallback in a loaded
        # room; a room left is kept and taken back without a read; the trim empties the cache; a container or item
        # elsewhere is narrow-loaded through the directory
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp) / 'id1'
            area_fixture(id1)
            self.compile_run('aga_area_tables_test.c', [Path(SOURCE)/'src'/n for n in
                ('aw_inventory.c','aw_state.c','aw_ledger.c','aw_ledger_drops.c','mathlib.c')],
                arguments=[str(id1)], cflags=['-fsanitize=address,undefined','-fno-sanitize-recover=all'])

    def test_levelled_contents_roll_once_and_actor_inventories(self):
        # CONTAINER-LEVELLED-CONTENTS-60 / CORPSE-LOOT-60: levelled entries rolled on the first open by the game's rule
        # and kept on the world change list; a body's inventory through the same strip data, never theft
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp) / 'id1'
            report = levelled_fixture(id1)
            self.assertEqual((report['levelled_item_lists'], report['areas_with_levelled'], report['actor_inventories'],
                              report['item_chunks'], report['item_chunk_items']), (4, 1, 1, 1, 3))
            self.compile_run('aga_levelled_contents_test.c', [Path(SOURCE)/'src'/n for n in
                ('aw_inventory.c','aw_state.c','aw_ledger.c','aw_ledger_drops.c','mathlib.c',
                 'chim/chim_actor_table.c','chim/chim_format.c')],
                arguments=[str(id1)], cflags=['-fsanitize=address,undefined','-fno-sanitize-recover=all'])

    def test_inventory_real_drop_placement_capacity_and_no_loss(self):
        # the old fixed table (aw_ledger_on 0) and the world change list (CELL-CHANGES-59), both through the real drop
        self.compile_run('aga_inventory_placement_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_inventory.c','aw_state.c','aw_ledger.c','aw_ledger_drops.c','mathlib.c')],
            cflags=['-fsanitize=address,undefined,float-cast-overflow','-fno-sanitize-recover=all'])

    def test_starting_outfit_worn_from_the_first_scene_once_per_game(self):
        # CHARGEN-NO-STARTING-CLOTHES-60: the player record's outfit, as tools/prepare_inventory.py writes it from a
        # synthetic master (shirt, pants, shoes on the NPC "player"), is carried and worn from the first scene spawn
        # on, also after a take marked the inventory before its first open; once per game
        import struct
        from unittest.mock import patch
        sys.path.insert(0, str(ROOT / 'tools'))
        try:
            import prepare_inventory
        finally:
            sys.path.pop(0)
        def record(kind, fields):
            data = b''.join(k.encode() + struct.pack('<I', len(v)) + v for k, v in fields)
            return kind.encode() + struct.pack('<III', len(data), 0, 0) + data
        raw = b''
        for ident, name, kind in (('common_shirt_01', 'Common Shirt', 2), ('common_pants_01', 'Common Pants', 0),
                                  ('common_shoes_01', 'Common Shoes', 1)):
            raw += record('CLOT', [('NAME', ident.encode() + b'\0'), ('FNAM', name.encode() + b'\0'),
                                   ('CTDT', struct.pack('<ifHH', kind, 1., 2, 0))])
        raw += record('NPC_', [('NAME', b'player\0')] + [('NPCO', struct.pack('<i', 1) + i.encode().ljust(32, b'\0'))
                       for i in ('common_shirt_01', 'common_shoes_01', 'common_pants_01')])
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); (base / 'Morrowind.esm').write_bytes(raw)
            with patch.object(prepare_inventory, 'resolve_data_files', return_value=base):
                report = prepare_inventory.prepare(base, base / 'id1', palette=b'\0' * 768, models=False)
            self.assertEqual(sorted(i['id'] for i in report['initial_items']),
                             ['common_pants_01', 'common_shirt_01', 'common_shoes_01'])
            self.compile_run('aga_starting_outfit_test.c', [Path(SOURCE)/'src'/n for n in
                ('aw_inventory.c','aw_state.c','aw_ledger.c','aw_ledger_drops.c','mathlib.c')],
                arguments=[str(base / 'id1')], cflags=['-fsanitize=address,undefined','-fno-sanitize-recover=all'])

    def test_inventory_actual_alias_preview_gear_depth_bounds_and_release(self):
        self.compile_run('aga_inventory_preview_test.c', [Path(SOURCE)/'src'/n for n in ('aw_head.c','mathlib.c')],
            cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'])

    def test_inventory_metadata_rejects_nonfinite_damage_and_path_escape(self):
        self.compile_run('aga_inventory_metadata_test.c', [Path(SOURCE)/'src'/n for n in ('aw_inventory.c','common.c')],
            cflags=['-Wl,--wrap=COM_FOpenFile','-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'])

    def test_inventory_fullscreen_events_real_equip_atomic_drop_and_exit(self):
        self.compile_run('aga_inventory_ui_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_worldui.c','aw_questbook.c','aw_jhist.c','aw_ledger.c','aw_textdef.c','aw_inventory.c','aw_harvest.c','aw_state.c','aw_save_codec.c','mathlib.c','common.c')],
            defines=['AW_INVENTORY_RULES_ONLY','AW_TEXTDEF_HOST_TEST'],
            cflags=['-Wl,--wrap=COM_FOpenFile','-Werror=implicit-function-declaration','-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'])

    def test_stats_and_magic_windows_content_grouping_keys_and_live_update(self):
        # The original's Stats window (P) and the Magic placeholder (O), aw_statswin.c.
        self.compile_run('aga_statswin_test.c', [Path(SOURCE)/'src'/n for n in ('aw_statswin.c','aw_console_glyphs.c')],
            cflags=['-Wl,--wrap=AW_SmallStringColor','-Wall','-Werror=implicit-function-declaration',
                    '-fsanitize=address,undefined','-fno-sanitize-recover=all'])

    def test_world_map_journal_disk_bounds_navigation_and_modal_exit(self):
        self.compile_run('aga_worldui_test.c', [Path(SOURCE)/'src'/n for n in ('aw_worldui.c','aw_questbook.c','aw_jhist.c','aw_ledger.c','aw_textdef.c','aw_inventory.c','aw_state.c','aw_save_codec.c','mathlib.c')],
            defines=['AW_INVENTORY_RULES_ONLY','AW_TEXTDEF_HOST_TEST'], cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_mouse_event_order_accumulation_modal_reset_and_signed_deltas(self):
        cases = ('same_batch_tabs', 'sequential_clamp', 'game_accumulation',
                 'signed_game', 'filter', 'modal_reset', 'ui_routes', 'bounds')
        for standard, selected in (('gnu89', cases),
                                   ('gnu99', ('signed_game', 'filter', 'bounds'))):
            with self.subTest(standard=standard):
                self.compile_run('aga_mouse_event_test.c', [Path(SOURCE)/'src'/n for n in
                    ('in_amiga.c', 'cl_input.c', 'aw_worldui.c', 'aw_questbook.c', 'aw_jhist.c', 'aw_ledger.c', 'aw_textdef.c', 'aw_inventory.c', 'aw_state.c', 'aw_save_codec.c', 'mathlib.c')],
                    defines=['AW_INVENTORY_RULES_ONLY', 'AW_TEXTDEF_HOST_TEST'], cflags=['-fsanitize=undefined,float-cast-overflow', '-fno-sanitize-recover=all'],
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
                   ('in_amiga.c', 'cl_input.c', 'keys.c', 'aw_worldui.c', 'aw_questbook.c', 'aw_jhist.c', 'aw_ledger.c', 'aw_textdef.c', 'aw_inventory.c', 'aw_state.c', 'mathlib.c')], adapter],
                defines=['AW_INVENTORY_RULES_ONLY', 'AW_TEXTDEF_HOST_TEST'], cflags=['-fsanitize=undefined,float-cast-overflow', '-fno-sanitize-recover=all'],
                argument_sets=[(case,) for case in cases])

    def test_journal_history_dates_duplicates_and_capacity_transaction(self):
        self.compile_run('aga_journal_state_test.c', [Path(SOURCE)/'src/aw_state.c'],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_journal_book_lists_every_kept_quest_by_name(self):
        # JOURNAL-BOOK-32-QUESTS-59: the book's quests from the kept stages on the world change list, no 32 limit
        self.compile_run('aga_questbook_test.c', [Path(SOURCE)/'src'/n for n in ('aw_questbook.c','aw_ledger.c')],
            cflags=['-fsanitize=address,undefined','-fno-sanitize-recover=all'])

    def test_dated_journal_history_on_the_change_list_and_in_saves(self):
        # JOURNAL-ORIGINAL-VIEW-59: the dated history past 32 quests and 256 entries, its save feature 128 both ways,
        # an older save's 32-slot history taken over
        self.compile_run('aga_jhist_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_jhist.c','aw_ledger.c','aw_save_codec.c','aw_state.c','mathlib.c')],
            cflags=['-fsanitize=address,undefined','-fno-sanitize-recover=all'])

    def test_dialogue_speaker_functions_and_disposition_terms(self):
        # DIALOGUE-COMPLETE-58: SameSex, SameRace, ShouldAttack through the shared evaluator; disease, drawn weapon, Charm
        self.compile_run('aga_dial_rules_test.c', [Path(SOURCE)/'src/aw_dial.c', Path(SOURCE)/'src/aw_glut.c'],
            defines=['AW_GLUT_HOST_TEST'], cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_dialogue_link_clicks_after_the_first(self):
        # DIALOGUE-LINKS-62 (v0.0.62-dev1): A, then B in the new answer, A again, C, in the topic and barter lists and
        # after scrolling; the old rule (the linkable set rebuilt only with the topic list) loses the second click
        self.compile_run('aga_dial_links_test.c', [Path(SOURCE)/'src/aw_dial_links.c'],
            cflags=['-fsanitize=address,undefined','-fno-sanitize-recover=all'])
        win = (Path(SOURCE)/'src/aw_dialwin.c').read_text(encoding='utf-8')
        body = win.split('static void refresh(void){')[1].split('\n}')[0]
        self.assertIn('if(linkable){\n        if(topics_at>=0)AW_DialLinksSet(', body)
        self.assertIn('AW_DialTopicList(&conv,known,&state,topics,AW_DIAL_MAX_TOPICS)', body)
        self.assertIn('AW_DialLinkHit(hits,nhits,mouse_x,mouse_y,row_h())', win)
        # DIALOGUE-SCROLLBARS-62: both panes' bars drawn every frame, a plain click and a held drag scroll them
        draw = win.split('static void draw(void){')[1].split('\n}')[0]
        self.assertIn('draw_bar(BAR_TEXT);', draw)
        self.assertIn('draw_bar(BAR_LIST);', draw)
        self.assertIn('if(b>=0){bar_click(b,mouse_y);return 1;}', win)
        self.assertIn('aw_worldui_panel_drag=bar_dragged;', win)
        ui = (Path(SOURCE)/'src/aw_worldui.c').read_text(encoding='utf-8')
        self.assertIn('if(modal==4 && drag==K_MOUSE1 && aw_worldui_panel_drag)', ui)

    def test_prefetch_byte_identity_cancellation_eviction_and_low_memory_fallback(self):
        self.compile_run('aga_stream_test.c', [Path(SOURCE)/'src/aw_stream.c'],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_sprite_scale_frame_bounds_leaf_membership_and_legacy_messages(self):
        self.compile_run('aga_sprite_scale_test.c', [Path(SOURCE)/'src'/n for n in ('r_sprite.c','r_efrag.c','model.c','cl_parse.c','mathlib.c','aw_skel.c','aw_skel_load.c')],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_sprite_scaled_authored_origins_match_pixels_and_occlusion(self):
        self.compile_run('aga_sprite_mapping_test.c',
            [Path(SOURCE)/'src'/n for n in ('r_sprite.c','d_sprite.c','mathlib.c')],
            cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'])

    def test_sprite_stream_matches_generic_pixels_groups_and_bounded_pack_member(self):
        self.compile_run('aga_sprite_stream_test.c', [Path(SOURCE)/'src'/n for n in SKEL_MODEL],
            cflags=['-fsanitize=address,undefined','-fno-sanitize-recover=all'])

    def test_sprite_stream_dispatch_precedes_full_file_staging(self):
        source=(Path(SOURCE)/'src/model.c').read_text(encoding='utf-8')
        self.assertIn('#define AW_STREAM_SPRITES 1',source)
        self.assertLess(source.index('if(Mod_TryStreamSprite(mod))return mod;'),
                        source.index('COM_LoadStackFile (mod->name'))

    def test_optional_alias_budget_default_cap_and_invalid_settings(self):
        self.compile_run('aga_alias_budget_test.c', [Path(SOURCE)/'src'/n for n in SKEL_MODEL])

    def test_gallery_lookup_variants_keys_bounds_and_return_scene(self):
        self.compile_run('aga_gallery_test.c', [Path(SOURCE)/'src'/n for n in ('aw_gallery.c','aw_intro.c','aw_story.c','aw_state.c','keys.c','in_amiga.c')],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_npc_visible_head_close_target_and_bounded_ground_contact(self):
        self.compile_run('aga_npc_contact_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_scene.c', 'mathlib.c')],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_modifier_qualifiers_lost_shift_caps_and_focus_reset(self):
        self.compile_run("aga_modifier_state_test.c", [Path(SOURCE)/"src/keys.c"])

    def test_console_history_arrows_from_native_raw_keys(self):
        self.compile_run("aga_console_history_test.c", [Path(SOURCE)/"src/keys.c"],
            cflags=['-fsanitize=address,undefined','-fno-sanitize-recover=all'])

    def test_configurable_map_desktop_flight_keys_and_literal_console_input(self):
        self.compile_run("aga_keymap_test.c", [Path(SOURCE)/"src/keys.c"])

    def test_legacy_numeric_view_binds_preserve_custom_slots(self):
        self.compile_run('aga_controls_migration_test.c', [Path(SOURCE)/'src/keys.c'])

    def test_console_half_full_closed_and_escape(self):
        self.compile_run('aga_console_cycle_test.c', [Path(SOURCE)/'src/console.c'])

    def test_sprite_background_depth_and_wall_occlusion(self):
        self.compile_run('aga_sprite_depth_test.c', [Path(SOURCE)/'src/d_sprite.c'])

    def test_brush_model_rotation_zero_yaw_and_cached_paths(self):
        self.compile_run('aga_rotate_bmodel_test.c', [Path(SOURCE)/'src'/n for n in
            ('r_bsp.c', 'r_efrag.c', 'mathlib.c')],
            cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all'])

    def test_engine_text_number_conversion_matches_c_library(self):
        # ENGINE-FPSP-MISSING-31: no C library float parsing/printing in the engine.
        self.compile_run('aga_format_test.c', [Path(SOURCE)/'src/aw_format.c'],
            cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all'])

    def test_fpu_support_status_line_and_command(self):
        self.compile_run('aga_fpu_status_test.c', [Path(SOURCE)/'src/aw_fpu_status.c'],
            cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all'])
        host = (Path(SOURCE)/'src/host.c').read_text()
        self.assertEqual(host.count('AW_FpuStatusInit ();'), 1)
        self.assertLess(host.index('AW_FpuCountInit ();'), host.index('AW_FpuStatusInit ();'))

    def test_table_sine_cosine_accuracy_and_exact_quadrants(self):
        self.compile_run('aga_sintable_test.c', [Path(SOURCE)/'src/mathlib.c'],
            cflags=['-fsanitize=undefined,float-cast-overflow', '-fno-sanitize-recover=all'])

    def test_brush_fragments_do_not_use_far_culled_leaf_keys(self):
        self.compile_run('aga_brush_culling_test.c', [Path(SOURCE)/'src'/n for n in
            ('r_bsp.c', 'r_efrag.c', 'mathlib.c')])

    def test_dialogue_modes_preserve_panel_and_transparent_names(self):
        self.compile_run('aga_dialogue_test.c', [Path(SOURCE)/'src/aw_ui.c'])

    def test_night_lamps_read_per_cell_and_light_the_nearest_at_night(self):
        self.compile_run('aga_lamps_test.c', [Path(SOURCE)/'src/aw_lamps.c'],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_location_fog_day_night_blend(self):
        self.compile_run('aga_fog_location_test.c', [Path(SOURCE)/'src/aw_fog_location.c'],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_remote_console_command_and_state_files(self):
        self.compile_run('aga_remote_test.c', [Path(SOURCE)/'src/aw_remote.c'],
            cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    # CHIM-FRAME-SOURCE-CONVERSION-59: callers on a CHIM frame map, through the real shared conversion (aw_world.c)
    # on a disk without the region table: the lighting kind (night lamps, both directions) and the readout kind (the
    # remote state file's GLOBAL line); the script host's map-load decision is in aga_world_regions_test.c (frame_maps),
    # the frame's own half in aga_chim_world_test.c (ring).
    def test_night_lamps_on_a_chim_frame_map(self):
        self.compile_run('aga_lamps_test.c', [Path(SOURCE)/'src/aw_lamps.c', Path(SOURCE)/'src/aw_world.c'],
            defines=['AW_FRAME_MAP'], cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_remote_state_global_line_on_a_chim_frame_map(self):
        self.compile_run('aga_remote_test.c', [Path(SOURCE)/'src/aw_remote.c', Path(SOURCE)/'src/aw_world.c'],
            defines=['AW_FRAME_MAP'], cflags=['-fsanitize=undefined','-fno-sanitize-recover=all'])

    def test_wait_cancel_bounds_calendar_and_debug_time(self):
        self.compile_run('aga_wait_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_wait.c','aw_rest_rules.c','aw_clock.c','aw_state.c','view.c','r_sky.c','mathlib.c')],
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

    def test_chargen_class_list_and_review_sheet(self):
        # CHARGEN-CENSUS-57 (a): class list with details; review sheet with derived stats and grouped skills
        self.compile_run('aga_chargen_class_review_test.c', [Path(SOURCE)/'src'/n for n in
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
                    [Path(SOURCE)/"src"/n for n in SKEL_MODEL] + [Path(SOURCE)/"src/r_part.c", Path(SOURCE)/"src/mathlib.c"],
                    cflags=["-fsanitize=undefined", "-fno-sanitize-recover=all"], arguments=[mode])

    def test_ship_ambience_gain_is_local_to_static_prison_channels(self):
        self.compile_run("aga_ship_ambience_test.c", [Path(SOURCE)/"src/snd_dma.c", Path(SOURCE)/"src/mathlib.c"])

    def test_sound_name_table_never_fills(self):
        # AUDIO-SFX-NAME-TABLE-FULL-58: more than MAX_SFX different sounds in a session, the newest still found
        self.compile_run("aga_sfx_names_test.c", [Path(SOURCE)/"src/snd_dma.c", Path(SOURCE)/"src/mathlib.c"])

    def test_movie_stream_clock_skip_and_bounds(self):
        self.compile_run("aga_movie_test.c", [ROOT/"engine/aga/src/aw_movie.c"])

    def test_quick_test_build_marker_and_missing_movie(self):
        # tools/build.py --exclude: id1/excluded-content.txt (aw_excluded.c) and aw_movie.c without videos.
        self.compile_run("aga_excluded_test.c", [ROOT/"engine/aga/src/aw_movie.c", ROOT/"engine/aga/src/aw_excluded.c"],
            cflags=["-fsanitize=undefined", "-fno-sanitize-recover=all"])

    def test_alias_decode_preserves_hot_cache_with_real_allocator(self):
        self.compile_run("aga_alias_residency_test.c", [Path(SOURCE)/"src"/n for n in SKEL_MODEL] + [Path(SOURCE)/"src/mathlib.c"],
                         cflags=["-fsanitize=undefined", "-fno-sanitize-recover=all", "-Wl,--wrap=malloc"])

    def test_alias_staging_is_released_before_cache_allocation(self):
        self.compile_run("aga_alias_cache_test.c", [Path(SOURCE)/"src"/n for n in SKEL_MODEL] + [Path(SOURCE)/"src/mathlib.c"])

    def test_alias_coarse_frustum_keeps_intersecting_bounds(self):
        self.compile_run("aga_alias_cull_test.c", [Path(SOURCE)/"src/r_alias.c", Path(SOURCE)/"src/aw_skel.c"])

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

    def test_inventory_dedicated_pose_equipment_cache_and_refusal(self):
        self.compile_run('aga_inventory_pose_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_anim.c','aw_view_rules.c')],
            cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'])

    def test_ui_bounds_and_corrupt_fonts(self):
        self.compile_run("aga_ui_test.c", [Path(SOURCE)/'src'/n for n in
            ('aw_ui.c','aw_intro.c','aw_inventory.c','aw_story.c','aw_state.c')],
            cflags=['-Wl,--wrap=malloc','-fsanitize=undefined','-fno-sanitize-recover=all'],
            # CURSOR-MW-58: Morrowind's pointer in the image, none, and a corrupt file (both: AmiWind's cursor)
            argument_sets=[(), ('nocursor',), ('badcursor',)])

    def test_noclip_has_no_bob_or_roll_and_walking_gets_them_back(self):
        # NOCLIP-BOB-DEFAULT-42
        self.compile_run('aga_noclip_bob_test.c', [ROOT/'engine/aga/src/view.c', Path(SOURCE)/'src/mathlib.c'])

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
        # AWSFX1 (earlier images), AWSFX2 (every load door, AW-20260928-10) and an AWSFX2 table with a bad pair row
        self.compile_run("aga_door_audio_test.c", [ROOT/"engine/aga/src/aw_door_audio.c"],
                         argument_sets=[("v1",), ("v2",), ("v2bad",)])

    def test_hinged_doors_turn_hold_lock_and_follow_chim_placements(self):
        # AW-20260928-12: ordinary hinged doors on the engine's own collision (world.c), 90 degrees in one second.
        self.compile_run("aga_hinged_door_test.c", [ROOT/"engine/aga/src/aw_hinged_door.c", Path(SOURCE)/"src/world.c",
                                                    Path(SOURCE)/"src/mathlib.c"],
                         argument_sets=[["table"], ["badtable"], ["door"], ["chim"], ["census"], ["locks"], ["kept"]],
                         cflags=["-fsanitize=undefined", "-fno-sanitize-recover=all"])

    def test_talk_rule_combat_dead_knocked_calm_and_one_read_a_frame(self):
        # TALK-PROMPT-RULES: one predicate for the prompt and E, from flags only (aw_talk.c).
        self.compile_run("aga_talk_test.c", [ROOT/"engine/aga/src/aw_talk.c"],
                         cflags=["-fsanitize=undefined", "-fno-sanitize-recover=all"])
        scene = (ROOT/"engine/aga/src/aw_scene.c").read_text(encoding="utf-8")
        self.assertIn('if(aw_can_talk?target && aw_can_talk(target):voice && voice->string && pr_strings[voice->string])',
                      scene)
        self.assertIn('if(target && aw_can_talk && !aw_can_talk(target))target=NULL;',
                      (ROOT/"engine/aga/src/pr_cmds.c").read_text(encoding="latin-1"))
        self.assertIn('AW_TalkInit();', (ROOT/"engine/aga/src/aw_debug.c").read_text(encoding="latin-1"))

    def test_mesh_depth_crossings_and_span_coverage(self):
        self.compile_run("aga_mesh_spans_test.c", [ROOT/"engine/aga/src/r_edge.c"])

    def test_console_dispatch_background_and_palette(self):
        self.compile_run("aga_console_test.c", [ROOT/"engine/aga/src/aw_console.c", ROOT/"engine/aga/src/aw_console_glyphs.c"],
            arguments=[str(ROOT/"config/debug-commands.txt")],
            cflags=["-fsanitize=undefined", "-fno-sanitize-recover=all"])

    def test_noclip_pitch_vertical_stop_and_speed(self):
        self.compile_run("aga_noclip_test.c", [ROOT/"engine/aga/src/aw_walk.c", Path(SOURCE)/"src/mathlib.c"])

    def test_movement_rules_match_the_original_speed_load_jump_and_fatigue(self):
        self.compile_run("aga_move_rules_test.c", [ROOT/"engine/aga/src/aw_move_rules.c"],
                         cflags=["-fsanitize=undefined", "-fno-sanitize-recover=all"])

    def test_movement_live_sheet_superspeed_old_numbers_fatigue_and_command(self):
        self.compile_run("aga_move_test.c", [ROOT/"engine/aga/src"/n for n in
                         ("aw_move.c", "aw_move_rules.c", "sv_user.c", "mathlib.c", "aw_state.c")],
                         cflags=["-fsanitize=undefined", "-fno-sanitize-recover=all"])

    def test_menu_disabled_options_cancel_and_confirm(self):
        self.compile_run("aga_menu_test.c", [ROOT/"engine/aga/src/aw_menu.c"])

    def test_coordinate_toggle_and_reserved_strip(self):
        self.compile_run("aga_hud_test.c", [ROOT/"engine/aga/src/aw_hud.c"])

    def test_inspection_click_identity_occlusion_and_attack_restore(self):
        self.compile_run("aga_inspect_test.c", [ROOT/"engine/aga/src/aw_inspect.c", Path(SOURCE)/"src/mathlib.c"],
                         cflags=["-fsanitize=undefined", "-fno-sanitize-recover=all"])

    def test_photo_mode_hides_restores_and_returns_player(self):
        self.compile_run("aga_photo_test.c", [ROOT/"engine/aga/src/aw_photo.c"])

    def test_unsigned_face_plane_indices_and_bounds(self):
        self.compile_run("aga_face_index_test.c", [Path(SOURCE)/"src"/n for n in SKEL_MODEL])

    def test_unsigned_face_texinfo_indices_and_double_precision_extents(self):
        self.compile_run("aga_face_texinfo_test.c", [Path(SOURCE)/"src"/n for n in SKEL_MODEL])

    def test_unsigned_marksurface_and_leaf_mark_indices(self):
        self.compile_run("aga_marksurface_index_test.c", [Path(SOURCE)/"src"/n for n in SKEL_MODEL])

    def test_interaction_only_on_game_key_down(self):
        self.compile_run('aga_interact_test.c', [Path(SOURCE)/'src/cl_input.c'])

    def test_miniwind_notice_file_from_the_builder(self):
        # The file tools/miniwind.py writes for a MiniWind plan parses in the engine.
        sys.path.insert(0, str(ROOT/'tools'))
        import miniwind
        names = ['chim', 'balmora', 'balmora-interiors', 'harvest', 'music', 'media', 'image']
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'miniwind.txt'
            path.write_bytes(miniwind.data_file(miniwind.features_line(names)))
            self.compile_run('aga_miniwind_test.c', [Path(SOURCE)/'src/aw_miniwind.c'],
                             cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all'],
                             arguments=[str(path)])

    def test_quick_character_screen_sequence_and_callers(self):
        # aw_quickchar.c: one entry point for New Game (--skip-census), dbg quickchar and test set-ups.
        self.compile_run('aga_quickchar_test.c', [Path(SOURCE)/'src/aw_quickchar.c'],
                         cflags=['-Wall', '-Wno-unused-function', '-Werror', '-fsanitize=undefined',
                                 '-fno-sanitize-recover=all'])

    def test_test_mailbox_drive_and_startup_options(self):
        # TEST-NATIVE-TMPDIR-32: compile_run executes in its private temp folder.
        # Keep the AWTEST drive relative, even when that host folder is very long.
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(prefix='aw-testbox-' + 'x' * 64) as host:
            self.assertGreater(len(host), 64)
            with patch.object(tempfile, 'tempdir', host):
                self.compile_run('aga_testbox_test.c', [Path(SOURCE)/'src/aw_testbox.c'],
                                 cflags=['-Wall', '-Wno-unused-function', '-Werror', '-fsanitize=undefined',
                                         '-fno-sanitize-recover=all'], arguments=['.'])

    def test_balmora_region_round_trip(self):
        self.compile_run('aga_region_test.c', [Path(SOURCE)/'src/aw_region.c'])

    def test_chim_towns_without_the_legacy_town_regions(self):
        # BUILD-LEGACY-ENGINE-PATHS-48: the engine built without the retired legacy town region streaming
        self.compile_run('aga_region_chim_only_test.c', [Path(SOURCE)/'src/aw_region.c'],
                         ['AW_LEGACY_TOWN_REGIONS=0'])

    def test_data_driven_town_table_and_generic_town_directory(self):
        self.compile_run('aga_town_table_test.c', [Path(SOURCE)/'src/aw_region.c'],
            cflags=['-Wall', '-Wno-unused-function', '-Werror', '-fsanitize=undefined', '-fno-sanitize-recover=all'],
            argument_sets=[(), ('prefix',), ('distance',)])

    def test_strider_available_destination_and_return(self):
        self.compile_run('aga_scene_test.c', [Path(SOURCE)/'src'/n for n in
            ('aw_scene.c', 'aw_region.c', 'aw_story.c', 'aw_state.c', 'mathlib.c', 'cl_main.c', 'view.c')], ['BALMORA_AVAILABLE'])

    def test_scenery_above_edict_limit_and_rotated_collision(self):
        self.compile_run('aga_scenery_test.c', [Path(SOURCE)/'src/world.c', Path(SOURCE)/'src/mathlib.c'])

    def test_entity_exhaustion_recovers_or_fails_as_configured(self):
        self.compile_run('aga_entity_exhaustion_test.c', [Path(SOURCE)/'src/pr_edict.c'])

    def test_dense_flora_signon_round_trip_at_buffer_capacity(self):
        self.compile_run('aga_flora_signon_test.c', [Path(SOURCE)/'src'/n for n in ('net_loop.c','common.c')])

    def test_model_index_over_255_round_trips(self):
        # ENGINE-MODEL-TABLE-58: MAX_MODELS 512, the index a short on the wire, every model table sized by it
        self.compile_run('aga_model_index_test.c', [Path(SOURCE)/'src/common.c'])
        src = Path(SOURCE)/'src'
        for name in ('sv_main.c', 'pr_cmds.c', 'cl_parse.c'):
            text = (src/name).read_text(encoding='utf-8', errors='replace')
            self.assertNotRegex(text, r'MSG_WriteByte\s*\([^;]*(modelindex|SV_ModelIndex)', name)
            self.assertNotRegex(text, r'modelindex\s*=\s*MSG_ReadByte', name)
        self.assertIn('MSG_ReadModel ();\n\t\tif (modnum >= MAX_MODELS)', (src/'cl_parse.c').read_text())

    def compile_run(self, fixture, sources, defines=(), cflags=(), arguments=(),
                    standard='gnu89', argument_sets=None):
        tree = Path(SOURCE).resolve()
        if any(p.name in ("aw_region.c", "aw_scene.c") for p in sources) and not any(p.name=="aw_section.c" for p in sources):
            sources = [*sources, tree/"src/aw_section.c"]
        if any(p.name == "aw_scene.c" for p in sources):
            sources = [*sources, tree/"src/aw_world.c"]
            # the travel services' table rules (TRAVEL-SERVICES-CHIM-51)
            if not any(p.name == "aw_travel_rules.c" for p in sources):
                sources.append(tree/"src/aw_travel_rules.c")
            # the use key's ray and box rules (FOCUS-NPC-OVERRIDES-ITEM-62)
            if not any(p.name == "aw_activate_rules.c" for p in sources):
                sources.append(tree/"src/aw_activate_rules.c")
        # The one map path resolver (aw_mappath.c) every map-path builder asks.
        if any(p.name in MAP_PATH_USERS for p in sources) and not any(p.name == "aw_mappath.c" for p in sources):
            sources = [*sources, tree/"src/aw_mappath.c"]
        # Partial-area builds (aw_miniwind.c): the scene, logo and New Game paths ask it.
        if any(p.name in ("aw_scene.c", "aw_movie.c", "aw_intro.c") for p in sources) and \
                not any(p.name == "aw_miniwind.c" for p in sources):
            sources = [*sources, tree/"src/aw_miniwind.c"]
        if any(p.name == "world.c" for p in sources):
            sources = [*sources, tree/"src/aw_scenery.c"]
        # the file buffer setting common.c and aw_inventory.c share (TRADEHOUSE-LONG-FRAME-59)
        if any(p.name in ("common.c", "aw_inventory.c") for p in sources) and \
                not any(p.name == "aw_fopenbuf.c" for p in sources):
            sources = [*sources, tree/"src/aw_fopenbuf.c"]
        if any(p.name in ("aw_scene.c", "aw_scenery.c") for p in sources):
            sources = [*sources, tree/"src/aw_harvest.c", tree/"src/aw_harvest_runtime.c"]
            if not any(p.name == "aw_state.c" for p in sources):
                sources.append(tree/"src/aw_state.c")
        hooked = ("aw_movie.c", "aw_scene.c", "aw_intro.c")
        fixture_text = (ROOT/'tests'/fixture).read_text(encoding='utf-8', errors='replace')
        if ((any(p.name in hooked for p in sources) or any('#include "%s"' % n in fixture_text for n in hooked))
                and not any(p.name == "aw_excluded.c" for p in sources)):
            # Quick-test-build marker (id1/excluded-content.txt) used by these files.
            sources = [*sources, tree/"src/aw_excluded.c"]
        if (any(p.name in LOG_USERS for p in sources) and not any(p.name == "aw_log.c" for p in sources)
                and not includes_aw_log(ROOT/"tests"/fixture)):
            # In-memory diagnostic logs (BOOT-VOLUME-NOT-VALIDATED-33); live when unbound.
            sources = [*sources, tree/"src/aw_log.c"]
        # The music stream reads through the asynchronous reader (HANG-IDLE-DUSK-35).
        if any(p.name == "aw_music.c" for p in sources) and not any(p.name == "aw_aread.c" for p in sources):
            sources = [*sources, tree/"src/aw_aread.c"]
        # Weak stand-ins for the quick character screen, the test channels and the notice
        # (tests/aga_hook_stubs.c): fixtures that link the real modules keep them.
        sources = [*sources, ROOT/"tests/aga_hook_stubs.c"]
        if not any(p.name == "aw_format.c" for p in sources):
            # Engine text/number conversion (Q_strtod, Q_sscanf, Q_fscanf).
            sources = [*sources, tree/"src/aw_format.c"]
        if any(p.name == "aw_harvest_runtime.c" for p in sources):
            if not any(p.name == "aw_harvest_proxy.c" for p in sources):
                sources.append(tree/"src/aw_harvest_proxy.c")
        with tempfile.TemporaryDirectory() as tmp:
            tree_project_version().generate_native(ROOT/'VERSION', Path(tmp))
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

    def test_step_rules_match_openmw_over_synthetic_stairs_and_slopes(self):
        # STEP-MOVEMENT-OPENMW-RULES-48 (docs/STEP_MOVEMENT.md): the real walk (aw_walk.c, sv_phys.c) over risers,
        # ramps, lips and drops under aw_step_rules 0 (Quake, the default) and 1 (Morrowind's rules as OpenMW's).
        self.compile_run('aga_step_rules_test.c', [ROOT/'engine/aga/src/aw_walk.c', ROOT/'engine/aga/src/sv_phys.c',
                                                   Path(SOURCE)/'src/mathlib.c'])

    def test_failed_step_inside_solid_settles_once(self):
        # AMBIENT-UNSTUCK-FLOOD-61: a resident put back inside solid by a failed step searched for a clear spot at
        # every step (ten a walk); aw_walk.c AW_ActorSettle runs the search once and keeps the spot (aw_ambient.c,
        # "chim actors ambient settle on", the default written into id1/default-game.cfg).
        self.compile_run('aga_unstuck_test.c', [ROOT/'engine/aga/src/aw_walk.c', ROOT/'engine/aga/src/sv_phys.c',
                                                Path(SOURCE)/'src/mathlib.c'])
        ambient = (ROOT/'engine/aga/src/aw_ambient.c').read_text(encoding='utf-8')
        self.assertIn('static int settle_on=1;', ambient)
        self.assertIn('if(!stepped && settle_on){', ambient)
        self.assertIn('if(AW_ActorSettle(s->e))st.settled++;', ambient)
        import build_aga
        self.assertIn(b'chim actors ambient settle on\n', build_aga.ACTOR_LOGIC_LINES)
