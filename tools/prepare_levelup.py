#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Levelling data from the player's own game files (LEVEL-UP-58; docs/CHARACTER_CREATION.md "Levelling").

Writes into the image's id1:
  levelup/settings.txt   AWLU1: the levelling game settings, each skill's governing attribute, specialization and
                         four use values (SKIL SKDT), the skill-raise sound, the game's own lines (GMST strings) and,
                         when the install has a Morrowind.ini, each level's own sentence ([Level Up] LevelN)
  levelup/<name>.awi     the level-up pictures (textures/levelup/<name>.dds), 128 x 64, the game palette (AWI1)
  levelup/coin.awi       the gold coin the box places on a picked attribute (8 x 8)
  sound/levelup/skillraise.wav   the "skillraise" sound record (11025 Hz, 8-bit mono)

The engine reads them in engine/aga/src/aw_levelup.c; the rules are the original's as OpenMW 0.51 implements them
(files/data-mw/scripts/omw/playerskillhandlers.lua, apps/openmw/mwgui/levelupdialog.cpp, mwmechanics/npcstats.cpp).
Nothing of the game is kept in the source tree: every value is read from the master at build time.
"""
import hashlib
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))      # ahead of tools/: src/mwad is the package (tools/mwad.py is its CLI)

# The engine's order (aw_levelup_rules.c setting_names); the misspelt name is the master file's own.
SETTINGS = ('fMajorSkillBonus', 'fMinorSkillBonus', 'fMiscSkillBonus', 'fSpecialSkillBonus', 'fLevelUpHealthEndMult',
            'iLevelupTotal', 'iLevelupMajorMult', 'iLevelupMinorMult', 'iLevelupMajorMultAttribute',
            'iLevelupMinorMultAttribute', 'iLevelupMiscMultAttriubte', 'iLevelupSpecialization') + tuple(
            'iLevelUp%02dMult' % n for n in range(1, 11))
# The game's lines the engine shows (aw_levelup.c game_text).
TEXTS = ('sNotifyMessage39', 'sLevelUpMsg', 'sLevelUpMenu1', 'sLevelUpMenu2', 'sNotifyMessage36')
# The level-up pictures by name (aw_levelup_rules.c AW_LevelupClassImage; OpenMW getLevelupClassImage).
PICTURES = ('acrobat', "agent", 'archer', 'assassin', 'barbarian', 'bard', 'battlemage', 'crusader', 'healer',
            'knight', 'mage', 'monk', 'pilgrim', 'rogue', 'scout', 'sorcerer', 'spellsword', 'thief', 'warrior',
            'witchhunter')
PICTURE = (128, 64)
COIN = 8
COIN_SOURCES = ('icons/tx_goldicon.dds', 'icons/gold.dds')
MAX_TEXT = 380            # the engine's line buffer (aw_levelup.c box_state_t text, game_text)
LEVELS = range(2, 101)


def load(master):
    """GMST, SKIL and SOUN records of the master: {tag: {key: {sub: bytes}}}; SKIL keyed by INDX."""
    from mwad.audit import records, subrecords, string
    kinds = {'GMST': {}, 'SKIL': {}, 'SOUN': {}}
    for tag, flags, raw in records(Path(master).read_bytes()):
        if tag not in kinds or flags & 0x20:
            continue
        fields = dict(subrecords(raw))
        if 'DELE' in fields:
            continue
        if tag == 'SKIL':
            kinds[tag][struct.unpack('<i', fields['INDX'])[0]] = fields
        else:
            kinds[tag][string(fields['NAME']).casefold()] = fields
    return kinds


def gmst_value(kinds, name):
    from mwad.audit import string
    fields = kinds['GMST'].get(name.casefold())
    if fields is None:
        raise ValueError('Missing game setting ' + name)
    if name[0] == 'f':
        return struct.unpack('<f', fields['FLTV'])[0]
    if name[0] == 'i':
        return struct.unpack('<i', fields['INTV'])[0]
    return string(fields.get('STRV', b''))


def clean(text):
    """One line of game text for the data file: printable cp1252, at most MAX_TEXT bytes."""
    text = ' '.join(''.join(c if ord(c) >= 32 else ' ' for c in text).split())
    raw = text.encode('cp1252', 'replace')[:MAX_TEXT]
    return raw.decode('cp1252')


def ini_levels(data_files):
    """{level: sentence} from Morrowind.ini [Level Up] LevelN (OpenMW Fallback Level_Up_LevelN), {} without the ini."""
    from prepare_chargen import ini_sections
    for parent in (Path(data_files), Path(data_files).parent):
        for p in parent.iterdir() if parent.is_dir() else ():
            if p.name.casefold() == 'morrowind.ini':
                section = ini_sections(p.read_bytes().decode('cp1252', 'replace')).get('level up', {})
                return {n: clean(section['level%d' % n]) for n in LEVELS if section.get('level%d' % n)}
    return {}


def settings_text(kinds, levels, sound):
    lines = ['AWLU1']
    for name in SETTINGS:
        value = gmst_value(kinds, name)
        lines.append('set %s %s' % (name, ('%.6g' % value) if name[0] == 'f' else '%d' % value))
    for index in range(27):
        fields = kinds['SKIL'].get(index)
        if fields is None or len(fields.get('SKDT', b'')) != 24:
            raise ValueError('Missing or short skill record %d' % index)
        attribute, special, *use = struct.unpack('<ii4f', fields['SKDT'])
        lines.append('skill %d %d %d %s' % (index, attribute, special, ' '.join('%.6g' % u for u in use)))
    if sound:
        lines.append('sound skillraise ' + sound)
    for name in TEXTS:
        try:
            value = clean(gmst_value(kinds, name))
        except ValueError:
            continue
        if value:
            lines.append('text %s %s' % (name, value))
    for level in sorted(levels):
        lines.append('level %d %s' % (level, levels[level]))
    return '\n'.join(lines) + '\n'


# Resting and waiting (REST-WAIT-59, docs/RESTING.md; rules of OpenMW 0.51 mwgui/waitdialog.cpp, mwworld/worldimp.cpp
# canRest, mwmechanics/actors.cpp restoreDynamicStats, mechanicsmanagerimp.cpp sleepInBed/isOwned).
REST_SETTINGS = ('fRestMagicMult', 'fEndFatigueMult', 'fFatigueReturnBase', 'fFatigueReturnMult', 'fSleepRandMod',
                 'fSleepRestMod', 'fEncumbranceStrMult')
REST_TEXTS = ('sNotifyMessage1', 'sNotifyMessage2', 'sNotifyMessage64', 'sRestIllegal', 'sRestMenu3', 'sRestMenu2',
              'sRest', 'sWait', 'sUntilHealed', 'sSleepInterrupt')
NO_SLEEP = 0x04            # CELL DATA flags: sleeping is illegal here without a bed
STUNTED_MAGICKA = 136      # the magic effect that stops magicka coming back while resting


def rest_text(raw, kinds):
    """levelup/rest.txt (AWRS1): the rest settings and lines, the cells where sleeping is illegal ("nosleep X Y" for an
    exterior grid cell, "nosleepi ID" for an interior, the ID folded), the regions whose wilderness rest can be cut
    short ("sleepregion LIST NAME", the region's display name), the beds with an owner ("bed REF RANK|FACTION|GLOBAL|OWNER",
    ids may hold spaces, '-' for an empty field; the Morrowind.esm reference number is its stable id, tools/ref_identity.py)
    and the birthsigns whose ability stunts magicka ("stunted ID")."""
    from mwad.audit import records, subrecords, string
    lines = ['AWRS1']
    for name in REST_SETTINGS:
        lines.append('set %s %.6g' % (name, gmst_value(kinds, name)))
    for name in REST_TEXTS:
        try:
            value = clean(gmst_value(kinds, name))
        except ValueError:
            continue
        if value:
            lines.append('text %s %s' % (name, value))
    beds_script, spells, regions, signs = set(), {}, [], {}
    for tag, flags, payload in records(raw):
        if flags & 0x20 or tag not in ('ACTI', 'SPEL', 'BSGN', 'REGN', 'CELL'):
            continue
        fields = list(subrecords(payload))
        f = dict(fields)
        if 'DELE' in f:
            continue
        if tag == 'ACTI' and string(f.get('SCRI', b'')).casefold().startswith('bed'):
            beds_script.add(string(f['NAME']).casefold())
        elif tag == 'SPEL':
            spells[string(f['NAME']).casefold()] = [struct.unpack_from('<H', v)[0] for k, v in fields if k == 'ENAM']
        elif tag == 'BSGN':
            signs[string(f['NAME']).casefold()] = [string(v).casefold() for k, v in fields if k == 'NPCS']
        elif tag == 'REGN' and f.get('BNAM') and string(f['BNAM']):
            regions.append((string(f['BNAM']), string(f.get('FNAM', b''))))
    for sign, powers in sorted(signs.items()):
        if any(STUNTED_MAGICKA in spells.get(p, ()) for p in powers):
            lines.append('stunted ' + sign)
    for sleep_list, name in sorted(regions):
        if name:
            lines.append('sleepregion %s %s' % (sleep_list.casefold(), name))
    from prepare_focus import cells_of
    for tag, flags, payload in records(raw):
        if tag != 'CELL' or flags & 0x20:
            continue
        head = {}
        for k, v in subrecords(payload):
            if k == 'FRMR':
                break
            head.setdefault(k, v)
        data = head.get('DATA', b'')
        if len(data) == 12 and struct.unpack('<I', data[:4])[0] & NO_SLEEP:
            cell_flags, x, y = struct.unpack('<Iii', data)
            name = string(head.get('NAME', b''))
            lines.append(('nosleepi ' + name.casefold()) if cell_flags & 1 else 'nosleep %d %d' % (x, y))
    for _, _, _, _, refs in cells_of(raw):
        for ref in refs:
            base = string(ref.get('NAME', b'')).casefold()
            if base not in beds_script or 'DELE' in ref:
                continue
            owner = string(ref.get('ANAM', b'')).casefold() or '-'
            faction = string(ref.get('CNAM', b'')).casefold() or '-'
            rank = struct.unpack('<i', ref['INDX'])[0] if len(ref.get('INDX', b'')) == 4 else -2
            glob = string(ref.get('BNAM', b'')).casefold() or '-'
            if owner == '-' and faction == '-':
                continue
            if '|' in owner + faction + glob:
                continue
            lines.append('bed %d %d|%s|%s|%s' % (ref['number'], rank, faction, glob, owner))
    return '\n'.join(lines) + '\n'


def picture(raw, palette, size):
    """A DDS picture scaled to size over black and put on the game palette (AWI1, as tools/prepare_icons.py
    writes)."""
    from prepare_icons import awi, premultiplied, rgba
    rgb, _ = premultiplied(rgba(raw), size)
    return awi(rgb, palette, size)


def prepare(data_files, id1):
    from mwad.audit import BSA, string
    from mwad.paths import child_ci, resolve_data_files
    from npc_geometry import Assets
    from prepare_combat import convert_wav
    data = resolve_data_files(Path(data_files))
    id1 = Path(id1)
    kinds = load(child_ci(data, 'Morrowind.esm'))
    assets = Assets(data, BSA(child_ci(data, 'Morrowind.bsa')))
    (id1 / 'levelup').mkdir(parents=True, exist_ok=True)
    report = {'pictures': {}, 'held': {}}
    sound = None
    record = kinds['SOUN'].get('skillraise')
    if record:
        source = 'sound/' + string(record['FNAM']).replace('\\', '/').casefold()
        try:
            (id1 / 'sound/levelup').mkdir(parents=True, exist_ok=True)
            seconds = convert_wav(assets.read(source), id1 / 'sound/levelup/skillraise.wav')
            sound = 'levelup/skillraise.wav'
            report['sound'] = {'record': 'skillraise', 'source': source, 'seconds': round(seconds, 3)}
        except (KeyError, OSError, ValueError) as error:
            report['held']['sound'] = str(error)
    palette = (id1 / 'gfx/palette.lmp').read_bytes() if (id1 / 'gfx/palette.lmp').is_file() else b''
    if len(palette) != 768:
        report['held']['pictures'] = 'no game palette in the image yet'
    for name in PICTURES if len(palette) == 768 else ():
        source = 'textures/levelup/%s.dds' % name
        try:
            raw = picture(assets.read(source), palette, PICTURE)
        except (KeyError, OSError, ValueError) as error:
            report['held'][name] = str(error)
            continue
        (id1 / 'levelup' / (name + '.awi')).write_bytes(raw)
        report['pictures'][name] = {'source': source, 'sha256': hashlib.sha256(raw).hexdigest()}
    for source in COIN_SOURCES if len(palette) == 768 else ():
        try:
            raw = picture(assets.read(source), palette, (COIN, COIN))
        except (KeyError, OSError, ValueError) as error:
            report['held']['coin:' + source] = str(error)
            continue
        (id1 / 'levelup/coin.awi').write_bytes(raw)
        report['coin'] = source
        break
    rest = rest_text(child_ci(data, 'Morrowind.esm').read_bytes(), kinds)
    (id1 / 'levelup/rest.txt').write_bytes(rest.encode('cp1252'))
    report['rest'] = {'lines': rest.count('\n'), 'no_sleep_cells': rest.count('\nnosleep'),
                      'owned_beds': rest.count('\nbed '), 'sleep_regions': rest.count('\nsleepregion ')}
    levels = ini_levels(data_files)
    text = settings_text(kinds, levels, sound)
    (id1 / 'levelup/settings.txt').write_bytes(text.encode('cp1252'))
    report['settings'] = {name: gmst_value(kinds, name) for name in SETTINGS}
    report['level_texts'] = len(levels)
    report['settings_sha256'] = hashlib.sha256(text.encode('cp1252')).hexdigest()
    print('Levelling data: %d settings, 27 skills, %d pictures (%d held), %d level texts%s' % (
          len(SETTINGS), len(report['pictures']), len(report['held']), len(levels),
          '' if sound else ', no skill-raise sound'), flush=True)
    return report
