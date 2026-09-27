/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "r_local.h"
#include <assert.h>
extern cvar_t aw_depthslop;
extern void R_LeadingEdge(edge_t *);
extern espan_t *span_p;
extern float fv;
int r_bmodelactive;

static int front(float tolerance, int new_is_nearer, int reverse_slope) {
    surf_t list[4];edge_t edge;espan_t spans[4];
    memset(list,0,sizeof list);memset(&edge,0,sizeof edge);
    surfaces=list;span_p=spans;fv=0;aw_depthslop.value=tolerance;
    list[1].key=0x7fffffff;list[1].next=list[1].prev=&list[2];
    list[2].next=list[2].prev=&list[1];list[2].key=10;
    list[3].key=10;list[3].insubmodel=1;
    list[2].d_ziorigin=new_is_nearer ? .01000 : .01002;
    list[3].d_ziorigin=new_is_nearer ? .01002 : .01000;
    list[3].d_zistepu=reverse_slope ? -.000001 : .000001;
    edge.surfs[1]=3;edge.u=0xFFFFF;
    R_LeadingEdge(&edge);
    return list[1].next==&list[3];
}
int main(void) {
    /* Old 1% band confuses a 0.2% separation with a tie and uses slope. */
    assert(!front(.01,1,1));assert(front(.01,0,0));
    assert(front(.00001,1,1));assert(front(.00001,1,0));
    assert(!front(.00001,0,1));assert(!front(.00001,0,0));
    puts("nearby depth ordering survives both slopes and insertion orders");
    return 0;
}
