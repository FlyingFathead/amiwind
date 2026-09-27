#!/usr/bin/env python3
"""Optional, confirmed Ubuntu/Debian host setup; never provisions game data."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

from mwad.paths import ensure_external, inside, installed_game_path

HOST_PACKAGES = ("python3", "python3-venv", "python3-pip", "build-essential",
                 "ffmpeg", "unzip", "xz-utils", "fonts-dejavu-core")
PYTHON_PACKAGES = ("PyFFI==2.2.3", "numpy>=1.23", "Pillow>=9.1",
                   "fast-simplification==0.2.0", "scipy>=1.10", "amitools==0.8.1")


def supported_host():
    if sys.platform != "linux":
        raise ValueError("Automatic host setup supports Ubuntu/Debian Linux, including WSL Ubuntu. See docs/LINUX_BUILD.md.")
    info = {}
    for line in Path("/etc/os-release").read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            info[key] = value.strip('"')
    if not {"ubuntu", "debian"}.intersection((info.get("ID", "") + " " + info.get("ID_LIKE", "")).split()):
        raise ValueError("Automatic host setup supports Ubuntu/Debian; install equivalent packages manually on this distribution")
    if not shutil.which("apt-get") or not shutil.which("dpkg-query"):
        raise ValueError("apt-get and dpkg-query are required for automatic host setup")


def missing_packages():
    missing = []
    for package in HOST_PACKAGES:
        result = subprocess.run(["dpkg-query", "-W", "-f=${Status}", package],
                                capture_output=True, text=True, timeout=15)
        if result.returncode or result.stdout.strip() != "install ok installed":
            missing.append(package)
    return missing


def install(args, confirm=None):
    supported_host()
    directory = ensure_external(args.tools_dir, "dependency tools directory")
    if args.data_files:
        game = installed_game_path(args.data_files).expanduser().resolve()
        if inside(directory, game) or inside(game, directory):
            raise ValueError("Keep the tools directory separate from the game installation")
    venv = directory / "venv"
    if venv.is_symlink() or (venv.exists() and not (venv / "pyvenv.cfg").is_file()):
        raise ValueError(f"Refusing to reuse a non-venv directory or symlink: {venv}")
    python = venv / "bin/python"
    if venv.exists() and not python.is_file():
        raise ValueError(f"Existing virtual environment has no bin/python: {venv}")
    missing = missing_packages()
    # Use the distribution Python so python3-venv matches its interpreter.
    host_python = Path("/usr/bin/python3")
    version = subprocess.check_output([str(host_python), "-c", "import sys; print('%d.%d' % sys.version_info[:2])"], text=True).strip()
    if tuple(map(int, version.split("."))) < (3, 10):
        raise ValueError("The distribution Python must be 3.10+; use Ubuntu 22.04+ or a suitable Debian release")
    prefix = [] if os.geteuid() == 0 else ["sudo"]
    if missing and prefix and not shutil.which("sudo"):
        raise ValueError("Missing system packages need sudo; install them with your system administrator")
    commands = []
    if missing:
        commands += [prefix + ["apt-get", "update"],
                     prefix + ["apt-get", "install", "--no-remove", *missing]]
    if not venv.exists():
        commands.append([str(host_python), "-m", "venv", str(venv)])
    commands.append([str(python), "-m", "pip", "install", *PYTHON_PACKAGES])
    print("Dependency setup preview")
    print("Missing Ubuntu/Debian packages: " + (", ".join(missing) or "none"))
    print(f"Python environment: {venv} ({'reuse' if venv.exists() else 'create'})")
    print("APT uses configured repositories; pip uses configured package indexes. Network access is required.")
    print("APT will show resolved package versions and sizes before its own confirmation.")
    if args.install_sdk:
        from fetch_toolchain import SPEC
        if (directory / 'sdk').exists():
            raise ValueError("SDK destination already exists; omit --install-sdk to reuse it")
        print(f"Amiga SDK: {SPEC['release']}, {SPEC['bytes']:,} download bytes; SHA-256 {SPEC['sha256']}")
        print("SDK source: " + SPEC['url'])
        commands.append([sys.executable, str(Path(__file__).with_name('fetch_toolchain.py')), '--out', str(directory/'sdk')])
    else:
        print("Amiga SDK/vasm: separate setup, or rerun with --install-sdk for the pinned Linux x86_64 download.")
    print("ericw-tools and qcc-host require separate setup for full game conversion; the dry-run does not need them.")
    for command in commands:
        print("  " + shlex.join(command))
    if args.plan or args.check:
        print("Preview only. No installation or directory creation performed.")
        return 0
    try:
        answer = (confirm or input)("Run this dependency setup? [y/N] ")
    except EOFError:
        answer = ""
    if answer.strip().casefold() not in ("y", "yes"):
        print("Cancelled. No installation or directory creation performed.")
        return 0
    try:
        for command in commands:
            subprocess.run(command, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("Dependency setup stopped; earlier completed installations remain. Fix the reported error and rerun setup.") from exc
    print("Host dependency setup completed. In this shell, run:")
    print("  . " + shlex.quote(str(venv / "bin/activate")))
    print("  ./build.sh --versions")
    print("Then supply your game path and external native tools to ./build.sh --check.")
    if args.install_sdk:
        print("Amiga SDK ready: --sdk " + shlex.quote(str(directory/'sdk')))
    return 0
