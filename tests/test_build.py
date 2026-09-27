"""Guided-build boundary checks with generated, non-game input."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build
from test_workflow import synthetic_install


class GuidedBuildTests(unittest.TestCase):
    def test_aga_variants_keep_interior_and_image_in_same_pipeline(self):
        args = build.parser().parse_args(["--hands", "sprites"])
        args.data_files = Path("/owned/Data Files")
        args.sdk = Path("/sdk")
        args.upstream_archive = Path("/upstream.tar.gz")
        tools = {name: "/tools/" + name for name in
                 ("qbsp", "vis", "light", "qcc", "ffmpeg", "xdftool", "rdbtool")}
        steps = build.commands(args, tools, Path("/private/run"))
        names = [name for name, _ in steps]
        self.assertLess(names.index("hands"), names.index("interior"))
        self.assertLess(names.index("interior"), names.index("image"))
        commands = dict(steps)
        self.assertNotIn('--archive', commands['engine'])
        self.assertIn('/private/run/engine/runtime/build/AmiQuakeGCC', commands['image'])
        for stage in ("engine", "image"):
            command = commands[stage]
            self.assertEqual(command[command.index("--hands") + 1], "sprites")
        image = commands["image"]
        self.assertEqual(image[image.index("--scene") + 1], "/private/run/interior-scene")

    def test_shell_wrapper_from_another_directory_and_space_path(self):
        with tempfile.TemporaryDirectory(prefix="amiwind build ") as tmp:
            base = Path(tmp)
            data = base / "Data Files"
            synthetic_install(data)
            output = base / "private output"
            run = subprocess.run(["sh", str(ROOT / "build.sh"), "--stage", "terrain", "--check", "--allow-data-differences",
                "--data-files", str(data), "--workspace", str(output)], cwd=base, text=True, capture_output=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("Prerequisites passed", run.stdout)
            self.assertFalse(output.exists())

    def test_repository_and_input_output_overlap_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "game"
            synthetic_install(data)
            for output in (ROOT / "private", data / "output", data.parent):
                args = build.parser().parse_args(["--stage", "terrain", "--data-files", str(data), "--workspace", str(output)])
                with self.assertRaises(ValueError):
                    build.prerequisites(args)

    def test_noninteractive_missing_input_reports_action(self):
        args = build.parser().parse_args(["--stage", "terrain"])
        with self.assertRaisesRegex(ValueError, "Supply --data-files"):
            build.prerequisites(args)

    def test_failed_stage_stops_and_preserves_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            steps = [("first", [sys.executable, "-c", "print('first result')"]),
                     ("broken", [sys.executable, "-c", "raise SystemExit(7)"]),
                     ("must-not-run", ["does-not-exist"])]
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(RuntimeError, "broken failed"):
                build.execute(steps, run, {})
            state = json.loads((run / "build-state.json").read_text())
            self.assertEqual(state["status"], "failed")
            self.assertEqual([s["status"] for s in state["steps"]], ["passed", "failed"])
            self.assertEqual((run / "logs/01-first.log").read_text().strip(), "first result")
            with self.assertRaises(FileExistsError):
                build.execute(steps, run, {})

    def test_terrain_builder_runs_real_conversion(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            data = base / "game"
            synthetic_install(data)
            args = build.parser().parse_args(["--stage", "terrain", "--allow-data-differences", "--data-files", str(data), "--workspace", str(base / "out")])
            tools = build.prerequisites(args)
            run = base / "out/run"
            steps = build.commands(args, tools, run)
            # The synthetic fixture contains one fictional cell at (0,0).
            steps[-1][1].extend(["--center", "0", "0", "--radius", "0"])
            with contextlib.redirect_stdout(io.StringIO()):
                build.execute(steps, run, {})
            result = json.loads((run / "work/generated/seyda-neen/conversion.json").read_text())
            self.assertEqual(result["verification"]["status"], "passed")
