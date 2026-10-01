/* SPDX-License-Identifier: GPL-2.0-or-later
 * On-demand island map and dated, earned journal entries. Closed panels retain
 * no map pixels/text cache. The single-player menu pause captures all input.
 */
#include "quakedef.h"
#include "aw_state.h"
#include "aw_story.h"
#include "aw_character.h"
#include "aw_maps.h"
#include "aw_world.h"
#include <stdint.h>
#define MAP_MAX (512*512+32+8*60)
#define BOOK_PAGES 256
#define BOOK_LINES 9
#define BOOK_WIDTH 132
static int modal,mouse_x=160,mouse_y=100,drag,grid,zoom;
static byte *map_data,*map_pixels;
static int map_w,map_h,map_bounds[4],area_count,marker,map_ocean;
static float map_x,map_y,player_x,player_y,player_z,map_step;
static int map_view_ready,teleport_mode,teleport_selected;
static float teleport_point[3];
static const char *teleport_message;
static char teleport_region[64];
static char opened_scene[64];
static struct {char id[16],title[32];float x,y,scale;} areas[8];
typedef struct {
    char raw[8192],text[16384],titles[AW_STATE_VALUES][96];unsigned short pages[BOOK_PAGES];
    int count,spread,entry,filter,index_mode,index_top,selection,title_rows,index_end;
    int index_x[AW_STATE_VALUES],index_y[AW_STATE_VALUES],index_rows[AW_STATE_VALUES];
} book_t;
static book_t *book;
extern int scr_copyeverything;

static uint32_t u32(const byte *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static float f32(const byte *p){uint32_t n=u32(p);float value;memcpy(&value,&n,4);return value;}
static int minmax(int v,int lo,int hi){return v<lo?lo:v>hi?hi:v;}
static void text(int x,int y,const char *s,int right){
    int w=AW_ConsoleCharWidth();
    for(;*s && x+w<=right;s++,x+=w)AW_ConsoleCharacter(x,y,(unsigned char)*s);
}
static void cursor(void){
    int x=minmax(mouse_x,0,312),y=minmax(mouse_y,0,192),c=AW_UIColor(255,245,190),dark=AW_UIColor(0,0,0);
    AW_UIFill(x,y,3,8,dark);AW_UIFill(x,y,8,3,dark);
    AW_UIFill(x+1,y+1,1,6,c);AW_UIFill(x+1,y+1,6,1,c);
}
static void close_panel(void){
    free(map_data);map_data=map_pixels=NULL;free(book);book=NULL;
    if(modal && key_dest==key_menu)key_dest=key_game;
    modal=drag=teleport_mode=teleport_selected=0;teleport_message=NULL;IN_AWClearButtons();
}
int AW_WorldUIActive(void){return modal!=0;}
static int allowed(void){
    return !modal && key_dest==key_game && sv.active && svs.maxclients==1 && svs.clients &&
        svs.clients[0].edict && cls.state==ca_connected && !AW_StoryRestricted() &&
        !AW_ReaderActive() && !AW_CharacterActive() && !AW_GalleryActive();
}
static void opened(int kind){
    strncpy(opened_scene,sv.name,sizeof(opened_scene)-1);opened_scene[sizeof(opened_scene)-1]=0;
    modal=kind;key_dest=key_menu;IN_AWClearButtons();
}
static void map_fit(void){
    float sx=(float)map_w/310,sy=(float)map_h/150;
    map_step=(sx>sy?sx:sy)/(1<<zoom);
}
static void map_home(void){zoom=0;map_x=map_w*.5f;map_y=map_h*.5f;map_fit();}
static void update_player(void){
    int i;float world[3];edict_t *e;
    marker=0;
    if(!sv.active || !svs.clients || !(e=svs.clients[0].edict))return;
    if(AW_WorldToSource(sv.name,e->v.origin,world)){
        player_x=world[0];player_y=world[1];player_z=world[2];marker=1;return;
    }
    /* Legacy converted payloads predate AWR2. Their AWM1 transform is explicit. */
    for(i=0;i<area_count;i++)if(!strcmp(sv.name,areas[i].id)){
        player_x=e->v.origin[0]/areas[i].scale+areas[i].x;
        player_y=e->v.origin[1]/areas[i].scale+areas[i].y;
        player_z=e->v.origin[2]/areas[i].scale;marker=1;return;
    }
}
static void map_player(void){
    if(!marker)return;
    update_player();
    map_x=(player_x-map_bounds[0])*map_w/(map_bounds[2]-map_bounds[0]);
    map_y=(map_bounds[3]-player_y)*map_h/(map_bounds[3]-map_bounds[1]);
}
static void open_map(void){
    FILE *f=NULL;int size,i,off;byte *p;
    if(!allowed())return;
    size=COM_FOpenFile("world/map.awm",&f);
    if(!f || size<32 || size>MAP_MAX)goto bad;
    map_data=(byte *)malloc(size);if(!map_data)goto bad;
    if(fread(map_data,1,size,f)!=(size_t)size)goto bad;
    fclose(f);f=NULL;p=map_data;
    if(memcmp(p,"AWM1",4))goto bad;
    map_w=p[4]+(p[5]<<8);map_h=p[6]+(p[7]<<8);area_count=(int)u32(p+24);
    if(map_w<1 || map_w>512 || map_h<1 || map_h>512 || area_count<0 || area_count>8)goto bad;
    off=32+area_count*60;map_ocean=(int)u32(p+28);if(map_ocean<0 || map_ocean>255)goto bad;if(size!=off+map_w*map_h)goto bad;
    for(i=0;i<4;i++){map_bounds[i]=(int32_t)u32(p+8+i*4);if(map_bounds[i]<-2000000 || map_bounds[i]>2000000)goto bad;}
    if(map_bounds[2]<=map_bounds[0] || map_bounds[3]<=map_bounds[1])goto bad;
    marker=0;
    for(i=0;i<area_count;i++){
        p=map_data+32+i*60;if(!memchr(p,0,16) || !memchr(p+16,0,32))goto bad;
        memcpy(areas[i].id,p,16);memcpy(areas[i].title,p+16,32);areas[i].x=f32(p+48);areas[i].y=f32(p+52);areas[i].scale=f32(p+56);
        if(!(areas[i].scale>=.0009765625f && areas[i].scale<=100 && areas[i].x>=-2000000 && areas[i].x<=2000000 &&
             areas[i].y>=-2000000 && areas[i].y<=2000000))goto bad;
    }
    update_player();map_pixels=map_data+off;
    if(!map_view_ready){map_home();map_view_ready=1;}else map_fit();
    opened(1);
    if(marker)Con_Printf("World map position: %ld %ld %ld (%s).\n",(long)player_x,(long)player_y,(long)player_z,sv.name);
    Con_Printf("World map: %ld bytes on demand; %s position.\n",(long)size,marker?"exterior":"no exterior");return;
 bad:
    if(f)fclose(f);
    free(map_data);map_data=map_pixels=NULL;
    Con_Printf("World map missing, invalid, or not enough memory.\n");
}
static void open_teleport_map(void){
    keydest_t previous=key_dest;
    if(modal || Cmd_Argc()!=1 || (key_dest!=key_game && key_dest!=key_console))return;
    key_dest=key_game;open_map();
    if(modal!=1){key_dest=previous;return;}
    teleport_mode=1;teleport_selected=0;teleport_message=NULL;
    mouse_x=160;mouse_y=100;
}
static void select_teleport_point(void){
    float px=map_x-156*map_step+(mouse_x-4)*map_step;
    float py=map_y-77*map_step+(mouse_y-19)*map_step;
    const char *region;
    teleport_selected=0;
    if(px<0 || px>=map_w || py<0 || py>=map_h){teleport_message="Outside map bounds";return;}
    teleport_point[0]=map_bounds[0]+px*(map_bounds[2]-map_bounds[0])/map_w;
    teleport_point[1]=map_bounds[3]-py*(map_bounds[3]-map_bounds[1])/map_h;
    teleport_point[2]=0;
    region=AW_RegionNameAt(teleport_point);
    strncpy(teleport_region,region?region:"Region unavailable",sizeof(teleport_region)-1);
    teleport_region[sizeof(teleport_region)-1]=0;
    teleport_selected=1;teleport_message=NULL;
}
static void confirm_teleport(void){
    if(!teleport_selected)return;
    if(AW_MapTeleport(teleport_point))close_panel();
    else teleport_message="Destination unavailable";
}
/* Sorted fixed records permit bounded disk lookups. Offset includes a possible
 * pak member start; no assumption that COM_FOpenFile starts at byte zero. */
static int entry_text(const char *id,int stage,char *out,int capacity){
    FILE *f=NULL;byte header[8],row[76];int size,count,lo,hi,mid,cmp,found=0;uint32_t offset=0,length=0;long base;
    size=COM_FOpenFile("world/journal.awj",&f);if(!f)return 0;
    base=ftell(f);
    if(size<8 || fread(header,1,8,f)!=8 || memcmp(header,"AWJ1",4))goto end_index;
    count=(int)u32(header+4);if(count<0 || count>10000 || size!=8+count*76)goto end_index;
    lo=0;hi=count;
    while(lo<hi){
        mid=lo+(hi-lo)/2;
        if(fseek(f,base+8+(long)mid*76,SEEK_SET) || fread(row,1,76,f)!=76 || !memchr(row,0,64))break;
        cmp=strcmp(id,(char *)row);
        if(!cmp){int value=(int32_t)u32(row+64);cmp=stage<value?-1:stage>value?1:0;}
        if(!cmp){offset=u32(row+68);length=u32(row+72);found=1;break;}
        if(cmp<0)hi=mid;else lo=mid+1;
    }
 end_index:
    fclose(f);f=NULL;if(!found || length<1 || length>(uint32_t)capacity)return 0;
    size=COM_FOpenFile("world/entries.dat",&f);if(!f)return 0;base=ftell(f);
    found=size>0 && offset<=(uint32_t)size && length<=(uint32_t)size-offset &&
        !fseek(f,base+offset,SEEK_SET) && fread(out,1,length,f)==length;
    fclose(f);
    return found && !out[length-1] && !memchr(out,0,length-1);
}
static int expand_entry(void){
    const char *p=book->raw,*value;int n=0,skip;
    while(*p){
        value=NULL;skip=0;
        if(!strncmp(p,"%PCName",7)){value=aw_story.name;skip=7;}
        else if(aw_character.valid && !strncmp(p,"%PCRace",7)){value=aw_races[aw_character.race].name;skip=7;}
        else if(aw_character.valid && !strncmp(p,"%PCClass",8)){value=aw_classes[aw_character.clas].name;skip=8;}
        if(value){while(*value){if(n>=sizeof(book->text)-1)return 0;book->text[n++]=*value++;}p+=skip;}
        else {if(n>=sizeof(book->text)-1)return 0;book->text[n++]=*p++;}
    }
    book->text[n]=0;return 1;
}
static int eligible(int i){return i>=0 && i<aw_state.journal_count && (book->filter<0 || aw_state.journal[i].quest==book->filter);}
static int next_entry(int i,int step){for(i+=step;i>=0 && i<aw_state.journal_count;i+=step)if(eligible(i))return i;return -1;}
/* Centre only already-wrapped lines: AW_UITextBox does not clip. */
static int title_rows(const char *p){
    char line[160];int rows=0;
    do {p=AW_UILine(p,BOOK_WIDTH,line,sizeof(line));rows++;}while(*p);
    return rows;
}
static int page_lines(int page){return BOOK_LINES-((page&1)?0:book->title_rows-1);}
static void index_layout(void){
    int i,col=0,row=0,lines;
    for(i=book->index_top;i<aw_state.count[AW_JOURNAL];i++){
        lines=title_rows(book->titles[i]);
        if(row+lines>BOOK_LINES){col++;row=0;}
        if(col>=2)break;
        book->index_x[i]=14+col*156;book->index_y[i]=40+row*14;book->index_rows[i]=lines;
        row+=lines+1;
    }
    book->index_end=i;
}
static void load_entry(int index){
    int i;const char *p,*before;char line[160];aw_journal_entry_t *entry;
    book->entry=index;book->spread=0;book->count=0;
    if(index<0){strcpy(book->text,"No dated journal entries have been recorded yet. Entries appear here as you earn them during play.");}
    else {
        entry=&aw_state.journal[index];
        if(!entry_text(aw_state.values[AW_JOURNAL][entry->quest].id,entry->stage,book->raw,sizeof(book->raw)))
            strcpy(book->text,"This earned entry has no matching text in the installed journal catalogue. Its quest stage and date remain saved.");
        else if(!expand_entry())strcpy(book->text,"This entry exceeds the reader's text capacity. Its saved history remains intact.");
    }
    AW_UIBookBegin();book->title_rows=1;
    if(index>=0){
        book->title_rows=title_rows(book->titles[aw_state.journal[index].quest]);
    }
    p=book->text;
    while(*p && book->count<BOOK_PAGES){
        book->pages[book->count++]=(unsigned short)(p-book->text);before=p;
        for(i=0;i<page_lines(book->count-1) && *p;i++){before=p;p=AW_UILine(p,BOOK_WIDTH,line,sizeof(line));if(p==before)break;}
        if(page_lines(book->count-1)>0 && p==before && *p)break;
    }
    AW_UIBookEnd();
    if(*p){strcpy(book->text,"This entry exceeds the reader's page capacity. Its saved history remains intact.");book->count=1;book->pages[0]=0;}
    if(!book->count){book->count=1;book->pages[0]=0;}
}
static void quest_titles(void){
    FILE *f=NULL;byte header[8],row[160];int i,j,count,size;
    for(i=0;i<aw_state.count[AW_JOURNAL];i++){
        strcpy(book->titles[i],aw_state.values[AW_JOURNAL][i].id);
        for(j=0;book->titles[i][j];j++)if(book->titles[i][j]=='_')book->titles[i][j]=' ';
    }
    if(!aw_state.count[AW_JOURNAL])return;
    size=COM_FOpenFile("world/quests.awq",&f);if(!f)return;
    if(size<8 || fread(header,1,8,f)!=8 || memcmp(header,"AWQ1",4)){fclose(f);return;}
    count=(int)u32(header+4);
    if(count<0 || count>10000 || size!=8+count*160){fclose(f);return;}
    for(i=0;i<count;i++){
        if(fread(row,1,160,f)!=160 || !memchr(row,0,64) || !memchr(row+64,0,96))break;
        for(j=0;j<aw_state.count[AW_JOURNAL];j++)if(!strcmp((char *)row,aw_state.values[AW_JOURNAL][j].id))
            memcpy(book->titles[j],row+64,96);
    }
    fclose(f);
}
static void open_journal(void){
    if(!allowed())return;
    book=(book_t *)calloc(1,sizeof(*book));if(!book){Con_Printf("Journal reader: not enough memory.\n");return;}
    quest_titles();book->filter=-1;load_entry(aw_state.journal_count-1);opened(2);
    Con_Printf("Journal: %ld earned entries; reader %ld bytes.\n",(long)aw_state.journal_count,(long)sizeof(*book));
}
void AW_WorldUIInit(void){Cmd_AddCommand("aw_teleport_map",open_teleport_map);Cmd_AddCommand("aw_worldmap",open_map);Cmd_AddCommand("aw_journal",open_journal);}
void AW_WorldUIMouse(int dx,int dy){
    int top;
    if(!modal || key_dest!=key_menu)return;
    if(modal==1 && drag){map_x-=dx*map_step;map_y-=dy*map_step;}
    mouse_x=minmax(mouse_x+dx,0,319);mouse_y=minmax(mouse_y+dy,0,199);
    if(modal==2 && book->index_mode && drag){
        top=AW_UIScrollHit(306,minmax(mouse_y,40,165),304,40,126,aw_state.count[AW_JOURNAL],(book->index_end-book->index_top),book->index_top);
        if(top>=0){book->index_top=top;book->selection=top;AW_UIBookBegin();index_layout();AW_UIBookEnd();}
    }
}
static void flip(int direction){
    int entry;
    if(direction>0 && book->spread+2<book->count){book->spread+=2;return;}
    if(direction<0 && book->spread>0){book->spread-=2;return;}
    entry=next_entry(book->entry,direction);
    if(entry>=0){load_entry(entry);if(direction<0)book->spread=((book->count-1)/2)*2;}
}
int AW_WorldUIKey(int key,int down){
    int n;
    if(!modal)return 0;
    if(key_dest!=key_menu){close_panel();return 0;}
    if(!down){if(key==K_MOUSE1 || key==K_MOUSE2)drag=0;return 1;}
    if(key==K_F10 || key=='`'){close_panel();return 0;}
    if(key==K_ESCAPE || (modal==1 && (key=='m' || key=='M')) || (modal==2 && (key=='j' || key=='J'))){close_panel();return 1;}
    if(modal==1){
        if(key==K_MWHEELUP || key=='+' || key=='='){zoom=minmax(zoom+1,0,5);map_fit();}
        if(key==K_MWHEELDOWN || key=='-'){zoom=minmax(zoom-1,0,5);map_fit();}
        if(key==K_LEFTARROW || key=='a')map_x-=24*map_step;
        if(key==K_RIGHTARROW || key=='d')map_x+=24*map_step;
        if(key==K_UPARROW || key=='w')map_y-=24*map_step;
        if(key==K_DOWNARROW || key=='s')map_y+=24*map_step;
        if(key==K_HOME)map_home();
        if(key=='p')map_player();
        if(key=='g')grid=!grid;
        if(teleport_mode){
            if(key==K_MOUSE2 && mouse_y>=19 && mouse_y<173)drag=1;
            if(key==K_ENTER)confirm_teleport();
            if(key==K_MOUSE1){
                if(mouse_x>=4 && mouse_x<316 && mouse_y>=19 && mouse_y<173)select_teleport_point();
                else if(mouse_x>=244 && mouse_x<316 && mouse_y>=184 && mouse_y<199)confirm_teleport();
            }
        }else if(key==K_MOUSE1){if(mouse_y>=19 && mouse_y<173)drag=1;else if(mouse_y>=184)close_panel();}
    }else if(book->index_mode){
        n=aw_state.count[AW_JOURNAL];
        AW_UIBookBegin();index_layout();AW_UIBookEnd();
        if(key==K_TAB){book->index_mode=0;return 1;}
        if(key==K_UPARROW || key==K_MWHEELUP)book->selection--;
        if(key==K_DOWNARROW || key==K_MWHEELDOWN)book->selection++;
        if(key==K_PGUP)book->selection-=(book->index_end-book->index_top);
        if(key==K_PGDN)book->selection+=(book->index_end-book->index_top);
        if(key==K_HOME)book->selection=0;
        if(key==K_END)book->selection=n-1;
        if(key==K_MOUSE1 && mouse_x>=304 && mouse_y>=40 && mouse_y<166){
            drag=1;AW_WorldUIMouse(0,0);return 1;
        }
        if(key==K_MOUSE1 && mouse_y>=40 && mouse_y<166){
            if(!((mouse_x>=14 && mouse_x<146) || (mouse_x>=170 && mouse_x<302)))return 1;
            for(n=book->index_top;n<book->index_end;n++)
                if(mouse_x>=book->index_x[n] && mouse_x<book->index_x[n]+BOOK_WIDTH &&
                   mouse_y>=book->index_y[n] && mouse_y<book->index_y[n]+book->index_rows[n]*14)break;
            if(n==book->index_end)return 1;
            book->selection=n;n=aw_state.count[AW_JOURNAL];key=K_ENTER;
        }
        book->selection=minmax(book->selection,0,n?n-1:0);
        if(book->selection<book->index_top)book->index_top=book->selection;
        AW_UIBookBegin();index_layout();
        while(book->selection>=book->index_end && book->index_top<book->selection){book->index_top++;index_layout();}
        AW_UIBookEnd();
        if(key==K_ENTER && n){book->filter=book->selection;book->index_mode=0;load_entry(next_entry(aw_state.journal_count,-1));}
        if(key==K_MOUSE1 && mouse_y>=176){book->index_mode=0;book->filter=-1;load_entry(aw_state.journal_count-1);}
    }else{
        if(key==K_TAB){book->index_mode=1;book->selection=book->index_top=0;return 1;}
        if(key==K_BACKSPACE){book->filter=-1;load_entry(aw_state.journal_count-1);return 1;}
        if(key==K_MOUSE1){
            if(mouse_y>=26 && mouse_y<26+book->title_rows*14 && mouse_x>=14 && mouse_x<146 && book->entry>=0){
                book->filter=aw_state.journal[book->entry].quest;load_entry(next_entry(aw_state.journal_count,-1));return 1;
            }
            if(mouse_y>=174 && mouse_y<188){
                if(mouse_x>=14 && mouse_x<90)key=K_LEFTARROW;
                else if(mouse_x>=230 && mouse_x<302)key=K_RIGHTARROW;
                else if(mouse_x>=102 && mouse_x<146){book->index_mode=1;return 1;}
            }
        }
        if(key==K_LEFTARROW || key==K_PGUP || key==K_MWHEELUP)flip(-1);
        if(key==K_RIGHTARROW || key==K_PGDN || key==K_MWHEELDOWN || key==K_SPACE)flip(1);
        if(key==K_HOME)load_entry(next_entry(-1,1));
        if(key==K_END)load_entry(next_entry(aw_state.journal_count,-1));
    }
    return 1;
}
static void map_draw(void){
    int x,y,sx,sy,cols[312],ocean=map_ocean,gold=AW_UIColor(248,225,136),i,mx,my;
    float left=map_x-156*map_step,top=map_y-77*map_step,px,py;byte *dst;char line[96];
    const char *region;float source[3];int width,limit;
    update_player();
    AW_UIFill(0,0,320,200,AW_UIColor(15,20,23));
    for(x=0;x<312;x++)cols[x]=(int)floor(left+x*map_step);
    for(y=0;y<154;y++){
        sy=(int)floor(top+y*map_step);dst=vid.buffer+(y+19)*vid.rowbytes+4;
        for(x=0;x<312;x++){sx=cols[x];dst[x]=(sx>=0 && sx<map_w && sy>=0 && sy<map_h)?map_pixels[sy*map_w+sx]:ocean;}
    }
    if(grid){
        for(i=map_bounds[0]/8192;i<=map_bounds[2]/8192;i++){
            px=(i*8192.0f-map_bounds[0])*map_w/(map_bounds[2]-map_bounds[0]);mx=4+(int)((px-left)/map_step);
            if(mx>=4 && mx<316)for(y=19;y<173;y+=4)AW_UIFill(mx,y,1,1,gold);
        }
        for(i=map_bounds[1]/8192;i<=map_bounds[3]/8192;i++){
            py=(map_bounds[3]-i*8192.0f)*map_h/(map_bounds[3]-map_bounds[1]);my=19+(int)((py-top)/map_step);
            if(my>=19 && my<173)for(x=4;x<316;x+=4)AW_UIFill(x,my,1,1,gold);
        }
    }
    for(i=0;i<area_count;i++){
        px=(areas[i].x-map_bounds[0])*map_w/(map_bounds[2]-map_bounds[0]);py=(map_bounds[3]-areas[i].y)*map_h/(map_bounds[3]-map_bounds[1]);
        mx=4+(int)((px-left)/map_step);my=19+(int)((py-top)/map_step);
        if(mx>=6 && mx<313 && my>=22 && my<161){AW_UIFill(mx-1,my-1,3,3,gold);text(mx+4,my,areas[i].title,314);}
    }
    if(marker){
        px=(player_x-map_bounds[0])*map_w/(map_bounds[2]-map_bounds[0]);py=(map_bounds[3]-player_y)*map_h/(map_bounds[3]-map_bounds[1]);
        mx=4+(int)((px-left)/map_step);my=19+(int)((py-top)/map_step);
        if(mx>=9 && mx<311 && my>=24 && my<168){AW_UIFill(mx-4,my,9,1,AW_UIColor(255,255,255));AW_UIFill(mx,my-4,1,9,AW_UIColor(255,255,255));}
        sprintf(line,"Cell %ld,%ld XYZ %ld %ld %ld",(long)floor(player_x/8192),(long)floor(player_y/8192),
            (long)player_x,(long)player_y,(long)player_z);
    }else strcpy(line,"Interior: no exterior position fix");
    if(teleport_mode){
        text(8,1,"DEBUG TELEPORT",315);
        text(8,10,"CLICK ON TARGET TO TELEPORT",315);
        if(teleport_selected){
            px=(teleport_point[0]-map_bounds[0])*map_w/(map_bounds[2]-map_bounds[0]);
            py=(map_bounds[3]-teleport_point[1])*map_h/(map_bounds[3]-map_bounds[1]);
            mx=4+(int)((px-left)/map_step);my=19+(int)((py-top)/map_step);
            for(i=-5;i<=5;i++){
                if(mx+i>=4 && mx+i<316 && my>=19 && my<173)AW_UIFill(mx+i,my,1,1,AW_UIColor(255,32,32));
                if(mx>=4 && mx<316 && my+i>=19 && my+i<173)AW_UIFill(mx,my+i,1,1,AW_UIColor(255,32,32));
            }
            sprintf(line,"XY %ld %ld / %s",(long)teleport_point[0],(long)teleport_point[1],teleport_region);
            text(8,176,teleport_message?teleport_message:line,315);
            AW_UIFill(244,184,72,15,gold);AW_UIFill(245,185,70,13,AW_UIColor(29,23,17));
            text(244+(72-8*AW_ConsoleCharWidth())/2,188,"TELEPORT",315);
        }else if(teleport_message)text(8,176,teleport_message,315);
        text(8,188,"R-drag/arrows pan +/- zoom Esc close",240);
    }else{
        text(8,5,"Vvardenfell",315);text(116,5,line,315);
        width=AW_ConsoleCharWidth();
        text(8,176,width<=4?"Drag/arrows pan  Wheel +/- zoom  P player G grid":
             "Pan: drag  +/- zoom  M/Esc close",315);
        text(8,188,width<=4?"Home fit M/Esc close":"P/G/Home",88);
        /* The player's original CELL determines the region, never map pan or
         * the pointer. Interiors have no exterior coordinate fix. */
        source[0]=player_x;source[1]=player_y;source[2]=player_z;
        region=marker?AW_RegionNameAt(source):NULL;
        snprintf(line,sizeof(line),"REGION: %s",region?region:"unavailable");
        limit=(315-96)/width;
        if((int)strlen(line)>limit){line[limit]=0;memcpy(line+limit-3,"...",3);}
        text(315-(int)strlen(line)*width,188,line,315);
    }
}
static void journal_draw(void){
    static const int month_days[12]={31,28,31,30,31,30,31,31,30,31,30,31};
    int i,j,x,y,entry=book->entry,page,ink=AW_UIColor(38,29,20),gold=AW_UIColor(103,65,27),d,m,year;
    char line[160];const char *p;aw_journal_entry_t *e;
    AW_UIFill(0,0,320,200,AW_UIColor(29,23,17));
    AW_UIFill(5,5,153,190,AW_UIColor(223,207,166));AW_UIFill(162,5,153,190,AW_UIColor(232,217,180));
    AW_UIFill(158,5,4,190,AW_UIColor(92,70,43));
    AW_UIBookBegin();
    if(book->index_mode){
        AW_UITextBox(14,12,BOOK_WIDTH,14,"Quests",ink);
        AW_UITextBox(170,12,BOOK_WIDTH,14,"Journal",ink);
        index_layout();
        for(j=book->index_top;j<book->index_end;j++){
            x=book->index_x[j];y=book->index_y[j];
            if(j==book->selection)AW_UIFill(x-4,y,140,book->index_rows[j]*14,AW_UIColor(203,186,145));
            p=book->titles[j];
            for(i=0;i<book->index_rows[j];i++){
                p=AW_UILine(p,BOOK_WIDTH,line,sizeof(line));
                AW_UITextBox(x,y+i*14,BOOK_WIDTH,14,line,gold);
            }
        }
        AW_UIScrollbar(304,40,126,aw_state.count[AW_JOURNAL],(book->index_end-book->index_top),book->index_top);
        if(!aw_state.count[AW_JOURNAL])AW_UITextBox(14,42,BOOK_WIDTH,14,"No quests yet.",ink);
        AW_UITextBox(14,176,BOOK_WIDTH,12,"Tab: return",ink);
        AW_UITextBox(170,176,BOOK_WIDTH,12,"All entries",gold);
    }else{
        if(entry>=0){
            e=&aw_state.journal[entry];d=e->days+227;year=427+d/365;d%=365;m=0;
            while(d>=month_days[m])d-=month_days[m++];
            sprintf(line,"%02ld/%02ld/%ld",(long)d+1,(long)m+1,(long)year);AW_UIText(14,10,line,ink);
            AW_UITextBox(170,10,132,14,"Journal",ink);
            p=book->titles[e->quest];
            for(i=0;i<book->title_rows;i++){
                p=AW_UILine(p,BOOK_WIDTH,line,sizeof(line));
                AW_UITextBox(14,26+i*14,BOOK_WIDTH,14,line,gold);
            }
        }else AW_UIText(14,12,"Journal",ink);
        for(j=0;j<2;j++){
            page=book->spread+j;if(page>=book->count)continue;p=book->text+book->pages[page];
            y=44+(j?0:(book->title_rows-1)*14);
            for(i=0;i<page_lines(page) && *p;i++){p=AW_UILine(p,BOOK_WIDTH,line,sizeof(line));AW_UIText(14+j*156,y+i*14,line,ink);}
        }
        AW_UIText(14,176,"< Previous",gold);AW_UIText(239,176,"Next >",gold);
        AW_UITextBox(102,174,44,14,"Quests",gold);
    }
    AW_UIBookEnd();
    sprintf(line,"%ld/%ld  Tab quests Backspace all J close",(long)(entry+1),(long)aw_state.journal_count);
    AW_UIFill(5,188,310,12,AW_UIColor(29,23,17));
    text(8,190,line,314);
}
int AW_WorldUIDraw(void){
    if(!modal)return 0;
    if(!sv.active || strcmp(opened_scene,sv.name) || key_dest!=key_menu){close_panel();return 0;}
    if(modal==1){
        /* Bounded ocean margin also keeps float-to-pixel casts in range. */
        if(map_x<-map_w)map_x=-map_w;
        if(map_x>2*map_w)map_x=2*map_w;
        if(map_y<-map_h)map_y=-map_h;
        if(map_y>2*map_h)map_y=2*map_h;
        map_draw();
    }else journal_draw();cursor();scr_copyeverything=1;return 1;
}
