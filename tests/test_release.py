import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from release import create_candidate, inspect_source, release, validate_candidate
from release import (INHERITED_PREFIXES, WHITESPACE_BASELINE, check_source_whitespace,
                     load_whitespace_baseline, whitespace_baseline, whitespace_baseline_record,
                     write_whitespace_baseline)

INHERITED = 'docs/aga/COPYING.NEWLIB'
LEGACY = b'Historical text \nClean line\n\n'


def fixture(root):
    root.mkdir()
    (root / "tools").mkdir()
    (root / "README.md").write_text("Synthetic source fixture\n")
    (root / "pyproject.toml").write_text('[project]\nversion = "0.1.0"\n')
    (root / "VERSION").write_text('0.1.0\n')
    (root / "tools/release-files.json").write_text(json.dumps(["README.md", "VERSION", "pyproject.toml", "tools/release-files.json"]))


class Release(unittest.TestCase):
    def test_only_project_authored_source_graphic_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            fixture(root)
            name = 'docs/images/amiwind-shared-sky-build-comparison.svg'
            (root / name).parent.mkdir(parents=True)
            (root / name).write_text('<svg xmlns="http://www.w3.org/2000/svg"/>\n')
            listing = root / 'tools/release-files.json'
            base = json.loads(listing.read_text())
            listing.write_text(json.dumps(base + [name]) + '\n')
            inspect_source(root)
            (root / name).write_bytes(b'not text\0')
            with self.assertRaisesRegex(ValueError, 'binary or oversized'):
                inspect_source(root)
            (root / name).unlink()
            other = 'docs/images/unreviewed.svg'
            (root / other).write_text('<svg/>\n')
            listing.write_text(json.dumps(base + [other]) + '\n')
            with self.assertRaisesRegex(ValueError, 'Unexpected distributable'):
                inspect_source(root)

    def test_only_selected_bounded_documentation_clip_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/"repo"
            fixture(root)
            media = root/'docs/images'
            media.mkdir(parents=True)
            name = 'docs/images/amiwind-v0.0.23-dev2-port.gif'
            allowlist = root/'tools/release-files.json'
            paths = json.loads(allowlist.read_text()) + ['.gitignore']
            (root/'.gitignore').write_text('*.gif\n!/' + name + '\n')
            allowlist.write_text(json.dumps(paths + [name]) + '\n')
            (root/name).write_bytes(b'GIF89a\0')
            inspect_source(root)
            for invalid in (b'not a GIF', b'GIF89a' + b'\0'*4194304):
                (root/name).write_bytes(invalid)
                with self.assertRaisesRegex(ValueError, 'Invalid public GIF'):
                    inspect_source(root)
            other = 'docs/images/unreviewed.gif'
            allowlist.write_text(json.dumps(paths + [other]) + '\n')
            (root/name).unlink()
            (root/other).write_bytes(b'GIF89a\0')
            with self.assertRaisesRegex(ValueError, 'Unexpected distributable'):
                inspect_source(root)

    def test_selected_screenshot_requires_tracking_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'repo';fixture(root)
            name='docs/images/amiwind-v0.0.24-rc3-dagoth.png'
            (root/name).parent.mkdir(parents=True);(root/name).write_bytes(b'\x89PNG\r\n\x1a\n')
            (root/'.gitignore').write_text('*.png\n')
            listing=root/'tools/release-files.json'
            listing.write_text(json.dumps(json.loads(listing.read_text())+[name,'.gitignore'])+'\n')
            with self.assertRaisesRegex(ValueError,'gitignore exception'):inspect_source(root)
            (root/'.gitignore').write_text('*.png\n!/'+name+'\n')
            inspect_source(root)

    def test_unknown_content_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/"repo"
            fixture(root)
            (root / "accidental.mp3").write_bytes(b"example")
            with self.assertRaises(ValueError):
                inspect_source(root)

    def test_reproducible_archive_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/"repo"
            fixture(root)
            a, b = Path(tmp)/"a.zip", Path(tmp)/"b.zip"
            create_candidate(root, a)
            create_candidate(root, b)
            self.assertEqual(hashlib.sha256(a.read_bytes()).digest(), hashlib.sha256(b.read_bytes()).digest())
            self.assertEqual(validate_candidate(root, a)["status"], "passed")
            unpacked = Path(tmp)/"unpacked"
            with zipfile.ZipFile(a) as z:
                z.extractall(unpacked)
            self.assertEqual(set(inspect_source(unpacked/"amiwind")), set(inspect_source(root)))
            with zipfile.ZipFile(a, "a") as z:
                z.writestr("amiwind/extra.dat", b"test")
            with self.assertRaises(ValueError):
                validate_candidate(root, a)

    def test_existing_release_is_immutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, workspace = Path(tmp)/"repo", Path(tmp)/"workspace"
            fixture(root)
            first = release(root, workspace)
            before = Path(first["archive"]).read_bytes()
            with self.assertRaises(ValueError):
                release(root, workspace)
            self.assertEqual(before, Path(first["archive"]).read_bytes())

    def test_whitespace_blocks_inspection_and_packaging(self):
        for bad in (b'word \n', b'word\t\n', b' \n', b'    \n', b' \tword\n', b'word\n\n'):
            with self.subTest(source=bad), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / 'repo'
                fixture(root)
                (root / 'README.md').write_bytes(bad)
                with self.assertRaisesRegex(ValueError, 'whitespace check failed'):
                    inspect_source(root)
                candidate = Path(tmp) / 'candidate.zip'
                with self.assertRaisesRegex(ValueError, 'whitespace check failed'):
                    create_candidate(root, candidate)
                self.assertFalse(candidate.exists())

    # RELEASE-WS-BASELINE-VERSION-33: inherited files are recognised from the last PUBLISHED release
    # (docs/WHITESPACE-BASELINE.json), not from a docs/PATCH-v<VERSION>.json made by hand per VERSION.
    def inherited_fixture(self, root, version='0.1.0'):
        fixture(root)
        (root / 'VERSION').write_text(version + '\n')
        (root / 'pyproject.toml').write_text(f'[project]\nversion = "{version}"\n')
        (root / 'docs/aga').mkdir(parents=True)
        (root / INHERITED).write_bytes(LEGACY)
        record = {'note': 'test', 'release': '0.0.32', 'commit': 'a' * 40,
                  'files': {INHERITED: hashlib.sha256(LEGACY).hexdigest()}}
        (root / WHITESPACE_BASELINE).write_text(json.dumps(record, indent=2) + '\n')
        allowlist = root / 'tools/release-files.json'
        allowlist.write_text(json.dumps(json.loads(allowlist.read_text()) + [INHERITED, WHITESPACE_BASELINE]) + '\n')

    def test_new_version_needs_no_patch_file_for_unchanged_inherited_files(self):
        for version in ('0.1.0', '0.0.33-dev1', '0.0.34'):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / 'repo'
                self.inherited_fixture(root, version)
                self.assertEqual(list((root / 'docs').glob('PATCH-*')), [])
                inspect_source(root)
                candidate = Path(tmp) / 'candidate.zip'
                create_candidate(root, candidate)
                self.assertEqual(validate_candidate(root, candidate)['status'], 'passed')

    def test_new_whitespace_in_our_own_file_still_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            self.inherited_fixture(root)
            (root / 'README.md').write_bytes(b'Synthetic source fixture \n')
            with self.assertRaisesRegex(ValueError, r'README\.md:1: trailing whitespace') as caught:
                inspect_source(root)
            self.assertNotIn(INHERITED, str(caught.exception))

    def test_edited_inherited_file_is_checked_in_full(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            self.inherited_fixture(root)
            (root / INHERITED).write_bytes(LEGACY.replace(b'Clean line', b'Edited line'))
            with self.assertRaises(ValueError) as caught:
                inspect_source(root)
            # The untouched historical defects count once the file is edited.
            self.assertIn(f'{INHERITED}:1: trailing whitespace', str(caught.exception))
            self.assertIn(f'{INHERITED}:3: blank line at EOF', str(caught.exception))

    def test_baseline_never_exempts_project_authored_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            self.inherited_fixture(root)
            own = b'Synthetic source fixture \n'
            (root / 'README.md').write_bytes(own)
            record = json.loads((root / WHITESPACE_BASELINE).read_text())
            record['files']['README.md'] = hashlib.sha256(own).hexdigest()
            (root / WHITESPACE_BASELINE).write_text(json.dumps(record, indent=2) + '\n')
            with self.assertRaisesRegex(ValueError, r'README\.md:1: trailing whitespace'):
                inspect_source(root)

    def test_patch_file_is_not_a_whitespace_baseline_and_missing_baseline_says_what_to_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            self.inherited_fixture(root)
            (root / WHITESPACE_BASELINE).unlink()
            patch_name = 'docs/PATCH-v0.1.0.json'
            (root / patch_name).write_text(json.dumps({'base_files': {
                INHERITED: {'sha256': hashlib.sha256(LEGACY).hexdigest()}}}) + '\n')
            allowlist = root / 'tools/release-files.json'
            names = [n for n in json.loads(allowlist.read_text()) if n != WHITESPACE_BASELINE] + [patch_name]
            allowlist.write_text(json.dumps(names) + '\n')
            with self.assertRaisesRegex(ValueError, r'is missing.*release\.py --whitespace-baseline v<LAST PUBLISHED'):
                inspect_source(root)

    def test_invalid_baseline_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            self.inherited_fixture(root)
            (root / WHITESPACE_BASELINE).write_text(json.dumps({'release': '0.0.32', 'commit': 'a' * 40,
                                                                'files': {INHERITED: 'not-a-hash'}}) + '\n')
            with self.assertRaisesRegex(ValueError, 'Invalid docs/WHITESPACE-BASELINE.json'):
                inspect_source(root)

    def test_engine_file_exemption_and_full_check_after_edit(self):
        name = 'engine/aga/src/example.c'
        record = {'release': '0.0.32', 'commit': 'b' * 40, 'files': {name: hashlib.sha256(LEGACY).hexdigest()}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'docs').mkdir()
            (root / WHITESPACE_BASELINE).write_text(json.dumps(record) + '\n')
            check_source_whitespace(root, {name: LEGACY})
            with self.assertRaisesRegex(ValueError, 'example.c:1: trailing whitespace'):
                check_source_whitespace(root, {name: LEGACY + b'new\n'})

    def test_repository_baseline_is_keyed_to_a_published_release(self):
        root = Path(__file__).resolve().parents[1]
        record = load_whitespace_baseline(root)
        self.assertIsNotNone(record, 'docs/WHITESPACE-BASELINE.json is required')
        self.assertRegex(record['release'], r'^\d+\.\d+\.\d+$', 'baseline must be a published final release')
        self.assertEqual(list(record['files']), sorted(record['files']))
        for name in record['files']:
            self.assertTrue(name.startswith(INHERITED_PREFIXES), name)
        self.assertIn(WHITESPACE_BASELINE, json.loads((root / 'tools/release-files.json').read_text()))
        # The writer refuses any commit its release tag does not name. Where git and the tag are present
        # (a developer clone), the file must also equal a fresh write; the offline gate image has no git.
        tag = f'v{record["release"]}'
        if shutil.which('git') and (root / '.git').exists() and not subprocess.run(
                ['git', '-C', str(root), 'rev-parse', '--verify', '--quiet', tag + '^{commit}'],
                capture_output=True).returncode:
            self.assertEqual(whitespace_baseline(root, tag), record,
                             f'stale: run python3 tools/release.py --whitespace-baseline {tag}')

    def test_baseline_record_requires_the_published_tag_and_lists_only_inherited_defects(self):
        blobs = {'VERSION': b'0.1.0\n', 'engine/aga/src/old.c': LEGACY, 'engine/aga/src/clean.c': b'int x;\n',
                 'docs/aga/COPYING.NEWLIB': LEGACY, 'docs/notes.md': b'Own text \n', 'tools/own.py': LEGACY,
                 'engine/aga/src/data.bin': b'\0 \n'}
        with self.assertRaisesRegex(ValueError, 'not the published release: tag v0.1.0'):
            whitespace_baseline_record(blobs, 'c' * 40, '')
        with self.assertRaisesRegex(ValueError, 'not the published release'):
            whitespace_baseline_record(blobs, 'c' * 40, 'd' * 40)
        record = whitespace_baseline_record(blobs, 'c' * 40, 'c' * 40)
        digest = hashlib.sha256(LEGACY).hexdigest()
        self.assertEqual(record['release'], '0.1.0')
        self.assertEqual(record['files'], {'docs/aga/COPYING.NEWLIB': digest, 'engine/aga/src/old.c': digest})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'docs').mkdir()
            (root / WHITESPACE_BASELINE).write_text(json.dumps(record) + '\n')
            check_source_whitespace(root, {'engine/aga/src/old.c': LEGACY, 'VERSION': b'0.2.0-dev1\n'})

    def test_baseline_writer_writes_lf_json_and_reports_the_release(self):
        record = {'note': 'n', 'release': '0.1.0', 'commit': 'c' * 40,
                  'files': {'engine/aga/src/old.c': hashlib.sha256(LEGACY).hexdigest()}}
        with tempfile.TemporaryDirectory() as tmp, mock.patch('release.whitespace_baseline', return_value=record):
            root = Path(tmp)
            (root / 'docs').mkdir()
            result = write_whitespace_baseline(root, 'v0.1.0')
            raw = (root / WHITESPACE_BASELINE).read_bytes()
            self.assertNotIn(b'\r', raw)
            self.assertTrue(raw.endswith(b'}\n'))
            self.assertEqual(json.loads(raw), record)
            self.assertEqual(load_whitespace_baseline(root), record)
            self.assertEqual(result['inherited_files'], 1)
