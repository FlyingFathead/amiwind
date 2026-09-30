/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "r_local.h"
#include <assert.h>
extern espan_t *span_p;
extern edge_t edge_head,edge_tail;
extern int edge_head_u_shift20,edge_tail_u_shift20,current_iv;
extern float fv;
extern void AW_GenerateMeshSpans(void);
static surf_t pool[8];static espan_t spans[100];static edge_t edges[8];
static void setup(void){
 memset(pool,0,sizeof(pool));memset(edges,0,sizeof(edges));surfaces=pool;span_p=spans;
 edge_head_u_shift20=0;edge_tail_u_shift20=20;current_iv=2;fv=2;
 pool[1].key=0x7fffffff;pool[1].spanstate=1;
}
static void edge(int n,int x,int end,int start){
 edges[n].u=x<<20;edges[n].surfs[0]=end;edges[n].surfs[1]=start;
 if(n)edges[n-1].next=&edges[n];else edge_head.next=&edges[n];edges[n].next=&edge_tail;
}
static void check(const int *wanted){
 int pixels[20],i,j,total=0;espan_t *p;
 for(i=0;i<20;i++)pixels[i]=-1;
 for(i=1;i<8;i++)for(p=pool[i].spans;p;p=p->pnext){
  assert(p->v==2 && p->count>0 && p->u>=0 && p->u+p->count<=20);
  for(j=p->u;j<p->u+p->count;j++){assert(pixels[j]==-1);pixels[j]=i;total++;}
 }
 assert(total==20 && span_p-spans<=20);
 for(i=0;i<20;i++)assert(pixels[i]==wanted[i]);
 for(i=1;i<8;i++)assert(!pool[i].spanstate);
}
int main(void){
 int want[20],i;setup();
 /* Same-leaf surfaces cross at x=10 with no mesh boundary there. */
 pool[2].key=pool[3].key=4;pool[2].insubmodel=pool[3].insubmodel=1;
 pool[2].d_ziorigin=2;pool[3].d_ziorigin=1;pool[3].d_zistepu=.1f;
 edge(0,2,0,2);edge(1,4,0,3);edge(2,16,3,0);edge(3,18,2,0);
 AW_GenerateMeshSpans();
 for(i=0;i<20;i++)want[i]=i<2 || i>=18?1:i>=11 && i<16?3:2;
 /* Exact-depth tie at x10 may keep the newly active surface. */
 check(want);
 setup();pool[2].key=3;pool[3].key=4;pool[2].d_ziorigin=.1f;pool[3].d_ziorigin=50;
 edge(0,0,0,2);edge(1,0,0,3);edge(2,20,3,0);edge(3,20,2,0);
 AW_GenerateMeshSpans();for(i=0;i<20;i++)want[i]=2;check(want);
 /* A subpixel sliver whose edges share a pixel emits no span. */
 setup();pool[2].key=1;edge(0,3,0,2);edge(1,3,2,0);
 AW_GenerateMeshSpans();for(i=0;i<20;i++)want[i]=1;check(want);
 return 0;
}
