#!/usr/bin/env python3
"""Capture two exterior views using an installed OpenMW on an X11 desktop."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mwad.paths import ensure_external, read_workspace, resolve_data_files

CAMERAS = [(-8550, -73660, 480, 0), (-11200, -71500, 300, 0)]


def capture(args):
    _, state = read_workspace(args.workspace)
    data = resolve_data_files(state["data_files"])
    out = ensure_external(args.out, "OpenMW capture")
    if out.exists():
        raise ValueError("Capture output already exists; choose a new directory")
    openmw, xdotool = shutil.which(args.openmw), shutil.which(args.xdotool)
    if not openmw or not xdotool or not os.environ.get("DISPLAY"):
        raise ValueError("Requires OpenMW, xdotool and an X11 DISPLAY; manual F12 captures also work")
    openmw, xdotool = str(Path(openmw).resolve()), str(Path(xdotool).resolve())
    out.mkdir(parents=True)
    config = out / "config"
    config.mkdir()
    # OpenMW's installed global config supplies weather and lighting fallbacks.
    (config / "openmw.cfg").write_text("# Private opening capture session.\n")
    (config / "settings.cfg").write_text(
        "[Video]\nresolution x = 640\nresolution y = 400\nfullscreen = false\nvsync = false\n"
        "[Camera]\nviewing distance = 7000\nfield of view = 75\n"
        "[Water]\nshader = false\n[Shadows]\nenable shadows = false\n"
        "[Navigator]\nenable = false\n[Terrain]\ndistant terrain = false\n")
    initial = config / "view.txt"
    initial.write_text('set gamehour to 7\nset timescale to 0\n'
                       'ChangeWeather "Bitter Coast Region" 2\nToggleCollision\n'
                       'player->Position ' + ' '.join(map(str, CAMERAS[0])) + '\nToggleMenus\n')
    command = [openmw, "--config", str(config), "--user-data", str(out / "userdata"),
               "--replace", "content", "--content", "builtin.omwscripts", "--content", "Morrowind.esm",
               "--replace", "data", "--data", str(data),
               "--replace", "fallback-archive", "--fallback-archive", "Morrowind.bsa",
               "--skip-menu", "--start", "Seyda Neen", "--no-sound", "--script-run", str(initial)]
    with (out / "capture.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=log)
        try:
            window = subprocess.check_output(
                [xdotool, "search", "--sync", "--onlyvisible", "--pid", str(process.pid)],
                timeout=60, text=True).splitlines()[0]
            subprocess.run([xdotool, "windowfocus", "--sync", window], check=True)
            time.sleep(args.settle_seconds)
            if process.poll() is not None:
                raise ValueError("OpenMW exited; inspect the external capture.log")
            shots = out / "userdata/screenshots"
            for i, camera in enumerate(CAMERAS):
                subprocess.run([xdotool, "windowfocus", "--sync", window], check=True)
                if i:
                    subprocess.run([xdotool, "key", "grave"], check=True)
                    time.sleep(.3)
                    subprocess.run([xdotool, "type", "--clearmodifiers",
                                    "player->Position " + " ".join(map(str, camera))], check=True)
                    subprocess.run([xdotool, "key", "Return"], check=True)
                    time.sleep(.3)
                    subprocess.run([xdotool, "key", "grave"], check=True)
                    time.sleep(5)
                before = set(shots.glob("*.png")) if shots.exists() else set()
                subprocess.run([xdotool, "key", "F12"], check=True)
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    new = set(shots.glob("*.png")) - before if shots.exists() else set()
                    if len(new) == 1:
                        time.sleep(.5)
                        shutil.copyfile(next(iter(new)), out / f"scene-{i}.png")
                        break
                    time.sleep(.2)
                else:
                    raise ValueError("No OpenMW screenshot arrived; check window focus and F12 binding")
                print(f"Captured view {i + 1}", flush=True)
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    (out / "capture.json").write_text(json.dumps({"backend": "OpenMW", "cameras": CAMERAS,
        "scope": "Exterior stills; actor animation baking is not implemented",
        "review": "Inspect both PNGs before building; loading time and NPC positions can vary"}, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--openmw", default="openmw")
    parser.add_argument("--xdotool", default="xdotool")
    parser.add_argument("--settle-seconds", type=float, default=30)
    args = parser.parse_args()
    if not 5 <= args.settle_seconds <= 60:
        parser.error("--settle-seconds must be between 5 and 60")
    try:
        capture(args)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
