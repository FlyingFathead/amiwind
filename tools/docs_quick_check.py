#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Docs quick check: the documentation checks of the full test suite that a docs change can break, run in seconds
on just the changed files, before a commit or a gate.

Usage:
  docs_quick_check.py                  check the working tree's changes against HEAD (staged, unstaged and
                                       untracked files); with no changes, the files of the last commit
  docs_quick_check.py --staged         only the staged files (what the pre-commit hook uses)
  docs_quick_check.py --last-commit    the files of the last commit
  docs_quick_check.py --files F [F...] the named files (paths relative to the repository root)
  docs_quick_check.py install-hook [--force]
                                       install a git pre-commit hook that runs --staged (optional, local only;
                                       skip it once with git commit --no-verify)

Checks, each only when a file it covers changed:
  whitespace     CR bytes and trailing whitespace in the changed text files (the gate preflight rule)
  doc-toc        tools/doc_toc.py check: contents lists and #anchor links of the public documents
                 (when any Markdown file changed: a renamed heading can break a link in another document)
  debug-help     tests/test_debug_help_coverage.py: every dbg command the docs or the engine name has a
                 debug help row (when docs/, config/debug-commands.txt or engine sources changed)
  console-page   tests/test_console_commands_doc.py: the generated console command page is current
                 (when config/debug-commands.txt or the page changed)
  register       tools/bug_register.py check: the bug register and its generated parts are in sync
                 (when docs/bugs/, docs/BUGS.md or docs/BUG_JOURNAL.md changed)

The checks read the files on disk. Exit 0 when every check that ran passed (or none applied), 1 when one failed,
2 on a usage error. It never replaces the gate: the full suite still runs there.
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_EXT = {'.py', '.c', '.h', '.md', '.json', '.sh', '.ps1', '.yml', '.yaml', '.txt', '.cfg', '.qc'}
HOOK_MARK = '# docs quick check hook (tools/docs_quick_check.py install-hook)'
HOOK = """#!/bin/sh
%s
# Runs the documentation checks on the staged files in seconds. Skip it once with: git commit --no-verify
exec "${PYTHON:-python3}" tools/docs_quick_check.py --staged
""" % HOOK_MARK


def git(*args):
    return subprocess.run(['git', '-C', str(ROOT)] + list(args), capture_output=True, text=True, encoding='utf-8',
                          errors='replace')


def git_lines(*args):
    result = git(*args)
    if result.returncode != 0:
        raise SystemExit('docs quick check: git %s failed: %s' % (' '.join(args), result.stderr.strip()))
    return [line for line in result.stdout.splitlines() if line.strip()]


def changed_files(mode, files):
    """(description, sorted repository-relative paths)."""
    if mode == 'files':
        return 'named files', sorted(set(Path(f).as_posix() for f in files))
    if mode == 'staged':
        return 'staged files', sorted(set(git_lines('diff', '--cached', '--name-only', '--diff-filter=ACMR')))
    if mode == 'working':
        names = set(git_lines('diff', '--name-only', '--diff-filter=ACMR', 'HEAD'))
        names |= set(git_lines('ls-files', '--others', '--exclude-standard'))
        if names:
            return 'working-tree changes', sorted(names)
    return 'last commit', sorted(set(git_lines('diff-tree', '--no-commit-id', '--name-only', '-r', '--diff-filter=ACMR',
                                               'HEAD')))


def whitespace_problems(paths, root=ROOT):
    problems = []
    for name in paths:
        path = Path(root) / name
        if Path(name).suffix.lower() not in TEXT_EXT or not path.is_file():
            continue
        raw = path.read_bytes()
        if b'\r' in raw:
            problems.append('%s: CR bytes (convert to LF)' % name)
        for number, line in enumerate(raw.split(b'\n'), 1):
            if line.endswith((b' ', b'\t')):
                problems.append('%s:%d: trailing whitespace' % (name, number))
    return problems


def plan(paths):
    """The checks that apply to these paths: [(name, why)]."""
    def any_of(test):
        return [p for p in paths if test(p)]
    out = []
    text = any_of(lambda p: Path(p).suffix.lower() in TEXT_EXT)
    if text:
        out.append(('whitespace', '%d text file(s)' % len(text)))
    md = any_of(lambda p: p.endswith('.md'))
    if md:
        out.append(('doc-toc', '%d Markdown file(s)' % len(md)))
    dbg = any_of(lambda p: (p.startswith('docs/') and p.endswith('.md')) or p == 'config/debug-commands.txt'
                 or (p.startswith('engine/') and p.endswith('.c')) or p == 'tools/console_commands_doc.py')
    if dbg:
        out.append(('debug-help', '%d file(s) that can name dbg commands' % len(dbg)))
    page = any_of(lambda p: p in ('config/debug-commands.txt', 'docs/AMIWIND_CONSOLE_COMMANDS.md',
                                  'tools/console_commands_doc.py'))
    if page:
        out.append(('console-page', 'the command catalogue or its page'))
    reg = any_of(lambda p: p.startswith('docs/bugs/') or p in ('docs/BUGS.md', 'docs/BUG_JOURNAL.md',
                                                                 'tools/bug_register.py'))
    if reg:
        out.append(('register', '%d register file(s)' % len(reg)))
    return out


def run_tool(args):
    result = subprocess.run([sys.executable] + args, cwd=str(ROOT), capture_output=True, text=True, encoding='utf-8',
                            errors='replace')
    return result.returncode, (result.stdout + result.stderr).strip()


def run_check(name, paths):
    """(ok, output text)."""
    if name == 'whitespace':
        problems = whitespace_problems(paths)
        return not problems, '\n'.join(problems[:60]) or 'no CR bytes, no trailing whitespace'
    if name == 'doc-toc':
        code, out = run_tool([str(ROOT / 'tools' / 'doc_toc.py'), 'check'])
        return code == 0, out
    if name == 'debug-help':
        code, out = run_tool(['-m', 'unittest', 'tests.test_debug_help_coverage'])
        return code == 0, out
    if name == 'console-page':
        code, out = run_tool(['-m', 'unittest', 'tests.test_console_commands_doc'])
        return code == 0, out
    if name == 'register':
        code, out = run_tool([str(ROOT / 'tools' / 'bug_register.py'), 'check'])
        return code == 0, out
    raise ValueError(name)


def install_hook(force):
    hooks = git_lines('rev-parse', '--git-path', 'hooks')[0]
    hooks = Path(hooks) if Path(hooks).is_absolute() else ROOT / hooks
    hook = hooks / 'pre-commit'
    if hook.exists() and HOOK_MARK not in hook.read_text(encoding='utf-8', errors='replace') and not force:
        print('docs quick check: %s exists and is not this hook; nothing was changed (--force replaces it)' % hook)
        return 1
    hooks.mkdir(parents=True, exist_ok=True)
    hook.write_text(HOOK, encoding='utf-8', newline='\n')
    hook.chmod(0o755)
    print('docs quick check: pre-commit hook installed: %s (remove the file to uninstall)' % hook)
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv and argv[0] == 'install-hook':
        if any(a not in ('--force',) for a in argv[1:]):
            print(__doc__, file=sys.stderr)
            return 2
        return install_hook('--force' in argv[1:])
    mode, files = 'working', []
    if argv[:1] == ['--staged'] and len(argv) == 1:
        mode = 'staged'
    elif argv[:1] == ['--last-commit'] and len(argv) == 1:
        mode = 'last'
    elif argv[:1] == ['--files'] and len(argv) > 1:
        mode, files = 'files', argv[1:]
    elif argv:
        print(__doc__, file=sys.stderr)
        return 2
    t0 = time.time()
    what, paths = changed_files(mode, files)
    checks = plan(paths)
    print('docs quick check: %s: %d file(s); checks: %s' % (what, len(paths), ', '.join(n for n, _ in checks) or 'none'),
          flush=True)
    failed = []
    for name, why in checks:
        t = time.time()
        ok, out = run_check(name, paths)
        print('%s %s (%s; %.1f s)' % ('PASS' if ok else 'FAIL', name, why, time.time() - t), flush=True)
        if not ok:
            failed.append(name)
            for line in out.splitlines()[-40:]:
                print('    ' + line)
    print('docs quick check: %s (%d check(s) run, %.1f s)%s' % (
        'FAIL: ' + ', '.join(failed) if failed else 'PASS', len(checks), time.time() - t0,
        '; fix these before the commit or the gate' if failed else ''))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
