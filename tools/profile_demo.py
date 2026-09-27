#!/usr/bin/env python3
"""Run a fixed native benchmark on an isolated HDF copy, decode and compare it."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mwad.paths import ensure_external

FIELDS = ("solid_frames", "solid_ticks", "wire_frames", "wire_ticks", "reads",
          "max_read_ticks", "total_read_ticks", "starvations", "errors", "track_opens",
          "max_solid_ticks", "max_wire_ticks")


def decode(data):
    if len(data) != 832:
        raise ValueError("Wrong MWP1 size")
    magic, version, hz, mode, ticks = struct.unpack_from(">4sHHII", data)
    if magic != b"MWP1" or version != 1 or hz not in (50, 60) or mode not in (0, 1, 2, 3):
        raise ValueError("Unsupported profile")
    result = dict(zip(FIELDS, struct.unpack_from(">12I", data, 16)))
    result.update(hz=hz, mode=("sync", "async", "async4k", "async8k")[mode], benchmark_ticks=ticks)
    for index, kind in enumerate(("read", "solid", "wire")):
        hist = list(struct.unpack_from(">64I", data, 64 + index * 256))
        count = sum(hist)
        expected = result["reads" if kind == "read" else kind + "_frames"]
        if count != expected:
            raise ValueError(f"{kind} histogram/count mismatch")
        def percentile(q):
            target = math.ceil(count * q)
            if not target:
                return None
            total = 0
            for tick, n in enumerate(hist):
                total += n
                if total >= target:
                    return tick * 1000 / hz
        result[kind + "_histogram"] = hist
        result[kind + "_p50_ms"] = percentile(.50)
        result[kind + "_p95_ms"] = percentile(.95)
        result[kind + "_p99_ms"] = percentile(.99)
    for mode_name in ("solid", "wire"):
        t = result[mode_name + "_ticks"]
        result[mode_name + "_fps"] = result[mode_name + "_frames"] * hz / t if t else None
    result["stream_bytes"] = result["reads"] * 16384
    result["histogram_overflow_note"] = "Bin 63 includes all intervals >=63 ticks. Percentiles in that bin are lower bounds."
    return result


def run(args):
    build = ensure_external(args.build, "benchmark build")
    out = ensure_external(args.out, "profile output")
    out.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((build / "build.json").read_text())
    duration = manifest.get("benchmark_seconds", 0)
    if duration <= 0:
        raise ValueError("Build with --benchmark-seconds first; interactive builds do not auto-exit")
    hdf = next(r for r in manifest["images"] if r["name"].endswith(".hdf"))
    source = build / hdf["name"]
    if hashlib.sha256(source.read_bytes()).hexdigest() != hdf["sha256"]:
        raise ValueError("Benchmark source HDF hash mismatch")
    image = out / "working.hdf"
    shutil.copyfile(source, image)
    rom = ensure_external(args.rom, "ROM")
    env = os.environ.copy()
    env.update(DISPLAY=f"127.0.0.1:{args.display}", SDL_VIDEODRIVER="x11",
               LIBGL_ALWAYS_SOFTWARE="1", LP_NUM_THREADS="2", ALSOFT_DRIVERS="wave",
               ALSOFT_CONF=str(out / "alsoft.conf"))
    if args.lib_dir:
        env["LD_LIBRARY_PATH"] = str(args.lib_dir.resolve())
    (out / "alsoft.conf").write_text("[general]\ndrivers=wave\n[wave]\nfile=" + str(out / "audio.wav") + "\n")
    (out / "reports").mkdir()
    config = out / "run.fs-uae"
    config.write_text(f"""[fs-uae]
amiga_model = A500
chip_memory = 512
slow_memory = 512
fast_memory = 0
kickstart_file = {rom}
hard_drive_0 = {image}
hard_drive_0_type = hdf
hard_drive_1 = {out}/reports
hard_drive_1_label = PROFILE
base_dir = {out}/state
logs_dir = {out}/logs
window_width = 640
window_height = 512
fullscreen = 0
video_sync = off
""")
    x = emulator = None
    with (out / "session.log").open("w") as log:
        try:
            command = [str(args.xvfb), f":{args.display}", "-screen", "0", "800x600x24", "-ac",
                       "-nolisten", "unix", "-nolisten", "local", "-listen", "tcp"]
            if args.xkb_dir:
                command += ["-xkbdir", str(args.xkb_dir)]
            x = subprocess.Popen(command, env=env, stdout=log, stderr=log)
            for _ in range(100):
                try:
                    with socket.create_connection(("127.0.0.1", 6000 + args.display), timeout=.2):
                        break
                except OSError:
                    if x.poll() is not None:
                        raise RuntimeError("Xvfb exited; see session.log")
                    time.sleep(.1)
            else:
                raise RuntimeError("Xvfb did not become ready")
            command = [str(args.emulator), str(config)]
            if args.emulator_data:
                command += ["--data-dir=" + str(args.emulator_data)]
            emulator = subprocess.Popen(command, env=env, stdout=log, stderr=log)
            for second in range(duration + args.boot_allowance):
                time.sleep(1)
                if emulator.poll() is not None:
                    raise RuntimeError("Emulator exited prematurely")
                if second % 10 == 9:
                    print(f"Benchmark elapsed: {second + 1}s", flush=True)
            from PIL import ImageGrab
            ImageGrab.grab(xdisplay=env["DISPLAY"]).save(out / "exit.png")
        finally:
            if emulator:
                emulator.terminate()
                try:
                    emulator.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    emulator.kill(); emulator.wait()
            if x:
                x.terminate(); x.wait(timeout=5)
    raw = out / "MWPROFILE.BIN"
    shutil.copyfile(out / "reports/MWPROFILE.BIN", raw)
    result = decode(raw.read_bytes())
    result["provenance"] = {"build": manifest, "rom_sha256": hashlib.sha256(rom.read_bytes()).hexdigest(),
                            "emulator_path": str(args.emulator),
                            "emulator_version": args.emulator_version,
                            "emulator_sha256": hashlib.sha256(args.emulator.read_bytes()).hexdigest(),
                            "executable_sha256": hashlib.sha256((build / "MorrowindDemo").read_bytes()).hexdigest(),
                            "route": "stationary dense-fog start; no injected movement"}
    config_path = out / "logs/debug.uae"
    if not config_path.exists():
        raise ValueError("Effective emulator configuration missing")
    config_text = config_path.read_text()
    required = ["cpu_model=68000", "cpu_speed=real", "cpu_cycle_exact=true", "chipset=ocs",
                "chipmem_size=1", "bogomem_size=2", "fastmem_size=0", "ntsc=false",
                "cpu_memory_cycle_exact=true", "blitter_cycle_exact=true", "immediate_blits=false"]
    if any(setting not in config_text.splitlines() for setting in required):
        raise ValueError("Effective emulator settings differ from the baseline")
    result["provenance"]["effective_baseline"] = required
    (out / "profile.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def compare(paths):
    results = [json.loads(p.read_text()) for p in paths]
    first = results[0]
    for r in results[1:]:
        for key in ("hz", "benchmark_ticks"):
            if r[key] != first[key]:
                raise ValueError("Unmatched benchmark duration/clock")
        for key in ("rom_sha256", "emulator_sha256", "route"):
            if r["provenance"][key] != first["provenance"][key]:
                raise ValueError("Unmatched benchmark provenance")
        for key in ("walking", "soundtrack"):
            if r["provenance"]["build"][key] != first["provenance"]["build"][key]:
                raise ValueError("Unmatched terrain or soundtrack")
    return [{"path": str(p), **{k: r[k] for k in ("mode", "solid_fps", "solid_p95_ms", "solid_p99_ms",
              "max_solid_ticks", "read_p95_ms", "starvations", "errors")}} for p, r in zip(paths, results)]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run")
    for name in ("build", "out", "rom", "emulator", "xvfb", "xdftool"):
        r.add_argument("--" + name, type=Path, required=True)
    for name in ("emulator-data", "lib-dir", "xkb-dir"):
        r.add_argument("--" + name, type=Path)
    r.add_argument("--display", type=int, default=98)
    r.add_argument("--emulator-version", required=True, help="Exact tested emulator version/build")
    r.add_argument("--boot-allowance", type=int, default=35)
    c = sub.add_parser("compare");c.add_argument("profiles", type=Path, nargs="+")
    d = sub.add_parser("decode");d.add_argument("profile", type=Path)
    args = p.parse_args()
    try:
        result = run(args) if args.command == "run" else compare(args.profiles) if args.command == "compare" else decode(args.profile.read_bytes())
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        p.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
