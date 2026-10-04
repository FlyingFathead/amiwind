"""Guided-build boundary checks with generated, non-game input."""
import contextlib
import io
import json
import os
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
    def test_startup_controls_do_not_launch_before_profile_selection(self):
        from build_aga import startup_config
        text = startup_config('bind ESCAPE quit\nr_drawviewmodel 0\nr_maxsurfs 1\nmap seyda\n')
        self.assertNotIn('map seyda', text)
        self.assertNotIn('map prison', text)
        self.assertIn('exec keymaps-default.cfg', text)
        self.assertNotIn('bind ', text)
        self.assertIn('bind "ESCAPE" togglemenu', (ROOT/'config/keymaps.cfg').read_text())
        self.assertIn('r_drawviewmodel 1', text)
        self.assertEqual(text.count('r_maxsurfs '), 1)
        self.assertEqual(text.count('r_maxedges '), 1)
        with self.assertRaisesRegex(ValueError, 'exactly one startup map'):
            startup_config('map seyda\nmap prison\n')

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
        self.assertLess(names.index("interior"), names.index("intro"))
        self.assertLess(names.index("intro"), names.index("image"))
        self.assertLess(names.index("world-terrain"), names.index("world-scenery"))
        self.assertLess(names.index("world-scenery-assets"), names.index("world-scenery"))
        self.assertLess(names.index("world-scenery"), names.index("image"))
        commands = dict(steps)
        self.assertNotIn('--archive', commands['engine'])
        self.assertIn(str(Path('/private/run/engine/runtime/build/AmiQuakeGCC')), commands['image'])
        for stage in ("engine", "image"):
            command = commands[stage]
            self.assertEqual(command[command.index("--hands") + 1], "sprites")
        image = commands["image"]
        self.assertEqual(Path(image[image.index("--sdk") + 1]), Path("/sdk"))
        self.assertEqual(Path(image[image.index("--scene") + 1]), Path("/private/run/intro-scene"))
        self.assertEqual(Path(image[image.index("--world-scenery") + 1]), Path("/private/run/world-scenery"))
        source = commands["world-scenery-assets"]
        self.assertIn("--export-meshes", source)
        overlay = commands["world-scenery"]
        self.assertEqual(Path(overlay[overlay.index("--terrain") + 1]), Path("/private/run/world-terrain"))
        self.assertEqual(Path(overlay[overlay.index("--scenery") + 1]), Path("/private/run/world-scenery-source/scenery"))

    def test_map_budget_policy_reaches_image_stage_only(self):
        tools = {name: '/tools/' + name for name in
                 ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
        for extra, expected in (([], 'strict'), (['--map-budget-policy', 'warning'], 'warning')):
            with self.subTest(expected=expected):
                args = build.parser().parse_args(extra)
                args.data_files = Path('/owned/Data Files')
                args.sdk = Path('/sdk')
                steps = dict(build.commands(args, tools, Path('/private/run')))
                image = steps['image']
                self.assertEqual(image.count('--map-budget-policy'), 1)
                self.assertEqual(image[image.index('--map-budget-policy') + 1], expected)
                for name, command in steps.items():
                    if name != 'image':
                        self.assertNotIn('--map-budget-policy', command)

    @unittest.skipUnless(os.name == 'posix', 'POSIX shell launcher; Windows launcher is covered by test_build_windows')
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

    def test_cancelled_stage_preserves_logs_and_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)/'run'
            with patch.object(build.subprocess, 'run', side_effect=KeyboardInterrupt) as command, \
                 contextlib.redirect_stdout(io.StringIO()), self.assertRaises(KeyboardInterrupt):
                build.execute([('interrupted', ['fixture']), ('must-not-run', ['fixture'])], run, {})
            self.assertEqual(command.call_count, 1)
            state = json.loads((run/'build-state.json').read_text())
            self.assertEqual(state['status'], 'cancelled')
            self.assertEqual(state['steps'][0]['status'], 'cancelled')
            self.assertTrue((run/'logs/01-interrupted.log').exists())
