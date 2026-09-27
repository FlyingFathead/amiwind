#!/usr/bin/env python3
"""Guided local build; private outputs stay in ignored out/ or a chosen workspace."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mwad.paths import child_ci, ensure_external, inside, resolve_data_files, installed_game_path, is_wsl
from mwad import input_check
import build_versions
from build_aga import UPSTREAM_SHA256, RUNTIME_BUILD_DIR, VERSION, runtime_sources


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-files", type=Path, help=r"Morrowind installation root or Data Files; e.g. C:\GOG Games\Morrowind (Windows/WSL). Guided mode offers a detected GOG install")
    p.add_argument("--workspace", type=Path, default=ROOT / "out",
                   help="Build output parent (default: ignored out/ in this checkout)")
    p.add_argument("--stage", choices=("terrain", "aga"), default="aga",
                   help="terrain: host packets only; aga: full experimental HDF")
    p.add_argument("--check", action="store_true", help="Read-only prerequisite check; no conversion")
    p.add_argument("--plan", action="store_true", help="Check prerequisites and print commands without running")
    p.add_argument("--install-dependencies", action="store_true", help="Preview and confirm Ubuntu/Debian host packages and an external Python environment")
    p.add_argument("--install-sdk", action="store_true", help="With --install-dependencies, also fetch the pinned Linux x86_64 Amiga SDK after confirmation")
    p.add_argument("--tools-dir", type=Path, default=ROOT.parent / "amiwind-tools", help="External dependency environment parent (default: ../amiwind-tools)")
    p.add_argument("--versions", action="store_true", help="Compare available tools/packages with the recorded build reference, then exit")
    p.add_argument("--check-inputs", action="store_true", help="Check the game installation without requiring build tools, then exit")
    p.add_argument("--dry-run", action="store_true", help="Actually compile the engine and create an asset-free boot-notice HDF; --plan only previews commands")
    p.add_argument("--allow-data-differences", action="store_true", help="Explicitly allow unverified edition/file checksum differences; container and required-group errors still block")
    p.add_argument("--name", help="New immutable run name; defaults to a UTC timestamp")
    p.add_argument("--sdk", type=Path, help="AmigaPorts GCC SDK root")
    p.add_argument("--vasm", type=Path, help="Separate vasmm68k_mot executable (default: SDK bin directory)")
    p.add_argument("--upstream-archive", type=Path, help="Optional legacy provenance check; the runtime source is included")
    p.add_argument("--quake-tools", type=Path, help="ericw-tools directory containing qbsp, vis, light")
    p.add_argument("--qcc", help="Path to id Quake-Tools qcc-host")
    p.add_argument("--ffmpeg", default="ffmpeg")
    p.add_argument("--xdftool", default="xdftool")
    p.add_argument("--rdbtool", default="rdbtool")
    p.add_argument("--hands", choices=("3d","sprites"), default="3d", help="First-person runtime build: sprites currently Nord unarmed only")
    return p


def ask(value, prompt, interactive):
    if value is not None:
        return value
    if interactive:
        return input(prompt + ": ").strip() or None
    return None


def gog_installation():
    if not (sys.platform == "win32" or is_wsl()):
        return None
    try:
        root = installed_game_path(r"C:\GOG Games\Morrowind")
        data = resolve_data_files(root)
        if input_check.matches_core(data):
            return root
    except (OSError, ValueError):
        pass
    return None


def game_input(value, interactive):
    if value is not None:
        return value
    if not interactive:
        return None
    print("Host: " + ("WSL" if is_wsl() else sys.platform))
    if sys.platform == "win32" or is_wsl():
        print(r"Checking C:\GOG Games\Morrowind for the reference core file sizes and SHA-256 hashes...", flush=True)
    candidate = gog_installation()
    if candidate:
        print(f"Found a matching GOG installation: {candidate}")
        print("Morrowind.esm and Morrowind.bsa match reference sizes and SHA-256 hashes; full input checks follow.")
        if input("Use this installation? [Y/n] ").strip().casefold() in ("", "y", "yes"):
            return candidate
    else:
        print("No matching default GOG installation detected. Select your installed game folder; another edition/location may still be usable.")
    return input("Morrowind installation root (or Data Files directory): ").strip() or None


def executable(value, label, errors):
    found = shutil.which(str(value)) if value else None
    if not found:
        errors.append(f"{label}: executable not found ({value or 'not supplied'})")
        return None
    return str(Path(found).resolve())


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def prerequisites(args, interactive=False):
    errors, tools = [], {}
    args.workspace = ensure_external(args.workspace, "build workspace")
    raw = game_input(args.data_files, interactive)
    data = None
    if raw:
        try:
            print("Checking the installed file tree, containers and reference SHA-256 hashes...", flush=True)
            args.input_report = input_check.inspect(raw, args.stage, args.allow_data_differences)
            input_check.display(args.input_report)
            errors.extend(args.input_report["errors"])
            data = Path(args.input_report["data_files"])
            if inside(args.workspace, data) or inside(data, args.workspace):
                errors.append("Use an output workspace separate from the game installation, not its parent or child")
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
    else:
        errors.append("Supply --data-files '/path/to/Morrowind/Data Files'")
    if args.stage == "aga":
        for module, package in (("PIL", "Pillow"), ("numpy", "numpy"),
                                ("scipy", "scipy"), ("pyffi", "PyFFI==2.2.3"),
                                ("fast_simplification", "fast-simplification==0.2.0")):
            if importlib.util.find_spec(module) is None:
                errors.append(f"Python dependency missing: {package}; use this Python environment's pip")
        for name in ("make",):
            tools[name] = executable(name, name, errors)
        for name in ("ffmpeg", "xdftool", "rdbtool"):
            tools[name] = executable(getattr(args, name), name, errors)
        sdk = ask(args.sdk, "AmigaPorts SDK root", interactive)
        if sdk:
            args.sdk = ensure_external(sdk, "SDK")
            tools["m68k-amigaos-gcc"] = executable(args.sdk / "bin/m68k-amigaos-gcc", "m68k-amigaos-gcc", errors)
            tools["vasmm68k_mot"] = executable(args.vasm or args.sdk / "bin/vasmm68k_mot", "vasmm68k_mot", errors)
            if not (args.sdk / "m68k-amigaos/ndk-include/exec/exec_lib.i").is_file():
                errors.append("SDK NDK includes missing: m68k-amigaos/ndk-include/exec/exec_lib.i")
        else:
            errors.append("Supply --sdk /path/to/m68k-amigaos-gcc-16.2")
        try:
            runtime_sources()
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
        archive = args.upstream_archive
        if archive:
            args.upstream_archive = ensure_external(archive, "upstream source archive")
            if not args.upstream_archive.is_file() or sha256(args.upstream_archive) != UPSTREAM_SHA256:
                errors.append(f"AmiQuake archive must match SHA-256 {UPSTREAM_SHA256}")
        tool_dir = ask(args.quake_tools, "ericw-tools bin directory (blank to use PATH)", interactive)
        for name in ("qbsp", "vis", "light"):
            value = Path(tool_dir).expanduser() / name if tool_dir else name
            tools[name] = executable(value, name, errors)
        tools["qcc"] = executable(ask(args.qcc, "qcc-host executable", interactive) or "qcc-host", "qcc-host", errors)
        if not Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf").is_file():
            errors.append("Install fonts-dejavu-core (the scene builder uses DejaVuSansMono.ttf)")
    args.version_report = build_versions.report(args, tools) if args.stage == "aga" else []
    if errors:
        raise ValueError("Prerequisites need attention:\n  - " + "\n  - ".join(errors) + "\nSee docs/LINUX_BUILD.md.")
    args.data_files = data
    return tools


def dry_run_prerequisites(args, interactive=False):
    errors, tools = [], {}
    args.workspace = ensure_external(args.workspace, "build workspace")
    if args.data_files:
        raise ValueError("The asset-free --dry-run does not accept --data-files")
    sdk = ask(args.sdk, "AmigaPorts SDK root", interactive)
    if not sdk:
        raise ValueError("Supply --sdk for the asset-free native compile")
    args.sdk = ensure_external(sdk, "SDK")
    for name, value in (("make", "make"), ("m68k-amigaos-gcc", args.sdk / "bin/m68k-amigaos-gcc"),
                        ("vasmm68k_mot", args.vasm or args.sdk / "bin/vasmm68k_mot")):
        tools[name] = executable(value, name, errors)
    if importlib.util.find_spec("amitools") is None:
        errors.append("Python dependency missing: amitools==0.8.1")
    if not (args.sdk / "m68k-amigaos/ndk-include/exec/exec_lib.i").is_file():
        errors.append("SDK NDK includes are missing")
    runtime_sources()
    args.version_report = build_versions.report(args, tools)
    if errors:
        raise ValueError("Dry-run prerequisites need attention:\n  - " + "\n  - ".join(errors))
    return tools


def dry_run_commands(args, run):
    common = ["--sdk", str(args.sdk)] + (["--vasm", str(args.vasm)] if args.vasm else [])
    binary = run / "engine" / RUNTIME_BUILD_DIR / "build/AmiQuakeGCC"
    return [
        ("engine", [sys.executable, str(ROOT / "tools/build_aga.py"), "engine", *common,
                    "--out", str(run / "engine"), "--hands", args.hands]),
        ("dry-run-image", [sys.executable, str(ROOT / "tools/build_dry_run.py"), *common,
                           "--engine", str(binary), "--out", str(run / "image")]),
    ]


def commands(args, tools, run):
    py = sys.executable
    def tool(name, *items):
        return [py, str(ROOT / "tools" / name), *map(str, items)]
    work = run / "work"
    steps = [
        ("setup", tool("mwad.py", "setup", "--data-files", args.data_files, "--workspace", work, "--target", "a1200" if args.stage == "aga" else "a500")),
        ("terrain", tool("mwad.py", "convert", "--workspace", work)),
    ]
    if args.stage == "aga":
        binary = run / "engine" / RUNTIME_BUILD_DIR / "build/AmiQuakeGCC"
        steps += [
            ("scenery", tool("prepare_scenery.py", "--workspace", work, "--out", run / "scenery")),
            ("scene", tool("prepare_quake.py", "--workspace", work, "--scene", run / "scenery", "--out", run / "alias-scene")),
            ("bsp", tool("prepare_mesh_bsp.py", "--scene", run / "alias-scene", "--scenery", run / "scenery", "--out", run / "bsp-scene",
                *[part for name in ("qbsp", "vis", "light") for part in ("--" + name, tools[name])])),
            ("npcs", tool("prepare_npcs.py", "--data-files", args.data_files, "--scene", run / "bsp-scene", "--out", run / "npc-scene", "--ffmpeg", tools["ffmpeg"])),
            ("hands", tool("prepare_hands.py", "--data-files", args.data_files, "--scene", run / "npc-scene", "--out", run / "hands-scene")),
            ("interior", tool("prepare_interior.py", "--data-files", args.data_files, "--scene", run / "hands-scene", "--out", run / "interior-scene",
                *[part for name in ("qbsp", "vis", "light") for part in ("--" + name, tools[name])])),
            ("dialogue-lookup", tool("prepare_dialogue_lookup.py", "--data-files", args.data_files, "--out", run / "voice-lookup.json")),
            ("music", tool("prepare_music.py", "--data-files", args.data_files, "--ffmpeg", tools["ffmpeg"], "--out", run / "music")),
            ("engine", tool("build_aga.py", "engine", "--sdk", args.sdk, "--out", run / "engine", "--hands", args.hands,
                            *(["--vasm", args.vasm] if args.vasm else []))),
            ("image", tool("build_aga.py", "image", "--hands", args.hands, "--scene", run / "interior-scene", "--music", run / "music", "--engine", binary, "--out", run / "image",
                *[part for name in ("qcc", "qbsp", "vis", "light", "xdftool", "rdbtool") for part in ("--" + name, tools[name])])),
        ]
    return steps


def execute(steps, run, metadata):
    run.mkdir(parents=True, exist_ok=False)
    (run / "logs").mkdir()
    receipt = {**metadata, "status": "running", "steps": []}
    def save():
        temporary = run / "build-state.tmp"
        temporary.write_text(json.dumps(receipt, indent=2) + "\n")
        temporary.replace(run / "build-state.json")
    save()
    for number, (name, command) in enumerate(steps, 1):
        log = run / "logs" / f"{number:02}-{name}.log"
        print(f"[{number}/{len(steps)}] {name} — log: {log}", flush=True)
        entry = {"name": name, "command": command, "status": "running", "log": str(log)}
        receipt["steps"].append(entry)
        save()
        start = time.monotonic()
        try:
            with log.open("w") as output:
                subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT, check=True)
        except (OSError, subprocess.CalledProcessError, KeyboardInterrupt) as exc:
            entry.update(status="failed", elapsed_seconds=round(time.monotonic() - start, 3))
            receipt["status"] = "failed"
            save()
            raise RuntimeError(f"{name} failed. Earlier results are retained. Read {log}; use a new --name after fixing the problem.") from exc
        entry.update(status="passed", elapsed_seconds=round(time.monotonic() - start, 3))
        save()
    receipt["status"] = "passed"
    save()


def provenance(args, tools):
    """Capture inputs and build choices once, before any conversion stage runs."""
    def hashes(base, accept):
        return {str(path.relative_to(base)): sha256(path)
                for path in sorted(base.rglob("*")) if path.is_file() and accept(path)}
    return {
        "schema": "amiwind-build-receipt-v1", "runtime_version": VERSION,
        "recipe": "asset-free-test-compile-v1" if args.dry_run else "seyda-neen-prison-v1" if args.stage == "aga" else "seyda-neen-terrain-v1",
        "stage": args.stage, "hands": args.hands if args.stage == "aga" else None,
        "python": sys.version, "data_files": str(args.data_files), "tools": tools,
        "version_comparison": getattr(args, "version_report", []),
        "input_check": getattr(args, "input_report", None),
        "tool_sha256": {name: sha256(path) for name, path in tools.items()},
        "input_sha256": {} if args.dry_run else hashes(args.data_files, lambda path: True),
        "source_sha256": hashes(ROOT, lambda path:
            (path.suffix in (".py", ".c", ".h", ".patch", ".qc", ".asm", ".sh") or path.name == "Makefile")
            and path.relative_to(ROOT).parts[0] != "out"
            and "__pycache__" not in path.parts),
    }


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    try:
        if sys.version_info < (3, 10):
            raise ValueError("Python 3.10 or newer is required")
        if args.install_sdk and not args.install_dependencies:
            raise ValueError("--install-sdk requires --install-dependencies")
        if sum((args.install_dependencies, args.versions, args.check_inputs)) > 1:
            raise ValueError("Use one of --install-dependencies, --versions or --check-inputs at a time")
        if args.install_dependencies:
            from install_dependencies import install
            return install(args)
        if args.versions:
            build_versions.report(args)
            return 0
        if args.check_inputs:
            raw = game_input(args.data_files, sys.stdin.isatty())
            if raw is None:
                raise ValueError("Supply --data-files with your Morrowind installation root")
            print("Checking the installed file tree, containers and reference SHA-256 hashes...", flush=True)
            report = input_check.inspect(raw, args.stage, args.allow_data_differences)
            input_check.display(report)
            return 1 if report["errors"] else 0
        args.name = args.name or datetime.now(timezone.utc).strftime("build-%Y%m%d-%H%M%S")
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}", args.name):
            raise ValueError("--name must be 1–64 letters, digits, dots, hyphens or underscores")
        tools = (dry_run_prerequisites if args.dry_run else prerequisites)(args, interactive=sys.stdin.isatty())
        run = ensure_external(args.workspace / "build" / args.name, "build run")
        print(f"Prerequisites passed. Scope: {'asset-free test compile' if args.dry_run else args.stage}; data: {args.data_files}")
        if args.check:
            print("Checks completed. No build outputs created. Individual assets are validated during conversion; target performance is not tested here.")
            return 0
        if run.exists():
            raise ValueError(f"Build already exists: {run}; choose a new --name")
        steps = dry_run_commands(args, run) if args.dry_run else commands(args, tools, run)
        if args.plan:
            for name, command in steps:
                print(name + ": " + shlex.join(command))
            return 0
        print("Recording input, tool and source checksums before conversion.", flush=True)
        execute(steps, run, provenance(args, tools))
        if args.dry_run:
            result = run / "image" / f"AmiWind-v{VERSION}-dry-run.hdf"
            print(f"Asset-free test build complete: {result}\nNo game assets or ROMs were used. This is not a playable demo.")
        else:
            result = run / "image" / f"AmiWind-v{VERSION}.hdf" if args.stage == "aga" else run / "work/generated/seyda-neen"
            print(f"Build complete: {result}\nPrivate generated content: do not include it in the public source package.")
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        p.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
