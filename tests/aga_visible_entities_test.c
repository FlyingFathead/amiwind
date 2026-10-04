/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "r_local.h"
#include <assert.h>
#include <setjmp.h>
int r_framecount=7,cl_numvisedicts;
entity_t *cl_visedicts[MAX_VISEDICTS];
client_state_t cl;
entity_t cl_entities[MAX_EDICTS],cl_static_entities[MAX_STATIC_ENTITIES];
efrag_t cl_efrags[MAX_EFRAGS];
int aw_efrags_used,aw_efrags_peak;
static void *pages[128];
static int page_count,allocations,expected_limit_error;
static jmp_buf limit_error;
void Sys_Error(char *fmt,...){assert(0);}
void Host_Error(char *fmt,...){
 assert(expected_limit_error && strstr(fmt,"leaf-link limit"));
 longjmp(limit_error,1);
}
void *Hunk_AllocName(int bytes,char *name){
 void *memory=calloc(1,bytes);
 assert(memory && !strcmp(name,"efrags") && page_count<128);
 pages[page_count++]=memory;allocations++;return memory;
}
float R_SpriteEntityScale(const entity_t *entity){return 1;}
static void release_hunk(void){
 int i;for(i=0;i<page_count;i++)free(pages[i]);page_count=0;
}
static void visible_capacity(void){
 int i,n=MAX_EDICTS+MAX_STATIC_ENTITIES;
 model_t model;efrag_t *head,*frags=calloc(n,sizeof(*frags));
 entity_t *actors=calloc(n,sizeof(*actors));
 assert(MAX_VISEDICTS>=n && n>256 && frags && actors);
 memset(&model,0,sizeof(model));model.type=mod_alias;
 for(i=0;i<n;i++){
  actors[i].model=&model;frags[i].entity=&actors[i];
  frags[i].leafnext=i+1<n?&frags[i+1]:NULL;
 }
 head=frags;R_StoreEfrags(&head);
 assert(cl_numvisedicts==n && cl_visedicts[n-1]==&actors[n-1]);
 R_StoreEfrags(&head);assert(cl_numvisedicts==n);
 free(frags);free(actors);
}

#define TEST_LEAVES 512
#define TEST_STATICS 128
static mnode_t nodes[TEST_LEAVES-1];
static mleaf_t leaves[TEST_LEAVES];
static mplane_t split;
static model_t world,static_model;
static int next_node;
static mnode_t *tree(int first,int count){
 mnode_t *node;
 if(count==1){leaves[first].contents=CONTENTS_EMPTY;return (mnode_t *)&leaves[first];}
 node=&nodes[next_node++];node->plane=&split;
 node->children[0]=tree(first,count/2);node->children[1]=tree(first+count/2,count/2);
 return node;
}
static void add_static(int index){
 cl_static_entities[index].model=&static_model;
 R_AddEfrags(&cl_static_entities[index]);
}
static void overflow_lifetime(void){
 int i,before;
 assert(TEST_STATICS*TEST_LEAVES==AW_EFRAG_LIMIT && MAX_EFRAGS<TEST_STATICS*TEST_LEAVES);
 split.type=0;split.normal[0]=1;
 world.nodes=tree(0,TEST_LEAVES);world.leafs=leaves;world.numleafs=TEST_LEAVES;
 static_model.type=mod_alias;
 for(i=0;i<3;i++){static_model.mins[i]=-1;static_model.maxs[i]=1;}
 cl.worldmodel=&world;R_ClearEfrags(false);
 for(i=0;i<TEST_STATICS;i++)add_static(i);
 assert(aw_efrags_used==AW_EFRAG_LIMIT && aw_efrags_capacity==AW_EFRAG_LIMIT);
 assert(page_count==(AW_EFRAG_LIMIT-MAX_EFRAGS)/AW_EFRAG_PAGE_LINKS);
 cl_numvisedicts=0;r_framecount++;
 R_StoreEfrags(&leaves[TEST_LEAVES-1].efrags);
 assert(cl_numvisedicts==TEST_STATICS);
 assert(cl_visedicts[0]==&cl_static_entities[TEST_STATICS-1]);

 expected_limit_error=1;before=allocations;
 if(!setjmp(limit_error)){add_static(TEST_STATICS);assert(0 && "hard cap must fail explicitly");}
 expected_limit_error=0;
 assert(allocations==before && aw_efrags_used==AW_EFRAG_LIMIT);
 assert(!cl_static_entities[TEST_STATICS].efrag);
 R_RemoveEfrags(&cl_static_entities[0]);
 assert(aw_efrags_used==AW_EFRAG_LIMIT-TEST_LEAVES);
 add_static(TEST_STATICS);assert(aw_efrags_used==AW_EFRAG_LIMIT && allocations==before);

 R_ClearEfrags(false);
 assert(aw_efrags_used==0 && aw_efrags_capacity==AW_EFRAG_LIMIT);
 for(i=0;i<TEST_LEAVES;i++)assert(!leaves[i].efrags);
 for(i=0;i<TEST_STATICS;i++)add_static(i);
 assert(allocations==before && aw_efrags_used==AW_EFRAG_LIMIT);

 /* Production invokes this before Hunk_FreeToLowMark. Reuse after freeing
  * catches retained map-page pointers under address/undefined sanitizers. */
 R_ClearEfrags(true);release_hunk();R_ClearEfrags(false);
 assert(aw_efrags_used==0 && aw_efrags_capacity==MAX_EFRAGS);
 for(i=0;i<TEST_LEAVES;i++)assert(!leaves[i].efrags);
 for(i=0;i<MAX_STATIC_ENTITIES;i++)assert(!cl_static_entities[i].efrag);
 for(i=0;i<17;i++)add_static(i);
 assert(page_count==1 && aw_efrags_used==17*TEST_LEAVES);
 R_ClearEfrags(true);release_hunk();
}
int main(void){visible_capacity();overflow_lifetime();return 0;}
