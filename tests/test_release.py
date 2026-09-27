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
    (root / "tools/release-files.json").write_text(json.dumps(["README.md", "pyproject.toml", "tools/release-files.json"]))


class Release(unittest.TestCase):
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
