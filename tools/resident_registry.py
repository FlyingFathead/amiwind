#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Resident registries of the engine: what every console command, console variable and large static name table
costs in memory for the whole session (ENGINE-RESIDENT-REGISTRY-GROWTH-36).

Quake keeps these for the whole game. Each console command (Cmd_AddCommand, cmd.c) is a cmd_function_t on the
low hunk: 12 bytes rounded up to 16, plus the 16-byte hunk header (zone.c Hunk_AllocName) = 32 bytes. Each
console variable (Cvar_RegisterVariable, cvar.c) is a cvar_t in the engine's data (6 fields of 4 bytes = 24
bytes) plus a copy of its default string on the zone (Z_Malloc: length + 1, the 24-byte memblock_t header and the
4-byte trash marker, rounded up to 8; zone.c Z_TagMalloc). Static tables of names (top-level initialised arrays
of string literals) of 1 KiB or more are listed too: they are in the binary for the whole session.

The engine sources are read as text: the files of engine/aga/Makefile's SRCS, comments and `#if 0` blocks left
out. tests/test_resident_registry.py compares the totals with tests/resident_registry_budget.json (a ratchet:
the numbers may go down freely; going up needs the budget raised in the same change with the owner's reason).
New debug commands go into the on-disk dbg command catalogue (aw_console.c, AWDC1) instead of new registrations.

  python3 tools/resident_registry.py [--json]
"""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'engine' / 'aga'
BUDGET = ROOT / 'tests' / 'resident_registry_budget.json'

POINTER = 4                      # 68k: pointers, int, qboolean, float are 4 bytes
HUNK_HEADER = 16                 # zone.c hunk_t: sentinal, size, name[8]
CMD_STRUCT = 3 * POINTER         # cmd.c cmd_function_t: next, name, function
CVAR_STRUCT = 6 * POINTER        # cvar.h cvar_t: name, string, archive, server, value, next
ZONE_HEADER = 24                 # zone.c memblock_t: size, tag, id, next, prev, pad
ZONE_TRASH = 4                   # zone.c Z_TagMalloc: the ZONEID marker at the block end
TABLE_MIN = 1024                 # static name tables listed from this size


def command_bytes():
    """Low-hunk bytes of one console command."""
    return HUNK_HEADER + ((CMD_STRUCT + 15) & ~15)


def zone_bytes(text):
    """Zone bytes of a Z_Malloc'd copy of TEXT (a cvar's default string)."""
    return (len(text.encode('latin-1')) + 1 + ZONE_HEADER + ZONE_TRASH + 7) & ~7


def sources(engine=ENGINE):
    """The engine's compiled C files: engine/aga/Makefile SRCS (and the lists it adds), relative to src/."""
    text = (engine / 'Makefile').read_text(encoding='utf-8').replace('\\\n', ' ')
    names = []
    for match in re.finditer(r'^(\w*SRCS)\s*\+?=\s*(.*)$', text, re.M):
        names += [word for word in match.group(2).split() if word.endswith('.c')]
    return sorted(set(names))


def strip(text):
    """C text without comments and `#if 0` blocks (string literals kept)."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == '"' or c == "'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == '\\' else 1
            out.append(text[i:j + 1])
            i = j + 1
        elif text.startswith('/*', i):
            j = text.find('*/', i + 2)
            i = n if j < 0 else j + 2
            out.append(' ')
        elif text.startswith('//', i):
            j = text.find('\n', i)
            i = n if j < 0 else j
        else:
            out.append(c)
            i += 1
    lines, kept, depth = ''.join(out).split('\n'), [], 0
    for line in lines:
        directive = line.strip()
        if depth:
            if re.match(r'#\s*if', directive):
                depth += 1
            elif re.match(r'#\s*endif', directive):
                depth -= 1
            elif depth == 1 and re.match(r'#\s*(else|elif)', directive):
                depth = 0
            kept.append('')
            continue
        if re.match(r'#\s*if\s+0\b', directive):
            depth = 1
            kept.append('')
            continue
        kept.append(line)
    return '\n'.join(kept)


def literal(text):
    """The value of a C string literal body (simple escapes)."""
    return re.sub(r'\\(.)', lambda m: {'n': '\n', 't': '\t', '0': '\0'}.get(m.group(1), m.group(1)), text)


def scan(engine=ENGINE):
    """{'commands': [...], 'cvars': [...], 'tables': [...], 'problems': [...]}: every registration in the
    compiled engine sources, with its file and resident bytes."""
    src = engine / 'src'
    commands, cvars, tables, problems = {}, {}, [], []
    texts, local, shared = {}, {}, {}
    # String macros used as cvar defaults (aw_lava.h: #define AW_LAVA_DEFAULT_TINT "128 4 4").
    macros = {}
    for header in sorted(src.rglob('*.[ch]')):
        for macro, value in re.findall(r'^[ \t]*#\s*define\s+(\w+)\s+("(?:[^"\\]|\\.)*")',
                                       header.read_text(encoding='latin-1'), re.M):
            macros.setdefault(macro, value)
    for name in sources(engine):
        path = src / name
        if not path.is_file():
            problems.append(f'{name}: listed in the Makefile but missing')
            continue
        raw = path.read_text(encoding='latin-1')
        # Included .inc files are part of the file that includes them (model.c: model_alias_stream.inc).
        raw = re.sub(r'^[ \t]*#\s*include\s+"([\w./-]+\.inc)"',
                     lambda m: (src / m.group(1)).read_text(encoding='latin-1') if (src / m.group(1)).is_file()
                     else m.group(0), raw, flags=re.M)
        texts[name] = text = strip(raw)
        for statement in re.finditer(r'(\bstatic\s+)?\bcvar_t\b([^;(]*);', text):
            for var, cvar_name, default in re.findall(r'(\w+)\s*=\s*\{\s*"((?:[^"\\]|\\.)*)"\s*,\s*'
                                                      r'("(?:[^"\\]|\\.)*"|\w+)', statement.group(2)):
                if not default.startswith('"'):
                    if default not in macros:
                        problems.append(f'{name}: cvar {cvar_name}: default {default} is not a string macro')
                        continue
                    default = macros[default]
                value = (literal(cvar_name), literal(default[1:-1]))
                local.setdefault(name, {})[var] = value
                if not statement.group(1):
                    shared[var] = value  # declared extern where it is registered
    for name, text in texts.items():
        defaults = dict(shared, **local.get(name, {}))
        for call in re.finditer(r'\bCmd_AddCommand\s*\(\s*([^,]*),', text):
            argument = call.group(1).strip()
            if name == 'cmd.c' and argument.startswith('char'):
                continue  # the definition
            found = re.fullmatch(r'"((?:[^"\\]|\\.)*)"', argument)
            if not found:
                problems.append(f'{name}: Cmd_AddCommand with a name that is not a literal: {argument}')
                continue
            commands.setdefault(literal(found.group(1)), name)
        for call in re.finditer(r'\bCvar_RegisterVariable\s*\(\s*([^)]*)\)', text):
            argument = call.group(1).strip()
            if name == 'cvar.c' and argument.startswith('cvar_t'):
                continue  # the definition
            found = re.fullmatch(r'&\s*(\w+)', argument)
            if not found or found.group(1) not in defaults:
                problems.append(f'{name}: Cvar_RegisterVariable({argument}): no cvar_t definition with a literal '
                                'name and default in the same file')
                continue
            cvar_name, default = defaults[found.group(1)]
            cost = CVAR_STRUCT + zone_bytes(default)
            if cvar_name not in cvars or cvars[cvar_name]['bytes'] < cost:
                cvars[cvar_name] = {'name': cvar_name, 'file': name, 'default': default,
                                    'static_bytes': CVAR_STRUCT, 'zone_bytes': zone_bytes(default), 'bytes': cost}
        for table in re.finditer(r'^[ \t]*(?:static\s+)?(?:const\s+)?[\w\s\*]*?\b(\w+)\s*\[[^\]]*\]\s*=\s*\{', text,
                                 re.M):
            depth, j = 1, table.end()
            while j < len(text) and depth:
                depth += {'{': 1, '}': -1}.get(text[j], 0) if text[j] not in '"\'' else 0
                if text[j] == '"':
                    k = j + 1
                    while k < len(text) and text[k] != '"':
                        k += 2 if text[k] == '\\' else 1
                    j = k
                j += 1
            body = text[table.end():j - 1]
            strings = [literal(s) for s in re.findall(r'"((?:[^"\\]|\\.)*)"', body)]
            size = sum(len(s.encode('latin-1')) + 1 for s in strings)
            if size >= TABLE_MIN:
                tables.append({'name': table.group(1), 'file': name, 'strings': len(strings), 'bytes': size})
    rows = [{'name': key, 'file': value, 'bytes': command_bytes()} for key, value in sorted(commands.items())]
    return {'commands': rows, 'cvars': [cvars[key] for key in sorted(cvars)],
            'tables': sorted(tables, key=lambda t: (t['file'], t['name'])), 'problems': problems}


def totals(found):
    """The budgeted numbers of a scan."""
    return {'commands': {'count': len(found['commands']), 'hunk_bytes': sum(r['bytes'] for r in found['commands'])},
            'cvars': {'count': len(found['cvars']), 'static_bytes': sum(r['static_bytes'] for r in found['cvars']),
                      'zone_bytes': sum(r['zone_bytes'] for r in found['cvars'])},
            'tables': {'count': len(found['tables']), 'bytes': sum(r['bytes'] for r in found['tables'])}}


def over_budget(found, budget):
    """Messages for every budgeted number above BUDGET, naming the entries the budget does not know."""
    now, limit, messages = totals(found), budget['totals'], []
    known = budget.get('entries', {})
    for group, fields in now.items():
        for field, value in fields.items():
            allowed = limit.get(group, {}).get(field)
            if allowed is None or value > allowed:
                new = [row['name'] for row in found[group] if row['name'] not in known.get(group, [])]
                messages.append(f'{group} {field}: {value} > budget {allowed}'
                                + (f'; new: {", ".join(new[:20])}' if new else ''))
    return messages


ADVICE = ('Route new debug commands through the on-disk dbg command catalogue (engine/aga/src/aw_console.c, AWDC1) '
          'instead of Cmd_AddCommand/Cvar_RegisterVariable, or raise the budget in the same commit with the '
          "owner-approved reason (tools/resident_registry.py --raise-budget 'YYYY-MM-DD: reason').")


def load_budget(path=BUDGET):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def budget_document(found, reasons):
    return {'format': 'AmiWind resident registry budget 1',
            'note': 'Ratchet: tests/test_resident_registry.py fails above these numbers and asks for them to be '
                    'lowered when the engine needs less. Raise only with a dated, owner-approved reason.',
            'totals': totals(found), 'reasons': reasons,
            'entries': {group: [row['name'] for row in found[group]] for group in ('commands', 'cvars', 'tables')}}


def write_budget(document, path=BUDGET):
    Path(path).write_text(json.dumps(document, indent=1) + '\n', encoding='utf-8', newline='\n')


def update_budget(found, budget, reason=None):
    """The new budget document: the current numbers. Without REASON only a lowering (nothing above BUDGET);
    with REASON (a dated, owner-approved line) a raise, the reason appended."""
    if over_budget(found, budget) and not reason:
        raise ValueError('above the budget: raising needs a reason (--raise-budget)')
    reasons = list(budget.get('reasons', []))
    if reason:
        reasons.append(reason)
    return budget_document(found, reasons)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--json', action='store_true', help='print every entry as JSON')
    parser.add_argument('--lower-budget', action='store_true',
                        help='write the current numbers to the budget (only when none is above it)')
    parser.add_argument('--raise-budget', metavar='REASON',
                        help="write the current numbers with a dated, owner-approved reason ('YYYY-MM-DD: why')")
    args = parser.parse_args(argv)
    found = scan()
    if args.lower_budget or args.raise_budget:
        if found['problems']:
            print('\n'.join('problem: ' + p for p in found['problems']))
            return 1
        try:
            document = update_budget(found, load_budget(), args.raise_budget)
        except ValueError as exc:
            print('Error: ' + str(exc), file=sys.stderr)
            return 1
        write_budget(document)
        print(json.dumps(document['totals'], indent=1))
        return 0
    if args.json:
        print(json.dumps(dict(found, totals=totals(found)), indent=1))
    else:
        print(json.dumps(totals(found), indent=1))
        for problem in found['problems']:
            print('problem: ' + problem)
        for table in found['tables']:
            print(f"table {table['file']}:{table['name']}: {table['strings']} strings, {table['bytes']} bytes")
    return 1 if found['problems'] else 0


if __name__ == '__main__':
    sys.exit(main())
