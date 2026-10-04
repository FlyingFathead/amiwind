import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from release import create_candidate, inspect_source, release, validate_candidate


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

    def test_only_exact_unchanged_legacy_files_are_exempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            fixture(root)
            legacy = b'Historical text \n'
            (root / 'README.md').write_bytes(legacy)
            (root / 'docs').mkdir()
            patch_name = 'docs/PATCH-v0.1.0.json'
            (root / patch_name).write_text(json.dumps({'base_files': {
                'README.md': {'sha256': hashlib.sha256(legacy).hexdigest()}}}) + '\n')
            allowlist = root / 'tools/release-files.json'
            allowlist.write_text(json.dumps(json.loads(allowlist.read_text()) + [patch_name]) + '\n')
            inspect_source(root)
            (root / 'README.md').write_bytes(legacy + b'Changed text\n')
            with self.assertRaisesRegex(ValueError, 'trailing whitespace'):
                inspect_source(root)
