# SPDX-License-Identifier: GPL-3.0-only
"""Photo mode (dbg photomode / dbg killhud) and the crosshair preference:
source contracts for the parts the native fixtures do not compile (screen.c,
host.c, view.c), the shipped defaults and the key bindings. The behaviour is
exercised by tests/aga_photo_test.c, aga_menu_test.c and aga_keymap_test.c."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'


def source(name):
    text = (SRC / name).read_text(encoding='utf-8')
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)


def body(text, name):
    start = re.search(r'\b' + name + r'\s*\([^;{}]*\)\s*\{', text).end()
    depth = 1
    for end in range(start, len(text)):
        depth += (text[end] == '{') - (text[end] == '}')
        if not depth:
            return text[start:end]
    raise AssertionError('unclosed function: ' + name)


class PhotoModeSourceTests(unittest.TestCase):
    def test_full_screen_view_uses_the_intermission_size(self):
        calc = body(source('screen.c'), 'SCR_CalcRefdef')
        self.assertRegex(calc, r'if \(cl\.intermission \|\| AW_PhotoModeActive\(\)\)\s*size = 120;')
        # Neither the reserved HUD strip nor the coordinate strip shrinks the view.
        self.assertIn('!cl.intermission && !AW_PhotoModeActive() && sb_lines < 48', calc)
        self.assertIn('AW_DebugCoordsEnabled() && !AW_PhotoModeActive() && sb_lines < 12', calc)

    def test_prompts_names_subtitles_and_pause_are_skipped_and_notice_drawn(self):
        update = body(source('screen.c'), 'SCR_UpdateScreen')
        self.assertRegex(update, r'if \(!AW_PhotoModeActive\(\)\)\s*SCR_DrawPause \(\);')
        self.assertRegex(update, r'if \(!AW_PhotoModeActive\(\)\)\s*AW_SceneDraw\(\);')
        # PHOTO-GALLERY-TEXT-33: test-room and gallery instruction text is hidden.
        self.assertRegex(update, r'if \(!AW_PhotoModeActive\(\)\)\s*AW_GalleryDraw\(\);')
        # The message box is drawn in photo mode only for photo mode's own notice.
        self.assertRegex(update, r'if \(!AW_PhotoModeActive\(\) \|\| AW_PhotoNoticeShowing\(\)\)\s*AW_UIDraw\(\);')
        self.assertLess(update.index('AW_PhotoDraw ()'), update.index('SCR_CheckDrawCenterString ();\n        Sbar_Draw ();'))
        # Notices use AmiWind's message box (the Wait refusal's), not a centre print.
        photo = source('aw_photo.c')
        self.assertIn('AW_UISubtitle("",text,seconds);', body(photo, 'show'))
        self.assertNotIn('CenterPrint', photo)
        self.assertNotIn('SCR_ClassicCenterPrint', source('screen.c'))
        self.assertIn('if(AW_PhotoModeActive() && h<72)h=72;', body(source('aw_ui.c'), 'AW_UIDraw'))
        # Game messages still go to subtitles; the original Quake body is kept.
        self.assertIn('AW_UICenterMessage(str);', body(source('screen.c'), 'SCR_CenterPrint'))

    def test_config_is_written_with_pre_photo_settings(self):
        shutdown = body(source('host.c'), 'Host_Shutdown')
        self.assertLess(shutdown.index('AW_PhotoConfigRestore ();'), shutdown.index('Host_WriteConfiguration ();'))

    def test_crosshair_is_quakes_saved_cvar_and_on_by_default(self):
        self.assertIn('cvar_t\tcrosshair = {"crosshair", "0", true};', (SRC / 'view.c').read_text(encoding='utf-8'))
        self.assertIn('if (crosshair.value)', source('view.c'))
        self.assertRegex((ROOT / 'tools' / 'prepare_quake.py').read_text(encoding='utf-8'), r'\ncrosshair 1\n')
        photo = source('aw_photo.c')
        self.assertIn('"crosshair"', photo)
        self.assertIn('Cvar_SetValue("crosshair"', photo)

    def test_photo_mode_switches_and_saved_settings(self):
        photo = source('aw_photo.c')
        self.assertIn('{"aw_photomode_nofog","1",true}', photo)
        self.assertIn('{"aw_photomode_noclip","1",true}', photo)
        self.assertIn('{"aw_photomode_hands","0",true}', photo)
        for name in ('crosshair', 'aw_fog', '_aw_debug_all', '_aw_debug_coords', 'aw_ui_hud', 'aw_compass', 'aw_ui_frame',
                     'r_drawviewmodel'):
            self.assertIn('"%s"' % name, body(photo, 'enter') + photo[:photo.index('static char saved_values')])
        # Every saved name is a setting the engine registers.
        registered = set()
        for f in SRC.glob('*.c'):
            registered.update(re.findall(r'cvar_t\s+\w+\s*=\s*\{\s*"([^"]+)"', f.read_text(encoding='latin-1')))
        for name in ('crosshair', 'aw_fog', '_aw_debug_all', '_aw_debug_coords', 'aw_ui_hud', 'aw_compass', 'aw_ui_frame',
                     'r_drawviewmodel'):
            self.assertIn(name, registered)
        # Hiding the hands model leaves the torch's eye light: the light does not read r_drawviewmodel.
        torch = source('aw_torch.c')
        self.assertNotIn('r_drawviewmodel', body(torch, 'AW_TorchUpdate'))
        self.assertIn('!r_drawviewmodel.value', body(torch, 'AW_TorchDraw'))
        self.assertIn('if (!r_drawviewmodel.value', body(source('r_main.c'), 'R_DrawViewModel'))
        # Ctrl+H is dbg hud itself, not a second overlay.
        self.assertIn('amiwind_show_debug 1', photo)

    def test_debug_strip_spans_the_full_width_in_photo_mode(self):
        # PHOTO-DEBUG-STRIP-33
        draw = body(source('aw_hud.c'), 'Sbar_Draw')
        self.assertIn('if(AW_PhotoModeActive())Draw_Fill(0,vid.height-18,vid.width,18,255);', draw)
        self.assertIn('else if(!AW_PhotoModeActive())AW_SmallString(92,vid.height-8,"WASD / F10 console");', draw)

    def test_light_gallery_strip_hidden_unless_debug_hud(self):
        draw = body(source('aw_hud.c'), 'Sbar_Draw')
        self.assertIn('if((!AW_PhotoModeActive() || AW_DebugOverlaysEnabled()) && AW_LightGalleryDraw())return;', draw)
        # Its keys do not depend on drawing.
        self.assertNotIn('AW_PhotoModeActive', body(source('aw_wait.c'), 'AW_WaitKey'))

    def test_bindings_f10_console_f_hands_and_photo_keys_before_bindings(self):
        keymaps = (ROOT / 'config' / 'keymaps.cfg').read_text(encoding='utf-8')
        self.assertIn('bind "F10" toggleconsole', keymaps)
        self.assertIn('bind "f" "impulse 202"', keymaps)
        self.assertIn('bind "CTRL" +aw_fastflight', keymaps)
        self.assertNotRegex(keymaps.lower(), r'bind "?(h|ctrl\+f|ctrl\+h)"? ')
        event = body(source('keys.c'), 'Key_Event')
        console = event.index("key == '`' || key == K_F10")
        photo = event.index('keydown[K_CTRL] && AW_PhotoKey(key)')
        self.assertLess(console, photo)
        self.assertLess(photo, event.index('AW_GalleryKey('))

    def test_console_opening_reminds_and_init_registers(self):
        self.assertIn('AW_PhotoConsoleReminder();', body(source('console.c'), 'Con_ToggleConsole_f'))
        self.assertIn('AW_PhotoInit();', body(source('aw_debug.c'), 'AW_DebugInit'))
        self.assertIn('aw_photo.c', (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8'))

    def test_catalogue_names_and_docs(self):
        catalogue = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        for words, handler in (('photomode', 'aw_photomode'), ('killhud', 'aw_photomode'),
                               ('crosshair', 'aw_crosshair'), ('crosshairs', 'aw_crosshair')):
            self.assertRegex(catalogue, r'\n[A-Z /]+\|%s\|%s\|' % (words, handler))
        keymaps_doc = (ROOT / 'docs' / 'KEYMAPS.md').read_text(encoding='utf-8')
        for text in ('Ctrl+F', 'Ctrl+H', 'dbg photomode', 'Show crosshairs'):
            self.assertIn(text, keymaps_doc)


if __name__ == '__main__':
    unittest.main()
