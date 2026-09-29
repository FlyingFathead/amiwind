/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "r_local.h"
#include <assert.h>
int r_framecount=7,cl_numvisedicts;
entity_t *cl_visedicts[MAX_VISEDICTS];
void Sys_Error(char *fmt,...){assert(0);}
int main(void){
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
 free(frags);free(actors);return 0;
}
