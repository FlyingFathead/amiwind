"""Host-specific paths and a read-only build setup inventory."""
import argparse
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import sysconfig


def host_name():
    return 'windows' if sys.platform == 'win32' else 'linux' if sys.platform == 'linux' else sys.platform


def executable_path(value):
    """Resolve an explicit Windows executable without altering its arguments."""
    path = Path(value)
    if host_name() == 'windows' and path.suffix.lower() != '.exe':
        candidate = Path(str(path) + '.exe')
        if candidate.is_file():
            return candidate
    return path


def find_executable(value):
    if not value:
        return None
    found = shutil.which(str(executable_path(value)))
    return str(Path(found).resolve()) if found else None


def venv_python(directory):
    directory = Path(directory)
    if host_name() == 'windows':
        if sysconfig.get_platform().startswith('mingw'):
            return directory / 'bin/python.exe'
        return directory / 'Scripts/python.exe'
    return directory / 'bin/python'


def make_python_assignment(interpreter=None):
    """Quote for make's POSIX recipe shell, preserving literal make dollars."""
    path = Path(interpreter or sys.executable).as_posix()
    return 'PYTHON=' + shlex.quote(path).replace('$', '$$')


def fallback_font(value=None, tools_dir=None):
    if value is not None:
        path = Path(value).expanduser().resolve()
        if not path.is_file():
            raise ValueError('Fallback font not found: ' + str(path))
        return path
    candidates = []
    if tools_dir is not None:
        candidates.append(Path(tools_dir) / 'fonts/DejaVuSansMono.ttf')
    if host_name() == 'linux':
        candidates.append(Path('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'))
    for path in candidates:
        if path.is_file():
            return path.resolve()
    raise ValueError('Supply --fallback-font with DejaVuSansMono.ttf, place it in '
                     '--tools-dir/fonts, or install fonts-dejavu-core on Linux')


def translate_path(value, cygpath='cygpath', style='unix'):
    """Translate one path at a Windows/MSYS2 boundary; never invoke a shell."""
    flags = {'unix': '-u', 'windows': '-w', 'mixed': '-m'}
    if style not in flags:
        raise ValueError('Unknown path style: ' + style)
    program = find_executable(cygpath)
    if not program:
        raise ValueError('MSYS2 cygpath not found; select its executable with --cygpath')
    result = subprocess.run([program, flags[style], '--', str(value)],
                            stdin=subprocess.DEVNULL, capture_output=True,
                            text=True, check=True, timeout=10)
    path = result.stdout.rstrip('\r\n')
    if not path or '\n' in path or '\r' in path or '\0' in path:
        raise ValueError('cygpath did not return a single path')
    return path


def setup_plan(args):
    """Describe selected tools without installing, downloading or running them."""
    from install_dependencies import PYTHON_PACKAGES
    directory = args.tools_dir.expanduser().resolve()
    sdk = args.sdk.expanduser().resolve() if args.sdk else directory / 'sdk'
    maps = args.quake_tools.expanduser().resolve() if args.quake_tools else directory / 'ericw/bin'
    values = {'make': 'make', 'sh': 'sh', 'cygpath': 'cygpath',
              'm68k-amigaos-gcc': sdk / 'bin/m68k-amigaos-gcc',
              'vasmm68k_mot': args.vasm or sdk / 'bin/vasmm68k_mot',
              'qcc': args.qcc or directory / 'Quake-Tools/qcc-host',
              'ffmpeg': args.ffmpeg,
              **{name: maps / name for name in ('qbsp', 'vis', 'light')}}
    python = venv_python(directory / 'venv')
    try:
        font = str(fallback_font(getattr(args, 'fallback_font', None), directory))
        font_error = None
    except ValueError as exc:
        font, font_error = None, str(exc)
    windows = host_name() == 'windows'
    return {'host': host_name(), 'mode': 'read-only inventory; no tools executed',
            'validation': 'Windows full build untested' if windows else 'Inventory is not a build result',
            'python': sys.executable, 'python_platform': sysconfig.get_platform(),
            'venv_python': str(python), 'venv_present': python.is_file(),
            'python_requirements': list(PYTHON_PACKAGES),
            'native_tools': {name: {'selected': str(value), 'found': find_executable(value)}
                             for name, value in values.items()},
            'ndk_present': (sdk / 'm68k-amigaos/ndk-include/exec/exec_lib.i').is_file(),
            'fallback_font': font, 'fallback_font_issue': font_error,
            'automatic_setup': 'use setup-windows.cmd -Yes; -Plan previews and -Offline reuses cached tools'
                               if windows else 'Ubuntu/Debian setup via --autoinstall',
            'next_step': 'docs/WINDOWS_BUILD_ROADMAP.md' if windows else 'docs/LINUX_BUILD.md'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Translate one Windows/MSYS2 filesystem path')
    parser.add_argument('path')
    parser.add_argument('--cygpath', default='cygpath')
    parser.add_argument('--style', choices=('unix', 'windows', 'mixed'), default='unix')
    args = parser.parse_args()
    try:
        print(translate_path(args.path, args.cygpath, args.style))
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.exit(1, str(exc) + '\n')
