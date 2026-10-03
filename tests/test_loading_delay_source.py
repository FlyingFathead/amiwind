"""Source contracts and extracted timer predicates; no compiler or game data.

These checks do not execute the engine. Real UI/mixer regression cases live in
aga_ui_test.c and aga_loading_audio_test.c for the existing Linux C harness.
"""
import ast
import math
from pathlib import Path
import re
import unittest

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


def predicate(expression, **values):
    """Evaluate only the arithmetic/comparison subset extracted from source."""
    expression = expression.replace('&&', ' and ').replace('||', ' or ')
    expression = re.sub(r'!(?!=)', ' not ', expression).strip()
    tree = ast.parse(expression, mode='eval')
    allowed = (ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp,
               ast.Not, ast.USub, ast.BinOp, ast.Sub, ast.Add, ast.Compare,
               ast.Gt, ast.GtE, ast.Lt, ast.LtE, ast.Eq, ast.NotEq,
               ast.Name, ast.Load, ast.Constant)
    if any(not isinstance(node, allowed) for node in ast.walk(tree)):
        raise AssertionError('unsupported timer predicate: ' + expression)
    return eval(compile(tree, '<production timer predicate>', 'eval'),
                {'__builtins__': {}}, values)


class LoadingDelaySourceTests(unittest.TestCase):
    def test_archived_default_and_config_seconds(self):
        ui = source('aw_ui.c')
        self.assertRegex(ui, r'region_loading_delay\s*=\s*\{\s*"aw_region_loading_delay","2",true\s*\}')
        self.assertIn('Cvar_RegisterVariable(&region_loading_delay)', body(ui, 'AW_UIInit'))
        config = (ROOT / 'config/game.cfg').read_text(encoding='utf-8')
        self.assertRegex(config, r'(?m)^aw_region_loading_delay 2$')
        self.assertIn('0 = instantly; 2 = after two seconds', config)

    def test_extracted_clamps_are_finite_and_bounded(self):
        clamp = body(source('aw_ui.c'), 'AW_SetNextLoadingDelay')
        statements = re.findall(r'if\((.*?)\)seconds=([0-9.]+);', clamp)
        self.assertEqual(len(statements), 2)
        for supplied, expected in ((0, 0), (2, 2), (.25, .25), (-1, 0),
                                   (float('nan'), 0), (float('-inf'), 0),
                                   (60, 60), (1000, 60), (float('inf'), 60)):
            seconds = supplied
            for expression, result in statements:
                if predicate(expression, seconds=seconds):
                    seconds = float(result)
            self.assertEqual(seconds, expected)
            self.assertTrue(math.isfinite(seconds))

    def test_extracted_deadline_is_elapsed_real_time(self):
        timer = body(source('aw_ui.c'), 'AW_LoadingDelayExpired')
        self.assertLess(timer.index('if(!AW_LoadingDelayed())return 0;'), timer.index('Sys_FloatTime()'))
        expression = re.search(r'if\((now.*?)\)return 0;', timer).group(1)
        for elapsed, waiting in ((0, True), (1.999, True), (2, False), (2.001, False)):
            self.assertEqual(predicate(expression, now=10+elapsed,
                                       loading_started=10, loading_delay=2), waiting)
        self.assertIn('loading_delay=0;return 1;', timer)
        self.assertNotIn('realtime', timer)
        self.assertNotIn('host_frametime', timer)

    def test_reconnect_does_not_rearm_and_end_clears_pending_override(self):
        ui = source('aw_ui.c')
        begin = body(ui, 'AW_BeginLoadingStyle')
        self.assertLess(begin.index('if(loading_active)return;'), begin.index('loading_started='))
        self.assertIn('loading_delay=next_loading_delay;next_loading_delay=0;', begin)
        end = body(ui, 'AW_EndLoadingStyle')
        self.assertIn('loading_delay=loading_started=next_loading_delay=0;', end)
        self.assertIn('loading_region=next_loading_region=0;', end)
        self.assertIn('next_loading_style=-1;', end)
        self.assertIn('AW_EndLoadingStyle();', body(source('screen.c'), 'SCR_EndLoadingPlaque'))
        self.assertIn('SCR_EndLoadingPlaque', body(source('host.c'), 'Host_Error'))

    def test_only_accepted_automatic_crossings_arm_the_delay(self):
        scene = source('aw_scene.c')
        load = body(scene, 'load_scene')
        self.assertLess(load.index('AW_RegionSelect('), load.index('AW_SetNextLoadingDelay();'))
        self.assertRegex(load, r'if\(region_crossing\)\s*\{\s*AW_SetNextLoadingStyle\(.*?;\s*AW_SetNextLoadingDelay\(\);\s*\}')
        calls = [(p.name, source(p.name).count('AW_SetNextLoadingDelay();'))
                 for p in SRC.glob('*.c') if 'AW_SetNextLoadingDelay();' in source(p.name)]
        self.assertEqual(calls, [('aw_scene.c', 1)])
        self.assertIn('if(!pending)region_crossing=0;', body(scene, 'AW_SceneTick'))

    def test_begin_and_signon_do_not_draw_while_waiting(self):
        screen = source('screen.c')
        begin = body(screen, 'SCR_BeginLoadingPlaque')
        self.assertIn('if(!AW_LoadingDelayed())SCR_UpdateScreen ();', begin)
        self.assertIn('scr_disabled_for_loading = true;', begin)
        draw = body(screen, 'SCR_UpdateScreen')
        self.assertIn('SCR_LoadingUpdate();\n            return;', draw)
        self.assertIn('SCR_LoadingUpdate();\n        if(AW_LoadingDelayed())return;', draw)
        ui = body(source('aw_ui.c'), 'AW_UILoading')
        self.assertLess(ui.index('if(AW_LoadingDelayed())return;'), ui.index('memcpy('))

    def test_progress_draws_only_ui_and_has_no_allocation_or_renderer(self):
        update = body(source('screen.c'), 'SCR_LoadingUpdate')
        self.assertLess(update.index('if(!AW_LoadingDelayed()'), update.index('AW_LoadingDelayExpired()'))
        self.assertLess(update.index('if(!AW_LoadingDelayExpired())return;'), update.index('AW_UILoading();'))
        self.assertIn('V_UpdatePalette();', update)
        self.assertIn('VID_Update(&vrect)', update)
        self.assertIn('scr_drawloading=was_loading;', update)
        for forbidden in ('SCR_UpdateScreen(', 'V_RenderView(', 'R_RenderView(',
                          'malloc(', 'Hunk_', 'Cache_', 'COM_Load'):
            self.assertNotIn(forbidden, update)
        ui = source('aw_ui.c')
        self.assertIn('static byte background[64776],loading_background[64776];', ui)

    def test_silent_mode_registers_progress_and_audio_keeps_its_cadence(self):
        sound = source('snd_dma.c')
        initialize = body(sound, 'S_Init')
        self.assertLess(initialize.index('aw_load_audio_tick = S_LoadingUpdate;'), initialize.index('COM_CheckParm("-nosound")'))
        update = body(sound, 'S_LoadingUpdate')
        self.assertIn('if(!aw_loading_music || servicing)return;', update)
        self.assertIn('if(sound_started && !snd_blocked){', update)
        self.assertIn('if(!(now>=previous && now-previous<0.02)){', update)
        self.assertLess(update.index('servicing=1;'), update.index('CDAudio_Update();S_Update_();'))
        self.assertLess(update.index('CDAudio_Update();S_Update_();'), update.index('SCR_LoadingUpdate();'))
        self.assertRegex(update, r'\}\s*\}\s*SCR_LoadingUpdate\(\);\s*servicing=0;')

    def test_automatic_black_indicator_keeps_font_palette_and_intro_black(self):
        ui = source('aw_ui.c')
        draw = body(ui, 'AW_UILoading')
        self.assertRegex(draw, r'if\(loading_blank\)\{\s*AW_UIFill\(.*loading_region\?AW_UIColor\(0,0,0\):0\);\s*if\(loading_region\)\{')
        self.assertIn('loading_region?host_basepal:loading_black_palette', body(ui, 'AW_UIMenuPalette'))
        style = body(ui, 'AW_SetNextLoadingStyle')
        self.assertIn('next_loading_delay=0;next_loading_region=0;', style)
        self.assertNotIn('AW_SetNextLoadingDelay', source('aw_intro.c'))


if __name__ == '__main__':
    unittest.main()
