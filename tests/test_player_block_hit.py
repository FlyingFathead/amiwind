# SPDX-License-Identifier: GPL-3.0-only
"""The compact player START/HIT pair retains original shield key timing."""
from pathlib import Path
import subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
import npc_anim
class Skeleton:
    N=None
    nodes={}
    keys=[]
    events={'idle: start':0.,'idle: stop':2.,'shield: block start':10.,
            'shield: block hit':10.333343505859375,'shield: block stop':11.333343505859375}
class PlayerBlockHit(unittest.TestCase):
    def plan(self,preserve):
        kit,groups=npc_anim.plan(Skeleton(),[('idle',8),('block',5)],player_block_hit=preserve)
        fitted,index=npc_anim.select(groups,{'idle':8,'block':2})
        return kit,fitted,index
    def test_previous_pair_misses_original_hit(self):
        kit,groups,index=self.plan(False);g=groups[1]
        self.assertNotEqual(kit.samples[index[g['base']+1]][1],Skeleton.events['shield: block hit'])
        self.assertEqual(int(g['hit']*(g['count']-1)+.5),0)
    def test_emitted_pair_is_start_exact_hit(self):
        kit,groups,index=self.plan(True);g=groups[1]
        self.assertEqual([kit.samples[index[g['base']+i]][1] for i in range(2)],
                         [Skeleton.events['shield: block start'],Skeleton.events['shield: block hit']])
    def test_actual_runtime_before_hit_at_hit_held_recoil_release(self):
        src=(ROOT/'engine/aga/src/aw_view.c').read_text();a=src.index('static float guard_time;');b=src.index('static int body_fists_ready',a)
        fixture='#include "aw_anim.h"\n#include <stdio.h>\nstatic aw_anim_t body_anim;static int guarding=1;static float shown;\nint AW_CombatGuarding(void){return guarding;}\nfloat AW_CombatBlockShown(void){return shown;}\n'+src[a:b]
        fixture+='\nint main(void){int count;for(count=2;count<=5;count+=3){aw_anim_group_t *g=&body_anim.g[AW_ANIM_BLOCK];float hit;guard_time=0;guarding=1;shown=0;g->base=25;g->count=count;g->present=1;g->step=count==2?.6667f:.2667f;g->x=.250f;hit=g->x*g->step*g->count;printf("%d ",body_block_frame(hit-.001f));printf("%d ",body_block_frame(.001f));printf("%d ",body_block_frame(1));guarding=0;shown=.1f;printf("%d ",body_block_frame(0));shown=0;printf("%d ",body_block_frame(0));}return 0;}\n'
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'fixture.c').write_text(fixture)
            subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-I',str(ROOT/'engine/aga/src'),str(p/'fixture.c'),'-o',str(p/'fixture')],check=True,capture_output=True)
            values=subprocess.check_output([str(p/'fixture')]).decode().split()
        self.assertEqual(values,['25','26','26','26','-1','25','26','26','29','-1'])
    def test_unrelated_samples_and_groups_unchanged(self):
        old,groups,index=self.plan(False);new,other,index2=self.plan(True)
        self.assertEqual(index[:-1],index2[:-1])
        self.assertEqual([s[1] for i,s in enumerate(old.samples) if i!=9],
                         [s[1] for i,s in enumerate(new.samples) if i!=9])
        self.assertEqual(groups[0],other[0])
    def test_all_retained_counts_preserve_hit(self):
        kit,groups=npc_anim.plan(Skeleton(),[('idle',8),('block',5)],player_block_hit=True)
        for count in (2,3,4,5):
            fitted,index=npc_anim.select(groups,{'idle':8,'block':count});g=fitted[1]
            hold=int(g['hit']*(count-1)+.5) if count>2 else 1
            self.assertEqual(kit.samples[index[g['base']+hold]][1],Skeleton.events['shield: block hit'])
    def test_missing_authored_hit_rejected(self):
        class Missing(Skeleton):events={k:v for k,v in Skeleton.events.items() if 'block hit' not in k}
        with self.assertRaises(ValueError):npc_anim.plan(Missing(),[('idle',8),('block',5)],player_block_hit=True)
if __name__=='__main__':unittest.main()
