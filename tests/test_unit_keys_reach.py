# SPDX-License-Identifier: GPL-3.0-only
"""Unit keys count only the settings their code reads (BUILD-UNIT-KEYS-REACH-64).

The v0.0.64-dev5 build stopped in its first minute: the hollow bevels and collision mesh settings, added to
tools/mesh_geometry_env.py and tools/collision_source_env.py as top-level constants, re-keyed every NPC, creature,
player-body and resident bake that imports those modules (import-time code counts in the reach of every function of
its module), and the model hull setting, held there as a constant, was keyed by all of them though only the
collision code reads it. These tests keep both narrowings and prove a setting that IS read still re-keys."""
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import pass_cache  # noqa: E402
import unit_store  # noqa: E402

LIB = textwrap.dedent('''\
    import os

    HULL_VARIABLE = 'AMIWIND_TEST_HULL'
    BEVEL_VARIABLE = 'AMIWIND_TEST_BEVELS'


    def hull_mode():
        return os.environ.get(HULL_VARIABLE, 'auto')


    from contextlib import contextmanager


    @contextmanager
    def hull_override(mode):
        before = os.environ.get(HULL_VARIABLE)
        os.environ[HULL_VARIABLE] = mode
        yield mode


    def head_detail():
        return 'budget'


    def bevels():
        return os.environ.get(BEVEL_VARIABLE, '2')
    ''')
BAKES = textwrap.dedent('''\
    import testlib


    def bake_head(task):
        return testlib.head_detail()


    def bake_collision(task):
        return testlib.hull_mode()


    def bake_override(task):
        with testlib.hull_override('chain'):
            return 1


    def bake_literal(task):
        import os
        return os.environ.get('AMIWIND_TEST_BEVELS')
    ''')


class Repo:
    def __enter__(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        (self.root / 'tools').mkdir()
        (self.root / 'tools/testlib.py').write_text(LIB, encoding='utf-8')
        (self.root / 'tools/testbakes.py').write_text(BAKES, encoding='utf-8')
        return self

    def __exit__(self, *_):
        self.folder.cleanup()

    def entry(self, function):
        return [(str(self.root / 'tools/testbakes.py'), function)]


class UnreadSettings(unittest.TestCase):
    NAMES = {'AMIWIND_TEST_HULL', 'AMIWIND_TEST_BEVELS'}

    def test_constant_only_is_unread(self):
        with Repo() as repo:
            self.assertEqual(unit_store.unread_settings(self.NAMES, repo.entry('bake_head'), repo.root), self.NAMES)

    def test_reading_function_counts(self):
        with Repo() as repo:
            self.assertEqual(unit_store.unread_settings(self.NAMES, repo.entry('bake_collision'), repo.root),
                             {'AMIWIND_TEST_BEVELS'})

    def test_wrapped_function_counts_when_called(self):
        """A @contextmanager function is import-time code of its module, but it reads the setting only when called:
        a bake that calls it is keyed by the setting (bake_head above, which does not, is not)."""
        with Repo() as repo:
            self.assertEqual(unit_store.unread_settings(self.NAMES, repo.entry('bake_override'), repo.root),
                             {'AMIWIND_TEST_BEVELS'})

    def test_literal_elsewhere_counts(self):
        with Repo() as repo:
            self.assertEqual(unit_store.unread_settings(self.NAMES, repo.entry('bake_literal'), repo.root),
                             {'AMIWIND_TEST_HULL'})


class KeyedEnvironment(unittest.TestCase):
    def test_unread_value_change_keeps_the_key(self):
        """The case of v0.0.64-dev5: the model hull default chain -> auto keeps a head bake's key, and the unit
        stored under the old full set is found under it."""
        with Repo() as repo:
            entry = repo.entry('bake_head')
            before = {'AMIWIND_TEST_HULL': 'chain', 'AMIWIND_TEST_BEVELS': None}
            after = {'AMIWIND_TEST_HULL': 'auto', 'AMIWIND_TEST_BEVELS': None}
            from unittest.mock import patch
            with patch.dict(unit_store.SETTING_VALUES, {'AMIWIND_TEST_HULL': ('auto', 'chain')}):
                old_key, _ = unit_store.keyed_environment(before, entry, repo.root)
                new_key, older = unit_store.keyed_environment(after, entry, repo.root)
            self.assertEqual(old_key, new_key)
            self.assertEqual(new_key, {})
            self.assertIn(before, older)            # the stored full set is looked up
            self.assertIn({'AMIWIND_TEST_HULL': 'auto'}, older)   # a setting new in the code: absent before

    def test_read_value_change_rekeys(self):
        """A bake that reads the model hull is keyed by it: chain and auto give different keys, and no older set
        of the other value is looked up."""
        with Repo() as repo:
            entry = repo.entry('bake_collision')
            before = {'AMIWIND_TEST_HULL': 'chain', 'AMIWIND_TEST_BEVELS': None}
            after = {'AMIWIND_TEST_HULL': 'auto', 'AMIWIND_TEST_BEVELS': None}
            old_key, _ = unit_store.keyed_environment(before, entry, repo.root)
            new_key, older = unit_store.keyed_environment(after, entry, repo.root)
            self.assertNotEqual(old_key, new_key)
            self.assertEqual(new_key, {'AMIWIND_TEST_HULL': 'auto'})
            self.assertNotIn(before, older)

    def test_read_bevels_rekeys(self):
        with Repo() as repo:
            entry = repo.entry('bake_literal')
            one, _ = unit_store.keyed_environment({'AMIWIND_TEST_BEVELS': '0'}, entry, repo.root)
            two, _ = unit_store.keyed_environment({'AMIWIND_TEST_BEVELS': '2'}, entry, repo.root)
            self.assertNotEqual(one, two)

    def test_no_bare_setting_text_in_unit_store(self):
        """unit_store is code every cache opener reaches: a setting name written whole there would be keyed by all
        of them, a bare prefix would key every setting."""
        text = (ROOT / 'tools/unit_store.py').read_text(encoding='utf-8')
        self.assertNotRegex(text, r"""['"]AMIWIND_(?![A-Z0-9_]*['"])""")   # no bare prefix
        self.assertNotRegex(text, r"""['"]AMIWIND_MODEL_HULL['"]""")
        # as the key code reads it (joined literals are folded): only the work place setting, never every setting
        from build_cache import ENV_ANY, SourceIndex, STAGE_TOP_FORMAT, environment_names
        index = SourceIndex(ROOT, top_format=STAGE_TOP_FORMAT)
        _, _, uncertain, constants = index._closure_symbols('tools/unit_store.py', 'test::unit_store::keys',
                                                            entry='keyed_environment')
        names = environment_names(constants, uncertain)
        self.assertNotIn(ENV_ANY, names)
        self.assertNotIn('AMIWIND_MODEL_HULL', names)


class PreviousOptions(unittest.TestCase):
    def test_stored_under_old_options_is_found_and_moved(self):
        with tempfile.TemporaryDirectory() as folder:
            old = pass_cache.UnitCache('test-unit', {'environment': {'AMIWIND_TEST_HULL': 'chain'}}, 's', folder)
            old.store_files({'unit': 1}, {'value': 7}, {'a.bin': b'abc'})
            new = pass_cache.UnitCache('test-unit', {'environment': {}}, 's', folder,
                                       previous_options=[{'environment': {'AMIWIND_TEST_HULL': 'chain'}}])
            self.assertEqual(new.load_unit({'unit': 1}), ({'value': 7}, {'a.bin': b'abc'}))
            plain = pass_cache.UnitCache('test-unit', {'environment': {}}, 's', folder)
            self.assertEqual(plain.load_unit({'unit': 1}), ({'value': 7}, {'a.bin': b'abc'}))  # stored again

    def test_other_options_never_match(self):
        with tempfile.TemporaryDirectory() as folder:
            old = pass_cache.UnitCache('test-unit', {'environment': {'AMIWIND_TEST_HULL': 'chain'}}, 's', folder)
            old.store_files({'unit': 1}, {'value': 7}, {'a.bin': b'abc'})
            new = pass_cache.UnitCache('test-unit', {'environment': {'AMIWIND_TEST_HULL': 'auto'}}, 's', folder)
            self.assertIsNone(new.load_unit({'unit': 1}))


class ModuleSplit(unittest.TestCase):
    def test_new_settings_live_in_their_own_modules(self):
        """mesh_geometry_env.py and collision_source_env.py are import-time code of every bake that imports them:
        the hollow bevels and collision mesh settings live in hollow_bevels_env.py and collision_mesh_env.py."""
        for path, word in (('tools/mesh_geometry_env.py', 'HOLLOW_BEVELS'),
                           ('tools/collision_source_env.py', 'COLLISION_MESH')):
            self.assertNotIn(word, (ROOT / path).read_text(encoding='utf-8'), path)
        import hollow_bevels_env
        import collision_mesh_env
        saved = os.environ.pop(hollow_bevels_env.HOLLOW_BEVELS_VARIABLE, None)
        try:
            self.assertIn(hollow_bevels_env.hollow_bevels_default(), hollow_bevels_env.HOLLOW_BEVELS)
        finally:
            if saved is not None:
                os.environ[hollow_bevels_env.HOLLOW_BEVELS_VARIABLE] = saved
        self.assertIn(collision_mesh_env.collision_mesh_mode(), collision_mesh_env.COLLISION_MESHES)


if __name__ == '__main__':
    unittest.main()
