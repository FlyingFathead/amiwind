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
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mwad.paths import child_ci, ensure_external, inside, resolve_data_files, installed_game_path, is_wsl, is_game_input
from mwad import input_check
from mwad.progress import Progress, live_log, section
import build_versions
from build_jobs import add_jobs, resolve_jobs
from build_font_options import add_font_options, resolve_font_options
from build_aga import UPSTREAM_SHA256, RUNTIME_BUILD_DIR, VERSION, runtime_sources, check_quakec


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-files", type=Path, help=r"Morrowind installation root or Data Files; e.g. C:\GOG Games\Morrowind (Windows/WSL). Guided mode offers a detected GOG install")
    p.add_argument("--workspace", type=Path, default=ROOT / "out",
                   help="Build output parent (default: ignored out/ in this checkout)")
    p.add_argument("--stage", choices=("terrain", "aga"), default="aga",
                   help="terrain: host packets only; aga: full experimental HDF")
    p.add_argument("--check", action="store_true", help="Check prerequisites without conversion; optional interactive SDK setup requires confirmation")
    p.add_argument("--plan", action="store_true", help="Check prerequisites and print commands without running")
    p.add_argument("--install-dependencies", action="store_true", help="Preview and confirm Ubuntu/Debian host packages and an external Python environment")
    p.add_argument("--autoinstall", action="store_true", help="Quickest setup: confirm missing host/Python/native dependencies, install them, then continue the build")
    p.add_argument("--yes", action="store_true", help="With --autoinstall, accept the displayed dependency proposal and APT installation (for CI)")
    p.add_argument("--install-sdk", action="store_true", help="Fetch the pinned Linux x86_64 Amiga SDK after confirmation; works alone or with --install-dependencies")
    p.add_argument("--tools-dir", type=Path, default=ROOT.parent / "amiwind-tools", help="External dependency environment parent (default: ../amiwind-tools)")
    p.add_argument("--versions", action="store_true", help="Compare available tools/packages with the recorded build reference, then exit")
    p.add_argument("--check-inputs", action="store_true", help="Check the game installation without requiring build tools, then exit")
    p.add_argument("--dry-run", action="store_true", help="Actually compile the engine and create an asset-free boot-notice HDF; --plan only previews commands")
    p.add_argument("--autorun-fs-uae", action="store_true", help="Check FS-UAE and your ROM before setup, then launch the completed HDF using the documented preset")
    p.add_argument("--kickstart-file", "--kickstart", dest="kickstart_file", type=Path,
                   help="Owned ROM file or directory for --autorun-fs-uae (default: ~/.roms/; asks if missing interactively)")
    p.add_argument("--allow-data-differences", action="store_true", help="Explicitly allow unverified edition/file checksum differences; container and required-group errors still block")
    p.add_argument("--name", help="New immutable run name; defaults to a UTC timestamp")
    p.add_argument("--sdk", type=Path, help="AmigaPorts GCC SDK root")
    p.add_argument("--vasm", type=Path, help="Separate vasmm68k_mot executable (default: SDK bin directory)")
    p.add_argument("--upstream-archive", type=Path, help="Optional legacy provenance check; the runtime source is included")
    p.add_argument("--quake-tools", type=Path, help="ericw-tools directory containing qbsp, vis, light")
    p.add_argument("--qcc", help="QuakeC compiler path or command (qcc-host, qcc or fteqcc)")
    p.add_argument("--intro-captions", type=Path, help="Private opening quote JSON; runtime aw_intro_text_overlay 0/1 selects original/readable text")
    p.add_argument("--ffmpeg", default="ffmpeg")
    p.add_argument("--xdftool", default="xdftool")
    p.add_argument("--rdbtool", default="rdbtool")
    p.add_argument("--hands", choices=("3d","sprites"), default="3d", help="First-person runtime build: sprites currently Nord unarmed only")
    add_jobs(p)
    p.add_argument('--serial-stages', action='store_true',
                   help='Run stages in order while retaining each stage job limit (diagnostics)')
    add_font_options(p)
    return p


def ask(value, prompt, interactive):
    if value is not None:
        return value
    if interactive:
        return input(prompt + ": ").strip() or None
    return None


def detected_sdk(args):
    """Find the SDK installed by our setup command, without writing anything."""
    candidate = ensure_external(args.tools_dir / "sdk", "SDK")
    assembler = args.vasm or candidate / "bin/vasmm68k_mot"
    required = (candidate / "bin/m68k-amigaos-gcc", assembler,
                candidate / "m68k-amigaos/ndk-include/exec/exec_lib.i")
    return candidate if all(path.is_file() for path in required) else None


def select_sdk(args, interactive=False, game_data=None, install_requested=False):
    """Downloads require explicit selection and consent; plans never fetch."""
    if args.sdk:
        return ensure_external(args.sdk, "SDK")
    found = detected_sdk(args)
    if found:
        print(f"Using installed Amiga SDK: {found}")
        return found

    from fetch_toolchain import SPEC, fetch
    destination = ensure_external(args.tools_dir / "sdk", "SDK download directory")
    command = [sys.executable, str(ROOT / "tools/fetch_toolchain.py"),
               "--out", str(destination)]
    print("Amiga SDK not configured. It provides the Amiga cross-compiler and assembler.")
    print(f"Pinned download: {SPEC['release']}, {SPEC['bytes']:,} bytes; size and SHA-256 checked before extraction.")
    print("SDK release page: https://github.com/AmigaPorts/m68k-amigaos-gcc/releases/tag/" + SPEC['release'])
    print("Source: " + SPEC['url'])
    print(f"Destination: {destination}")
    available = not destination.exists() and not destination.is_symlink()
    if available:
        print("Standalone SDK download command (no APT or pip installation):")
        print("  " + shlex.join(command))
    else:
        print("This destination already exists but is not a complete SDK; it will not be overwritten.")
        print("Select an existing SDK with --sdk, or choose a new --tools-dir for setup.")
    if install_requested and (args.plan or args.check):
        print("SDK setup preview only. No download or directory creation performed.")
        return None
    if args.plan:
        print("Plan mode never downloads; use the standalone command separately.")
    elif args.check:
        print("This is a prerequisite check. Only choosing 'install' and confirming will write SDK files; no build will run.")
    prompt = "SDK root, 'install' to download" if available and not args.plan else "Existing AmigaPorts SDK root"
    raw = 'install' if install_requested else ask(None, prompt + " (Enter to report missing)", interactive)
    if not raw:
        return None
    if raw.casefold() != 'install':
        return ensure_external(raw, "SDK")
    if args.plan or not available:
        print("SDK download unavailable in this mode or destination. Use the setup guidance above.")
        return None
    if game_data and (inside(destination, game_data) or inside(game_data, destination)):
        raise ValueError("Keep the SDK download directory separate from the game installation")
    if input("Download and extract this SDK now? [y/N] ").strip().casefold() in ("y", "yes"):
        try:
            fetch(destination)
        except tarfile.TarError as exc:
            raise ValueError(f"SDK extraction failed: {exc}") from exc
        return destination
    print("SDK download declined. No SDK files created.")
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
    print("Use your installed Morrowind files. Store pages:")
    print("  GOG: https://www.gog.com/en/game/the_elder_scrolls_iii_morrowind_goty_edition")
    print("  Steam: https://store.steampowered.com/app/22320/The_Elder_Scrolls_III_Morrowind_Game_of_the_Year_Edition/")
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


def choose_installation(candidates):
    print("Multiple candidate installations found; choose the one to validate:")
    for number, path in enumerate(candidates, 1):
        print(f"  {number}. {path}")
    while True:
        answer = input("Installation number (Enter to cancel): ").strip()
        if not answer:
            raise ValueError("No installation selected; rerun with --data-files pointing to the desired folder")
        if answer.isdigit() and 1 <= int(answer) <= len(candidates):
            return candidates[int(answer)-1]
        print(f"Enter a number from 1 to {len(candidates)}.")


def executable(value, label, errors):
    found = shutil.which(str(value)) if value else None
    if not found:
        errors.append(f"{label}: executable not found ({value or 'not supplied'})")
        return None
    return str(Path(found).resolve())


def prepare_dependencies(args, interactive):
    if args.autoinstall or (interactive and sys.platform == 'linux' and not args.plan):
        from setup_build import setup
        if not args.sdk:
            args.sdk = detected_sdk(args)
        if not setup(args, getattr(args, '_argv', []), interactive=interactive):
            raise ValueError('Dependency setup was not accepted; build stopped before conversion')
        if not args.sdk:
            args.sdk = detected_sdk(args)


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
            with Progress("Verifying game files, containers and reference hashes"):
                args.input_report = input_check.inspect(raw, args.stage, args.allow_data_differences,
                                                       notify=print, choose=choose_installation if interactive else None)
            input_check.display(args.input_report)
            errors.extend(args.input_report["errors"])
            data = Path(args.input_report["data_files"])
            if inside(args.workspace, data) or inside(data, args.workspace):
                errors.append("Use an output workspace separate from the game installation, not its parent or child")
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
    else:
        errors.append("Supply --data-files '/path/to/Morrowind/Data Files'")
    if errors:
        raise ValueError("Game inputs need attention before tool setup:\n  - " + "\n  - ".join(errors))
    args.data_files = data
    if args.stage == "aga":
        prepare_dependencies(args, interactive)
        for module, package in (("setuptools", "setuptools>=68 (provides distutils for PyFFI)"),
                                ("PIL", "Pillow"), ("numpy", "numpy"),
                                ("scipy", "scipy"), ("pyffi", "PyFFI==2.2.3"),
                                ("fast_simplification", "fast-simplification==0.2.0")):
            if importlib.util.find_spec(module) is None:
                errors.append(f"Python dependency missing: {package}; use this Python environment's pip")
        if not errors and not args.plan:
            try:
                with Progress('Checking the PyFFI TES3 reader'):
                    from prepare_scenery import check_nif_reader
                    check_nif_reader()
            except (ImportError, AttributeError, ValueError, OSError) as exc:
                errors.append(f'PyFFI reader check failed: {exc}. Run --autoinstall to install required Python dependencies, including setuptools; see docs/BUILD_DEPENDENCIES.md')
        if errors:
            raise ValueError('Python conversion dependencies need attention:\n  - ' + '\n  - '.join(errors))
        for name in ("make",):
            tools[name] = executable(name, name, errors)
        for name in ("ffmpeg", "xdftool", "rdbtool"):
            tools[name] = executable(getattr(args, name), name, errors)
        sdk = select_sdk(args, interactive, game_data=data)
        if sdk:
            args.sdk = ensure_external(sdk, "SDK")
            tools["m68k-amigaos-gcc"] = executable(args.sdk / "bin/m68k-amigaos-gcc", "m68k-amigaos-gcc", errors)
            tools["vasmm68k_mot"] = executable(args.vasm or args.sdk / "bin/vasmm68k_mot", "vasmm68k_mot", errors)
            if not (args.sdk / "m68k-amigaos/ndk-include/exec/exec_lib.i").is_file():
                errors.append("SDK NDK includes missing: m68k-amigaos/ndk-include/exec/exec_lib.i")
        else:
            errors.append("Amiga SDK missing: use the download command above or supply --sdk /path/to/sdk")
        try:
            runtime_sources()
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
        archive = args.upstream_archive
        if archive:
            args.upstream_archive = ensure_external(archive, "upstream source archive")
            if not args.upstream_archive.is_file() or sha256(args.upstream_archive) != UPSTREAM_SHA256:
                errors.append(f"AmiQuake archive must match SHA-256 {UPSTREAM_SHA256}")
        if interactive:
            print("Map tools: https://github.com/ericwa/ericw-tools/releases/tag/v0.18.1")
        tool_dir = build_versions.find_quake_tools(args)
        if not tool_dir and not all(shutil.which(name) for name in ('qbsp', 'vis', 'light')):
            tool_dir = ask(args.quake_tools, "ericw-tools bin directory (blank to use PATH)", interactive)
        for name in ("qbsp", "vis", "light"):
            value = Path(tool_dir).expanduser() / name if tool_dir else name
            tools[name] = executable(value, name, errors)
        qcc = build_versions.find_qcc(args)
        if not qcc:
            print("QuakeC compiler missing. Ubuntu/Debian package: sudo apt-get install fteqcc")
            print("FTEQCC: https://fte.triptohell.info/ | Reference compiler: https://github.com/id-Software/Quake-Tools")
            qcc = ask(args.qcc, "QuakeC compiler path (qcc-host, qcc or fteqcc)", interactive)
        tools["qcc"] = executable(qcc, "QuakeC compiler", errors)
        if tools["qcc"] and not args.plan:
            print(f"Checking QuakeC compilation with {tools['qcc']} (temporary files only)...", flush=True)
            try:
                check_quakec(tools['qcc'], args.hands)
                print("  [ok] AmiWind QuakeC compiled; program version and system-variable CRC match the engine.")
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                errors.append(f"QuakeC compile check failed: {exc}")
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
    prepare_dependencies(args, interactive)
    sdk = select_sdk(args, interactive)
    if not sdk:
        raise ValueError("Amiga SDK missing: use the download command above or supply --sdk for the asset-free native compile")
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
                    "--out", str(run / "engine"), "--hands", args.hands, "--jobs", str(resolve_jobs(args.jobs))]),
        ("dry-run-image", [sys.executable, str(ROOT / "tools/build_dry_run.py"), *common,
                           "--engine", str(binary), "--out", str(run / "image")]),
    ]


def commands(args, tools, run):
    font_options = getattr(args, "font_options", None) or resolve_font_options(args)
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
            ("scenery", tool("prepare_scenery.py", "--workspace", work, "--out", run / "scenery", "--jobs", resolve_jobs(args.jobs))),
            ("scene", tool("prepare_quake.py", "--workspace", work, "--scene", run / "scenery", "--out", run / "alias-scene", "--jobs", resolve_jobs(args.jobs))),
            ("bsp", tool("prepare_mesh_bsp.py", "--scene", run / "alias-scene", "--scenery", run / "scenery", "--out", run / "bsp-scene", "--jobs", resolve_jobs(args.jobs),
                *[part for name in ("qbsp", "vis", "light") for part in ("--" + name, tools[name])])),
            ("npcs", tool("prepare_npcs.py", "--data-files", args.data_files, "--scene", run / "bsp-scene", "--out", run / "npc-scene", "--ffmpeg", tools["ffmpeg"])),
            ("hands", tool("prepare_hands.py", "--data-files", args.data_files, "--scene", run / "npc-scene", "--out", run / "hands-scene")),
            ("interior", tool("prepare_interior.py", "--data-files", args.data_files, "--scene", run / "hands-scene", "--out", run / "interior-scene", "--jobs", resolve_jobs(args.jobs),
                *[part for name in ("qbsp", "vis", "light") for part in ("--" + name, tools[name])])),
            ("dialogue-lookup", tool("prepare_dialogue_lookup.py", "--data-files", args.data_files, "--out", run / "voice-lookup.json")),
            ("intro", tool("prepare_intro.py", "--jobs", resolve_jobs(args.jobs), "--data-files", args.data_files, "--scene", run / "interior-scene", "--out", run / "intro-scene", "--ffmpeg", tools["ffmpeg"])),
            ("census", tool("prepare_census.py", "--data-files", args.data_files, "--scene", run / "intro-scene",
                "--jobs", resolve_jobs(args.jobs),
                *[part for name in ("qbsp", "vis", "light") for part in ("--" + name, tools[name])])),
            ("area", tool("prepare_area.py", "--data-files", args.data_files, "--scene", run / "intro-scene",
                "--jobs", resolve_jobs(args.jobs), "--ffmpeg", tools["ffmpeg"],
                "--qbsp", tools["qbsp"], "--vis", tools["vis"], "--light", tools["light"])),
            ("balmora", tool("prepare_balmora.py", "--data-files", args.data_files, "--scene", run / "intro-scene",
                "--out", run / "balmora-work", "--jobs", resolve_jobs(args.jobs), "--ffmpeg", tools["ffmpeg"],
                "--qbsp", tools["qbsp"], "--vis", tools["vis"], "--light", tools["light"])),
            ("balmora-interiors", tool("prepare_balmora_interiors.py", "--data-files", args.data_files,
                "--scene", run / "intro-scene", "--jobs", resolve_jobs(args.jobs), "--ffmpeg", tools["ffmpeg"],
                "--qbsp", tools["qbsp"], "--vis", tools["vis"], "--light", tools["light"])),
            ("door-audio", tool("prepare_door_audio.py", "--data-files", args.data_files, "--scene", run / "intro-scene", "--ffmpeg", tools["ffmpeg"])),
            ("character", tool("prepare_character.py", "--jobs", resolve_jobs(args.jobs), "--data-files", args.data_files, "--scene", run / "intro-scene")),
            ("reading", tool("prepare_reading.py", "--data-files", args.data_files, "--scene", run / "intro-scene",
                "--bitmap-paper-ink", font_options["bitmap_paper_ink"])),
            ("opening-references", tool("prepare_opening_refs.py", "--data-files", args.data_files, "--scene", run / "intro-scene")),
            ("world-survey", tool("survey_vvardenfell.py", "--data-files", args.data_files,
                "--out", run / "world-survey", "--jobs", resolve_jobs(args.jobs))),
            ("world-terrain", tool("prepare_world_regions.py", "--survey", run / "world-survey",
                "--data-files", args.data_files, "--scene", run / "intro-scene",
                "--out", run / "world-terrain", "--bindir", Path(tools['qbsp']).parent,
                "--jobs", resolve_jobs(args.jobs))),
            ("music", tool("prepare_music.py", "--data-files", args.data_files, "--ffmpeg", tools["ffmpeg"], "--out", run / "music", "--jobs", resolve_jobs(args.jobs))),
            ("engine", tool("build_aga.py", "engine", "--sdk", args.sdk, "--out", run / "engine", "--hands", args.hands, "--jobs", resolve_jobs(args.jobs),
                            *(["--vasm", args.vasm] if args.vasm else []))),
            ("image", tool("build_aga.py", "image", *(["--intro-captions", args.intro_captions] if getattr(args,"intro_captions",None) else []), "--data-files", args.data_files, "--hands", args.hands, "--scene", run / "intro-scene", "--music", run / "music", "--engine", binary, "--out", run / "image",
                *[part for name in ("qcc", "qbsp", "vis", "light", "xdftool", "rdbtool") for part in ("--" + name, tools[name])])),
        ]
    return steps


def execute(steps, run, metadata):
    if metadata.get('compiler_jobs', 1) > 1 and not metadata.get('serial_stages', False):
        from build_parallel import execute_parallel
        return execute_parallel(steps, run, metadata, ROOT)
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
        section(f"Build [{number}/{len(steps)}]: {name}")
        print(f"Log: {log}", flush=True)
        entry = {"name": name, "command": command, "status": "running", "log": str(log)}
        receipt["steps"].append(entry)
        save()
        start = time.monotonic()
        try:
            with log.open("w") as output:
                with Progress(f"[{number}/{len(steps)}] {name}"), live_log(log):
                    from build_parallel import THREAD_LIMITS
                    subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT, check=True,
                                   env=dict(os.environ, **THREAD_LIMITS, PYTHONUNBUFFERED='1',
                                            AMIWIND_BUILD_JOBS=str(metadata.get('compiler_jobs', 1))))
        except (OSError, subprocess.CalledProcessError, KeyboardInterrupt) as exc:
            status = "cancelled" if isinstance(exc, KeyboardInterrupt) else "failed"
            entry.update(status=status, elapsed_seconds=round(time.monotonic() - start, 3))
            receipt["status"] = status
            save()
            if isinstance(exc, KeyboardInterrupt):
                print(f"Build cancelled. Earlier results and logs retained in {run}", flush=True)
                raise
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
        "compiler_jobs": resolve_jobs(args.jobs),
        "serial_stages": args.serial_stages,
        "font_options": getattr(args, "font_options", None) or resolve_font_options(args),
        "input_check": getattr(args, "input_report", None),
        "tool_sha256": {name: sha256(path) for name, path in tools.items()},
        "input_sha256": {} if args.dry_run else hashes(args.data_files, lambda path: is_game_input(path.relative_to(args.data_files))),
        "source_sha256": hashes(ROOT, lambda path:
            (path.suffix in (".py", ".c", ".h", ".patch", ".qc", ".asm", ".sh", ".cfg") or path.name in ("Makefile", "VERSION", "pyproject.toml"))
            and path.relative_to(ROOT).parts[0] != "out"
            and "__pycache__" not in path.parts),
    }


def main(argv=None):
    # Also cover direct Python invocations and subsequent environment re-exec.
    os.environ['PYTHONUNBUFFERED'] = '1'
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(line_buffering=True)
    p = parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    args = p.parse_args(argv)
    args._argv = argv
    try:
        args.font_options = resolve_font_options(args)
        if sys.version_info < (3, 10):
            raise ValueError("Python 3.10 or newer is required")
        if args.yes and not args.autoinstall:
            raise ValueError('--yes requires --autoinstall')
        if args.autoinstall and (args.install_sdk or args.versions or args.check_inputs or args.stage != 'aga'):
            raise ValueError('--autoinstall is for AGA builds/checks; use it separately from setup-only or inventory modes')
        if sum((args.install_dependencies or args.install_sdk, args.versions, args.check_inputs)) > 1:
            raise ValueError("Use dependency/SDK setup, --versions or --check-inputs separately")
        emulator = None
        if args.kickstart_file and not args.autorun_fs_uae:
            raise ValueError('--kickstart-file requires --autorun-fs-uae')
        if args.autorun_fs_uae:
            if args.stage != 'aga' or args.install_dependencies or args.install_sdk or args.versions or args.check_inputs:
                raise ValueError('--autorun-fs-uae requires an AGA build; setup-only and inventory modes do not create an HDF')
            from run_fs_uae import prepare_launch
            emulator = prepare_launch(args.kickstart_file, interactive=sys.stdin.isatty() and not args.yes)
            # Keep an interactively selected/relative ROM across managed-venv re-exec.
            argv.extend(['--kickstart-file', str(emulator[1])])
            if args.check or args.plan:
                print('Check/plan mode: FS-UAE will not launch and no emulator configuration will be written.')
        if args.install_dependencies:
            if args.autoinstall:
                from setup_build import setup, use_environment
                use_environment(args, argv)
                args.sdk = args.sdk or detected_sdk(args)
                if args.data_files:
                    args.data_files = installed_game_path(args.data_files).expanduser().resolve()
                accepted = setup(args, argv, interactive=sys.stdin.isatty(), preview=args.plan or args.check)
                return 0 if accepted or args.plan or args.check else 1
            from install_dependencies import install
            return install(args)
        if args.install_sdk:
            if args.sdk:
                raise ValueError("--install-sdk installs into --tools-dir/sdk; use --sdk only to select an existing SDK for checks/builds")
            game = installed_game_path(args.data_files).expanduser().resolve() if args.data_files else None
            select_sdk(args, interactive=sys.stdin.isatty(), game_data=game, install_requested=True)
            return 0
        if not args.check_inputs and args.stage == 'aga':
            from setup_build import use_environment
            use_environment(args, argv)
        if args.autoinstall and args.plan:
            from setup_build import setup
            args.sdk = args.sdk or detected_sdk(args)
            if args.data_files:
                args.data_files = installed_game_path(args.data_files).expanduser().resolve()
            setup(args, argv, preview=True)
            return 0
        if args.versions:
            if not args.sdk:
                args.sdk = detected_sdk(args)
            build_versions.report(args)
            return 0
        if args.check_inputs:
            raw = game_input(args.data_files, sys.stdin.isatty())
            if raw is None:
                raise ValueError("Supply --data-files with your Morrowind installation root")
            print("Checking the installed file tree, containers and reference SHA-256 hashes...", flush=True)
            with Progress("Verifying game files, containers and reference hashes"):
                report = input_check.inspect(raw, args.stage, args.allow_data_differences,
                                             notify=print, choose=choose_installation if sys.stdin.isatty() else None)
            input_check.display(report)
            return 1 if report["errors"] else 0
        args.name = args.name or datetime.now(timezone.utc).strftime("build-%Y%m%d-%H%M%S")
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}", args.name):
            raise ValueError("--name must be 1–64 letters, digits, dots, hyphens or underscores")
        if args.stage == "aga" and not args.dry_run:
            print("Bitmap paper ink: " + args.font_options["bitmap_paper_ink"] +
                  " (" + args.font_options["selected_by"] +
                  "); preferred TTF conversion and dialogue/menu fonts unchanged.")
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
        with Progress("Recording input, tool and source checksums"):
            metadata = provenance(args, tools)
        print(f"Build run: {run}\nLive tool output follows; per-stage logs are saved in {run / 'logs'}.", flush=True)
        execute(steps, run, metadata)
        if args.dry_run:
            result = run / "image" / f"AmiWind-v{VERSION}-dry-run.hdf"
            print(f"Asset-free test build complete: {result}\nNo game assets or ROMs were used. This is not a playable demo.")
        else:
            result = run / "image" / f"AmiWind-v{VERSION}.hdf" if args.stage == "aga" else run / "work/generated/seyda-neen"
            print(f"Build complete: {result}\nPrivate generated content: do not include it in the public source package.")
        if emulator:
            from run_fs_uae import launch
            try:
                if launch(result, *emulator):
                    print('[warning] Build succeeded, but FS-UAE launch/playtest did not complete successfully. HDF retained.')
            except (OSError, ValueError) as exc:
                print(f'[warning] Build succeeded; FS-UAE launch skipped: {exc}. HDF retained: {result}')
        return 0
    except (KeyboardInterrupt, EOFError):
        p.exit(130, "\nCancelled.\n")
    except (OSError, ValueError, RuntimeError) as exc:
        p.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
