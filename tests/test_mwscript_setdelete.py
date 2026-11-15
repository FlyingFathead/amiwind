# SPDX-License-Identifier: GPL-3.0-only
"""MWSCRIPT-SETDELETE-STOPS-66: SetDelete deletes for good and stops the object's script, as OpenMW 0.51 does
(miscextensions.cpp OpSetDelete, worldimp.cpp deleteObject: the count 0, out of the scene, the local script
removed; undeleteObject: back with its script). Source checks of the engine host (aw_mwhost.c)."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'engine/aga/src'


def body(text, head):
    start = text.index(head)
    return text[start:text.index('\n}\n', start) + 2]


class SetDeleteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.host = (SOURCE / 'aw_mwhost.c').read_text(encoding='utf-8', errors='replace')

    def test_the_opcode_deletes_on_the_world_change_list(self):
        case = self.host[self.host.index('case AWF_SETDELETE:'):]
        case = case[:case.index('return 1;\n    }')]
        self.assertIn('object_set_deleted(ref,numbers[0].i);', case)
        self.assertIn('else host_object(instance,target,numbers[0].i?AWM_DISABLE:AWM_ENABLE,0);', case)  # old table

    def test_delete_is_the_taken_count_and_survives_enable_and_saves(self):
        fn = body(self.host, 'static void object_set_deleted(uint32_t ref,int deleted){')
        # deleted = TAKEN on its row (OpenMW: count 0, as a taken item); the row is saved with the list
        self.assertIn('r->fields|=AW_LEDGER_TAKEN;ledger_place(r);ledger_hide(ref);', fn)
        # its script stops after the frame's run (a script may delete its own object)
        self.assertIn('deleted_pending[deleted_count++]=ref;', fn)
        # undelete: TAKEN goes, shown again unless a script's Disable still holds it
        self.assertIn('r->fields&=~(AW_LEDGER_TAKEN|AW_LEDGER_STOLEN);', fn)
        self.assertIn('if(!(r->fields&AW_LEDGER_DISABLED)){ledger_show(ref);enabled(ref);}', fn)
        # Enable never undoes a deletion (the taken rule)
        enable = self.host[self.host.index('    case AWM_ENABLE:\n        if(r && (r->fields&AW_LEDGER_DISABLED)){'):]
        self.assertIn('if(!(r->fields&AW_LEDGER_TAKEN))ledger_show(ref);', enable[:600])

    def test_the_script_stops_and_is_not_bound_again(self):
        self.assertIn('for(i=0;i<deleted_count;i++)AW_MwvmDetach(deleted_pending[i]);',
                      body(self.host, 'static void deleted_flush(void){'))
        tick = self.host[self.host.index('AW_MwvmTick(dt,player);'):]
        self.assertLess(tick.index('deleted_flush();'), tick.index('leave_now();'))
        attach = body(self.host, 'static int attach_script(uint32_t ref,int script,int flags,int entity,const float origin[3]){')
        self.assertIn('if(object_deleted(ref))return -1;', attach)

    def test_the_bytecode_page_says_so(self):
        doc = (ROOT / 'docs/MWSCRIPT_BYTECODE.md').read_text(encoding='utf-8')
        line = next(l for l in doc.splitlines() if l.startswith('| `SetDelete` |'))
        self.assertIn('its local script stops', line)
        self.assertNotIn('keeps running', line)


if __name__ == '__main__':
    unittest.main()
