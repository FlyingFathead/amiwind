# SPDX-License-Identifier: GPL-3.0-only
"""Every dbg command the game tells the player about is in the debug help (project rule, 2026-10-10: "always update
our debug help").

The dbg layer is one table: config/debug-commands.txt (AWDC1). The engine's `dbg` / `debug` dispatcher
(aw_console.c AW_DebugTranslate) routes only through it, the in-game `dbg help` lists it row by row, and
docs/AMIWIND_CONSOLE_COMMANDS.md is generated from it (tests/test_console_commands_doc.py). So a dbg subcommand or
alias exists for the player exactly when it has a row, and every row is in the help and on the page.

This test closes the other direction island-wide: every `dbg <word>` / `debug <word>` the engine prints (usage
lines, notices, menus), the F1 quick help and the public docs mention must reach a catalogue row, and every row's
handler must be registered. A failure names each missing command and where it is mentioned."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
sys.path.insert(0, str(ROOT / 'tools'))
import console_commands_doc as doc  # noqa: E402

LITERAL = re.compile(r'"((?:[^"\\\n]|\\.)*)"')
MENTION = re.compile(r'(?<![\w-])(?:dbg|debug) ([a-z][a-z0-9]*)(?: ([a-z][a-z0-9]*))?(?: ([a-z][a-z0-9]*))?')
DOC_MENTION = re.compile(r'`(?:dbg|debug)\s+([a-z][a-z0-9]*)(?:[ \n]([a-z][a-z0-9]*))?(?:[ \n]([a-z][a-z0-9]*))?')
# Lines that describe a command still to be made, not one the game has.
FUTURE = ('propos', 'planned', '- [ ]', 'intended', 'TODO')
# Words after "dbg"/"debug" in prose that are not commands ("debug help" is the help itself; "debug only",
# "debug build", "debug overlay" ... describe things).
NOT_COMMANDS = {'help', 'only', 'build', 'builds', 'mode', 'overlays', 'overlay', 'flag', 'flags', 'way', 'use',
                'commands', 'command', 'image', 'images', 'text', 'output', 'logs', 'log', 'line', 'lines',
                'hud', 'information', 'info', 'data', 'map', 'maps', 'is', 'and', 'or', 'the', 'a', 'to', 'in',
                'prefix', 'console', 'list', 'session', 'catalogue', 'tools', 'tool', 'option', 'options',
                'menu', 'teleport', 'run', 'runs', 'test', 'tests', 'version', 'versions', 'route', 'routes',
                'value', 'values', 'switch', 'switches', 'aliases', 'alias', 'name', 'names', 'word', 'words'}


def catalogue_words():
    return {w.lower() for _, w, _, _ in doc.entries(doc.CATALOGUE.read_text(encoding='utf-8'))}


def reaches(words, mention):
    """True when a catalogue row's words are the mention's first one, two or three words (the dispatcher matches
    the longest row; extra words are arguments)."""
    parts = [p for p in mention if p]
    return any(' '.join(parts[:n]) in words for n in range(1, len(parts) + 1))


def engine_mentions():
    out = {}
    for f in sorted(SRC.rglob('*.c')):
        text = f.read_text(encoding='latin-1')
        for literal in LITERAL.findall(text):
            for m in MENTION.finditer(literal):
                if m.group(1) in NOT_COMMANDS:
                    continue
                out.setdefault(m.groups(), set()).add(f.relative_to(SRC).as_posix())
    return out


def doc_mentions():
    out = {}
    for f in sorted((ROOT / 'docs').glob('*.md')):
        # the generated page itself; history kept as written (the changelog, the maintainer's dated journal and musings)
        if f.name == 'AMIWIND_CONSOLE_COMMANDS.md' or f.name == 'CHANGELOG.md' or f.name.startswith('HORSTATORS_'):
            continue
        text = f.read_text(encoding='utf-8')
        for m in DOC_MENTION.finditer(text):
            line = text[text.rfind('\n', 0, m.start()) + 1:text.find('\n', m.start())]
            if m.group(1) in NOT_COMMANDS or any(word.lower() in line.lower() for word in FUTURE):
                continue
            out.setdefault(m.groups(), set()).add('docs/' + f.name)
    return out


class DebugHelpCoverage(unittest.TestCase):
    def test_every_dbg_command_the_engine_prints_is_in_the_debug_help(self):
        words = catalogue_words()
        missing = {' '.join(p for p in k if p): sorted(v) for k, v in engine_mentions().items() if not reaches(words, k)}
        self.assertEqual(missing, {}, 'add a config/debug-commands.txt row (then tools/console_commands_doc.py '
                                      'sort + render) for each dbg command named here')

    def test_every_dbg_command_the_docs_name_is_in_the_debug_help(self):
        words = catalogue_words()
        missing = {' '.join(p for p in k if p): sorted(v) for k, v in doc_mentions().items() if not reaches(words, k)}
        self.assertEqual(missing, {}, 'add the catalogue row or correct the docs for each dbg command named here')

    def test_every_row_has_a_registered_handler_and_reaches_help_and_page(self):
        rows = doc.entries(doc.CATALOGUE.read_text(encoding='utf-8'))
        names = doc.registered_names(SRC)
        self.assertEqual(sorted({h for _, _, h, _ in rows if h not in names}), [])
        page = (ROOT / 'docs' / 'AMIWIND_CONSOLE_COMMANDS.md').read_text(encoding='utf-8')
        for _, w, _, _ in rows:
            self.assertIn('`dbg ' + w + '`', page, w)
        # the in-game help prints every row: AW_DebugTranslate's catalogue walk, no filter but availability notes
        console = (SRC / 'aw_console.c').read_text(encoding='utf-8')
        help_body = console[console.index('static void help(void)'):console.index('static void help_for')]
        self.assertIn('Con_Printf(" %s %s%s\\n",r.words,r.arguments,availability(omitted,&r));', help_body)

    def test_aliases_are_catalogue_rows_read_from_disk(self):
        """Project rule: aliases live as rows in the on-disk catalogue, read only when a dbg command is submitted;
        no resident alias table and no command registered per alias."""
        console = (SRC / 'aw_console.c').read_text(encoding='utf-8')
        translate = console[console.index('int AW_DebugTranslate('):console.index('static const char *availability')]
        self.assertIn('f=catalogue_open(&left,line);', translate)       # opened from disk on every submission
        self.assertIn('fclose(f);', translate)
        rows = doc.entries(doc.CATALOGUE.read_text(encoding='utf-8'))
        handlers = {}
        for _, w, h, _ in rows:
            handlers.setdefault(h, []).append(w)
        engine = ''.join(f.read_text(encoding='latin-1') for f in sorted(SRC.rglob('*.c')))
        for handler in ('aw_camera', 'aw_vanitycam'):
            self.assertGreaterEqual(len(handlers[handler]), 2, handler)   # one handler, its aliases as rows
            self.assertEqual(engine.count('Cmd_AddCommand("%s"' % handler), 1, handler)
        for alias in ('aw_vanitycamera', 'aw_pov', 'aw_thirdperson'):      # no command per alias
            self.assertFalse('Cmd_AddCommand("%s"' % alias in engine, alias)

    def test_the_view_commands(self):
        words = catalogue_words()
        for w in ('camera', 'pov', 'thirdperson', 'vanitycamera', 'vanitycam'):
            self.assertIn(w, words)


if __name__ == '__main__':
    unittest.main()
