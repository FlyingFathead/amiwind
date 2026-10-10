# SPDX-License-Identifier: GPL-3.0-only
"""v0.0.35 crash paths reachable from the console, saves and map data: one regression check each.

ENGINE-MAP-NAME-OVERFLOW-35: map, changelevel, connect, restart and load copied a typed (or saved) name of
any length into fixed buffers; SV_SpawnServer now refuses a name that does not fit "maps/<name>.bsp" before
anything changes, and the map command joins its arguments with a bound (native fixture, ASan).
ENGINE-FRAME-TIME-FLOAT-35: the main loop held the seconds since start in floats.
ENGINE-LOADGAME-SYSERROR-35: a damaged save stopped the program (Sys_Error) and its strings were read
without a width.
ENGINE-SUBMODEL-LIMIT-32: a map with more inline models than the precache holds wrote past it.
The fatal-path sweep (ENGINE-FATAL-PATH-SWEEP-35): ENGINE-SOUND-NAME-SYSERROR-35, ENGINE-MODEL-NAME-SYSERROR-35,
ENGINE-WRITE-OPEN-SYSERROR-35, ENGINE-CBUF-OVERFLOW-35, ENGINE-COM-TOKEN-UNBOUNDED-35,
ENGINE-ENTITY-TEXT-UNBOUNDED-35, ENGINE-LEAF-LIMIT-UNCHECKED-35, ENGINE-QC-ARGS-SYSERROR-35 and
CHIM-STATIC-PLACE-HOST-ERROR-35."""
from pathlib import Path
import os
import re
import shutil
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FN_END = chr(10) + '}' + chr(10)
SRC = ROOT / 'engine/aga/src'


def text(name):
    return (SRC / name).read_text(encoding='utf-8')


def section(body, start, end):
    at = body.index(start)
    return body[at:body.index(end, at)]


def strip_comments(body):
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', body, flags=re.S)


def build_run(test, program):
    with tempfile.TemporaryDirectory() as tmp:
        c = Path(tmp) / 'fixture.c'
        c.write_text(program, encoding='utf-8', newline='\n')
        exe = Path(tmp) / 'fixture'
        built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-fsanitize=address,undefined',
                                '-fno-sanitize-recover=all', str(c), '-o', str(exe)], capture_output=True, text=True)
        test.assertEqual(built.returncode, 0, built.stderr)
        ran = subprocess.run([str(exe)], capture_output=True, text=True)
        test.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        return ran.stdout


@unittest.skipIf(os.name == 'nt', 'native fixtures run in Linux Docker')
@unittest.skipUnless(shutil.which('cc'), 'requires a C compiler')
class CrashPathsNative(unittest.TestCase):
    def test_map_name_fits_and_joined_arguments_are_bounded(self):
        fits = section(text('sv_main.c'), 'qboolean SV_MapNameFits (const char *name)', '#ifdef QUAKE2')
        join = section(text('host_cmd.c'), 'static qboolean Host_JoinArgs', '/*\n======================\nHost_Map_f')
        program = r'''
#include <stdio.h>
#include <string.h>
typedef int qboolean;
#define true 1
#define false 0
#define MAX_QPATH 64
#define SV_MAPNAME_MAX (MAX_QPATH - 10)
static int printed;
static void Con_Printf (const char *f, ...) { (void)f; printed++; }
static int argc; static char *argv[8];
static int Cmd_Argc (void) { return argc; }
static char *Cmd_Argv (int i) { return i < argc ? argv[i] : ""; }
''' + fits + join + r'''
int main(void)
{
    static char name[80], big[200];
    char modelname[MAX_QPATH], mapstring[MAX_QPATH];
    memset(name, 'a', SV_MAPNAME_MAX); name[SV_MAPNAME_MAX] = 0;
    if (!SV_MapNameFits(name) || printed) return 1;
    /* the longest accepted name fills maps/<name>.bsp exactly */
    if (snprintf(modelname, sizeof modelname, "maps/%s.bsp", name) != MAX_QPATH - 1) return 2;
    name[SV_MAPNAME_MAX] = 'a'; name[SV_MAPNAME_MAX + 1] = 0;
    if (SV_MapNameFits(name) || printed != 1) return 3;
    if (SV_MapNameFits(NULL)) return 4;
    argc = 3; argv[0] = "map"; argv[1] = "bm001"; argv[2] = "x";
    if (!Host_JoinArgs(mapstring, sizeof mapstring - 1, 0) || strcmp(mapstring, "map bm001 x ")) return 5;
    memset(big, 'b', sizeof big - 1); argv[2] = big;
    if (Host_JoinArgs(mapstring, sizeof mapstring - 1, 0) || mapstring[0]) return 6;
    argv[2] = "x"; memset(big, 'c', 61); big[61] = 0; argv[1] = big; argc = 2;
    /* "map " + 61 + " " = 66 does not fit 63 */
    if (Host_JoinArgs(mapstring, sizeof mapstring - 1, 0)) return 7;
    return 0;
}
'''
        build_run(self, program)

    def test_com_parse_and_default_extension_are_bounded(self):
        body = text('common.c')
        parse = section(body, 'char *COM_Parse (char *data)', FN_END) + FN_END
        ext = section(body, 'void COM_DefaultExtension (char *path, char *extension)', FN_END) + FN_END
        program = r'''
#include <string.h>
char com_token[1024];
''' + parse + ext + r'''
int main(void)
{
    static char data[4000], path[16];
    char *p;
    memset(data, 'a', 3000); data[3000] = 0;
    p = COM_Parse(data);
    if (strlen(com_token) != sizeof(com_token) - 1 || !p || *p) return 1;
    data[0] = '"'; data[2999] = '"';
    p = COM_Parse(data);
    if (strlen(com_token) != sizeof(com_token) - 1 || !p) return 2;
    path[0] = 0; COM_DefaultExtension(path, ".dem");
    if (strcmp(path, ".dem")) return 3;
    strcpy(path, "x/a.sav"); COM_DefaultExtension(path, ".sav");
    if (strcmp(path, "x/a.sav")) return 4;
    return 0;
}
'''
        build_run(self, program)

    def test_varstring_joins_with_a_bound(self):
        join = section(text('pr_cmds.c'), 'char *PF_VarString (int' + chr(9) + 'first)', FN_END) + FN_END
        program = r'''
#include <stdio.h>
#include <string.h>
#define Q_snprintf snprintf
static int pr_argc; static char *args[8];
#define OFS_PARM0 0
#define G_STRING(o) args[(o)/3]
''' + join + r'''
int main(void)
{
    static char big[700];
    memset(big, 'q', 699); args[0] = "a"; args[1] = big; args[2] = big; pr_argc = 3;
    if (strlen(PF_VarString(0)) != 255) return 1;
    args[1] = "b"; pr_argc = 2;
    if (strcmp(PF_VarString(0), "ab")) return 2;
    return 0;
}
'''
        build_run(self, program)


class CrashPathsSource(unittest.TestCase):
    def test_spawn_server_refuses_a_long_name_before_anything_changes(self):
        body = strip_comments(section(text('sv_main.c'), 'void SV_SpawnServer (char *server)\n#endif\n{', '\n}\n'))
        first = body.index('SV_MapNameFits (server)')
        self.assertLess(first, body.index('Cvar_Set ("hostname"'))
        self.assertLess(first, body.index('SV_SendReconnect'))
        self.assertNotIn('strcpy (sv.name', body)
        self.assertNotIn('sprintf (sv.modelname', body)
        self.assertIn('#define SV_MAPNAME_MAX (MAX_QPATH - 10)', text('server.h'))   # "maps/" ".bsp" NUL

    def test_console_commands_copy_names_with_a_bound(self):
        host = strip_comments(text('host_cmd.c'))
        for pattern in (r'strcpy\s*\(\s*name\s*,\s*Cmd_Argv', r'strcpy\s*\(\s*level\s*,\s*Cmd_Argv',
                        r'strcpy\s*\(\s*_startspot\s*,\s*Cmd_Argv', r'strcat\s*\(\s*cls\.(mapstring|spawnparms)\s*,\s*Cmd_Argv',
                        r'strcpy\s*\(\s*mapname\s*,\s*sv\.name'):
            self.assertNotRegex(host, pattern)
        mapf = section(host, 'void Host_Map_f (void)', 'void Host_Changelevel_f')
        # refused before the running game is left
        self.assertLess(mapf.index('SV_MapNameFits (Cmd_Argv(1))'), mapf.index('CL_Disconnect ()'))
        self.assertLess(mapf.index('Host_JoinArgs (cls.spawnparms'), mapf.index('CL_Disconnect ()'))
        change = section(host, 'void Host_Changelevel_f', 'void Host_Restart_f')
        plain = change[change.index('#else'):]
        self.assertLess(plain.index('SV_MapNameFits'), plain.index('SV_SaveSpawnparms'))

    def test_loadgame_reads_with_widths_and_never_stops_the_program(self):
        load = strip_comments(section(text('host_cmd.c'), 'void Host_Loadgame_f (void)', '#ifdef QUAKE2\nvoid SaveGamestate'))
        self.assertNotRegex(load, r'Q_fscanf\s*\(\s*f\s*,\s*"%s')
        self.assertIn('"%63s\\n",mapname', load)
        self.assertNotIn('Sys_Error', load)
        self.assertIn('Host_Error ("Loadgame buffer overflow', load)
        self.assertIn('entnum >= MAX_EDICTS', load)

    def test_frame_times_are_double(self):
        loop = section(text('sys_amiga.c'), 'static void RunGameLoop(void)', '\n}\n')
        self.assertRegex(loop, r'double\s+newtime;')
        self.assertRegex(loop, r'double\s+oldtime;')
        self.assertNotRegex(loop, r'float\s+(newtime|oldtime)')
        # Why: the step between floats near the seconds since start (about 1 ms after 4.5 hours, 4 ms after 18).
        def step(seconds):
            bits = struct.unpack('<I', struct.pack('<f', seconds))[0]
            return struct.unpack('<f', struct.pack('<I', bits + 1))[0] - struct.unpack('<f', struct.pack('<I', bits))[0]
        self.assertGreaterEqual(step(4.5 * 3600), 1 / 1024)
        self.assertGreaterEqual(step(18 * 3600), 1 / 256)

    def test_submodel_count_is_checked_before_the_precache_loop(self):
        body = text('sv_main.c')
        spawn = section(body, 'void SV_SpawnServer (char *server)\n#endif\n{', '// load the rest of the entities')
        self.assertLess(spawn.index('numsubmodels > MAX_MODELS - 1'), spawn.index('sv.model_precache[1+i] = localmodels[i]'))


    def test_sweep_sites_refuse_instead_of_stopping(self):
        snd = strip_comments(section(text('snd_dma.c'), 'sfx_t *S_FindName (char *name)', FN_END))
        self.assertNotIn('Sys_Error', snd)
        self.assertIn('return NULL', snd)
        model = text('model.c')
        forname = section(model, 'model_t *Mod_ForName (char *name, qboolean crash)', FN_END)
        self.assertLess(forname.index('strlen (name) >= MAX_QPATH'), forname.index('Mod_FindName (name)'))
        self.assertIn('count > MAX_MAP_LEAFS', model)
        self.assertNotIn('Sys_Error ("Mod_NumForName', model)
        self.assertIn('name[sizeof(pdaliasframe->name) - 1] = 0;', model)
        openw = section(text('sys_file_amiga.c'), 'int Sys_FileOpenWrite (char *path)', FN_END)
        self.assertNotIn('Sys_Error', openw)
        self.assertIn('return -1;', openw)
        cmd = strip_comments(text('cmd.c'))
        self.assertIn('Q_strlen (text) + cmd_text.cursize >= cmd_text.maxsize', cmd)
        self.assertNotRegex(cmd, r'memcpy \(line, text, i\);')
        edict = strip_comments(text('pr_edict.c'))
        self.assertNotRegex(edict, r'Sys_Error \("ED_(ParseEntity|LoadFromFile)')
        self.assertNotRegex(edict, r'strcpy \((keyname|string|temp), ')
        self.assertIn('return pr_strings + val->string;', edict)
        self.assertIn('Q_snprintf (message, sizeof(message), "%s", pr_strings+sv.edicts->v.message);', text('sv_main.c'))
        for name in ('console.c', 'host.c', 'pr_exec.c', 'sys_amiga.c'):
            self.assertNotRegex(strip_comments(text(name)), r'vsprintf\s*\(', name)
        parse = strip_comments(text('cl_parse.c'))
        self.assertEqual(parse.count('strlen (str) >= MAX_QPATH'), 2)
        self.assertNotIn('strcpy (cl.scores[i].name', parse)
        demo = strip_comments(text('cl_demo.c'))
        self.assertNotIn('strcpy (name, Cmd_Argv(1))', demo)
        self.assertNotRegex(strip_comments(text('host_cmd.c')), r'COM_FormatPath \(name, sizeof\(name\), "%s/%s", com_gamedir')
        qc = strip_comments(text('pr_cmds.c'))
        self.assertNotIn('Sys_Error ("SV_StartSound', qc)
        self.assertIn('style >= MAX_LIGHTSTYLES', qc)
        place = strip_comments(section(text('chim/chim_statics.c'), 'static int Place (chim_static_t *s)', FN_END))
        self.assertNotIn('Host_Error', place)


if __name__ == '__main__':
    unittest.main()
