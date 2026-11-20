# SPDX-License-Identifier: GPL-3.0-only
"""A map spawned again keeps its script-disabled actors hidden (PLAZA-FABRICANTS-LIVE-AT-START-67).

On the v0.0.67 release image a server spawn of the map already loaded (a teleport inside Plaza Brindisi Dorom, frame
map mh0005; Seyda Neen spawned again while it is the map in play) drew the actors the world change list holds disabled:
the Plaza's four fabricants (4218689, 4218690, 4218692, 4218693; fab_attack_1 / fab_attack_2 disable them until An
Attack on Mournhold) and Seyda Neen's Dreamer_Talker04, Dreamer_Talker05 and agronian guy (297837, 297840, 474443;
disabled once by Startup). The script host (aw_mwhost.c AW_MwscriptTick) told a new map by its world model and its
name, and such a spawn gets the same model slot back by name (model.c Mod_FindName): the map was never attached again,
so ledger_attach never hid the new edicts, and a script's Disable of a reference disabled already did nothing. Now
every server spawn resets the host's map (AW_MwscriptServerReset, called by sv_main.c SV_SpawnServer), and a Disable
of a disabled reference hides an edict of it that is still drawn. OpenMW 0.51 loads a cell from its references'
enabled state at every load (mwworld/scene.cpp, worldimp.cpp World::disable).

The behaviour runs natively: aw_mwhost.c's own functions are cut out of the file (they are file-static in an engine
file too large to link alone) into a slice that tests/aga_mwhost_reload_test.c includes, with the real world change
list (aw_ledger.c). On the old host the slice has no reset (an empty stand-in, as SV_SpawnServer called none) and the
check fails at the second spawn of mh0005. AMIWIND_RUNTIME_SOURCE selects another engine tree for that comparison."""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import test_aga_native_source as native

ROOT = Path(__file__).resolve().parents[1]
ENGINE = Path(os.environ.get('AMIWIND_RUNTIME_SOURCE', str(ROOT / 'engine/aga')))
SRC = ENGINE / 'src'
COMPILER = os.environ.get('CC') or shutil.which('cc') or shutil.which('gcc')


def function(text, head):
    """The C definition starting at HEAD: to the end of its line when it closes there, else to its brace at column 0."""
    at = text.index(head)
    line = text[at:text.index('\n', at)]
    if line.rstrip().endswith('}') and line.count('{') == line.count('}'):
        return line + '\n'
    return text[at:text.index('\n}\n', at) + 3]


def line(text, head):
    at = text.index('\n' + head) + 1
    return text[at:text.index('\n', at) + 1]


def block(text, head, end):
    at = text.index(head)
    return text[at:text.index(end, at) + len(end)] + '\n'


def host_slice(text):
    """aw_mwhost.c's object state over map attaches, as one C text (definitions before their use)."""
    parts = [
        function(text, 'static edict_t *edict_of(int number){'),
        function(text, 'static int entity_of_reference(uint32_t ref){'),
        function(text, 'static int compare_refs(const void *a,const void *b){'),
        function(text, 'static void shown_state(edict_t *e,float *model,float *solid){'),
        line(text, '#define OBJECTS '),
        block(text, 'typedef struct {\n    uint32_t ref;\n    unsigned char disabled,lock_set,level,last_level;',
              '} object_t;'),
        line(text, 'static object_t objects[OBJECTS];static int object_count;'),
        line(text, 'static unsigned long objects_hidden,objects_full;'),
        function(text, 'static object_t *object_find(uint32_t ref,int create){'),
        function(text, 'static void object_hide(object_t *o){'),
        line(text, 'typedef struct {uint32_t ref;int entity,map;float model,solid;} hidden_t;'),
        line(text, 'static hidden_t *hidden;static int hidden_count,hidden_capacity;'),
        line(text, 'static unsigned long ledger_hidden,ledger_refused;'),
        function(text, 'static hidden_t *hidden_find(uint32_t ref,int create){'),
        function(text, 'static void ledger_hide(uint32_t ref){'),
        function(text, 'static void ledger_show(uint32_t ref){'),
    ]
    if 'static void disabled_drawn(uint32_t ref){' in text:
        parts += [line(text, 'static unsigned long ledger_rehidden;'),
                  function(text, 'static void disabled_drawn(uint32_t ref){')]
    else:
        parts.append('static unsigned long ledger_rehidden;   /* the old host: no such step */\n')
    parts += [
        function(text, 'static aw_ledger_row_t *ledger_row(uint32_t ref){'),
        function(text, 'int AW_ObjectDisabled(unsigned int reference){'),
        function(text, 'static int32_t ledger_object(uint32_t ref,int op,int32_t value){'),
        function(text, 'static int ledger_take(uint32_t reference,int stolen){'),
        function(text, 'static void ledger_attach(void){'),
        function(text, 'static void ledger_import(const aw_changes_t *in){'),
        function(text, 'static void objects_import(const aw_changes_t *in){'),
        function(text, 'static void attach_objects(void){'),
    ]
    if 'void AW_MwscriptServerReset(void){' in text:
        parts.append(function(text, 'void AW_MwscriptServerReset(void){'))
    else:
        parts.append('void AW_MwscriptServerReset(void){}   /* the old host: SV_SpawnServer reset nothing here */\n')
    tick = block(text, '    if(sv.worldmodel!=map_model || strcmp(sv.name,map_name)){', '\n    }')
    parts.append('/* AW_MwscriptTick\'s map test, its first lines after a spawn */\nstatic void tick_map(void){\n'
                 + tick + '}\n')
    return '/* cut from aw_mwhost.c by tests/test_same_map_reload.py */\n' + ''.join(parts)


def compile_and_run(test, host_text):
    with tempfile.TemporaryDirectory(prefix='amiwind-mhreload-') as tmp:
        tmp = Path(tmp)
        native.tree_project_version().generate_native(ROOT / 'VERSION', tmp)
        (tmp / 'mwhost_reload_slice.c').write_text(host_slice(host_text), encoding='utf-8')
        exe = tmp / 'check'
        cmd = [COMPILER, '-std=gnu89', '-O1', '-g', '-Wall', '-Wno-unused-function', '-Wno-unused-variable',
               '-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-ffunction-sections', '-fdata-sections',
               '-Wl,--gc-sections', '-include', str(ROOT / 'tests/aga_test_files.h'), '-I' + str(tmp), '-I' + str(SRC),
               str(ROOT / 'tests/aga_mwhost_reload_test.c'), str(SRC / 'aw_ledger.c'), '-lm', '-o', str(exe)]
        built = subprocess.run(cmd, capture_output=True, text=True)
        test.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        return subprocess.run([str(exe)], cwd=tmp, capture_output=True, text=True, timeout=120)


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8', errors='replace'), flags=re.S)


@unittest.skipUnless(COMPILER, 'a host C compiler is required')
class SameMapReloadNativeTests(unittest.TestCase):
    def test_a_map_spawned_again_keeps_its_disabled_actors_hidden(self):
        """The Plaza's four fabricants and Seyda Neen's three Startup references stay hidden over a spawn of the map in
        play, a save loaded in place and a map change; a Disable hides a drawn edict of a disabled reference and never
        one whose record is enabled; Enable after such a spawn shows the actor with its own model; every reference is
        drawn as its record says whatever its script does next; the Dreamers, Tarhiel and the fabricants are drawn once
        their scripts' stage is reached, over every load."""
        host = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8', errors='replace')
        run = compile_and_run(self, host)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn('second spawn of mh0005: map attached 2 times', run.stdout)
        # every record state (untouched, disabled, enabled again, enabled only, taken, disabled and taken) under every
        # next run of its script (none, GetDisabled, Disable, Enable) over every load (the same map, a save in place,
        # a change of place and back, New Game): drawn exactly as the record says
        self.assertIn('generic: 24 references, 6 record states x 4 next runs, 4 kinds of load: drawn as recorded',
                      run.stdout)
        # the game's own conditions both ways: hidden before the stage, drawn after it, over every load
        self.assertIn('conditions: the Dreamers (A2_2_6thHouse 50)', run.stdout)
        self.assertIn('PASS:', run.stdout)


class SameMapReloadWiringTests(unittest.TestCase):
    def test_every_server_spawn_resets_the_script_host_before_the_new_entities(self):
        server = code('sv_main.c')
        spawn = server[server.index('void SV_SpawnServer (char *server)\n#endif\n{'):]
        spawn = spawn[:spawn.index('\n}\n')]
        reset = spawn.index('AW_MwscriptServerReset();')
        self.assertLess(spawn.index('memset (&sv, 0, sizeof(sv));'), reset)
        self.assertLess(reset, spawn.index('ED_LoadFromFile (sv.worldmodel->entities);'))
        # declared by its caller, not in a header a world or actor stage keys
        self.assertIn('void AW_MwscriptServerReset (void);', server)
        for header in SRC.glob('*.h'):
            self.assertNotIn('AW_MwscriptServerReset', header.read_text(encoding='utf-8', errors='replace'), header.name)

    def test_the_reset_makes_the_tick_attach_the_map_again(self):
        host = code('aw_mwhost.c')
        reset = function(host, 'void AW_MwscriptServerReset(void){')
        self.assertIn('map_model=NULL;', reset)
        tick = function(host, 'void AW_MwscriptTick(float dt){')
        test = tick.index('if(sv.worldmodel!=map_model || strcmp(sv.name,map_name)){')
        self.assertLess(test, tick.index('attached_map++;attach_objects();script_model=NULL;'))
        self.assertLess(tick.index('attach_objects();'), tick.index('attach_map();'))

    def test_a_disable_of_a_disabled_reference_hides_a_drawn_edict(self):
        ledger = function(code('aw_mwhost.c'), 'static int32_t ledger_object(uint32_t ref,int op,int32_t value){')
        disable = ledger[ledger.index('case AWM_DISABLE:'):ledger.index('case AWM_GETDISABLED:')]
        self.assertIn('if(r && (r->fields&AW_LEDGER_DISABLED)){disabled_drawn(ref);return 0;}', disable)
        drawn = function(code('aw_mwhost.c'), 'static void disabled_drawn(uint32_t ref){')
        self.assertIn('if(!e || e->free || !e->v.modelindex)return;', drawn)   # the common case: nothing more

    def test_the_status_counts_the_attaches(self):
        status = function(code('aw_mwhost.c'), 'void AW_MwscriptLedgerStatus(void){')
        self.assertIn('server_spawns,(unsigned long)attached_map,ledger_rehidden', status)


if __name__ == '__main__':
    unittest.main()
