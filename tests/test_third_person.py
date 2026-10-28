# SPDX-License-Identifier: GPL-3.0-only
"""The player's view (docs/THIRD_PERSON.md): first/third person on the chase camera, the held orbit,
the vanity orbit, the wheel zoom, the player's body and the death scene (PLAYER-DEATH-LIMBO-35,
COMBAT-PLAYER-DEATH-FALL-33). The rules run as host C; the engine wiring and the builder's data are
checked as source contracts and with synthetic records."""
import os
import re
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import test_aga_native_source as native

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


def body(text, name):
    start = text.index(name)
    start = text.index('{', start)
    depth = 0
    for i in range(start, len(text)):
        depth += {'{': 1, '}': -1}.get(text[i], 0)
        if depth == 0:
            return text[start:i + 1]
    raise ValueError(name)


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class ViewRulesNativeTests(unittest.TestCase):
    def test_toggle_orbit_vanity_zoom_obstacle_and_death_sequence(self):
        native.NativeSourceTests().compile_run('aga_view_test.c', [SRC / 'aw_view_rules.c', SRC / 'aw_anim.c'],
                                               defines=('AW_VIEW_HOST_TEST', 'AW_ANIM_HOST_TEST'), cflags=UBSAN)

    def test_player_dead_predicate(self):
        native.NativeSourceTests().compile_run('aga_player_dead_test.c', [], cflags=UBSAN)


class ViewEngineContracts(unittest.TestCase):
    def test_first_person_is_the_default_and_the_settings_come_from_the_image(self):
        view = (SRC / 'aw_view.c').read_text(encoding='utf-8')
        self.assertIn('static cvar_t view_cvar={"aw_view_third","0"};', view)
        rules = code('aw_view_rules.c')
        self.assertIn('v->mode=v->primary=AW_VIEW_FIRST;', rules)
        # fVanityDelay and the prompt's text are read from the image (the master's game settings).
        self.assertIn('COM_FOpenFile("view/settings.txt"', view)
        for name in ('"fVanityDelay"', '"sLoadLastSaveMsg"', '"sYes"', '"sNo"'):
            self.assertIn(name, view)

    def test_dead_player_cannot_talk_activate_attack_or_move(self):
        intro = code('aw_intro.c')
        self.assertIn('int (*aw_death_input_locked)(void);', intro)
        for name in ('void AW_IntroMove(', 'int AW_IntroButtons(', 'int AW_IntroImpulse('):
            self.assertIn('dead_locked()', body(intro, name), name)
        self.assertIn('dead_locked()', intro[intro.index('int AW_IntroUse(void)'):][:200])
        # E (talk, activate) goes through AW_IntroUse; the QuakeC impulse 201 through AW_IntroImpulse.
        self.assertIn('if (AW_IntroUse()) return;', body((SRC / 'cl_input.c').read_text(encoding='utf-8'),
                                                          'void IN_AWUseDown'))
        self.assertIn('aw_death_input_locked=AW_DeathLocked;', code('aw_view.c'))

    def test_chase_camera_hooks_hands_body_keys_and_prompt(self):
        view = code('view.c')
        self.assertIn('if (chase_active.value && !(aw_view_camera && aw_view_camera ()))', view)
        self.assertIn('Chase_Update ();', view)                       # the previous method stays
        self.assertIn('r_refdef.viewangles[ROLL] = 80;', view)        # the first-person death view stays
        self.assertIn('aw_view_frame ();', body(view, 'void V_RenderView'))
        self.assertIn('aw_view_hide_hands && aw_view_hide_hands ()', body(code('r_main.c'), 'void R_DrawViewModel'))
        self.assertIn('aw_view_body (ent)', code('cl_main.c'))
        keys = code('keys.c')
        event = body(keys, 'void Key_Event')
        self.assertLess(event.index('aw_view_input (key, down)'), event.index('keydown[key] = down;'))
        self.assertGreater(event.index('aw_view_key(key)'), event.index('AW_IntroKey('))
        self.assertIn('aw_view_draw ();', code('screen.c'))
        self.assertIn('AW_ViewInit();', code('aw_debug.c'))
        make = (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8')
        self.assertIn('aw_view_rules.c aw_view.c', make)

    def test_relink_keeps_its_cursor_and_draws_the_body_through_its_own_pointer(self):
        # CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36: `ent = aw_view_body (ent)` moved CL_RelinkEntities'
        # cursor onto aw_view.c's static body, so in third person every later entity (every NPC) was
        # read and written past that body and never drawn.
        relink = body(code('cl_main.c'), 'void CL_RelinkEntities')
        self.assertIn('draw = aw_view_body (ent)', relink)
        self.assertIn('cl_visedicts[cl_numvisedicts] = draw;', relink)
        loop = relink[relink.index('for (i=1,ent=cl_entities+1'):]
        self.assertIsNone(re.search(r'(?<![\w.>=!<])\bent\s*=(?!=)', loop[loop.index('{'):]))

    def test_held_torch_comes_back_after_eviction_and_shows_in_the_inventory(self):
        # PLAYER-TORCH-THIRDPERSON-38: the held torch alias was drawn only while Cache_Check found it;
        # after any eviction the raised arm stayed (the renderer reloads the body) and the torch never
        # returned. The inventory picture never drew it at all.
        view = code('aw_view.c')
        held = body(view, 'static entity_t *view_held')
        self.assertIn('held_ready()', held)
        self.assertNotIn('Cache_Check(&held_model->cache)', held)
        ready = body(view, 'static int held_ready')
        self.assertIn('AW_ViewHeldRetry(', ready)
        self.assertIn('Mod_ForName(held_path,false)', ready)
        self.assertIn('held_ready()', body(view, 'int AW_ViewInventoryHeld'))
        self.assertIn('AW_ViewInventoryHeld(', body(code('aw_head.c'), 'int AW_InventoryPreviewDraw'))

    def test_no_engine_loop_moves_its_pointer_cursor(self):
        # Island-wide sweep: a `for (...,p=array...; ...; ...,p++)` loop never reassigns p in its body.
        offenders = []
        for path in sorted(SRC.glob('*.c')):
            text = re.sub(r'/\*.*?\*/|//[^\n]*', '', path.read_text(encoding='utf-8', errors='replace'), flags=re.S)
            for m in re.finditer(r'\bfor\s*\(([^;]*);[^;]*;[^)]*,\s*(\w+)\s*\+\+\s*\)\s*\{', text):
                cursor = m.group(2)
                if not re.search(r'\b' + cursor + r'\s*=\s*&?[A-Za-z_]', m.group(1)):
                    continue                                   # an index, not a pointer cursor
                start, depth = m.end() - 1, 0
                for i in range(start, len(text)):
                    depth += {'{': 1, '}': -1}.get(text[i], 0)
                    if depth == 0:
                        break
                if re.search(r'(?<![\w.>=!<+\-*/&|^%])\b' + cursor + r'\s*=(?!=)', text[start:i]):
                    offenders.append('%s:%d %s' % (path.name, text[:m.start()].count('\n') + 1, cursor))
        self.assertEqual(offenders, [])

    def test_vanity_full_view_hides_the_interface_and_comes_back(self):
        # Maintainer request 2026-10-11: the vanity orbit shows the world alone, full screen (photo mode's view
        # without its notices); default on, saved, aw_vanity_fullview 0 keeps the HUD.
        view = (SRC / 'aw_view.c').read_text(encoding='utf-8')
        self.assertIn('static cvar_t fullview_cvar={"aw_vanity_fullview","1",true};', view)
        self.assertIn('Cvar_RegisterVariable(&fullview_cvar);', view)
        self.assertIn('aw_view_fullscreen=AW_ViewVanityFullscreen;', code('aw_view.c'))
        full = body(code('aw_view.c'), 'int AW_ViewVanityFullscreen')
        for part in ('owned', 'view.mode==AW_VIEW_VANITY', 'death.stage==AW_DEATH_NONE', 'fullview_cvar.value'):
            self.assertIn(part, full)
        screen = code('screen.c')
        # (and the hidden HUD, Ctrl+Alt+H: UI-HUD-TOGGLE-KEY-51)
        self.assertIn('return AW_PhotoModeActive () || (aw_view_fullscreen && aw_view_fullscreen ()) || aw_hud_hidden;',
                      body(screen, 'static int SCR_AWFullView'))
        calc = body(screen, 'static void SCR_CalcRefdef')
        self.assertIn('if (cl.intermission || SCR_AWFullView ())', calc)
        self.assertNotIn('AW_PhotoModeActive', calc)
        update = body(screen, 'void SCR_UpdateScreen')
        # the view size follows the orbit without a cvar change: entering and leaving recalculate the view
        self.assertIn('if (SCR_AWFullView () != scr_aw_full_view)', update)
        self.assertLess(update.index('scr_aw_full_view = SCR_AWFullView ();'), update.index('SCR_CalcRefdef ();'))
        self.assertIn('vanity = SCR_AWFullView () && !AW_PhotoModeActive ();', update)
        for draw in ('Sbar_Draw ();', 'AW_SceneDraw();', 'AW_UIDraw();', 'AW_GalleryDraw();', 'AW_UIOuterFrame();'):
            tail = update[update.index('vanity = SCR_AWFullView ()'):]
            guard = tail[:tail.index(draw)].rsplit('if (', 1)[1]
            self.assertIn('vanity', guard, draw)
        help_text = (ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8')
        self.assertIn('fullview on/off', help_text)
        self.assertIn('aw_vanity_fullview', (ROOT / 'docs/THIRD_PERSON.md').read_text(encoding='utf-8'))

    def test_vanity_full_view_changes_no_render_setting(self):
        # Maintainer 2026-10-11 14:39: "that does NOT mean you disable fog and such": only the interface hides and
        # the view grows; fog, lighting, sky, draw distance and noclip stay exactly as in play.
        view = code('aw_view.c')
        full = body(view, 'int AW_ViewVanityFullscreen')
        screen_full = body(code('screen.c'), 'static int SCR_AWFullView')
        for text in (full, screen_full):
            for setting in ('aw_fog', 'photomode', 'noclip', 'Cvar_Set', 'r_draw', 'aw_draw'):
                self.assertNotIn(setting, text)
        self.assertNotIn('Cvar_Set', body(view, 'void AW_ViewFrame').split('set_chase(AW_ViewBehind(&view));')[0]
                         .replace('Cvar_SetValue(view_cvar.name', '').replace('Cvar_SetValue(distance_cvar.name', ''))
        # photo mode keeps its own overrides; the orbit never enters photo mode
        self.assertNotIn('AW_PhotoModeSet', view)

    def test_the_game_screen_never_moves_and_clicks_carry_no_amiga_qualifier(self):
        # UI-MAP-CLICK-DRAGS-SCREEN-36: a click (map drags, right+left combos) with an Amiga qualifier, held or
        # latched by a crashed program, dragged the game screen down over the AmigaDOS screen.
        vid = code('vid_amiga.c')
        self.assertIn('SA_Draggable,   FALSE,', vid)
        sys_c = code('sys_amiga.c')
        mouse = body(sys_c, 'struct InputEvent *AW_InputGuardMouse')
        self.assertIn('IntuitionBase->FirstScreen==video_window->WScreen', mouse)
        self.assertIn('if(e->ie_Class==IECLASS_RAWMOUSE)e->ie_Qualifier&=~(IEQUALIFIER_LCOMMAND|IEQUALIFIER_RCOMMAND);', mouse)
        entry = sys_c[sys_c.index('_AW_InputGuardEntry:'):]
        self.assertLess(entry.index('jsr _AW_InputGuardMouse'), entry.index('jsr _AW_InputGuardEvents'))
        self.assertIn('move.l %d0,-(%sp)', entry[:entry.index('jsr _AW_InputGuardEvents')])

    def test_a_toggle_pov_tap_between_frames_still_switches(self):
        # CAMERA-POV-TAP-LOST-36: press and release before the next frame lost the switch.
        view = code('aw_view.c')
        self.assertIn('pov_down=pov_tapped=1;', view)
        frame = body(view, 'void AW_ViewFrame')
        self.assertIn('if(pov_tapped && !pov_down)AW_ViewPOVTap(&view,&rules);', frame)
        self.assertIn('pov_tapped', frame[frame.index('input=input_seen'):])
        self.assertIn('input_seen=pov_tapped=0;', frame)

    def test_default_bindings_toggle_pov_tab_and_wheel_zoom(self):
        keymaps = (ROOT / 'config/keymaps.cfg').read_text(encoding='utf-8')
        self.assertIn('bind "TAB" +aw_pov', keymaps)
        self.assertIn('bind "MWHEELUP" "aw_view_zoom 1"', keymaps)
        self.assertIn('bind "MWHEELDOWN" "aw_view_zoom -1"', keymaps)
        migrate = body(code('keys.c'), 'void AW_ControlsMigrate')
        self.assertIn('Key_SetBinding(K_TAB,"+aw_pov")', migrate)
        self.assertIn('Key_SetBinding(K_MWHEELUP,"aw_view_zoom 1")', migrate)
        view = code('aw_view.c')
        for command in ('"+aw_pov"', '"-aw_pov"', '"aw_view_zoom"', '"aw_camera"'):
            self.assertIn('Cmd_AddCommand(' + command, view)

    def test_console_aliases_and_docs(self):
        catalogue = (ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8')
        for word in ('camera', 'pov', 'thirdperson'):
            self.assertIn('VIDEO|' + word + '|aw_camera|', catalogue)
        # the engine reads catalogue lines of at most 383 characters (aw_console.c DEBUG_LINE)
        self.assertTrue(all(len(line) < 384 for line in catalogue.splitlines()))
        page = (ROOT / 'docs/AMIWIND_CONSOLE_COMMANDS.md').read_text(encoding='utf-8')
        self.assertIn('`dbg camera`', page)
        doc = (ROOT / 'docs/THIRD_PERSON.md').read_text(encoding='utf-8')
        for text in ('fVanityDelay', 'Tab', 'aw_death_retry', '--player-body', 'dbg camera'):
            self.assertIn(text, doc)

    def test_vanity_camera_command(self):
        view = code('aw_view.c')
        self.assertIn('Cmd_AddCommand("aw_vanitycam",vanity_command);', view)
        command = body(view, 'static void vanity_command(void)')
        for word in ('"on"', '"now"', '"auto"', '"off"', '"delay"', '"default"'):
            self.assertIn(word, command)
        self.assertIn('Cvar_SetValue(vanity_cvar.name,1)', command)      # auto = the original (aw_view_vanity 1)
        self.assertIn('Cvar_SetValue(vanity_cvar.name,0)', command)      # off (saved cvar)
        self.assertIn('vanity_start()', command)
        self.assertIn('rules.vanity_delay=d;', command)                  # test delay: the rules, not the cvar or file
        self.assertIn('rules.vanity_delay=vanity_delay_setting=v;', view)  # the game's own fVanityDelay is kept
        # an orbit started by hand runs also with the automatic orbit off, until any input
        self.assertIn('(vanity_cvar.value || vanity_forced) && body_ready()', view)
        self.assertIn('vanity_start();', body(view, 'static void command(void)'))   # dbg camera vanity now stays
        # console keys are not play input (the orbit started from the console survives closing it)
        self.assertIn('if(down && key_dest==key_game)input_seen=1;', body(view, 'void AW_ViewInput'))
        catalogue = (ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8')
        self.assertIn('VIDEO|vanitycamera|aw_vanitycam|', catalogue)
        self.assertIn('VIDEO|vanitycam|aw_vanitycam|same as vanitycamera', catalogue)
        self.assertIn('`dbg vanitycamera`', (ROOT / 'docs/THIRD_PERSON.md').read_text(encoding='utf-8'))

    def test_one_fight_check_for_battle_music_and_waiting(self):
        """WAIT-DURING-COMBAT-36: the battle music and the wait refusal ask the same AW_PlayerInCombat()."""
        combat = code('aw_combat.c')
        self.assertIn('int AW_PlayerInCombat(void) {return AW_CombatHostiles()>0 && !you.dead;}', combat)
        self.assertIn('int want=AW_PlayerInCombat();', body(combat, 'void AW_CombatPhysics'))
        wait = code('aw_wait.c')
        self.assertIn('if(AW_PlayerInCombat()){enemies_notice();return;}', body(wait, 'static void wait_open'))
        self.assertIn('AW_PlayerInCombat()){close_modal();return 1;}', wait)
        self.assertIn('"sNotifyMessage2 "', body(wait, 'static void enemies_notice'))
        import prepare_player_view
        self.assertIn('sNotifyMessage2', prepare_player_view.STRINGS)

    def test_death_scene_music_retry_and_choices(self):
        view = code('aw_view.c')
        begin = body(view, 'static void begin_death')
        self.assertIn('if(!AW_CombatDeathMusicPlayed())AW_MusicDeath();', begin)
        self.assertIn('AW_CombatRetryAvailable()', begin)
        self.assertIn('retry_cvar.value', begin)
        self.assertIn('AW_SaveLatest(', begin)
        choose = body(view, 'static void choose')
        self.assertIn('AW_CombatRetry()', choose)
        self.assertIn('AW_SaveRead(AW_SaveProfile(),save_slot)', choose)
        self.assertIn('"disconnect\\naw_main_menu\\n"', choose)
        self.assertIn('static cvar_t retry_cvar={"aw_death_retry","1"};', (SRC / 'aw_view.c').read_text(encoding='utf-8'))


class DeadPlayerShowsAndDoesNothing(unittest.TestCase):
    """Project rule (PLAYER-DEATH-LIMBO-35): dead in a fight, you cannot talk to anyone or interact, and no names or
    hints show. One predicate (quakedef.h AW_PlayerDead) that every such path asks."""

    def test_one_predicate_behind_the_input_lock(self):
        quake = (SRC / 'quakedef.h').read_text(encoding='utf-8')
        self.assertIn('static inline int AW_PlayerDead(void)', quake)
        self.assertIn('svs.clients[0].edict->v.health<=0', body(quake, 'static inline int AW_PlayerDead'))
        self.assertIn('AW_PlayerDead()', body(code('aw_view.c'), 'int AW_DeathLocked'))
        self.assertIn('AW_UISubtitle("","",0);', body(code('aw_view.c'), 'static void begin_death'))

    def test_no_name_no_hint_no_prompt_no_use(self):
        scene = code('aw_scene.c')
        self.assertIn('AW_PlayerDead()', body(scene, 'const char *AW_SceneTargetName(void)'))   # names, driver, harvest
        self.assertIn('AW_PlayerDead()', body(scene, 'void AW_SceneDraw(void)'))              # door/opening/NPC prompts
        use = body(scene, 'int AW_SceneUse(void)')
        self.assertLess(use.index('AW_PlayerDead()'), use.index('travel_use()'))               # before any use
        self.assertLess(use.index('AW_PlayerDead()'), use.index('AW_HarvestUse()'))
        # E, attack, jump and impulses (talk to NPCs: impulse 201) go through the input lock
        intro = code('aw_intro.c')
        for name in ('int AW_IntroButtons(', 'int AW_IntroImpulse(', 'void AW_IntroMove('):
            self.assertIn('dead_locked()', body(intro, name), name)

    def test_no_crosshair_no_enemy_bar_no_pick(self):
        view = code('view.c')
        draw = view[view.index('AW_TorchDraw ();'):]
        # dead (or the HUD hidden, or an orbit: PHOTO-CROSSHAIR-51) = no crosshair and no inspect mark
        self.assertIn('int clean = AW_PlayerDead () || aw_hud_hidden || (aw_view_orbiting && aw_view_orbiting ());',
                      draw[:900])
        self.assertIn('if (inspect && !clean && crosshair.value)', draw[:1200])
        self.assertIn('if (!clean && !chase_active.value)', draw[:1400])
        self.assertIn('AW_PlayerDead()', body(code('aw_combat.c'), 'int AW_CombatEnemyBar'))
        self.assertIn('AW_PlayerDead()', body(code('aw_combat.c'), 'static void alt_down'))
        self.assertIn('AW_PlayerDead()', body(code('aw_companion.c'), 'static edict_t *pick_target'))

    def test_no_greeting_no_voice_line(self):
        self.assertIn('if(AW_PlayerDead())return 0;', body(code('aw_anim.c'), 'int AW_VoiceSay'))
        qc = (ROOT / 'engine/aga/qc/world.qc').read_text(encoding='utf-8')
        # the automatic greeting (QuakeC) skips a dead player, as OpenMW Actors::updateGreetingState
        self.assertIn('aw_player.health <= 0', qc[qc.index('void() aw_npc_idle'):qc.index('float(entity actor) aw_npcfloor')])


class PlayerViewBuilderTests(unittest.TestCase):
    def kinds(self):
        def fields(**values):
            return list(values.items())
        gmst = {
            'fvanitydelay': [('NAME', b'fVanityDelay'), ('FLTV', struct.pack('<f', 30.0))],
            'sloadlastsavemsg': [('NAME', b'sLoadLastSaveMsg'),
                                 ('STRV', b"The most recent Save Game is '%s'. \nWould you like to load it?")],
            'syes': [('NAME', b'sYes'), ('STRV', b'Yes')],
            'sno': [('NAME', b'sNo'), ('STRV', b'No')],
            'snotifymessage2': [('NAME', b'sNotifyMessage2'), ('STRV', b'Test: enemies near.')],
        }
        playable = struct.pack('<4fI', 1, 1, 1, 1, 1)
        races = {'dark elf': [('RADT', b'\0' * 120 + playable)], 'nopc': [('RADT', b'\0' * 120 + struct.pack('<4fI', 1, 1, 1, 1, 0))]}
        bodyparts = {
            'b_n_dark elf_m_head_02': [('BYDT', bytes((0, 0, 0, 0))), ('FNAM', b'Dark Elf\0')],
            'b_n_dark elf_m_head_01': [('BYDT', bytes((0, 0, 0, 0))), ('FNAM', b'Dark Elf\0')],
            'b_n_dark elf_f_head_01': [('BYDT', bytes((0, 0, 1, 0))), ('FNAM', b'Dark Elf\0')],
            'b_v_dark elf_m_head_01': [('BYDT', bytes((0, 1, 0, 0))), ('FNAM', b'Dark Elf\0')],
        }
        return {'GMST': gmst, 'RACE': races, 'BODY': bodyparts, 'NPC_': {}}

    def test_settings_from_the_master(self):
        import prepare_player_view as v
        text = v.settings_text(self.kinds())
        self.assertEqual(text.splitlines(), ['AWVS1', 'fVanityDelay 30',
                                             "sLoadLastSaveMsg The most recent Save Game is '%s'. \\nWould you like to load it?",
                                             'sYes Yes', 'sNo No', 'sNotifyMessage2 Test: enemies near.'])
        bad = self.kinds()
        bad['GMST']['sloadlastsavemsg'] = [('STRV', b'No placeholder')]
        with self.assertRaises(ValueError):
            v.settings_text(bad)
        missing = self.kinds()
        del missing['GMST']['fvanitydelay']
        with self.assertRaises(ValueError):
            v.settings_text(missing)

    def test_races_paths_heads_and_catalogue(self):
        import prepare_player_view as v
        kinds = self.kinds()
        self.assertEqual(v.playable_races(kinds), ['dark elf'])
        self.assertEqual(v.body_path('dark elf', False), 'progs/body/dark_elf_m.mdl')
        self.assertEqual(v.body_path('Khajiit', True), 'progs/body/khajiit_f.mdl')
        self.assertTrue(all(len(Path(v.body_path(r, f)).name) <= 30 for r in ('dark elf', 'high elf', 'redguard') for f in (0, 1)))
        self.assertEqual(v.first_part(kinds, 'dark elf', False, 0), 'b_n_dark elf_m_head_01')   # first by ID, no vampire
        self.assertEqual(v.first_part(kinds, 'dark elf', True, 0), 'b_n_dark elf_f_head_01')
        self.assertIsNone(v.first_part(kinds, 'dark elf', False, 1))
        text = v.bodies_text([('dark elf', False, 'progs/body/dark_elf_m.mdl'), ('dark elf', True, 'progs/body/dark_elf_f.mdl')])
        self.assertEqual(text, 'AWPB1\ndark elf\t0\tprogs/body/dark_elf_m.mdl\ndark elf\t1\tprogs/body/dark_elf_f.mdl\n')
        with self.assertRaises(ValueError):
            v.bodies_text([('dark elf', False, 'a.mdl'), ('dark elf', False, 'b.mdl')])

    def test_switches_default_on_and_image_arguments_only_when_off(self):
        import prepare_player_view as v
        on = v.configure(SimpleNamespace(player_body=None, death_retry=None))
        self.assertEqual(on, {'player_body': True, 'death_retry': True, 'source': 'default'})
        self.assertEqual(v.image_arguments(on), [])
        off = v.configure(SimpleNamespace(player_body='off', death_retry='off'))
        self.assertEqual(v.image_arguments(off), ['--no-player-body', '--no-death-retry'])
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'default-game.cfg').write_bytes(b'aw_world_bounds 1')
            self.assertEqual(v.stage_death_retry(False, tmp), {'on': True})
            self.assertEqual((Path(tmp) / 'default-game.cfg').read_bytes(), b'aw_world_bounds 1')
            record = v.stage_death_retry(True, tmp)
            self.assertFalse(record['on'])
            self.assertTrue((Path(tmp) / 'default-game.cfg').read_bytes().endswith(b'\naw_death_retry 0\n'))

    def test_builder_wiring(self):
        image = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn("view_job=Background(prepare_player_view_image,args.data_files,boot/'id1',jobs,\n"
                      "                        not getattr(args,'no_player_body',False),jobs=jobs)", image)
        self.assertIn("i.add_argument('--no-player-body'", image)
        self.assertIn("i.add_argument('--no-death-retry'", image)
        build = (ROOT / 'tools/build.py').read_text(encoding='utf-8')
        self.assertIn('add_player_view_options(p)', build)
        self.assertIn("args.player_view_record = __import__('prepare_player_view').configure(args)", build)
        files = (ROOT / 'tools/release-files.json').read_text(encoding='utf-8')
        for name in ('tools/prepare_player_view.py', 'engine/aga/src/aw_view.c', 'engine/aga/src/aw_view_rules.c',
                     'engine/aga/src/aw_view.h', 'tests/aga_view_test.c', 'tests/test_third_person.py',
                     'docs/THIRD_PERSON.md'):
            self.assertIn('"' + name + '"', files)


class PlayerBodyBudgetTests(unittest.TestCase):
    """Small synthetic geometry; the real byte fitter runs at a controlled test limit."""
    def groups(self):
        groups, base = [], 0
        for name, count, kind in (('idle', 8, 'loop'), ('walk', 6, 'loop'),
                                  ('jump', 4, 'hold'), ('land', 4, 'hold')):
            groups.append(dict(name=name, count=count, kind=kind, base=base, step=0.1, events=[]))
            base += count
        return groups

    def mesh(self, vertices):
        import numpy as np
        return (np.zeros((22, vertices, 3)), np.array([[0, 1, 2]]),
                np.zeros((vertices, 2)), SimpleNamespace(size=(128, 128)))

    def fit(self, attempts, byte_limit):
        import npc_anim as anim
        import prepare_player_view as view
        real_fit = anim.fit
        def limited_fit(groups, nv, nt, sw, sh):
            return real_fit(groups, nv, nt, sw, sh, budget=byte_limit)
        source = iter(attempts)
        def labeled_bake(*args, **kwargs):
            result = next(source)
            if isinstance(result, Exception):
                raise result
            kwargs['face_parts'].extend([17] * len(result[1]))
            return result
        with patch('npc_geometry.bake', side_effect=labeled_bake) as bake, \
             patch('npc_anim.fit', side_effect=limited_fit):
            result = view._fit_body('synthetic body', [], [], [], b'', self.groups())
        budget, frames, faces, _, skin, groups, index = result
        self.assertLessEqual(anim.alias_bytes(len(index), frames.shape[1], len(faces), *skin.size), byte_limit)
        self.assertEqual(frames[index].shape[0], sum(g['count'] for g in groups))
        self.assertEqual([g['count'] for g in groups if g['name'] == 'idle'], [8])
        self.assertTrue(all(g['count'] >= 2 for g in groups if g['name'] in ('jump', 'land')))
        return budget, groups, bake

    def test_minimum_frames_overflow_tries_smaller_mesh_and_stops_at_full_fit(self):
        import prepare_player_view as view
        budget, groups, bake = self.fit([self.mesh(600), self.mesh(100)], 48 * 1024)
        self.assertEqual(budget, view.BUDGETS[1])
        self.assertEqual([g['count'] for g in groups], [8, 6, 4, 4])
        self.assertEqual([c.kwargs['budget'] for c in bake.call_args_list], list(view.BUDGETS[:2]))

    def test_reduced_fit_keeps_searching_for_full_action_sampling(self):
        import prepare_player_view as view
        budget, groups, bake = self.fit([self.mesh(600), self.mesh(100)], 64 * 1024)
        self.assertEqual(budget, view.BUDGETS[1])
        self.assertEqual([g['count'] for g in groups], [8, 6, 4, 4])
        self.assertEqual(bake.call_count, 2)

    def test_valid_reduced_fit_survives_all_later_geometry_failures(self):
        from npc_geometry import AliasOverflow
        import prepare_player_view as view
        attempts = [self.mesh(600)] + [AliasOverflow('Alias vertex budget exceeded')] * 15
        budget, groups, bake = self.fit(attempts, 64 * 1024)
        self.assertEqual(budget, view.BUDGETS[0])
        self.assertLess(sum(g['count'] for g in groups), 22)
        self.assertEqual(bake.call_count, 4 * len(view.BUDGETS))

    def test_fallback_keeps_more_animation_samples_then_first_equal_fit(self):
        from npc_geometry import AliasOverflow
        import prepare_player_view as view
        attempts = [self.mesh(600), self.mesh(550), self.mesh(550)]
        attempts += [AliasOverflow('Alias vertex budget exceeded')] * 13
        budget, groups, bake = self.fit(attempts, 64 * 1024)
        self.assertEqual(budget, view.BUDGETS[1])
        self.assertEqual(sum(g['count'] for g in groups), 19)
        self.assertEqual(bake.call_count, 4 * len(view.BUDGETS))

    def test_leg_section_guard_checks_union_not_hidden_fragment(self):
        import numpy as np
        from npc_geometry import player_leg_section_ok
        points = np.array([[x, y, z] for z in (0., 1.) for x, y in
                           ((-2., -1.), (-1., -1.), (-1., 1.), (-2., 1.))])
        faces = np.array([[0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5],
                          [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]])
        right = points.copy(); right[:, 0] += 3
        hidden = points.copy(); hidden[:, 0] = -1.4 + .1 * (hidden[:, 0] + 2)
        # A complete mesh keeps the visible outer trouser outline even when
        # an inner fragment is reduced. The validator sees the complete union.
        def joined(*meshes):
            return np.concatenate(meshes), np.concatenate([faces + 8 * i for i in range(len(meshes))])
        original, original_faces = joined(points, right, hidden)
        self.assertTrue(player_leg_section_ok(original, original_faces, original, original_faces))
        # The inner fragment can collapse without changing the outer outline.
        collapsed = hidden.copy(); collapsed[:, 0] = -1.45
        candidate, candidate_faces = joined(points, right, collapsed)
        self.assertTrue(player_leg_section_ok(original, original_faces, candidate, candidate_faces))
        thin = points.copy(); thin[:, 0] = -1.5 + .6 * (thin[:, 0] + 1.5)
        candidate, candidate_faces = joined(thin, right, collapsed)
        self.assertFalse(player_leg_section_ok(original, original_faces, candidate, candidate_faces))

    def test_leg_guard_ignores_tail_but_still_catches_narrowed_leg(self):
        import numpy as np
        from npc_geometry import player_leg_section_ok
        cube = np.array([[x,y,z] for z in (0.,1.) for x,y in
                         ((-2.,-1.),(-1.,-1.),(-1.,1.),(-2.,1.))])
        quads = np.array([[0,1,5],[0,5,4],[1,2,6],[1,6,5],
                          [2,3,7],[2,7,6],[3,0,4],[3,4,7]])
        right=cube.copy();right[:,0]+=3
        tail=cube.copy();tail[:,1]-=5
        def joined(left, tailpiece):
            return (np.concatenate((left,right,tailpiece)),
                    np.concatenate((quads,quads+8,quads+16)))
        original,faces=joined(cube,tail)
        tailgone=tail.copy();tailgone[:,1]+=4
        candidate,candidate_faces=joined(cube,tailgone)
        labels=np.array([17]*8+[22]*8+[26]*8)
        self.assertTrue(player_leg_section_ok(original,faces,candidate,candidate_faces,
            reference_parts=labels,candidate_parts=labels))
        thin=cube.copy();thin[:,0]=-1.5+.6*(thin[:,0]+1.5)
        candidate,candidate_faces=joined(thin,tailgone)
        self.assertFalse(player_leg_section_ok(original,faces,candidate,candidate_faces,
            reference_parts=labels,candidate_parts=labels))

    def test_vertex_overflow_also_retries_a_smaller_mesh(self):
        from npc_geometry import AliasOverflow
        import prepare_player_view as view
        budget, _, bake = self.fit([AliasOverflow('Alias vertex budget exceeded'), self.mesh(100)], 48 * 1024)
        self.assertEqual(budget, view.BUDGETS[1])
        self.assertEqual(bake.call_count, 2)

    def test_compact_contour_fallback_only_after_plain_paths_fail(self):
        from npc_geometry import AliasOverflow
        import prepare_player_view as view
        unavailable = AliasOverflow('Player visible leg silhouette narrowed')
        attempts = [self.mesh(600)] + [unavailable] * (2 * len(view.BUDGETS) - 1)
        attempts += [unavailable, self.mesh(100)]
        budget, groups, bake = self.fit(attempts, 48 * 1024)
        self.assertEqual(budget, view.BUDGETS[1])
        self.assertEqual(bake.call_count, 2 * len(view.BUDGETS) + 2)
        self.assertTrue(bake.call_args.kwargs['body_leg_contour'])
        self.assertEqual(bake.call_args.kwargs['body_skin_rows'], 80)
        self.assertEqual([g['count'] for g in groups], [8, 6, 4, 4])

    def test_upper_thigh_fallback_runs_only_after_knee_path_fails(self):
        from npc_geometry import AliasOverflow
        import prepare_player_view as view
        unavailable=AliasOverflow('Player visible leg silhouette narrowed')
        attempts=[self.mesh(600)]+[unavailable]*(3*len(view.BUDGETS)-1)
        attempts += [unavailable,self.mesh(100)]
        budget,_,bake=self.fit(attempts,48*1024)
        self.assertEqual(budget,view.BUDGETS[1])
        self.assertEqual(bake.call_count,3*len(view.BUDGETS)+2)
        self.assertEqual(bake.call_args.kwargs['body_leg_contour'],2)

    def test_all_budget_failures_report_appearance_and_attempts(self):
        import npc_anim as anim
        import prepare_player_view as view
        real_fit = anim.fit
        def labeled_bake(*args, **kwargs):
            result=self.mesh(600)
            kwargs['face_parts'].extend([17] * len(result[1]))
            return result
        with patch('npc_geometry.bake', side_effect=labeled_bake) as bake, \
             patch('npc_anim.fit', side_effect=lambda *args: real_fit(*args, budget=48 * 1024)), \
             patch.dict('os.environ', {'AMIWIND_NPC_HEAD_REDUCER': 'default', 'AMIWIND_NPC_HAIR_SHARE': 'plain'}):
            with self.assertRaisesRegex(ValueError, 'synthetic body: no body fits') as caught:
                view._fit_body('synthetic body', [], [], [], b'', self.groups())
        self.assertEqual(bake.call_count, 4 * len(view.BUDGETS))
        for budget in view.BUDGETS:
            self.assertIn('%d/96/plain: Alias byte budget exceeded' % budget, str(caught.exception))
        self.assertEqual([c.kwargs['body_skin_rows'] for c in bake.call_args_list],
                         [96] * len(view.BUDGETS) + [80] * (3 * len(view.BUDGETS)))
        self.assertEqual([c.kwargs['body_leg_contour'] for c in bake.call_args_list],
                         [0] * (2 * len(view.BUDGETS)) + [1] * len(view.BUDGETS) +
                         [2] * len(view.BUDGETS))

    def test_locked_head_reducer_falls_back_to_the_previous_reducer(self):
        """NPC-HEAD-DECIMATION-33 (v0.0.44-dev1 image step): when no body fits with the locked head reducer, the
        whole search runs again with the previous head reducer, and the environment is restored afterwards."""
        import os
        import prepare_player_view as view
        seen = []
        def search(*args):
            seen.append(os.environ.get('AMIWIND_NPC_HEAD_REDUCER'))
            if len(seen) == 1:
                raise ValueError('synthetic body: no body fits the existing budgets (480/96/plain: over)')
            return 'fitted'
        # the hair share's own fallback (NPC-HAIR-BACK-MISSING-53) runs first unless the share is the previous one
        with patch.object(view, '_fit_body_search', side_effect=search), \
             patch.dict('os.environ', {'AMIWIND_NPC_HEAD_REDUCER': 'locked', 'AMIWIND_NPC_HAIR_SHARE': 'plain'}):
            self.assertEqual(view._fit_body('synthetic body', [], [], [], b'', self.groups()), 'fitted')
            self.assertEqual(os.environ['AMIWIND_NPC_HEAD_REDUCER'], 'locked')
        self.assertEqual(seen, ['locked', 'default'])
        with patch.object(view, '_fit_body_search', side_effect=ValueError('synthetic body: malformed source')), \
             patch.dict('os.environ', {'AMIWIND_NPC_HEAD_REDUCER': 'locked'}):
            with self.assertRaisesRegex(ValueError, 'malformed source'):
                view._fit_body('synthetic body', [], [], [], b'', self.groups())

    def test_unrelated_geometry_error_aborts_before_a_later_fit(self):
        import npc_anim as anim
        import prepare_player_view as view
        real_fit = anim.fit
        with patch('npc_geometry.bake', side_effect=[ValueError('malformed source'), self.mesh(600)]) as bake, \
             patch('npc_anim.fit', side_effect=lambda *args: real_fit(*args, budget=64 * 1024)):
            with self.assertRaisesRegex(ValueError, 'synthetic body: malformed source'):
                view._fit_body('synthetic body', [], [], [], b'', self.groups())
        self.assertEqual(bake.call_count, 1)


class PlayerTorchDataTests(unittest.TestCase):
    def test_paths_and_frame_aligned_fixed_point_emitters(self):
        import numpy as np
        import prepare_player_view as view
        self.assertEqual(view.torch_paths('progs/body/nord_m.mdl'),
                         ('progs/body/nord_m_t.mdl', 'progs/body/nord_m_h.mdl',
                          'progs/body/nord_m_t.awt'))
        raw = view.torch_emitters([[1.25, -2.5, 0], [0, 3, 127.5]])
        self.assertEqual(raw[:8], struct.pack('>4sHH', b'AWBT', 2, 0))
        self.assertEqual(len(raw), 8 + 2 * 12)
        self.assertEqual(np.frombuffer(raw[8:], dtype='>i4').reshape(-1, 3).tolist(),
                         [[81920, -163840, 0], [0, 196608, 8355840]])

    def test_emitter_bounds_are_rejected_before_pack(self):
        import prepare_player_view as view
        for points in ([], [[float('nan'), 0, 0]], [[129, 0, 0]], [[0, 0]],
                       [[0, 0, 0]] * 257):
            with self.subTest(points=len(points)), self.assertRaises(ValueError):
                view.torch_emitters(points)


class PlayerSwimDataTests(unittest.TestCase):
    def test_water_alias_path_and_full_original_groups(self):
        import prepare_player_view as view
        self.assertEqual(view.swim_path('progs/body/nord_m.mdl'), 'progs/body/nord_m_w.mdl')
        self.assertEqual(view.BODY_SWIM, (('idle', 8), ('swimidle', 8), ('swim', 8), ('death', 2)))
        for invalid in ('progs/other/nord_m.mdl', 'progs/body/nord_m.anm'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                view.swim_path(invalid)


if __name__ == '__main__':
    unittest.main()
