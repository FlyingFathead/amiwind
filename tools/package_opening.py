#!/usr/bin/env python3
"""Package a checked source release with explicitly private opening assets/ROM."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mwad.paths import ensure_external
from release import validate_candidate
from build_opening import DEMO_VERSION, hunk_memory


def package(args):
    root = Path(__file__).resolve().parents[1]
    source = ensure_external(args.source_archive, "source archive")
    validate_candidate(root, source)
    build = ensure_external(args.build, "opening build")
    rom_path = ensure_external(args.kickstart, "private ROM")
    destination = ensure_external(args.out, "private package")
    if destination.exists():
        raise ValueError("Versioned packages are immutable; choose a new version/name")
    rom = rom_path.read_bytes()
    if len(rom) != 262144 or struct.unpack_from(">HH", rom, 12) != (34, 5):
        raise ValueError("This opening package expects a 256 KiB Kickstart 1.3 revision 34.5")
    rom_sum = 0
    for word in struct.unpack(">65536I", rom):
        rom_sum += word
        rom_sum = (rom_sum & 0xffffffff) + (rom_sum >> 32)
    if rom_sum != 0xffffffff:
        raise ValueError("Kickstart checksum failed")
    manifest = json.loads((build / "build.json").read_text())
    if manifest["demo_version"] != DEMO_VERSION:
        raise ValueError("Build and packer demo versions differ")
    hunk_memory(build / "MorrowindDemo")
    for record in manifest["images"]:
        p = build / record["name"]
        if p.parent != build or hashlib.sha256(p.read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError("Image differs from its build manifest")
    payload = {}
    with zipfile.ZipFile(source) as z:
        for name in z.namelist():
            payload[name] = z.read(name)
    prefix = f"morrowind-amiga-workspace/demo-v{DEMO_VERSION}/"
    names = ["MorrowindDemo", "build.json", "assembler.log", "opening-assets.i", "walking-assets.i", "music-assets.i", "startup-sequence"]
    names += [r["name"] for r in manifest["images"]]
    for name in names:
        payload[prefix + name] = (build / name).read_bytes()
    for p in sorted((build / "converted").iterdir()):
        if p.is_symlink() or not p.is_file() or p.suffix not in (".png", ".s8", ".planes"):
            raise ValueError("Unexpected converted asset")
        payload[prefix + "converted/" + p.name] = p.read_bytes()
    payload[prefix + "soundtrack.json"] = (build / "music/soundtrack.json").read_bytes()
    rom_name = "kickstart-1.3-a500.rom"
    payload[prefix + "roms/" + rom_name] = rom
    rom_info = {"name": rom_name, "version": "Kickstart 1.3 revision 34.5", "bytes": len(rom),
                "sha256": hashlib.sha256(rom).hexdigest()}
    payload[prefix + "ROM.json"] = (json.dumps(rom_info, indent=2) + "\n").encode()
    for kind in ("hdf",):
        disk = (f"floppy_drive_0 = MorrowindDemo-v{DEMO_VERSION}.adf\nfloppy_drive_speed = 100\n"
                if kind == "adf" else f"hard_drive_0 = MorrowindDemo-v{DEMO_VERSION}.hdf\nhard_drive_0_type = hdf\n")
        config = ("[fs-uae]\namiga_model = A500\nchip_memory = 512\nslow_memory = 512\n"
                  "fast_memory = 0\n" + f"kickstart_file = roms/{rom_name}\n" + disk +
                  "fullscreen = 0\nwindow_width = 640\nwindow_height = 512\nvideo_sync = off\n")
        payload[prefix + f"demo-{kind}.fs-uae"] = config.encode()
    if args.evidence:
        evidence = ensure_external(args.evidence, "test evidence")
        for p in sorted(evidence.iterdir()):
            if p.is_symlink() or not p.is_file() or p.suffix not in (".png", ".json", ".txt", ".fs-uae", ".uae"):
                raise ValueError("Evidence directory must contain only selected screenshots/configs/reports")
            payload[prefix + "validation/" + p.name] = p.read_bytes()
    if args.scenery:
        from mwad.scene import read_asset, unpack_geometry
        scenery = ensure_external(args.scenery, "private scenery study")
        index = json.loads((scenery / "scenery-index.json").read_text())
        with (scenery / "scenery.mwpak").open("rb") as f:
            for record in index["models"]:
                unpack_geometry(read_asset(f, record))
            for record in index["textures"]:
                read_asset(f, record)
        for name in ("scenery.mwpak", "scenery-index.json", "scenery-report.json", "static-turntables.png"):
            p = ensure_external(scenery / name, "private scenery payload")
            if p.is_symlink() or not p.is_file():
                raise ValueError("Unexpected scenery payload")
            payload[f"morrowind-amiga-workspace/scenery-v{DEMO_VERSION}/" + name] = p.read_bytes()
    payload["README-PRIVATE.md"] = (f"""# AmiWind v{DEMO_VERSION} — private checkpoint

A Morrowind conversion pipeline and demake for Commodore Amiga.

## File to run

Mount **MorrowindDemo-v{DEMO_VERSION}.hdf** as a bootable hardfile in WinUAE.
It is inside `morrowind-amiga-workspace/demo-v{DEMO_VERSION}/`.
The complete soundtrack is inside the HDF. This checkpoint requires HDD storage.
The file named `MorrowindDemo` is the AmigaDOS executable. If copying it to a real
hard disk, preserve the `MWBOOT:`, `MWMUSIC1:` and `MWMUSIC2:` volume names
or assign those names to folders containing each partition's files.
FS-UAE users can open `demo-hdf.fs-uae` in that same folder.

Use A500, PAL, OCS, stock 68000, 512 KiB Chip + 512 KiB slow expansion, no Fast RAM.
HDF layout: RDB with three 32 MiB OFS partitions, UAE controller, 512-byte blocks.
Use RDB/full-drive autodetection; do not mount this as the earlier plain partition image. Detailed WinUAE setup: source docs/WINUAE.md.
The included ROM is `roms/{rom_name}`. Select it manually if needed.

## Controls

Click to capture the mouse, then Enter to walk. WASD moves, mouse looks,
left Shift runs, Tab switches filled/wireframe, 1/2/3 select fog distance,
and Escape returns to AmigaDOS and prints frame/audio counters. Dense fog is default.
Wait at least 10 seconds at the DOS prompt before closing the emulator, so the
profile file and filesystem buffers reach disk. `MWBOOT:MWPROFILE.BIN` records
the last run.
F6/F7 audition next/previous songs in the active group. F8 auditions battle or
exploration music. Automatic exploration uses a shuffled bag without immediate
duplicates; the current song continues while walking. Death/triumph are reserved
for future gameplay events. There is no combat detection yet.
In the opening, left mouse changes the still image and right mouse exits.

Boot prints `Loading AmiWind v{DEMO_VERSION}...`; the opening also shows its version.
The optional `scenery-v{DEMO_VERSION}/` sibling is a host conversion study with
original trees/buildings and a turntable preview. The native executable does
not yet render that scenery or implement collision. It is private game-derived data.

## Private content and source

This package contains the owner's converted Morrowind terrain, artwork/audio
and, at the owner's explicit request, the tested Kickstart ROM. Keep it private.
Only `amiwind/` is the source tree. Host tools and the A500 runtime are GPLv3;
the separate AGA engine retains its GPLv2 notices. The content policy explains
which material can be shared. All derived assets and ROMs remain
in the separate sibling workspace. Full original game files remain in the earlier
private workspace; rebuilds require that installation and the host build tools.

Public docs record ROM metadata, emulator settings and validation results.
Working ROM SHA-256: `{rom_info['sha256']}`.
""").encode()
    receipt = {n: {"bytes": len(d), "sha256": hashlib.sha256(d).hexdigest()} for n, d in payload.items()}
    payload["PRIVATE-MANIFEST.json"] = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="opening-candidate-", dir=destination.parent) as tmp:
        candidate = Path(tmp) / destination.name
        with zipfile.ZipFile(candidate, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for name, data in sorted(payload.items()):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = (0o100755 if name.endswith(("/AmiWind-FS-UAE-launcher.py", "/run_fs_uae.py", "/build.sh")) else 0o100644) << 16
                z.writestr(info, data)
        with zipfile.ZipFile(candidate) as z:
            if z.testzip() or set(z.namelist()) != set(payload):
                raise ValueError("Private package validation failed")
            for name, data in payload.items():
                if z.read(name) != data:
                    raise ValueError(f"Private package mismatch: {name}")
        with destination.open("xb") as f:
            f.write(candidate.read_bytes())
    return {"package": str(destination), "bytes": destination.stat().st_size,
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(), "rom": rom_info}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("source-archive", "build", "kickstart", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--evidence", type=Path)
    p.add_argument("--scenery", type=Path)
    args = p.parse_args()
    try:
        print(json.dumps(package(args), indent=2))
    except (OSError, ValueError, KeyError) as exc:
        p.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
