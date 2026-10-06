/* SPDX-License-Identifier: GPL-2.0-or-later
 * Transient hand animation state, independent of the old VM/map allocation.
 * Include after quakedef.h. No inventory/save format or per-frame allocation. */
#ifndef AW_HAND_STATE_H
#define AW_HAND_STATE_H

typedef struct {
    float goal,state,torch,latched,frame;
    double age;
    char model[MAX_QPATH];
    int valid;
} aw_hand_snapshot_t;

static int AW_HandSnapshotCapture(aw_hand_snapshot_t *s,edict_t *p,double now)
{
    eval_t *goal,*state,*torch,*started,*latched;const char *model;size_t n;
    memset(s,0,sizeof(*s));
    now=(double)(float)now; /* QC timestamps have float precision. */
    goal=GetEdictFieldValue(p,"aw_hand_goal");state=GetEdictFieldValue(p,"aw_hand_state");
    torch=GetEdictFieldValue(p,"aw_torch");started=GetEdictFieldValue(p,"aw_hand_started");
    latched=GetEdictFieldValue(p,"aw_attack_latched");
    if(!goal || !state || !torch || !started || !latched || !isfinite(now))return 0;
    if((goal->_float!=0 && goal->_float!=1) || (torch->_float!=0 && torch->_float!=1) ||
       (latched->_float!=0 && latched->_float!=1) || !isfinite(state->_float) ||
       state->_float<0 || state->_float>4 || state->_float!=floor(state->_float) ||
       !isfinite(p->v.weaponframe) || p->v.weaponframe<0 || p->v.weaponframe>255 ||
       p->v.weaponframe!=floor(p->v.weaponframe))return 0;
    s->age=state->_float?now-started->_float:0;
    /* Ready/idle may have stayed raised across a long simulation pause.
     * Keep its age/first frame; the normal QC idle loop decides its next frame. */
    if(!isfinite(s->age) || s->age<0 || (state->_float!=2 && s->age>60))return 0;
    model=pr_strings+p->v.weaponmodel;
    for(n=0;n<sizeof(s->model) && model[n];n++);
    if(n==sizeof(s->model))return 0;
    memcpy(s->model,model,n+1);
    s->goal=goal->_float;s->state=state->_float;s->torch=torch->_float;
    s->latched=latched->_float;s->frame=p->v.weaponframe;s->valid=1;return 1;
}
static int AW_HandSnapshotRestore(const aw_hand_snapshot_t *s,edict_t *p,double now)
{
    eval_t *goal,*state,*torch,*started,*latched;int i;
    now=(double)(float)now;
    if(!s->valid || !isfinite(now) || !isfinite((float)(now-s->age)))return 0;
    goal=GetEdictFieldValue(p,"aw_hand_goal");state=GetEdictFieldValue(p,"aw_hand_state");
    torch=GetEdictFieldValue(p,"aw_torch");started=GetEdictFieldValue(p,"aw_hand_started");
    latched=GetEdictFieldValue(p,"aw_attack_latched");
    if(!goal || !state || !torch || !started || !latched)return 0;
    /* Validate the copied identity against the new map's precache. Never keep
     * the old VM string offset, entity pointer or client model pointer. */
    if(s->model[0]){
        for(i=1;i<MAX_MODELS;i++)if(sv.model_precache[i] && !strcmp(sv.model_precache[i],s->model))break;
        if(i==MAX_MODELS)return 0;
    }
    goal->_float=s->goal;state->_float=s->state;torch->_float=s->torch;
    latched->_float=s->latched;started->_float=(float)(now-s->age);
    p->v.weaponframe=s->frame;
    p->v.weaponmodel=s->model[0]?ED_NewString((char *)s->model)-pr_strings:0;
    return 1;
}
#endif
