# SPDX-License-Identifier: GPL-3.0-only
"""When a placement a script switches is shown: the stage of its own script (DOOR-USE-COLLISION-EXPANSIONS-68).

Many outdoor placements are switched on and off by their own record's script as the game goes on: a colony's
buildings stage by stage (Raven Rock's houses, its construction pieces and the trees cleared for them, each script
reading one global, the colony's state), a quest's plug in front of an entrance (an ice block or a rock its script
disables once a journal entry is reached). The engine hides such a placement, drawing and collision, when its script
switches it off (tools/effect_links.py hide rows, OUTDOOR-DISABLE-NOT-HIDDEN-68), but a converted frame holds the
collision of every stage at once. The door check (tools/door_engine_check.py) asks, for a door in the way of such a
placement: is there a time when the door is shown and the placement is not?

The stage form read here is the one these scripts share: a script whose own Disable and Enable lines stand under
conditions that compare one global (a GLOB record of the masters), the script's own locals or GetDisabled with a
number. For each value of that global met in such a script (and one either side), the script is run on its own
state, from shown and from hidden, until it settles: the values at which it can end shown are its stage. A script
that switches its own object under any other condition (a journal index, a distance, a cell) has no readable stage:
its placement can be hidden at some point, and when is not known. Rules from OpenMW apps/openmw/mwscript/
miscextensions.cpp OpEnable / OpDisable (the script's own object) and OpGetDisabled; the language as
components/compiler reads it (if, elseif, else, endif, set, the locals' short, long and float).

    stages = read(data_files)      # Stages: .switched {reference: stage}, .of_record(id) -> stage
    moments(door_stage, {reference: stage}) -> [(what, references hidden then)] while the door is shown

A stage is None (switched by a script whose stage is not read: hidden at some point), ALWAYS (never switched by its
own script) or (global, shown values, hidden values), the values over that global's domain."""
import re
from pathlib import Path

ALWAYS = 'always'
OPS = {'==': lambda a, b: a == b, '!=': lambda a, b: a != b, '>=': lambda a, b: a >= b, '<=': lambda a, b: a <= b,
       '>': lambda a, b: a > b, '<': lambda a, b: a < b}
CONDITION = re.compile(r'^\(\s*(\w+)\s*(==|!=|>=|<=|<|>)\s*(-?\d+(?:\.\d+)?)\s*\)$')
OWN_TOGGLE = re.compile(r'(?i)^(disable|enable)$')
ANY_TOGGLE = re.compile(r'(?i)(?<![\w>])(disable|enable)(?!\w)')
SET = re.compile(r'(?i)^set\s+(\w+)\s+to\s+(-?\d+(?:\.\d+)?)$')
RUNS = 3            # the script is run this many times on one value: these scripts settle in one or two


class Unknown(Exception):
    """The script switches its own object in a way the stage form does not read."""


def _lines(text):
    for raw in (text or '').replace('\r', '').split('\n'):
        line = raw.split(';', 1)[0].strip()
        if line:
            yield line


def parse(text, globals_):
    """The parsed script: (body, its locals), or raises Unknown (an if without its endif, its own object switched
    by a line the form does not read). A body is a list of ('toggle', on) | ('set', name, value) | ('return',) | ('if', [(condition, body)], else body)
    | ('other', touched locals); a condition is (kind, name, op, number) with kind 'disabled', 'local', 'global' or
    None (not read)."""
    locals_ = set()
    root = []
    stack = [('top', root)]

    def cond(text_):
        m = CONDITION.match(re.sub(r'\s+', ' ', text_.strip()))
        if not m:
            return (None, text_, None, None)
        name, op, number = m.group(1).casefold(), m.group(2), float(m.group(3))
        kind = 'disabled' if name == 'getdisabled' else 'local' if name in locals_ else \
            'global' if name in globals_ else None
        return (kind, name, op, number)
    for line in _lines(text):
        low = line.casefold()
        word = low.split(None, 1)[0]
        rest = line[len(word):].strip()
        if word == 'begin':
            continue
        if word == 'end':
            break
        if word in ('short', 'long', 'float'):
            locals_.update(n.casefold() for n in rest.replace(',', ' ').split())
            continue
        if word == 'if':
            node = ('if', [(cond(rest), [])], [])
            stack[-1][1].append(node)
            stack.append(('if', node[1][0][1], node))
            continue
        if word in ('elseif', 'else'):
            if stack[-1][0] != 'if':
                raise Unknown('%s outside an if' % word)
            node = stack.pop()[2]
            if word == 'elseif':
                node[1].append((cond(rest), []))
                stack.append(('if', node[1][-1][1], node))
            else:
                stack.append(('else', node[2], node))
            continue
        if word == 'endif':
            if stack[-1][0] not in ('if', 'else'):
                raise Unknown('endif outside an if')
            stack.pop()
            continue
        body = stack[-1][1]
        if OWN_TOGGLE.match(line):
            body.append(('toggle', low == 'enable'))
        elif ANY_TOGGLE.search(line) and '->' not in line:
            raise Unknown('its own object switched by %r' % line)
        elif word == 'return':
            body.append(('return',))
        elif SET.match(line):
            m = SET.match(line)
            body.append(('set', m.group(1).casefold(), float(m.group(2))))
        elif word == 'set':
            name = rest.split(None, 1)[0].casefold() if rest else ''
            body.append(('other', {name}))
        else:
            body.append(('other', set()))
    if len(stack) != 1:
        raise Unknown('an if without its endif')
    return root, locals_


def _toggles(body):
    """Whether BODY (with its nested ifs) holds an own toggle."""
    for s in body:
        if s[0] == 'toggle':
            return True
        if s[0] == 'if' and (any(_toggles(b) for _, b in s[1]) or _toggles(s[2])):
            return True
    return False


def _sets(body):
    out = set()
    for s in body:
        if s[0] == 'set':
            out.add(s[1])
        elif s[0] == 'other':
            out |= s[1]
        elif s[0] == 'if':
            for _, b in s[1]:
                out |= _sets(b)
            out |= _sets(s[2])
    return out


def _guards(body, out=None):
    """The names the conditions of the ifs that hold an own toggle read."""
    out = set() if out is None else out
    for s in body:
        if s[0] == 'if':
            if any(_toggles(b) for _, b in s[1]) or _toggles(s[2]):
                out.update(c[1] for c, _ in s[1])
            for _, b in s[1]:
                _guards(b, out)
            _guards(s[2], out)
    return out


def program(text, globals_):
    """(body, the one global its own toggles depend on, the numbers compared with it) of a script of the stage form,
    ALWAYS for a script that never switches its own object, or raises Unknown."""
    body, _locals = parse(text, globals_)
    if not _toggles(body):
        return ALWAYS
    guards = _guards(body)
    numbers, names = set(), set()

    def check(b):
        for s in b:
            if s[0] != 'if':
                continue
            for c, branch in s[1]:
                if c[0] is None:
                    # a condition not read: allowed only around lines that neither switch the object nor set a name
                    # one of its toggles' conditions reads
                    if _toggles(branch) or _toggles(s[2]) or (_sets(branch) & guards):
                        raise Unknown('its own toggle under a condition not read: %s' % c[1])
                elif c[0] == 'global':
                    names.add(c[1])
                    numbers.add(c[3])
                check(branch)
            check(s[2])
    check(body)
    if len(names) != 1:
        raise Unknown('its own toggles read %d globals' % len(names))
    return body, names.pop(), numbers


def run(body, value, shown, locals_):
    """SHOWN after one run of BODY with its global at VALUE (LOCALS changed in place)."""
    state = {'shown': shown, 'done': False}

    def test(c):
        kind, name, op, number = c
        if kind is None:
            return None
        current = (0.0 if state['shown'] else 1.0) if kind == 'disabled' else \
            locals_.get(name, 0.0) if kind == 'local' else value
        return OPS[op](current, number)

    def walk(b):
        for s in b:
            if state['done']:
                return
            if s[0] == 'toggle':
                state['shown'] = s[1]
            elif s[0] == 'set':
                locals_[s[1]] = s[2]
            elif s[0] == 'return':
                state['done'] = True
            elif s[0] == 'if':
                for c, branch in s[1]:
                    got = test(c)
                    if got is None:
                        break           # a condition not read (program() let it stand: it switches nothing)
                    if got:
                        walk(branch)
                        break
                else:
                    walk(s[2])
    walk(body)
    return state['shown']


def stage_of(prog, domain):
    """(global, shown values, hidden values) of a program over its global's DOMAIN: a value is shown when a run from
    shown or from hidden can settle shown, hidden when one can settle hidden."""
    if prog is ALWAYS:
        return ALWAYS
    body, name, _numbers = prog
    shown, hidden = set(), set()
    for value in domain:
        for start in (True, False):
            locals_, state = {}, start
            for _ in range(RUNS):
                state = run(body, value, state, locals_)
            (shown if state else hidden).add(value)
    return (name, frozenset(shown), frozenset(hidden))


MOMENTS = 40        # the most moments one door is traced at


def moments(door, placements):
    """[(what, sorted references)]: the moments at which PLACEMENTS ({reference: stage}, the switched ones near a door)
    can be hidden while DOOR (its stage) is shown, each with the placements hidden then, in the order they are
    tried. First a value of a global at which the door is shown (the door's own global: its shown values; for a door
    that is always shown, every value at which one of them is hidden), with every placement of that global its script
    hides at that value; then each placement whose stage is not read, alone (its script hides it at some point, but
    not known with which others); then each such placement together with each of those values' sets."""
    out, seen = [], set()

    def add(what, refs):
        key = tuple(sorted(refs))
        if key and key not in seen and len(out) < MOMENTS:
            seen.add(key)
            out.append((what, list(key)))
    read_ = {}
    for ref, stage in placements.items():
        if stage not in (None, ALWAYS):
            read_.setdefault(stage[0], []).append((ref, stage))
    values = []
    for name, rows in sorted(read_.items()):
        shown = door[1] if door not in (None, ALWAYS) and door[0] == name else \
            frozenset().union(*(stage[2] for _, stage in rows))
        for value in sorted(shown):
            refs = [ref for ref, stage in rows if value in stage[2]]
            if refs:
                values.append(('%s at %g' % (name, value), refs))
                add('with %s at %g, the placements its scripts hide then' % (name, value), refs)
    unread = sorted(ref for ref, stage in placements.items() if stage is None)
    for ref in unread:
        add('placement %d alone, which a script hides at some point' % ref, [ref])
    for ref in unread:
        for what, refs in values:
            add('with %s and placement %d, which a script hides at some point' % (what, ref), refs + [ref])
    return out


class Stages:
    """The stages of the masters' scripted placements: .switched {reference: stage} of every placement a script can
    switch (tools/effect_links.py scripted_placements; keyed by the merged master's number, merged_key, as the CHIM
    world names its placements), .records {record id: stage} of every record whose script switches its own object
    (of_record gives ALWAYS for the rest)."""

    def __init__(self, switched, records):
        self.switched, self.records = switched, records

    def of_record(self, ident):
        return self.records.get((ident or '').casefold(), ALWAYS)


def read(data_files):
    """Stages of the masters in DATA_FILES (Morrowind.esm, Tribunal.esm, Bloodmoon.esm, as present)."""
    import effect_links
    from mwad.audit import records, string, subrecords
    from mwad.paths import child_ci
    data = Path(data_files)
    raws = {m: p.read_bytes() for m, p in ((m, child_ci(data, m, required=False)) for m in effect_links.MASTERS)
            if p is not None}
    globals_, texts = set(), {}
    for m in effect_links.MASTERS:
        for tag, flags, payload in records(raws.get(m, b'')) if m in raws else ():
            if flags & 0x20 or tag not in ('GLOB', 'SCPT'):
                continue
            s = dict(subrecords(payload))
            if tag == 'GLOB' and 'NAME' in s:
                globals_.add(string(s['NAME'], errors='replace').casefold())
            elif tag == 'SCPT':
                texts[string(s.get('SCHD', b'')[:32], errors='replace').casefold()] = \
                    string(s.get('SCTX', b''), errors='replace')
    _ids, _scripts, _kinds, scripted = effect_links.script_targets(raws)
    progs = {}
    for name, text in texts.items():
        try:
            progs[name] = program(text, globals_)
        except Unknown:
            progs[name] = None
    domains = {}
    for p in progs.values():
        if p not in (None, ALWAYS):
            domains.setdefault(p[1], {0.0}).update(v + d for v in p[2] for d in (-1.0, 0.0, 1.0))
    stage_by_script = {n: (None if p is None else stage_of(p, sorted(domains[p[1]])) if p is not ALWAYS else ALWAYS)
                       for n, p in progs.items()}
    records_ = {ident: stage_by_script.get(script) for ident, script in scripted.items()
                if stage_by_script.get(script, ALWAYS) is not ALWAYS}
    switched = {}
    for ref, entry in effect_links.scripted_placements(data_files).items():
        stage = records_.get(entry['id'], ALWAYS)
        # named by another script's "X->Disable" / "X->Enable": switched, its stage not read
        switched[merged_key(ref)] = None if stage is ALWAYS else stage
    return Stages(switched, records_)


def merged_key(stable):
    """The merged master's key of a stable reference (src/mwad/masters.py _ref_key: the master's index times
    ADDON_KEY_STRIDE plus its own number): the number the CHIM world and the door check name a placement by."""
    import ref_identity
    content_file, low = ref_identity.split(stable)
    return ref_identity.file_index(content_file) * ref_identity.MERGED_STRIDE + low
