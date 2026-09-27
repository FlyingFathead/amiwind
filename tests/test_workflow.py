import contextlib
import io
import json
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mwad.audit import audit
from mwad.cli import main
from mwad.paths import ensure_external, init_workspace, resolve_data_files
from mwad.verify import verify


def sub(tag, value):
    return struct.pack("<4sI", tag.encode(), len(value)) + value


def record(tag, value):
    return struct.pack("<4sIII", tag.encode(), len(value), 0, 0) + value


def synthetic_install(path):
    """Generate fictional fixtures at test time; no game content is embedded."""
    path.mkdir()
    head = struct.pack("<fI32s256sI", 1.3, 1, b"Synthetic fixture", b"Format test", 3)
    land = sub("INTV", struct.pack("<ii", 0, 0)) + sub("DATA", struct.pack("<I", 1))
    land += sub("VHGT", struct.pack("<f4225b3x", 0., *([0]*4225)))
    land += sub("VTEX", bytes(512))
    cell = sub("NAME", b"Test cell\0") + sub("DATA", struct.pack("<Iii", 0, 0, 0))
    cell += sub("FRMR", struct.pack("<I", 1)) + sub("NAME", b"test_object\0")
    cell += sub("DATA", struct.pack("<6f", 128., 256., 0., 0., 0., 0.))
    obj = sub("NAME", b"test_object\0") + sub("MODL", b"test.nif\0")
    esm = record("TES3", sub("HEDR", head)) + record("STAT", obj) + record("CELL", cell) + record("LAND", land)
    (path / "morrowind.esm").write_bytes(esm)
    name = b"meshes\\test.nif\0"
    directory = struct.pack("<III", 9, 0, 0) + name
    bsa = struct.pack("<III", 0x100, len(directory), 1) + directory + bytes(8) + b"synthetic"
    (path / "MORROWIND.BSA").write_bytes(bsa)


class Workflow(unittest.TestCase):
    def test_synthetic_end_to_end_and_overwrite_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, out = Path(tmp)/"Data Files", Path(tmp)/"area"
            synthetic_install(data)
            self.assertEqual(resolve_data_files(Path(tmp)), data)
            with contextlib.redirect_stdout(io.StringIO()):
                audit(data, out, [0, 0], 0, 2)
                result = verify(out)
            self.assertEqual(result["packets_checked"], 16)
            self.assertEqual(result["bytes_checked"], 4096)
            report = json.loads((out / "audit.json").read_text())
            self.assertEqual(report["area"]["direct_model_bytes"], 9)
            self.assertEqual(report["area"]["references"], 1)
            with self.assertRaises(ValueError):
                audit(data, out, [0, 0], 0, 2)

    def test_repository_paths_are_rejected(self):
        with self.assertRaises(ValueError):
            ensure_external(ROOT / "generated" / "area")

    def test_other_project_checkout_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text('[project]\nname = "morrowind-amiga-demake"\n')
            with self.assertRaises(ValueError):
                ensure_external(root / "data")

    def test_symlink_into_repository_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            link = Path(tmp)/"link"
            try:
                link.symlink_to(ROOT, target_is_directory=True)
            except OSError:
                self.skipTest("Creating symlinks is unavailable")
            with self.assertRaises(ValueError):
                ensure_external(link / "generated")

    def test_workspace_creates_only_empty_data_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"workspace"
            init_workspace(p)
            self.assertTrue((p / "original").is_dir())
            self.assertEqual(list((p / "original").iterdir()), [])
            with self.assertRaises(ValueError):
                init_workspace(p)

    def test_doctor_cli_works_without_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"data"
            synthetic_install(p)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                main(["doctor", "--data-files", str(p)])
            report = json.loads(output.getvalue())
            self.assertFalse(report["voices"]["present"])
            self.assertTrue(report["terrain_inputs_present"])

    def test_setup_remembers_external_install_and_convert_uses_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, workspace = Path(tmp)/"game", Path(tmp)/"workspace"
            synthetic_install(data)
            with contextlib.redirect_stdout(io.StringIO()):
                main(["setup", "--data-files", str(data), "--workspace", str(workspace)])
                main(["convert", "--workspace", str(workspace), "--name", "fixture", "--center", "0", "0", "--radius", "0"])
            state = json.loads((workspace / "workspace.json").read_text())
            self.assertEqual(state["data_files"], str(data))
            result = json.loads((workspace / "generated/fixture/conversion.json").read_text())
            self.assertEqual(result["verification"]["status"], "passed")
            self.assertEqual(list((workspace / "original").iterdir()), [])
