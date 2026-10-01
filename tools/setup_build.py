"""One confirmed setup proposal, followed by the original build invocation."""
import importlib.util
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

from mwad.paths import ensure_external, inside
from mwad.progress import section, setup_step
import build_versions
from build_host import venv_python
from fetch_toolchain import SPEC
from fetch_native import ERICW, QCC_COMMIT, QCC_URL
from install_dependencies import HOST_PACKAGES, PYTHON_PACKAGES, missing_packages, supported_host

ROOT = Path(__file__).resolve().parents[1]


def use_environment(args, argv, force=False):
    """Use a previously created environment without shell activation."""
    venv = ensure_external(args.tools_dir / 'venv', 'Python environment')
    python = venv_python(venv)
    if not (venv/'pyvenv.cfg').is_file() or not python.is_file():
        return
    if os.environ.get('AMIWIND_PYTHON') and not force:
        return
    # Keep the venv path, not the interpreter symlink target, for exec.
    os.environ['PATH'] = str(python.parent) + os.pathsep + os.environ.get('PATH', '')
    current = Path(sys.prefix).resolve() == venv
    if current and not force:
        return
    if not current and os.environ.get('AMIWIND_ACTIVE_ENV') == str(venv):
        raise ValueError('The selected virtual environment did not activate correctly: ' + str(venv))
    env = dict(os.environ, VIRTUAL_ENV=str(venv), AMIWIND_ACTIVE_ENV=str(venv))
    print(f'Using Python environment: {venv}', flush=True)
    sys.stdout.flush(); sys.stderr.flush()
    os.execve(str(python), [str(python), str(ROOT/'tools/build.py'), *argv], env)


def proposal(args):
    """Only inspect and plan here. No package install, download or mkdir."""
    supported_host()
    directory = ensure_external(args.tools_dir, 'dependency tools directory')
    if args.data_files and (inside(directory, args.data_files) or inside(args.data_files, directory)):
        raise ValueError('Keep the tools directory separate from the game installation')
    packages = list(HOST_PACKAGES)
    missing = missing_packages(packages)
    modules = ('amitools',) if args.dry_run else ('setuptools', 'PIL', 'numpy', 'scipy', 'pyffi', 'fast_simplification', 'amitools')
    python_missing = [name for name in modules if importlib.util.find_spec(name) is None]
    if args.autoinstall and not (directory/'venv/pyvenv.cfg').is_file():
        python_missing = list(modules)  # An empty tools directory must exercise fresh Python setup.
    commands = []
    if missing:
        prefix = [] if os.geteuid() == 0 else ['sudo']
        if prefix and not shutil.which('sudo'):
            raise ValueError('Automatic APT setup needs sudo for missing packages')
        commands += [prefix + ['apt-get', 'update'], prefix + ['apt-get', 'install', '--no-remove', *(['-y'] if args.yes else []), *missing]]
    if python_missing:
        venv = directory/'venv'
        if venv.is_symlink() or (venv.exists() and not (venv/'pyvenv.cfg').is_file()):
            raise ValueError('Refusing to overwrite a non-venv directory: ' + str(venv))
        if not venv.exists():
            commands.append(['/usr/bin/python3', '-m', 'venv', str(venv)])
        elif not (venv/'bin/python').is_file():
            raise ValueError('Incomplete Python environment: ' + str(venv))
        requirements = ('amitools==0.8.1',) if args.dry_run else PYTHON_PACKAGES
        commands.append([str(venv/'bin/python'), '-m', 'pip', 'install', '--verbose', *requirements])
    downloads = []
    if not args.sdk:
        downloads.append(('sdk', directory/'sdk', SPEC['url']))
    if not args.dry_run:
        map_dir = build_versions.find_quake_tools(args)
        if not map_dir and (args.autoinstall or not all(shutil.which(name) for name in ('qbsp', 'vis', 'light'))):
            downloads.append(('ericw', directory/'ericw', ERICW['url']))
        qcc = build_versions.find_qcc(args)
        # --autoinstall follows the tested reference recipe unless explicitly overridden.
        reference_needed = args.autoinstall and not args.qcc and not shutil.which(str(directory/'Quake-Tools/qcc-host'))
        if not qcc or reference_needed:
            downloads.append(('qcc', directory/'Quake-Tools', QCC_URL))
    for component, target, url in downloads:
        if target.exists() or target.is_symlink():
            raise ValueError(f'Incomplete/unselected {component} destination will not be overwritten: {target}; use --tools-dir for a new location or supply its existing tool path')
        script = 'fetch_toolchain.py' if component == 'sdk' else 'fetch_native.py'
        command = [sys.executable, str(ROOT/'tools'/script)]
        if component != 'sdk':
            command.append(component)
        commands.append([*command, '--out', str(target)])
    return commands, python_missing, downloads


def setup(args, argv, interactive=False, preview=False):
    commands, python_missing, downloads = proposal(args)
    if not commands:
        print('Build dependencies already available; continuing.')
        return True
    section('Build dependency setup proposal')
    print(f'Tools and Python environment: {args.tools_dir.resolve()}')
    section('System packages (APT)')
    apt = next((c for c in commands if 'apt-get' in c and 'install' in c), None)
    packages = [item for item in apt[apt.index('install') + 1:] if not item.startswith('-')] if apt else []
    print('APT packages requested: ' + (', '.join(packages) or 'none; all required system packages are already installed.'))
    if packages:
        print('APT refreshes package lists first, then resolves these packages and any dependencies.')
        print('APT shows the final changes and sizes before its confirmation (unless --yes was selected).')
    section('Python environment')
    for command in commands:
        if 'venv' in command or 'pip' in command:
            print('  ' + shlex.join(command))
    if not python_missing:
        print('Python dependencies already available.')
    section('Native tool downloads')
    print('SDK releases: https://github.com/AmigaPorts/m68k-amigaos-gcc/releases')
    print('Map tools: https://github.com/ericwa/ericw-tools/releases/tag/v0.18.1')
    print('Reference QuakeC source: https://github.com/id-Software/Quake-Tools/tree/' + QCC_COMMIT)
    for component, target, url in downloads:
        detail = ('pinned source files checked by size/SHA-256, then compiled with cc' if component == 'qcc'
                  else f"{(SPEC if component == 'sdk' else ERICW)['bytes']:,} bytes; pinned SHA-256 checked before extraction")
        print(f'  {component}: {detail}\n    {url}\n    -> {target}')
    if not downloads:
        print('No native tool downloads required.')
    if preview or args.plan:
        print('Preview only. No dependency installation or directory creation performed.')
        return False
    if not interactive and not args.autoinstall:
        print('Rerun with --autoinstall to confirm setup and continue the build.')
        return False
    section(f'Confirm setup: {len(commands)} steps')
    answer = 'yes' if args.yes else input("Install these dependencies and continue? [y/N, or 'paths' to supply existing tools] ").strip().casefold()
    if answer == 'paths':
        for component, _, _ in downloads:
            value = input(f'Existing {component} path (SDK root / ericw bin directory / qcc executable): ').strip()
            if not value:
                raise ValueError('No path selected; setup cancelled')
            if component == 'sdk': args.sdk = ensure_external(value, 'SDK')
            elif component == 'ericw': args.quake_tools = Path(value).expanduser().resolve()
            else: args.qcc = str(Path(value).expanduser().resolve())
        return setup(args, argv, interactive=interactive)
    if answer not in ('y', 'yes'):
        print('Setup declined. No dependencies changed.')
        return False
    try:
        for number, command in enumerate(commands, 1):
            with setup_step(command, number, len(commands)):
                subprocess.run(command, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        print('Manual host/Python setup: docs/LINUX_BUILD.md (Manual or partial setup)')
        print('Online guide: https://github.com/FlyingFathead/amiwind/blob/main/docs/LINUX_BUILD.md')
        raise RuntimeError('Dependency setup stopped. Completed tools were preserved; rerun the same build command to retry. ' + str(exc)) from exc
    print('Dependency setup complete; continuing the build.')
    if python_missing:
        resumed = list(argv)
        if args.data_files:
            resumed += ['--data-files', str(args.data_files)]
        for flag, value in (('--sdk', args.sdk), ('--quake-tools', args.quake_tools), ('--qcc', args.qcc)):
            if value: resumed += [flag, str(value)]
        use_environment(args, resumed, force=True)
        raise RuntimeError('Python environment could not be activated after setup')
    return True
