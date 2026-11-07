#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Alchemy data (ALCHEMY-61, docs/ALCHEMY.md): what the engine needs to make, drink and eat as the original does.

Two parts, both from the user's master file at build time (nothing of the game is kept in the source tree):

1. The alchemy block of an inventory catalogue row (tools/prepare_inventory.py; bytes 440..495 of the 512-byte row, in
   place of the weapon and armour numbers, which such a row does not use; catalogue flag 64 says the block is there):
     440  u8   kind: 1 ingredient, 2 potion, 3 apparatus
     441  u8   effects in the list (an ingredient: always 4 slots, an empty one has effect 255)
     442  u16  0
     444  f32  the apparatus quality (AADT), 0 for the others
     448  8 x (u8 effect, u8 argument, u16 duration, u16 magnitude), little-endian, zero past the list:
          the argument is the attribute or skill the effect names (255 none); an ingredient's duration and magnitude
          are 0 (they come from the eater's skill); a potion's are the record's (every potion of the masters has
          magnitude min = max and range Self)
   The engine reads it with the row (aw_inventory.c inv_parse_row): no file of its own, no extra read when an item is
   used.
2. id1/alchemy/settings.txt (AWAL1, read when the alchemy window opens or an item is drunk or eaten, then freed):
     set NAME VALUE     fWortChanceValue, fPotionStrengthMult, iAlchemyMod, fPotionT1MagMult, fPotionT1DurMult
     text NAME LINE     the game's own lines (TEXTS)
     sound NAME PATH    Drink, Swallow, potion success, potion fail (sound/alchemy/*.wav, 11025 Hz 8-bit mono)
     tier NAME ID       a potion of the masters for each of the six bottle looks (OpenMW 0.51 alchemy.cpp addPotion
                        rolls one of standard, bargain, cheap, fresh, exclusive, quality for a made potion); a made
                        potion borrows that potion's model and picture

Rules from OpenMW 0.51 (reference, own code): components/esm3/loadingr.cpp (an ingredient effect keeps its attribute
or skill only when the effect is one that names it), components/esm3/loadalch.cpp, loadappa.cpp.
"""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))

FLAG_ALCHEMY = 64          # catalogue flag (aw_inventory.h AW_INV_ALCHEMY)
BLOCK = 56                 # bytes 440..495
KIND_INGREDIENT, KIND_POTION, KIND_APPARATUS = 1, 2, 3
SLOTS = 8                  # effects a block holds (a potion of the masters has at most 6; a made one at most 8)
NONE = 255
# OpenMW loadingr.cpp: the effects that name an attribute and those that name a skill (absorb, damage, drain, fortify,
# restore); every other effect's argument is dropped.
ATTRIBUTE_EFFECTS = (85, 22, 17, 79, 74)
SKILL_EFFECTS = (89, 26, 21, 83, 78)
SETTINGS = ('fWortChanceValue', 'fPotionStrengthMult', 'iAlchemyMod', 'fPotionT1MagMult', 'fPotionT1DurMult')
# The lines the engine shows (aw_alchemy.c): the window's words, the results of Create, eating without effect, and the
# words of an effect that names an attribute or skill (OpenMW magiceffects.cpp getMagicEffectString).
TEXTS = ('sPotionSuccess', 'sNotifyMessage8', 'sNotifyMessage6a', 'sNotifyMessage45', 'sNotifyMessage50',
         'sCreate', 'sIngredients', 'sApparatus', 'sEffects', 'sName', 'sCancel', 'sCalcinator', 'sAlembic', 'sRetort',
         'sAbsorb', 'sDamage', 'sDrain', 'sFortify', 'sRestore')
SOUNDS = (('drink', 'Drink'), ('swallow', 'Swallow'), ('success', 'potion success'), ('fail', 'potion fail'))
TIERS = ('standard', 'bargain', 'cheap', 'fresh', 'exclusive', 'quality')


def effect_argument(effect, skill, attribute):
    """The one argument an effect keeps: its skill for a skill effect, its attribute for an attribute effect, else
    NONE (OpenMW loadingr.cpp's fix of the records)."""
    if effect in SKILL_EFFECTS:
        return skill if 0 <= skill < 27 else NONE
    if effect in ATTRIBUTE_EFFECTS:
        return attribute if 0 <= attribute < 8 else NONE
    return NONE


def pack(kind, effects, quality=0.0):
    """The 56-byte block: EFFECTS a list of (effect, argument, duration, magnitude)."""
    if len(effects) > SLOTS:
        raise ValueError('An alchemy block holds at most %d effects' % SLOTS)
    out = struct.pack('<BBHf', kind, len(effects), 0, float(quality))
    for effect, argument, duration, magnitude in effects:
        if not (0 <= effect <= 142 or effect == NONE) or not 0 <= argument <= 255:
            raise ValueError('Effect out of range: %r' % ((effect, argument),))
        out += struct.pack('<BBHH', effect, argument, max(0, min(0xFFFF, duration)), max(0, min(0xFFFF, magnitude)))
    out += b'\0' * (BLOCK - len(out))
    assert len(out) == BLOCK
    return out


def ingredient_block(irdt):
    """IRDT (weight, value, 4 effects, 4 skills, 4 attributes) -> the block; four slots kept in place (an empty one
    NONE), so "the first effect" and the slot a skill reveals stay the record's."""
    if len(irdt) != 56:
        raise ValueError('Ingredient data of %d bytes' % len(irdt))
    values = struct.unpack('<fi4i4i4i', irdt)
    effects, skills, attributes = values[2:6], values[6:10], values[10:14]
    slots = []
    for effect, skill, attribute in zip(effects, skills, attributes):
        if 0 <= effect <= 142:
            slots.append((effect, effect_argument(effect, skill, attribute), 0, 0))
        else:
            slots.append((NONE, NONE, 0, 0))
    return pack(KIND_INGREDIENT, slots)


def potion_block(enams):
    """The ENAM effects (ENAMstruct: effect, skill, attribute, range, area, duration, min, max) -> the block. A potion
    acts on the drinker whatever its range (OpenMW spellcasting.cpp cast(Potion) inflicts every range on the caster);
    its magnitude is the record's (min = max in every potion of the masters; the block keeps the larger)."""
    effects = []
    for raw in enams:
        effect, skill, attribute, _range, _area, duration, low, high = struct.unpack('<hbbiiiii', raw)
        if not 0 <= effect <= 142:
            continue
        effects.append((effect, effect_argument(effect, skill, attribute), duration, max(low, high)))
    return pack(KIND_POTION, effects[:SLOTS])


def apparatus_block(aadt):
    """AADT (type, quality, weight, value) -> the block."""
    kind, quality, _, _ = struct.unpack('<iffi', aadt)
    if not 0 <= kind <= 3 or not quality > 0:
        raise ValueError('Apparatus type %d, quality %r' % (kind, quality))
    return pack(KIND_APPARATUS, [], quality)


def block_for(kind, fields):
    """The block of a record of KIND ('INGR', 'ALCH', 'APPA') from its subrecords, None for any other."""
    from mwad.esm import first
    if kind == 'INGR':
        return ingredient_block(first(fields, 'IRDT'))
    if kind == 'ALCH':
        return potion_block([e for t, e in fields if t == 'ENAM' and len(e) == 24])
    if kind == 'APPA':
        return apparatus_block(first(fields, 'AADT'))
    return None


def settings_text(kinds, tiers, sounds):
    """alchemy/settings.txt from the GMSTs (prepare_levelup.load's kinds), the bottle tiers {name: potion id} and the
    sounds {name: path under sound/}. A setting the master lacks is left out (the engine then refuses to make potions
    and says so); the report names it."""
    from prepare_levelup import clean, gmst_value
    lines = ['AWAL1']
    for name in SETTINGS:
        try:
            value = gmst_value(kinds, name)
        except ValueError:
            continue
        lines.append('set %s %s' % (name, ('%.6g' % value) if name[0] == 'f' else '%d' % value))
    for name in TEXTS:
        try:
            value = clean(gmst_value(kinds, name))
        except ValueError:
            continue
        if value:
            lines.append('text %s %s' % (name, value))
    for name, path in sorted(sounds.items()):
        lines.append('sound %s %s' % (name, path))
    for name in TIERS:
        if name in tiers:
            lines.append('tier %s %s' % (name, tiers[name]))
    return '\n'.join(lines) + '\n'


def bottle_tiers(items):
    """{tier: potion id}: for each bottle look the first catalogued potion (by id) without a script whose model is
    m/misc_potion_<tier>_01."""
    tiers = {}
    for identifier in sorted(items):
        item = items[identifier]
        if item['kind'] != 'ALCH' or item['script']:
            continue
        model = item['source_model'].replace('\\', '/').casefold()
        for tier in TIERS:
            if tier not in tiers and model == 'm/misc_potion_%s_01.nif' % tier:
                tiers[tier] = identifier
    return tiers


def prepare(data, id1, items):
    """Write alchemy/settings.txt and the four sounds; DATA the resolved data folder, ITEMS prepare_inventory.source_items'
    catalogue."""
    from mwad.audit import BSA, string
    from mwad.paths import child_ci
    from prepare_levelup import load
    data = Path(data)
    id1 = Path(id1)
    kinds = load(child_ci(data, 'Morrowind.esm'))
    report = {'held': {}, 'sounds': {}}
    sounds = {}
    try:
        from npc_geometry import Assets
        from prepare_combat import convert_wav
        assets = Assets(data, BSA(child_ci(data, 'Morrowind.bsa')))
    except (ImportError, OSError, KeyError, ValueError) as error:
        assets, report['held']['sounds'] = None, str(error)
    for name, record_id in SOUNDS:
        record = kinds['SOUN'].get(record_id.casefold())
        if not record or assets is None:
            report['held'].setdefault('sound ' + name, 'no record or no archive')
            continue
        source = 'sound/' + string(record['FNAM']).replace('\\', '/').casefold()
        try:
            (id1 / 'sound/alchemy').mkdir(parents=True, exist_ok=True)
            seconds = convert_wav(assets.read(source), id1 / ('sound/alchemy/%s.wav' % name))
            sounds[name] = 'alchemy/%s.wav' % name
            report['sounds'][name] = {'record': record_id, 'source': source, 'seconds': round(seconds, 3)}
        except (KeyError, OSError, ValueError) as error:
            report['held']['sound ' + name] = str(error)
    tiers = bottle_tiers(items)
    (id1 / 'alchemy').mkdir(parents=True, exist_ok=True)
    text = settings_text(kinds, tiers, sounds)
    (id1 / 'alchemy/settings.txt').write_text(text, encoding='cp1252', newline='\n')
    report['tiers'] = tiers
    report['missing_settings'] = [n for n in SETTINGS if ('set %s ' % n) not in text]
    report['bytes'] = len(text.encode('cp1252'))
    report['rows'] = {k: sum(1 for i in items.values() if i['kind'] == k) for k in ('INGR', 'ALCH', 'APPA')}
    return report
