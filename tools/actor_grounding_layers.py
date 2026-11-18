# SPDX-License-Identifier: GPL-3.0-only
"""The expansions' id file beside the grounding policy (config/actor_grounding_layers.json).

Outdoors a person is classed by id (actor_grounding.initial_state, config/actor_grounding.json). The people only
Tribunal or Bloodmoon place outdoors (Mournhold's districts presented as exterior cells, Solstheim) are classed in a
file of their own, measured by tools/actor_grounding_census.py with the expansions selected, and read here.

This is a module of its own on purpose. The room actor, actor ground and region actor unit caches key the import-time
code of tools/actor_grounding.py and the functions their workers reach in it: one new name there bakes all 2,342
room actors again although none of them reads this file. So actor_grounding.py and its policy file do not move for an
expansion; the outdoor paths that can meet an expansion's person call outdoor_state() here, which asks the policy
first and this file only for an id the policy does not name.
"""
import json
from pathlib import Path

NAME = 'actor_grounding_layers.json'
FORMAT = 'AmiWind actor grounding layers 1'
MODES = ('scripted_airborne', 'flying', 'levitating', 'swimming', 'authored_dead')
LAYERS = None           # another file (tests); None: NAME beside the policy file
_LAYERS = {}


def layers_path():
    import actor_grounding
    return Path(LAYERS) if LAYERS else Path(actor_grounding.POLICY).with_name(NAME)


def layer_policy(path=None):
    """(ground ids, {id: rule}) of the expansions' id file; a missing file: nothing."""
    path = Path(path or layers_path())
    try:
        stamp = (str(path), path.stat().st_mtime_ns)
    except OSError:
        return frozenset(), {}
    if stamp not in _LAYERS:
        doc = json.loads(path.read_text(encoding='utf-8'))
        if doc.get('format') != FORMAT:
            raise ValueError('Unsupported grounding layers file: %s' % path.name)
        _LAYERS.clear()
        _LAYERS[stamp] = (frozenset(str(i).casefold() for i in doc.get('ground_npcs', ())),
                          {str(k).casefold(): v for k, v in (doc.get('exceptions') or {}).items()})
    return _LAYERS[stamp]


def outdoor_state(identifier):
    """The initial support state of a person placed outdoors: the policy's class of its id
    (actor_grounding.initial_state: the policy wins), else the expansions' id file's, else an error (never a guess)."""
    from actor_grounding import initial_state
    try:
        return initial_state(identifier)
    except ValueError as error:
        if not str(error).startswith('Unclassified'):
            raise
    key = identifier.casefold()
    ground, rules = layer_policy()
    if key in rules:
        rule = rules[key]
        if rule.get('mode') not in MODES or not rule.get('reason'):
            raise ValueError('Unknown or undocumented initial support state')
        return rule['mode']
    if key in ground:
        return 'ground'
    raise ValueError('Unclassified initial support state: ' + key)
