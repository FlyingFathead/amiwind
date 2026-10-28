# SPDX-License-Identifier: GPL-3.0-only
"""An engine source edit rekeys only the stages that read that file (BUILD-ENGINE-SOURCE-KEY-BROAD-36).

The v0.0.50 final rebuilt the CHIM world for an edit of engine/aga/src/aw_scene.c (the `dbg tp` named places): three
builder modules name the engine folder (tools/engine_limits.py SOURCE, tools/chim/zone_sim.py SRC and the include
folders of check_world_map_heap's target ABI probe), and a folder named in reached code counts whole, so every CHIM
world stage keyed all 331 files of engine/aga/src. In those modules (build_cache.C_HEADER_READERS) the folder now
counts as the engine files the reach names and their #include closure. This gate test fails when a stage started by
tools/build.py keys an engine C file outside ENGINE_C_INPUTS (read only, no build)."""
import json
import re
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_cache  # noqa: E402

# Engine C files a stage may key, each read by a builder check whose result is in the stage's output:
# - engine_limits / map_engine_limits defines and cvar defaults: aw_combat.c, chim/chim_statics.c, chim/chim_world.c,
#   sys_amiga.c (the entity, zone and heap budgets of the CHIM gates);
# - the zone walk gate compiles chim/chim_zone.c (zone_sim);
# - check_world_map_heap hashes the loaders into its receipt and checks their policies: model.c, r_efrag.c, cl_main.c,
#   host.c, zone.c, aw_harvest*.c, aw_section.c (harvest and section budgets), r_draw.c (edge_cache_heap's pins);
# - chim/chim_chunks.c: the chunk link budget.
ENGINE_C_INPUTS = frozenset('engine/aga/src/' + name for name in (
    'aw_combat.c', 'aw_harvest.c', 'aw_harvest_proxy.c', 'aw_harvest_runtime.c', 'aw_section.c', 'chim/chim_chunks.c',
    'chim/chim_statics.c', 'chim/chim_world.c', 'chim/chim_zone.c', 'cl_main.c', 'host.c', 'model.c', 'r_draw.c',
    'r_efrag.c', 'sys_amiga.c', 'zone.c'))
# Engine files no builder check reads: an edit of one must rebuild only the engine and the image
ENGINE_ONLY = ('engine/aga/src/aw_scene.c', 'engine/aga/src/r_main.c', 'engine/aga/src/sv_main.c',
               # tools/door_graph.py room_limits reads it, but only the door graph tool runs that (no stage): the room
               # pre-grow fix of v054-persisting re-keys no CHIM stage (2026-10-27)
               'engine/aga/src/chim/chim_room.c')
CHIM_STAGES = ('chim_build.py', 'chim_rooms.py', 'chim_room_batches.py', 'chim_interiors.py', 'chim_town.py')


def stage_scripts():
    """Every tools/*.py script tools/build.py starts as a stage (its tool('NAME.py', ...) calls)."""
    text = (ROOT / 'tools' / 'build.py').read_text(encoding='utf-8')
    return sorted(name for name in set(re.findall(r"tool\(\s*'([A-Za-z0-9_]+\.py)'", text))
                  if (ROOT / 'tools' / name).is_file())


class RepositoryEngineKeyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = build_cache.SourceIndex(ROOT, top_format=build_cache.STAGE_TOP_FORMAT)
        cls.engine = [path for path in cls.index.files if path.startswith('engine/aga/src/')]

    def engine_files(self, script):
        selected, uncertain = self.index.selection(ROOT / 'tools' / script)
        self.assertFalse(uncertain, script)
        return {path for path in selected if path.startswith('engine/')}

    def test_the_engine_only_files_exist(self):
        for path in ENGINE_ONLY:
            self.assertIn(path, self.index.files)

    def test_no_stage_keys_an_engine_c_file_it_does_not_read(self):
        for script in stage_scripts():
            extra = sorted(path for path in self.engine_files(script)
                           if path.endswith('.c') and path not in ENGINE_C_INPUTS)
            self.assertEqual(extra, [], '%s: an edit of these engine files would rebuild the stage' % script)

    def test_an_engine_only_edit_rebuilds_no_stage(self):
        for script in stage_scripts():
            self.assertFalse(self.engine_files(script) & set(ENGINE_ONLY), script)

    def test_the_chim_world_keys_far_less_than_the_engine_folder(self):
        for script in CHIM_STAGES:
            if (ROOT / 'tools' / script).is_file():
                self.assertLess(len(self.engine_files(script)), len(self.engine) // 2, script)

    def test_the_chim_stage_still_keys_what_the_zone_gate_compiles(self):
        files = self.engine_files('chim_build.py')
        self.assertIn('engine/aga/src/chim/chim_zone.c', files)
        self.assertIn('engine/aga/src/chim/chim_zone.h', files)
        self.assertIn('engine/aga/src/quakedef.h', files)


READER = '''
from pathlib import Path
SOURCE = Path(__file__).resolve().parents[1] / 'engine/aga/src'
def define(header, source=SOURCE):
    return (Path(source) / header).read_text()
'''
STAGE = '''
import engine_limits
print(engine_limits.define('limits.c'))
'''
STAGE_WHOLE = '''
from pathlib import Path
print(sorted((Path(__file__).resolve().parents[1] / 'engine/aga/src').iterdir()))
'''


class HeaderRuleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        files = {'tools/engine_limits.py': READER, 'tools/stage.py': STAGE, 'tools/stage_whole.py': STAGE_WHOLE,
                 'engine/aga/src/limits.c': '#include "quakedef.h"\n#include <stdio.h>\nint x;\n',
                 'engine/aga/src/quakedef.h': '#include "chim/zone.h"\n#include "generated_version.h"\n',
                 'engine/aga/src/chim/zone.h': '  #  include "../common.h"\n',
                 'engine/aga/src/common.h': '/* no includes */\n',
                 'engine/aga/src/scene.c': '#include "quakedef.h"\nint scene;\n'}
        for relative, text in files.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf-8')

    def tearDown(self):
        self.temp.cleanup()

    def selected(self, script, top_format=build_cache.STAGE_TOP_FORMAT, **options):
        index = build_cache.SourceIndex(self.root, top_format=top_format, **options)
        selected, uncertain = index.selection(self.root / 'tools' / script)
        self.assertFalse(uncertain)
        return {path for path in selected if path.startswith('engine/')}

    def test_a_reader_keys_the_named_file_and_its_includes(self):
        self.assertEqual(self.selected('stage.py', engine_facts=False), {
            'engine/aga/src/limits.c', 'engine/aga/src/quakedef.h', 'engine/aga/src/chim/zone.h',
            'engine/aga/src/common.h'})
        # by their C facts (BUILD-STAGE-KEY-ENGINE-HEADERS-54): headers holding nothing limits.c names leave the key
        self.assertEqual(self.selected('stage.py'), {'engine/aga/src/limits.c'})

    def test_the_folder_named_elsewhere_still_counts_whole(self):
        self.assertIn('engine/aga/src/scene.c', self.selected('stage_whole.py'))

    def test_the_unit_caches_keep_their_reach(self):
        self.assertIn('engine/aga/src/scene.c', self.selected('stage.py', top_format=1))
        self.assertIn('engine/aga/src/scene.c', self.selected('stage.py', narrow_headers=False))

    def test_the_companion_follows_the_stage_index(self):
        index = build_cache.SourceIndex(self.root, top_format=build_cache.STAGE_TOP_FORMAT)
        self.assertTrue(index.companion().narrow_headers)
        self.assertTrue(index.companion().engine_facts)
        self.assertFalse(build_cache.SourceIndex(self.root, top_format=1).engine_facts)


# --------------------------------------------------------------------------
# BUILD-STAGE-KEY-ENGINE-HEADERS-54: engine headers count by their C facts (tools/engine_facts.py)

import engine_facts  # noqa: E402

SRC = 'engine/aga/src/'
# the v0.0.54 edits that re-keyed the CHIM world (the actor record be93bf6c, magic 2389209a): what they add is
# declared for the engine alone
NEUTRAL_EDITS = {
    'actor record: quakedef.h prototypes and hooks': (SRC + 'quakedef.h', lambda text: text + (
        '\nint AW_MwscriptActors(void);\nstruct edict_s;\n'
        'extern int (*aw_mwscript_combat_end)(struct edict_s *e);\n'
        'extern int (*aw_mwscript_wander)(struct edict_s *e,int distance,int duration,int hour,'
        'const unsigned char idle[8],int repeat);\nint AW_MwscriptSpeedAttribute(struct edict_s *e);\n')),
    'magic: sound.h S_MoveSound': (SRC + 'sound.h', lambda text: text.replace(
        'void S_StopSound (int entnum, int entchannel);',
        'void S_StopSound (int entnum, int entchannel);\nvoid S_MoveSound (int entnum, int entchannel, vec3_t origin);')),
    'actor record: aw_save.h block and hooks': (SRC + 'aw_save.h', lambda text: text.replace(
        '} aw_changes_t;', '    unsigned char *test_block;\n    int test_bytes,test_capacity;\n} aw_changes_t;').replace(
        '} aw_changes_t;', '} aw_changes_t;\n#define AW_SAVE_TEST_BYTES 32768\n'
        'extern int (*aw_save_test_export)(unsigned char *out,int capacity);', 1)),
    'a comment in quakedef.h': (SRC + 'quakedef.h', lambda text: text.replace(
        '#define\tMAX_EDICTS', '/* the edict table */\n#define\tMAX_EDICTS', 1)),
    # BUILD-STAGE-KEY-ENGINE-C-WHOLE-54 (v054-persisting): a diagnostic status print in chim_world.c, which the
    # world build reads only for its cvar defaults
    'a status print in chim_world.c': (SRC + 'chim/chim_world.c', lambda text: text.replace(
        'Con_Printf ("CHIM: room %s: %lu KiB of Fast RAM free',
        'Con_Printf ("CHIM: status diagnostic\\n");\n\t\t\tCon_Printf ("CHIM: room %s: %lu KiB of Fast RAM free', 1)),
}
# edits of what the world build reads: each must re-key the CHIM world
READ_EDITS = {
    'quakedef.h MAX_EDICTS (map_engine_limits)': (SRC + 'quakedef.h', lambda text: re.sub(
        r'(#define\s+MAX_EDICTS\s+)(\d+)', lambda m: m.group(1) + str(int(m.group(2)) + 1), text, count=1)),
    'render.h entity_t gains a field (the ABI probe sizes it)': (SRC + 'render.h', lambda text: text.replace(
        '} entity_t;', '    int aw_probe_field;\n} entity_t;', 1)),
    'chim_world.c chim_zone_kib default (engine_limits.cvar_default)': (SRC + 'chim/chim_world.c', lambda text: re.sub(
        r'(\{"chim_zone_kib", ")(\d+)', lambda m: m.group(1) + str(int(m.group(2)) + 16), text, count=1)),
}


class EngineFactsRepositoryTests(unittest.TestCase):
    """The CHIM world's keys against the edits of v0.0.54 (read only: edits are shown to the key, never written)."""

    @classmethod
    def setUpClass(cls):
        cls.index = build_cache.SourceIndex(ROOT, top_format=build_cache.STAGE_TOP_FORMAT)

    def key(self, script, edit=None):
        original = engine_facts.read_text

        def read(index, path):
            text = original(index, path)
            return edit[1](text) if edit and path == edit[0] else text
        with unittest.mock.patch.object(engine_facts, 'read_text', read):
            selected, uncertain = self.index.selection(ROOT / 'tools' / script)
        self.assertFalse(uncertain)
        return selected

    def test_the_edits_change_the_files(self):
        for name, (path, edit) in {**NEUTRAL_EDITS, **READ_EDITS}.items():
            text = (ROOT / path).read_text(encoding='utf-8')
            self.assertNotEqual(edit(text), text, name)

    def test_engine_only_header_edits_keep_the_chim_world_keys(self):
        for script in CHIM_STAGES:
            if not (ROOT / 'tools' / script).is_file():
                continue
            base = self.key(script)
            for name, edit in NEUTRAL_EDITS.items():
                self.assertEqual(self.key(script, edit), base, '%s re-keys %s' % (name, script))

    def test_what_the_world_reads_still_rekeys_it(self):
        base = self.key('chim_build.py')
        for name, edit in READ_EDITS.items():
            changed = self.key('chim_build.py', edit)
            self.assertNotEqual(changed.get(edit[0]), base.get(edit[0]), name)

    def test_the_probe_receipt_files_are_not_keyed_by_the_world(self):
        files = set(self.key('chim_build.py'))
        for name in ('cl_main.c', 'host.c', 'zone.c', 'r_efrag.c'):
            self.assertNotIn(SRC + name, files)
        self.assertTrue(str(self.key('chim_build.py')[SRC + 'quakedef.h']).startswith(engine_facts.PREFIX))

    def test_every_define_reader_reads_one_define_by_its_name(self):
        found = {}
        for path in sorted((ROOT / 'tools').rglob('*.py')):
            text = path.read_text(encoding='utf-8')
            for match in re.finditer(r'^def (%s)\(' % '|'.join(sorted(engine_facts.DEFINE_READ_FUNCTIONS_2)), text, re.M):
                body = text[match.start():text.find('\ndef ', match.end()) % len(text)]
                found[(path.relative_to(ROOT).as_posix(), match.group(1))] = body
        self.assertEqual(set(found), {('tools/engine_limits.py', 'define'), ('tools/engine_limits.py', '_mib_define'),
                                      ('tools/world_estimate.py', '_define'), ('tools/engine_limits.py', 'cvar_default')})
        for unit, body in found.items():
            # one regular expression built around the name: a #define line, or a cvar's {"name", "value"}
            self.assertRegex(body, r"""re\.search\(r'[^']*(define\\s\+|\\\{\\s\*")' \+ name \+""", unit)

    def test_only_the_heap_audit_keeps_the_probe_receipt(self):
        for path in sorted((ROOT / 'tools').rglob('*.py')):
            text = path.read_text(encoding='utf-8')
            for match in re.finditer(r'(\w+(?:\s*,\s*\w+)?)\s*=\s*compile_target_sizes\([^)]*\)(\[0\])?', text):
                if match.group(2) or match.group(1).replace(' ', '').endswith(',_'):
                    continue
                function = re.findall(r'^def (\w+)\(', text[:match.start()], re.M)[-1]
                self.assertIn((path.relative_to(ROOT).as_posix(), function), engine_facts.RECEIPT_WRITERS)


HEADERS = {
    'tools/engine_limits.py': '''
import re
from pathlib import Path
SOURCE = Path(__file__).resolve().parents[1] / 'engine/aga/src'
DEFINES = {'max_edicts': ('quakedef.h', 'MAX_EDICTS')}
def define(header, name, source=SOURCE):
    return int(re.search(r'#define\\s+' + name + r'\\s+(\\d+)', (Path(source) / header).read_text()).group(1))
def limits():
    return {key: define(header, name) for key, (header, name) in DEFINES.items()}
''',
    'tools/check_world_map_heap.py': '''
import hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PROBE_SOURCE = """#include "probe.h"
const unsigned int aw_size_box = sizeof(box_t);
"""
def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def compile_target_sizes(sdk):
    includes = [ROOT / 'engine/aga/src']
    return {'box': len(PROBE_SOURCE)}, {'main': digest(ROOT / 'engine/aga/src/cl_main.c')}
def audit_world_maps(out):
    sizes, abi = compile_target_sizes(None)
    Path(out).write_text(str(abi))
''',
    'tools/stage.py': '''
import engine_limits, check_world_map_heap
print(engine_limits.limits(), check_world_map_heap.compile_target_sizes(None)[0])
''',
    'tools/audit.py': '''
import engine_limits, check_world_map_heap
check_world_map_heap.audit_world_maps('x')
''',
    SRC + 'quakedef.h': '#ifndef QUAKEDEF_H\n#define QUAKEDEF_H\n#include "sound.h"\n#define MAX_EDICTS 600\n'
                        'void Host_Frame(float t);\n#endif\n',
    SRC + 'sound.h': '#include "vec.h"\nvoid S_StopSound(int e);\n',
    SRC + 'vec.h': 'typedef float vec3_t[3];\n',
    SRC + 'probe.h': '#include "vec.h"\ntypedef struct { vec3_t origin; int flags; } box_t;\nstruct edict_s;\n'
                     'typedef struct { int unrelated; } other_t;\n#define BOX_LIMIT 4\nint Box_Count(void);\n',
    SRC + 'cl_main.c': '#include "quakedef.h"\nvoid CL_Frame(void) { S_StopSound(0); }\n',
    'engine/aga/qc/world.qc': '',
}


class EngineFactsRuleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.write(HEADERS)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, files):
        for relative, text in files.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf-8')

    def key(self, script='stage.py', **options):
        index = build_cache.SourceIndex(self.root, top_format=build_cache.STAGE_TOP_FORMAT, **options)
        selected, uncertain = index.selection(self.root / 'tools' / script)
        self.assertFalse(uncertain)
        return {path: value for path, value in selected.items() if path.startswith('engine/')}

    def edited(self, relative, old, new, script='stage.py'):
        self.write(HEADERS)                                       # each edit against the same tree
        before = self.key(script)
        path = self.root / relative
        text = path.read_text(encoding='utf-8')
        self.assertIn(old, text)
        path.write_text(text.replace(old, new), encoding='utf-8')
        return before, self.key(script)

    def test_what_the_stage_keys(self):
        key = self.key()
        # quakedef.h for MAX_EDICTS (a define), probe.h and vec.h for the probe's box_t; sound.h holds nothing named
        self.assertEqual(set(key), {SRC + 'quakedef.h', SRC + 'probe.h', SRC + 'vec.h'})
        self.assertTrue(all(value.startswith(engine_facts.PREFIX) for value in key.values()))
        # the earlier method: whole files, the receipt's cl_main.c and every include (and not the probe's own header)
        self.assertEqual(set(self.key(engine_facts=False)), {SRC + name for name in (
            'quakedef.h', 'sound.h', 'vec.h', 'cl_main.c')})

    def test_new_prototypes_forward_declarations_and_unread_types_keep_the_key(self):
        for relative, old, new in (
                (SRC + 'quakedef.h', 'void Host_Frame(float t);', 'void Host_Frame(float t);\nint AW_New(void);'),
                (SRC + 'sound.h', 'void S_StopSound(int e);', 'void S_StopSound(int e);\nvoid S_MoveSound(int e);'),
                (SRC + 'probe.h', 'int unrelated;', 'int unrelated, more;'),
                (SRC + 'probe.h', 'struct edict_s;', 'struct edict_s;\nstruct client_s;'),
                (SRC + 'cl_main.c', 'S_StopSound(0);', 'S_StopSound(1);'),
                (SRC + 'quakedef.h', '#define MAX_EDICTS 600', '/* edicts */ #define MAX_EDICTS 600')):
            before, after = self.edited(relative, old, new)
            self.assertEqual(after, before, '%s: %s' % (relative, new))

    def test_read_facts_rekey(self):
        for relative, old, new in (
                (SRC + 'quakedef.h', 'MAX_EDICTS 600', 'MAX_EDICTS 601'),
                (SRC + 'probe.h', 'int flags;', 'int flags, more;'),
                (SRC + 'vec.h', 'float vec3_t[3]', 'double vec3_t[3]'),
                (SRC + 'quakedef.h', '#define MAX_EDICTS 600', '#ifdef BIG\n#define MAX_EDICTS 900\n#endif\n'
                                                              '#define MAX_EDICTS 600')):
            before, after = self.edited(relative, old, new)
            self.assertNotEqual(after, before, '%s: %s' % (relative, new))

    def test_the_receipt_counts_where_it_is_written(self):
        self.assertIn(SRC + 'cl_main.c', self.key('audit.py'))
        before, after = self.edited(SRC + 'cl_main.c', 'S_StopSound(0);', 'S_StopSound(1);', script='audit.py')
        self.assertNotEqual(after, before)

    def test_a_folder_named_whole_keeps_every_file_whole(self):
        self.write({'tools/lister.py': "from pathlib import Path\nimport engine_limits\nprint(engine_limits.limits(),"
                                       " sorted(Path('engine/aga/src').iterdir()))\n"})
        key = self.key('lister.py')
        self.assertIn(SRC + 'sound.h', key)
        self.assertFalse(any(value.startswith(engine_facts.PREFIX) for value in key.values()))

    def test_a_pasting_macro_keeps_the_files_whole(self):
        self.write({SRC + 'probe.h': HEADERS[SRC + 'probe.h'] + '#define UNUSED(x) u_##x\n'})
        self.assertTrue(any(value.startswith(engine_facts.PREFIX) for value in self.key().values()))   # not kept
        self.write({SRC + 'probe.h': '#include "vec.h"\n#define FIELD(x) f_##x\n'
                                     'typedef struct { vec3_t origin; int FIELD(flags); } box_t;\n'})
        self.assertFalse(any(value.startswith(engine_facts.PREFIX) for value in self.key().values()))

    def test_header_items(self):
        items = engine_facts.parse_header(
            '#ifdef A\n#define B 1 /* c */\n#endif\nstruct s;\ntypedef struct t { int f; } t_t;\n'
            'enum {E1, E2 = 3};\nextern int (*fp)(int x);\nint fn(int y);\nstatic inline int g(void) { return 1; }\n'
            '#pragma pack(2)\n')
        rows = [(sorted(item['defines']), item['always']) for item in items]
        self.assertEqual(rows, [(['B'], False), (['t', 't_t'], False), (['E1', 'E2'], False), (['fp'], False),
                                (['fn'], False), (['g'], False), ([], True)])
        self.assertEqual(items[0]['stack'], (('#ifdef A',),))
        self.assertIn('A', items[0]['uses'])


class EngineFactsTranslationTests(unittest.TestCase):
    """A reuse source keyed with whole engine files is compared by its C facts when its source tree proves it."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.old, self.new = self.base / 'old', self.base / 'new'
        for root in (self.old, self.new):
            for relative, text in HEADERS.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding='utf-8')
        self.run = self.base / 'run'
        self.run.mkdir()
        (self.run / 'build-state.json').write_text(json.dumps({
            'stage_cache': {'scope': 'units'},
            'steps': [{'name': 'chim', 'command': ['python3', str(self.old / 'tools' / 'stage.py')]}]}))

    def tearDown(self):
        self.temp.cleanup()

    def components(self, root, facts):
        index = build_cache.SourceIndex(root, top_format=build_cache.STAGE_TOP_FORMAT, engine_facts=facts)
        selected, _ = index.selection(root / 'tools' / 'stage.py')
        return {'stage': 'chim', 'sources': {'digest': build_cache.digest_json(selected), 'files': len(selected),
                                             'by_file': selected}}

    def compare(self):
        old = self.components(self.old, False)              # the record, as the earlier builder wrote it
        new = self.components(self.new, True)
        return build_cache.explain(old, engine_facts.translate(old, new, self.run, 'chim'))

    def test_an_engine_only_edit_compares_equal(self):
        path = self.new / SRC / 'quakedef.h'
        path.write_text(path.read_text().replace('void Host_Frame', 'int AW_New(void);\nvoid Host_Frame'))
        self.assertEqual(self.compare(), [])

    def test_a_record_of_the_first_reading_compares_equal(self):
        # records written between the first reading (cfacts1, merged 87983fd1) and version 2: equal when unchanged
        path = self.new / SRC / 'quakedef.h'
        path.write_text(path.read_text().replace('void Host_Frame', 'int AW_New(void);\nvoid Host_Frame'))
        record = self.components(self.old, 1)
        self.assertTrue(any(str(v).startswith('cfacts1:') for v in record['sources']['by_file'].values()))
        self.assertEqual(build_cache.explain(record, engine_facts.translate(record, self.components(self.new, True),
                                                                            self.run, 'chim')), [])

    def test_a_python_edit_beside_shows_alone(self):
        # v0.0.54 seyda-ui 3d6b612: a builder edit beside an engine-only header edit named every engine file too
        path = self.new / SRC / 'quakedef.h'
        path.write_text(path.read_text().replace('void Host_Frame', 'int AW_New(void);\nvoid Host_Frame'))
        stage = self.new / 'tools' / 'stage.py'
        stage.write_text(stage.read_text() + "print('more')\n")
        self.assertEqual(self.compare(), ['sources (tools/stage.py)'])

    def test_a_read_fact_still_shows(self):
        path = self.new / SRC / 'probe.h'
        path.write_text(path.read_text().replace('int flags;', 'int flags, more;'))
        self.assertEqual(self.compare(), ['sources (engine/aga/src/probe.h)'])

    def test_a_tree_that_is_not_the_records_is_not_trusted(self):
        path = self.new / SRC / 'quakedef.h'
        path.write_text(path.read_text().replace('void Host_Frame', 'int AW_New(void);\nvoid Host_Frame'))
        record = self.components(self.old, False)
        (self.old / SRC / 'sound.h').write_text('void S_StopSound(int e, int f);\n')   # changed after the run
        engine_facts._OLD_INDEXES.clear()
        changed = build_cache.explain(record, engine_facts.translate(record, self.components(self.new, True),
                                                                      self.run, 'chim'))
        self.assertIn('engine/aga/src/quakedef.h', changed[0])    # compared as before: the whole files differ


if __name__ == '__main__':
    unittest.main()
