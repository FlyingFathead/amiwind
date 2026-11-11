# SPDX-License-Identifier: GPL-3.0-only
"""Engine C files in the stage keys by what the builder reads of them (BUILD-STAGE-KEY-ENGINE-HEADERS-54).

The CHIM world stages reach builder checks that read the engine's C sources: limits read as single #define lines
(tools/engine_limits.py define(), the DEFINES table, map_engine_limits), the target ABI probe of
tools/check_world_map_heap.py (sizes of engine structures, compiled from quakedef.h and the headers it includes),
the zone walk gate (tools/chim/zone_sim.py compiles chim/chim_zone.c) and policies parsed from named files. Keyed as
whole files with their whole #include closure, every engine header edit re-keyed the CHIM world: a new function
prototype in quakedef.h (the actor record) or sound.h (S_MoveSound for magic) rebuilt about six hours of world that
reads neither. A stage key (build_cache.SourceIndex.selection, stage form) now counts an engine file by its use:

* named as text (read whole, parsed, hashed, compiled by name): the whole file, as before;
* named only in define() calls or the DEFINES table, or only in docstrings, or reached only through the #include
  closure of a named file or of the ABI probe's own #include lines: a header counts as its C facts, the
  declarations and macros the stage can reach (below); a .c or .inc file stays whole;
* named only for the probe's receipt (the SHA-256 lines compile_target_sizes writes and every stage caller but the
  map heap audit drops, RECEIPT_UNITS): left out, unless the reach writes that receipt (RECEIPT_WRITERS).

The C facts of a header: its top-level items (each #define / #undef, each declaration or definition up to its ';'
or its body's '}', with the #if conditions around it), kept when an item defines a name the stage reaches:
an identifier in a string constant of the stage's reached Python code (the define names, the probe's source), in
an engine C file the key counts whole, or in a kept item (transitively, its #if conditions included). A struct's
forward declaration ("struct x;") defines nothing. An item whose name cannot be told (a pragma, a macro used as a
declaration) is always kept. A header with nothing kept leaves the key. A kept macro that pastes tokens (##) names
what cannot be followed: the stage then keys its engine files whole. Any engine C file in the key that this reading
cannot explain (a folder named whole, a name this walk does not find) keeps every engine file whole.

Instrumentation (build_cache.INSTRUMENTATION_MODULES): it decides what a key counts, never what a stage computes.
Tested in tests/test_stage_engine_key.py."""
import ast
import hashlib
import json
import posixpath
import re

# The reading's versions (SourceIndex(engine_facts=N); a key value says which made it):
# 1 (2026-10-27, merged 87983fd1): headers by their facts, every .c and .inc file whole;
# 2 (BUILD-STAGE-KEY-ENGINE-C-WHOLE-54): a .c file read only for single definitions (define(), DEFINES,
#   cvar_default: chim/chim_world.c's cvar defaults, chim_statics.c's CHIM_MAX_STATICS) counts by its facts too, so a
#   diagnostic print in chim_world.c re-keys no CHIM world; a declaration whose string literal is a name the stage
#   reaches (a cvar's {"name", "value"}) defines that name.
# 3 (BUILD-ENGINE-SOURCE-KEY-BROAD-36, reopened 2026-11-03): the frame timing header (TIMING_HEADERS) counts only by
#   what can carry a layout. Its prototypes, extern counters, function-like timing macros and slot enums were kept
#   because a prototype shares its name with the host-test stub macro (the "macro used as a declaration" rule), the
#   chunk code names a slot and quakedef.h's disk wait wrappers call the macros: three timing edits of v0.0.59
#   re-keyed the CHIM world and its interiors. A struct, union, typedef or object-like macro there still counts, and a
#   timing item still counts when such a layout item names it.
# 4 (BUILD-ENGINE-SOURCE-KEY-BROAD-36, CHIM-KEYS-TOO-BROAD-62): an engine file named only in define() calls or the
#   DEFINES table (DEFINE_READ_FUNCTIONS_2), and included by nothing else the key counts, counts as the VALUES those
#   readers return (define_value: the first match of each reader's pattern for each name read), not as its C facts,
#   and its own #include lines leave the key. map_engine_limits reads one define (SLOTS) of aw_combat.c: the facts
#   kept every declaration whose name is an English word in a string of the reached code (slots, you, retry, cost,
#   music, rules, ...), so combat edits re-keyed the CHIM world, the three towns and the flora (about 2,700 s).
# 5 (CHIM-KEYS-TOO-BROAD-62, v0.0.64-dev4): a name found only as a word in a one-line string of the reached Python
#   code (a message, an option's help or choices) keeps only a header item that can carry a value the builder reads
#   as text (_word_value: an object-like #define, a struct, union, enum, typedef or a defined variable), never a
#   prototype, a function body, a function-like macro or an extern declaration: the words "free" and "mirror" kept
#   aw_tryalloc.h's free() wrapper and glquake.h's `extern qboolean mirror`, so an engine memory census edit and an
#   option's help text re-keyed the CHIM world (about 3.8 h). Names from compiled C (an engine file counted whole,
#   the ABI probe's C source) keep every item, as before, except a target-only item (_target_only: in an
#   `#if defined(AMIGA) && defined(__m68k__)` branch) that cannot carry a size: the host compiles (the zone walk
#   gate's chim_zone.c) never see it and the builder's one target compile, the ABI probe, reads only sizes; the
#   memory census added `#define free(block) AW_TryFree(block)` there. From this reading on, stage keys also leave the
#   default-off switches' code out (build_cache.DEFAULT_OFF_SWITCHES).
# A record made by an earlier version is compared through its own source tree (translate).
VERSION = 5
PREFIXES = {1: 'cfacts1:', 2: 'cfacts2:', 3: 'cfacts3:', 4: 'cfacts4:', 5: 'cfacts5:'}
# Version 4: the patterns of the define readers (engine_limits.define on the comment-free text, world_estimate._define,
# engine_limits._mib_define and cvar_default on the raw text); a define-only file counts as the first match of each
# for every name read (tests/test_stage_key_engine_defines.py checks each reader against them).
DEFINE_PATTERNS = {
    'define': ('stripped', r'^\s*#\s*define\s+%s\s+(\d+)\b', re.M),      # engine_limits.define, the DEFINES table
    '_define': ('raw', r'^\s*#\s*define\s+%s\s+(\d+)', re.M),             # world_estimate._define
    '_mib_define': ('raw', r'#\s*define\s+%s\s+\(\s*(\d+)UL\s*\*\s*CHIM_AUTO_MIB\s*\)', 0),
    'cvar_default': ('raw', r'\{\s*"%s"\s*,\s*"(-?\d+)"', 0),
}
DEFINES_TAG = 'defs:'
# Engine headers that only time frames (spike slots, wait counters, their macros): version 3 reads them by layout
TIMING_HEADERS = frozenset({'engine/aga/src/aw_spike.h'})
PREFIX = PREFIXES[VERSION]
C_SUFFIXES = ('.c', '.h', '.inc')
HEADER = '.h'
# Reader functions whose first argument is an engine file and second a literal name; each reads only that name's
# #define line (engine_limits.define and _mib_define, world_estimate._define) or its cvar initialiser (cvar_default,
# version 2). tests/test_stage_engine_key.py checks that every function of these names in tools/ is one of them and
# builds its pattern from the name.
DEFINE_READ_FUNCTIONS = frozenset({'define', '_define', '_mib_define'})
DEFINE_READ_FUNCTIONS_2 = DEFINE_READ_FUNCTIONS | {'cvar_default'}
# Tables of (file, NAME) pairs that only those readers consume (engine_limits.DEFINES).
DEFINE_TABLE_SUFFIX = 'DEFINES'
# Units whose digest() calls hash engine files only for a receipt: check_world_map_heap.compile_target_sizes returns
# (sizes, receipt), and only audit_world_maps writes the receipt (the map heap audit); every other caller takes [0].
RECEIPT_UNITS = frozenset({('tools/check_world_map_heap.py', 'compile_target_sizes')})
RECEIPT_WRITERS = frozenset({('tools/check_world_map_heap.py', 'audit_world_maps')})
RECEIPT_CALL = 'digest'
# Engine files the heap audits read only for their loader policy (BUILD-CHIM-HEAP-KEY-LOADER-63): named only in these
# modules (and not for a receipt the reach writes), such a file counts as its policy (tools/engine_loader_policy.py
# key_value), never whole. Named anywhere else, it counts as before.
POLICY_FILES = frozenset({'engine/aga/src/model.c'})
POLICY_MODULES = frozenset({'tools/check_world_map_heap.py', 'tools/alias_stream_heap.py', 'tools/edge_cache_heap.py',
                            'tools/sprite_heap.py', 'tools/engine_loader_policy.py'})
UPPER_NAME = re.compile(r'[A-Z][A-Z0-9_]*')
IDENTIFIER = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
INCLUDE_LINE = re.compile(r'^[ \t]*#[ \t]*include[ \t]*"([^"\n]+)"', re.M)
TOKEN = re.compile(r'"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|[A-Za-z_]\w*|\d[\w.]*|##|->|\S')
KEYWORDS = frozenset((
    'auto break case char const continue default do double else enum extern float for goto if inline int long '
    'register restrict return short signed sizeof static struct switch typedef union unsigned void volatile while '
    '_Bool __inline __inline__ __attribute__ __asm__ asm __extension__ __restrict').split())
TAGS = ('struct', 'union', 'enum')

_PARSED = {}       # header text -> items
_TREES = {}        # module text -> (tree, parents, unit of each node)


# --------------------------------------------------------------------------
# C headers as items

def strip_comments(text):
    """TEXT without /* */ and // comments (each replaced by a space; newlines kept), string literals untouched."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c in '"\'':
            j = i + 1
            while j < n and text[j] != c and text[j] != '\n':
                j += 2 if text[j] == '\\' else 1
            out.append(text[i:j + 1])
            i = j + 1
        elif text.startswith('/*', i):
            j = text.find('*/', i + 2)
            j = n if j < 0 else j + 2
            out.append(' ' + '\n' * text.count('\n', i, j))
            i = j
        elif text.startswith('//', i):
            j = text.find('\n', i)
            i = n if j < 0 else j
            out.append(' ')
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def _depths(tokens):
    """[(paren, brace, bracket) before each token]."""
    paren = brace = bracket = 0
    out = []
    for tok in tokens:
        out.append((paren, brace, bracket))
        if tok == '(':
            paren += 1
        elif tok == ')':
            paren -= 1
        elif tok == '{':
            brace += 1
        elif tok == '}':
            brace -= 1
        elif tok == '[':
            bracket += 1
        elif tok == ']':
            bracket -= 1
    return out


def _names(tokens):
    """(defined names, call name or None, forward) of one declaration's tokens (directive texts left out)."""
    seq = [t for t in tokens if not t.startswith('#')]
    if len(seq) == 3 and seq[0] in TAGS and IDENTIFIER.fullmatch(seq[1]) and seq[2] == ';':
        return set(), None, True
    depth = _depths(seq)
    names, call = set(), None
    for i, tok in enumerate(seq):
        if tok in TAGS and i + 2 < len(seq) and IDENTIFIER.fullmatch(seq[i + 1]) and seq[i + 2] == '{':
            names.add(seq[i + 1])
        if tok == 'enum':
            start = i + 1 if i + 1 < len(seq) and seq[i + 1] == '{' else i + 2
            if start < len(seq) and seq[start] == '{':
                level = depth[start][1] + 1
                for j in range(start + 1, len(seq)):
                    if depth[j][1] < level:
                        break
                    if depth[j][1] == level and IDENTIFIER.fullmatch(seq[j]) and seq[j - 1] in ('{', ','):
                        names.add(seq[j])
    typedef = seq[:1] == ['typedef']
    for i, tok in enumerate(seq):
        if not IDENTIFIER.fullmatch(tok) or tok in KEYWORDS:
            continue
        paren, brace, bracket = depth[i]
        if brace or bracket:
            continue
        after = seq[i + 1] if i + 1 < len(seq) else None
        before = seq[i - 1] if i else None
        if paren == 0 and after in (';', ',', '[', '=') and before not in TAGS:
            names.add(tok)
        elif paren == 1 and after == ')' and before == '*' and i >= 2 and seq[i - 2] == '(':
            names.add(tok)
        elif paren == 0 and after == '(':
            if typedef:
                names.add(tok)
            elif call is None:
                call = tok
                names.add(tok)
    return names, call, False


def parse_header(text, version=1):
    """The items of a C header: [{'stack', 'text', 'defines', 'uses', 'always', 'call', 'paste'}] in file order.
    Version 2: a declaration (not a function body) also defines each name its string literals spell."""
    if (text, version) in _PARSED:
        return _PARSED[(text, version)]
    lines = strip_comments(text).replace('\\\r\n', ' ').replace('\\\n', ' ').splitlines()
    items, stack, item = [], [], None

    def snapshot():
        return tuple(tuple(entry) for entry in stack)

    def finish(current, always=False):
        names, call, forward = _names(current['tokens'])
        if forward:
            return
        if version >= 2 and not current.get('function'):
            names |= {tok[1:-1] for tok in current['tokens'] if tok.startswith('"') and IDENTIFIER.fullmatch(tok[1:-1])}
        words = set()
        for tok in current['tokens']:
            words.update(IDENTIFIER.findall(tok) if tok.startswith('#') else
                         ([tok] if IDENTIFIER.fullmatch(tok) else []))
        items.append({'stack': current['stack'], 'text': ' '.join(current['tokens']), 'defines': frozenset(names),
                      'uses': frozenset(words - names), 'always': always or not names, 'call': call,
                      'paste': any('##' in tok for tok in current['tokens'] if tok.startswith('#')),
                      'body': bool(current.get('function'))})

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#'):
            match = re.match(r'#\s*(\w*)\s*(.*)', stripped)
            keyword, rest = match.group(1), match.group(2)
            norm = ('#' + keyword + ' ' + ' '.join(TOKEN.findall(rest))).strip()
            if item is not None:
                item['tokens'].append(norm)
            if keyword in ('if', 'ifdef', 'ifndef'):
                stack.append([norm])
            elif keyword in ('elif', 'else'):
                if stack:
                    stack[-1] = stack[-1] + [norm]
            elif keyword == 'endif':
                if stack:
                    stack.pop()
            elif item is None and keyword in ('define', 'undef'):
                name = IDENTIFIER.match(rest)
                body = rest[name.end():] if name else rest
                uses = set(IDENTIFIER.findall(body))
                for entry in stack:
                    for directive in entry:
                        uses.update(IDENTIFIER.findall(directive))
                items.append({'stack': snapshot(), 'text': norm,
                              'defines': frozenset([name.group(0)]) if name else frozenset(),
                              'uses': frozenset(uses), 'always': not name, 'call': None, 'paste': '##' in body,
                              'function_macro': bool(name) and body.startswith('(')})
            elif item is None and keyword not in ('include', 'include_next', 'import', ''):
                items.append({'stack': snapshot(), 'text': norm, 'defines': frozenset(),
                              'uses': frozenset(IDENTIFIER.findall(rest)), 'always': True, 'call': None,
                              'paste': False})
            continue
        for tok in TOKEN.findall(line):
            if item is None:
                item = {'stack': snapshot(), 'tokens': [], 'paren': 0, 'brace': 0, 'last0': None}
            tokens = item['tokens']
            if tok == '{' and item['paren'] == 0 and item['brace'] == 0:
                item['function'] = item['last0'] == ')' and '=' not in [t for t, d in zip(tokens, _depths(tokens))
                                                                       if d[:2] == (0, 0)]
            tokens.append(tok)
            if tok == '(':
                item['paren'] += 1
            elif tok == ')':
                item['paren'] -= 1
            elif tok == '{':
                item['brace'] += 1
            elif tok == '}':
                item['brace'] -= 1
            if item['paren'] == 0 and item['brace'] == 0:
                if tok == ';' or (tok == '}' and item.get('function')):
                    finish(item)
                    item = None
                    continue
                item['last0'] = tok
    if item is not None:
        finish(item, always=True)
    for entry in items:
        stack_words = {word for level in entry['stack'] for directive in level for word in IDENTIFIER.findall(directive)}
        entry['uses'] = frozenset(entry['uses'] | stack_words)
    _PARSED[(text, version)] = items
    return items


def _shapes(item):
    """True when ITEM can carry a size or a value into what it declares: not a function (body or prototype) and not a
    function-like macro (version 3)."""
    if item.get('body') or item.get('function_macro'):
        return False
    return not (item['call'] and not item['text'].startswith('typedef'))


def _timing_only(item):
    """True for an item of a TIMING_HEADERS file that only times frames (version 3): a function, a prototype, an
    extern variable, a function-like macro, an #undef (the disk wait wrappers replace fopen, fread and fseek) or an
    enum of slot numbers. A struct, union, typedef or object-like macro is never timing-only: it can carry a
    layout."""
    text = item['text']
    if text.startswith('typedef') or any(re.search(r'\b%s\s+\w+\s*\{' % tag, text) for tag in ('struct', 'union')):
        return False
    if text.startswith('#'):
        return bool(item.get('function_macro')) or text.startswith('#undef')
    return not _shapes(item) or text.startswith('extern') or text.startswith('enum {')


TARGET_TEST = 'defined ( __m68k__ )'


def _target_only(item):
    """True when ITEM sits in an #if branch that needs __m68k__ (version 5): only the target compiler sees it, and the
    builder's only target compile is the ABI probe, which reads sizes (an `#if ... && defined(__m68k__)` first branch,
    no `||`, not negated)."""
    for level in item['stack']:
        test = level[0] if len(level) == 1 else ''
        if TARGET_TEST in test and '! ' + TARGET_TEST not in test and '||' not in test:
            return True
    return False


def _word_value(item):
    """True when ITEM can carry a value a builder reads as text (version 5): not a function, a prototype, a
    function-like macro or an extern declaration."""
    return _shapes(item) and not item['text'].startswith('extern')


def kept_items(headers, roots, version=1, definitions_only=(), word_roots=()):
    """({path: [kept item, ...]}, uncertain) of HEADERS {path: text} for the names ROOTS can reach (module doc).
    DEFINITIONS_ONLY: files nothing compiles, read only for single definitions (a .c file named only in define()
    or cvar_default calls): their function bodies are never kept (version 2).
    Version 3: a timing-only item of a TIMING_HEADERS file (_timing_only) is kept only when an item that can carry a
    layout (_shapes: a struct, typedef, variable or object-like macro outside the timing items) names it; the names
    a function body, a prototype, a function-like macro or the reached code itself use do not keep it."""
    parsed = {path: parse_header(text, version) for path, text in headers.items()}
    parsed = {path: [item for item in items if not (path in definitions_only and item.get('body'))]
              for path, items in parsed.items()}
    timing = {(path, index) for path, items in parsed.items() if version >= 3 and path in TIMING_HEADERS
              for index, item in enumerate(items) if _timing_only(item)}
    macros = {name for items in parsed.values() for item in items if item['text'].startswith('#define')
              for name in item['defines']}
    by_name = {}
    for path, items in parsed.items():
        for index, item in enumerate(items):
            for name in item['defines']:
                by_name.setdefault(name, []).append((path, index))
    # (name, reached from a layout item): a timing-only item is kept only on the second
    reached, kept = {(name, False) for name in roots}, set()
    pending = list(reached)

    def keep(ref):
        kept.add(ref)
        item = parsed[ref[0]][ref[1]]
        shaped = ref not in timing and _shapes(item)
        for name in item['uses']:
            if (name, shaped) not in reached:
                reached.add((name, shaped))
                pending.append((name, shaped))
    # version 5: a target-only item that cannot carry a size (_target_only, _shapes) is never kept by a name: the host
    # compiles never see it and the ABI probe reads only sizes
    sizeless = {(path, index) for path, items in parsed.items() for index, item in enumerate(items)
                if version >= 5 and not item['always'] and _target_only(item) and not _shapes(item)}
    for path, items in parsed.items():
        for index, item in enumerate(items):
            if ((path, index) in timing or (path, index) in sizeless) and not item['always']:
                continue
            if item['always'] or item['call'] in macros:
                keep((path, index))
    # version 5: WORD_ROOTS (words of one-line strings) keep only the items that can carry a value (_word_value)
    for name in sorted(set(word_roots) - set(roots)):
        for ref in by_name.get(name, ()):
            if ref not in kept and ref not in timing and ref not in sizeless and _word_value(parsed[ref[0]][ref[1]]):
                keep(ref)
    while pending:
        name, shaped = pending.pop()
        for ref in by_name.get(name, ()):
            if ref not in kept and (shaped or ref not in timing) and ref not in sizeless:
                keep(ref)
    out = {path: [item for index, item in enumerate(items) if (path, index) in kept] for path, items in parsed.items()}
    uncertain = any(item['paste'] for items in out.values() for item in items)
    return out, uncertain


def value(items, version=VERSION):
    """The key value of a file's kept items: the version's prefix + SHA-256 of their #if conditions and texts, in
    order."""
    rows = [[[list(level) for level in item['stack']], item['text']] for item in items]
    return PREFIXES[version] + hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode('utf-8')).hexdigest()


def define_rows(text, reads):
    """[[reader, name, its first match or None], ...] of a file's TEXT for READS {(name, reader)} (version 4): every
    value those readers return for those names, nothing else of the file."""
    stripped = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    rows = []
    for name, reader in sorted(reads):
        which, pattern, flags = DEFINE_PATTERNS[reader]
        match = re.search(pattern % re.escape(name), stripped if which == 'stripped' else text, flags)
        rows.append([reader, name, match.group(1) if match else None])
    return rows


def define_value(text, names, version=4):
    """The key value of a define-only file (version 4 and later): the reading's prefix, DEFINES_TAG and the SHA-256
    of define_rows."""
    rows = define_rows(text, names)
    return PREFIXES[max(4, version)] + DEFINES_TAG + hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode('utf-8')).hexdigest()


def _define_read(node, parents):
    """(name, reader) a define-context string constant NODE is read for: the call's second argument and the called
    reader, or the DEFINES table entry's NAME (read by engine_limits.define); None when it is not a literal or the
    reader has no pattern."""
    child, above = node, parents.get(node)
    while isinstance(above, ast.BinOp):
        child, above = above, parents.get(above)
    if isinstance(above, ast.Call) and len(above.args) >= 2 and above.args[0] is child \
            and isinstance(above.args[1], ast.Constant) and isinstance(above.args[1].value, str):
        read = (above.args[1].value, _callee(above))
    else:
        parent = parents.get(node)
        if not (isinstance(parent, ast.Tuple) and len(parent.elts) == 2 and isinstance(parent.elts[1], ast.Constant)
                and isinstance(parent.elts[1].value, str)):
            return None
        read = (parent.elts[1].value, 'define')
    return read if IDENTIFIER.fullmatch(read[0]) and read[1] in DEFINE_PATTERNS else None


# --------------------------------------------------------------------------
# How the reached Python code names the engine files

def _callee(call):
    func = call.func
    return func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None


def _module_tree(text):
    """(tree, {node: parent}, {node: unit names}) of a module's text; None when it does not parse."""
    if text in _TREES:
        return _TREES[text]
    try:
        tree = ast.parse(text)
    except SyntaxError:
        _TREES[text] = None
        return None
    parents, units = {}, {}

    def visit(node, names):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
            here = names
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node is tree:
                here = frozenset({child.name})
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and isinstance(node, ast.ClassDef) \
                    and parents.get(node) is tree:
                here = frozenset({node.name + '.' + child.name, node.name})
            elif node is tree:
                targets = [t.id for t in getattr(child, 'targets', [getattr(child, 'target', None)])
                           if isinstance(t, ast.Name)]
                here = frozenset({'<top>', '<main>', *targets})
            units[child] = here
            visit(child, here)
    visit(tree, frozenset({'<top>'}))
    _TREES[text] = (tree, parents, units)
    return _TREES[text]


def _context(node, parents, units, relative, readers=DEFINE_READ_FUNCTIONS):
    """'doc', 'define', 'receipt' or 'text': how the string constant NODE names a file (READERS: the define readers
    of the reading's version)."""
    parent = parents.get(node)
    if isinstance(parent, ast.Expr):
        return 'doc'
    child, above = node, parent
    while isinstance(above, ast.BinOp):
        child, above = above, parents.get(above)
    if isinstance(above, ast.Call) and above.args and above.args[0] is child and len(above.args) >= 2 \
            and _callee(above) in readers and isinstance(above.args[1], ast.Constant) \
            and isinstance(above.args[1].value, str):
        return 'define'
    if isinstance(parent, ast.Tuple) and len(parent.elts) == 2 and parent.elts[0] is node \
            and isinstance(parent.elts[1], ast.Constant) and isinstance(parent.elts[1].value, str) \
            and UPPER_NAME.fullmatch(parent.elts[1].value):
        table, assign = parents.get(parent), parents.get(parents.get(parent))
        if isinstance(table, ast.Dict) and isinstance(assign, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id.endswith(DEFINE_TABLE_SUFFIX) for t in assign.targets):
            return 'define'
    if any((relative, unit) in RECEIPT_UNITS for unit in units.get(node, ())):
        above = parent
        while above is not None and not isinstance(above, ast.stmt):
            if isinstance(above, ast.Call) and _callee(above) == RECEIPT_CALL:
                return 'receipt'
            above = parents.get(above)
    return 'text'


def _named(text, engine, by_base):
    """The engine files of ENGINE a string constant TEXT names (build_cache._match_data's rules, for one constant)."""
    found = set()
    if '/' in text or '\\' in text:
        path = posixpath.normpath(text.replace('\\', '/'))
        found |= {f for f in engine if f == path or f.endswith('/' + path)}
    for token in re.findall(r'[A-Za-z0-9_.+-]+', text):
        found |= by_base.get(token, set())
    return found


def read_text(index, path):
    """A checkout file's text (one place, so a test can show the stage an edited header)."""
    return (index.root / path).read_text(encoding='utf-8', errors='replace')


def resolve_include(name, files, folders):
    for base in folders:
        candidate = posixpath.normpath(base + '/' + name)
        if candidate in files:
            return candidate
    return None


def narrow(index, script, selected, folders, readers):
    """SELECTED ({path: digest}, a stage key's selection) with its engine C files counted by their use (module doc).
    INDEX: the stage's build_cache.SourceIndex; FOLDERS: the engine's -I folders; READERS: the modules that name an
    engine folder only to read the files they name (build_cache.C_HEADER_READERS). Unchanged when the reach cannot
    be read file by file. The reading's version: INDEX.engine_facts (True: VERSION)."""
    version = VERSION if index.engine_facts is True else int(index.engine_facts)
    define_readers = DEFINE_READ_FUNCTIONS if version < 2 else DEFINE_READ_FUNCTIONS_2
    engine = {path for path in selected if path.startswith('engine/') and path.endswith(C_SUFFIXES)}
    reached = index.reached_units(script) or {}
    if not engine or not reached:
        return selected
    by_base = {}
    for path in engine:
        by_base.setdefault(path.rsplit('/', 1)[-1], set()).add(path)
    contexts, probes, roots, writers, define_names, words = {}, set(), set(), False, {}, set()
    for relative, unit_names in reached.items():
        symbols = index._module_symbols(relative)
        for unit in unit_names:
            if (relative, unit) in RECEIPT_WRITERS:
                writers = True
            for text, _ in (symbols['units'].get(unit) or {}).get('constants', ()):
                if version < 2:
                    roots.update(IDENTIFIER.findall(text))
                if relative not in readers and posixpath.normpath(text.replace('\\', '/')) in folders:
                    return selected        # an engine folder named whole: every file of it counts whole
        parsed = _module_tree((index.root / relative).read_text(encoding='utf-8', errors='replace'))
        if parsed is None:
            return selected
        tree, parents, units = parsed
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)) \
                    or not set(units.get(node, ())) & set(unit_names):
                continue
            if version >= 5 and not isinstance(parents.get(node), ast.Expr) \
                    and not ('\n' in node.value and relative in readers):
                words.update(IDENTIFIER.findall(node.value))    # a word of a message or option text (version 5)
            elif version >= 2 and not isinstance(parents.get(node), ast.Expr):
                roots.update(IDENTIFIER.findall(node.value))    # what the code uses; a docstring reads nothing
            if '\n' in node.value:
                if relative in readers:      # a C source the reader compiles (the ABI probe): its #include lines
                    probes.update(filter(None, (resolve_include(name, index.files, folders)
                                                for name in INCLUDE_LINE.findall(node.value))))
                continue
            if len(node.value) > 400:
                continue
            for path in _named(node.value, engine, by_base):
                found = _context(node, parents, units, relative, define_readers)
                if path in POLICY_FILES and relative in POLICY_MODULES and found == 'text':
                    found = 'policy'
                contexts.setdefault(path, set()).add(found)
                if found == 'define' and version >= 4:
                    define_names.setdefault(path, set()).add(_define_read(node, parents))
    kinds = {}
    for path, found in contexts.items():
        if found & {'policy'} and not ('text' in found or ('receipt' in found and writers)):
            kinds[path] = 'policy'
        elif 'text' in found or ('receipt' in found and writers):
            kinds[path] = 'text'
        elif 'define' in found:
            kinds[path] = 'define'
        elif 'doc' in found:
            kinds[path] = 'doc'
        else:
            kinds[path] = 'receipt'
    defines_only = set()
    if version >= 4:
        # read only by the define readers and included by nothing else the key counts: the values read (define_value)
        others = index.include_closure(sorted({path for path, kind in kinds.items()
                                               if kind not in ('receipt', 'policy', 'define')} | probes))
        defines_only = {path for path, kind in kinds.items() if kind == 'define' and path not in others
                        and define_names.get(path) and None not in define_names[path]}
    closure = index.include_closure(sorted({path for path, kind in kinds.items()
                                            if kind not in ('receipt', 'policy') and path not in defines_only}
                                           | probes))
    # what the folder rule put in the key: every named file and the closure of them all (receipts included)
    named_closure = index.include_closure(sorted(set(kinds) | probes))
    whole, facts, out = set(), set(), dict(selected)
    # the probe's own #include closure counts too (the earlier method reached it only through the receipt's names)
    for path in sorted(engine | {p for p in closure if p.endswith(C_SUFFIXES)}):
        kind = kinds.get(path)
        if path not in out:
            out[path] = index.files[path]
        if path in defines_only:
            out[path] = define_value(read_text(index, path), define_names[path], version)
        elif kind == 'policy' and path not in closure:
            import engine_loader_policy
            out[path] = engine_loader_policy.key_value(index.root)
        elif kind == 'text':
            whole.add(path)
        elif kind not in ('define', 'doc') and path not in closure:
            if path not in named_closure:
                return selected            # in the key for a reason this reading does not know
            del out[path]                  # named only for the receipt, or included only by such a file
        elif path.endswith(HEADER) or (version >= 2 and kind in ('define', 'doc')):
            facts.add(path)
        else:
            whole.add(path)
    for path in whole:
        if kinds.get(path) in ('text', None):    # read whole or compiled: what it names counts
            roots.update(TOKEN.findall(strip_comments(read_text(index, path))))
    headers = {path: read_text(index, path) for path in sorted(facts)}
    included = {target for path in closure for target in index._includes.get(path, ())}   # what an #include reaches
    definitions_only = {path for path in facts if version >= 2 and kinds.get(path) in ('define', 'doc')
                        and not path.endswith(HEADER) and path not in included}
    kept, uncertain = kept_items(headers, {word for word in roots if IDENTIFIER.fullmatch(word)}, version,
                                 definitions_only, words)
    if uncertain:
        return selected
    for path in facts:
        if kept[path]:
            out[path] = value(kept[path], version)
        else:
            del out[path]
    return out


# --------------------------------------------------------------------------
# Reuse sources keyed before this reading

_OLD_INDEXES = {}


def translate(old_components, new_components, old_run, name, current=None):
    """NEW_COMPONENTS (a stage key's parts, as build_cache.comparable gives them: this checkout in the record's form)
    read against OLD_COMPONENTS, a record made by an earlier key method: whole engine files or an earlier version of
    this reading (its values' prefix says which), or an earlier stage key form (BUILD-KEY-TOP-DEFAULTS-NAME-54: form 3).
    When OLD_RUN's own source tree (the checkout its stage ran from) gives exactly the recorded sources by the record's
    method, that tree's sources by today's method are compared with this checkout's (CURRENT: its stage key parts in
    today's form; default NEW_COMPONENTS): every file the same both ways takes the record's value (equal), every other
    file this checkout's. Anything else: NEW_COMPONENTS unchanged (the stage is compared as before)."""
    import build_cache as B
    current = current or new_components
    old = ((old_components or {}).get('sources') or {}).get('by_file')
    new = ((new_components or {}).get('sources') or {}).get('by_file')
    now = ((current or {}).get('sources') or {}).get('by_file')
    if not old_run or not old or not new or not now:
        return new_components
    made = {version for version, prefix in PREFIXES.items() if any(str(v).startswith(prefix) for v in old.values())}
    if len(made) > 1:
        return new_components
    recorded = made.pop() if made else False
    form = B.source_format(old_components)
    if (recorded == VERSION and form in (None, B.STAGE_TOP_FORMAT)) or old == new:
        return new_components      # the same method, or nothing to explain
    if form is not None and form < 3:
        return new_components      # forms 1 and 2: the older reach, compared as before (build_cache.comparable)
    if recorded is False and not any(path.startswith('engine/') and path.endswith(C_SUFFIXES) for path in old) \
            and form in (None, B.STAGE_TOP_FORMAT):
        return new_components
    try:
        state = json.loads((B.Path(old_run) / 'build-state.json').read_text())
    except (OSError, ValueError):
        return new_components
    reused = ((state.get('stage_cache') or {}).get('reused') or {}).get(name) or {}
    step = next((s for s in state.get('steps') or () if s.get('name') == name), None)
    command = [str(part) for part in (reused.get('original_command') or (step or {}).get('command') or ())]
    script = B.stage_script(command) if command else None
    if script is None or not script.is_file() or 'tools' not in script.parts:
        return new_components
    parts = script.parts
    root = B.Path(*parts[:len(parts) - 1 - parts[::-1].index('tools')])
    scope = (state.get('stage_cache') or {}).get('scope') or B.DEFAULT_SCOPE
    selections = []
    for facts, wanted in ((recorded, form), (VERSION, None)):
        key = (str(root), scope, facts)
        if key not in _OLD_INDEXES:
            _OLD_INDEXES[key] = B.SourceIndex(root, scope=scope, top_format=B.STAGE_TOP_FORMAT, engine_facts=facts)
        index = _OLD_INDEXES[key]
        try:
            chosen = (index.selection(script)[0] if wanted in (None, index.top_format)
                      else index.previous_selections(script).get(wanted))
        except (OSError, ValueError, SyntaxError):
            return new_components
        # as the stage key itself reads them (build_cache.stage_components): the layer-row tables by the layers the
        # stage reads. Without it a stage that reads such a table (chim: config/collision-hull-surface.json) never
        # matched its record here, and every reading change re-keyed it (CHIM-KEYS-TOO-BROAD-62)
        selections.append(B.layer_table_values(chosen, name, root) if isinstance(chosen, dict) else chosen)
    recorded_again, today = selections
    if recorded_again != old or today is None:
        return new_components      # the tree is not the one the record was made from
    merged = {}
    for path in set(old) | set(today) | set(now):
        if today.get(path) == now.get(path):
            if path in old:
                merged[path] = old[path]   # the same both ways today: the record's own value
        elif path in now:
            merged[path] = now[path]
    sources = dict(new_components['sources'], by_file=merged, digest=B.digest_json(merged), files=len(merged))
    return dict(new_components, sources=sources)
