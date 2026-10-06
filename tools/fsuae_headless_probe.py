#!/usr/bin/env python3
"""Bounded FS-UAE smoke probe for an isolated Docker container."""
from __future__ import annotations

import json
import math
import argparse
import fcntl
import os
import pty
import re
import select
import signal
import struct
import subprocess
import sys
import time
import wave
import zlib
from pathlib import Path

OUT = Path("/work/runs")
ROM = Path("/input/kickstart-3.1-a1200.rom")
HOME = Path("/tmp/amiwind-home")
RUNTIME = Path("/tmp/amiwind-runtime")
CONFIG = OUT / "kickstart-probe.fs-uae"
TIMEOUT = 20
children: list[subprocess.Popen] = []
logs = []
master_fd: int | None = None
worker_lock = None
transcript = bytearray()


def run(args: list[str], timeout: int = TIMEOUT, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=True, timeout=timeout, env=ENV, **kwargs)


def launch(args: list[str], log_name: str) -> subprocess.Popen:
    log = (OUT / log_name).open("wb")
    logs.append(log)
    proc = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, env=ENV,
                            start_new_session=True)
    children.append(proc)
    return proc


def wait_for(predicate, description: str, seconds: int = TIMEOUT):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(0.1)
    raise TimeoutError(f"Timed out waiting for {description}")


def drain_until(predicate, description: str, seconds: int = TIMEOUT, start: int = 0) -> str:
    assert master_fd is not None
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate(transcript[start:].decode("utf-8", "replace")):
            return transcript.decode("utf-8", "replace")
        readable, _, _ = select.select([master_fd], [], [], min(0.2, max(0, deadline-time.monotonic())))
        if readable:
            try:
                block = os.read(master_fd, 65536)
            except OSError:
                block = b""
            if block:
                transcript.extend(block)
    raise TimeoutError(f"Timed out waiting for {description}")


def prompt_present(data: str) -> bool:
    # Memory-map rows contain <none>; only a standalone prompt is ready.
    return re.search(r"(?:^|\r?\n)>[ \t]*$", data) is not None


def debugger_command(command: str) -> str:
    """Send only at a known prompt; return after the next prompt arrives."""
    assert master_fd is not None
    before = len(transcript)
    os.write(master_fd, (command + "\n").encode("ascii"))
    deadline = time.monotonic() + TIMEOUT
    while time.monotonic() < deadline:
        current = transcript[before:].decode("utf-8", "replace")
        if prompt_present(current):
            return current
        readable, _, _ = select.select([master_fd], [], [], min(0.2, max(0, deadline-time.monotonic())))
        if readable:
            try:
                block = os.read(master_fd, 65536)
            except OSError:
                block = b""
            if block:
                transcript.extend(block)
    raise TimeoutError(f"No debugger prompt after command {command!r}")


def png_has_content(path: Path) -> bool:
    """Require several RGB colours in an 8-bit FS-UAE PNG, not a blank frame."""
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return False
    offset, compressed = 8, bytearray()
    width = height = channels = 0
    while offset + 12 <= len(data):
        length = int.from_bytes(data[offset:offset+4], "big")
        kind = data[offset+4:offset+8]
        chunk = data[offset+8:offset+8+length]
        if len(chunk) != length:
            return False
        if kind == b"IHDR":
            width, height, depth, colour, comp, filt, interlace = struct.unpack(">IIBBBBB", chunk)
            if depth != 8 or colour not in (2, 6) or comp or filt or interlace:
                return False
            channels = 3 if colour == 2 else 4
        elif kind == b"IDAT":
            compressed.extend(chunk)
        elif kind == b"IEND":
            break
        offset += length + 12
    if not width or not height or not channels or width*height > 4096*4096:
        return False
    raw = zlib.decompress(compressed)
    stride = width*channels
    if len(raw) != height*(stride+1):
        return False
    prior = bytearray(stride)
    colours = set()
    for row in range(height):
        start = row*(stride+1)
        filter_type = raw[start]
        current = bytearray(raw[start+1:start+1+stride])
        if filter_type > 4:
            return False
        for i in range(stride):
            left = current[i-channels] if i >= channels else 0
            above = prior[i]
            diagonal = prior[i-channels] if i >= channels else 0
            if filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = above
            elif filter_type == 3:
                predictor = (left+above)//2
            elif filter_type == 4:
                p = left+above-diagonal
                a, b, c = abs(p-left), abs(p-above), abs(p-diagonal)
                predictor = left if a <= b and a <= c else above if b <= c else diagonal
            else:
                predictor = 0
            current[i] = (current[i]+predictor) & 255
        for i in range(0, stride, channels):
            colours.add(bytes(current[i:i+3]))
            if len(colours) >= 3:
                return True
        prior = current
    return False


def wait_pngs(previous: set[Path], minimum: int = 2) -> list[Path]:
    assert master_fd is not None
    deadline = time.monotonic() + 40
    next_capture = time.monotonic() + 2.0
    attempts = 1
    while time.monotonic() < deadline:
        if time.monotonic() >= next_capture and attempts < 20:
            run(["xdotool", "key", "Print"])
            attempts += 1
            next_capture = time.monotonic() + 2.0
        readable, _, _ = select.select([master_fd], [], [], 0.05)
        if readable:
            try:
                chunk = os.read(master_fd, 65536)
            except OSError:
                chunk = b""
            if chunk:
                transcript.extend(chunk)
        fresh = [p for p in OUT.glob("*.png") if p not in previous and p.is_file() and p.stat().st_size > 32]
        valid = []
        for path in fresh:
            try:
                with path.open("rb") as capture:
                    if capture.read(8) == b"\x89PNG\r\n\x1a\n":
                        valid.append(path)
            except OSError:
                pass
        crops = sorted((p for p in valid if "-crop-" in p.name), reverse=True)
        if len(valid) >= minimum and crops:
            try:
                if png_has_content(crops[0]):
                    return valid
            except (OSError, ValueError, struct.error, zlib.error):
                pass
    raise TimeoutError("Timed out waiting for fresh screenshots with visible guest content")


def wait_for_window(emulator: subprocess.Popen) -> str:
    """Find the emulator window while continuously draining its PTY."""
    assert master_fd is not None
    deadline = time.monotonic() + TIMEOUT
    while time.monotonic() < deadline:
        if emulator.poll() is not None:
            raise RuntimeError(f"FS-UAE exited during window startup ({emulator.returncode})")
        readable, _, _ = select.select([master_fd], [], [], 0.1)
        if readable:
            try:
                chunk = os.read(master_fd, 65536)
            except OSError:
                chunk = b""
            if chunk:
                transcript.extend(chunk)
        found = subprocess.run(["xdotool", "search", "--onlyvisible", "--class", "fs-uae"],
                               capture_output=True, text=True, env=ENV, timeout=2)
        if found.returncode == 0 and found.stdout.strip():
            return found.stdout.strip().splitlines()[-1]
    raise TimeoutError("Timed out waiting for a visible FS-UAE window")


def synthetic_audio_check() -> dict:
    tone = OUT / "synthetic-tone.wav"
    with wave.open(str(tone), "wb") as wav:
        wav.setnchannels(2); wav.setsampwidth(2); wav.setframerate(48000)
        frames = (struct.pack("<hh", int(5000*math.sin(2*math.pi*440*n/48000)),
                              int(5000*math.sin(2*math.pi*440*n/48000))) for n in range(48000))
        wav.writeframes(b"".join(frames))
    recording = (OUT / "virtual-audio.raw").open("wb")
    logs.append(recording)
    recorder = subprocess.Popen(["parec", "--device=amiwind.monitor", "--format=s16le",
                                 "--rate=48000", "--channels=2", "--latency-msec=20"],
                                stdout=recording, stderr=subprocess.PIPE, env=ENV,
                                start_new_session=True)
    children.append(recorder)
    try:
        wait_for(lambda: recorder.poll() is None and "amiwind.monitor" in
                 run(["pactl", "list", "short", "sources"], capture_output=True, text=True).stdout,
                 "audio recorder and monitor source", 5)
        time.sleep(0.3)
        run(["paplay", "--device=amiwind", "--latency-msec=100", str(tone)], timeout=10)
        time.sleep(1.0)
    finally:
        if recorder.poll() is None:
            os.killpg(recorder.pid, signal.SIGTERM)
            recorder.wait(timeout=5)
        recording.flush(); recording.close()
    raw = (OUT / "virtual-audio.raw").read_bytes()
    if len(raw) < 4096 or len(raw) % 2:
        raise RuntimeError("Synthetic audio recording is missing or too short")
    peak = max(abs(value[0]) for value in struct.iter_unpack("<h", raw))
    if peak == 0:
        raise RuntimeError("Synthetic tone was not observed on the PulseAudio monitor")
    return {"bytes": len(raw), "peak": peak, "synthetic_only": True}


ENV = os.environ.copy()
ENV.update(HOME=str(HOME), XDG_RUNTIME_DIR=str(RUNTIME), DISPLAY=":99",
           LIBGL_ALWAYS_SOFTWARE="1", SDL_VIDEODRIVER="x11",
           ALSOFT_DRIVERS="pulse", PULSE_SERVER=f"unix:{RUNTIME / 'pulse.sock'}",
           PYTHONDONTWRITEBYTECODE="1")


def cleanup() -> None:
    for proc in reversed(children):
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=5)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait(timeout=3)
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    pass
    for stream in logs:
        if not stream.closed:
            stream.close()
    if master_fd is not None:
        try:
            os.close(master_fd)
        except OSError:
            pass


def main() -> int:
    global master_fd, OUT, CONFIG, worker_lock
    report = {"status": "failed", "guest": "Kickstart only; no game disk mounted"}
    fresh_output = False
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--output", required=True, help="new run directory directly under /work/runs")
        args = parser.parse_args()
        runs_root = Path("/work/runs").resolve()
        selected_output = Path(args.output).resolve()
        if selected_output.parent != runs_root:
            raise RuntimeError("--output must name a direct child directory under /work/runs")
        if any(char.isspace() for char in selected_output.name):
            raise RuntimeError("--output directory name must not contain whitespace")
        if not ROM.is_file() or ROM.stat().st_size < 262144:
            raise RuntimeError("Required A1200 Kickstart file is missing or smaller than 256 KiB")
        # The display and virtual audio endpoints belong to one probe at a time.
        worker_lock = Path("/tmp/amiwind-fsuae-probe.lock").open("a")
        fcntl.flock(worker_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        selected_output.mkdir(parents=False, exist_ok=False)
        OUT = selected_output
        CONFIG = OUT / "kickstart-probe.fs-uae"
        fresh_output = True
        HOME.mkdir(mode=0o700, parents=True, exist_ok=True)
        RUNTIME.mkdir(mode=0o700, parents=True, exist_ok=True)

        launch(["Xvfb", ":99", "-screen", "0", "1024x768x24", "+extension", "GLX",
                "+render", "-noreset", "-nolisten", "tcp"], "xvfb.log")
        wait_for(lambda: Path("/tmp/.X11-unix/X99").exists(), "Xvfb socket")
        report["graphics"] = run(["glxinfo", "-B"], capture_output=True, text=True).stdout
        if "llvmpipe" not in report["graphics"].lower():
            raise RuntimeError("Mesa llvmpipe software renderer was not detected")

        launch(["pulseaudio", "--daemonize=no", "--exit-idle-time=-1", "--use-pid-file=no",
                "--log-target=stderr", "-n", "-L", f"module-native-protocol-unix socket={RUNTIME/'pulse.sock'}",
                "-L", "module-null-sink sink_name=amiwind rate=48000 channels=2"], "pulseaudio.log")
        wait_for(lambda: (RUNTIME / "pulse.sock").exists(), "PulseAudio socket")
        report["synthetic_audio"] = synthetic_audio_check()

        CONFIG.write_text(f"""[config]
amiga_model = A1200
cpu = 68040-NOMMU
fpu = 68040
chip_memory = 2048
zorro_iii_memory = 16384
jit_compiler = 0
kickstart_file = /input/kickstart-3.1-a1200.rom
console_debugger = 1
modifier_key = key_lalt
initial_input_grab = 0
automatic_input_grab = 0
fullscreen = 0
window_width = 800
window_height = 600
screenshots_output_dir = {OUT}
screenshots_output_mask = 3
base_dir = /tmp/amiwind-home/fs-uae
floppy_drive_volume = 0
joystick_port_1 = none
""", encoding="ascii")
        master_fd, slave_fd = pty.openpty()
        emulator = subprocess.Popen(["fs-uae", "--stdout", str(CONFIG)], stdin=slave_fd,
                                    stdout=slave_fd, stderr=slave_fd, env=ENV, start_new_session=True)
        children.append(emulator)
        os.close(slave_fd)
        wait_for(lambda: emulator.poll() is None, "FS-UAE launch", 3)
        window = wait_for_window(emulator)
        # Window visibility precedes the emulation thread and event loop.
        drain_until(lambda text: "wait_for_frame_no_netplay:" in text,
                    "FS-UAE frame scheduling")
        run(["xdotool", "windowfocus", "--sync", window])
        before = set(OUT.glob("*.png"))
        run(["xdotool", "key", "Print"])
        captures = wait_pngs(before)

        before_text = len(transcript)
        run(["xdotool", "keydown", "Alt_L"]); time.sleep(0.2)
        run(["xdotool", "key", "--delay", "150", "d"]); time.sleep(0.2)
        run(["xdotool", "keyup", "Alt_L"])
        drain_until(prompt_present, "fresh FS-UAE debugger prompt", start=before_text)
        responses = {}
        for command in ("r", "dm", "d"):
            response = debugger_command(command)
            if command == "r" and not re.search(r"\bD0\s+[0-9A-Fa-f]{8}", response):
                raise RuntimeError("Debugger register response is missing")
            if command == "dm" and not re.search(r"(?im)^\s*[0-9A-Fa-f]{8}\s+.+memory", response):
                raise RuntimeError("Debugger memory-map response is missing")
            if command == "d" and not re.search(r"(?im)^\s*[0-9A-Fa-f]{8}\s+[0-9A-Fa-f]{4}", response):
                raise RuntimeError("Debugger disassembly response is missing")
            responses[command] = response
        if len(captures) < 2:
            raise RuntimeError("Both full and cropped screenshots were not captured")
        (OUT / "fs-uae-pty.log").write_bytes(transcript)
        report.update(status="passed", visible_guest_content=True, captures=[p.name for p in captures], debugger=responses,
                      debugger_entry=transcript[before_text:].decode("utf-8", "replace"))
        (OUT / "runtime-probe.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2), flush=True)
        return 0
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        if transcript:
            (OUT / "fs-uae-pty.log").write_bytes(transcript)
        if fresh_output:
            (OUT / "runtime-probe.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2), file=sys.stderr, flush=True)
        return 1
    finally:
        cleanup()
        if worker_lock is not None:
            worker_lock.close()


if __name__ == "__main__":
    sys.exit(main())
