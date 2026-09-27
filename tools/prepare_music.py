#!/usr/bin/env python3
"""Convert an owner's complete installed Music directory to Paula stream blocks."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mwad.paths import child_ci, ensure_external

RATE = 11015
BLOCK_FRAMES = 8192
HEADER = struct.Struct(">4sHHII")


def playlists(tracks):
    """Canonical PCM identities; retain source files but never queue aliases twice."""
    identities = {}
    groups = {"explore": [], "battle": [], "special": []}
    title = None
    for i, track in enumerate(tracks):
        canonical = identities.setdefault(track["sha256"], i)
        path = track["source"].replace("\\", "/").casefold().split("/")
        group = path[-2] if len(path) > 1 else "special"
        group = group if group in groups else "special"
        if canonical not in groups[group]:
            groups[group].append(canonical)
        if path[-1] == "morrowind title.mp3" and group == "special":
            title = canonical
    # Menu music remains menu-only even when an installation has copied the
    # same recording into Explore. Retain the files, exclude their PCM identity.
    if title is not None:
        for group in ("explore", "battle"):
            groups[group] = [i for i in groups[group] if i != title]
    if not groups["explore"]:
        raise ValueError("An exploration playlist with non-title music is required")
    if title is None:
        title = groups["explore"][0]
    # A source folder without battle music can still play the exploration demo.
    if not groups["battle"]:
        groups["battle"] = groups["explore"].copy()
    return {"title": title, **groups, "selection": "shuffled world groups; canonical title excluded; controls depend on runtime"}


def music_include(manifest, paths, stream_mode="async4k", benchmark_seconds=0):
    groups = playlists(manifest["tracks"])
    kinds = {"sync": 0, "async": 1, "async4k": 2, "async8k": 3}
    lines = [f"MUSIC_TRACKS equ {len(manifest['tracks'])}",
             f"MUSIC_TITLE equ {groups['title']}",
             f"STREAM_ASYNC equ {kinds[stream_mode]}",
             f"BENCHMARK_TICKS equ {benchmark_seconds * 50}",
             f"READ_SLICE equ {4096 if stream_mode == 'async4k' else 8192 if stream_mode == 'async8k' else 16384}",
             "        section music_table,data", "music_playlists:",
             "        dc.l music_explore,music_battle"]
    for group in ("explore", "battle"):
        ids = groups[group]
        lines += [f"music_{group}:", "        dc.w " + ",".join(map(str, [len(ids), *ids]))]
    lines += ["music_paths:", "        dc.l " + ",".join(f"music_path_{i}" for i in range(len(manifest["tracks"])))]
    for i, track in enumerate(manifest["tracks"]):
        lines += [f"music_path_{i}:", f'        dc.b "{paths[track["file"]]}",0', "        even"]
    return "\n".join(lines) + "\n"


def pack_stream(interleaved):
    """MWA1 header, then fixed right/left signed-eight-bit planar blocks."""
    if len(interleaved) % 2 or not interleaved:
        raise ValueError("Expected nonempty stereo s8 PCM")
    frames = len(interleaved) // 2
    blocks = (frames + BLOCK_FRAMES - 1) // BLOCK_FRAMES
    out = bytearray(HEADER.pack(b"MWA1", RATE, BLOCK_FRAMES, frames, blocks))
    for start in range(0, frames, BLOCK_FRAMES):
        chunk = interleaved[start * 2:(start + BLOCK_FRAMES) * 2]
        out.extend(chunk[1::2].ljust(BLOCK_FRAMES, b"\0"))
        out.extend(chunk[0::2].ljust(BLOCK_FRAMES, b"\0"))
    return bytes(out)


def unpack_stream(data):
    """Independent stream validation and PCM reconstruction for release checks."""
    if len(data) < HEADER.size:
        raise ValueError("Truncated music header")
    magic, rate, block, frames, count = HEADER.unpack_from(data)
    if magic != b"MWA1" or rate != RATE or block != BLOCK_FRAMES or not frames:
        raise ValueError("Unsupported music stream")
    if count != (frames + block - 1) // block or len(data) != HEADER.size + count * block * 2:
        raise ValueError("Music length mismatch")
    out = bytearray(count * block * 2)
    for i in range(count):
        p = HEADER.size + i * block * 2
        out[i * block * 2:(i + 1) * block * 2:2] = data[p + block:p + block * 2]
        out[i * block * 2 + 1:(i + 1) * block * 2:2] = data[p:p + block]
    if any(out[frames * 2:]):
        raise ValueError("Nonzero music padding")
    return bytes(out[:frames * 2])


def prepare_music(data_files, output, ffmpeg):
    output = ensure_external(output, "soundtrack conversion")
    output.mkdir(parents=True, exist_ok=False)
    music = child_ci(data_files, "Music")
    sources = sorted(music.rglob("*"), key=lambda p: p.relative_to(music).as_posix().casefold())
    sources = [p for p in sources if p.is_file() and p.suffix.lower() == ".mp3"]
    if not sources or len(sources) > 99:
        raise ValueError("Expected 1–99 installed music files")
    # Title first, then exploration, battle and remaining special cues. Keep every file.
    sources.sort(key=lambda p: (0 if p.relative_to(music).as_posix().casefold() == "special/morrowind title.mp3"
                              else 1 if p.parts[-2].casefold() == "explore"
                              else 2 if p.parts[-2].casefold() == "battle" else 3))
    records = []
    for i, source in enumerate(sources):
        pcm = subprocess.check_output([ffmpeg, "-v", "error", "-nostdin", "-i", str(source),
                                       "-vn", "-ac", "2", "-ar", str(RATE),
                                       "-af", "aresample=osf=u8:dither_method=triangular",
                                       "-f", "s8", "pipe:1"])
        packed = pack_stream(pcm)
        if unpack_stream(packed) != pcm:
            raise ValueError("Music round-trip mismatch")
        name = f"track{i:02d}.mws"
        (output / name).write_bytes(packed)
        frames = len(pcm) // 2
        records.append({"file": name, "source": source.relative_to(data_files).as_posix(),
                        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                        "pcm_frames": frames, "seconds": frames / RATE,
                        "blocks": (frames + BLOCK_FRAMES - 1) // BLOCK_FRAMES,
                        "bytes": len(packed), "sha256": hashlib.sha256(packed).hexdigest()})
    manifest = {"format": "MWA1", "rate": RATE, "channels": 2, "bits": 8,
                "block_frames": BLOCK_FRAMES, "tracks": records,
                "seconds": sum(r["seconds"] for r in records),
                "bytes": sum(r["bytes"] for r in records)}
    manifest["playlists"] = playlists(records)
    (output / "soundtrack.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-files", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    print(json.dumps(prepare_music(args.data_files, args.out, args.ffmpeg), indent=2))
