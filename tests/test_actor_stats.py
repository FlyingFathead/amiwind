# SPDX-License-Identifier: GPL-3.0-only
"""Every being's stats (ACTOR-STATS-ALL-61, docs/ACTOR_STATE.md "Every being's stats"): the builder's squeezed stat
entries (tools/actor_stats.py) on a small synthetic game data set (a stored-stat NPC, an auto-calculated NPC, an NPC
without AIDT, a creature; no game data in the repo), the area tables' AWS1 section (tools/prepare_area_tables.py), and
the engine's aw_stats.c natively on it: the record types' fields kept as they are, the auto-calculated NPC derived as
the builder's autocalculation does, a creature's skill by specialization, the defaults, and "no such stat" by kind."""
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src'), str(ROOT / 'tests')]

import actor_stats as ast  # noqa: E402
import prepare_combat  # noqa: E402
from test_actorstate import master_bytes, record, sub, aidt, npcs, build as build_awm  # noqa: E402


def extra_records():
    """Beside test_actorstate's set: an NPC without AIDT, with a faction, services and gold; a second auto-calculated
    NPC at a higher level (female); a creature with a long attack table."""
    npdt = struct.pack('<h8B27BB3HBBbBi', 7, *range(60, 68), *range(20, 47), 0, 70, 30, 110, 41, 3, 2, 0, 0)
    out = [record('FACT', sub('NAME', 'Test Guild')),
           record('BSGN', sub('NAME', 'Test Sign'), npcs('test spell'), npcs('other spell')),
           record('NPC_', sub('NAME', 'quiet_npc'), sub('RNAM', 'Test Race'), sub('CNAM', 'Test Class'),
                  sub('ANAM', 'Test Guild'), sub('NPDT', npdt), sub('FLAG', struct.pack('<I', 0x400 * 2))),
           record('NPC_', sub('NAME', 'auto_high'), sub('RNAM', 'Test Race'), sub('CNAM', 'Test Class'),
                  sub('NPDT', struct.pack('<hBBb3si', 17, 45, 4, 2, b'\0' * 3, 250)), sub('FLAG', struct.pack('<I', 0x19)),
                  sub('AIDT', struct.pack('<HBBB3sI', 300, 0, 20, 100, b'\0' * 3, 0x1234)), npcs('test spell')),
           record('CREA', sub('NAME', 'test_ghost'),
                  sub('NPDT', struct.pack('<24i', 2, 12, *range(30, 38), 400, 120, 300, 900, 70, 80, 90,
                                          5, 25, 6, 30, 7, 350, 0)),
                  sub('FLAG', struct.pack('<I', 0x8 | 0x40 | (2 << 10))), aidt(10, 90, 0, 0), npcs('other spell'),
                  npcs('race power'))]
    return b''.join(out)


HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_stats.h"
int main(int argc,char **argv){
    FILE *f=fopen(argv[1],"rb");static unsigned char s[65536],t[65536];long n=(long)fread(s,1,sizeof(s),f),tn=0;
    int i,k,sp[96];
    fclose(f);
    if(strcmp(argv[2],"-")){f=fopen(argv[2],"rb");tn=(long)fread(t,1,sizeof(t),f);fclose(f);}
    for(i=3;i<argc;i++){
        aw_stat_block_t b;uint32_t h=AW_StatIdHash(argv[i]);int got=AW_StatDecode(s,n,h,tn?t:NULL,tn,&b);
        printf("%s found %d kind %d mask %d\n",argv[i],got,b.kind,b.mask);
        for(k=0;k<AWS_STATS;k++)if(AW_StatName(k)[0])printf("%s %s %d %d\n",argv[i],AW_StatName(k),AW_StatHas(&b,k),AW_StatRead(&b,k));
        {int m=AW_StatSpells(&b,sp,96),j;printf("%s spells %d race %d",argv[i],m,b.race_spells);for(j=0;j<m;j++)printf(" %d",sp[j]);printf("\n");}
    }
    printf("missing %d\n",AW_StatSectionFind(s,n,AW_StatIdHash("nobody"))!=0);
    return 0;
}
'''

IDS = ('Fixed_NPC', 'auto_npc', 'quiet_npc', 'auto_high', 'test_rat', 'test_ghost')


def data():
    """(records, gmst, spell rows) of the synthetic masters."""
    tmp = Path(tempfile.mkdtemp(prefix='aw-stats-'))
    try:
        (tmp / 'Morrowind.esm').write_bytes(master_bytes() + extra_records())
        recs, gmst = ast.master_records(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    _prog, awm, _ = build_awm()
    return recs, gmst, ast.spell_rows(awm)


class BuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recs, cls.gmst, cls.spells = data()
        cls.voc = ast.read_vocabulary(ast.write_vocabulary(cls.recs, cls.gmst))
        cls.section, cls.report = ast.section([ast.name_hash(i) for i in IDS], cls.voc, cls.spells)

    def entry(self, ident):
        n = struct.unpack_from('>H', self.section, 4)[0]
        for i in range(n):
            h, off = struct.unpack_from('>IH', self.section, ast.SECTION_HEAD + 6 * i if hasattr(ast, 'SECTION_HEAD')
                                         else 66 + 6 * i)
            if h == ast.name_hash(ident):
                return ast.decode(self.section, off)[0]
        return None

    def test_kinds_and_sizes(self):
        self.assertEqual(self.report['entries'], 6)
        self.assertEqual((self.report['stored'], self.report['auto'], self.report['creatures']), (2, 2, 2))
        auto = ast.encode(ast.actor('NPC_', self.recs['NPC_']['auto_npc'], self.spells), 0, 0)
        # kind and mask; level, disposition, reputation; flags and blood; race and class; gold 7
        self.assertEqual(len(auto), 3 + 4 + 2 + 2 + 4)
        self.assertEqual(self.entry('auto_npc')['mask'], ast.P_BASE | ast.P_FLAGS | ast.P_RACE | ast.P_GOLD)

    def test_stored_values_as_recorded(self):
        e = self.entry('Fixed_NPC')
        self.assertEqual(e['kind'], ast.KIND_STORED)
        self.assertEqual((e['level'], e['attributes'], e['skills']), (5, list(range(50, 58)), list(range(10, 37))))
        self.assertEqual(e['dynamic'], [50, 20, 100])
        self.assertEqual((e['disposition'], e['reputation']), (40, 1))
        self.assertEqual(e['ai'], (30, 90, 10, 5))
        self.assertEqual(e['gold'], 30)

    def test_no_aidt_and_faction(self):
        e = self.entry('quiet_npc')
        self.assertFalse(e['mask'] & ast.P_AI)
        self.assertEqual(e['faction'], ast.name_hash('Test Guild'))
        self.assertEqual(e['blood'], 2)
        self.assertNotIn('gold', e)

    def test_creature_fields(self):
        e = self.entry('test_ghost')
        self.assertEqual(e['kind'], ast.KIND_CREATURE)
        self.assertEqual((e['type'], e['level'], e['soul'], e['cms']), (2, 12, 900, [70, 80, 90]))
        self.assertEqual(e['attacks'], [5, 25, 6, 30, 7, 350])
        self.assertEqual(len(e['spells']), 2)
        self.assertNotIn(ast.NO_SPELL, e['spells'])

    def test_services_and_hello_wide(self):
        e = self.entry('auto_high')
        self.assertEqual(e['ai'], (300, 0, 20, 100))      # hello is 16 bits in AIDT: kept whole
        self.assertEqual(e['services'], 0x1234)

    def test_area_record_rows_point_at_their_entries(self):
        """Every placed actor's row in its area record carries the offset of its own entry (the direct lookup), and
        the record ends with the AWS1 section named by its last 8 bytes."""
        import prepare_area_tables as pat
        refs = {100 + i: ast.name_hash(ident) for i, ident in enumerate(IDS)}
        refs[200] = ast.name_hash('nobody placed')         # an actor with no record: no offset
        rows = [struct.pack('<BBBBIiiifi', ord('A'), 0, 3, 0, ref, 0, 0, 0, 0.0, 0) + b'Someone'.ljust(36, b'\0') +
                bytes(32) for ref in refs]
        rows.append(struct.pack('<BBBBIiiifi', ord('D'), 0, 0, 0, 300, 0, 0, 0, 0.0, 0) + bytes(36) + bytes(32))

        def make(references):
            block, report = ast.section([refs[r] for r in references], self.voc, self.spells)
            offsets = report.pop('offsets')
            report['ref_offsets'] = {r: offsets[refs[r]] for r in references if refs[r] in offsets}
            report['ref_actb'] = {r: 1000 + r for r in report['ref_offsets']}     # the actor table rows
            return block, report
        record, s = pat.area(rows, {}, {}, {}, {}, {}, {}, stats=make)
        self.assertEqual(record[-4:], b'AWS1')
        at = struct.unpack_from('<I', record, len(record) - 8)[0]
        sec = record[at:len(record) - 8]
        self.assertEqual(sec[:4], b'AWS1')
        self.assertEqual(s['stats_entries'], len(IDS))
        n = struct.unpack_from('>H', sec, 4)[0]
        by_offset = {struct.unpack_from('>IH', sec, 66 + 6 * i)[1]: struct.unpack_from('>I', sec, 66 + 6 * i)[0]
                     for i in range(n)}
        placed = [record[16 + 96 * i: 16 + 96 * (i + 1)] for i in range(len(rows))]
        for row in placed:
            ref, off = struct.unpack_from('<I', row, 4)[0], ast.row_offset(row)
            if ref in (200, 300):
                self.assertEqual(off, 0, ref)
                continue
            self.assertEqual(by_offset[off], refs[ref], ref)
            self.assertEqual(ast.row_actb(row), 1000 + ref, ref)
            self.assertEqual(row[64], 0)                       # the id stays empty
            self.assertEqual(ast.decode(sec, off)[0]['kind'], self.entry(IDS[ref - 100])['kind'])

    def test_levelled_expanded(self):
        voc = dict(self.voc, levelled={1: [ast.name_hash('test_rat'), 2], 2: [ast.name_hash('test_ghost')]})
        _s, rep = ast.section([1], voc, self.spells)
        self.assertEqual((rep['entries'], rep['creatures']), (2, 2))


@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recs, cls.gmst, cls.spells = data()
        voc = ast.read_vocabulary(ast.write_vocabulary(cls.recs, cls.gmst))
        section, _ = ast.section([ast.name_hash(i) for i in IDS], voc, cls.spells)
        cls.tmp = Path(tempfile.mkdtemp(prefix='aw-stats-c-'))
        (cls.tmp / 's.aws').write_bytes(section)
        (cls.tmp / 'h.c').write_text(HARNESS, encoding='utf-8')
        src = ROOT / 'engine/aga/src'
        built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wno-unused-parameter', '-Wshadow',
                                '-fsanitize=undefined,address', '-fno-sanitize-recover=all', '-I' + str(src),
                                str(cls.tmp / 'h.c'), str(src / 'aw_stats.c'), '-lm', '-o', str(cls.tmp / 'h')],
                               capture_output=True, text=True)
        assert built.returncode == 0, built.stdout + built.stderr
        r = subprocess.run([str(cls.tmp / 'h'), str(cls.tmp / 's.aws'), '-', *IDS], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        cls.lines = r.stdout.splitlines()
        # DRY: the slim area section with the shared record's tables reads the same values as the whole section
        tables = ast.shared_tables(voc)
        slim, _ = ast.section([ast.name_hash(i) for i in IDS], voc, cls.spells, shared=tables)
        shared, _ = ast.shared_section([], voc, cls.spells, tables)
        (cls.tmp / 'slim.aws').write_bytes(slim)
        (cls.tmp / 'shared.aws').write_bytes(shared)
        r = subprocess.run([str(cls.tmp / 'h'), str(cls.tmp / 'slim.aws'), str(cls.tmp / 'shared.aws'), *IDS],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        cls.slim_lines = r.stdout.splitlines()
        cls.slim_bytes, cls.whole_bytes = len(slim), len(section)
        r = subprocess.run([str(cls.tmp / 'h'), str(cls.tmp / 'slim.aws'), '-', 'Fixed_NPC'], capture_output=True,
                           text=True)
        cls.slim_alone = r.stdout.splitlines()
        cls.values, cls.has = {}, {}
        for line in cls.lines:
            w = line.split()
            if len(w) == 4 and w[0] in IDS:
                cls.has[(w[0], w[1])] = int(w[2]); cls.values[(w[0], w[1])] = int(w[3])

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    ATTR = ('strength', 'intelligence', 'willpower', 'agility', 'speed', 'endurance', 'personality', 'luck')
    SKILLS = ('block', 'armorer', 'mediumarmor', 'heavyarmor', 'bluntweapon', 'longblade', 'axe', 'spear', 'athletics',
              'enchant', 'destruction', 'alteration', 'illusion', 'conjuration', 'mysticism', 'restoration', 'alchemy',
              'unarmored', 'security', 'sneak', 'acrobatics', 'lightarmor', 'shortblade', 'marksman', 'mercantile',
              'speechcraft', 'handtohand')

    def v(self, ident, name):
        return self.values[(ident, name)]

    def test_slim_section_reads_the_same_with_the_shared_record(self):
        self.assertEqual(self.slim_lines, self.lines)
        self.assertLess(self.slim_bytes, self.whole_bytes)
        self.assertIn('Fixed_NPC found 0 kind 0 mask 0', self.slim_alone)   # no tables: not found, never guessed

    def test_all_found(self):
        for ident in IDS:
            self.assertIn('%s found 1' % ident, '\n'.join(self.lines))
        self.assertIn('missing 0', self.lines)

    def test_stored_npc_reads_its_record(self):
        self.assertEqual([self.v('Fixed_NPC', a) for a in self.ATTR], list(range(50, 58)))
        self.assertEqual([self.v('Fixed_NPC', s) for s in self.SKILLS], list(range(10, 37)))
        self.assertEqual([self.v('Fixed_NPC', d) for d in ('health', 'magicka', 'fatigue', 'level')], [50, 20, 100, 5])
        self.assertEqual([self.v('Fixed_NPC', d) for d in ('disposition', 'reputation')], [40, 1])
        self.assertEqual([self.v('Fixed_NPC', d) for d in ('hello', 'fight', 'flee', 'alarm')], [30, 90, 10, 5])
        self.assertEqual(self.v('Fixed_NPC', 'gold'), 30)
        self.assertEqual(self.v('Fixed_NPC', 'rank'), -1)    # no faction: OpenMW getFactionRank -1

    def test_auto_npc_derived_as_the_builder(self):
        for ident in ('auto_npc', 'auto_high'):
            fields = self.recs['NPC_'][ident.casefold()]
            level = struct.unpack_from('<h', dict(fields)['NPDT'])[0]
            attributes, skills, health = prepare_combat.autocalc(self.recs, fields, level)
            self.assertEqual([self.v(ident, a) for a in self.ATTR], attributes, ident)
            self.assertEqual([self.v(ident, s) for s in self.SKILLS], skills, ident)
            self.assertEqual(self.v(ident, 'health'), int(health), ident)
            self.assertEqual(self.v(ident, 'fatigue'), attributes[0] + attributes[2] + attributes[3] + attributes[5])
            self.assertEqual(self.v(ident, 'magicka'), int(attributes[1] * self.gmst['fnpcbasemagickamult']))
            self.assertEqual(self.has[(ident, 'block')], 1)

    def test_creature_skill_by_specialization(self):
        # the synthetic skill i has specialization i % 3: combat 70, magic 80, stealth 90
        for i, s in enumerate(self.SKILLS):
            self.assertEqual(self.v('test_ghost', s), (70, 80, 90)[i % 3], s)
            self.assertEqual(self.has[('test_ghost', s)], 0)       # not stored: read by the rule
        self.assertEqual([self.v('test_ghost', x) for x in ('combat', 'magic', 'stealth', 'soul', 'type')],
                         [70, 80, 90, 900, 2])
        self.assertEqual(self.v('test_ghost', 'thrustmax'), 350)
        self.assertEqual(self.v('test_ghost', 'blood'), 2)

    def test_lacking_reads_zero_and_defaults(self):
        self.assertEqual([self.v('quiet_npc', d) for d in ('hello', 'fight', 'flee', 'alarm')], [30, 30, 30, 0])
        self.assertEqual(self.v('quiet_npc', 'gold'), 0)
        self.assertEqual(self.v('quiet_npc', 'rank'), 2)
        for x in ('soul', 'combat', 'chopmin', 'type'):
            self.assertEqual((self.has[('Fixed_NPC', x)], self.v('Fixed_NPC', x)), (0, 0), x)
        for x in ('disposition', 'reputation'):
            self.assertEqual((self.has[('test_rat', x)], self.v('test_rat', x)), (0, 0), x)
        self.assertEqual(self.v('test_rat', 'rank'), -1)
        self.assertEqual(self.v('auto_high', 'hello'), 300)
        self.assertEqual(self.v('auto_high', 'services'), 0x1234)

    def test_spells_own_then_race(self):
        line = [x for x in self.lines if x.startswith('Fixed_NPC spells')][0].split()
        n, race = int(line[2]), int(line[4])
        self.assertEqual((n, race), (3, 1))                  # test spell, auto spell; the race's power
        self.assertEqual(int(line[-1]), self.spells['race power'])
        ghost = [x for x in self.lines if x.startswith('test_ghost spells')][0].split()
        self.assertEqual([int(x) for x in ghost[5:]], [self.spells['other spell'], self.spells['race power']])


LIVE_HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_actorstate.h"
#include "aw_stats.h"
static unsigned char *file;static long size;
static int rd(void *c,uint32_t off,void *out,uint32_t n){(void)c;if(off+n>(uint32_t)size)return 1;memcpy(out,file+off,n);return 0;}
static long load(const char *path,unsigned char *buf,long cap){FILE *f=fopen(path,"rb");long n=(long)fread(buf,1,cap,f);fclose(f);return n;}
int main(int argc,char **argv){
    static unsigned char slim[65536],shared[65536];aw_actorstate_io_t io={rd,NULL};FILE *f=fopen(argv[1],"rb");
    long sn=load(argv[2],slim,sizeof(slim)),hn=load(argv[3],shared,sizeof(shared));int i,k;unsigned long c[2];
    fseek(f,0,SEEK_END);size=ftell(f);fseek(f,0,SEEK_SET);file=malloc(size);if(fread(file,1,size,f)!=(size_t)size)return 2;fclose(f);
    if(!AW_ActorStateOpen(file,(uint32_t)size,&io))return 3;
    for(i=4;i<argc;i++){
        aw_stat_block_t b;aw_actor_t *a,*again;int row=AW_ActorFind(argv[i]);
        if(!AW_StatDecode(slim,sn,AW_StatIdHash(argv[i]),shared,hn,&b))return 4;
        a=AW_ActorFromStats(500+i,row,&b);again=AW_ActorFromStats(500+i,row,&b);
        printf("%s kind %d flags %d same %d",argv[i],a->kind,a->record_flags,a==again);
        for(k=0;k<44;k++)printf(" %d",(int)AW_ActorStat(a,k));
        printf("\n");
        printf("%s block",argv[i]);
        for(k=0;k<44;k++)printf(" %d",k>=AWS_HELLO && k<=AWS_ALARM?(k==AWS_HELLO && AW_StatRead(&b,k)>255?255:AW_StatRead(&b,k)):AW_StatRead(&b,k));
        printf("\n");
    }
    AW_ActorStatsCounts(c);printf("counts %lu %lu\n",c[0],c[1]);
    {int sp[16],n=AW_StatRaceSpells(shared,hn,AW_StatIdHash("test race"),sp,16),j;printf("race spells %d",n);
     for(j=0;j<n;j++){printf(" %d",sp[j]);}
     printf("\n");
     n=AW_StatBirthSpells(shared,hn,AW_StatIdHash("TEST SIGN"),sp,16);printf("birth spells %d",n);
     for(j=0;j<n;j++){printf(" %d",sp[j]);}
     printf("\n");
     printf("no birth %d\n",AW_StatBirthSpells(shared,hn,AW_StatIdHash("nobody"),sp,16));}
    AW_ActorStatsSwitch(0);
    {int row=AW_ActorFind("auto_npc");aw_actor_t *a=AW_ActorGet(900,row,1);
     AW_ActorStatsCounts(c);printf("off %lu %lu attr %d\n",c[0],c[1],(int)AW_ActorStat(a,0));}
    return 0;
}
'''


@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class LiveRecordTests(unittest.TestCase):
    """The area load's live records (AW_ActorFromStats): every stat the block reads, made once, kept as it is."""

    def test_live_records_from_area_blocks(self):
        recs, gmst, spells = data()
        voc = ast.read_vocabulary(ast.write_vocabulary(recs, gmst))
        tables = ast.shared_tables(voc)
        ids = ('Fixed_NPC', 'auto_npc', 'test_rat')
        slim, _ = ast.section([ast.name_hash(i) for i in ids], voc, spells, shared=tables)
        shared, _ = ast.shared_section([], voc, spells, tables)
        _prog, awm, _ = build_awm()
        tmp = Path(tempfile.mkdtemp(prefix='aw-stats-live-'))
        try:
            for name, data_ in (('a.awm', awm), ('slim.aws', slim), ('shared.aws', shared), ('h.c', LIVE_HARNESS.encode())):
                (tmp / name).write_bytes(data_)
            src = ROOT / 'engine/aga/src'
            built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wno-unused-parameter', '-Wshadow',
                                    '-fsanitize=undefined,address', '-fno-sanitize-recover=all', '-I' + str(src),
                                    str(tmp / 'h.c'), str(src / 'aw_actorstate.c'), str(src / 'aw_stats.c'), '-lm',
                                    '-o', str(tmp / 'h')], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            r = subprocess.run([str(tmp / 'h'), str(tmp / 'a.awm'), str(tmp / 'slim.aws'), str(tmp / 'shared.aws'),
                                *ids], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            lines = r.stdout.splitlines()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        for ident in ids:
            live = [x for x in lines if x.startswith(ident + ' kind')][0].split()
            block = [x for x in lines if x.startswith(ident + ' block')][0].split()
            self.assertEqual(live[6], '1', ident)                      # the second call returns the same record
            # the live record reads what the block reads (disposition 0 for a creature on both sides)
            self.assertEqual(live[7:], block[2:], ident)
        self.assertIn('kind 1', [x for x in lines if x.startswith('test_rat kind')][0])
        self.assertIn('counts 3 0', lines)
        self.assertIn('off 3 1', ' '.join(lines))
        # the player's spells at creation: the race's powers (race rows) and the birthsign's spells (BSG1 rows)
        self.assertIn('race spells 1 %d' % spells['race power'], lines)
        self.assertIn('birth spells 2 %d %d' % (spells['test spell'], spells['other spell']), lines)
        self.assertIn('no birth 0', lines)


if __name__ == '__main__':
    unittest.main()
