# SPDX-License-Identifier: GPL-3.0-only
"""A version change rekeys only what shows the version (BUILD-CHIM-KEY-VERSION-48).

The maintainer, 2026-10-24 02:51 +0300 / 2026-10-23 23:51 UTC: "A VERSION NUMBER CHANGE SHOULD NOT FUCKING CAUSE THIS
KIND OF A FUCKING HULABALLOO". v0.0.48 had to ship its rc1 image as the final because the label alone re-keyed the
whole CHIM world: tools/project_version.py read the version file at import, so every stage that imported it keyed
the file. This gate test fails when a stage script of tools/build.py keys the version file without showing the
version in its output (read only, no build). The engine and the image show it and are rebuilt by policy."""
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_cache  # noqa: E402
import project_version  # noqa: E402
import reuse_report  # noqa: E402

# Stage scripts whose outputs show the version: the CHIM Progress Tracker data names the working version
# (tools/cell_progress.py working_version). Nothing else may key the version file.
SHOWS_VERSION = frozenset({'cell_progress_build.py'})
# The CHIM world's stages: v0.0.48's rc1 label rebuilt them all
CHIM_STAGES = ('chim_build.py', 'chim_rooms.py', 'chim_room_batches.py', 'chim_interiors.py', 'chim_town.py')


def stage_scripts():
    """Every tools/*.py script tools/build.py starts as a stage (its tool('NAME.py', ...) calls)."""
    text = (ROOT / 'tools' / 'build.py').read_text(encoding='utf-8')
    return sorted(set(re.findall(r"tool\(\s*'([A-Za-z0-9_]+\.py)'", text)))


class RepositoryVersionKeyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = build_cache.SourceIndex(ROOT, top_format=build_cache.STAGE_TOP_FORMAT)

    def keys_version(self, script):
        selected, uncertain = self.index.selection(ROOT / 'tools' / script)
        self.assertFalse(uncertain, script)
        return build_cache.VERSION_FILE in selected

    def test_the_builder_starts_stages(self):
        scripts = stage_scripts()
        self.assertIn('chim_build.py', scripts)
        self.assertGreater(len(scripts), 8)

    def test_no_stage_keys_the_version_unless_it_shows_it(self):
        keyed = [script for script in stage_scripts()
                 if (ROOT / 'tools' / script).is_file() and self.keys_version(script)]
        self.assertEqual([script for script in keyed if script not in SHOWS_VERSION], [],
                         'a version change would rebuild these stages (build_cache.VERSION_HIDDEN_UNITS)')

    def test_the_chim_world_stages_never_key_the_version(self):
        for script in CHIM_STAGES:
            if (ROOT / 'tools' / script).is_file():
                self.assertFalse(self.keys_version(script), script)
                self.assertFalse(self.index.names_version(ROOT / 'tools' / script), script)

    def test_the_tracker_still_keys_the_version_it_shows(self):
        self.assertTrue(self.keys_version('cell_progress_build.py'))

    def test_no_stage_is_listed_as_version_stamped(self):
        self.assertEqual(reuse_report.VERSION_STAMPED, frozenset())


STAGE_REFUSAL = '''
from project_version import run_version, require_private_test_version
require_private_test_version(run_version(), [])
'''
STAGE_SHOWS = '''
from project_version import public_version
print(public_version())
'''
STAGE_IMPORT = '''
import project_version
print(project_version.CREDITS)
'''


class VersionKeyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repository = Path(self.temp.name) / 'repo'
        tools = self.repository / 'tools'
        tools.mkdir(parents=True)
        shutil.copyfile(ROOT / 'tools' / 'project_version.py', tools / 'project_version.py')
        for name, text in (('stage_refusal.py', STAGE_REFUSAL), ('stage_shows.py', STAGE_SHOWS),
                           ('stage_import.py', STAGE_IMPORT)):
            (tools / name).write_text(text, encoding='utf-8')
        self.version('0.0.49-rc1')
        (self.repository / 'CHIM_VERSION').write_text('0.2.2\n', encoding='utf-8')

    def tearDown(self):
        self.temp.cleanup()

    def version(self, value):
        (self.repository / 'VERSION').write_text(value + '\n', encoding='utf-8')

    def selections(self):
        index = build_cache.SourceIndex(self.repository, top_format=build_cache.STAGE_TOP_FORMAT)
        return {name: index.selection(self.repository / 'tools' / name)
                for name in ('stage_refusal.py', 'stage_shows.py', 'stage_import.py')}

    def test_only_a_stage_that_shows_the_version_keys_it(self):
        selected = self.selections()
        for name, (files, uncertain) in selected.items():
            self.assertFalse(uncertain, name)
        self.assertIn('VERSION', selected['stage_shows.py'][0])
        self.assertNotIn('VERSION', selected['stage_refusal.py'][0])
        self.assertNotIn('VERSION', selected['stage_import.py'][0])

    def test_rc_to_final_rekeys_only_the_stage_that_shows_it(self):
        before = self.selections()
        self.version('0.0.49')
        after = self.selections()
        changed = sorted(name for name in before if before[name] != after[name])
        self.assertEqual(changed, ['stage_shows.py'])


class RunVersionTests(unittest.TestCase):
    def test_the_builder_value_comes_first(self):
        old = os.environ.get('AMIWIND_RUN_VERSION')
        os.environ['AMIWIND_RUN_VERSION'] = '0.0.49-dev7'
        try:
            self.assertEqual(project_version.run_version(), '0.0.49-dev7')
        finally:
            if old is None:
                os.environ.pop('AMIWIND_RUN_VERSION', None)
            else:
                os.environ['AMIWIND_RUN_VERSION'] = old

    def test_the_tree_version_otherwise(self):
        old = os.environ.pop('AMIWIND_RUN_VERSION', None)
        try:
            self.assertEqual(project_version.run_version(), project_version.public_version())
        finally:
            if old is not None:
                os.environ['AMIWIND_RUN_VERSION'] = old

    def test_the_module_version_is_read_when_asked(self):
        self.assertEqual(project_version.VERSION, project_version.public_version())
        with self.assertRaises(AttributeError):
            project_version.NO_SUCH_NAME


if __name__ == '__main__':
    unittest.main()
