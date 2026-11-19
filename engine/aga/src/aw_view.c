/* SPDX-License-Identifier: GPL-2.0-or-later
 * The player's view in the engine (aw_view.h, docs/THIRD_PERSON.md):
 * first/third person on Quake's chase camera, the held Toggle POV orbit, the
 * idle (vanity) orbit, the wheel zoom, the player's body, and the death
 * scene with the original's choices and the AmiWind quick retry.
 *
 * Quake first: chase.c's chase_active makes the client draw the player's own
 * entity (cl_main.c) and R_DrawViewModel skip the hands; Chase_Update's view
 * placement is replaced while this view owns the camera (behind the player at
 * the original's distance, pulled in front of walls by a point trace through
 * the server's world, as chase.c traces its look point). The body is a
 * client-side copy of the view entity with the player's race/sex body model
 * (tools/prepare_player_view.py) and the animation kit's groups (aw_anim.c).
 *
 * Previous methods stay: aw_view_death 0 keeps the first-person death view
 * (Quake's dead roll); aw_player_body 0 draws no body (third person is then
 * refused); chase_active set by hand still runs Chase_Update.
 *
 * Cost: one point trace per frame in third person; the body one frame step
 * per frame; the body model is loaded on first use (Mod_ForName, cache).
 */
#include "quakedef.h"
#include "aw_view.h"
#include "aw_anim.h"
#include "aw_animkit.h"
#include "aw_character.h"
#include "aw_save.h"
#include "aw_combat.h"
#include "aw_story.h"
#include "aw_torch.h"
#include "aw_items.h"
#include "aw_inventory.h"
#include "aw_inspect.h"
#include "aw_hand_models.h"
#include "aw_player_parts.h"
#include "aw_skel.h"
#include "aw_animpick.h"
#include "aw_move.h"       /* the sneak for the body's sneak groups (PLAYER-ANIM-GROUPS-NOT-PLAYED-66) */
#include "aw_msgbox.h"     /* the death box's button rectangles (MSGBOX-NO-CURSOR-62) */
#include "aw_tryalloc.h"   /* dbg camera held's measure, allocated per call (CONFIRMED-LOOKBOOK-67) */

extern cvar_t chase_active;
/* The hooks (defined beside their callers, NULL in fixtures without this file). */
extern int (*aw_death_input_locked)(void);
extern void (*aw_view_frame)(void);
extern int (*aw_view_camera)(void);
extern entity_t *(*aw_view_body)(entity_t *ent);
extern entity_t *(*aw_view_held)(entity_t *ent);
extern int (*aw_view_hide_hands)(void);
extern void (*aw_view_input)(int key,int down);
extern int (*aw_view_key)(int key);
extern void (*aw_view_draw)(void);
extern void (*aw_combat_scene)(void);
extern int (*aw_view_fullscreen)(void);
extern int (*aw_view_orbiting)(void);
extern void (*aw_view_turned)(void);   /* cl_parse.c: the server set the view (svc_setangle) */
extern int (*aw_hand_parts_apply)(const char *race,int female,int stance,int frame);   /* aw_hand_models.c */
extern struct model_s *(*aw_view_hand_part)(int i);                                     /* r_main.c */
int AW_ArenaActive(void);
void AW_MusicDeath(void);
void IN_AWClearButtons(void);

/* aw_view_third 1 = third person (not saved: the original starts in first person) */
static cvar_t view_cvar={"aw_view_third","0"};
static cvar_t distance_cvar={"aw_view_distance","48",true};
static cvar_t vanity_cvar={"aw_view_vanity","1",true};
/* aw_vanity_fullview 1 (default, saved): the vanity orbit shows the world alone, full screen, no HUD
 * (photo mode's view without its own notices); 0 = the orbit inside the normal HUD. */
static cvar_t fullview_cvar={"aw_vanity_fullview","1",true};
static cvar_t death_cvar={"aw_view_death","1",true};
/* The AmiWind quick retry after a lost fight: a build-config switch (--death-retry on|off,
 * default on); an off build writes aw_death_retry 0 into default-game.cfg. */
static cvar_t retry_cvar={"aw_death_retry","1"};
static cvar_t body_cvar={"aw_player_body","1",true};
/* PLAYER-GEAR-VISUAL-59: 1 (default, saved) = the body assembled from parts by what is worn (view/parts.txt,
 * aw_player_parts.h); 0 = the baked body of the race and sex in the starting clothes (the previous method). A carried
 * torch and swimming keep their baked companions in both. */
static cvar_t parts_cvar={"aw_player_body_parts","1",true};

static aw_view_rules_t rules;
/* the image's fVanityDelay (dbg vanitycamera delay N changes rules.vanity_delay for a test, not saved) */
static float vanity_delay_setting=30;
/* dbg vanitycamera on: an orbit started by hand runs until any input, also with the automatic orbit off */
static int vanity_forced;
static aw_view_t view;
/* dbg cam orbit (the orbit section below) */
static struct {
    int active,photo,edict,pending,pending_photo,anglehack;double pending_since;
    vec3_t point,offset,origin,angles,view;float yaw,pitch,distance,rate,pending_rate,movetype,flags;
} orbit;
static aw_death_t death;
static int death_mouse_x=-1,death_mouse_y=-1;   /* the death box's pointer (MSGBOX-NO-CURSOR-62) */
static int ready,pov_down,pov_tapped,input_seen,owned,last_view=-1,warned,death_arena,acted;
static vec3_t anchor,last_angles,death_angles;
/* VIEW-VANITY-UNDOES-SET-VIEW-67: the game turned the player since the last frame (cl_parse.c svc_setangle) */
static int view_forced;
static void view_turned(void) {view_forced=1;}
static char load_text[160]="The most recent Save Game is '%s'. \nWould you like to load it?";
static char yes_text[16]="Yes",no_text[16]="No";
static char save_label[64];
static int save_slot=-1;

/* ---- settings from the image (view/settings.txt, tools/prepare_player_view.py) ---- */
static void unescape(char *s) {
    char *o=s;
    while(*s){if(s[0]=='\\' && s[1]=='n'){*o++='\n';s+=2;}else *o++=*s++;}
    *o=0;
}
static void load_settings(void) {
    FILE *f=NULL;char line[200],*value;float v;
    AW_ViewRulesDefault(&rules);ready=1;
    if(COM_FOpenFile("view/settings.txt",&f)<0 || !f)return;
    if(!fgets(line,sizeof(line),f) || strncmp(line,"AWVS1",5)){fclose(f);return;}
    while(fgets(line,sizeof(line),f)){
        line[strcspn(line,"\r\n")]=0;
        value=strchr(line,' ');if(!value)continue;*value++=0;
        if(!strcmp(line,"fVanityDelay")){v=Q_atof(value);if(v>0 && v<=3600)rules.vanity_delay=vanity_delay_setting=v;}
        else if(!strcmp(line,"sLoadLastSaveMsg") && strlen(value)<sizeof(load_text) && strstr(value,"%s") &&
                !strchr(strstr(value,"%s")+2,'%')){strcpy(load_text,value);unescape(load_text);}
        else if(!strcmp(line,"sYes") && strlen(value)<sizeof(yes_text))strcpy(yes_text,value);
        else if(!strcmp(line,"sNo") && strlen(value)<sizeof(no_text))strcpy(no_text,value);
    }
    fclose(f);
}

static edict_t *local_player(void) {
    if(!sv.active || svs.maxclients!=1 || !svs.clients || cls.state!=ca_connected || cls.signon!=SIGNONS)return NULL;
    return svs.clients[0].edict;
}

/* ---- the body ---- */
#define BODIES 32
static struct {char race[32],path[48];int female;} bodies[BODIES];
static int body_count=-1,body_race=-2,body_female=-1,body_index=-1;
static model_t *body_model;
static model_t *held_model;
static int body_torch,body_water,torch_failed,water_failed,held_visible;
static aw_view_torch_t body_emitter;
static char held_path[64];   /* the admitted held torch alias, for its re-admission */
static double held_next;      /* AW_ViewHeldRetry's clock */
static entity_t held_body;
static aw_anim_t body_anim;
static aw_anim_play_t body_play;
static aw_anim_air_t body_air;
static aw_view_layers_t body_layers;
static entity_t body;
/* ---- the assembled body (PLAYER-GEAR-VISUAL-59, aw_player_parts.h) ----
 * The parts of what the player wears, assembled from the recipe when the race, sex, head, hair or a worn item changes
 * (the recipe is read then and let go: nothing of it stays in memory), each part one shared model drawn at the
 * body's table frame; the body entity draws the first, view_held the rest. The bones are posed once per table frame
 * for all parts (r_alias.c), the vertices per part. */
static aw_parts_body_t parts;
static model_t *part_models[AW_PARTS_MAX];
static const aw_skel_table_t *parts_table;
static aw_anim_t parts_anim;
static entity_t part_ents[AW_PARTS_MAX];
static char parts_sig[AW_PARTS_ITEMS*64+256];   /* what the parts were assembled for */
static int body_parts,parts_failed,parts_built;   /* the body is the assembled one; assembly failed (said once); count */
static double parts_ms;                          /* the last assembly's time, dbg camera */
static void body_layers_read(const char *text,int frames) {
    if(!AW_ViewLayersParse(&body_layers,text,frames))return;
    if(!AW_ViewLayersBind(&body_layers,&body_anim))memset(&body_layers,0,sizeof(body_layers));
}
static void load_bodies(void) {
    byte *raw;int mark=Hunk_LowMark();char *p,*e,race[32],path[48];int female;
    body_count=0;
    raw=COM_LoadHunkFile("view/bodies.txt");
    if(raw && !strncmp((char *)raw,"AWPB1",5)){
        for(p=(char *)raw;p && *p && body_count<BODIES;p=e){
            e=strchr(p,'\n');if(e)*e++=0;
            /* RACE<TAB>0|1<TAB>PATH (no scanf: it pulls in FPU-emulated number parsing) */
            {char *t1=strchr(p,'\t'),*t2=t1?strchr(t1+1,'\t'):NULL;size_t n;
             if(!t1 || !t2 || t2!=t1+2 || (t1[1]!='0' && t1[1]!='1'))continue;
             n=(size_t)(t1-p);if(!n || n>=sizeof(race))continue;memcpy(race,p,n);race[n]=0;
             female=t1[1]-'0';n=strcspn(t2+1,"\r\t ");if(!n || n>=sizeof(path))continue;memcpy(path,t2+1,n);path[n]=0;}
            if(!strncmp(path,"progs/body/",11) && !strstr(path,"..") && strlen(path)>15 && !strcmp(path+strlen(path)-4,".mdl")){
                strcpy(bodies[body_count].race,race);strcpy(bodies[body_count].path,path);bodies[body_count].female=female;body_count++;
            }
        }
    }
    Hunk_FreeToLowMark(mark);
}
/* ---- the assembled body's parts ---- */
/* The parts forgotten, not freed: they stay in the model cache as any model does until it needs the room (its LRU),
 * so the parts the next outfit keeps (the skin, the head, an unchanged piece) need no disk read. */
static void parts_release(void) {
    memset(part_models,0,sizeof(part_models));
}
/* 0 = no assembled body now (the baked one draws); 1 = the parts are those of what is worn; 2 = assembled again now
 * (the race, sex, head, hair or a worn item changed). */
/* ARRIVAL-LONG-FRAME-DEV6-59: an assembly loads its part models over several frames, PARTS_FRAME_BUDGET seconds of
 * loading per frame at most (at least one part), never all of them inside one frame (about 28 parts took 12-15 s of
 * the first frame after arriving); -1 while it is under way (no body drawn yet; the previous one stays until the new
 * one is complete when one was assembled before) */
#define PARTS_FRAME_BUDGET .04
/* aw_player_cache 1 (the default, id1/default-game.cfg): this way; 0 = the previous way for an A/B on the same image
 * (every part in the frame that needs the body, the parts left to the cache's LRU) */
static cvar_t player_cache_cvar={"aw_player_cache","1"};
static void part_pin(model_t *m,int on){if(m)Cache_Pin(&m->cache,on && player_cache_cvar.value);}
/* FP-ARMS-NO-MODEL-SLOT-67 (the maintainer, 2026-11-18: swapping races and sexes unloads what was before): a part model
 * that leaves its set (the body's or the first-person arms', on a race, sex or outfit change) is released at once
 * (Mod_ReleaseAlias: its data freed, its slot in the engine's model table free for the next model), unless the other
 * set draws it. Before, the old sets were only unpinned: each kept its slot, optional models are admitted only below
 * the table's static base or into a released slot (model.c Mod_CanFindName), and after six race and sex changes in one
 * place the Khajiit's arm parts found no slot, the arms fell back to the legacy hand model and the held light was not
 * drawn. dbg race also releases both sets at the swap (AW_ViewPartsUnload). */
static unsigned long parts_released;
static void part_drop(model_t *m);
/* model.c's NL_UNREFERENCED (its loader states are private there; model.c and model.h are not changed here: their
 * bytes key the world stages): a released slot (tests/test_fp_hands_per_race.py checks the two agree) */
#define VIEW_NL_UNREFERENCED 2
/* the one place every race or sex change passes (the maintainer, 2026-11-18: dbg race, dbg set race, aw_quickchar_set,
 * the character menus, New Game, a load): the body and the arms read the race and sex each frame they are drawn;
 * a change since the last assembly releases both old sets at once (AW_ViewPartsUnload) before the new ones load */
static char parts_race_seen[64];
static int parts_female_seen=-1;
static void parts_race_check(const char *race,int female);
static aw_parts_body_t pend;
static model_t *pend_models[AW_PARTS_MAX];
static char pend_sig[sizeof(parts_sig)];
static int pend_on,pend_next,pend_count,pend_frames;
static unsigned long pend_loads;
static double pend_t;
extern unsigned long aw_file_finds;   /* aw_spike.c: files looked up by name (a part read from disk: 3 lookups) */
static int parts_in_use(const model_t *m){int i;for(i=0;i<AW_PARTS_MAX;i++)if(part_models[i]==m)return 1;return 0;}
static int parts_ready(const char *race,int female) {
    const char *items[AW_PARTS_ITEMS],*head=NULL,*hair=NULL;char sig[sizeof(parts_sig)];
    aw_parts_body_t next;int n=0,s,i,ok,mark;byte *text;double t0,start;
    parts_race_check(race,female);
    if(!parts_cvar.value || parts_failed)return 0;
    if(aw_character.valid){
        if(aw_character.head>=0 && aw_character.head<aw_part_count)head=aw_parts[aw_character.head].id;
        if(aw_character.hair>=0 && aw_character.hair<aw_part_count)hair=aw_parts[aw_character.hair].id;
    }
    /* what is worn: the clothing and armour slots (helmet .. robe), their ids straight from the state (asked every
     * frame: no catalogue read, which is a disk read per item); rings, amulets and belts show nothing on the
     * original body, the weapon and shield are held items (parts_draws) */
    for(s=AW_SLOT_HELMET;s<=AW_SLOT_ROBE && n<AW_PARTS_ITEMS;s++)
        if(aw_state.inventory.equipped[s][0])items[n++]=aw_state.inventory.equipped[s];
    snprintf(sig,sizeof(sig),"%s|%d|%s|%s",race,female,head?head:"",hair?hair:"");
    for(i=0;i<n;i++){size_t used=strlen(sig);snprintf(sig+used,sizeof(sig)-used,"|%s",items[i]);}
    if(body_parts && parts.count && parts_table && !strcmp(sig,parts_sig))return 1;
    start=Sys_FloatTime();
    if(!pend_on || strcmp(sig,pend_sig)){
        /* a new assembly: the recipe read once (one file), its parts loaded over the next frames */
        mark=Hunk_LowMark();text=COM_LoadHunkFile("view/parts.txt");
        ok=text && AW_PartsAssemble((const char *)text,com_filesize,race,female,head,hair,items,n,&next);
        Hunk_FreeToLowMark(mark);
        if(!ok){
            parts_failed=1;pend_on=0;
            Con_Printf("Assembled player body unavailable (%s, %s): the baked body draws.\n",
                text?"no recipe for this race and sex":"no view/parts.txt in this image",race);
            return 0;
        }
        if(!AW_SkelTableFor(next.table)){parts_failed=1;pend_on=0;Con_Printf("Assembled player body: no table %s.\n",next.table);return 0;}
        /* an assembly left unfinished: its parts no longer kept (those the body in use draws stay pinned) */
        for(i=0;i<pend_count;i++)if(pend_models[i] && !parts_in_use(pend_models[i])){
            model_t *old=pend_models[i];
            pend_models[i]=NULL;part_pin(old,0);part_drop(old);
        }
        pend=next;strcpy(pend_sig,sig);pend_on=1;pend_next=pend_count=pend_frames=0;pend_t=0;
        pend_loads=aw_file_finds;
        memset(pend_models,0,sizeof(pend_models));
    }
    {
        const aw_skel_table_t *table=AW_SkelTableFor(pend.table);
        while(pend_next<pend.count){
            model_t *m=Mod_ForName(pend.model[pend_next],false);
            aliashdr_t *h=m && m->type==mod_alias?(aliashdr_t *)Mod_Extradata(m):NULL;
            if(!h || !h->aw_skel || (const void *)h->aw_skel_table!=(const void *)table)
                Con_Printf("Assembled player body: part %s (slot %d) not drawn: %s.\n",pend.model[pend_next],pend.slot[pend_next],
                    !m?"not in this image":!h?"not a model":"not on the body's table");
            else{
                part_pin(m,1);     /* kept from now on: no lack of room evicts it */
                pend_models[pend_count]=m;
                if(pend_count!=pend_next){strcpy(pend.model[pend_count],pend.model[pend_next]);pend.slot[pend_count]=pend.slot[pend_next];}
                pend_count++;
            }
            pend_next++;
            if(pend_next<pend.count && player_cache_cvar.value && Sys_FloatTime()-start>=PARTS_FRAME_BUDGET){
                pend_t+=Sys_FloatTime()-start;pend_frames++;
                return body_parts && parts.count && parts_table?1:-1;   /* the rest in the next frames */
            }
        }
        pend_t+=Sys_FloatTime()-start;
        t0=Sys_FloatTime()-pend_t;      /* parts_ms below: the loading time in all, over its frames */
        pend_on=0;pend_frames++;
        /* the parts of the body in use that the new one does not keep: unpinned, and released once the new set is the
         * body's (FP-ARMS-NO-MODEL-SLOT-67) */
        {
            model_t *gone[AW_PARTS_MAX];int k,g=0;
            for(i=0;i<AW_PARTS_MAX;i++)if(part_models[i]){
                int kept=0;
                for(k=0;k<pend_count;k++)if(pend_models[k]==part_models[i])kept=1;
                if(!kept){part_pin(part_models[i],0);gone[g++]=part_models[i];}
            }
            parts_table=table;
            parts_release();
            parts=pend;parts.count=s=pend_count;
            memcpy(part_models,pend_models,sizeof(part_models));
            memset(pend_models,0,sizeof(pend_models));pend_count=0;
            for(k=0;k<g;k++)part_drop(gone[k]);
        }
        Con_Printf("Assembled player body: %d parts, %lu file lookups, %.0f ms over %d frames (%lu KB kept).\n",
            s,aw_file_finds-pend_loads,pend_t*1000,pend_frames,aw_cache_pinned_bytes/1024);
    }
    mark=Hunk_LowMark();text=COM_LoadHunkFile(parts.anm);
    ok=s>0 && text && AW_AnimParse(&parts_anim,(const char *)text,parts_table->frames);
    Hunk_FreeToLowMark(mark);
    if(!ok){
        parts_release();parts.count=0;parts_failed=1;
        Con_Printf("Assembled player body unavailable (%s): the baked body draws.\n",s?"its animation layout did not load":"no part loaded");
        return 0;
    }
    strcpy(parts_sig,sig);parts_built++;parts_ms=(Sys_FloatTime()-t0)*1000;
    return 2;
}
/* aw_worldui.c (INVENTORY-PREVIEW-STALE-61): 1 while a changed outfit's parts are still loading, so the inventory
 * picture waits for them instead of keeping the previous outfit */
extern int (*aw_inventory_preview_pending)(void);
static int parts_pending(void){return pend_on && parts_cvar.value && !parts_failed;}
/* EQUIP-ACTION-REGRESSION-62: the player is a beast race when the race's recipe is on the beast skeleton (the
 * builder takes the skeleton from the race's Beast flag, tools/prepare_player_parts.py race_rows): the assembled
 * body's own answer, or the one being assembled */
static int player_beast(void){return (pend_on && pend.beast) || (body_parts && parts.count && parts.beast);}
/* ---- the first-person arms from parts (PLAYER-GEAR-VISUAL-59, docs/THIRD_PERSON.md "First-person arms") ----
 * The same recipe reader on view/parts_1st.txt (tools/prepare_player_fp_parts.py): the race's arm skin and the arm
 * parts of what is worn (gloves, gauntlets, bracers, sleeves; a robe's own first-person sleeves), each one shared
 * skeletal model on the first-person table (progs/humanoid_1st.awsk: 28 frames per stance in the baked hands' frame
 * contract, already in the view's space). Assembled only when the race, sex or a worn item changes (the recipe read
 * then and let go: nothing of it kept, no catalogue read per frame); drawn as the view model at the hands' frame of
 * the stance (aw_hand_models.c), the further parts by the renderer at the same frame (r_main.c R_DrawViewModel).
 * aw_hand_parts 0 (dbg camera hands off) = the baked arms of the race and sex, the previous method; the carried torch
 * and the shield guard keep their baked arms in both. */
static cvar_t hand_parts_cvar={"aw_hand_parts","1",true};
#define HAND_PART_FRAMES 28     /* aw_hand_models.c: the hands' frame contract */
/* bare hands, then AW_HandStance's six (an older table: the first four), then the held light (v0.0.61,
 * HELD-LIGHT-OWN-MODEL-61: aw_hand_models.h AW_HAND_LIGHT_STANCE; an older table has no such frames) */
/* then the spell stance by range (v0.0.66, PLAYER-CASTING-59: aw_hand_models.h AW_HAND_SPELL_STANCE + self, touch,
 * target; an older table has no such frames: the bare hands) */
#define HAND_PART_STANCES 11
#define HAND_PART_MELEE 4       /* the stances every table has */
static aw_parts_body_t hparts;
static model_t *hpart_models[AW_PARTS_MAX];
static const aw_skel_table_t *hparts_table;
static char hparts_sig[sizeof(parts_sig)];
static int hparts_failed,hparts_built,hparts_shown,hparts_frame;
static double hparts_ms;
/* FP-ARMS-NO-MODEL-SLOT-67: the race, sex and outfit whose arm parts all found no model slot: the baked arms draw for
 * it, and the parts are tried again at the next change (before, hparts_failed held them off for the session) */
static char hparts_noslot_sig[sizeof(parts_sig)];
static int hparts_in_use(const model_t *m){int i;for(i=0;i<AW_PARTS_MAX;i++)if(hpart_models[i]==m)return 1;return 0;}
static int pend_in_use(const model_t *m){int i;for(i=0;i<pend_count;i++)if(pend_models[i]==m)return 1;return 0;}
/* M, a part model that left its set: released now unless a set still draws it (FP-ARMS-NO-MODEL-SLOT-67) */
static void part_drop(model_t *m) {
    if(!m || m->type!=mod_alias || m->needload==VIEW_NL_UNREFERENCED || strncmp(m->name,"progs/parts/",12) ||
       parts_in_use(m) || hparts_in_use(m) || pend_in_use(m))return;
    part_pin(m,0);Mod_ReleaseAlias(m);parts_released++;
}
static model_t *hold_models[AW_PARTS_MAX];   /* the arms' set being replaced (hand_parts_ready) */
static void hparts_drop_old(void) {
    int i;
    for(i=0;i<AW_PARTS_MAX;i++){model_t *m=hold_models[i];hold_models[i]=NULL;part_drop(m);}
}
extern int mod_numknown;   /* model.c: the slots of the loaded-model table (ENGINE-MODEL-TABLE-58) */
/* the model table's slots in use (not released) and how many of them are the player's part models (progs/parts/) */
static int model_slots_in_use(int *part_slots) {
    int i,used=0,parts_n=0;
    for(i=0;i<mod_numknown;i++){
        model_t *m=Mod_Known(i);
        if(m->needload==VIEW_NL_UNREFERENCED)continue;
        used++;if(!strncmp(m->name,"progs/parts/",12))parts_n++;
    }
    if(part_slots)*part_slots=parts_n;
    return used;
}
/* 0 = no arms from parts now (the baked arms draw); 1 = the parts are those of what is worn; 2 = assembled now */
static int hand_parts_ready(const char *race,int female) {
    const char *items[AW_PARTS_ITEMS];char sig[sizeof(hparts_sig)];aw_parts_body_t next;int n=0,s,i,ok,mark,noslot=0;
    byte *text;double t0;
    parts_race_check(race,female);
    if(!hand_parts_cvar.value || hparts_failed || !race)return 0;
    /* what is worn, as the body asks it (parts_ready): ids straight from the state, a string compare per frame */
    for(s=AW_SLOT_HELMET;s<=AW_SLOT_ROBE && n<AW_PARTS_ITEMS;s++)
        if(aw_state.inventory.equipped[s][0])items[n++]=aw_state.inventory.equipped[s];
    snprintf(sig,sizeof(sig),"%s|%d",race,female);
    for(i=0;i<n;i++){size_t used=strlen(sig);snprintf(sig+used,sizeof(sig)-used,"|%s",items[i]);}
    if(hparts.count && hparts_table && !strcmp(sig,hparts_sig))return 1;
    if(hparts_noslot_sig[0] && !strcmp(sig,hparts_noslot_sig))return 0;
    t0=Sys_FloatTime();
    mark=Hunk_LowMark();text=COM_LoadHunkFile("view/parts_1st.txt");
    ok=text && AW_PartsAssemble((const char *)text,com_filesize,race,female,NULL,NULL,items,n,&next);
    Hunk_FreeToLowMark(mark);
    /* ARRIVAL-LONG-FRAME-DEV6-59: the arms' parts are kept (pinned) while worn; the old set back to the LRU (a part
     * the new set keeps is pinned again below, still in memory: no disk read) */
    /* the set in use: unpinned; released below once the new set is loaded (those it keeps stay: no disk read) */
    memcpy(hold_models,hpart_models,sizeof(hold_models));
    for(i=0;i<AW_PARTS_MAX;i++)if(hpart_models[i] && !parts_in_use(hpart_models[i]))part_pin(hpart_models[i],0);
    hparts.count=0;memset(hpart_models,0,sizeof(hpart_models));
    if(!ok){
        hparts_drop_old();
        hparts_failed=1;
        Con_Printf("First-person arms from parts unavailable (%s, %s): the baked arms draw.\n",
            text?"no recipe for this race and sex":"no view/parts_1st.txt in this image",race);
        return 0;
    }
    if(!(hparts_table=AW_SkelTableFor(next.table)) || hparts_table->frames<HAND_PART_FRAMES*HAND_PART_MELEE){
        hparts_drop_old();
        hparts_failed=1;Con_Printf("First-person arms from parts: no usable table %s: the baked arms draw.\n",next.table);
        return 0;
    }
    hparts=next;
    for(i=0,s=0;i<next.count;i++){
        model_t *m;aliashdr_t *h;
        if(!Mod_CanFindName(next.model[i])){
            noslot++;
            Con_Printf("First-person arms from parts: no model slot for %s (slot %d).\n",next.model[i],next.slot[i]);
            continue;
        }
        m=Mod_ForName(next.model[i],false);
        h=m && m->type==mod_alias?(aliashdr_t *)Mod_Extradata(m):NULL;
        if(!h || !h->aw_skel || (const void *)h->aw_skel_table!=(const void *)hparts_table){
            Con_Printf("First-person arms from parts: part %s (slot %d) not drawn: %s.\n",next.model[i],next.slot[i],
                !m?"not in this image":!h?"not a model":"not on the first-person table");
            continue;
        }
        part_pin(m,1);
        hpart_models[s]=m;strcpy(hparts.model[s],next.model[i]);hparts.slot[s]=next.slot[i];s++;
    }
    hparts.count=s;
    hparts_drop_old();
    if(!s){
        /* every part refused a slot: this outfit only (tried again at the next change); any other cause: the session */
        if(noslot==next.count)strcpy(hparts_noslot_sig,sig);else hparts_failed=1;
        Con_Printf("First-person arms from parts: no part loaded%s: the baked arms draw.\n",
            noslot==next.count?" (no model slot; tried again at the next change)":"");
        return 0;
    }
    hparts_noslot_sig[0]=0;
    strcpy(hparts_sig,sig);hparts_built++;hparts_ms=(Sys_FloatTime()-t0)*1000;
    Con_Printf("First-person arms from parts: %d parts in %.0f ms (%lu KB kept).\n",s,hparts_ms,aw_cache_pinned_bytes/1024);
    return 2;
}
/* aw_hand_models.c (aw_hand_parts_apply): the view model becomes the first part at the hands' FRAME (0..27) of
 * STANCE (0 bare hands, 1 one-handed, 2 two-handed close, 3 two-handed wide, 4 bow, 5 crossbow, 6 thrown; the last three
 * only in a table that has them, FIRST-PERSON-WEAPONS-56). 1 = drawn from parts. */
/* READY-MAGIC-SHOWS-WEAPON-65: the spell stance (magic ready, R) shows the empty hands in first person */
static int weapon_hidden(void) {return aw_magic_readied;}
/* READY-MAGIC-SHOWS-WEAPON-65 (v0.0.66): the left hand's torch or light put away while magic is ready (aw_torch.h
 * aw_torch_put_away; aw_hand_models.h AW_HandCarriesLeft) */
static int left_put_away(void) {return !AW_HandCarriesLeft(aw_magic_readied);}
static int hand_parts_apply(const char *race,int female,int stance,int frame) {
    hparts_shown=0;
    if(stance<0 || stance>=HAND_PART_STANCES || !hand_parts_ready(race,female) ||
       hparts_table->frames<(stance+1)*HAND_PART_FRAMES)return 0;
    if(frame<0)frame=0;
    if(frame>=HAND_PART_FRAMES)frame=HAND_PART_FRAMES-1;
    hparts_frame=stance*HAND_PART_FRAMES+frame;
    cl.viewent.model=hpart_models[0];cl.viewent.frame=hparts_frame;
    hparts_shown=1;return 1;
}
/* r_main.c (aw_view_hand_part): the further parts (I from 1) of the arms drawn this frame, NULL after the last. */
static struct model_s *hand_part(int i) {
    /* only while the view model drawn is this frame's first part (a torch or the guard drawn instead: none) */
    if(!hparts_shown || cl.viewent.model!=hpart_models[0] || cl.viewent.frame!=hparts_frame)return NULL;
    return i>0 && i<hparts.count?hpart_models[i]:NULL;
}
/* aw_hand_models.c (aw_hand_parts_bone_tag; HELD-LIGHT-OWN-MODEL-61, FP-TORCH-HAND-REGRESSION-67): the bone of HAND
 * (AW_HAND_LEFT the shield bone, AW_HAND_RIGHT the weapon bone) of the arms drawn now, at this frame's table frame, as a
 * tag in the view model's space (the table's root carries the view: tools/prepare_player_fp_parts.py): the one place
 * every held item of first person rides */
static int hand_parts_bone_tag(int hand,float tag[6]) {
    static float world[AW_SKEL_MAX_BONES][3][4];static const aw_skel_table_t *posed;static int posed_frame=-1;
    float scale[3],w=hparts.weight>0?hparts.weight:1,h=hparts.height>0?hparts.height:1;
    int bone=hand==AW_HAND_LEFT?hparts.shield_bone:hparts.weapon_bone;
    if(!hparts_shown || !hparts_table || bone<0 || bone>=hparts_table->bones)return 0;
    if(posed!=hparts_table || posed_frame!=hparts_frame){
        AW_SkelPose(hparts_table,(float)hparts_frame,world);posed=hparts_table;posed_frame=hparts_frame;
    }
    scale[0]=scale[1]=w*.25f;scale[2]=h*.25f;
    AW_SkelBoneTag((const float (*)[4])world[bone],scale,tag);
    return 1;
}
static int body_find(const char *race,int female) {
    int i;
    for(i=0;i<body_count;i++)if(bodies[i].female==female && !Q_strcasecmp(bodies[i].race,(char *)race))return i;
    for(i=0;i<body_count && bodies[i].female!=female;i++);
    return i<body_count?i:-1;
}
/* The body of the character's race and sex (the original's player record, a Dark Elf man,
 * before a character exists). 1 = a body is ready. */
static int body_ready(void) {
    const char *race="dark elf";int female=0,i,mark,carried,swimming,changed;char anm[64],path[64],held[64];byte *text;size_t n;
    edict_t *player=local_player();
    if(!body_cvar.value)return 0;
    if(body_count<0)load_bodies();
    if(!body_count)return 0;
    if(aw_character.valid && aw_character.race>=0 && aw_character.race<aw_race_count){
        race=aw_races[aw_character.race].id;female=aw_character.female?1:0;
    }
    changed=body_race!=(aw_character.valid?aw_character.race:-1) || body_female!=female;
    if(changed)torch_failed=water_failed=0;
    swimming=player && player->v.health>0 && player->v.waterlevel>=2 && death.stage==AW_DEATH_NONE && !water_failed;
    carried=AW_TorchEquipped() && player && player->v.waterlevel<2 && death.stage==AW_DEATH_NONE && !torch_failed;
    /* the assembled body (the default): without a torch, on land and in water (SWIM-BAKED-CLOTHES-60: the image's
     * layout has the table's swim groups, so the swimmer wears what is worn); a carried torch keeps its baked
     * companion (its own pose), and so does swimming in an image whose layout has no swim groups (the previous
     * method) */
    if(!carried && (i=parts_ready(race,female))<0)return 0;   /* parts still loading (ARRIVAL-LONG-FRAME-DEV6-59) */
    if(!carried && i!=0 && (!swimming || AW_AnimSwims(&parts_anim))){
        if(!body_parts || changed){
            if(body_model && body_model->type==mod_alias && body_model->cache.data && !body_parts)Cache_Free(&body_model->cache);
            if(held_model && held_model->type==mod_alias && held_model->cache.data)Cache_Free(&held_model->cache);
            held_model=NULL;body_emitter.count=0;held_visible=0;held_path[0]=0;
            memset(&body_play,0,sizeof(body_play));body_play.group=255;memset(&body_air,0,sizeof(body_air));
        }
        body_model=part_models[0];body_parts=1;body_anim=parts_anim;memset(&body_layers,0,sizeof(body_layers));
        body_race=aw_character.valid?aw_character.race:-1;body_female=female;body_torch=body_water=0;
        body_index=body_find(race,female);
        return 1;
    }
    if(body_parts){
        /* leaving the assembled body (torch, water, aw_player_body_parts 0): the baked one loads below */
        body_parts=0;body_model=NULL;
        memset(&body_play,0,sizeof(body_play));body_play.group=255;memset(&body_air,0,sizeof(body_air));
    }
    if(body_model && !changed && body_torch==carried && body_water==swimming)return 1;
    /* These player-only aliases are alternatives, not three resident bodies.
     * Relinking has discarded last frame's draw list before this switch. */
    if(body_model && body_model->type==mod_alias && body_model->cache.data)Cache_Free(&body_model->cache);
    if(held_model && held_model->type==mod_alias && held_model->cache.data)Cache_Free(&held_model->cache);
    body_model=NULL;held_model=NULL;body_emitter.count=0;held_visible=0;held_path[0]=0;
    body_race=aw_character.valid?aw_character.race:-1;body_female=female;body_torch=body_water=0;
    for(i=0;i<body_count;i++)if(bodies[i].female==female && !Q_strcasecmp(bodies[i].race,(char *)race))break;
    if(i==body_count)for(i=0;i<body_count && bodies[i].female!=female;i++);
    if(i==body_count)return 0;
    body_index=i;
    strcpy(path,bodies[i].path);n=strlen(path);
    if(swimming){
        model_t *candidate;aw_anim_t water_anim;
        strcpy(path+n-4,"_w.mdl");candidate=Mod_ForName(path,false);
        strcpy(anm,path);strcpy(anm+strlen(anm)-4,".anm");
        mark=Hunk_LowMark();text=COM_LoadHunkFile(anm);
        if(candidate && candidate->type==mod_alias && Cache_Check(&candidate->cache) && text &&
           AW_AnimParse(&water_anim,(const char *)text,candidate->numframes) &&
           water_anim.g[AW_ANIM_SWIM].present && water_anim.g[AW_ANIM_SWIMIDLE].present){
            body_model=candidate;body_water=1;
        }
        Hunk_FreeToLowMark(mark);
        if(!body_water){
            if(candidate && candidate->type==mod_alias && candidate->cache.data)Cache_Free(&candidate->cache);
            water_failed=1;strcpy(path,bodies[i].path);
            Con_Printf("Player swim companion unavailable; original body retained.\n");
        }
    }
    if(carried){
        model_t *candidate,*equipment;extern int hunk_size,hunk_low_used,hunk_high_used;
        strcpy(path+n-4,"_t.mdl");strcpy(held,bodies[i].path);strcpy(held+n-4,"_h.mdl");
        candidate=equipment=NULL;
        /* Same bounded optional-alias admission used by guard equipment. */
        if(hunk_size-hunk_low_used-hunk_high_used>=2*1024*1024){
            candidate=Mod_ForName(path,false);equipment=Mod_ForName(held,false);
        }
        strcpy(anm,path);strcpy(anm+strlen(anm)-4,".awt");
        mark=Hunk_LowMark();text=COM_LoadHunkFile(anm);
        if(candidate && equipment && candidate->type==mod_alias && equipment->type==mod_alias &&
           candidate->numframes==equipment->numframes && Cache_Check(&candidate->cache) && Cache_Check(&equipment->cache) &&
           AW_ViewTorchParse(&body_emitter,text,com_filesize,candidate->numframes)){
            body_model=candidate;held_model=equipment;body_torch=1;strcpy(held_path,held);held_next=0;
        }
        Hunk_FreeToLowMark(mark);
        if(!body_torch){
            torch_failed=1;strcpy(path,bodies[i].path);
            Con_Printf("Player torch companion unavailable; original body retained.\n");
        }
    }
    if(!body_model)body_model=Mod_ForName(path,false);
    if(!body_model || body_model->type!=mod_alias){body_model=NULL;return 0;}
    n=strlen(path);memcpy(anm,path,n-4);strcpy(anm+n-4,".anm");
    mark=Hunk_LowMark();text=COM_LoadHunkFile(anm);
    if(!text || !AW_AnimParse(&body_anim,(const char *)text,body_model->numframes)){
        AW_AnimDefault(&body_anim,body_model->numframes);memset(&body_layers,0,sizeof(body_layers));
    }else body_layers_read((const char *)text,body_model->numframes);
    Hunk_FreeToLowMark(mark);
    if(changed){
        memset(&body_play,0,sizeof(body_play));body_play.group=255;
        memset(&body_air,0,sizeof(body_air));
    }
    return 1;
}
/* PLAYER-TORCH-THIRDPERSON-38: 1 = the held torch alias is in the cache now.
 * It is an optional model admitted once with its torch body; any later alias,
 * map chunk or hunk load can evict it from the cache. The torch body survives
 * that (the alias renderer reloads its own entity through Mod_Extradata), but
 * the held torch was only ever drawn when Cache_Check found it, so after one
 * eviction the raised arm stayed and the torch never came back. Load it again
 * under its first admission's free-memory rule, at most once a second; the
 * same slot (Mod_ForName finds it by name) and the body's frame count. */
static int held_ready(void) {
    extern int hunk_size,hunk_low_used,hunk_high_used;model_t *m;int cached;
    if(!body_torch || !held_model || !body_model || !held_path[0])return 0;
    cached=Cache_Check(&held_model->cache)!=NULL;
    if(!AW_ViewHeldRetry(cached,hunk_size-hunk_low_used-hunk_high_used,realtime,&held_next))return cached;
    m=Mod_ForName(held_path,false);
    return m==held_model && m->type==mod_alias && m->numframes==body_model->numframes &&
        Cache_Check(&m->cache)!=NULL;
}
/* Modal-only alias: original inventory frames do not replace locomotion or
 * advance its animation clock. One optional model, released on panel close. */
static model_t *inventory_model;
static char inventory_body_path[64];
static int inventory_failed,inventory_left=1;
void AW_ViewInventoryClear(void){
    if(inventory_model && inventory_model->type==mod_alias && inventory_model->cache.data)
        Cache_Free(&inventory_model->cache);
    inventory_model=NULL;inventory_body_path[0]=0;inventory_failed=0;inventory_left=1;
    AW_ItemsAliasClear();
}
static entity_t inventory_held[2];
static entity_t *held_draws[AW_PARTS_MAX+2];
static int held_cursor,held_draw_count;
int AW_ViewEquipmentReady(void){
    if(!body_ready() || body_water)return 0;
    /* the assembled body holds items on its table's weapon bone (parts_draws), the baked one by its tag rows */
    if(body_parts)return parts_table && parts.weapon_bone>=0 && parts.weapon_bone<parts_table->bones;
    return AW_ItemsAliasTag(body_model,-1,0,NULL);
}
/* ---- the inventory picture of the assembled body (INVENTORY-PREVIEW-BAKED-BODY-59) ----
 * The picture draws what the third-person view draws: the same parts (the recipe assembled for the race, sex, head,
 * hair and what is worn: parts_ready, again only when one of them changes) on the same table, posed at the start of
 * the original's inventory group for the weapon in the right hand (AW_PartsInventoryGroups), the weapon and shield on
 * the table's item bones. The picture follows the body's switch (no setting of its own: the resident registry's
 * budget): aw_player_body_parts 0 draws the race's baked inventory companion (the _i.mdl beside each baked body, its
 * own starting outfit), the previous method; the carried torch keeps its torch body in both. */
static int inventory_parts_frame=-1,inventory_parts_said;
/* the table frame of the group's start key (its first frame when it has no such key), -1 when the table has neither
 * group */
static int parts_inventory_frame(int type,int *left){
    const char *g[2];int n=AW_PartsInventoryGroups(type,g,left),i,group,frame;aw_skel_group_t at;
    for(i=0;i<n;i++){
        if((group=AW_SkelGroup(parts_table,g[i]))<0)continue;
        frame=AW_SkelKeyFrame(parts_table,group,"start");
        if(frame<0){AW_SkelGroupAt(parts_table,group,&at);frame=(int)at.first;}
        if(frame>=0 && frame<parts_table->frames)return frame;
    }
    return -1;
}
/* aw_head.c: the picture's further parts (the first is AW_ViewInventoryBody's model) and the race's scale (x y by
 * weight, z by height, as the third-person view scales them after posing); -1 when the picture is not the assembled
 * body. */
int AW_ViewInventoryParts(model_t **models,int max,float scale[3]){
    int i,n=0;
    if(inventory_parts_frame<0 || !body_parts || !parts_table)return -1;
    for(i=1;i<parts.count && n<max;i++)if(part_models[i])models[n++]=part_models[i];
    scale[0]=scale[1]=parts.weight;scale[2]=parts.height;
    return n;
}
/* the weapon and the shield on the item bones of the table posed at the picture's frame (as parts_draws) */
static int parts_inventory_items(int frame,model_t *models[2],float origins[2][3],float angles[2][3]){
    static float world[AW_SKEL_MAX_BONES][3][4];
    int kind,n=0,bone,posed=0;aw_inventory_item_t item;float tag[6],scale[3];
    scale[0]=scale[1]=parts.weight*.25f;scale[2]=parts.height*.25f;
    for(kind=0;kind<2;kind++){
        bone=kind?parts.shield_bone:parts.weapon_bone;
        if(bone<0 || bone>=parts_table->bones || (kind && !inventory_left))continue;
        if(!AW_InventoryEquippedItem(kind?AW_SLOT_LEFT:AW_SLOT_RIGHT,&item) || !item.model[0] ||
           (kind && (item.category!=AW_INV_ARMOUR || item.subtype!=8)))continue;
        models[n]=Mod_ForName(item.model,false);
        if(!models[n] || models[n]->type!=mod_alias || !Cache_Check(&models[n]->cache))continue;
        if(!posed){AW_SkelPose(parts_table,(float)frame,world);posed=1;}
        AW_SkelBoneTag((const float (*)[4])world[bone],scale,tag);
        memcpy(origins[n],tag,3*sizeof(float));memcpy(angles[n],tag+3,3*sizeof(float));n++;
    }
    return n;
}
int AW_ViewInventoryEquipment(model_t *models[2],float origins[2][3],float angles[2][3]){
    int kind,n=0,frame;model_t *actual;aw_inventory_item_t item;float tag[6];
    if(!AW_ViewInventoryBody(&actual,&frame))return 0;
    if(inventory_parts_frame>=0 && body_parts && parts_table && actual==part_models[0])
        return parts_inventory_items(frame,models,origins,angles);
    if(!AW_ItemsAliasTag(actual,-1,0,NULL))return 0;
    for(kind=0;kind<2;kind++){
        int slot=kind?AW_SLOT_LEFT:AW_SLOT_RIGHT;
        if(kind && !inventory_left)continue;
        if(!AW_InventoryEquippedItem(slot,&item) || !item.model[0] ||
           (kind && (item.category!=AW_INV_ARMOUR || item.subtype!=8)))continue;
        models[n]=Mod_ForName(item.model,false);
        if(!models[n] || models[n]->type!=mod_alias || !Cache_Check(&models[n]->cache) ||
           !AW_ItemsAliasTag(actual,frame,kind,tag))continue;
        memcpy(origins[n],tag,3*sizeof(float));memcpy(angles[n],tag+3,3*sizeof(float));n++;
    }
    return n;
}
/* The carried torch in the inventory picture (PLAYER-TORCH-THIRDPERSON-38; rule from
 * OpenMW characterpreview.cpp InventoryPreview::update: a light in the carried-left slot
 * plays the torch group on the left arm and npcanimation.cpp showCarriedLeft shows its
 * mesh). The torch body is already the picture's pose; its frame-aligned held alias is
 * drawn at the same frame and placement. 1 = draw MODEL at FRAME with the body. */
int AW_ViewInventoryHeld(model_t **model,int *frame){
    model_t *actual;int shown;
    if(!model || !frame || !AW_ViewInventoryBody(&actual,&shown) || !body_torch || actual!=body_model ||
       !held_ready() || shown<0 || shown>=held_model->numframes)return 0;
    *model=held_model;*frame=shown;return 1;
}
static cvar_t aw_inventory_preview_reserve={"aw_inventory_preview_reserve","0",true};
static const char *unavailable_reason="the pose model did not load";
/* UI-INVENTORY-PREVIEW-STILL-42: 0 (default) = the original still picture, rendered once per
 * equipment change (aw_worldui.c); 1 = the old live preview, drawn every frame and turnable. */
static cvar_t aw_inventory_preview_live={"aw_inventory_preview_live","0",true};
int AW_ViewInventoryLive(void){return aw_inventory_preview_live.value!=0;}
/* Bytes the pose model's load needs (see AW_ViewInventoryBody); -1 when it is absent. */
static int inventory_need(const char *path){
    FILE *f=NULL;int size=COM_FOpenFile((char *)path,&f);
    if(!f)return -1;
    fclose(f);
    if(aw_inventory_preview_reserve.value>0)return (int)(aw_inventory_preview_reserve.value*1024*1024);
    return 3*size+256*1024;
}
/* Ten companion frames: unarmed, then original melee weapon types 0..8.
 * The builder samples each original inventory group at its START key. */
int AW_ViewInventoryBody(model_t **model,int *frame){
    aw_inventory_item_t item;char path[64];int type=-1;
    extern int hunk_size,hunk_low_used,hunk_high_used;
    inventory_parts_frame=-1;
    if(!model || !frame || !body_ready() || body_index<0)return 0;
    inventory_left=1;
    /* Torch preview retains its existing companion until its dedicated
     * inventory left-arm layer and held resource are converted together. */
    if(body_torch){
        *model=body_model;*frame=body.model==body_model?body.frame:0;
        if(*frame<0 || *frame>=body_model->numframes)*frame=0;
        return 1;
    }
    if(AW_InventoryEquippedItem(AW_SLOT_RIGHT,&item)){
        if(item.category!=AW_INV_WEAPON || item.subtype<0 || item.subtype>11)return 0;
        type=item.subtype;
    }
    /* a bow, crossbow or thrown weapon: the one-handed pose (OpenMW characterpreview.cpp: a ranged weapon's own group,
     * else the one-handed fallback); a bow or crossbow hides the shield (two-handed) */
    {int ranged=type>=9,left_shown=type!=2 && type!=4 && type!=5 && type!=6 && type!=8 && type!=9 && type!=10;
    if(ranged)type=1;
    inventory_left=left_shown;
    if(body_parts && parts_table && part_models[0]){
        int f=parts_inventory_frame(type,&inventory_left);
        if(ranged)inventory_left=left_shown;
        if(f>=0){inventory_parts_frame=f;*model=part_models[0];*frame=f;return 1;}
        if(!inventory_parts_said){
            inventory_parts_said=1;
            Con_Printf("Inventory picture: the table %s has no inventory pose; the baked companion draws.\n",parts.table);
        }
    }
    strcpy(path,bodies[body_index].path);strcpy(path+strlen(path)-4,"_i.mdl");
    if(strcmp(path,inventory_body_path)){
        AW_ViewInventoryClear();strcpy(inventory_body_path,path);
        inventory_left=left_shown;
    }
    }
    if(inventory_failed)return 0;
    if(!inventory_model || !Cache_Check(&inventory_model->cache)){
        /* UI-INVENTORY-PREVIEW-GAP-41: admit the load by what it needs, not a blanket 2 MiB:
         * Mod_ForName holds the file as a temporary (high hunk), unpacks it on the low hunk and
         * copies it into the cache, so at most three times the file size, plus a 256 KiB margin.
         * The old fixed rule refused every area leaving under 2 MiB (Seyda Neen CHIM: 1.96 MiB);
         * aw_inventory_preview_reserve 2 brings it back (DON'T DELETE ANY METHOD). */
        int need=inventory_need(path),gap=hunk_size-hunk_low_used-hunk_high_used;
        if(need<0){unavailable_reason="no inventory pose model in this image";goto unavailable;}
        if(gap<need){unavailable_reason="not enough free memory in this area";goto unavailable;}
        inventory_model=Mod_ForName(path,false);
        if(!inventory_model || inventory_model->type!=mod_alias ||
           inventory_model->numframes!=10 || !Cache_Check(&inventory_model->cache))goto unavailable;
    }
    *model=inventory_model;*frame=type+1;return 1;
 unavailable:
    if(inventory_model && inventory_model->type==mod_alias && inventory_model->cache.data)
        Cache_Free(&inventory_model->cache);
    inventory_model=NULL;inventory_failed=1;
    Con_Printf("Original inventory poses unavailable: %s (%s).\n",unavailable_reason,path);
    return 0;
}
static float death_seconds(void) {
    const aw_anim_group_t *g=&body_anim.g[AW_ANIM_DEATH];
    if(body_model && g->present && g->count>1)return (g->count-1)*g->step;
    return 1.5f;    /* AmiWind: no death animation; the original waits for it to finish */
}
/* The body's height under the player's origin: the player's hull floor (world.qc setsize). */
static float feet(void) {
    edict_t *p=local_player();
    return p && p->v.mins[2]<0?-p->v.mins[2]:16.625f;
}
/* The body's shield block (COMBAT-BLOCKING-36): the block group (base_anim "shield: block start" ..
 * "block stop", hit key "block hit"; OpenMW plays it on a block, character.cpp refreshHitRecoilAnims).
 * While the player guards (aw_combat_block 1, an AmiWind extension) the shield rises to the hit key
 * and stays up; after a blocked blow the rest of the clip plays. -1 = no block frame now. */
static float guard_time;
static int body_block_frame(float dt) {
    const aw_anim_group_t *g=&body_anim.g[AW_ANIM_BLOCK];int hold,i;float left;
    if(!g->present || g->count<1){guard_time=0;return -1;}
    /* Compact player block pairs are START/HIT, not two uniform clip
     * samples. STEP*COUNT remains the authored clip duration; X is its
     * original hit fraction. Retain larger legacy groups below. */
    if(g->count==2 && g->x>0 && g->x<1){
        if(AW_CombatGuarding()){
            guard_time+=dt;
            return g->base+(guard_time>=g->x*g->step*g->count?1:0);
        }
        guard_time=0;
        return AW_CombatBlockShown()>0?g->base+1:-1;
    }
    hold=g->x>0 && g->x<1?(int)(g->x*(g->count-1)+.5f):g->count/2;
    if(AW_CombatGuarding()){
        guard_time+=dt;i=(int)(guard_time/g->step);
        if(g->x>0 && g->x<1){
            if(guard_time>=g->x*g->step*g->count)i=hold;
            else if(i>=hold)i=hold>0?hold-1:0;
        }
        if(i>hold)i=hold;
        return g->base+i;
    }
    guard_time=0;left=AW_CombatBlockShown();
    if(!(left>0))return -1;
    i=g->count-1-(int)(left/g->step);if(i<hold)i=hold;if(i>g->count-1)i=g->count-1;
    return g->base+i;
}
static int body_fists_ready(edict_t *p) {
    eval_t *v;
    if(!p || p->v.health<=0 || p->v.waterlevel>=2)return 0;
    v=GetEdictFieldValue(p,"aw_hand_goal");if(!v || v->_float!=1)return 0;
    v=GetEdictFieldValue(p,"aw_hand_state");
    if(!v || (v->_float!=2 && v->_float!=3))return 0;
    /* The carried-light pose is separate; do not show two fists around a
     * missing torch. Attack overlays and carried equipment are separate. */
    v=GetEdictFieldValue(p,"aw_torch");return !v || v->_float!=1;
}
static int body_hand_layer(edict_t *p,int frame) {
    eval_t *v;int state;float started,duration,fraction;
    if(!AW_ANIMKIT || !aw_anim_kit_enabled || !body_layers.count || !p || p->v.health<=0 ||
       p->v.waterlevel>=2 || p->v.movetype!=MOVETYPE_WALK)return -1;
    v=GetEdictFieldValue(p,"aw_hand_state");if(!v || (v->_float!=1 && v->_float!=3 && v->_float!=4))return -1;
    state=(int)v->_float;
    v=GetEdictFieldValue(p,"aw_torch");if(v && v->_float==1)return -1;
    v=GetEdictFieldValue(p,"aw_hand_started");if(!v)return -1;started=v->_float;
    duration=AW_HandDuration(state==1?AW_HAND_DRAW:state==3?AW_HAND_PUNCH:AW_HAND_LOWER,0);
    if(!(duration>0 && duration<=60))return -1;
    /* The authoritative QuakeC state owns this clock; never restart it when
     * switching camera, gait or landing. The legs retain their own frame. */
    fraction=((float)sv.time-started)/duration;
    if(fraction>1)fraction=1;
    return AW_ViewLayerFrame(&body_layers,state,frame,fraction);
}
/* ---- the weapon's stance on the assembled body (WEAPONS-57) ----
 * With a weapon drawn the body plays the original's groups for that weapon from its shared table, as the NPCs do
 * (aw_animkit.c): drawing "equip", putting away "unequip", a swing the weapon's chop/slash/thrust to its large follow,
 * else the stance's idle, walk, run (forward, back, left, right) and jump (AW_AnimPick: OpenMW 0.51 character.cpp,
 * weapontype.cpp). The draw, swing and put-away follow the first-person hand clock, so both views and the strike's hit
 * key stay together. The table is the one the body already uses: no new data, a group looked up by name only when the
 * state changes. aw_player_stances 0 (saved) = the previous way: the fixed layout (the bare-hand poses) with the weapon
 * on the hand bone. */
static cvar_t stances_cvar={"aw_player_stances","1",true};
static struct {
    aw_pick_state_t last;int picked,from,to,lfrom,loop;float t;const aw_skel_table_t *table;
    char group[AW_PICK_NAME];const char *rule;unsigned long changes;
} stance;
static int stance_has(void *c,const char *name){return AW_SkelGroup((const aw_skel_table_t *)c,name)>=0;}
static int stance_key(const aw_skel_table_t *t,int g,const char *key){
    aw_skel_group_t gg;
    AW_SkelGroupAt(t,g,&gg);
    if(!strcmp(key,"start"))return (int)gg.first;
    if(!strcmp(key,"stop"))return (int)gg.last;
    return AW_SkelKeyFrame(t,g,key);
}
static float hand_fraction(edict_t *p,int clip){
    eval_t *v=GetEdictFieldValue(p,"aw_hand_started");float d=AW_HandDuration(clip,0),f;
    if(!v || !(d>0 && d<=60))return 1;
    f=((float)sv.time-v->_float)/d;
    return f<0?0:f>1?1:f;
}
/* PLAYER-ANIM-GROUPS-NOT-PLAYED-66: turning on the spot (OpenMW character.cpp: any turn while standing, held 0.05 s
 * after the last one: mTurnAnimationThreshold); the view's yaw a frame before */
static struct {float yaw,hold;int dir,seen;} turn;
static int body_turn(int move,float dt){
    float d=cl.viewangles[YAW]-turn.yaw;
    while(d>180)d-=360;
    while(d<-180)d+=360;
    if(!turn.seen){turn.seen=1;d=0;}
    turn.yaw=cl.viewangles[YAW];
    if(move==AW_PM_NONE && (d>.01f || d<-.01f)){turn.dir=d>0?AW_PM_TURNLEFT:AW_PM_TURNRIGHT;turn.hold=.05f;}
    else if((turn.hold-=dt)<=0 || move!=AW_PM_NONE){turn.dir=0;turn.hold=0;}
    return turn.dir;
}
/* The body's frame for the drawn weapon's stance, or -1 (nothing drawn, bare hands, swimming, a torch, no such group). */
static int body_stance_frame(edict_t *p,int group,int air,float dt,float rate){
    eval_t *v;aw_pick_state_t s;aw_pick_t o;aw_pick_player_t in;int hand,goal,move=AW_PM_NONE,run=0,gi,react,roll;float age;
    if(!stances_cvar.value || !body_parts || !parts_table || !p || p->v.health<=0)return -1;
    if((v=GetEdictFieldValue(p,"aw_torch")) && v->_float==1)return -1;
    hand=(v=GetEdictFieldValue(p,"aw_hand_state"))?(int)v->_float:0;
    goal=(v=GetEdictFieldValue(p,"aw_hand_goal"))?(int)v->_float:0;
    if(group==AW_ANIM_WALK || group==AW_ANIM_RUN || group==AW_ANIM_READYWALK || group==AW_ANIM_READYRUN){
        /* the motion against the facing, as aw_animkit.c drive() reads an NPC's */
        float yaw=cl.viewangles[YAW]*(float)M_PI/180,fx=Q_CosRad(yaw),fy=Q_SinRad(yaw);
        float fwd=cl.velocity[0]*fx+cl.velocity[1]*fy,side=cl.velocity[0]*fy-cl.velocity[1]*fx;
        run=group==AW_ANIM_RUN || group==AW_ANIM_READYRUN;
        if(side*side>fwd*fwd)move=side>0?AW_PM_RIGHT:AW_PM_LEFT;else move=fwd>=0?AW_PM_FORWARD:AW_PM_BACK;
    }
    /* READY-MAGIC-SHOWS-WEAPON-65 / PLAYER-CASTING-59 (v0.0.66): the spell stance holds no weapon: the original's spell
     * groups (idlespell, spellcast equip / unequip, the cast by the selected spell's first range) */
    /* PLAYER-ANIM-GROUPS-NOT-PLAYED-66 (v0.0.66): with the stance, the sneak (the key or ForceSneak), the turn on the
     * spot and the reaction to the last blow (hit1..5, knockdown, knockout: AW_CombatPlayerReaction) */
    memset(&in,0,sizeof(in));
    in.weapon=aw_magic_readied?AW_PW_SPELL:AW_InventoryEquippedWeaponType();in.hand=hand;in.goal=goal;in.move=move;
    in.run=run;in.attack=AW_CombatPlayerAttackType();in.air=air;in.swim=p->v.waterlevel>=2;
    in.sneak=AW_MoveSneaking() || aw_move_force_sneak;in.turn=body_turn(move,dt);
    react=AW_CombatPlayerReaction(&age,&roll);
    in.react=react==1?AW_PE_HIT:react==2?AW_PE_KNOCKDOWN:react==3?AW_PE_KNOCKOUT:0;in.roll=roll;
again:
    if(!AW_PickPlayerBody(&in,&s)){stance.picked=0;return -1;}
    if(aw_magic_readied)s.range=(unsigned char)(aw_magic_cast_range>=0 && aw_magic_cast_range<3?aw_magic_cast_range:AW_PR_TARGET);
    if(!stance.picked || stance.table!=parts_table || memcmp(&s,&stance.last,sizeof(s))){
        int from=-1,to=-1;
        stance.last=s;stance.picked=1;stance.table=parts_table;
        if(AW_AnimPick(&s,stance_has,(void *)parts_table,&o) && (gi=AW_SkelGroup(parts_table,o.group))>=0){
            from=stance_key(parts_table,gi,o.start);to=stance_key(parts_table,gi,o.stop);
            if(from<0 || to<from){aw_skel_group_t gg;AW_SkelGroupAt(parts_table,gi,&gg);from=(int)gg.first;to=(int)gg.last;}
            stance.lfrom=o.loop_start[0]?stance_key(parts_table,gi,o.loop_start):-1;
            if(from!=stance.from || strcmp(o.group,stance.group))stance.t=0;
            memcpy(stance.group,o.group,sizeof(stance.group));stance.rule=o.rule;stance.loop=o.loop;stance.changes++;
        }else stance.group[0]=0;
        stance.from=from;stance.to=to;
    }
    if(stance.from<0 || stance.to>=parts_table->frames){
        if(in.react==AW_PE_HIT){in.react=0;goto again;}   /* no hit group in the table: the stance */
        return -1;
    }
    if(s.event==AW_PE_HIT || s.event==AW_PE_KNOCKDOWN || s.event==AW_PE_KNOCKOUT){
        /* the reaction from the moment of the blow (or of going down), at the table's rate: a hit plays once and then
         * gives way to the stance; a knockdown holds its last frame until the player gets up; a knockout loops from its
         * "loop start" while the player is out */
        float f=(float)stance.from+age*(parts_table->rate>0?parts_table->rate:15);
        if(s.event==AW_PE_HIT && f>(float)stance.to){in.react=0;goto again;}
        if(s.event==AW_PE_KNOCKOUT && stance.lfrom>stance.from && stance.lfrom<stance.to && f>(float)stance.to)
            f=(float)(stance.lfrom+(int)(f-(float)stance.lfrom)%(stance.to-stance.lfrom));   /* whole frames: no libm */
        return f>(float)stance.to?stance.to:(int)f;
    }
    switch(s.event){
    case AW_PE_EQUIP:return stance.from+(int)(hand_fraction(p,AW_HAND_DRAW)*(float)(stance.to-stance.from)+.5f);
    case AW_PE_UNEQUIP:return stance.from+(int)(hand_fraction(p,AW_HAND_LOWER)*(float)(stance.to-stance.from)+.5f);
    case AW_PE_ATTACK:return stance.from+(int)(hand_fraction(p,AW_HAND_PUNCH)*(float)(stance.to-stance.from)+.5f);
    case AW_PE_JUMP:return stance.lfrom>=stance.from && stance.lfrom<=stance.to?stance.lfrom:stance.from;   /* held in the air */
    default:
        return AW_AnimKitSpanFrame((unsigned)stance.from,(unsigned)stance.to,parts_table->rate,&stance.t,
                                   dt*(move!=AW_PM_NONE && rate>0?rate:1),1,NULL);
    }
}
/* ---- the body's animation state across camera and control changes (PLAYER-VANITY-WALK-STUCK-67) ----
 * The maintainer, 18 November 2026, on the v0.0.67-dev2 image: after the idle vanity orbit (also after view switches,
 * perhaps noclip) the player's walk and run no longer played in third person (the body glided, small jerks, as if the
 * group restarted every frame) while attacks, the sneak and swimming still played; a map load brought them back. A
 * load re-makes the body's animation state; a camera or control change did not. Now every change of what that state
 * lives through (aw_view.h aw_view_body_sig_t: the view mode, noclip, swimming, a menu or dialogue over play, the body
 * drawn or not) restarts it as a load does: the move group, the jump and landing state, the weapon stance's pick and
 * clock, the turn on the spot. The restarts, and the move group's and the air state's changes a second (a group
 * restarted every frame shows there), are in "dbg camera". */
static aw_view_body_sig_t body_sig;
static int body_restart_on=1;   /* dbg camera motion restart on/off (not saved): off = the earlier way, for comparison */
static struct {unsigned long restarts,switches,air_flips,window_switches,window_air,rate_switches,rate_air;double window;
               int last_group,last_air;float speed;char why[24];} motion;
static void body_motion_restart(const char *why) {
    AW_ViewBodyRestart(&body_play,&body_air);
    stance.picked=0;stance.t=0;stance.group[0]=0;stance.from=stance.to=-1;stance.rule=NULL;
    memset(&turn,0,sizeof(turn));
    motion.restarts++;strncpy(motion.why,why,sizeof(motion.why)-1);motion.why[sizeof(motion.why)-1]=0;
}
/* once a frame, after the view's own changes (AW_ViewFrame): a change of the signature restarts the body's animation */
static void body_motion_check(edict_t *p) {
    aw_view_body_sig_t now,was=body_sig;
    memset(&now,0,sizeof(now));
    now.valid=1;now.mode=view.mode;now.movetype=p?(int)p->v.movetype:-1;now.swimming=p && p->v.waterlevel>=2;
    now.playing=key_dest==key_game && !con_forcedup;now.drawn=owned;
    if(AW_ViewBodySigChanged(&body_sig,&now) && body_restart_on)
        body_motion_restart(!was.valid?"map":was.mode!=now.mode?"view":was.movetype!=now.movetype?"movetype":
                            was.swimming!=now.swimming?"water":was.playing!=now.playing?"menu":"drawn");
}
/* the body's move group and air state, counted a second at a time (the diagnosis of a group restarted every frame) */
static void body_motion_count(int air,float speed) {
    if(body_play.group!=motion.last_group){motion.switches++;motion.window_switches++;motion.last_group=body_play.group;}
    if((air>=0)!=motion.last_air){motion.air_flips++;motion.window_air++;motion.last_air=air>=0;}
    motion.speed=speed;
    if(realtime-motion.window>=1 || realtime<motion.window){
        motion.rate_switches=motion.window_switches;motion.rate_air=motion.window_air;
        motion.window_switches=motion.window_air=0;motion.window=realtime;
    }
}
float AW_ViewRaceHeight(void) {return body_parts && parts.height>.5f && parts.height<2?parts.height:1;}
entity_t *AW_ViewBody(entity_t *ent) {
    float speed=0,rate=1,dt=(float)host_frametime;int group,block=-1,air,fists,layer;edict_t *p=local_player();
    held_visible=0;held_cursor=held_draw_count=0;
    if(!owned || !body_ready() || orbit.active)return NULL;     /* the orbit: the player is not there */
    fists=body_fists_ready(p);
    if(dt<0)dt=0;
    if(dt>.25f)dt=.25f;
    if(death.stage!=AW_DEATH_NONE)group=AW_ANIM_DEATH;
    else{
        speed=(float)sqrt(cl.velocity[0]*cl.velocity[0]+cl.velocity[1]*cl.velocity[1]+
            (p && p->v.waterlevel>=2?cl.velocity[2]*cl.velocity[2]:0));
        group=AW_AnimPlayerMoveGroup(&body_anim,speed,p && p->v.waterlevel>=2,fists,&rate);
    }
    body=*ent;body.model=body_model;
    body.frame=AW_AnimPlayerAdvance(&body_anim,&body_play,group,dt,rate);
    air=AW_AnimAirFrame(&body_anim,&body_air,
        death.stage==AW_DEATH_NONE && p && p->v.movetype==MOVETYPE_WALK && p->v.waterlevel<2,
        p && !((int)p->v.flags&FL_ONGROUND),p && p->v.velocity[2]>0,fists,dt);
    if(air>=0)body.frame=air;
    body_motion_count(air,speed);
    if(death.stage==AW_DEATH_NONE && (layer=body_hand_layer(p,body.frame))>=0)body.frame=layer;
    if(death.stage==AW_DEATH_NONE && (layer=body_stance_frame(p,group,air>=0,dt,rate))>=0)body.frame=layer;
    if(death.stage==AW_DEATH_NONE && (block=body_block_frame(dt))>=0)body.frame=block;
    /* the assembled body's frame is a frame of its table (every part draws it); the baked body's one of its own */
    if(body.frame<0 || body.frame>=(body_parts && parts_table?parts_table->frames:body_model->numframes))body.frame=0;
    /* Converted characters face local +Y; Quake yaw 0 is +X (world.qc aw_npc_idle). */
    body.angles[PITCH]=0;body.angles[ROLL]=0;
    body.angles[YAW]=(death.stage!=AW_DEATH_NONE?death_angles[YAW]:view.mode==AW_VIEW_PREVIEW || view.mode==AW_VIEW_VANITY?anchor[YAW]:cl.viewangles[YAW])-90;
    body.origin[2]=ent->origin[2]-feet();
    body.colormap=vid.colormap;body.skinnum=0;body.efrag=NULL;body.topnode=NULL;body.aw_sprite_scale=1;
    body.effects&=~AW_EF_ALIAS_SCALE;body.aw_alias_zscale=0;
    if(body_parts){
        /* the parts are built at the unit scale; the race's own weight (x, y) and height (z) here, after posing, as
         * the original scales the whole actor (aw_skel.h: a non-uniform scale does not commute with the bones) */
        body.effects|=AW_EF_ALIAS_SCALE;body.aw_sprite_scale=parts.weight;body.aw_alias_zscale=parts.height;
    }
    return &body;
}

/* The assembled body's other parts and its held items: the weapon in the right hand while it is drawn, the shield on
 * the left arm whenever one is worn, except while a two-handed weapon is drawn (rule from OpenMW
 * actoranimation.cpp updateCarriedLeftVisible, read not copied: no sheathing by default; the original shows no
 * weapon at the hip). Each item on its bone of the table posed at the body's frame (AW_SkelBoneTag, as the skeletal
 * NPCs' items: aw_items.c skel_rows). */
/* The held items' rows, read from the catalogue only when the id in a hand changes (a catalogue read is a disk
 * read: per frame it cost the frame rate and set off the emulator's disk stall). */
static struct {char id[64];int have;aw_inventory_item_t item;} parts_hand[2];
static const aw_inventory_item_t *parts_hand_item(int kind) {
    const char *id=aw_state.inventory.equipped[kind?AW_SLOT_LEFT:AW_SLOT_RIGHT];
    if(strcmp(parts_hand[kind].id,id)){
        Q_strncpy(parts_hand[kind].id,(char *)id,63);parts_hand[kind].id[63]=0;
        parts_hand[kind].have=id[0] && AW_InventoryEquippedItem(kind?AW_SLOT_LEFT:AW_SLOT_RIGHT,&parts_hand[kind].item);
    }
    return parts_hand[kind].have?&parts_hand[kind].item:NULL;
}
/* HELD-LIGHT-OWN-MODEL-61: a held candle, candlestick or lantern on the assembled body: the left arm on the table's
 * "torch" group (as a skeletal guard holds his torch, aw_items.c AW_ItemsTorchLayer: the group's frames in turn with
 * the body's), the light's own item model on the shield bone at its carried-light place, its flames from it. */
static int parts_light_layer(int frame,float *layer_frame,int *root) {
    /* the arm's root and the group's frames looked up once per table (asked for every part drawn) */
    static const aw_skel_table_t *seen;static int arm=-1,first,span;
    if(!parts_table)return 0;
    if(seen!=parts_table){
        aw_skel_group_t g;int i;
        seen=parts_table;span=0;
        arm=AW_SkelLeftArmRoot(parts_table,parts.shield_bone,parts.weapon_bone);
        if(arm>=0 && (i=AW_SkelGroup(parts_table,"torch"))>=0){
            AW_SkelGroupAt(parts_table,i,&g);first=(int)g.first;span=(int)(g.last-g.first)+1;
        }
    }
    if(arm<0 || span<1)return 0;
    *root=arm;
    *layer_frame=(float)(first+(unsigned)(frame<0?0:frame)%(unsigned)span);
    return 1;
}
/* aw_items.c aw_items_player_layer: the renderer poses the body's parts so while the light is held in third person */
static int player_light_layer(const model_t *m,const void *skel_table,int frame,float *layer_frame,int *root) {
    extern int r_framecount;
    static int asked=-1,held;      /* the held light asked once a frame, not once per drawn part */
    if(!body_parts || !parts_table || skel_table!=(const void *)parts_table || !m || !chase_active.value ||
       !parts_in_use(m))return 0;
    if(asked!=r_framecount){asked=r_framecount;held=AW_HeldLight()!=NULL;}
    return held && parts_light_layer(frame,layer_frame,root);
}
static model_t *held_light_model;            /* the held light's model drawn this frame (NULL none) */
static float held_light_place[6];            /* its origin and alias angles */
/* the host frame (realtime) it was placed in: the body's items are placed when the client relinks its entities, before
 * the frame's render, so the render's own counter is one ahead of it by then */
static double held_light_time=-1;
static void parts_draws(edict_t *p) {
    static float world[AW_SKEL_MAX_BONES][3][4];static const aw_skel_table_t *posed;static int posed_frame=-1;
    static float posed_layer=-1;
    eval_t *goal;int i,kind,drawn,bone,root=-1,layered=0;float tag[6],scale[3],layer=-1;
    const aw_inventory_item_t *right,*item;const aw_held_light_t *light;
    held_light_model=NULL;
    for(i=1;i<parts.count && held_draw_count<AW_PARTS_MAX;i++){
        part_ents[i]=body;part_ents[i].model=part_models[i];
        held_draws[held_draw_count++]=&part_ents[i];
    }
    if(!p || p->v.health<=0 || p->v.waterlevel>=2 || !parts_table)return;
    goal=GetEdictFieldValue(p,"aw_hand_goal");
    drawn=goal && AW_HandShowsWeapon(goal->_float==1,aw_magic_readied);   /* the spell stance: no weapon in the hand */
    right=parts_hand_item(0);
    scale[0]=scale[1]=parts.weight*.25f;scale[2]=parts.height*.25f;
    light=AW_HeldLight();
    if(light)layered=parts_light_layer(body.frame,&layer,&root);
    for(kind=0;kind<2;kind++){
        model_t *model;entity_t *out=&inventory_held[kind];
        bone=kind?parts.shield_bone:parts.weapon_bone;
        if(bone<0 || bone>=parts_table->bones)continue;
        if(kind && light){
            model=Mod_ForName((char *)light->model,false);
            if(!model || model->type!=mod_alias || !Cache_Check(&model->cache))continue;
        }else{
            if(!kind){if(!drawn || !right)continue;item=right;}
            /* READY-MAGIC-SHOWS-WEAPON-65 (v0.0.66): the shield is put away while magic is ready, as for a drawn
             * two-handed weapon (AW_HandCarriesLeft; OpenMW: the spell is a two-handed draw) */
            else if(!(item=parts_hand_item(1)) || item->category!=AW_INV_ARMOUR || item->subtype!=8 ||
                    !AW_HandCarriesLeft(aw_magic_readied) || (drawn && right && AW_TWO_HANDED(right->weapon)))continue;
            if(!item->model[0])continue;
            model=Mod_ForName((char *)item->model,false);
            if(!model || model->type!=mod_alias || !Cache_Check(&model->cache))continue;
        }
        if(posed!=parts_table || posed_frame!=body.frame || posed_layer!=(layered?layer:-1)){
            if(layered)AW_SkelPoseLayer(parts_table,(float)body.frame,layer,root,world);
            else AW_SkelPose(parts_table,(float)body.frame,world);
            posed=parts_table;posed_frame=body.frame;posed_layer=layered?layer:-1;
        }
        AW_SkelBoneTag((const float (*)[4])world[bone],scale,tag);
        *out=body;out->model=model;out->frame=0;out->effects&=~AW_EF_ALIAS_SCALE;out->aw_alias_zscale=0;out->aw_sprite_scale=1;
        AW_ItemsPose(tag,body.origin,body.angles[YAW],out->origin,out->angles);
        if(kind && light){
            float origin[3],angles[3];
            VectorCopy(out->origin,origin);VectorCopy(out->angles,angles);
            AW_BlockCompose(origin,angles,light->offset,out->origin,out->angles);
            held_light_model=model;
            memcpy(held_light_place,out->origin,3*sizeof(float));memcpy(held_light_place+3,out->angles,3*sizeof(float));
            held_light_time=realtime;
        }
        held_draws[held_draw_count++]=out;
    }
}
/* aw_torch.h aw_view_held_flames / aw_view_held_light: the third-person held light's flames and light place */
/* placed in this host frame (the flames), or in the previous one too (SLACK: the light, set before this frame's relink) */
static int held_light_placed(int slack) {
    return held_light_model && held_light_time>=0 && (held_light_time==realtime || (slack && realtime-held_light_time<.25));
}
static int view_held_flames(vec3_t out[AW_HELD_FLAMES]) {
    const aw_held_light_t *light=AW_HeldLight();vec3_t forward,right,up,angles;int i,j;
    if(!light || !owned || !chase_active.value || !held_light_placed(0))return 0;
    memcpy(angles,held_light_place+3,3*sizeof(float));angles[PITCH]=-angles[PITCH];
    AngleVectors(angles,forward,right,up);
    for(i=0;i<light->flames && i<AW_HELD_FLAMES;i++)
        for(j=0;j<3;j++)out[i][j]=held_light_place[j]+light->flame[i][0]*forward[j]-light->flame[i][1]*right[j]+
                                  light->flame[i][2]*up[j];
    return i;
}
static int view_held_light(vec3_t out) {
    const aw_held_light_t *light;vec3_t forward,right,up,angles;edict_t *p=local_player();trace_t t;int j;
    if(!p || !(light=AW_HeldLight()) || !owned || !chase_active.value || !held_light_placed(1))return 0;
    /* from its first flame; a light without one (the paper lantern) from its model's place */
    memcpy(out,held_light_place,3*sizeof(float));
    if(light->flames){
        memcpy(angles,held_light_place+3,3*sizeof(float));angles[PITCH]=-angles[PITCH];
        AngleVectors(angles,forward,right,up);
        for(j=0;j<3;j++)out[j]+=light->flame[0][0]*forward[j]-light->flame[0][1]*right[j]+light->flame[0][2]*up[j];
    }
    if(SV_PointContents(out)!=CONTENTS_EMPTY)return 0;
    t=SV_Move(p->v.origin,vec3_origin,vec3_origin,out,MOVE_NOMONSTERS,p);
    return !t.startsolid && !t.allsolid && t.fraction==1;
}
static entity_t *view_held(entity_t *draw) {
    edict_t *p=local_player();eval_t *goal;int kind;float tag[6];aw_inventory_item_t item,right;
    if(draw!=&body)return NULL;
    if(!held_cursor && body_parts){held_draw_count=0;parts_draws(p);}
    else if(!held_cursor){
        held_draw_count=0;
        goal=p?GetEdictFieldValue(p,"aw_hand_goal"):NULL;
        if(p && goal && AW_HandShowsWeapon(goal->_float==1,aw_magic_readied) && p->v.health>0 && p->v.waterlevel<2 && AW_ViewEquipmentReady()){
            int have_right=AW_InventoryEquippedItem(AW_SLOT_RIGHT,&right);
            for(kind=0;kind<2 && held_draw_count<2;kind++){
                model_t *model;entity_t *out=&inventory_held[kind];
                if(kind && (body_torch || !have_right || AW_TWO_HANDED(right.weapon)))continue;
                if(!AW_InventoryEquippedItem(kind?AW_SLOT_LEFT:AW_SLOT_RIGHT,&item) || !item.model[0] ||
                   !AW_ItemsAliasTag(body_model,body.frame,kind,tag))continue;
                model=Mod_ForName(item.model,false);
                if(!model || model->type!=mod_alias || !Cache_Check(&model->cache))continue;
                *out=body;out->model=model;out->frame=0;
                AW_ItemsPose(tag,body.origin,body.angles[YAW],out->origin,out->angles);
                held_draws[held_draw_count++]=out;
            }
        }
        /* The body needs no cache test here: the renderer reloads it itself, and the
         * held torch only copies its frame and placement (PLAYER-TORCH-THIRDPERSON-38). */
        if(held_draw_count<2 && body_torch && held_model && AW_TorchEquipped() && held_ready() &&
           body.frame>=0 && body.frame<body_emitter.count && body.frame<held_model->numframes){
            held_body=body;held_body.model=held_model;
            held_body.frame=body.frame;
            VectorCopy(body.origin,held_body.origin);VectorCopy(body.angles,held_body.angles);
            held_visible=1;held_draws[held_draw_count++]=&held_body;
        }
    }
    if(held_cursor>=held_draw_count){held_cursor=AW_PARTS_MAX+2;return NULL;}
    return held_draws[held_cursor++];
}

static int view_torch_emitter(vec3_t out) {
    vec3_t forward,right,up;int j;edict_t *p=local_player();
    if(!owned || !chase_active.value || !held_visible || !body_torch || !p || p->v.waterlevel>=2 ||
       !AW_TorchEquipped() || !body.model || !held_model ||
       !Cache_Check(&held_model->cache) || body.frame<0 || body.frame>=body_emitter.count)return 0;
    AngleVectors(body.angles,forward,right,up);
    for(j=0;j<3;j++)out[j]=body.origin[j]+body_emitter.point[body.frame][0]*forward[j]-
        body_emitter.point[body.frame][1]*right[j]+body_emitter.point[body.frame][2]*up[j];
    return 1;
}
static int view_torch_light(vec3_t out) {
    edict_t *p=local_player();trace_t t;
    if(!p || !view_torch_emitter(out) || SV_PointContents(out)!=CONTENTS_EMPTY)return 0;
    t=SV_Move(p->v.origin,vec3_origin,vec3_origin,out,MOVE_NOMONSTERS,p);
    return !t.startsolid && !t.allsolid && t.fraction==1;
}

/* ---- the camera ---- */
static void trace(vec3_t from,vec3_t to,vec3_t out,float *fraction) {
    edict_t *p=local_player();
    if(p){
        trace_t t=SV_Move(from,vec3_origin,vec3_origin,to,MOVE_NOMONSTERS,p);
        *fraction=t.allsolid?0:t.fraction;VectorCopy(t.endpos,out);return;
    }
    {extern void TraceLine(vec3_t,vec3_t,vec3_t);vec3_t d;float a,b;
     TraceLine(from,to,out);VectorSubtract(out,from,d);a=Length(d);VectorSubtract(to,from,d);b=Length(d);
     *fraction=b>0?a/b:1;}
}
/* ---- dbg cam orbit (aw_cam.c, docs/CAMERA_MARKS.md "Orbit") ----
 * The vanity camera turned on another centre: the same placement (chase_active, the point
 * trace and obstacle pull-in below, the full view without HUD), around the entity under the
 * crosshair (followed as it moves, by its drawn frame box), an entity by its original
 * reference, or a point, at a set speed in degrees a second. While it runs the player is
 * detached from the world: noclip, Quake's god mode and notarget (combat and idle voices
 * check notarget: aw_combat.c, pr_cmds.c), hidden, held in place, and every game key goes to
 * the orbit (+/- speed, 0 holds, wheel distance, right click or Esc ends); the end restores
 * the position, view, movement and flags as they were. */
#define ORBIT_MIN_DISTANCE 8
#define ORBIT_MAX_DISTANCE 1024
#define ORBIT_STEP 6
int AW_ViewOrbitActive(void) {return orbit.active;}
static void orbit_focal(vec3_t out) {
    if(orbit.edict>0 && orbit.edict<cl.num_entities && cl_entities[orbit.edict].model){
        VectorAdd(cl_entities[orbit.edict].origin,orbit.offset,out);
    }else{VectorCopy(orbit.point,out);}
}
static float orbit_seconds(void) {return orbit.rate?360.0f/(orbit.rate<0?-orbit.rate:orbit.rate):0;}
static void orbit_say(void) {
    if(orbit.rate)Con_Printf("Orbit: %.0f degrees a second (one orbit %.1f s), distance %.0f.\n",orbit.rate,orbit_seconds(),orbit.distance);
    else Con_Printf("Orbit: held (speed 0), distance %.0f.\n",orbit.distance);
}
void AW_ViewOrbitSpeed(float rate) {
    if(rate<-360)rate=-360;
    if(rate>360)rate=360;
    orbit.rate=rate;if(orbit.active)orbit_say();
}
/* Start (or move) the orbit: around edict EDICT (0: the fixed point) whose centre is FOCAL now,
 * the camera starting where the view is, at that distance. 0 = not now. */
int AW_ViewOrbitStart(int edict,const float *focal,int photo,float rate) {
    edict_t *p=local_player();vec3_t d;float flat;
    if(!p || death.stage!=AW_DEATH_NONE || p->v.health<=0){Con_Printf("Orbit: not now (no live player in a running scene).\n");return 0;}
    if(!orbit.active){
        VectorCopy(p->v.origin,orbit.origin);VectorCopy(p->v.angles,orbit.angles);VectorCopy(cl.viewangles,orbit.view);
        orbit.movetype=p->v.movetype;orbit.flags=p->v.flags;orbit.anglehack=noclip_anglehack;
    }
    orbit.edict=edict>0 && edict<cl.num_entities?edict:0;
    VectorCopy(focal,orbit.point);
    if(orbit.edict){VectorSubtract(focal,cl_entities[orbit.edict].origin,orbit.offset);}else{VectorCopy(vec3_origin,orbit.offset);}
    VectorSubtract(focal,r_refdef.vieworg,d);
    orbit.distance=Length(d);
    if(orbit.distance<ORBIT_MIN_DISTANCE)orbit.distance=ORBIT_MIN_DISTANCE*4;
    if(orbit.distance>ORBIT_MAX_DISTANCE)orbit.distance=ORBIT_MAX_DISTANCE;
    flat=(float)sqrt(d[0]*d[0]+d[1]*d[1]);
    orbit.yaw=flat>.01f?(float)(Q_atan2(d[1],d[0])*180/M_PI):cl.viewangles[YAW];
    orbit.pitch=(float)(Q_atan2(-d[2],flat>.01f?flat:1)*180/M_PI);
    if(orbit.pitch>80)orbit.pitch=80;
    if(orbit.pitch<-80)orbit.pitch=-80;
    orbit.photo=photo;orbit.rate=rate;orbit.pending=0;orbit.active=1;
    /* detached: noclip, god, notarget; no velocity, nothing touched (SV_LinkEdict without triggers) */
    p->v.movetype=MOVETYPE_NOCLIP;noclip_anglehack=true;
    p->v.flags=(float)((int)p->v.flags|FL_GODMODE|FL_NOTARGET);
    VectorCopy(vec3_origin,p->v.velocity);SV_LinkEdict(p,false);
    IN_AWClearButtons();
    orbit_say();
    Con_Printf("Orbit keys: + / - speed, 0 holds, mouse wheel distance, mouse turns, right click or Esc ends.\n");
    return 1;
}
static void set_chase(int on);
void AW_ViewOrbitEnd(int say) {
    edict_t *p=local_player();
    orbit.pending=0;
    if(!orbit.active)return;
    orbit.active=0;
    if(p){
        VectorCopy(orbit.origin,p->v.origin);VectorCopy(vec3_origin,p->v.velocity);
        p->v.movetype=orbit.movetype;p->v.flags=orbit.flags;noclip_anglehack=orbit.anglehack;
        VectorCopy(orbit.view,cl.viewangles);VectorCopy(orbit.angles,p->v.angles);p->v.fixangle=1;
        SV_LinkEdict(p,false);
    }
    IN_AWClearButtons();
    set_chase(AW_ViewBehind(&view));
    if(say)Con_Printf("Orbit ended: position, view, movement and flags restored.\n");
}
/* dbg cam orbit mark NAME: start on what the mark's shot shows once it has arrived. */
void AW_ViewOrbitPending(int photo,float rate) {
    orbit.pending=1;orbit.pending_photo=photo;orbit.pending_rate=rate;orbit.pending_since=realtime;
}
int AW_SceneStarting(void);
static void orbit_frame(float dt) {
    if(orbit.pending && !orbit.active){
        int n;vec3_t focal;
        if(AW_SceneStarting() || cls.signon!=SIGNONS){orbit.pending_since=realtime;return;}
        if(realtime-orbit.pending_since<1.5)return;          /* the arrival view has been drawn */
        orbit.pending=0;
        if(AW_InspectTarget(&n,focal)>0)AW_ViewOrbitStart(n,focal,orbit.pending_photo,orbit.pending_rate);
        else Con_Printf("Orbit: nothing under the crosshair of the mark's shot.\n");
        return;
    }
    if(!orbit.active)return;
    /* the mouse turns the orbit; the player's own view stays as it was */
    orbit.yaw+=cl.viewangles[YAW]-orbit.view[YAW];orbit.pitch+=cl.viewangles[PITCH]-orbit.view[PITCH];
    VectorCopy(orbit.view,cl.viewangles);
    if(!cl.paused)orbit.yaw+=orbit.rate*dt;
    orbit.yaw-=360.0f*(float)floor(orbit.yaw/360.0f);
    if(orbit.pitch>80)orbit.pitch=80;
    if(orbit.pitch<-80)orbit.pitch=-80;
}
static int orbit_key(int key) {
    if(!orbit.active || key_dest!=key_game)return 0;
    if(key=='+' || key=='=')AW_ViewOrbitSpeed(orbit.rate+ORBIT_STEP);
    else if(key=='-')AW_ViewOrbitSpeed(orbit.rate-ORBIT_STEP);
    else if(key=='0')AW_ViewOrbitSpeed(0);
    else if(key==K_MWHEELUP || key==K_MWHEELDOWN){
        orbit.distance*=key==K_MWHEELUP?.9f:1.1f;
        if(orbit.distance<ORBIT_MIN_DISTANCE)orbit.distance=ORBIT_MIN_DISTANCE;
        if(orbit.distance>ORBIT_MAX_DISTANCE)orbit.distance=ORBIT_MAX_DISTANCE;
    }
    else if(key==K_ESCAPE || key==K_MOUSE2)AW_ViewOrbitEnd(1);
    return 1;                                                  /* every other game key: nothing */
}
static int orbit_camera(void) {
    vec3_t focal,angles,forward,right,up,end,hit;float fraction,d;
    orbit_focal(focal);
    angles[PITCH]=orbit.pitch;angles[YAW]=orbit.yaw;angles[ROLL]=0;
    AngleVectors(angles,forward,right,up);
    VectorMA(focal,-orbit.distance,forward,end);
    trace(focal,end,hit,&fraction);
    d=AW_ViewObstacle(orbit.distance,fraction,rules.obstacle);
    VectorMA(focal,-d,forward,r_refdef.vieworg);
    VectorCopy(angles,r_refdef.viewangles);
    return 1;
}
int AW_ViewCamera(void) {
    vec3_t focal,angles,forward,right,up,end,hit;float fraction,d;entity_t *ent;
    if(!owned)return 0;
    if(orbit.active)return orbit_camera();
    ent=&cl_entities[cl.viewentity];
    /* camera.cpp: the focal point mHeight above the feet (124 x 0.25), not the eye's bob */
    VectorCopy(ent->origin,focal);focal[2]+=rules.height-feet();
    if(death.stage!=AW_DEATH_NONE){VectorCopy(death_angles,angles);}
    else if(view.mode==AW_VIEW_PREVIEW || view.mode==AW_VIEW_VANITY){
        angles[PITCH]=anchor[PITCH]+view.orbit_pitch;angles[YAW]=anchor[YAW]+view.orbit_yaw;angles[ROLL]=0;
    }else{VectorCopy(cl.viewangles,angles);}
    if(angles[PITCH]>80)angles[PITCH]=80;
    if(angles[PITCH]<-80)angles[PITCH]=-80;
    angles[ROLL]=0;
    AngleVectors(angles,forward,right,up);
    VectorMA(focal,-view.distance,forward,end);
    trace(focal,end,hit,&fraction);
    d=AW_ViewObstacle(view.distance,fraction,rules.obstacle);
    VectorMA(focal,-d,forward,r_refdef.vieworg);
    VectorCopy(angles,r_refdef.viewangles);
    return 1;
}
void AW_ViewRoll(void) {if(owned)r_refdef.viewangles[ROLL]=0;}
/* The vanity orbit's full view (screen.c): only while it orbits; any input ends the orbit and brings the HUD back. */
int AW_ViewVanityFullscreen(void) {
    if(owned && orbit.active)return orbit.photo;
    return owned && view.mode==AW_VIEW_VANITY && death.stage==AW_DEATH_NONE && fullview_cvar.value!=0;
}
int AW_ViewThirdPerson(void) {return owned;}
/* view.c (PHOTO-CROSSHAIR-51): the camera turns around a centre (vanity, the Toggle POV orbit, dbg cam orbit): no crosshair. */
static int AW_ViewOrbiting(void) {
    return owned && (orbit.active || view.mode==AW_VIEW_VANITY || view.mode==AW_VIEW_PREVIEW);
}

/* ---- the death scene ---- */
int AW_DeathLocked(void) {return death.stage!=AW_DEATH_NONE || AW_PlayerDead();}
static int death_prompt_active(void) {return death.stage==AW_DEATH_ASK && !acted && key_dest==key_game;}
static void begin_death(void) {
    int retry,saved;
    death_arena=AW_ArenaActive();
    save_slot=AW_SaveProfile()?AW_SaveLatest(AW_SaveProfile(),save_label,sizeof(save_label)):-1;
    saved=save_slot>=0 && !death_arena;
    retry=retry_cvar.value && !death_arena && AW_CombatRetryAvailable();
    VectorCopy(cl.viewangles,death_angles);death_angles[ROLL]=0;   /* the player's own pitch (OpenMW reference frames) */
    body_play.group=255;
    /* character.cpp playRandomDeath -> useDeathCamera: third person for the death animation */
    view.orbit_yaw=view.orbit_pitch=0;
    if(death_cvar.value && body_ready())view.mode=AW_VIEW_DEATH;
    AW_DeathBegin(&death,death_seconds(),retry,saved);acted=0;death_mouse_x=death_mouse_y=-1;
    /* the death track (music.lua playerDied); combat plays it for a death in a fight */
    if(!AW_CombatDeathMusicPlayed())AW_MusicDeath();
    IN_AWClearButtons();
    AW_UISubtitle("","",0);      /* no speaker name or line stays on screen */
    Con_Printf("You have died.%s\n",death_arena?" (Arena)":"");
}
static void end_death(void) {
    AW_DeathEnd(&death);
    if(view.mode==AW_VIEW_DEATH)view.mode=view.primary;
}
static void choose(int choice) {
    acted=1;
    if(choice==AW_DEATH_RETRY){
        if(AW_CombatRetry()){Con_Printf("Try again: the fight restarts.\n");end_death();return;}
        Con_Printf("The fight cannot restart; choose again.\n");acted=0;return;
    }
    if(choice==AW_DEATH_LOAD && save_slot>=0){
        if(AW_SaveRead(AW_SaveProfile(),save_slot))return;
        acted=0;return;
    }
    /* No: the main menu (the menu's own "Return to main menu") */
    key_dest=key_game;Cbuf_AddText("disconnect\naw_main_menu\n");
}
/* The death box's pointer (MSGBOX-NO-CURSOR-62): shown over the box, a button under it is the selection, a click
 * chooses it; the box's geometry as AW_ViewDraw draws it. */
static int death_button_at(int px,int py) {
    return death.count<1?-1:AW_DeathBoxButtonAt(death.count,vid.width,vid.height,px,py);
}
int AW_ViewDeathMouse(int dx,int dy) {
    int i;
    if(death.stage!=AW_DEATH_ASK || key_dest!=key_game)return 0;
    if(death_mouse_x<0){death_mouse_x=vid.width/2;death_mouse_y=vid.height/2;}
    death_mouse_x+=dx;death_mouse_y+=dy;
    if(death_mouse_x<0)death_mouse_x=0;
    if(death_mouse_x>(int)vid.width-1)death_mouse_x=(int)vid.width-1;
    if(death_mouse_y<0)death_mouse_y=0;
    if(death_mouse_y>(int)vid.height-1)death_mouse_y=(int)vid.height-1;
    if((dx || dy) && (i=death_button_at(death_mouse_x,death_mouse_y))>=0)death.selection=i;
    return 1;
}
int AW_ViewKey(int key) {
    int k=0,c;
    if(orbit_key(key))return 1;
    if(death.stage!=AW_DEATH_ASK || acted || key_dest!=key_game)return 0;
    if(key==K_MOUSE1){
        int i=death_button_at(death_mouse_x,death_mouse_y);
        if(i<0)return 1;          /* a click outside the buttons does nothing */
        death.selection=i;k=3;
    }
    else if(key==K_LEFTARROW || key=='a' || key=='A')k=1;
    else if(key==K_RIGHTARROW || key==K_TAB || key=='d' || key=='D')k=2;
    else if(key==K_ENTER || key==K_SPACE || key=='e' || key=='E')k=3;
    else if(key=='y' || key=='Y')k=4;
    else if(key=='n' || key=='N')k=5;
    if(!k)return 0;
    c=AW_DeathKey(&death,k);
    if(c>=0)choose(c);
    return 1;
}
static const char *choice_label(int c) {
    if(death.count==2 && death.choice[0]==AW_DEATH_RETRY)return c==AW_DEATH_RETRY?yes_text:no_text;
    return c==AW_DEATH_LOAD?yes_text:c==AW_DEATH_MENU?no_text:"Retry fight";
}
void AW_ViewDraw(void) {
    char text[240];const char *at;int i,w=AW_DEATHBOX_W,x=(vid.width-w)/2,y,h=AW_DEATHBOX_H,r[4],gold=AW_UIColor(223,199,144),grey=AW_UIColor(150,130,100);
    extern int scr_copyeverything;
    if(death.stage!=AW_DEATH_ASK || key_dest!=key_game)return;
    scr_copyeverything=1;
    y=(vid.height-h)/2;
    if(death.choice[0]==AW_DEATH_RETRY)strcpy(text,"Try the fight again?");      /* AmiWind: no save to offer */
    else if((at=strstr(load_text,"%s"))!=NULL){
        int n=(int)(at-load_text);
        snprintf(text,sizeof(text),"%.*s%s%s",n,load_text,save_label,at+2);
    }else strcpy(text,load_text);
    AW_UIBox(x,y,w,h);
    AW_UICenteredLines(x+6,y+4,w-12,h-40,text);   /* above the buttons (UI-NO-SHARED-LAYOUT-67: they rose 2 rows) */
    for(i=0;i<death.count;i++){
        AW_DeathBoxButtonRect(death.count,i,vid.width,vid.height,r);   /* the pointer's rectangles too */
        AW_UIBox(r[0],r[1],r[2],r[3]);
        if(i==death.selection)AW_UIFill(r[0]+3,r[1]+3,r[2]-6,18,AW_UIColor(70,52,30));
        AW_UITextBox(r[0],r[1],r[2],r[3],choice_label(death.choice[i]),i==death.selection?gold:grey);
    }
    if(death_mouse_x<0){death_mouse_x=vid.width/2;death_mouse_y=vid.height/2;}
    if(!AW_UICursor(death_mouse_x,death_mouse_y)){
        AW_UIFill(death_mouse_x,death_mouse_y,2,6,gold);AW_UIFill(death_mouse_x,death_mouse_y,6,2,gold);
    }
}

/* ---- the frame ---- */
static void set_chase(int on) {
    if(on && !owned){owned=1;Cvar_SetValue("chase_active",1);}
    else if(!on && owned){owned=0;memset(&body_air,0,sizeof(body_air));Cvar_SetValue("chase_active",0);}
}
static int playing(void) {
    return key_dest==key_game && !cl.paused && !con_forcedup && !AW_IntroUse();
}
void AW_ViewFrame(void) {
    float dt=(float)host_frametime;int input,dead,mode_before,forced=view_forced;edict_t *p;
    view_forced=0;      /* a turn the game made counts in this frame only */
    if(!ready)load_settings();
    if(dt<0)dt=0;
    if(dt>.25f)dt=.25f;
    p=local_player();
    if(!p){if(death.stage!=AW_DEATH_NONE)end_death();orbit.active=0;set_chase(0);return;}
    orbit_frame(dt);
    if(orbit.active){if(p->v.health<=0)AW_ViewOrbitEnd(0);else{set_chase(1);return;}}
    /* Story permission is separate from the saved camera preferences and
     * body availability. Clear pending input so locked Tab taps cannot fire
     * when registration ends, and cancel an orbit carried across new game. */
    if(!AW_StoryViewAllowed()){
        view.mode=view.primary=AW_VIEW_FIRST;view.idle=view.pov_held=0;
        view.orbit_yaw=view.orbit_pitch=0;vanity_forced=0;
        pov_down=pov_tapped=input_seen=0;last_view=0;
        VectorCopy(cl.viewangles,last_angles);set_chase(0);return;
    }
    if(distance_cvar.value>=rules.min_distance && distance_cvar.value<=rules.max_distance && distance_cvar.value!=view.distance &&
       view.mode!=AW_VIEW_DEATH)view.distance=distance_cvar.value;
    /* aw_view_third set from the console or a config: the primary mode */
    if((int)view_cvar.value!=last_view && AW_ViewLockedMode(&view)>=0){
        /* dbg setpov: the lock holds; the setting follows it */
        int third=AW_ViewLockedMode(&view)==AW_VIEW_THIRD;
        if((int)view_cvar.value!=third)Cvar_SetValue(view_cvar.name,(float)third);
        last_view=third;
    }
    if((int)view_cvar.value!=last_view){
        int want=view_cvar.value?AW_VIEW_THIRD:AW_VIEW_FIRST;
        if(last_view>=0 && view.mode!=AW_VIEW_DEATH){
            if(want==AW_VIEW_THIRD && !body_ready()){
                if(!warned)Con_Printf("No player body in this image (--player-body on builds it): first person only.\n");
                warned=1;want=AW_VIEW_FIRST;
            }
            view.primary=view.mode=want;
        }
        last_view=(int)view_cvar.value;
    }
    dead=p->v.health<=0;
    if(dead && death.stage==AW_DEATH_NONE)begin_death();
    else if(!dead && death.stage!=AW_DEATH_NONE)end_death();
    if(death.stage!=AW_DEATH_NONE){
        VectorCopy(death_angles,cl.viewangles);   /* no turning while dead */
        if(!death_arena && !acted && AW_DeathStep(&death,dt)==AW_DEATH_MAIN_MENU)choose(AW_DEATH_MENU);
    }else if(playing()){
        int turned=cl.viewangles[YAW]!=last_angles[YAW] || cl.viewangles[PITCH]!=last_angles[PITCH];
        mode_before=view.mode;
        /* a script's DisablePlayerViewSwitch (MWSCRIPT-PLAYER-CONTROL-62): the view stays as it is, the key does
         * nothing (OpenMW camera.lua updatePOV reads the ViewMode switch) */
        if(!AW_ControlAllowed(AW_CONTROL_VIEWSWITCH))pov_down=pov_tapped=0;
        if(pov_tapped && !pov_down)AW_ViewPOVTap(&view,&rules);
        else AW_ViewPOV(&view,&rules,pov_down,dt);
        if(view.mode!=AW_VIEW_FIRST && !body_ready()){
            if(!warned)Con_Printf("No player body in this image (--player-body on builds it): first person only.\n");
            warned=1;view.mode=view.primary=AW_VIEW_FIRST;
        }
        if(view.mode==AW_VIEW_PREVIEW || view.mode==AW_VIEW_VANITY){
            /* the mouse turns the camera, not the player (camera.lua Preview); a turn the game made is the player's
             * new heading and stays (VIEW-VANITY-UNDOES-SET-VIEW-67: it counts as input, so the vanity orbit ends
             * there; before, the anchor was copied back over it) */
            AW_ViewOrbitHold(&view,cl.viewangles,anchor,mode_before!=view.mode,forced);
        }else if(mode_before==AW_VIEW_PREVIEW){
            /* leaving the orbit: the player turns to the camera's heading (OpenMW turns the
             * character gradually, deferredPreviewRotation; AmiWind turns at once) */
            cl.viewangles[YAW]=anchor[YAW]+view.orbit_yaw;
            view.orbit_yaw=view.orbit_pitch=0;
        }
        input=input_seen || pov_down || pov_tapped || turned || cl.velocity[0] || cl.velocity[1] || cl.velocity[2];
        mode_before=view.mode;
        /* DisableVanityMode: no idle orbit, and a running one ends (camera.lua updateVanity) */
        AW_ViewIdle(&view,&rules,input,AW_ViewVanityAllowed(vanity_cvar.value || vanity_forced,body_ready(),AW_ArenaActive()) &&
                    AW_ControlAllowed(AW_CONTROL_VANITY),dt);
        if(view.mode!=AW_VIEW_VANITY)vanity_forced=0;
        if(mode_before==AW_VIEW_VANITY && view.mode!=AW_VIEW_VANITY)view.orbit_yaw=view.orbit_pitch=0;
        else if(mode_before!=AW_VIEW_VANITY && view.mode==AW_VIEW_VANITY)VectorCopy(cl.viewangles,anchor);
        if((view.primary==AW_VIEW_THIRD)!=(view_cvar.value!=0)){Cvar_SetValue(view_cvar.name,view.primary==AW_VIEW_THIRD);last_view=(int)view_cvar.value;}
        if(view.distance!=distance_cvar.value)Cvar_SetValue(distance_cvar.name,view.distance);
    }
    input_seen=pov_tapped=0;VectorCopy(cl.viewangles,last_angles);
    set_chase(AW_ViewBehind(&view));
    body_motion_check(p);   /* PLAYER-VANITY-WALK-STUCK-67: a camera or control change restarts the body's animation */
}
void AW_ViewInput(int key,int down) {
    (void)key;
    /* game keys only: the console's own keys (typing a command, closing the console) are not play input */
    if(down && key_dest==key_game)input_seen=1;
}
void AW_ViewSceneSpawn(void) {
    /* a new map ends an orbit (the arrival places the player); its detachment goes with it */
    if(orbit.active){
        edict_t *p=sv.active && svs.clients?svs.clients[0].edict:NULL;
        orbit.active=0;
        if(p){p->v.flags=(float)(((int)p->v.flags&~(FL_GODMODE|FL_NOTARGET))|((int)orbit.flags&(FL_GODMODE|FL_NOTARGET)));
              if(p->v.movetype==MOVETYPE_NOCLIP && orbit.movetype!=MOVETYPE_NOCLIP){p->v.movetype=orbit.movetype;noclip_anglehack=orbit.anglehack;}}
        set_chase(0);
    }
    AW_ViewInventoryClear();
    AW_ItemsAliasClear();held_cursor=held_draw_count=0;
    memset(&body_air,0,sizeof(body_air));
    body_sig.valid=0;   /* PLAYER-VANITY-WALK-STUCK-67: the new map's first frame restarts the body's animation */
    if(death.stage!=AW_DEATH_NONE)end_death();
    body_model=held_model=NULL;body_race=-2;body_torch=body_water=held_visible=torch_failed=water_failed=0;body_emitter.count=0;
    held_path[0]=0;held_next=0;
    /* a new map flushes the models: the parts are looked up again (the recipe read again at the first draw) */
    memset(part_models,0,sizeof(part_models));parts.count=0;parts_sig[0]=0;parts_table=NULL;body_parts=0;parts_failed=0;
    hparts_noslot_sig[0]=0;     /* FP-ARMS-NO-MODEL-SLOT-67: the flush frees slots: the arms are tried again */
}
/* aw_view.h (FP-ARMS-NO-MODEL-SLOT-67, DBG-RACE-SWAP-67): a race or sex swap releases what the old one wore at once:
 * the body's and the first-person arms' part models are unpinned and released, and both sets are assembled again for
 * the new race and sex at the next frame that draws them. Prints the model table before and after, by number. */
void AW_ViewPartsUnload(void) {
    int i,before_parts,after_parts,before=model_slots_in_use(&before_parts),after;
    model_t *gone[3*AW_PARTS_MAX];int g=0;
    for(i=0;i<AW_PARTS_MAX;i++){
        if(part_models[i])gone[g++]=part_models[i];
        if(hpart_models[i])gone[g++]=hpart_models[i];
        if(i<pend_count && pend_models[i])gone[g++]=pend_models[i];
    }
    for(i=0;i<g;i++)part_pin(gone[i],0);
    memset(part_models,0,sizeof(part_models));parts.count=0;parts_sig[0]=0;body_parts=0;pend_on=0;
    memset(pend_models,0,sizeof(pend_models));pend_count=0;
    memset(hpart_models,0,sizeof(hpart_models));hparts.count=0;hparts_sig[0]=0;hparts_shown=0;hparts_noslot_sig[0]=0;
    parts_failed=hparts_failed=0;        /* a refusal of the old race's data is not the new one's */
    for(i=0;i<g;i++)part_drop(gone[i]);
    if(aw_character.valid && aw_character.race>=0 && aw_character.race<aw_race_count){
        snprintf(parts_race_seen,sizeof(parts_race_seen),"%s",aw_races[aw_character.race].id);
        parts_female_seen=aw_character.female?1:0;
    }
    after=model_slots_in_use(&after_parts);
    Con_Printf("Player parts released: model table %d slots in use (%d player parts) before, %d (%d) after; "
               "%lu released in all.\n",before,before_parts,after,after_parts,parts_released);
}
static void parts_race_check(const char *race,int female) {
    if(!race)return;
    if(parts_female_seen>=0 && (parts_female_seen!=(female?1:0) || Q_strcasecmp(parts_race_seen,(char *)race)))
        AW_ViewPartsUnload();
    snprintf(parts_race_seen,sizeof(parts_race_seen),"%s",race);parts_female_seen=female?1:0;
}
/* aw_view.h (DBG-RACE-SWAP-67): 1 = RACE (a race id) and sex are a beast race by the body recipe's skeleton row (the
 * builder writes it from the race's Beast flag, tools/prepare_player_parts.py race_rows), 0 not, -1 unknown (no recipe
 * for it). One file read; nothing kept. */
int AW_ViewRaceBeast(const char *race,int female) {
    aw_parts_body_t next;byte *text;int mark,ok;
    if(!race)return -1;
    mark=Hunk_LowMark();text=COM_LoadHunkFile("view/parts.txt");
    ok=text && AW_PartsAssemble((const char *)text,com_filesize,race,female,NULL,NULL,NULL,0,&next);
    Hunk_FreeToLowMark(mark);
    return ok?(next.beast?1:0):-1;
}
/* aw_quickchar.c aw_race_swapped (dbg race, DBG-RACE-SWAP-67): after a race or sex swap, the new race's equip rules at
 * once (a beast race: nothing over the head, nothing on the feet, AW_InventoryBeastRefusal; each such piece back into
 * the inventory, one line per item) and the old race's body and arm parts released (AW_ViewPartsUnload). Returns the
 * items unequipped; *BEAST: 1 a beast race, 0 not, -1 unknown. */
extern int (*aw_race_swapped)(int *beast);
static int race_swapped(int *beast) {
    int s,dropped=0,b=-1;
    if(aw_character.valid && aw_character.race>=0 && aw_character.race<aw_race_count)
        b=AW_ViewRaceBeast(aw_races[aw_character.race].id,aw_character.female?1:0);
    for(s=0;s<AW_INVENTORY_SLOTS && b>0;s++){
        aw_inventory_item_t it;const char *why;
        if(!AW_InventoryEquippedItem(s,&it) || !(why=AW_InventoryBeastRefusal(&it,1)))continue;
        if(AW_InventoryUnequip(&aw_state,it.id)){
            dropped++;
            Con_Printf("Race swap: %s (%s) back into the inventory: the new race cannot wear it (%s).\n",it.name,it.id,why);
        }
    }
    AW_ViewPartsUnload();
    if(beast)*beast=b;
    return dropped;
}

/* The vanity orbit now, until any input (dbg vanitycamera on, dbg camera vanity now). */
/* dbg setpov (aw_view.h AW_ViewLock; FP-TORCH-HAND-REGRESSION-67): the view locked in a mode for the test stills, with a
 * message on the screen and in the console; nothing else switches it until dbg setpov off */
static const char *mode_name(int m);
static int pov_locked_say(void) {
    if(AW_ViewLockedMode(&view)<0)return 0;
    Con_Printf("POV locked: %s (dbg setpov off unlocks it).\n",mode_name(AW_ViewLockedMode(&view)));return 1;
}
/* the view as dbg setpov's number: 1 first person, 2 the vanity camera, 3 third person; 0 another (orbit, death) */
static int pov_number(int mode) {
    return mode==AW_VIEW_FIRST?1:mode==AW_VIEW_VANITY?2:mode==AW_VIEW_THIRD?3:0;
}
static void setpov_command(void) {
    const char *a=Cmd_Argc()>1?Cmd_Argv(1):"";int mode=-2;char line[96];
    if(!ready)load_settings();
    if(!*a){
        int locked=AW_ViewLockedMode(&view);
        Con_Printf("POV: %s (setpov %d), primary %s; %s%s\n",mode_name(view.mode),pov_number(view.mode),
                   mode_name(view.primary),locked<0?"not locked":"locked: ",locked<0?"":mode_name(locked));
        return;
    }
    /* the maintainer's numbers (2026-11-18): 1 first person, 2 the vanity camera, 3 third person; the words alias them */
    if(!strcmp(a,"1") || !Q_strcasecmp((char *)a,"first"))mode=AW_VIEW_FIRST;
    else if(!strcmp(a,"2") || !Q_strcasecmp((char *)a,"vanity"))mode=AW_VIEW_VANITY;
    else if(!strcmp(a,"3") || !Q_strcasecmp((char *)a,"third"))mode=AW_VIEW_THIRD;
    else if(!Q_strcasecmp((char *)a,"off"))mode=-1;
    if(mode==-2){Con_Printf("Usage: dbg setpov [1 first | 2 vanity | 3 third | off]\n");return;}
    if(mode==-1){
        if(AW_ViewLockedMode(&view)<0){Con_Printf("POV is not locked.\n");return;}
        AW_ViewLock(&view,-1);view.mode=view.primary;
        snprintf(line,sizeof(line),"POV unlocked: %s",mode_name(view.mode));
    }else{
        if(mode!=AW_VIEW_FIRST && !body_ready()){Con_Printf("No player body in this image: first person only.\n");return;}
        if(death.stage!=AW_DEATH_NONE){Con_Printf("POV: not while the death camera runs.\n");return;}
        if(orbit.active)AW_ViewOrbitEnd(0);
        if(mode==AW_VIEW_VANITY)VectorCopy(cl.viewangles,anchor);
        AW_ViewLock(&view,mode);vanity_forced=mode==AW_VIEW_VANITY;
        Cvar_SetValue(view_cvar.name,(float)(view.primary==AW_VIEW_THIRD));last_view=(int)view_cvar.value;
        snprintf(line,sizeof(line),"POV locked: %s (setpov %d)",mode_name(mode),pov_number(mode));
    }
    Con_Printf("%s.\n",line);AW_UISubtitle("",line,4);
}
static void vanity_start(void) {
    if(!ready)load_settings();
    if(!AW_StoryViewAllowed()){Con_Printf("Vanity camera: character registration is not complete.\n");return;}
    if(!AW_ControlAllowed(AW_CONTROL_VANITY)){Con_Printf("Vanity camera: a script has switched it off.\n");return;}
    if(!body_ready()){Con_Printf("No player body in this image (--player-body on builds it): no vanity camera.\n");return;}
    if(death.stage!=AW_DEATH_NONE || !local_player()){Con_Printf("Vanity camera: not now.\n");return;}
    if(pov_locked_say())return;
    view.idle=rules.vanity_delay+1;VectorCopy(cl.viewangles,anchor);
    view.mode=AW_VIEW_VANITY;view.orbit_yaw=view.orbit_pitch=0;vanity_forced=1;
    Con_Printf("Vanity camera: orbiting until any input.\n");
}
/* dbg vanitycamera (alias dbg vanitycam): auto = the original (orbit after fVanityDelay seconds without input,
 * 3 degrees a second; aw_view_vanity 1, the default), off = never (aw_view_vanity 0, saved), on/now = orbit now
 * until any input; delay N = a test delay in seconds (not saved; "delay default" = the game's own setting). */
static void vanity_command(void) {
    char *a=Cmd_Argv(1);float d;
    if(!ready)load_settings();
    if(Cmd_Argc()==1){
        Con_Printf("Vanity camera: %s; delay %.1f s (game setting fVanityDelay %.1f s)%s; turn %.0f deg/s; idle %.1f s now; orbiting %s; full view %s\n",
            vanity_cvar.value?"auto (the original)":"off",rules.vanity_delay,vanity_delay_setting,
            rules.vanity_delay!=vanity_delay_setting?" [test delay, not saved]":"",rules.vanity_rate,view.idle,
            view.mode==AW_VIEW_VANITY?"yes":"no",fullview_cvar.value?"on":"off");
        return;
    }
    if(Cmd_Argc()==2 && (!Q_strcasecmp(a,"on") || !Q_strcasecmp(a,"now"))){vanity_start();return;}
    if(Cmd_Argc()==2 && !Q_strcasecmp(a,"auto")){Cvar_SetValue(vanity_cvar.name,1);Con_Printf("Vanity camera: auto (the original).\n");return;}
    if(Cmd_Argc()==2 && !Q_strcasecmp(a,"off")){
        Cvar_SetValue(vanity_cvar.name,0);vanity_forced=0;
        if(view.mode==AW_VIEW_VANITY){view.mode=view.primary;view.orbit_yaw=view.orbit_pitch=0;}
        Con_Printf("Vanity camera: off.\n");return;
    }
    if(Cmd_Argc()==3 && !Q_strcasecmp(a,"fullview")){
        int on;
        if(!Q_strcasecmp(Cmd_Argv(2),"on"))on=1;else if(!Q_strcasecmp(Cmd_Argv(2),"off"))on=0;
        else{Con_Printf("Usage: dbg vanitycamera fullview on|off\n");return;}
        Cvar_SetValue(fullview_cvar.name,(float)on);
        Con_Printf("Vanity full view: %s (aw_vanity_fullview %d, saved).\n",on?"on: no HUD, full screen":"off: the orbit inside the HUD",on);
        return;
    }
    if(Cmd_Argc()==3 && !Q_strcasecmp(a,"delay")){
        if(!Q_strcasecmp(Cmd_Argv(2),"default"))d=vanity_delay_setting;else d=Q_atof(Cmd_Argv(2));
        if(d<.5f || d>3600){Con_Printf("Vanity delay: 0.5 to 3600 seconds, or default.\n");return;}
        rules.vanity_delay=d;
        Con_Printf("Vanity delay %.1f s (test value, not saved; the original is the game setting fVanityDelay, %.1f s).\n",d,vanity_delay_setting);
        return;
    }
    Con_Printf("Usage: dbg vanitycamera [auto | off | on (now) | delay N/default | fullview on/off]\n");
}

/* aw_scene.c: a scene spawned; the combat layer's hook first */
static void (*combat_scene)(void);
static void scene_spawn(void) {if(combat_scene)combat_scene();AW_ViewSceneSpawn();}

/* ---- commands ---- */
static void pov_press(void) {if(key_dest==key_game)pov_down=pov_tapped=1;}
static void pov_release(void) {pov_down=0;}
static void zoom_command(void) {
    float clicks=Cmd_Argc()>1?Q_atof(Cmd_Argv(1)):0;
    if(key_dest!=key_game || death.stage!=AW_DEATH_NONE)return;
    if(clicks<0 && view.mode==AW_VIEW_FIRST && !body_ready()){
        if(!warned)Con_Printf("No player body in this image (--player-body on builds it): first person only.\n");
        warned=1;return;
    }
    AW_ViewZoom(&view,&rules,clicks*rules.zoom_step);
    input_seen=1;
}
/* ---- dbg camera held (CONFIRMED-LOOKBOOK-67, FP-TORCH-OUT-OF-HAND-67): the light in the left hand against the hand
 * it is drawn in, by number, for the look book's page HELD-LIGHT-IN-HAND (docs/LOOKBOOK.md). Read only, on demand:
 * the vertices of the arms (first person) or of the body (third person) that hang on the left hand (the shield bone's
 * parent and the bones under it, the shield bone left out), posed and placed as the renderer draws them, against the
 * light's drawn place and every one of its own vertices. Nothing is kept (memory note: debug tools take the least
 * memory): the hand's point list of at most HELD_POINTS (7 KB) and the posed bones (3 KB) are allocated for the call and
 * freed after it; the light's vertices are measured as they are placed, none stored. */
#define HELD_POINTS 600
static float (*held_hand_points)[3],(*held_world)[3][4];
static int held_under(const aw_skel_table_t *t,int bone,int root) {
    int i;
    for(i=0;i<AW_SKEL_MAX_BONES && bone>=0 && bone<t->bones;i++){if(bone==root)return 1;bone=t->parent[bone];}
    return 0;
}
/* a point of a model's own space as the alias renderer places it (the tag composition the held items use) */
static void held_place(const float origin[3],const float angles[3],const float p[3],float out[3]) {
    float tag[6],a[3];
    tag[0]=p[0];tag[1]=p[1];tag[2]=p[2];tag[3]=tag[4]=tag[5]=0;
    AW_BlockCompose(origin,angles,tag,out,a);
}
/* the vertices of the part M (on table T, posed as WORLD) that hang on HAND or a bone under it and not on SKIP, as
 * drawn: the pose quantised into the model's bytes and read back by its scale and origin, times the axis SCALE, placed
 * at ORIGIN and ANGLES; appended to the hand points from N; the new count */
static int held_hand(model_t *m,const aw_skel_table_t *t,const float world[][3][4],int hand,int skip,const float origin[3],
                     const float angles[3],const float scale[3],int n) {
    aliashdr_t *h;mdl_t *pmdl;aw_skel_block_t block;const unsigned char *v;int i,j,k;
    if(!m || m->type!=mod_alias || !(h=(aliashdr_t *)Mod_Extradata(m)) || !h->aw_skel)return n;
    pmdl=(mdl_t *)((byte *)h+h->model);
    if(!AW_SkelBlockHead((byte *)h+h->aw_skel,AW_SKEL_BLOCK_HEAD+(long)pmdl->numverts*AW_SKEL_VERT_BYTES,pmdl->numverts,
                         &block))return n;
    for(i=0,v=block.data;i<pmdl->numverts && n<HELD_POINTS;i++,v+=AW_SKEL_VERT_BYTES){
        int b=v[0];float in[3],pos,p[3];
        if(b>=t->bones || b==skip || !held_under(t,b,hand))continue;
        for(k=0;k<3;k++)in[k]=(float)(short)((v[4+2*k]<<8)|v[5+2*k])*block.rest_scale;
        for(k=0;k<3;k++){
            pos=world[b][k][3];
            for(j=0;j<3;j++)pos+=world[b][k][j]*in[j];
            p[k]=block.pose_step[k]!=0?((pos-block.pose_origin[k])/block.pose_step[k]*pmdl->scale[k]+pmdl->scale_origin[k])*
                 scale[k]:0;
        }
        held_place(origin,angles,p,held_hand_points[n++]);
    }
    return n;
}
static float held_nearest(const float a[3],int n);
/* every vertex of the light model's one frame placed at ORIGIN and ANGLES, against the N hand points: the nearest
 * distance into *GAP (-1 none); the vertex count (all of them: nothing is stored per vertex) */
static int held_item(model_t *m,const float origin[3],const float angles[3],int n,float *gap) {
    aliashdr_t *h;mdl_t *pmdl;trivertx_t *v;int i,k;float p[3],at[3],d;
    *gap=-1;
    if(!m || m->type!=mod_alias || !(h=(aliashdr_t *)Mod_Extradata(m)))return 0;
    pmdl=(mdl_t *)((byte *)h+h->model);v=(trivertx_t *)((byte *)h+h->frames[0].frame);
    for(i=0;i<pmdl->numverts;i++){
        for(k=0;k<3;k++)p[k]=v[i].v[k]*pmdl->scale[k]+pmdl->scale_origin[k];
        held_place(origin,angles,p,at);
        if((d=held_nearest(at,n))>=0 && (*gap<0 || d<*gap))*gap=d;
    }
    return pmdl->numverts;
}
static float held_nearest(const float a[3],int n) {
    float best=-1,d,x,y,z;int i;
    for(i=0;i<n;i++){
        x=a[0]-held_hand_points[i][0];y=a[1]-held_hand_points[i][1];z=a[2]-held_hand_points[i][2];d=x*x+y*y+z*z;
        if(best<0 || d<best)best=d;
    }
    return best<0?-1:(float)sqrt(best);
}
static void held_measure(void);
static void held_report(void) {
    unsigned long bytes=(unsigned long)HELD_POINTS*sizeof(float[3])+AW_SKEL_MAX_BONES*sizeof(float[3][4]);
    void *block=AW_TryMalloc(bytes);
    if(!block){Con_Printf("held light: no memory for the measure (%lu bytes)\n",bytes);return;}
    held_world=(float (*)[3][4])block;
    held_hand_points=(float (*)[3])(held_world+AW_SKEL_MAX_BONES);
    held_measure();
    free(block);held_hand_points=NULL;held_world=NULL;
}
static void held_measure(void) {
    float (*world)[3][4]=held_world;
    const aw_held_light_t *l=AW_HeldLight();const char *id=aw_state.inventory.equipped[AW_SLOT_LEFT];
    float origin[3],angles[3],scale[3]={1,1,1},attach,gap=-1;int n=0,items,i,hand,third=chase_active.value!=0;model_t *lm;
    if(!l){
        Con_Printf("held light: none lit in the left hand (%s)%s\n",id[0]?id:"nothing equipped there",
                   AW_TorchEquipped()?"; the carried torch's baked arms are drawn (the torch and the hand one model)":"");
        return;
    }
    if(third){
        if(!body_parts || !parts_table || parts.shield_bone<0 || parts.shield_bone>=parts_table->bones){
            Con_Printf("held light: third person, %s: the body is not assembled from parts; not measured\n",id);return;
        }
        if(!held_light_placed(1)){Con_Printf("held light: third person, %s: not placed in the last frames\n",id);return;}
        memcpy(origin,held_light_place,sizeof(origin));memcpy(angles,held_light_place+3,sizeof(angles));
        hand=parts_table->parent[parts.shield_bone];
        {
            float layer;int root;
            if(parts_light_layer(body.frame,&layer,&root))AW_SkelPoseLayer(parts_table,(float)body.frame,layer,root,world);
            else AW_SkelPose(parts_table,(float)body.frame,world);
        }
        scale[0]=scale[1]=parts.weight>0?parts.weight:1;scale[2]=parts.height>0?parts.height:1;
        for(i=0;i<parts.count;i++)
            n=held_hand(part_models[i],parts_table,(const float (*)[3][4])world,hand,parts.shield_bone,body.origin,
                        body.angles,scale,n);
    }else{
        if(!hparts_shown || !hparts_table || hparts.shield_bone<0 || hparts.shield_bone>=hparts_table->bones){
            Con_Printf("held light: first person, %s: the arms are not drawn from parts; not measured\n",id);return;
        }
        if(!aw_hand_held_light || !aw_hand_held_light(origin,angles)){
            Con_Printf("held light: first person, %s: not drawn in the last frame\n",id);return;
        }
        hand=hparts_table->parent[hparts.shield_bone];
        AW_SkelPose(hparts_table,(float)hparts_frame,world);
        for(i=0;i<hparts.count;i++)
            n=held_hand(hpart_models[i],hparts_table,(const float (*)[3][4])world,hand,hparts.shield_bone,
                        cl.viewent.origin,cl.viewent.angles,scale,n);
    }
    if(hand<0 || !n){Con_Printf("held light: %s person, %s: no vertex hangs on the left hand (bone %d)\n",third?"third":"first",
                                id,hand);return;}
    lm=Mod_ForName((char *)l->model,false);
    items=held_item(lm,origin,angles,n,&gap);
    attach=held_nearest(origin,n);
    Con_Printf("held light: %s person, %s (%s); left hand bone %d, %d hand vertices, %d light vertices; attach point "
               "%.1f units from the hand, nearest vertex %.1f units from the hand\n",third?"third":"first",id,l->model,hand,
               n,items,attach,gap);
}
static const char *mode_name(int m) {
    return m==AW_VIEW_THIRD?"third person":m==AW_VIEW_PREVIEW?"orbit (Toggle POV held)":m==AW_VIEW_VANITY?"vanity orbit":
           m==AW_VIEW_DEATH?"death camera":"first person";
}
static void command(void) {
    char *a=Cmd_Argv(1);int on;
    if(!ready)load_settings();
    if(Cmd_Argc()==1){
        Con_Printf("View: %s (primary %s), distance %.1f (%.1f..%.1f), vanity %s after %.0f s idle (%.1f s now), death camera %s, retry %s\n",
            mode_name(view.mode),mode_name(view.primary),view.distance,rules.min_distance,rules.max_distance,
            vanity_cvar.value?"on":"off",rules.vanity_delay,view.idle,death_cvar.value?"on":"off",retry_cvar.value?"on":"off");
        Con_Printf("Body: %s%s\n",body_ready()?body_model->name:"none",body_cvar.value?"":" (aw_player_body 0)");
        if(body_parts){
            int i;
            Con_Printf("Assembled body: %d parts (scale %.3f x %.3f), table %s, assembled %d times, last %.1f ms; slots",
                parts.count,parts.weight,parts.height,parts.table,parts_built,parts_ms);
            for(i=0;i<parts.count;i++)Con_Printf(" %d",parts.slot[i]);
            Con_Printf("\n");
        }else Con_Printf("Assembled body: off (%s)\n",!parts_cvar.value?"aw_player_body_parts 0":parts_failed?"unavailable in this image":
            body_torch?"torch carried":body_water?"swimming":"not drawn now");
        if(hparts.count && hand_parts_cvar.value && !hparts_failed){
            int i;
            Con_Printf("First-person arms: %d parts, table %s, frame %d, assembled %d times, last %.1f ms; slots",
                hparts.count,hparts.table,hparts_frame,hparts_built,hparts_ms);
            for(i=0;i<hparts.count;i++)Con_Printf(" %d",hparts.slot[i]);
            Con_Printf("\n");
        }else Con_Printf("First-person arms: the baked arms (%s)\n",!hand_parts_cvar.value?"aw_hand_parts 0":
            hparts_failed?"parts unavailable in this image":hparts_noslot_sig[0]?"no model slot for this outfit":
            "parts not drawn yet");
        {   /* FP-ARMS-NO-MODEL-SLOT-67: the model table by number (the player's parts of old sets are released) */
            int part_slots,used=model_slots_in_use(&part_slots);
            Con_Printf("Model table: %d slots in use of %d known, %d of them player parts; %lu player parts released\n",
                used,mod_numknown,part_slots,parts_released);
        }
        /* FP-FOREARMS-BELOW-VIEW-61: the first-person model's own view (view.c) */
        if(aw_fp_view.value)Con_Printf("First-person view: the original's (aw_fp_view 1): its own field %.0f degrees "
            "high, the arms turn %.2f of the pitch; view pitch %.1f, arms pitch %.1f\n",V_FP_FOV,V_FP_NECK,
            cl.viewangles[PITCH],-cl.viewent.angles[PITCH]);
        else Con_Printf("First-person view: the world's projection, the arms follow the whole pitch (aw_fp_view 0)\n");
        /* HELD-LIGHT-OWN-MODEL-61: the held light's state, for the in-game checks */
        {
            const aw_held_light_t *l=AW_HeldLight();vec3_t at;int lroot;float lframe;
            if(!l)Con_Printf("Held light: none lit (chase %d, owned %d)\n",(int)chase_active.value,owned);
            else{
                int lit=view_held_light(at);
                Con_Printf("Held light: %s, reach %.0f, %s, %d flames; third person placed %.2f s ago at %.1f %.1f %.1f "
                    "(player %.1f %.1f %.1f), light from it %d; layer %d\n",l->model,l->radius,l->flicker?"flickering":"steady",
                    l->flames,held_light_time>=0?realtime-held_light_time:-1.0,held_light_place[0],held_light_place[1],
                    held_light_place[2],body.origin[0],body.origin[1],body.origin[2],lit,
                    parts_table?parts_light_layer(body.frame,&lframe,&lroot):-1);
            }
        }
        if(body_model){
            edict_t *p=local_player();
            Con_Printf("Body animation: frame %d/%d, group %d, layers %d, kit %d, water %d, torch %d\n",
                body.frame,body_model->numframes,body_play.group,body_layers.count,
                aw_anim_kit_enabled,body_water,body_torch);
            Con_Printf("Weapon stance: %s (aw_player_stances %d), group %s (%s), frames %d..%d, %lu picks\n",
                stance.picked && stance.group[0]?"playing":"not now",(int)stances_cvar.value,
                stance.group[0]?stance.group:"-",stance.rule?stance.rule:"-",stance.from,stance.to,stance.changes);
            if(p)Con_Printf("Player state: waterlevel %.0f, movetype %.0f, velocity %.1f %.1f %.1f\n",
                p->v.waterlevel,p->v.movetype,p->v.velocity[0],p->v.velocity[1],p->v.velocity[2]);
            /* PLAYER-VANITY-WALK-STUCK-67: walking, the move group changes a few times a second at most and the air
             * state not at all; a group restarted every frame shows as one change per frame */
            Con_Printf("Body motion: speed %.1f, on ground %d, air %s, group changes %lu in the last second (%lu in all), "
                "air changes %lu (%lu), restarts %lu (last: %s)%s\n",motion.speed,p?((int)p->v.flags&FL_ONGROUND)!=0:-1,
                body_air.airborne?"jumping":body_air.landing?"landing":"no",motion.rate_switches,motion.switches,
                motion.rate_air,motion.air_flips,motion.restarts,motion.why[0]?motion.why:"none",
                body_restart_on?"":" [restart off: dbg camera motion restart on]");
        }
        return;
    }
    if(!Q_strcasecmp(a,"held")){held_report();return;}   /* CONFIRMED-LOOKBOOK-67: the grip by number */
    if((!Q_strcasecmp(a,"first") || !Q_strcasecmp(a,"third") || !Q_strcasecmp(a,"toggle")) && pov_locked_say())return;
    if(!Q_strcasecmp(a,"first")){view.primary=view.mode=AW_VIEW_FIRST;Cvar_SetValue(view_cvar.name,0);last_view=0;return;}
    if(!Q_strcasecmp(a,"third")){Cvar_SetValue(view_cvar.name,1);return;}
    if(!Q_strcasecmp(a,"toggle")){Cvar_SetValue(view_cvar.name,view.primary==AW_VIEW_FIRST);return;}
    if(!Q_strcasecmp(a,"distance") && Cmd_Argc()==3){
        float d=Q_atof(Cmd_Argv(2));
        if(d<rules.min_distance)d=rules.min_distance;
        if(d>rules.max_distance)d=rules.max_distance;
        Cvar_SetValue(distance_cvar.name,d);view.distance=d;return;
    }
    if(!Q_strcasecmp(a,"vanity") && Cmd_Argc()==3 && !Q_strcasecmp(Cmd_Argv(2),"now")){vanity_start();return;}
    if(!Q_strcasecmp(a,"die") && Cmd_Argc()==2){
        /* test the death scene: world damage through the combat layer (as lava, aw_lava.c) */
        /* GODMODE-LAVA-DEATH-62: god mode keeps the player alive here too */
        if(sv_player && ((int)sv_player->v.flags&FL_GODMODE))Con_Printf("God mode is on: no death (dbg god off first).\n");
        else if(!AW_CombatHurtPlayer(100000,"dbg camera die"))Con_Printf("Not in a game, or already dead.\n");
        return;
    }
    /* FP-WEAPON-SWAY-61: dbg camera sway [1|2|groove|stiff|bench] (view.c aw_fp_sway, saved) */
    if(!Q_strcasecmp(a,"sway") && Cmd_Argc()<=3){
        extern cvar_t aw_fp_sway;extern double V_SwayBench(int n);static char none[1];char *w=Cmd_Argc()==3?Cmd_Argv(2):none;
        if(!Q_strcasecmp(w,"bench")){
            double us=V_SwayBench(2000);
            Con_Printf("Weapon sway arithmetic: %.2f us a frame (2000 rounds: bob, gun angle, idle; table sines).\n",us);
            return;
        }
        if(!strcmp(w,"1") || !Q_strcasecmp(w,"groove"))Cvar_SetValue(aw_fp_sway.name,1);
        else if(!strcmp(w,"2") || !Q_strcasecmp(w,"stiff"))Cvar_SetValue(aw_fp_sway.name,2);
        else if(w[0]){Con_Printf("dbg camera sway [1 groove | 2 stiff | bench]\n");return;}
        Con_Printf("Weapon sway: %s (aw_fp_sway %d, saved).\n",aw_fp_sway.value==2?"Morrowind stiff (still hands)":
            "AmiWind groove (the hands sway with the stride)",aw_fp_sway.value==2?2:1);
        return;
    }
    /* residents drawn from parts (aw_npc_parts.c, NPC-PARTS-RUNTIME-59): npcs = the counters, npcs on/off */
    if(!Q_strcasecmp(a,"npcs") && Cmd_Argc()==2){AW_NpcPartsStatus();return;}
    if(Cmd_Argc()==3 && (on=AW_CompanionToggleWord(Cmd_Argv(2)))>=0){
        if(!Q_strcasecmp(a,"npcs")){AW_NpcPartsSet(on);AW_NpcPartsStatus();return;}
        if(!Q_strcasecmp(a,"vanity")){Cvar_SetValue(vanity_cvar.name,(float)on);return;}
        if(!Q_strcasecmp(a,"death")){Cvar_SetValue(death_cvar.name,(float)on);return;}
        if(!Q_strcasecmp(a,"retry")){Cvar_SetValue(retry_cvar.name,(float)on);return;}
        if(!Q_strcasecmp(a,"body")){Cvar_SetValue(body_cvar.name,(float)on);body_model=NULL;body_race=-2;return;}
        /* the assembled body (on, the default) or the baked one (off, the previous method) */
        if(!Q_strcasecmp(a,"parts")){
            Cvar_SetValue(parts_cvar.name,(float)on);parts_failed=0;parts_sig[0]=0;
            Con_Printf("Player body: %s (aw_player_body_parts %d, saved).\n",on?"assembled from what is worn":"the baked body",on);
            return;
        }
        /* the drawn weapon's stance on the assembled body (on, the default) or the fixed layout (off, the previous way) */
        if(!Q_strcasecmp(a,"stances")){
            Cvar_SetValue(stances_cvar.name,(float)on);stance.picked=0;
            Con_Printf("Weapon stances in third person %s (aw_player_stances %d, saved).\n",on?"on":"off: the fixed layout",on);
            return;
        }
        /* FP-FOREARMS-BELOW-VIEW-61: the original's first-person view (on, the default) or the world's projection with
         * the arms following the whole pitch (off, the previous method) */
        if(!Q_strcasecmp(a,"fpview")){
            Cvar_SetValue(aw_fp_view.name,(float)on);
            Con_Printf("First-person view: %s (aw_fp_view %d, saved).\n",on?"the original's: its own field of view, "
                "the arms lag the pitch":"the world's projection, the arms follow the whole pitch",on);
            return;
        }
        /* the first-person arms from parts (on, the default) or the baked arms (off, the previous method) */
        if(!Q_strcasecmp(a,"hands")){
            Cvar_SetValue(hand_parts_cvar.name,(float)on);hparts_failed=0;hparts_sig[0]=0;hparts.count=0;
            Con_Printf("First-person arms: %s (aw_hand_parts %d, saved).\n",on?"assembled from what is worn":"the baked arms",on);
            return;
        }
    }
    /* PLAYER-VANITY-WALK-STUCK-67: the restart of the body's animation on camera and control changes, off for a
     * before/after comparison (not saved) */
    if(!Q_strcasecmp(a,"motion") && Cmd_Argc()==4 && !Q_strcasecmp(Cmd_Argv(2),"restart")){
        body_restart_on=!Q_strcasecmp(Cmd_Argv(3),"on");
        Con_Printf("Body motion restart on camera and control changes: %s\n",
                   body_restart_on?"on (the default)":"off (the earlier way, for a comparison; not saved)");
        return;
    }
    Con_Printf("Usage: dbg camera [first | third | toggle | distance N | vanity on/off/now | death on/off | retry on/off | body on/off | parts on/off | stances on/off | hands on/off | fpview on/off | sway 1/2/bench | npcs [on/off] | held | motion restart on/off | die]\n");
}
void AW_ViewInit(void) {
    Cvar_RegisterVariable(&view_cvar);Cvar_RegisterVariable(&distance_cvar);Cvar_RegisterVariable(&vanity_cvar);
    Cvar_RegisterVariable(&death_cvar);Cvar_RegisterVariable(&retry_cvar);Cvar_RegisterVariable(&body_cvar);
    Cvar_RegisterVariable(&parts_cvar);Cvar_RegisterVariable(&hand_parts_cvar);Cvar_RegisterVariable(&player_cache_cvar);
    Cvar_RegisterVariable(&stances_cvar);
    aw_hand_weapon_hidden=weapon_hidden;aw_hand_parts_apply=hand_parts_apply;aw_view_hand_part=hand_part;aw_inventory_preview_pending=parts_pending;
    aw_torch_put_away=left_put_away;   /* READY-MAGIC-SHOWS-WEAPON-65: the carried light put away while magic is ready */
    aw_inventory_player_beast=player_beast;aw_race_swapped=race_swapped;
    Cvar_RegisterVariable(&fullview_cvar);Cvar_RegisterVariable(&aw_inventory_preview_reserve);Cvar_RegisterVariable(&aw_inventory_preview_live);
    AW_ViewRulesDefault(&rules);AW_ViewReset(&view,&rules);
    Cmd_AddCommand("+aw_pov",pov_press);Cmd_AddCommand("-aw_pov",pov_release);
    Cmd_AddCommand("aw_view_zoom",zoom_command);Cmd_AddCommand("aw_camera",command);
    Cmd_AddCommand("aw_vanitycam",vanity_command);
    Cmd_AddCommand("aw_setpov",setpov_command);   /* dbg setpov: the view locked for the test stills */
    aw_death_input_locked=AW_DeathLocked;
    aw_death_mouse=AW_ViewDeathMouse;   /* the death box's pointer (MSGBOX-NO-CURSOR-62) */
    aw_death_prompt_active=death_prompt_active;
    aw_view_frame=AW_ViewFrame;aw_view_camera=AW_ViewCamera;aw_view_body=AW_ViewBody;aw_view_hide_hands=AW_ViewThirdPerson;
    aw_view_held=view_held;aw_view_torch_emitter=view_torch_emitter;aw_view_torch_light=view_torch_light;
    /* HELD-LIGHT-OWN-MODEL-61: the held light's place, flames and arm pose in both views */
    aw_view_held_flames=view_held_flames;aw_view_held_light=view_held_light;aw_hand_parts_bone_tag=hand_parts_bone_tag;
    aw_items_player_layer=player_light_layer;
    if(!R_AliasTorchLayer)R_AliasTorchLayer=AW_ItemsTorchLayer;
    aw_view_input=AW_ViewInput;aw_view_key=AW_ViewKey;aw_view_draw=AW_ViewDraw;aw_view_fullscreen=AW_ViewVanityFullscreen;
    aw_view_orbiting=AW_ViewOrbiting;aw_view_turned=view_turned;
    combat_scene=aw_combat_scene;aw_combat_scene=scene_spawn;   /* after AW_CombatInit (aw_debug.c) */
}
