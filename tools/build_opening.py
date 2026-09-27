#!/usr/bin/env python3
"""Build a private 68000 opening and terrain walk from the owner's assets."""
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mwad.paths import child_ci, ensure_external, read_workspace, resolve_data_files

DEMO_VERSION = "0.0.7"
SAMPLE_RATE = 11015
MAX_CHIP_BYTES = 352 * 1024


def planar_bytes(indices):
    """320x200 indices -> four 8000-byte planes, most significant pixel first."""
    if len(indices) != 64000 or max(indices) > 15:
        raise ValueError("Expected 320x200 four-bit pixels")
    out = bytearray(32000)
    for p in range(4):
        for i in range(8000):
            value = 0
            for bit in range(8):
                value |= ((indices[i * 8 + bit] >> p) & 1) << (7 - bit)
            out[p * 8000 + i] = value
    return bytes(out)


def prepare_scene(source, output, index):
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    source = ensure_external(source, "scene capture")
    with Image.open(source) as image:
        rgb = ImageOps.fit(image.convert("RGB"), (320, 200), method=Image.Resampling.LANCZOS)
    indexed = rgb.quantize(colors=14, method=Image.Quantize.MEDIANCUT)
    pal = indexed.getpalette()[:42]
    pal += [0] * (42 - len(pal))
    # Quantize palette channels to the OCS DAC's four bits per component.
    pal = [min(15, (c + 8) // 17) * 17 for c in pal] + [0, 0, 0, 221, 204, 153]
    indexed.putpalette(pal + [0] * (768 - len(pal)))
    draw = ImageDraw.Draw(indexed)
    font = ImageFont.load_default()
    draw.rectangle((4, 4, 140, 30), fill=14)
    draw.text((8, 6), "SEYDA NEEN", font=font, fill=15)
    draw.text((8, 18), f"ARRIVAL / VIEW {index + 1}", font=font, fill=15)
    draw.rectangle((0, 176, 319, 199), fill=14)
    draw.text((6, 178), "Enter: walk   LMB: view   RMB: exit", font=font, fill=15)
    draw.text((6, 189), f"AmiWind v{DEMO_VERSION}", font=font, fill=15)
    pixels = indexed.tobytes()
    (output / f"scene-{index}.planes").write_bytes(planar_bytes(pixels))
    indexed.save(output / f"scene-{index}-ocs.png")
    words = [(pal[i] // 17 << 8) | (pal[i + 1] // 17 << 4) | pal[i + 2] // 17
             for i in range(0, 48, 3)]
    return words


def game_path(root, relative):
    path = Path(relative.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("Music/voice paths must be relative to Data Files")
    for part in path.parts:
        root = child_ci(root, part)
    if not root.is_file():
        raise ValueError("Expected an audio file")
    return root


def pcm(ffmpeg, path, seconds, channels, start=0):
    command = [ffmpeg, "-v", "error", "-nostdin", "-ss", str(start), "-i", str(path),
               "-t", str(seconds), "-vn", "-ac", str(channels), "-ar", str(SAMPLE_RATE),
               "-af", "afade=t=in:d=0.04", "-f", "s8", "pipe:1"]
    data = bytearray(subprocess.check_output(command))
    # Fade the actual end, including files shorter than the requested excerpt.
    frames = len(data) // channels
    fade = min(frames, SAMPLE_RATE // 8)
    for f in range(fade):
        for c in range(channels):
            i = (frames - fade + f) * channels + c
            signed = data[i] if data[i] < 128 else data[i] - 256
            data[i] = round(signed * (fade - 1 - f) / max(1, fade - 1)) & 255
    return bytes(data)


def hunk_memory(path):
    data = path.read_bytes()
    if len(data) < 20 or struct.unpack_from(">II", data) != (1011, 0):
        raise ValueError("Not an Amiga LoadSeg executable")
    count, first, last = struct.unpack_from(">III", data, 8)
    if first != 0 or last + 1 != count or not 1 <= count <= 32 or len(data) < 20 + count * 4:
        raise ValueError("Unexpected executable segment table")
    sizes = struct.unpack_from(">" + "I" * count, data, 20)
    chip = sum((v & 0x3fffffff) * 4 for v in sizes if v & 0x40000000)
    total = sum((v & 0x3fffffff) * 4 for v in sizes)
    if chip > MAX_CHIP_BYTES or total > 1800 * 1024:
        raise ValueError(f"Executable exceeds opening memory budget: {chip=} {total=}")
    return {"chip_hunks_bytes": chip, "all_hunks_bytes": total, "segments": count,
            "excludes": "OS, loader overhead, stack and disk buffers"}


def build(args):
    workspace, state = read_workspace(args.workspace)
    data_files = resolve_data_files(state["data_files"])
    out = ensure_external(args.out, "opening build")
    if out.exists():
        raise ValueError("Build output already exists; choose a new directory")
    if not 1 <= len(args.scene) <= 3:
        raise ValueError("Supply one to three scene captures")
    for capture in args.scene:
        if not ensure_external(capture, "scene capture").is_file():
            raise ValueError(f"Missing scene capture: {capture}")
    assembler = shutil.which(args.vasm)
    ffmpeg = shutil.which(args.ffmpeg)
    xdftool = shutil.which(args.xdftool)
    rdbtool = shutil.which(args.rdbtool)
    if not all((assembler, ffmpeg, xdftool, rdbtool)):
        raise ValueError("Install vasm (m68k/mot), FFmpeg and amitools; or pass executable paths")
    assembler, ffmpeg, xdftool = (str(Path(p).resolve()) for p in (assembler, ffmpeg, xdftool))
    voice_source = game_path(data_files, args.voice)
    out.mkdir(parents=True)
    assets = out / "converted"
    assets.mkdir()
    palettes = [prepare_scene(p, assets, i) for i, p in enumerate(args.scene)]
    from prepare_walk import prepare_walk
    walking = prepare_walk(args.terrain_area or workspace / "generated/seyda-neen", out, data_files)
    from prepare_town import include as include_town
    town = include_town(args.town, out)
    from prepare_music import prepare_music, music_include
    soundtrack = prepare_music(data_files, out / "music", ffmpeg)
    from disk_image import music_layout, music_paths, write_hdf
    layout = music_layout(soundtrack["tracks"])
    paths = music_paths(layout)
    (out / "music-assets.i").write_text(music_include(soundtrack, paths, args.stream_mode, args.benchmark_seconds))
    voice_data = pcm(ffmpeg, voice_source, 6, 1)
    voice_data += bytes(len(voice_data) % 2)
    if len(voice_data) < 2 or len(voice_data) > 131070:
        raise ValueError("Audio does not fit Paula's sample-length register")
    (assets / "voice.s8").write_bytes(voice_data)
    lines = [f"SCENE_COUNT equ {len(palettes)}",
             f"VOICE_WORDS equ {len(voice_data) // 2}",
             f"VOICE_MILLISECONDS equ {round(len(voice_data) / SAMPLE_RATE * 1000)}",
             "        section tables,data", "loading_text:",
             f'        dc.b "Loading AmiWind v{DEMO_VERSION}...",10',
             "loading_text_end:", "        even", "scene_table:",
             "        dc.l " + ",".join(f"scene_{i}" for i in range(len(palettes))), "palettes:"]
    for palette in palettes:
        lines.append("        dc.w " + ",".join(f"${v:03x}" for v in palette))
    lines.append("        section assets,data_c")
    for label, name in [(f"scene_{i}", f"scene-{i}.planes") for i in range(len(palettes))] + [
            ("voice", "voice.s8")]:
        lines.extend([f"{label}:", f'        incbin "converted/{name}"', "        even"])
    (out / "opening-assets.i").write_text("\n".join(lines) + "\n", encoding="ascii")
    source = Path(__file__).resolve().parents[1] / "runtime/src/opening.asm"
    command = [assembler, "-m68000", "-Fhunkexe", "-kick1hunks", "-nosym", "-I", str(source.parent), "-o", "MorrowindDemo", str(source)]
    completed = subprocess.run(command, cwd=out, check=True, text=True, capture_output=True)
    (out / "assembler.log").write_text(completed.stdout + completed.stderr)
    memory = hunk_memory(out / "MorrowindDemo")
    startup = out / "startup-sequence"
    startup.write_text("C:MorrowindDemo\n", encoding="ascii")
    image, storage = write_hdf(out, DEMO_VERSION, layout, xdftool, rdbtool)
    images = [image]
    result = {"demo_version": DEMO_VERSION, "cpu": "68000", "display": "OCS 320x200; four-plane stills, four-plane terrain/scenery",
              "target": "A500, 512 KiB Chip + 512 KiB slow + 2 MiB Fast RAM", "memory": memory,
              "scenes": len(palettes), "soundtrack": soundtrack, "music_buffer_bytes": 49152,
              "voice_seconds": len(voice_data) / SAMPLE_RATE, "pcm_rate": SAMPLE_RATE,
              "walking": walking, "town": town, "fast_memory_kib": 2048, "stream_mode": args.stream_mode, "benchmark_seconds": args.benchmark_seconds,
              "voice_input": args.voice,
              "images": images, "storage": storage, "status": "assembled; filesystem contents verified",
              "runtime_validation": "See the separately recorded emulator/hardware test results",
              "scope": "Opening, terrain, eight-view scenery, building footprint collision, full streamed soundtrack and preloaded voice; no interiors or actors"}
    (out / "build.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--scene", type=Path, action="append", required=True)
    parser.add_argument("--terrain-area", type=Path)
    parser.add_argument("--town", type=Path, required=True)
    parser.add_argument("--stream-mode", choices=("sync", "async", "async4k", "async8k"), default="async4k")
    parser.add_argument("--benchmark-seconds", type=int, choices=range(0, 601), default=0)
    parser.add_argument("--voice", default="Sound/Vo/Misc/CharGen Cap1.mp3")
    parser.add_argument("--vasm", default="vasmm68k_mot")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--xdftool", default="xdftool")
    parser.add_argument("--rdbtool", default="rdbtool")
    args = parser.parse_args()
    try:
        print(json.dumps(build(args), indent=2))
    except (ValueError, OSError, subprocess.CalledProcessError, KeyError) as exc:
        if isinstance(exc, subprocess.CalledProcessError):
            print(exc.stdout or "", file=sys.stderr)
            print(exc.stderr or "", file=sys.stderr)
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
