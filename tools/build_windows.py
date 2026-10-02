#!/usr/bin/env python3
"""Native Windows environment adapter for the shared AmiWind build pipeline.

No conversion stages, SDK versions or Python requirements are duplicated here.
MSYS2 and the Windows SDK are supplied explicitly; Linux downloads are never used.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import sysconfig

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import build
from install_dependencies import PYTHON_PACKAGES
from mwad.paths import ensure_external


def arguments(argv):
    adapter = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    adapter.add_argument('--msys2', type=Path, help='MSYS2 root (default: TOOLS/msys64)')
    adapter.add_argument('--setup-python', action='store_true', help='Create the Windows venv and install shared Python requirements; then exit')
    windows, shared = adapter.parse_known_args(argv)
    # The shared parser remains authoritative for every actual build option.
    options = build.parser().parse_args(shared)
    return windows, options, shared


def environment(options, msys2, original=None):
    env = dict(os.environ if original is None else original)
    tools = options.tools_dir.expanduser().resolve()
    sdk = (options.sdk or tools / 'sdk').expanduser().resolve()
    paths = [tools / 'venv/Scripts', sdk / 'bin', tools / 'ffmpeg/bin', msys2 / 'usr/bin']
    env['PATH'] = os.pathsep.join([str(path) for path in paths] + [env.get('PATH', '')])
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONUNBUFFERED'] = '1'
    env['PYTHONUTF8'] = '1'
    # Do not inherit a Linux/MSYS Python module search path or Python home.
    env.pop('PYTHONHOME', None)
    env.pop('PYTHONPATH', None)
    return env


def setup_python(options, env):
    tools = ensure_external(options.tools_dir, 'Windows dependency tools directory')
    venv = tools / 'venv'
    python = venv / 'Scripts/python.exe'
    if venv.is_symlink() or (venv.exists() and not ((venv / 'pyvenv.cfg').is_file() and python.is_file())):
        raise ValueError('Refusing to reuse an incomplete or non-Windows venv: ' + str(venv))
    commands = []
    if not venv.exists():
        commands.append([sys.executable, '-m', 'venv', str(venv)])
    commands.append([str(python), '-m', 'pip', 'install', '--disable-pip-version-check', *PYTHON_PACKAGES])
    print('Windows Python setup only; native tools are installed separately.', flush=True)
    for command in commands:
        print('& ' + ' '.join("'" + part.replace("'", "''") + "'" for part in command), flush=True)
    if options.plan:
        print('Preview only. No directories created or packages installed.')
        return 0
    if options.data_files:
        raise ValueError('--setup-python does not accept game inputs; run it separately from conversion')
    tools.mkdir(parents=True, exist_ok=True)
    for command in commands:
        subprocess.run(command, env=env, check=True)
    print('Python environment ready: ' + str(python), flush=True)
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--help' in argv or '-h' in argv:
        build.parser().print_help()
        print('\nWindows additions:\n  --msys2 PATH     MSYS2 root (default: TOOLS/msys64)'
              '\n  --setup-python   Install shared Python requirements into TOOLS/venv; then exit'
              '\n                   Combine with --plan to preview without installation.'
              '\nRun setup-windows.cmd -Yes to provision the Windows tools; see docs/WINDOWS_BUILD.md.')
        return 0
    try:
        windows, options, shared = arguments(argv)
        if sys.platform != 'win32' or sysconfig.get_platform().startswith('mingw'):
            raise ValueError('build.cmd/build.ps1 requires official Windows CPython; use build.sh on Linux')
        if options.autoinstall or options.install_dependencies or options.install_sdk:
            raise ValueError('Linux automatic provisioning is not used on Windows. Use --setup-python '
                             'for Python packages, or setup-windows.cmd -Yes for complete Windows setup.')
        if windows.setup_python and (options.host_plan or options.versions or options.check_inputs or options.check or options.dry_run):
            raise ValueError('--setup-python must run separately from inventory, checks and builds')
        tools = ensure_external(options.tools_dir, 'Windows tools directory')
        msys2 = (windows.msys2 or tools / 'msys64').expanduser().resolve()
        env = environment(options, msys2)
        if windows.setup_python:
            return setup_python(options, env)
        if not (options.host_plan or options.versions or options.check_inputs):
            missing = [str(msys2 / 'usr/bin' / name) for name in ('make.exe', 'sh.exe')
                       if not (msys2 / 'usr/bin' / name).is_file()]
            if missing:
                raise ValueError('MSYS2 make/shell missing: ' + ', '.join(missing)
                                 + '. Install MSYS2 and its make package, or select --msys2 PATH.')
        python = tools / 'venv/Scripts/python.exe'
        if os.environ.get('AMIWIND_PYTHON') or not python.is_file():
            python = Path(sys.executable)
        # Avoid the Linux-oriented re-exec path; the selected interpreter is explicit.
        env['AMIWIND_PYTHON'] = str(python)
        return subprocess.run([str(python), '-B', '-u', '-X', 'utf8', str(ROOT / 'tools/build.py'), *shared],
                              env=env).returncode
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print('Windows build: ' + str(exc), file=sys.stderr)
        return exc.returncode if isinstance(exc, subprocess.CalledProcessError) else 1


if __name__ == '__main__':
    sys.exit(main())
