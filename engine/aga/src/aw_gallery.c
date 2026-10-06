/* SPDX-License-Identifier: GPL-2.0-or-later
 * Disk catalogue, one actor and its footprint per isolated inspection map.
 * Catalogue rows are scanned, not kept resident in the Amiga runtime heap.
 */
#include "quakedef.h"
#include "aw_save.h"
#include "aw_character.h"
#include "aw_region.h"
typedef struct {
    int number;char kind[8],model[2][24],id[96],name[96];float size[3];
} gallery_entry_t;
static gallery_entry_t current;
#define GALLERY_PAGE 8
static int count,selected,body,editing,session,returning,help;
static gallery_entry_t *page;
static int page_indices[GALLERY_PAGE],page_top,page_count,page_total,page_selected,filtering;
static int mouse_x,mouse_y,mouse_visible,scroll_drag;
static char filter[96];
static aw_save_t *back_state;
typedef struct {char sound[96],text[2048];float duration;} gallery_voice_t;
static gallery_voice_t *voice;
static int back_intro,combat,torch_test,torch_actor;
static float back_torch,combat_timing[4],back_fullbright;
extern cvar_t r_fullbright;
static const char *hand_timing[4]={"aw_hand_idle","aw_hand_draw","aw_hand_lower","aw_hand_punch"};
static void hand_field(edict_t *p,const char *name,float value){
    eval_t *v=GetEdictFieldValue(p,(char *)name);if(v)v->_float=value;
}
static void combat_pose(edict_t *p,int state){
    hand_field(p,"aw_hand_goal",state==4?0:1);
    hand_field(p,"aw_torch",0);hand_field(p,"aw_attack_latched",0);
    hand_field(p,"aw_hand_state",state);hand_field(p,"aw_hand_started",sv.time);
}
static void combat_center(edict_t *p){
    p->v.origin[0]=p->v.origin[1]=0;p->v.origin[2]=17;
    VectorCopy(p->v.origin,p->v.oldorigin);VectorCopy(vec3_origin,p->v.velocity);
    p->v.angles[0]=p->v.angles[2]=0;p->v.angles[1]=180;
    VectorCopy(p->v.angles,p->v.v_angle);VectorCopy(p->v.angles,cl.viewangles);
    p->v.movetype=MOVETYPE_WALK;p->v.fixangle=1;SV_LinkEdict(p,false);
}
static char query[96],notice[96],back_map[32],model_path[2][64];
static vec3_t back_origin,back_angles;
static float back_move,back_health,back_hand_goal;

int AW_TorchTestActive(void){return torch_test && session && sv.active && !strcmp(sv.name,"torchtest");}
/* Only captured, active diagnostic rooms may ignore the source story's input
 * restrictions. Revoke permission as soon as return begins, before map load. */
int AW_DebugTestInputActive(void){
    return session && !returning && sv.active &&
        ((combat && !strcmp(sv.name,"charplane")) ||
         (torch_test && !strcmp(sv.name,"torchtest")));
}
int AW_GalleryActive(void){return sv.active && (!strcmp(sv.name,"charplane") || AW_TorchTestActive());}
int AW_GalleryModal(void){return AW_GalleryActive() && key_dest==key_game && (page || help || editing);}
static void normalize(const char *in,char *out) {
    int n=0;unsigned char c;
    while((c=(unsigned char)*in++) && n<95){
        if(c>='A' && c<='Z')c+='a'-'A';
        if((c>='a' && c<='z') || (c>='0' && c<='9'))out[n++]=c;
    }
    out[n]=0;
}
static int model_key(const char *s) {
    int i;if(!strcmp(s,"-"))return 1;
    if(strlen(s)!=17 || s[0]!='m')return 0;
    for(i=1;i<17;i++)if(!((s[i]>='0' && s[i]<='9') || (s[i]>='a' && s[i]<='f')))return 0;
    return 1;
}
static int read_entry(char *line,gallery_entry_t *e) {
    char *fields[9],*s=line,*end;int i;long number;
    for(i=0;i<9;i++){
        fields[i]=s;end=strchr(s,i==8?'\n':'\t');
        if(!end)return 0;
        *end=0;s=end+1;
    }
    number=strtol(fields[0],&end,10);
    if(*end || number<1 || number>100000)return 0;
    if(strcmp(fields[1],"NPC_") && strcmp(fields[1],"CREA"))return 0;
    if(!model_key(fields[2]) || !model_key(fields[3]) || strlen(fields[7])>95 || strlen(fields[8])>95)return 0;
    memset(e,0,sizeof(*e));e->number=(int)number;strcpy(e->kind,fields[1]);
    strcpy(e->model[0],fields[2]);strcpy(e->model[1],fields[3]);strcpy(e->id,fields[7]);strcpy(e->name,fields[8]);
    for(i=0;i<3;i++){
        e->size[i]=(float)strtod(fields[4+i],&end);
        if(*end || !(e->size[i]>=0 && e->size[i]<4096))return 0;
    }
    return 1;
}
static void read_voice(void) {
    FILE *f=NULL;char line[2304],*path,*duration,*speech,*end;float seconds;
    if(voice){free(voice);voice=NULL;}
    if(!session || combat || torch_test || COM_FOpenFile("gallery/voices.txt",&f)<0 || !f)return;
    if(!fgets(line,sizeof(line),f) || strcmp(line,"AWGV1\n")){fclose(f);return;}
    while(fgets(line,sizeof(line),f)){
        path=strchr(line,'\t');if(!path)break;*path++=0;
        duration=strchr(path,'\t');if(!duration)break;*duration++=0;
        speech=strchr(duration,'\t');if(!speech)break;*speech++=0;
        end=strchr(speech,'\n');if(!end)break;*end=0;
        if(Q_strcasecmp(line,current.id))continue;
        seconds=(float)strtod(duration,&end);
        if(*end || !(seconds>0 && seconds<=120) || strlen(path)>95 || strlen(speech)>2047 ||
           strstr(path,"..") || path[0]=='/' || strchr(path,':') || strchr(path,'\\'))break;
        voice=(gallery_voice_t *)malloc(sizeof(*voice));
        if(voice){strcpy(voice->sound,path);strcpy(voice->text,speech);voice->duration=seconds;}
        break;
    }
    fclose(f);
}
static void talk(void) {
    FILE *f=NULL;char path[112];
    if(!voice)return;
    sprintf(path,"sound/%s",voice->sound);
    if(COM_FOpenFile(path,&f)<44 || !f){if(f)fclose(f);strcpy(notice,"Greeting audio unavailable.");return;}
    fclose(f);S_LocalSound(voice->sound);AW_UIVoiceSubtitle(current.name,voice->text,voice->duration);
}
/* Prefer an exact source ID. Repeated display names select the first stable ID
 * and explicitly report how many variants share that name. */
static int select_entry(int index,const char *search) {
    FILE *f=NULL;char line[512],needle[96],id[96],name[96],extra;int total,i,matches=0,match_index=0,exact=0;
    gallery_entry_t e,match;long number=0;char *end;
    if(COM_FOpenFile("gallery/catalog.txt",&f)<0 || !f){
        f=NULL;
        if(COM_FOpenFile("npc-gallery-disabled.txt",&f)>=0 && f){
            fclose(f);strcpy(notice,"Gallery disabled by --no-npc-gallery.");
        }else strcpy(notice,"Gallery catalogue missing; rebuild the image.");
        return 0;
    }
    if(!fgets(line,sizeof(line),f) || sscanf(line,"AWG1 %d %c",&total,&extra)!=1 || total<1 || total>100000)goto bad;
    if(search){normalize(search,needle);if(!needle[0])goto bad;number=strtol(search,&end,10);if(*end)number=0;}
    index=(index%total+total)%total;
    for(i=0;i<total;i++){
        if(!fgets(line,sizeof(line),f) || !read_entry(line,&e))goto bad;
        if(!search){if(i==index){match=e;match_index=i;matches=1;}}
        else{
            normalize(e.id,id);normalize(e.name,name);
            if((number && number==e.number) || (!number && !strcmp(id,needle))){match=e;match_index=i;exact=1;}
            else if(!number && !strcmp(name,needle)){
                matches++;if(!exact && (matches==1 || e.number<match.number)){match=e;match_index=i;}
            }
        }
    }
    fclose(f);
    if(search && !exact && !matches){strcpy(notice,"No matching source ID, name or number.");return 0;}
    current=match;selected=match_index;count=total;notice[0]=0;
    if(search && !exact && matches>1)sprintf(notice,"%ld matches; first ID shown. Use source ID for variant.",(long)matches);
    return 1;
bad:
    fclose(f);strcpy(notice,"Invalid gallery catalogue or lookup.");return 0;
}
/* Only this small page is allocated while the browser is open. Drawing,
 * ordinary play and typing do not scan the catalogue. Enter applies a filter;
 * paging reads one bounded row at a time from disk. All keywords must match. */
static int keyword_match(const gallery_entry_t *e,const char *search) {
    char id[96],name[96],term[96],token[96],number[16];int n;
    normalize(e->id,id);normalize(e->name,name);sprintf(number,"%ld",(long)e->number);
    while(*search){
        while(*search==' ')search++;
        if(!*search)break;
        n=0;while(*search && *search!=' '){if(n<95)token[n++]=*search;search++;}token[n]=0;
        normalize(token,term);
        if(!term[0] || (!strstr(id,term) && !strstr(name,term) && strcmp(number,term)))return 0;
    }
    return 1;
}
static void close_browser(void){if(page){free(page);page=NULL;}filtering=scroll_drag=mouse_visible=0;}
static int read_page(int top) {
    FILE *f=NULL;char text[512],extra;gallery_entry_t e;int total,i,n=0;
    page_count=page_total=0;
    if(!page || COM_FOpenFile("gallery/catalog.txt",&f)<0 || !f)goto bad;
    if(!fgets(text,sizeof(text),f) || sscanf(text,"AWG1 %d %c",&total,&extra)!=1 || total<1 || total>100000)goto bad;
    for(i=0;i<total;i++){
        if(!fgets(text,sizeof(text),f) || !read_entry(text,&e))goto bad;
        if(!keyword_match(&e,filter))continue;
        if(n>=top && page_count<GALLERY_PAGE){page[page_count]=e;page_indices[page_count++]=i;}n++;
    }
    fclose(f);page_total=n;page_top=top;page_selected=0;notice[0]=0;return 1;
bad:
    if(f)fclose(f);
    page_count=page_total=0;strcpy(notice,"Gallery browser: catalogue unavailable or invalid.");return 0;
}
static void open_browser(void) {
    if(!page)page=(gallery_entry_t *)malloc(sizeof(*page)*GALLERY_PAGE);
    if(!page){strcpy(notice,"Not enough memory for the gallery browser.");return;}
    help=editing=0;filter[0]=0;filtering=1;read_page(0);IN_AWClearButtons();
    mouse_x=vid.width/2;mouse_y=vid.height/2;mouse_visible=1;scroll_drag=0;
}
static int page_rows(void){int n=(vid.height-76)/(2*AW_ConsoleCharHeight()+2);if(n<1)n=1;if(n>GALLERY_PAGE)n=GALLERY_PAGE;return n;}
static int mouse_row(void) {
    int h=AW_ConsoleCharHeight(),top=22+3*h,row;
    if(mouse_x<6 || mouse_x>=vid.width-22 || mouse_y<top)return -1;
    row=(mouse_y-top)/(2*h+2);
    return row<page_count && row<page_rows()?row:-1;
}
static void scroll_mouse(void) {
    int h=AW_ConsoleCharHeight(),top=22+3*h,height=page_rows()*(2*h+2),y=mouse_y,n;
    if(y<top)y=top;
    if(y>=top+height)y=top+height-1;
    n=AW_UIScrollHit(vid.width-14,y,vid.width-18,top,height,page_total,page_rows(),page_top);
    if(n>=0 && n!=page_top)read_page(n);
}
void AW_GalleryMouse(int dx,int dy) {
    int row;
    if(!AW_GalleryModal() || !page || (!dx && !dy))return;
    mouse_visible=1;mouse_x+=dx;mouse_y+=dy;
    if(mouse_x<0)mouse_x=0;
    if(mouse_x>=vid.width)mouse_x=vid.width-1;
    if(mouse_y<0)mouse_y=0;
    if(mouse_y>=vid.height)mouse_y=vid.height-1;
    if(scroll_drag){scroll_mouse();return;}
    row=mouse_row();if(row>=0){page_selected=row;filtering=0;}
}
static void reload(void) {
    close_browser();read_voice();editing=help=0;key_dest=key_game;IN_AWClearButtons();
    Cbuf_InsertText(torch_test?"map torchtest\n":"map charplane\n");
}
static void leave(void) {
    char command[64];FILE *f=NULL;
    if(!session || !back_state || returning){Con_Printf("No gallery return is pending.\n");return;}
    /* A missing return scene must leave the temporary snapshot available. */
    sprintf(command,"maps/%s.bsp",back_map);
    if(COM_FOpenFile(command,&f)<124 || !f){if(f)fclose(f);strcpy(notice,"Return scene unavailable; snapshot retained.");Con_Printf("%s\n",notice);return;}
    fclose(f);
    if(!AW_RegionSelect(back_map,back_origin,back_intro)){strcpy(notice,"Return region unavailable; snapshot retained.");return;}
    AW_SaveSnapshotRestore(back_state);
    close_browser();editing=help=0;returning=1;key_dest=key_game;IN_AWClearButtons();
    sprintf(command,"map %s\n",back_map);Cbuf_InsertText(command);
}
static int capture_game(void) {
    edict_t *p;eval_t *goal;
    if(!session){
        if(!sv.active || svs.maxclients!=1 || !svs.clients || !(p=svs.clients[0].edict)){
            Con_Printf("Start a local game before entering the gallery.\n");return 0;
        }
        if(strlen(sv.name)>=sizeof(back_map)){Con_Printf("Scene name too long.\n");return 0;}
        back_state=(aw_save_t *)malloc(sizeof(*back_state));
        if(!back_state || !AW_SaveSnapshot(back_state)){
            if(back_state)free(back_state);
            back_state=NULL;
            Con_Printf("Cannot capture the current game for gallery return.\n");return 0;
        }
        strcpy(back_map,sv.name);VectorCopy(p->v.origin,back_origin);
        back_intro=!strcmp(sv.modelname,"maps/intro_docks.bsp");
        VectorCopy(cl.viewangles,back_angles);back_move=p->v.movetype;session=1;body=0;
        back_health=p->v.health;goal=GetEdictFieldValue(p,"aw_hand_goal");back_hand_goal=goal?goal->_float:0;
        goal=GetEdictFieldValue(p,"aw_torch");back_torch=goal?goal->_float:0;
    }
    return 1;
}
static void command(void) {
    char search[96];int i,n=0;
    if(Cmd_Argc()==2 && !Q_strcasecmp(Cmd_Argv(1),"exit")){leave();return;}
    if(combat || torch_test){Con_Printf("Exit combat/torch test before entering the NPC gallery.\n");return;}
    if(AW_GalleryActive() && Cmd_Argc()==2 && !Q_strcasecmp(Cmd_Argv(1),"talk")){key_dest=key_game;talk();return;}
    if(AW_GalleryActive() && Cmd_Argc()==2 && !Q_strcasecmp(Cmd_Argv(1),"browse")){key_dest=key_game;open_browser();return;}
    if(AW_GalleryActive() && Cmd_Argc()==2 && !Q_strcasecmp(Cmd_Argv(1),"help")){key_dest=key_game;close_browser();help=1;return;}
    if(AW_GalleryActive() && Cmd_Argc()==2 && (!strcmp(Cmd_Argv(1),"next") || !strcmp(Cmd_Argv(1),"previous"))){
        if(select_entry(selected+(!strcmp(Cmd_Argv(1),"next")?1:-1),NULL))reload();
        return;
    }
    if(AW_GalleryActive() && Cmd_Argc()==2 && !strcmp(Cmd_Argv(1),"body")){body=!body;reload();return;}
    for(i=1;i<Cmd_Argc();i++){
        if(n+(int)strlen(Cmd_Argv(i))+2>(int)sizeof(search)){Con_Printf("Gallery lookup too long.\n");return;}
        if(n)search[n++]=' ';
        strcpy(search+n,Cmd_Argv(i));n+=strlen(Cmd_Argv(i));
    }
    search[n]=0;
    if(!select_entry(0,n?search:NULL)){Con_Printf("%s\n",notice);return;}
    if(!capture_game())return;
    reload();
}
static void combat_command(void){
    edict_t *p;eval_t *v;FILE *f=NULL;int i,state=-1;
    const char *arg=Cmd_Argv(1);
    if(Cmd_Argc()==2 && !Q_strcasecmp((char *)arg,"exit")){leave();return;}
    if(Cmd_Argc()>2){Con_Printf("Usage: dbg combattest [idle/draw/lower/punch/center/help/exit].\n");return;}
    if(combat && AW_GalleryActive() && !returning){
        p=svs.clients[0].edict;
        if(!*arg || !Q_strcasecmp((char *)arg,"center"))combat_center(p);
        else if(!Q_strcasecmp((char *)arg,"help"))help=1;
        else if(!Q_strcasecmp((char *)arg,"idle"))state=2;
        else if(!Q_strcasecmp((char *)arg,"draw"))state=1;
        else if(!Q_strcasecmp((char *)arg,"lower"))state=4;
        else if(!Q_strcasecmp((char *)arg,"punch"))state=3;
        else {Con_Printf("Usage: dbg combattest [idle/draw/lower/punch/center/help/exit].\n");return;}
        if(state>=0)combat_pose(p,state);
        key_dest=key_game;IN_AWClearButtons();return;
    }
    if(*arg){Con_Printf("Enter with dbg combattest before choosing an action.\n");return;}
    if(session || AW_GalleryActive()){Con_Printf("Exit the current gallery first.\n");return;}
    if(!sv.active || !sv.edicts || svs.maxclients!=1 || !svs.clients || !svs.clients[0].edict){
        Con_Printf("Start a local game before entering combat test.\n");return;
    }
    /* Reuse the authored timing contract from the running game. The gallery
     * BSP has no hand stamp; inventing durations would hide conversion bugs. */
    for(i=0;i<4;i++){
        v=GetEdictFieldValue(sv.edicts,(char *)hand_timing[i]);
        if(!v || !isfinite(v->_float) || v->_float<=0 || v->_float>60){
            Con_Printf("Combat test needs valid hands in the current game.\n");return;
        }
        combat_timing[i]=v->_float;
    }
    if(COM_FOpenFile("maps/charplane.bsp",&f)<124 || !f){
        if(f)fclose(f);Con_Printf("Combat test floor missing; rebuild the gallery.\n");return;
    }
    fclose(f);
    if(!capture_game())return;
    combat=1;notice[0]=0;reload();
}
static void torch_center(edict_t *p){combat_center(p);p->v.origin[0]=64;VectorCopy(p->v.origin,p->v.oldorigin);SV_LinkEdict(p,false);}
static void torch_command(void){
    edict_t *p;eval_t *v;FILE *f=NULL;int i,n=0,want_actor=0;char search[96];
    gallery_entry_t previous=current;
    const char *arg=Cmd_Argv(1);
    if(Cmd_Argc()==2 && !Q_strcasecmp((char *)arg,"exit")){leave();return;}
    if(session && !torch_test){Con_Printf("Exit the current gallery first.\n");return;}
    if(torch_test && AW_TorchTestActive() && !returning && Cmd_Argc()<=2){
        if(!*arg || !Q_strcasecmp((char *)arg,"center"))torch_center(svs.clients[0].edict);
        else if(!Q_strcasecmp((char *)arg,"help"))help=1;
        else if(!Q_strcasecmp((char *)arg,"empty")){torch_actor=0;reload();return;}
        else goto usage;
        key_dest=key_game;IN_AWClearButtons();return;
    }
    if(*arg){
        if(Q_strcasecmp((char *)arg,"npc") || Cmd_Argc()<3)goto usage;
        for(i=2;i<Cmd_Argc();i++){
            if(n+(int)strlen(Cmd_Argv(i))+2>(int)sizeof(search))goto usage;
            if(n)search[n++]=' ';strcpy(search+n,Cmd_Argv(i));n+=strlen(Cmd_Argv(i));
        }
        search[n]=0;
        if(!select_entry(0,search)){Con_Printf("%s\n",notice);return;}
        if(strcmp(current.kind,"NPC_") || current.size[0]>96 || current.size[1]>96 || current.size[2]>104){
            current=previous;
            Con_Printf("Torch room needs an NPC no larger than 96 x 96 x 104 units.\n");return;
        }
        want_actor=1;
    }
    if(torch_test && AW_TorchTestActive() && !returning){torch_actor=want_actor;body=0;reload();return;}
    if(session || AW_GalleryActive()){Con_Printf("Exit the current gallery first.\n");return;}
    if(!sv.active || !sv.edicts || svs.maxclients!=1 || !svs.clients || !(p=svs.clients[0].edict)){
        Con_Printf("Start a local game before entering torch test.\n");return;
    }
    for(i=0;i<4;i++){
        v=GetEdictFieldValue(sv.edicts,(char *)hand_timing[i]);
        if(!v || !isfinite(v->_float) || v->_float<=0 || v->_float>60){
            Con_Printf("Torch test needs valid hands in the current game.\n");return;
        }
        combat_timing[i]=v->_float;
    }
    if(COM_FOpenFile("maps/torchtest.bsp",&f)<124 || !f){
        if(f)fclose(f);Con_Printf("Dark torch test room missing; rebuild the image.\n");return;
    }
    fclose(f);if(!capture_game())return;
    torch_test=1;torch_actor=want_actor;body=0;notice[0]=0;
    back_fullbright=r_fullbright.value;Cvar_Set("r_fullbright","0");reload();return;
usage:
    Con_Printf("Usage: dbg torchtest [npc ID/name | empty/center/help/exit].\n");
}
void AW_GalleryInit(void){Cmd_AddCommand("aw_charplane",command);Cmd_AddCommand("aw_combattest",combat_command);Cmd_AddCommand("aw_torchtest",torch_command);}
static int gallery_budget(const char *path) {
    FILE *f=NULL;unsigned char head[72];int vertices,triangles;
    if(COM_FOpenFile((char *)path,&f)<72 || !f){if(f)fclose(f);return 0;}
    if(fread(head,1,sizeof(head),f)!=sizeof(head)){fclose(f);return 0;}fclose(f);
    if(memcmp(head,"IDPO",4))return 0;
    vertices=head[60]+(head[61]<<8)+(head[62]<<16);triangles=head[64]+(head[65]<<8)+(head[66]<<16);
    if(head[63] || head[67])return 0;
    if(!AW_AliasBudgetAllows(vertices,triangles)){
        sprintf(notice,"%ld triangles: needs aw_allow_poly_budget_over true and sufficient cap.",(long)triangles);return 0;
    }
    return 1;
}
/* Called before server baseline creation, while precaching is still legal. */
static float model_lift(void) {
    FILE *f=NULL;char line[96],*tab,*end;float lift=0,value;
    if(COM_FOpenFile("gallery/poses.txt",&f)<0 || !f)return 0;
    if(fgets(line,sizeof(line),f) && !strcmp(line,"AWGP1\n"))while(fgets(line,sizeof(line),f)){
        tab=strchr(line,'\t');if(!tab)break;*tab++=0;
        value=(float)strtod(tab,&end);
        if((*end!='\n' && *end) || !(value>=0 && value<=1024))break;
        if(!strcmp(line,current.model[body])){lift=value;break;}
    }
    fclose(f);return lift;
}
void AW_GalleryEntities(void) {
    int i,j;edict_t *e;model_t *m;float lift;
    /* SV_SpawnServer calls this before setting sv.active. Runtime predicates
     * must stay inactive then, but this captured session's map needs its
     * timings and actors before physics/baselines and client spawn. */
    if(!session || strcmp(sv.name,torch_test?"torchtest":"charplane"))return;
    if(combat || torch_test){
        for(i=0;i<4;i++)hand_field(sv.edicts,hand_timing[i],combat_timing[i]);
        if(!torch_test || !torch_actor)return; /* Empty tests need no catalogue. */
    }
    if(!strcmp(current.model[body],"-")){strcpy(notice,"Conversion failed; see the private gallery audit.");return;}
    sprintf(model_path[0],"gallery/%s.mdl",current.model[body]);
    sprintf(model_path[1],"gallery/f%s.mdl",current.model[body]+1);
    lift=model_lift();
    for(j=0;j<(torch_test?1:2);j++){
        if(!gallery_budget(model_path[j])){if(!notice[0])strcpy(notice,"Selected model is missing or invalid.");continue;}
        m=Mod_ForName(model_path[j],false);
        if(!m){strcpy(notice,"Model unavailable: check its budget exception, cap and files.");continue;}
        if(torch_test && (!(m->maxs[0]>=m->mins[0]) || !(m->maxs[1]>=m->mins[1]) || !(m->maxs[2]>=m->mins[2]))){
            strcpy(notice,"NPC model bounds are invalid.");return;
        }
        if(torch_test && (!(m->maxs[0]-m->mins[0]<=96) || !(m->maxs[1]-m->mins[1]<=96) ||
           !(m->maxs[2]-m->mins[2]+lift<=104))){strcpy(notice,"NPC model does not fit the dark room.");return;}
        for(i=1;i<MAX_MODELS && sv.model_precache[i];i++);
        if(i==MAX_MODELS){strcpy(notice,"Gallery model table full.");return;}
        sv.model_precache[i]=model_path[j];sv.models[i]=m;
        e=ED_Alloc();e->v.model=ED_NewString(model_path[j])-pr_strings;e->v.modelindex=i;
        e->v.movetype=MOVETYPE_NONE;e->v.solid=SOLID_NOT;
        if(!j)for(i=0;i<3;i++)current.size[i]=m->maxs[i]-m->mins[i];
        e->v.origin[2]=j?0.35f:0.25f-m->mins[2]+lift;
        if(torch_test){e->v.origin[0]=-40-(m->mins[0]+m->maxs[0])*.5f;e->v.origin[1]=-(m->mins[1]+m->maxs[1])*.5f;}
        SV_LinkEdict(e,false);
    }
    Con_Printf("Gallery #%ld %s: %s (%s)\n",(long)current.number,current.id,current.name,body?"base body":"equipped");
}
void AW_GallerySpawn(edict_t *p) {
    float distance;eval_t *goal;
    if(returning){
        if(strcmp(sv.name,back_map)){returning=0;strcpy(notice,"Return scene did not load; snapshot retained.");return;}
        AW_SaveSnapshotRestore(back_state);free(back_state);back_state=NULL;
        if(voice){free(voice);voice=NULL;}
        if(torch_test)Cvar_SetValue("r_fullbright",back_fullbright);
        returning=session=combat=torch_test=torch_actor=0;VectorCopy(back_origin,p->v.origin);VectorCopy(back_origin,p->v.oldorigin);
        VectorCopy(vec3_origin,p->v.velocity);VectorCopy(back_angles,p->v.angles);VectorCopy(back_angles,p->v.v_angle);
        VectorCopy(back_angles,cl.viewangles);p->v.movetype=back_move;p->v.health=back_health;
        goal=GetEdictFieldValue(p,"aw_hand_goal");if(goal)goal->_float=back_hand_goal;
        hand_field(p,"aw_torch",back_torch);
        p->v.fixangle=1;SV_LinkEdict(p,false);return;
    }
    if(!AW_GalleryActive()){
        if(torch_test)Cvar_SetValue("r_fullbright",back_fullbright);
        close_browser();editing=help=session=combat=torch_test=torch_actor=0;
        if(back_state){free(back_state);back_state=NULL;}
        if(voice){free(voice);voice=NULL;}return;
    }
    if(!session)return;
    if(torch_test){torch_center(p);combat_pose(p,1);return;}
    if(combat){combat_center(p);combat_pose(p,1);return;}
    distance=current.size[0]>current.size[1]?current.size[0]:current.size[1];
    if(distance<current.size[2])distance=current.size[2];
    distance*=1.5f;if(distance<72)distance=72;if(distance>400)distance=400;
    p->v.origin[0]=distance;p->v.origin[1]=0;p->v.origin[2]=17;
    VectorCopy(vec3_origin,p->v.velocity);p->v.movetype=MOVETYPE_WALK;
    p->v.angles[0]=0;p->v.angles[1]=180;p->v.angles[2]=0;p->v.fixangle=1;
    VectorCopy(p->v.angles,cl.viewangles);SV_LinkEdict(p,false);
}
int AW_GalleryKey(int key,int down,int shift,int control) {
    int n,rows;
    if(!AW_GalleryActive() || key_dest!=key_game)return 0;
    if(control && (key=='x' || key=='X')){if(down)leave();return 1;}
    if(key==K_F1){if(down){close_browser();editing=0;help=!help;IN_AWClearButtons();}return 1;}
    if(help){if(down && key==K_ESCAPE)help=0;return 1;}
    if(combat || torch_test)return 0; /* Normal movement, hands and torch bindings. */
    if(page){
        if(key==K_MOUSE1 && !down){scroll_drag=0;return 1;}
        if(!down)return 1;
        if(key==K_ESCAPE || key==K_TAB || key==K_MOUSE2){close_browser();IN_AWClearButtons();return 1;}
        rows=page_rows();
        if(key==K_MOUSE1){
            int h=AW_ConsoleCharHeight(),top=22+3*h,height=rows*(2*h+2);
            n=AW_UIScrollHit(mouse_x,mouse_y,vid.width-18,top,height,page_total,rows,page_top);
            if(n>=0){filtering=0;scroll_drag=mouse_y>=top+10 && mouse_y<top+height-10;if(n!=page_top)read_page(n);return 1;}
            n=mouse_row();
            if(n>=0){current=page[n];selected=page_indices[n];notice[0]=0;reload();}
            else if(mouse_y>=10+h && mouse_y<14+2*h)filtering=1;
            return 1;
        }
        if(shift && key==K_UPARROW)key=K_PGUP;
        if(shift && key==K_DOWNARROW)key=K_PGDN;
        if(key==K_ENTER){
            if(filtering){read_page(0);filtering=0;}
            else if(page_count){current=page[page_selected];selected=page_indices[page_selected];notice[0]=0;reload();}
            return 1;
        }
        if(key==K_DOWNARROW || key==K_MWHEELDOWN){
            if(filtering)filtering=0;
            if(page_top+page_selected+1<page_total){
                if(page_selected+1<rows && page_selected+1<page_count)page_selected++;
                else read_page(page_top+rows);
            }return 1;
        }
        if(key==K_UPARROW || key==K_MWHEELUP){
            filtering=0;
            if(page_selected)page_selected--;
            else if(page_top){read_page(page_top>rows?page_top-rows:0);page_selected=rows-1;if(page_selected>=page_count)page_selected=page_count-1;}
            return 1;
        }
        if(key==K_PGDN || key==K_PGUP){
            filtering=0;n=page_top+(key==K_PGDN?rows:-rows);if(n<0)n=0;
            if(n<page_total)read_page(n);
            return 1;
        }
        if(key==K_HOME){filtering=0;read_page(0);return 1;}
        if(key==K_END){filtering=0;read_page(page_total?((page_total-1)/rows)*rows:0);return 1;}
        n=strlen(filter);
        if(key==K_BACKSPACE){filtering=1;if(n)filter[n-1]=0;return 1;}
        if(key>=32 && key<127 && n<95){filtering=1;filter[n]=(char)key;filter[n+1]=0;}return 1;
    }
    if(editing){
        if(!down)return 1;
        if(key==K_ESCAPE){editing=0;IN_AWClearButtons();return 1;}
        n=strlen(query);
        if(key==K_ENTER){if(select_entry(0,query))reload();return 1;}
        if(key==K_BACKSPACE){if(n)query[n-1]=0;return 1;}
        if(key>=32 && key<127 && n<95){query[n]=(char)key;query[n+1]=0;}return 1;
    }
    if(key==K_ENTER){if(down){editing=1;query[0]=notice[0]=0;IN_AWClearButtons();}return 1;}
    if(key>='A' && key<='Z')key+='a'-'A';
    if(key=='e'){if(down)talk();return 1;}
    /* Amiga's middle button is K_MOUSE2; the right button is K_MOUSE3. */
    if(key==K_TAB || key==K_MOUSE2 || (key=='b' && !shift)){if(down)open_browser();return 1;}
    if(key==K_MWHEELUP || key==K_MWHEELDOWN){
        if(down && select_entry(selected+(key==K_MWHEELDOWN?1:-1),NULL))reload();
        return 1;
    }
    if(shift && (key=='n' || key=='p' || key=='b')){
        if(!down)return 1;
        if(key=='b')body=!body;
        else if(!select_entry(selected+(key=='n'?1:-1),NULL))return 1;
        reload();return 1;
    }
    return 0;
}
static void text_at(int x,int y,const char *s,int limit) {
    int w=AW_ConsoleCharWidth();
    if(y<0 || y+AW_ConsoleCharHeight()>vid.height)return;
    for(;*s && limit-- && x+w<=vid.width;s++,x+=w)AW_ConsoleCharacter(x,y,(unsigned char)*s);
}
static void line(int row,const char *s){text_at(4,4+row*AW_ConsoleCharHeight(),s,160);}
static void right_line(int y,const char *s){
    int n=strlen(s),w=AW_ConsoleCharWidth(),limit=(vid.width-12)/w;if(n>limit)n=limit;
    text_at(vid.width-6-n*w,y,s,n);
}
void AW_GalleryDraw(void) {
    char text[160];int y,h=AW_ConsoleCharHeight(),w=AW_ConsoleCharWidth(),i,rows;
    extern int scr_copyeverything;
    static const char *guide[]={"Character Model Gallery","Tab / B: browse friendly names","Type keywords; Enter: apply filter",
        "Arrows / wheel / PgUp/PgDn: browse","Shift+Up/Down: page on Amiga keys","Enter / click: show character","Shift+N / Shift+P: next / previous",
        "Shift+B: equipped / base body","Enter (in gallery): exact ID/name/#","WASD + mouse: inspect at true scale",
        "E: converted greeting, when available",
        "Ctrl+X: return to the captured game","F10: console; dbg gallery exit","F1 / Esc: close this help"};
    if(!AW_GalleryActive() || key_dest!=key_game)return;
    if(torch_test){
        line(0,"Torch test - dark enclosed room");
        line(1,torch_actor?current.name:"Empty room");line(2,"V: torch  F: hands  F1: help  Ctrl+X: return");
        if(notice[0])line(4,notice);
        if(help){
            AW_UIBox(2,2,vid.width-4,vid.height-4);
            line(1,"Torch test: no baked or ambient room light");
            line(3,"WASD + mouse: move; V: torch on/off");
            line(4,"F: hands; weapon retains minimum visibility");
            line(6,"dbg torch strength 0..1 / radius 32..288");
            line(7,"dbg torchtest npc ID/name (one fitting NPC)");
            line(8,"dbg torchtest empty / center");
            line(10,"Ctrl+X or dbg torchtest exit: return");line(11,"F1 / Esc: close help");
        }
        scr_copyeverything=1;return;
    }
    if(combat){
        edict_t *p=svs.clients[0].edict;eval_t *state=GetEdictFieldValue(p,"aw_hand_state");
        line(0,"Combat test - empty gallery floor");
        sprintf(text,"Hands state %ld / frame %ld",state?(long)state->_float:0L,(long)p->v.weaponframe);line(1,text);
        line(2,"Attack: punch  F: draw/lower  F1: help");
        if(help){
            AW_UIBox(2,2,vid.width-4,vid.height-4);
            line(1,"Combat test: current race/sex hands");
            line(3,"WASD + mouse: move and inspect");
            line(4,"Attack: punch; release for next punch");
            line(5,"F: draw/lower using normal animation");
            line(7,"F10: dbg combattest idle/draw/lower");
            line(8,"dbg combattest punch / center");
            line(10,"Ctrl+X or dbg combattest exit: return");
            line(11,"F1 / Esc: close help");
        }
        scr_copyeverything=1;return;
    }
    sprintf(text,"%ld/%ld #%ld %s",(long)(selected+1),(long)count,(long)current.number,current.name);line(0,text);
    line(1,current.id);
    sprintf(text,"%s: %ld x %ld x %ld units",body?"Base body":"Equipped",(long)current.size[0],(long)current.size[1],(long)current.size[2]);line(2,text);
    line(3,"Wheel / Shift+N/P: next/prev  F1: help");
    if(editing){sprintf(text,"> %s_",query);line(5,text);}if(notice[0])line(6,notice);
    /* The reserved strip remains readable independently of target aim and HUD.
     * Paint after normal subtitles: the identity and browse controls persist. */
    y=vid.height-2*h-6;
    AW_UIFill(0,vid.height-28,vid.width,28,AW_UIColor(0,0,0));
    right_line(y,current.name);right_line(y+h,voice?"(Talk: E / Browse: Tab)  F1: help":"(Browse: Tab / B)  F1: help");
    if(help){
        AW_UIBox(2,2,vid.width-4,vid.height-4);
        for(i=0;i<(int)(sizeof(guide)/sizeof(*guide));i++)text_at(8,8+i*(h+3),guide[i],(vid.width-16)/w);
    }else if(page){
        rows=page_rows();AW_UIBox(2,2,vid.width-4,vid.height-4);
        text_at(8,8,"Gallery browser - Tab/Esc: close",(vid.width-16)/w);
        sprintf(text,"Find: %s%s",filter,filtering?"_":"");text_at(8,10+h,text,(vid.width-16)/w);
        sprintf(text,"%ld matches - Enter: %s",(long)page_total,filtering?"filter":"show");text_at(8,14+2*h,text,(vid.width-16)/w);
        for(i=0;i<page_count && i<rows;i++){
            y=22+3*h+i*(2*h+2);
            if(i==page_selected && !filtering)AW_UIFill(6,y-1,vid.width-26,2*h+2,AW_UIColor(50,43,28));
            /* Amiga's small formatter consumes a word for %c. Construct the
             * prefix directly so an int-sized vararg cannot insert a NUL. */
            text[0]=i==page_selected?'>':' ';text[1]=' ';strcpy(text+2,page[i].name);
            text_at(8,y,text,(vid.width-34)/w);
            sprintf(text,"  #%ld %s",(long)page[i].number,page[i].id);text_at(8,y+h,text,(vid.width-34)/w);
        }
        AW_UIScrollbar(vid.width-18,22+3*h,rows*(2*h+2),page_total,rows,page_top);
        if(notice[0])text_at(8,vid.height-h-5,notice,(vid.width-16)/w);
        else text_at(8,vid.height-h-5,"Wheel/page keys; click to show",(vid.width-16)/w);
        if(mouse_visible){
            int ink=AW_UIColor(255,230,160),dark=AW_UIColor(0,0,0);
            AW_UIFill(mouse_x,mouse_y,2,9,dark);AW_UIFill(mouse_x,mouse_y,7,2,dark);
            AW_UIFill(mouse_x+1,mouse_y+1,1,7,ink);AW_UIFill(mouse_x+1,mouse_y+1,5,1,ink);
            AW_UIFill(mouse_x+2,mouse_y+2,3,3,ink);
        }
    }
    scr_copyeverything=1;
}
