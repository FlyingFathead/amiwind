# SPDX-License-Identifier: GPL-3.0-only
"""Release readiness: what a release candidate or final would refuse, listed at the start of every build.

A development build may use private-test waivers (--allow-known-actor-ground-findings, accepted stair
findings, quick-test exclusions such as --no-npc-gallery), accepted entity losses (--accept-entity-loss)
and debugging opt-outs of shipped features. A release candidate or final refuses them, so each one is a
release blocker the day it appears (BUILD-RELEASE-READINESS-HIDDEN-41: dev5 passed with three of them and
the final found them only on its first run).

The list is not kept here a second time: every private-test refusal of the builder goes through
project_version.require_private_test_version, which records the options it saw; this module adds the
accepted entity loss, the retired flags used with --override and the debugging opt-outs that print a
warning instead of a refusal. Before the first stage the builder prints the block and writes it into the
build receipt (build-state.json "release_readiness").

Every item names its tracker ID (an entry of docs/bugs/bugs.json):
- --accept-known-stair-findings ID: the ID itself;
- --accept-entity-loss REASON: the IDs written in the reason;
- any item: --readiness-id KEY=ID[,ID...] (KEY = the option without its dashes, as the block prints it).
A full development build with an item that has no registered ID stops before any stage. MiniWind and other
area test builds (never a release) and asset-free dry runs list their items without that requirement.
Standard library only.
"""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BUGS = ROOT / 'docs' / 'bugs' / 'bugs.json'
OPTION = '--readiness-id'
TRACKER_ID = re.compile(r'\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-[0-9]{2}\b')

# Debugging opt-outs of shipped features: a warning in a development build, never in a release.
OPT_OUTS = (
    ('--no-tree-sprites', 'no_tree_sprites', 'shipped feature left out: world flora'),
    ('--no-extra-town', 'no_extra_town', 'shipped feature left out: the extra towns'),
    ('--only-core-towns', 'only_core_towns', 'shipped feature left out: the extra towns'),
    ('--skip-dressing', 'skip_dressing', 'shipped feature left out: interior dressing'),
    ('--no-entity-baseline', 'no_entity_baseline', 'the entity baseline check is off (losses are not seen)'),
)


def key_of(option):
    """'--stair-walk-sample 0' -> 'stair-walk-sample' (the KEY of --readiness-id KEY=ID)."""
    first = str(option).strip().split()[0] if str(option).strip() else str(option)
    return first.lstrip('-') or re.sub(r'[^a-z0-9]+', '-', str(option).lower()).strip('-')


def parse_ids(values):
    """{KEY: [ID, ...]} from --readiness-id KEY=ID[,ID...] values; a malformed value is an error."""
    named = {}
    for value in values or ():
        key, sep, ids = str(value).partition('=')
        key = key.strip().lstrip('-')
        found = [part.strip() for part in ids.split(',') if part.strip()]
        if not sep or not key or not found or any(not TRACKER_ID.fullmatch(part) for part in found):
            raise ValueError(f'{OPTION} {value!r}: use KEY=ID[,ID...] with tracker IDs such as '
                             'HARVEST-CHIM-REGION-LOSS-41 (KEY = the option without its dashes)')
        named.setdefault(key, []).extend(part for part in found if part not in named.get(key, ()))
    return named


def registered_ids(path=BUGS):
    """The tracker IDs of docs/bugs/bugs.json, or None when the register is not there (a staged tree)."""
    try:
        return {row['id'] for row in json.loads(Path(path).read_text(encoding='utf-8'))}
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _exclude_items(option):
    """One item per group of a recorded '--exclude a, b' (their aliases name the same item)."""
    import build_exclusions
    groups = [part.strip() for part in option[len(build_exclusions.OPTION):].split(',') if part.strip()]
    items = []
    for name in groups:
        row = build_exclusions.GROUPS.get(name, {})
        aliases = ['exclude-' + name]
        if row.get('alias'):
            aliases.append(row['alias'].lstrip('-'))
        if row.get('legacy'):
            aliases.append(row['legacy'].replace('_', '-'))
        what = 'quick test build leaves out ' + (row.get('label') or name)
        items.append({'option': build_exclusions.OPTION + ' ' + name, 'key': aliases[0],
                      'aliases': sorted(set(aliases[1:])), 'what': what, 'kind': 'skipped shipped feature'})
    return items


def collect(args, recorded):
    """[item] of this build: {option, key, aliases, what, kind, ids, id_source}. RECORDED: the options the
    private-test refusals saw (project_version.private_test_options)."""
    items = []
    for option in dict.fromkeys(recorded or ()):
        if option.startswith('--exclude '):
            items += _exclude_items(option)
            continue
        item = {'option': option, 'key': key_of(option), 'aliases': [], 'kind': 'private-test waiver',
                'what': 'refused for release candidates and finals'}
        if item['key'] == 'accept-known-stair-findings':
            ids = list(dict.fromkeys(getattr(args, 'accept_known_stair_findings', None) or ()))
            item.update(option=option + ' ' + ','.join(ids), what='known stair findings accepted', ids=ids,
                        id_source='option value')
        elif item['key'] == 'allow-known-actor-ground-findings':
            item['what'] = 'known actor ground findings accepted'
        items.append(item)
    reason = getattr(args, 'accept_entity_loss', None)
    if reason:
        items.append({'option': '--accept-entity-loss', 'key': 'accept-entity-loss', 'aliases': [],
                      'kind': 'accepted entity loss', 'what': 'reason: ' + str(reason),
                      'ids': list(dict.fromkeys(TRACKER_ID.findall(str(reason)))), 'id_source': 'reason text'})
    for row in getattr(args, 'retired_flags_record', None) or ():
        if row.get('overridden'):
            items.append({'option': row.get('flag') or row.get('name'), 'key': row.get('name'), 'aliases': [],
                          'kind': 'retired flag (--override)', 'what': row.get('why') or 'retired flag'})
    seen = {key for item in items for key in [item['key'], *item['aliases']]}
    for option, attribute, what in OPT_OUTS:
        if getattr(args, attribute, False) and key_of(option) not in seen:
            items.append({'option': option, 'key': key_of(option), 'aliases': [], 'kind': 'debugging opt-out',
                          'what': what})
    return items


def assess(items, named=None, registered=None, enforced=True, note=None):
    """The readiness record: items with their IDs (named by --readiness-id or carried by the item), missing
    and unknown IDs, and whether this build may start (enforced builds need a registered ID per item)."""
    named = dict(named or {})
    used = set()
    for item in items:
        ids = list(item.get('ids') or ())
        source = item.get('id_source') if ids else None
        for key in [item['key'], *item.get('aliases', ())]:
            if key in named:
                used.add(key)
                ids += [value for value in named[key] if value not in ids]
                source = OPTION if source is None else source + ' + ' + OPTION
        item['ids'], item['id_source'] = ids, source
        item['unknown_ids'] = sorted(value for value in ids if registered is not None and value not in registered)
        item['ok'] = bool(ids) and not item['unknown_ids']
    unused = sorted(set(named) - used)
    missing = [item for item in items if not item['ok']]
    return {'schema': 'amiwind-release-readiness-v1', 'items': items, 'ready': not items,
            'enforced': bool(enforced), 'refused': bool(enforced and missing), 'note': note,
            'unused_ids': {key: named[key] for key in unused},
            'register': 'docs/bugs/bugs.json' if registered is not None else 'not found (IDs not checked)'}


def lines(record):
    """The block printed before the first stage."""
    out = ['=' * 72, 'Release readiness: what a release candidate or final would refuse in this build']
    if not record['items']:
        out.append('  none: nothing here stops a release candidate or final')
    for number, item in enumerate(record['items'], 1):
        if item['ok']:
            ids = ', '.join(item['ids']) + f" ({item['id_source']})"
        elif item['unknown_ids']:
            ids = 'NOT IN THE TRACKER: ' + ', '.join(item['unknown_ids'])
        else:
            ids = f"NO TRACKER ID (name it: {OPTION} {item['key']}=ID)"
        out.append(f"  {number}. {item['option']} [{item['kind']}]: {item['what']} -> {ids}")
    if record['items']:
        out.append(f"  {len(record['items'])} release blocker(s) until fixed, or maintainer-accepted for the release "
                   'with their tracker links')
    for key, ids in record['unused_ids'].items():
        out.append(f"  note: {OPTION} {key}={','.join(ids)} matches no option of this build")
    if record.get('note'):
        out.append('  ' + record['note'])
    out.append('=' * 72)
    return out


def refusal(record):
    """The error of an enforced build with items that lack a registered tracker ID, or None."""
    if not record['refused']:
        return None
    missing = [item for item in record['items'] if not item['ok']]
    return ('release readiness: %d item(s) without a registered tracker ID (a waiver is a release blocker and '
            'needs its bug page first): ' % len(missing)
            + '; '.join(f"{item['option']} ({OPTION} {item['key']}=ID"
                        + (', unknown: ' + ', '.join(item['unknown_ids']) if item['unknown_ids'] else '') + ')'
                        for item in missing))


def check(args, recorded, enforced, note=None, register=BUGS):
    """collect + assess for the builder (args.readiness_id holds the --readiness-id values)."""
    return assess(collect(args, recorded), parse_ids(getattr(args, 'readiness_id', None)),
                  registered_ids(register), enforced, note)
