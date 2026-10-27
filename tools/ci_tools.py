#!/usr/bin/env python3
"""The bootstrapped public tools of the hosted CI: their cache key, and a manifest that proves a restored copy.

The CI bootstraps every public tool from nothing with
``tools/build.py --autoinstall --install-dependencies --yes --tools-dir DIR``
and keeps DIR between runs. A kept copy may stand in for a fresh bootstrap only
when nothing the installer reads has changed, so the key is a hash of:

- the installer's own code: the import closure of its modules (setup_build,
  install_dependencies, fetch_toolchain, fetch_native), found by reading their
  import statements, so a new module it starts to use joins the key by itself;
  the pinned versions and download lists (SDK, map tools, QuakeC source, the
  Python packages and the host packages) are constants in those modules;
- this file;
- the runner: operating system image and version, machine, and the version of
  the distribution Python the tool environment is created from.

``record DIR`` writes the manifest of a finished bootstrap (every file's
SHA-256, size and executable bit, every link target) into DIR; ``verify DIR``
checks a restored copy against it, file by file, and fails on any difference.

    python tools/ci_tools.py key
    python tools/ci_tools.py inputs
    python tools/ci_tools.py record DIR
    python tools/ci_tools.py verify DIR
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
# src first: the installer's modules put src in front of sys.path (src/mwad is the package; tools/mwad.py is a
# command-line wrapper of the same name).
SEARCH = (ROOT / 'src', ROOT / 'tools')
# The modules build.py hands the setup to (--autoinstall --install-dependencies); build.py itself only
# dispatches to them, and is left out so that every builder change does not throw the tools away.
ENTRY = ('setup_build', 'install_dependencies', 'fetch_toolchain', 'fetch_native')
# Imports of the installer that only check a finished tool and add nothing to the tools directory. They stay out of
# the key: build_aga is the image builder, and keying on it would throw the tools away on nearly every commit.
CHECK_ONLY = {
    'build_aga': 'fetch_native runs build_aga.check_quakec after building qcc from its pinned sources: a test compile '
                 'of our QuakeC in a temporary directory; the suite compiles the same sources with that qcc again',
}
MANIFEST = 'amiwind-tools-manifest.json'
HOST_PYTHON = '/usr/bin/python3'


def module_file(name, search=SEARCH):
    """The repository file of a dotted module name (tools/ or src/), or None for anything else."""
    parts = name.split('.')
    for base in search:
        for candidate in (base.joinpath(*parts).with_suffix('.py'), base.joinpath(*parts, '__init__.py')):
            if candidate.is_file():
                return candidate
    return None


def _imported_names(path, search=SEARCH):
    """Dotted names a module may import: import statements anywhere in it, and __import__ /
    importlib.import_module calls with a constant name."""
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    package = None
    for base in search:
        if base in path.parents:
            package = path.relative_to(base).with_suffix('').parts[:-1]  # a/b.py and a/__init__.py: package a
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                anchor = list(package or ())[:len(package or ()) - (node.level - 1)]
                base = '.'.join(anchor + ([node.module] if node.module else []))
            else:
                base = node.module or ''
            if base:
                names.append(base)
                names += [base + '.' + alias.name for alias in node.names if alias.name != '*']
        elif isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant) \
                and isinstance(node.args[0].value, str):
            func = node.func
            called = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ''
            if called in ('__import__', 'import_module'):
                names.append(node.args[0].value)
    return names


def inputs(root=ROOT, entry=ENTRY):
    """Sorted repository paths (POSIX, relative) of the installer's import closure and this file."""
    root = Path(root)
    search = (root / 'src', root / 'tools')
    found, todo = set(), list(entry)
    while todo:
        name = todo.pop()
        parts = name.split('.')
        if parts[0] in CHECK_ONLY:
            continue
        # A dotted import runs every package __init__ on the way.
        for depth in range(1, len(parts) + 1):
            path = module_file('.'.join(parts[:depth]), search)
            if path is not None and path not in found:
                found.add(path)
                todo += _imported_names(path, search)
    if (root / 'tools/ci_tools.py').is_file():
        found.add(root / 'tools/ci_tools.py')
    return sorted(p.relative_to(root).as_posix() for p in found)


def inputs_digest(root=ROOT, entry=ENTRY):
    """SHA-256 over the inputs' names and contents (line endings as in a Linux checkout)."""
    digest = hashlib.sha256()
    for name in inputs(root, entry):
        data = (Path(root) / name).read_bytes().replace(b'\r\n', b'\n')
        digest.update(name.encode() + b'\0' + hashlib.sha256(data).hexdigest().encode() + b'\n')
    return digest.hexdigest()


def host_python_version():
    try:
        return subprocess.run([HOST_PYTHON, '-c', 'import sys; print("%d.%d.%d" % sys.version_info[:3])'],
                              capture_output=True, text=True, timeout=30, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return 'none'


def key():
    runner = '-'.join(os.environ.get(name) or 'local' for name in ('ImageOS', 'ImageVersion'))
    return 'amiwind-tools-%s-%s-py%s-%s' % (runner, platform.machine() or 'unknown', host_python_version(),
                                            inputs_digest()[:24])


def manifest(directory):
    """{relative path: entry} of every file, link and directory under DIR (the manifest itself left out)."""
    directory = Path(directory)
    entries = {}
    for current, dirs, files in os.walk(directory, followlinks=False):
        dirs.sort()
        here = Path(current)
        for name in sorted(dirs + files):
            path = here / name
            rel = path.relative_to(directory).as_posix()
            if rel == MANIFEST:
                continue
            if path.is_symlink():
                entries[rel] = {'link': os.readlink(path)}
            elif path.is_dir():
                entries[rel] = {'dir': True}
            else:
                digest = hashlib.sha256()
                with path.open('rb') as stream:
                    for block in iter(lambda: stream.read(1 << 20), b''):
                        digest.update(block)
                entries[rel] = {'sha256': digest.hexdigest(), 'size': path.stat().st_size,
                                'exec': os.access(path, os.X_OK)}
    return entries


def record(directory):
    entries = manifest(directory)
    text = json.dumps({'key': key(), 'entries': entries}, indent=0, sort_keys=True) + '\n'
    (Path(directory) / MANIFEST).write_text(text, encoding='utf-8', newline='\n')
    files = sum(1 for e in entries.values() if 'sha256' in e)
    print('Recorded %d files, %d bytes, in %s' % (files, sum(e.get('size', 0) for e in entries.values()),
                                                  Path(directory) / MANIFEST))
    return 0


def verify(directory):
    path = Path(directory) / MANIFEST
    if not path.is_file():
        print('NOT A RECORDED BOOTSTRAP: %s is missing' % path)
        return 1
    stored = json.loads(path.read_text(encoding='utf-8'))
    problems = []
    if stored.get('key') != key():
        # The jobs of one run restore the tools job's key; a runner image rolled out between two jobs of one
        # run gives this job another key. The files are still checked one by one below.
        print('Note: recorded under key %s; this runner computes %s' % (stored.get('key'), key()))
    now, then = manifest(directory), stored['entries']
    for rel in sorted(set(now) | set(then)):
        if now.get(rel) != then.get(rel):
            problems.append('%s: recorded %s, found %s' % (rel, then.get(rel, 'nothing'), now.get(rel, 'nothing')))
    if problems:
        print('The restored tools differ from their bootstrap (%d differences):' % len(problems))
        for line in problems[:40]:
            print('  ' + line)
        return 1
    print('The restored tools match their bootstrap: %d entries, key %s' % (len(now), stored['key']))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('key', help='print the cache key')
    sub.add_parser('inputs', help='print the repository files the key hashes')
    for name in ('record', 'verify'):
        sub.add_parser(name).add_argument('directory', type=Path)
    args = parser.parse_args(argv)
    if args.command == 'key':
        print(key())
    elif args.command == 'inputs':
        print('\n'.join(inputs()))
    elif args.command == 'record':
        return record(args.directory)
    else:
        return verify(args.directory)
    return 0


if __name__ == '__main__':
    sys.exit(main())
