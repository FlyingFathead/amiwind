# SPDX-License-Identifier: GPL-3.0-only
"""Conservative source visibility audit; never executes scripts or changes assets."""
import hashlib
import math
import operator
import re
from collections import Counter
from .audit import cell_data
from .esm import records, subrecords, string, text, first, is_deleted, require

BASE_TYPES = set('STAT ACTI CONT DOOR LIGH NPC_ CREA LEVC LEVI ALCH APPA ARMO BOOK CLOT INGR LOCK MISC PROB REPA WEAP'.split())
OPS = {'==': operator.eq, '!=': operator.ne, '<': operator.lt, '>': operator.gt,
       '<=': operator.le, '>=': operator.ge}
CONDITION = re.compile(r'if\s*\(\s*([a-z_][a-z_0-9]*)\s*(==|!=|<=|>=|<|>)\s*(-?\d+(?:\.\d+)?)\s*\)')


def classify_script(source, globals_known):
    """Recognize only a complete, side-effect-free guarded enable/disable template."""
    digest = hashlib.sha256(source.encode('utf-8')).hexdigest()
    unknown = {'status': 'unresolved_script', 'source_text_sha256': digest,
               'runtime_implemented': False}
    lines = [line.split(';', 1)[0].strip().casefold() for line in source.splitlines()]
    lines = [re.sub(r'\s+', ' ', line) for line in lines if line]
    if len(lines) != 11 or not re.fullmatch(r'begin [a-z_][a-z_0-9]*', lines[0]):
        return unknown
    name = lines[0].split()[1]
    if lines[-1] not in ('end', 'end ' + name):
        return unknown
    match = CONDITION.fullmatch(lines[1])
    if not match or match[1] not in {g.casefold() for g in globals_known}:
        return unknown
    if lines[5] != 'else' or lines[9] != 'endif':
        return unknown
    # Exact nested guards prevent local variables, event logic or other commands
    # from being silently treated as a persistent global predicate.
    def branch(start, action, disabled):
        return (re.fullmatch(r'if\s*\(\s*getdisabled\s*==\s*' + str(disabled) + r'\s*\)', lines[start])
                and lines[start + 1:start + 3] == [action, 'endif'])
    positive = branch(2, 'enable', 1) and branch(6, 'disable', 0)
    negative = branch(2, 'disable', 0) and branch(6, 'enable', 1)
    if not (positive or negative) or lines[9] != 'endif':
        return unknown
    return {**unknown, 'status': 'conditional', 'global': match[1], 'operator': match[2],
            'value': float(match[3]), 'enabled_when_condition': bool(positive)}


def evaluate_visibility(rule, state):
    """Evaluate audit metadata at an explicit state; None means unknown, never hidden."""
    if rule.get('status') != 'conditional':
        return None
    values = {k.casefold(): v for k, v in state.items()}
    value = values.get(rule['global'])
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return OPS[rule['operator']](value, rule['value']) == rule['enabled_when_condition']


def filter_references(references, report):
    """Apply an explicit audited fixed state; unknown and unaudited references survive.

    This is a build-time snapshot, not quest execution. Reuse the same report for
    geometry, flora and point-entity inputs so later passes cannot restore hidden
    placements. Never mutate the shared source index or model pool.
    """
    hidden = {r['reference'] for r in report['references']
              if r['enabled_at_requested_state'] is False}
    return [r for r in references if r['number'] not in hidden]


def audit_cell(raw, cell, state=None):
    """Audit one exterior CELL in one master; mod merging and runtime execution unsupported."""
    bases = {}; scripts = {}; globals_known = set(); selected = []
    for tag, flags, payload in records(raw):
        if tag not in BASE_TYPES | {'SCPT', 'GLOB', 'CELL'}:
            continue
        fields = list(subrecords(payload))
        deleted = is_deleted(flags, fields, header_only=tag == 'CELL')
        if tag in BASE_TYPES:
            ident = text(fields, 'NAME').casefold()
            require(ident not in bases, 'Duplicate base record: ' + ident)
            bases[ident] = (tag, text(fields, 'SCRI'), deleted)
        elif tag == 'GLOB' and not deleted:
            globals_known.add(text(fields, 'NAME').casefold())
        elif tag == 'SCPT':
            ident = string(first(fields, 'SCHD')[:32]).casefold()
            require(ident not in scripts, 'Duplicate script: ' + ident)
            scripts[ident] = None if deleted else text(fields, 'SCTX')
        elif tag == 'CELL' and not deleted:
            data = cell_data(fields)
            if not data['flags'] & 1 and (data['x'], data['y']) == tuple(cell):
                selected.append(data)
    require(len(selected) == 1, 'Expected exactly one exterior cell')
    rows = []; seen = set()
    for ref in selected[0]['refs']:
        require(ref['number'] not in seen, 'Duplicate placed reference')
        seen.add(ref['number'])
        if ref.get('deleted'):
            continue
        base = bases.get(ref['id'].casefold())
        rule = {'status': 'missing_base', 'runtime_implemented': False}
        script = ''
        if base:
            kind, script, deleted = base
            rule['status'] = 'deleted_base' if deleted else 'no_script'
            if not deleted and script:
                source = scripts.get(script.casefold())
                rule = (classify_script(source, globals_known) if source is not None else
                        {'status': 'missing_script', 'runtime_implemented': False})
        rows.append({'reference': ref['number'], 'object': ref['id'],
                     'type': base[0] if base else None, 'script': script, 'visibility': rule,
                     'enabled_at_requested_state': evaluate_visibility(rule, state or {})})
    return {'schema': 'cell-script-visibility-1', 'master_sha256': hashlib.sha256(raw).hexdigest(),
            'cell': list(cell), 'requested_state': state or {}, 'references': rows,
            'counts': dict(Counter(r['visibility']['status'] for r in rows)),
            'scope': 'Source metadata only. No conversion, residency, native or gameplay acceptance. '
                     'No-script does not prove unconditional presence; other scripts may target it.'}
