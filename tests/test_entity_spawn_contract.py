"""Every entity the map converters write must load silently through the game
logic (QC-AW-FLAME-SPAWN-32).

Quake's server spawns every map entity through QuakeC (pr_edict.c
ED_LoadFromFile): a key without a declared field prints "'<key>' is not a
field", a classname without a spawn function prints "No spawn function for:"
and dumps the whole edict to the console. So each classname the converters
write needs a spawn function in engine/aga/qc, and each key needs a declared
field, a leading underscore (a utility key the loader discards) or handling of
its own in the engine's loader. Static flames are the case that broke: the
engine reads aw_flame entities from the entity text itself, the game logic did
not know them, and every Census load printed 51 edict dumps.
"""
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
QC = ROOT / 'engine/aga/qc'
SRC = ROOT / 'engine/aga/src'
TOOLS = ROOT / 'tools'
sys.path.insert(0, str(TOOLS))

# Entities the compilers consume before the map reaches the game: ericw-tools
# light reads "light" entities, qbsp merges "func_detail" brushes into the
# world, and "info_null" only marks points for the converters (light targets,
# temporary render-pool holders), which drop it again before the final BSP.
COMPILER_ONLY_CLASSES = {'light', 'func_detail', 'info_null'}
# Keys of those compiler-only light entities (ericw-tools light keys).
COMPILER_ONLY_KEYS = {'light', 'delay', 'style'}
QC_TYPES = {'float': 2, 'vector': 3, 'string': 1, 'entity': 4}


def _qc_source():
    text = '\n'.join((QC / name).read_text(encoding='utf-8') for name in ('defs.qc', 'world.qc'))
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)


def qc_fields():
    """name -> declared type for every entity field in the game logic."""
    fields = {}
    for kind, names in re.findall(r'(?m)^\s*\.(\w+(?:\s*\([^)]*\))?)\s+([^;]+);', _qc_source()):
        for name in names.split(','):
            fields[name.strip()] = kind.replace(' ', '')
    return fields


def qc_spawn_functions():
    """Functions with a body and no arguments: what ED_FindFunction can spawn."""
    return set(re.findall(r'(?m)^\s*void\s*\(\s*\)\s*(\w+)\s*=\s*\{', _qc_source()))


def qc_function_body(name):
    source = _qc_source()
    start = re.search(r'void\s*\(\s*\)\s*' + name + r'\s*=\s*\{', source).end()
    return source[start:source.index('};', start)]


def engine_loader_keys():
    """Keys ED_ParseEdict handles before the field lookup (anglehack, render
    metadata), read from the engine source, not from a list kept here."""
    source = (SRC / 'pr_edict.c').read_text(encoding='latin-1')
    body = source[source.index('char *ED_ParseEdict'):source.index('ED_LoadFromFile')]
    handled = set(re.findall(r'strcmp\s*\(\s*keyname\s*,\s*"(\w+)"\s*\)', body))
    if re.search(r'strcmp\s*\(\s*com_token\s*,\s*"angle"\s*\)', body):
        handled.add('angle')  # rewritten to "angles" before the lookup
    return handled


def converter_entity_literals():
    """(classnames, keys) written as entity text or entity dicts in tools/."""
    classes, keys = {}, {}
    for path in sorted(TOOLS.glob('**/*.py')):
        text = path.read_text(encoding='utf-8')
        for name in re.findall(r'"classname" "([A-Za-z_]\w*)"', text):
            classes.setdefault(name, set()).add(path.name)
        for name in re.findall(r"""['"]classname['"]\s*:\s*['"]([A-Za-z_]\w*)['"]""", text):
            classes.setdefault(name, set()).add(path.name)
        # A key at the start of an entity line inside a map-text literal.
        for name in re.findall(r'(?:\\n|\{|[\'(])"([A-Za-z_]\w*)" "', text):
            keys.setdefault(name, set()).add(path.name)
    return classes, keys


def parse_entities(text):
    """Entity text -> list of key/value dicts (the COM_Parse token rules)."""
    entities, current, key = [], None, None
    for value, brace in re.findall(r'"([^"]*)"|([{}])', text):
        if brace == '{':
            current, key = {}, None
        elif brace == '}':
            entities.append(current)
            current = None
        elif key is None:
            key = value
        else:
            current[key] = value
            key = None
    return entities


class EntitySpawnContractTests(unittest.TestCase):
    def assert_loads_silently(self, entity, fields, spawn, engine_keys):
        classname = entity['classname']
        self.assertIn(classname, spawn, f'no QuakeC spawn function for {classname}: '
                      '"No spawn function" and an edict dump at every map load')
        for key in entity:
            if key.startswith('_') or key in engine_keys:
                continue
            self.assertIn(key, fields, f"{classname} key {key}: \"'{key}' is not a field\" at every map load")

    def test_converter_classnames_have_spawn_functions(self):
        classes, _ = converter_entity_literals()
        spawn = qc_spawn_functions()
        self.assertIn('aw_flame', classes, 'the scan no longer sees the static flame writer')
        for name, files in sorted(classes.items()):
            if name in COMPILER_ONLY_CLASSES:
                continue
            with self.subTest(classname=name):
                self.assertIn(name, spawn, f'{name} written by {sorted(files)} has no spawn function')

    def test_converter_keys_are_declared_fields(self):
        _, keys = converter_entity_literals()
        fields, engine_keys = qc_fields(), engine_loader_keys()
        self.assertTrue({'aw_flame_size', 'aw_flame_shape', 'wad'} <= set(keys),
                        'the scan no longer sees the flame and worldspawn keys')
        for name, files in sorted(keys.items()):
            if name.startswith('_') or name in engine_keys or name in COMPILER_ONLY_KEYS:
                continue
            with self.subTest(key=name):
                self.assertIn(name, fields, f'{name} written by {sorted(files)} is not a QuakeC field')

    def test_static_flame_writer_output_loads_silently_and_keeps_engine_keys(self):
        import prepare_mesh_bsp
        ref = {'position': [128.0, -64.0, 32.0], 'scale': 1.5, 'rotation_radians': [0.0, 0.0, 0.7]}
        model = {'flames': [[1.0, 2.0, 3.0, 1.25], [0.0, 0.0, 8.0, 2.0, 6.0, 4.0, 3.0]]}
        saved = prepare_mesh_bsp.NO_FLAMES
        prepare_mesh_bsp.NO_FLAMES = False
        try:
            texts = prepare_mesh_bsp.flame_entities(ref, model, (0.0, 0.0))
        finally:
            prepare_mesh_bsp.NO_FLAMES = saved
        entities = parse_entities('\n'.join(texts))
        self.assertEqual([e['classname'] for e in entities], ['aw_flame', 'aw_flame'])
        self.assertNotIn('aw_flame_shape', entities[0])
        self.assertIn('aw_flame_shape', entities[1])
        fields, spawn, engine_keys = qc_fields(), qc_spawn_functions(), engine_loader_keys()
        for entity in entities:
            self.assert_loads_silently(entity, fields, spawn, engine_keys)
        # Declared with the types the values parse as (ED_ParseEpair).
        self.assertEqual(fields['aw_flame_size'], 'float')
        self.assertEqual(fields['aw_flame_shape'], 'vector')
        self.assertEqual(len(entities[1]['aw_flame_shape'].split()), 3)
        # The engine's static-flame table still reads these same names.
        reader = (SRC / 'aw_guard_torch.c').read_text(encoding='latin-1')
        reader = reader[reader.index('static void static_flames_load'):]
        reader = reader[:reader.index('\n}\n')]
        for name in ('"aw_flame"', '"aw_flame_size"', '"aw_flame_shape"', '"origin"'):
            self.assertIn(name, reader)
        self.assertIn('world->entities', reader, 'static flames must come from the map text, not live edicts')

    def test_aw_flame_spawn_removes_the_edict_like_the_old_load_path(self):
        # Before the fix the loader freed the unknown edict (ED_Free); the spawn
        # function must free it too, so edict numbering and counts do not change.
        self.assertRegex(qc_function_body('aw_flame').strip(), r'^remove\s*\(\s*self\s*\)\s*;$')
        declared = re.search(r'void\s*\(\s*entity\s+\w+\s*\)\s*remove\s*=\s*#(\d+)\s*;', _qc_source())
        self.assertIsNotNone(declared)
        table = (SRC / 'pr_cmds.c').read_text(encoding='latin-1').split('builtin_t pr_builtin[] =', 1)[1]
        table = re.sub(r'/\*.*?\*/|//[^\n]*', '', table.split('#ifdef QUAKE2', 1)[0], flags=re.S)
        self.assertEqual(re.findall(r'\bPF_\w+\b', table).index('PF_Remove'), int(declared.group(1)))
        remove = (SRC / 'pr_cmds.c').read_text(encoding='latin-1')
        remove = remove[remove.index('void PF_Remove'):]
        self.assertIn('ED_Free', remove[:remove.index('\n}')])

    def test_worldspawn_wad_key_is_declared(self):
        fields = qc_fields()
        self.assertEqual(fields.get('wad'), 'string')
        worldspawn = parse_entities('{\n"classname" "worldspawn"\n"wad" "terrain.wad"\n"message" "Vvardenfell"\n}')[0]
        self.assert_loads_silently(worldspawn, fields, qc_spawn_functions(), engine_loader_keys())

    def test_compiled_progs_declare_flame_fields_without_moving_old_fields(self):
        compiler = os.environ.get('QCC_PATH') or shutil.which('qcc-host')
        if not compiler:
            self.skipTest('set QCC_PATH to the validated host QCC')
        from build_aga import validate_quakec

        def compile_fields(world_text):
            with tempfile.TemporaryDirectory() as tmp:
                qc = Path(tmp) / 'qc'
                qc.mkdir()
                for name in ('defs.qc', 'progs.src'):
                    shutil.copyfile(QC / name, qc / name)
                (qc / 'world.qc').write_text(world_text, encoding='utf-8', newline='\n')
                result = subprocess.run([str(Path(compiler).resolve())], cwd=qc, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                validate_quakec(Path(tmp) / 'progs.dat')  # version and system-field CRC
                raw = (Path(tmp) / 'progs.dat').read_bytes()
            header = struct.unpack_from('<15i', raw)
            names = {}
            for i in range(header[7]):
                kind, offset, name = struct.unpack_from('<HHi', raw, header[6] + i * 8)
                start = header[10] + name
                names[raw[start:raw.index(b'\0', start)].decode('ascii')] = (kind & 0x7fff, offset)
            functions = set()
            for i in range(header[9]):
                name = struct.unpack_from('<9i', raw, header[8] + i * 36)[4]
                start = header[10] + name
                functions.add(raw[start:raw.index(b'\0', start)].decode('ascii'))
            return names, functions, header[14]

        world = (QC / 'world.qc').read_text(encoding='utf-8')
        fields, functions, size = compile_fields(world)
        self.assertEqual(fields['aw_flame_size'][0], QC_TYPES['float'])
        self.assertEqual(fields['aw_flame_shape'][0], QC_TYPES['vector'])
        self.assertEqual(fields['wad'][0], QC_TYPES['string'])
        self.assertIn('aw_flame', functions)
        # Without the block every other field keeps the same offset.
        start = world.index('/* Static flames (QC-AW-FLAME-SPAWN-32)')
        base, _, base_size = compile_fields(world[:start])
        new = {'aw_flame_size', 'aw_flame_shape', 'aw_flame_shape_x', 'aw_flame_shape_y',
               'aw_flame_shape_z', 'wad'}
        self.assertEqual({k: v for k, v in fields.items() if k not in new}, base)
        self.assertEqual(size - base_size, 5)  # one float, one vector, one string per edict


if __name__ == '__main__':
    unittest.main()
