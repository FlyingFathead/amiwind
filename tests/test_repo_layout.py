"""Regression checks for using one checked-in source tree after consolidation."""
from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
from build_aga import stage_runtime, runtime_sources
from mwad.paths import ensure_external, read_workspace


class RepositoryLayoutTests(unittest.TestCase):
    def test_staging_preserves_local_edits_and_ignores_build_products(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / 'source'
            for name in ('Makefile','COPYING','src/quakedef.h','src/aw_c2p.c',
                         'boot/bootcheck.asm','qc/world.qc'):
                p = source/name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('local source: '+name+'\n')
            (source/'obj').mkdir()
            (source/'obj/stale.o').write_bytes(b'not source')
            out = base/'external'
            out.mkdir()
            tree, hashes = stage_runtime(out, source)
            self.assertEqual((tree/'src/aw_c2p.c').read_text(), 'local source: src/aw_c2p.c\n')
            self.assertNotIn('obj/stale.o', hashes)
            self.assertFalse((tree/'obj').exists())
            with self.assertRaises(FileExistsError):
                stage_runtime(out, source)

    def test_incomplete_bundled_source_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'Bundled runtime source missing'):
                runtime_sources(Path(tmp))

    def test_both_repository_names_protect_private_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ('amiwind', 'morrowind-amiga-demake'):
                with self.subTest(name=name):
                    (root/'pyproject.toml').write_text('[project]\nname = "'+name+'"\n')
                    with self.assertRaises(ValueError):
                        ensure_external(root/'private')

    def test_legacy_and_new_workspaces_remain_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ('amiwind', 'morrowind-amiga-demake'):
                with self.subTest(name=name):
                    (root/'workspace.json').write_text(json.dumps({'format':1,'project':name}))
                    self.assertEqual(read_workspace(root)[1]['project'], name)
