# SPDX-License-Identifier: GPL-3.0-only
"""MWSCRIPT-TICK-SHARE-66: the scripts' share of the frame can be read (chim spikes report, mwscript status), and the
cheap fixes of the scripts' engine ticks keep their behaviour (source checks; the timing has no effect on play)."""
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'engine/aga/src'


def read(name):
    return (SOURCE / name).read_text(encoding='utf-8', errors='replace')


def body(text, head):
    start = text.index(head)
    return text[start:text.index('\n}\n', start) + 2]


class TickShareTests(unittest.TestCase):
    def test_every_frame_adds_to_the_slot_totals_and_the_report_gives_shares(self):
        spike = read('aw_spike.c')
        frame = body(spike, 'void AW_SpikeFrame (void)')
        # accumulated before the early return of spikes off, with the frame count the shares divide by
        add = frame.index('slot_total[i] += frame_time[i];')
        self.assertLess(frame.index('wait_frames_time += dt;'), add)
        self.assertLess(add, frame.index('if (threshold <= 0 || dt <= 0)'))
        report = body(spike, 'void AW_SpikeReport (void)')
        self.assertIn('share of all frames: %-9s %ld ms, %ld.%ld %%', report)
        self.assertIn('memset (slot_total, 0, sizeof(slot_total));', report)

    def test_interpreter_and_host_call_times_in_mwscript_status(self):
        vm = read('aw_mwvm.c')
        tick = body(vm, 'void AW_MwvmTick(float dt,const float player[3]){')
        self.assertIn('t0=aw_mwvm_clock?aw_mwvm_clock():0;', tick)
        self.assertIn('vm.stats.tick_time+=aw_mwvm_clock()-t0;', tick)
        self.assertIn('vm.stats.host_time+=aw_mwvm_clock()-c0;', vm)
        self.assertIn('double tick_time,host_time;', read('aw_mwvm.h'))
        host = read('aw_mwhost.c')
        self.assertIn('aw_mwvm_clock=Sys_FloatTime;', host)
        self.assertIn('time: interpreter with its calls %ld ms, of it host calls %ld ms (%lu calls)', host)


class CheapFixTests(unittest.TestCase):
    def test_edict_of_ref_tries_the_sorted_table_first(self):
        fn = body(read('aw_mwhost.c'), 'static int edict_of_ref(uint32_t key){')
        self.assertIn('entity_of_reference(key)', fn)
        self.assertIn('if(t && !t->free && ref_of_edict(t)==key)return i;', fn)
        self.assertIn('for(i=1;i<sv.num_edicts;i++)', fn)   # the scan stays for an edict the table has not met

    def test_the_two_fields_are_found_once_per_game_code(self):
        host = read('aw_mwhost.c')
        self.assertNotIn('GetEdictFieldValue(e,"aw_ref")', host)
        self.assertNotIn('GetEdictFieldValue(e,"aw_source_id")', host)
        fn = body(host, 'static eval_t *field_of(edict_t *e,int which){')
        self.assertIn('{"aw_ref","aw_source_id"}', fn)
        self.assertIn('if(loaded[which]!=(const void *)pr_fielddefs){', fn)
        # the same address GetEdictFieldValue gives (pr_edict.c)
        self.assertIn('(eval_t *)((char *)&e->v+ofs[which]*4)', fn)
        self.assertIn('return (eval_t *)((char *)&ed->v + def->ofs*4);', read('pr_edict.c'))

    def test_fights_read_back_from_the_fighter_list(self):
        fn = body(read('aw_mwhost.c'), 'static void actors_from_fights(void){')
        self.assertIn('n=AW_CombatFighterEdicts(fighting,AW_COMBAT_FIGHTERS_MAX);', fn)
        self.assertIn('qsort(fighting,', fn)        # the edict order the scan had
        self.assertNotIn('for(i=1;i<sv.num_edicts;i++)', fn)
        combat = read('aw_combat.c')
        self.assertIn('int AW_CombatFighterEdicts(edict_t **out,int max) {', combat)
        self.assertIn('#define SLOTS 4', combat)
        self.assertIn('#define AW_COMBAT_FIGHTERS_MAX 16', read('aw_combat.h'))


if __name__ == '__main__':
    unittest.main()
