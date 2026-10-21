# SPDX-License-Identifier: GPL-3.0-only
"""Engine compiler warnings (ENGINE-STRICT-WARNINGS-36, docs/DEVELOPMENT.md).

Every engine file builds with -Wall -Wextra -Wformat-security (less unused code, partly initialised
structs and signed/unsigned comparisons, which are noise in the inherited Quake code); AmiWind's own
files (aw_*.c, chim/*.c) also get -Wunused, -Wsign-compare, -Wshadow and -Wmissing-prototypes. The
builder fails on any warning, so the gate's engine step holds both sets at zero. These host tests pin
the make command lines, the printf format checks the warnings rely on, and the real faults the
stricter warnings found (each fixed in the source).
"""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'engine' / 'aga'
SRC = ENGINE / 'src'
ALL_FILES = ('-Wall', '-Wextra', '-Wformat-security')
OWN_FILES = ('-Wunused', '-Wsign-compare', '-Wshadow', '-Wmissing-prototypes')


def make_commands(*variables):
    result = subprocess.run(['make', '-n', '-B', 'fpu', 'PYTHON=python3', *variables], cwd=ENGINE,
                            capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise AssertionError(result.stdout[-2000:] + result.stderr[-2000:])
    return [' '.join(line.split()) for line in result.stdout.splitlines() if line.strip()]


def effective(flags, name):
    """The last of -Wname / -Wno-name on the command line wins (GCC)."""
    state = None
    for flag in flags:
        if flag == '-W' + name:
            state = True
        elif flag == '-Wno-' + name:
            state = False
    return state


@unittest.skipUnless(shutil.which('make'), 'GNU make not installed')
class WarningLevelTests(unittest.TestCase):
    def check_levels(self, *variables):
        compiles = {line.split()[-1]: line.split() for line in make_commands(*variables) if ' -c -o obj' in line}
        self.assertTrue(compiles)
        own = [name for name in compiles if re.match(r'src/(aw_[^/]*|chim/[^/]*)\.c$', name)]
        upstream = [name for name in compiles if name not in own]
        self.assertIn('src/aw_ui.c', own)
        self.assertIn('src/chim/chim_world.c', own)
        self.assertIn('src/d_scan.c', upstream)
        self.assertIn('src/d_sprite.c', upstream)
        for name, flags in compiles.items():
            for flag in ALL_FILES:
                self.assertIn(flag, flags, name)
            for flag in OWN_FILES:
                if name in own:
                    self.assertIs(effective(flags, flag[2:]), True, (name, flag))
                else:
                    self.assertIsNot(effective(flags, flag[2:]), True, (name, flag))
            self.assertNotEqual(effective(flags, 'unused-parameter'), True, name)

    def test_default_build(self):
        self.check_levels()

    def test_every_engine_variant(self):
        # the gate's engine step builds these too (build_aga.py engine --check-profiles, the 68060 engine)
        self.check_levels('ENGINE_OPT=o2')
        self.check_levels('ENGINE_CPU=68060')
        self.check_levels('ENGINE_ASM=turb c2p')


class FormatCheckTests(unittest.TestCase):
    """Every printf-like engine function is declared with the format attribute, so -Wall's -Wformat
    checks its callers (35 mismatches were found when they were added, 20 October 2026)."""

    def test_printf_like_declarations_carry_the_format_attribute(self):
        decl = re.compile(r'^[^#/\n]*\b(\w+)\s*\(([^()]*)\.\.\.\s*\)\s*([^;{]*);', re.M)
        found = {}
        for header in sorted(SRC.rglob('*.h')):
            for m in decl.finditer(header.read_text(encoding='latin-1')):
                params = m.group(2)
                if re.search(r'char\s*\*\s*(fmt|format|error|message)\s*,\s*$', params):
                    found[m.group(1)] = (header.name, m.group(3))
        for name in ('Con_Printf', 'Con_DPrintf', 'Con_SafePrintf', 'Sys_Error', 'Sys_Printf', 'Host_Error',
                     'Host_EndGame', 'SV_ClientPrintf', 'SV_BroadcastPrintf', 'PR_RunError', 'va', 'AW_LogPrintf',
                     'COM_FormatPath', 'Q_snprintf'):
            self.assertIn(name, found)
        for name, (header, attributes) in found.items():
            self.assertRegex(attributes, r'format\((printf|scanf),', '%s in %s has no format attribute' % (name, header))

    def test_no_text_passed_as_a_format(self):
        console = (SRC / 'console.c').read_text(encoding='latin-1')
        self.assertIn('Con_Printf ("%s", text);', console)
        self.assertNotRegex(console, r'Con_Printf \(text\);')
        self.assertIn('Con_Printf("%s", reason);', (SRC / 'net_dgrm.c').read_text(encoding='latin-1'))

    def test_floor_div_mod_error_prints_the_double(self):
        mathlib = (SRC / 'mathlib.c').read_text(encoding='latin-1')
        self.assertIn('Sys_Error ("FloorDivMod: bad denominator %f\\n", denom);', mathlib)


class FoundFaultTests(unittest.TestCase):
    """Faults the stricter warnings showed in the engine source (ENGINE-STRICT-WARNINGS-36)."""

    def test_chase_direction_compares_float_distances(self):
        # -Wabsolute-value: abs() truncated the float deltas to int (inherited Quake code)
        self.assertIn('fabs(deltay)>fabs(deltax)', (SRC / 'sv_move.c').read_text(encoding='latin-1'))

    def test_ui_fill_clips_rectangles_left_of_or_above_the_screen(self):
        # -Wsign-compare: right/bottom were compared with the unsigned screen size, so a rectangle
        # wholly left of (or above) the screen became a fill of the whole row span (or column)
        ui = (SRC / 'aw_ui.c').read_text(encoding='latin-1')
        self.assertIn('if(right>(int)vid.width)right=(int)vid.width;', ui)
        self.assertIn('if(bottom>(int)vid.height)bottom=(int)vid.height;', ui)

    def test_text_starting_left_of_the_screen_is_clipped_not_dropped_or_overrun(self):
        gallery = (SRC / 'aw_gallery.c').read_text(encoding='latin-1')
        # a character cell partly left of the screen went to Draw_Character, which does not clip x
        self.assertIn('x+w<=(int)vid.width;s++,x+=w)if(x>=0)AW_ConsoleCharacter(', gallery)
        arena = (SRC / 'aw_arena.c').read_text(encoding='latin-1')
        self.assertIn('x+w<=(int)vid.width;s++,x+=w)if(x>=0)AW_ConsoleCharacter(', arena)
        glyphs = (SRC / 'aw_console_glyphs.c').read_text(encoding='latin-1')
        self.assertIn('for(;*text && x<(int)vid.width;text++,x+=4){', glyphs)


if __name__ == '__main__':
    unittest.main()
