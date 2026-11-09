/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_character.h"
#include "aw_inventory.h"
#include "aw_story.h"
aw_character_t aw_character;
#include <assert.h>
#include <sys/stat.h>
#include <unistd.h>
viddef_t vid;refdef_t r_refdef;keydest_t key_dest;double realtime;double host_frametime=.02;
client_static_t cls;server_t sv;server_static_t svs;int scr_copyeverything;
byte pal[768],glyphs[16384],frame[64004];byte *host_basepal=pal,*draw_chars=glyphs;
static char *directory;
static int hud_tracking,hud_allocations,file_reads;
void *__real_malloc(size_t size);
void *__wrap_malloc(size_t size){if(hud_tracking)hud_allocations++;return __real_malloc(size);}
static void item_u32(byte *p,unsigned n){int i;for(i=0;i<4;i++)p[i]=(n>>(8*i))&255;}
static void item_float(byte *p,float f){unsigned bits;memcpy(&bits,&f,4);item_u32(p,bits);}
static void item_row(FILE *f,const char *id,int shield){
    byte row[512];memset(row,0,sizeof(row));
    strcpy((char *)row,id);strcpy((char *)row+64,id);
    item_u32(row+160,shield?AW_INV_ARMOUR:AW_INV_WEAPON);
    item_u32(row+164,shield?8:1);item_float(row+172,12);
    item_u32(row+176,1U<<(shield?AW_SLOT_LEFT:AW_SLOT_RIGHT));item_u32(row+180,7);
    strcpy((char *)row+184,"progs/inv/fixture.mdl");
    item_u32(row+440,shield?0:2);item_u32(row+444,26);
    item_float(row+472,shield?0:1);item_float(row+476,shield?0:1.35f);
    item_float(row+480,shield?300:900);item_float(row+484,shield?15:0);
    item_u32(row+488,shield?2:0);item_u32(row+492,shield?30:0);
    assert(fwrite(row,1,sizeof(row),f)==sizeof(row));
}
static void hud_box(byte *out,int x){
    int y;for(y=0;y<24;y++)memcpy(out+y*24,vid.buffer+(174+y)*vid.rowbytes+x,24);
}

static int guard_state;static int test_guard(void){return guard_state;}
static cvar_t *loading_parameter,*region_parameter,*delay_parameter,*hud_parameter,*cursor_parameter;
static double loading_clock;
double Sys_FloatTime(void){return loading_clock;}
static int queued_prison;
static int hud_debug;
int AW_DebugTestInputActive(void){return hud_debug;}
void AW_CharacterReset(void){}
void AW_SaveReset(void){}
void IN_AWClearButtons(void){}
int AW_MusicStartTrack(int track){assert(track==4);return 1;}
void AW_MusicHold(void){}
void Cbuf_AddText(char *text){assert(!strcmp(text,"map prison\n"));queued_prison=1;}
int COM_FOpenFile(char *name,FILE **f){char p[1024];int n;file_reads++;sprintf(p,"%s/%s",directory,name);*f=fopen(p,"rb");if(!*f)return -1;fseek(*f,0,SEEK_END);n=ftell(*f);rewind(*f);return n;}
void Con_Printf(char *fmt,...){}
void CDAudio_Update(void){}
void S_ExtraUpdate(void){}
void Cvar_RegisterVariable(cvar_t *c){c->value=atof(c->string);if(!strcmp(c->name,"aw_loading_style"))loading_parameter=c;else if(!strcmp(c->name,"aw_region_loading"))region_parameter=c;else if(!strcmp(c->name,"aw_region_loading_delay"))delay_parameter=c;else if(!strcmp(c->name,"aw_ui_hud"))hud_parameter=c;else if(!strcmp(c->name,"aw_cursor_type"))cursor_parameter=c;}
int AW_LoadingScreen(void){return 1;}
int AW_MenuFrontEnd(void){return 0;}
void Cvar_SetValue(char *s,float v){if(region_parameter && !strcmp(s,region_parameter->name))region_parameter->value=v;
 if(cursor_parameter && !strcmp(s,cursor_parameter->name))cursor_parameter->value=v;}
/* CURSOR-MW-58: Morrowind's pointer from gfx/cursor.awc (AWC1: width, height, the tip, then indices, 255 clear).
 * art: 1 a valid file (4x3, tip at 1,0), 0 none in the image, -1 a corrupt one (tip outside the art). Without a
 * usable file, or with aw_cursor_type 1, AW_UICursor draws nothing and returns 0: the window draws AmiWind's cursor. */
static void check_cursor(int art){
 static const byte pixels[12]={255,7,255,255, 7,7,7,255, 255,255,255,9};
 byte file[8+12];char path[160];FILE *f;int i;
 memcpy(file,"AWC1",4);file[4]=4;file[5]=3;file[6]=art<0?4:1;file[7]=0;memcpy(file+8,pixels,12);
 sprintf(path,"%s/gfx/cursor.awc",directory);
 if(art){f=fopen(path,"wb");assert(f);assert(fwrite(file,1,sizeof(file),f)==sizeof(file));fclose(f);}
 assert(cursor_parameter && cursor_parameter->archive && !strcmp(cursor_parameter->string,"2"));
 assert(cursor_parameter->value==2 && AW_UICursorType()==2);
 memset(frame,137,sizeof(frame));
 if(art>0){
  assert(AW_UICursorAvailable() && AW_UICursor(50,60));
  /* the tip (1,0) lands on the pointer; clear pixels keep what was under them */
  assert(vid.buffer[60*320+50]==7 && vid.buffer[60*320+49]==137 && vid.buffer[60*320+51]==137);
  assert(vid.buffer[61*320+49]==7 && vid.buffer[61*320+51]==7 && vid.buffer[61*320+52]==137);
  assert(vid.buffer[62*320+52]==9 && vid.buffer[62*320+49]==137);
  /* at the screen's edges the art is clipped, nothing outside the frame is written */
  assert(AW_UICursor(319,199) && AW_UICursor(0,0) && AW_UICursor(-5,-5) && AW_UICursor(400,300));
  assert(vid.buffer[199*320+319]==7 && frame[0]==137 && frame[1]==137 && frame[64002]==137 && frame[64003]==137);
 }else{
  assert(!AW_UICursorAvailable() && !AW_UICursor(50,60));
  for(i=0;i<(int)sizeof(frame);i++)assert(frame[i]==137);
 }
 /* aw_cursor_type 1: AmiWind's cursor; the setting is saved (archive) and anything else reads as Morrowind's (2) */
 AW_UICursorTypeSet(1);assert(cursor_parameter->value==1 && AW_UICursorType()==1);
 memset(frame,137,sizeof(frame));assert(!AW_UICursor(50,60));
 for(i=0;i<(int)sizeof(frame);i++)assert(frame[i]==137);
 AW_UICursorTypeSet(7);assert(cursor_parameter->value==2 && AW_UICursorType()==2);
 cursor_parameter->value=0;assert(AW_UICursorType()==2);cursor_parameter->value=2;
 assert(!AW_UICursor(50,60)==(art<=0));
 if(art)unlink(path);
}
void Cmd_AddCommand(char *s,void(*f)(void)){}
char *Cmd_Argv(int i){return "";}
int Cmd_Argc(void){return 0;}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
static void check_hud_bars(int health,int magicka,int fatigue) {
 int row,x,n,expected[3];expected[0]=health;expected[1]=magicka;expected[2]=fatigue;
 memset(vid.buffer,137,64000);AW_UIHud();
 for(row=0;row<3;row++){
  n=0;for(x=10;x<81;x++)if(vid.buffer[(176+row*8)*320+x]!=0)n++;
  assert(n==expected[row]);
 }
}
int main(int argc,char **argv){
 byte raw[2057],before[3];const char *p;char line[9],temporary[]="aw-ui-XXXXXX",path[128];int i;FILE *f;
 directory=argc>1?argv[1]:".";
 memset(raw,0,sizeof(raw));memcpy(raw,"AWF1",4);raw[4]=16;raw[5]=18;raw[6]=1;
 assert(AW_UIValidateFont(raw,sizeof(raw)));raw[8+2]=32;raw[8+3]=32;assert(!AW_UIValidateFont(raw,sizeof(raw)));
 raw[8+2]=raw[8+3]=0;raw[8+6]=255;assert(!AW_UIValidateFont(raw,sizeof(raw)));
 /* Three coverage levels expose gold fringes around explicitly black text. */
 assert(mkdtemp(temporary));directory=temporary;
 sprintf(path,"%s/gfx",directory);assert(!mkdir(path,0700));
 memset(raw,0,sizeof(raw));memcpy(raw,"AWF1",4);raw[4]=14;raw[5]=16;raw[6]=1;
 raw[8+'A'*8+2]=3;raw[8+'A'*8+3]=1;raw[8+'A'*8+6]=3;raw[2056]=0x6c;
 /* Visible masks for the actual Guard/name rendering controls. */
 {const char *letters="GuardTarget";const char *c;
  for(c=letters;*c;c++){raw[8+(unsigned char)*c*8+2]=1;
   raw[8+(unsigned char)*c*8+3]=1;raw[8+(unsigned char)*c*8+6]=4;}}

 sprintf(path,"%s/gfx/magic14.awf",directory);f=fopen(path,"wb");assert(f);assert(fwrite(raw,1,sizeof(raw),f)==sizeof(raw));fclose(f);
 raw[4]=12;raw[5]=14;
 sprintf(path,"%s/gfx/book12.awf",directory);f=fopen(path,"wb");assert(f);assert(fwrite(raw,1,sizeof(raw),f)==sizeof(raw));fclose(f);
 for(i=0;i<256;i++)pal[i*3]=pal[i*3+1]=pal[i*3+2]=i;
 memset(frame,137,sizeof(frame));vid.width=320;vid.height=200;vid.rowbytes=320;vid.buffer=frame+2;
 AW_UIInit();AW_UIBox(-12,-12,80,80);AW_UIBox(300,190,80,80);
 /* UI-INVENTORY-HEADING-CENTRE-42: a title centred by its painted rows has equal space above and
  * below in its band (the fixture glyphs paint one row), and is centred across the band. */
 {
  int x,y,top=-1,bottom=-1,left=-1,right=-1,c=AW_UIColor(223,199,144);(void)c;
  memset(frame,0,sizeof(frame));AW_UITextCentred(6,6,308,12,"Guard",c);
  for(y=6;y<18;y++)for(x=6;x<314;x++)if(vid.buffer[y*vid.rowbytes+x]){
   if(top<0)top=y;
   bottom=y;if(left<0 || x<left)left=x;if(x>right)right=x;}
  assert(top>=0 && (top-6)-(17-bottom)>=-1 && (top-6)-(17-bottom)<=1);
  assert((left-6)-(313-right)>=-1 && (left-6)-(313-right)<=1);
  memset(frame,137,sizeof(frame));
 }
 /* Real HUD pixels: full non-100 stats, independent fractions, live health,
  * invalid maxima, damage and overheal must not alter character state. */
 {
  client_t local;edict_t player;aw_character_t saved;
  memset(&local,0,sizeof(local));memset(&player,0,sizeof(player));
  cls.state=ca_connected;aw_character.valid=1;
  aw_character.current[0]=aw_character.maximum[0]=55;
  aw_character.current[1]=aw_character.maximum[1]=40;
  aw_character.current[2]=aw_character.maximum[2]=180;
  check_hud_bars(71,71,71);
  aw_character.current[0]=27.5;aw_character.current[1]=10;aw_character.current[2]=90;
  check_hud_bars(35,17,35);
  sv.active=true;svs.maxclients=1;svs.clients=&local;local.edict=&player;
  player.v.health=55;saved=aw_character;check_hud_bars(71,17,35);
  assert(!memcmp(&saved,&aw_character,sizeof(saved)));
  player.v.health=0;check_hud_bars(0,17,35);
  player.v.health=100;check_hud_bars(71,17,35);
  aw_character.maximum[0]=0;aw_character.maximum[1]=-1;aw_character.maximum[2]=NAN;
  check_hud_bars(0,0,0);
  aw_character.valid=0;sv.active=false;check_hud_bars(71,71,71);
  svs.clients=NULL;cls.state=ca_disconnected;
 }
 /* Original opening channels: compare actual pixels, including clearing a
  * formerly visible rail and preserving game state when toggling manual HUD. */
 {
  int stage,channel,x,y,painted;aw_state_t unchanged;
  const int left[3]={8,88,116},width[3]={75,24,24},bit[3]={1,2,4};
  cls.state=ca_connected;r_refdef.vrect.height=172;r_refdef.vrect.width=320;
  AW_StoryReset(1);
  for(stage=AW_STAGE_SHIP;stage<=AW_STAGE_PAPERS;stage++){
   aw_story.stage=stage;unchanged=aw_state;memset(vid.buffer,137,64000);AW_UIHud();
   for(channel=0;channel<3;channel++){
    painted=0;for(y=174;y<198;y++)for(x=left[channel];x<left[channel]+width[channel];x++)
     if(vid.buffer[y*320+x])painted++;
    assert((painted>0)==(stage==AW_STAGE_PAPERS && channel==0));
   }
   assert(!memcmp(&unchanged,&aw_state,sizeof(unchanged)));
  }
  assert(AW_StoryPapersRead());assert(AW_StoryHudChannels()==(AW_HUD_STATS|AW_HUD_WEAPON));
  for(stage=0;stage<3;stage++){
   int mask=stage==2?AW_HUD_ALL:AW_HUD_STATS|AW_HUD_WEAPON;
   if(stage==1){assert(AW_ItemAdd(&aw_state,"chargen statssheet",1));assert(AW_StoryTransition(AW_STAGE_COURTYARD));}
   if(stage==2){assert(AW_CourtyardTakeRing());assert(AW_ItemAdd(&aw_state,"ring_keley",-1));}
   AW_UIHud();
   for(channel=0;channel<3;channel++){
    painted=0;for(y=174;y<198;y++)for(x=left[channel];x<left[channel]+width[channel];x++)if(vid.buffer[y*320+x])painted++;
    assert((painted>0)==((mask&bit[channel])!=0));
   }
  }
  unchanged=aw_state;hud_parameter->value=0;AW_UIHud();
  for(y=174;y<198;y++)for(x=8;x<140;x++)assert(vid.buffer[y*320+x]==0);
  assert(!memcmp(&unchanged,&aw_state,sizeof(unchanged)));
  hud_parameter->value=1;AW_UIHud();assert(vid.buffer[174*320+88]!=0);
  AW_StoryReset(1);AW_UIHud();for(y=174;y<198;y++)for(x=8;x<140;x++)assert(vid.buffer[y*320+x]==0);
  hud_debug=1;AW_UIHud();assert(vid.buffer[174*320+88]!=0);hud_debug=0;
  AW_StoryReset(0);memset(&r_refdef.vrect,0,sizeof(r_refdef.vrect));cls.state=ca_disconnected;
 }
 /* Guard is painted at the lower right under the viewport, never over the world or the crosshair.
  * Compare real pixels while the guard callback/state toggles; target-name drawing stays alive. */
 {
  static byte unguarded[64000];int x,y,painted=0,changed=0;
  cls.state=ca_connected;r_refdef.vrect.x=r_refdef.vrect.y=0;
  r_refdef.vrect.width=320;r_refdef.vrect.height=172;
  aw_combat_guard_marker=test_guard;guard_state=0;
  memset(vid.buffer,137,64000);AW_UIHud();memcpy(unguarded,vid.buffer,64000);
  guard_state=1;memset(vid.buffer,137,64000);AW_UIHud();
  assert(guard_state==1 && aw_combat_guard_marker());
  for(y=0;y<200;y++)for(x=0;x<320;x++)if(vid.buffer[y*320+x]!=unguarded[y*320+x]){
    assert(x>=200 && y>=172);changed++;   /* only the strip's lower right */
  }
  assert(changed>0);
  for(y=50;y<120;y++)for(x=100;x<220;x++)assert(vid.buffer[y*320+x]==137);
  AW_UITargetName("Target");
  for(y=0;y<25;y++)for(x=200;x<320;x++)if(vid.buffer[y*320+x]!=137)painted++;
  assert(painted>0); /* Ordinary target labels retain their original location. */
  aw_combat_guard_marker=NULL;guard_state=0;
  memset(&r_refdef.vrect,0,sizeof(r_refdef.vrect));cls.state=ca_disconnected;
 }
 /* Actual HUD pixels plus real inventory lookup/transactions. The generic
  * weapon/fist mark follows carried state; left shield never becomes magic. */
 {
  byte fist[576],armed[576],empty_magic[576],again[576];aw_inventory_item_t item;
  int reads,draws;char inventory_path[128];FILE *catalogue;
  sprintf(inventory_path,"%s/inventory",directory);assert(!mkdir(inventory_path,0700));
  strcat(inventory_path,"/items.awi");catalogue=fopen(inventory_path,"wb");assert(catalogue);
  assert(fwrite("AWI2",1,4,catalogue)==4);
  {byte count[4]={3,0,0,0};assert(fwrite(count,1,4,catalogue)==4);}
  item_row(catalogue,"fixture_axe",0);item_row(catalogue,"fixture_shield",1);item_row(catalogue,"fixture_sword",0);
  fclose(catalogue);memset(&aw_state,0,sizeof(aw_state));cls.state=ca_connected;
  AW_UIHud();hud_box(fist,88);hud_box(empty_magic,116);
  assert(AW_InventoryRead("fixture_sword",&item));
  assert(AW_ItemAdd(&aw_state,item.id,1) && AW_InventoryEquip(&aw_state,&item));
  AW_UIHud();hud_box(armed,88);assert(memcmp(fist,armed,sizeof(fist)));
  reads=file_reads;hud_allocations=0;hud_tracking=1;
  for(draws=0;draws<32;draws++)AW_UIHud();
  hud_tracking=0;assert(!hud_allocations && file_reads==reads);
  assert(AW_InventoryUnequip(&aw_state,item.id));AW_UIHud();hud_box(again,88);
  assert(!memcmp(fist,again,sizeof(fist)));
  assert(AW_InventoryRead("fixture_shield",&item));
  assert(AW_ItemAdd(&aw_state,item.id,1) && AW_InventoryEquip(&aw_state,&item));
  AW_UIHud();hud_box(again,116);assert(!memcmp(empty_magic,again,sizeof(again)));
  hud_box(again,88);assert(!memcmp(fist,again,sizeof(again)));
  assert(AW_InventoryRead("fixture_axe",&item));
  assert(AW_ItemAdd(&aw_state,item.id,1) && AW_InventoryEquip(&aw_state,&item));
  AW_UIHud();hud_box(again,88);assert(!memcmp(armed,again,sizeof(again)));
  /* A stale slot without actual ownership cannot display an equipped weapon. */
  assert(AW_StateSet(&aw_state,AW_ITEM,item.id,0));AW_UIHud();hud_box(again,88);
  assert(!memcmp(fist,again,sizeof(again)));
  assert(AW_ItemAdd(&aw_state,item.id,1));AW_UIHud();hud_box(again,88);
  assert(!memcmp(armed,again,sizeof(again)));
  assert(AW_InventoryUnequip(&aw_state,item.id));AW_UIHud();hud_box(again,88);
  assert(!memcmp(fist,again,sizeof(again)));
  hud_box(again,116);assert(!memcmp(empty_magic,again,sizeof(again)));
  cls.state=ca_disconnected;unlink(inventory_path);
  sprintf(inventory_path,"%s/inventory",directory);rmdir(inventory_path);
 }
 AW_UIScrollbar(276,54,133,9,7,0);AW_UIScrollbar(315,190,100,100,6,94);
 assert(AW_UIScrollHit(280,55,276,54,133,9,7,1)==0);
 assert(AW_UIScrollHit(280,186,276,54,133,9,7,1)==2);
 assert(AW_UIScrollHit(275,100,276,54,133,9,7,0)==-1);
 assert(AW_UIScrollHit(280,100,276,54,133,7,7,0)==-1);
 for(i=64;i<177;i++){int top=AW_UIScrollHit(280,i,276,54,133,100,7,0);assert(top>=0 && top<=93);}
 AW_UIText(-40,-10,"Bounds: Wgjpq 123",-1);AW_UIText(315,195,"offscreen",-1);
 assert(frame[0]==137 && frame[1]==137 && frame[64002]==137 && frame[64003]==137);
 p="A verylongword and more";i=0;
 while(*p){const char *next=AW_UILine(p,32,line,sizeof(line));assert(next>p && strlen(line)<sizeof(line));p=next;assert(++i<30);}
 p="abc";assert(AW_UILine(p,0,line,sizeof(line))>p);
 /* INFO-BOX-TEXT-CUT-62: the Morrowind name box measures its rows in the small font it is drawn with and wraps at the
  * screen width, so no name is ever cut (the maintainer's door: "Seyda Neen, Census and Excise Office"). For names
  * of every length and word mix, and at screen widths from a handset to a desktop: every character of the name is
  * in the rows, no row is wider than the screen, the box is as wide as its widest row plus the padding. */
 {
  static const char *words[]={"Seyda","Neen,","Census","and","Excise","Office","Vivec,","Foreign","Quarter","Waistworks",
   "Telvanni","Tower,","Sadrith","Mora,","Wolverine","Hall:","Imperial","Chapels","Ald-ruhn,","Manor","Superlongunbrokencompoundname"};
  static const int screens[]={160,240,320,640};
  char rows[AW_FOCUS_ROWS][AW_FOCUS_ROW_CHARS],name[300],kept[300],got[400];int n,box,wide,k,s,length,j,m,pos;
  for(s=0;s<4;s++)for(length=1;length<=21;length++)for(k=0;k<21;k++){
   int max=screens[s]-8,widest=0;
   name[0]=0;for(j=0;j<length;j++){strcat(name,words[(k+j*5)%21]);if(j+1<length)strcat(name," ");}
   n=AW_UIFocusLayout(name,"Weight: 1.5","Value: 30",max,rows,&box);
   assert(n>=3 && n<=AW_FOCUS_ROWS);
   AW_UISmallBegin();
   for(j=0;j<n;j++){int rw=AW_UIWidth(rows[j]);if(rw>widest)widest=rw;assert(rw<=max-10);}
   AW_UISmallEnd();
   assert(box==widest+10 && box<=max);
   /* the name's rows are all but the last two: the same characters as the name, only the wrapping spaces differ */
   pos=0;for(m=0;name[m];m++)if(name[m]!=' ')kept[pos++]=name[m];kept[pos]=0;
   got[0]=0;for(j=0;j<n-2;j++)strcat(got,rows[j]);
   pos=0;for(m=0;got[m];m++)if(got[m]!=' ')got[pos++]=got[m];got[pos]=0;
   assert(!strcmp(got,kept));
   assert(!strcmp(rows[n-2],"Weight: 1.5") && !strcmp(rows[n-1],"Value: 30"));
  }
  /* the named cases from the maintainer's pictures: the Census door ("Seyda Neen, Census and Excise Office", shown as
   * "...Excise Offic") and the Suran apothecary's door ("Suran, Ibarnadad Assimarari: Apothecary", shown as
   * "...: Apoth"), at the real screen width and at a narrow one where they wrap: the whole name, nothing cut */
  {
   static const char *named[]={"Seyda Neen, Census and Excise Office","Suran, Ibarnadad Assimarari: Apothecary"};
   static const int widths[]={312,200,120};int a,b;
   for(a=0;a<2;a++)for(b=0;b<3;b++){
    n=AW_UIFocusLayout(named[a],NULL,NULL,widths[b],rows,&box);
    pos=0;for(m=0;named[a][m];m++)if(named[a][m]!=' ')kept[pos++]=named[a][m];kept[pos]=0;
    got[0]=0;for(j=0;j<n;j++)strcat(got,rows[j]);
    pos=0;for(m=0;got[m];m++)if(got[m]!=' ')got[pos++]=got[m];got[pos]=0;
    assert(n>=1 && !strcmp(got,kept) && box<=widths[b]);
    if(b==0 && a==0)assert(n==1 && !strcmp(rows[0],named[a]));   /* one row at the real width, the whole name */
   }
  }
  /* the maintainer's door at the real screen width: one row, the whole name, the box as wide as that row */
  n=AW_UIFocusLayout("Seyda Neen, Census and Excise Office",NULL,NULL,312,rows,&box);
  AW_UISmallBegin();
  assert(n==1 && !strcmp(rows[0],"Seyda Neen, Census and Excise Office") && box==AW_UIWidth(rows[0])+10);
  AW_UISmallEnd();
  assert(!AW_UIFocusLayout("",NULL,NULL,312,rows,&box));
 }
 /* UI-THIN-BUTTON-62: the house button: a 56 x 14 box has a 1 pixel line (the skin frame's 4 pixel edges left 6 pixels
  * for the text) and the text box is the whole 54 x 12 inside; lit, the line is the bright colour; the pixels outside the
  * box are never touched */
 {
  int ix,iy,iw,ih,x,y,dim=AW_UIColor(120,109,87),lit=AW_UIColor(223,199,144),black=AW_UIColor(0,0,0),ring=0,inside=0;
  assert(AW_UI_THIN_LINE==1 && dim!=lit && dim!=black && lit!=black);
  AW_UIThinInner(100,100,56,14,&ix,&iy,&iw,&ih);assert(ix==101 && iy==101 && iw==54 && ih==12);
  memset(vid.buffer,7,320*200);
  AW_UIThinBox(100,100,56,14,0);
  for(y=98;y<117;y++)for(x=98;x<158;x++){
   int in_box=x>=100 && x<156 && y>=100 && y<114,edge=in_box && (x==100 || x==155 || y==100 || y==113);
   byte p=vid.buffer[y*320+x];
   if(!in_box)assert(p==7);                   /* outside: untouched */
   else if(edge){assert(p==dim);ring++;}      /* the line: 1 pixel wide, 2*56 + 2*12 pixels */
   else{assert(p==black);inside++;}           /* inside: black, the 54 x 12 the text gets */
  }
  assert(ring==2*56+2*12 && inside==iw*ih);
  AW_UIThinBox(100,100,56,14,1);assert(vid.buffer[100*320+100]==lit && vid.buffer[113*320+155]==lit && vid.buffer[101*320+101]==black);
  AW_UIThinBox(100,100,2,2,0);assert(vid.buffer[100*320+100]==lit);   /* too small for a line and a face: left alone */
 }
 AW_UIText(20,20,"A",0);memcpy(before,vid.buffer+20*320+20,3);
 AW_UIBookBegin();AW_UIText(20,20,"A",0);
 assert(vid.buffer[20*320+20]==170 && vid.buffer[20*320+21]==85 && vid.buffer[20*320+22]==0);
 AW_UIBookEnd();AW_UIText(20,20,"A",0);assert(!memcmp(before,vid.buffer+20*320+20,3));
 /* Only the small top box changes; padded rows and repeated reconnect plaques
  * preserve the original pixels after the live buffer has been overwritten. */
 {
  byte padded[64804];int x,y,left,w,h;
  assert(region_parameter && region_parameter->archive && AW_RegionLoadingFrozen());
  AW_RegionLoadingToggle();assert(!AW_RegionLoadingFrozen());AW_RegionLoadingToggle();
  memset(padded,137,sizeof(padded));vid.buffer=padded+2;vid.rowbytes=324;
  for(y=0;y<200;y++)for(x=0;x<320;x++)vid.buffer[y*324+x]=(x+y)%251+1;
  AW_SetNextLoadingStyle(AW_LOADING_FROZEN);AW_BeginLoadingStyle();assert(AW_LoadingFrozen());
  for(y=0;y<200;y++)memset(vid.buffer+y*324,0,320);
  AW_BeginLoadingStyle();AW_UILoading();assert(!AW_UIMenuPalette());
  w=AW_UIWidth("Loading...")+20;h=AW_UIHeight()+8;left=(320-w)/2;
  for(y=0;y<200;y++)for(x=0;x<324;x++){
   if(x>=320)assert(vid.buffer[y*324+x]==137);
   else if(y<6 || y>=6+h || x<left || x>=left+w)assert(vid.buffer[y*324+x]==(x+y)%251+1);
  }
  AW_UILoading();assert(vid.buffer[150*324+88]==(150+88)%251+1);
  assert(padded[0]==137 && padded[64803]==137);
  vid.height=199;AW_UILoading();assert(!AW_LoadingFrozen());
  assert(AW_UIMenuPalette() && !AW_UIMenuPalette()[100]);
  AW_EndLoadingStyle();assert(!AW_LoadingFrozen());
  vid.buffer=NULL;AW_SetNextLoadingStyle(AW_LOADING_FROZEN);AW_BeginLoadingStyle();
  assert(!AW_LoadingFrozen());AW_EndLoadingStyle();
  vid.buffer=frame+2;vid.rowbytes=320;vid.height=200;
 }
 /* Short automatic crossings leave every live framebuffer byte untouched.
  * Reconnect cannot restart the clock; completion cancels a pending display. */
 assert(delay_parameter && delay_parameter->archive && delay_parameter->value==2);
 memset(vid.buffer,137,64000);loading_clock=10;
 AW_SetNextLoadingStyle(AW_LOADING_FROZEN);AW_SetNextLoadingDelay();AW_BeginLoadingStyle();
 assert(AW_LoadingDelayed());AW_UILoading();
 for(i=0;i<64000;i++)assert(vid.buffer[i]==137);
 loading_clock=11.999;assert(!AW_LoadingDelayExpired());AW_BeginLoadingStyle();
 loading_clock=12;assert(AW_LoadingDelayExpired());assert(!AW_LoadingDelayExpired());
 AW_UILoading();assert(vid.buffer[150*320+88]==137);AW_EndLoadingStyle();
 AW_SetNextLoadingStyle(AW_LOADING_BLANK);AW_SetNextLoadingDelay();AW_BeginLoadingStyle();
 assert(AW_LoadingDelayed());AW_EndLoadingStyle();loading_clock=100;
 assert(!AW_LoadingDelayed() && !AW_LoadingDelayExpired());
 AW_BeginLoadingStyle();assert(!AW_LoadingDelayed());AW_EndLoadingStyle();
 delay_parameter->value=0;AW_SetNextLoadingDelay();AW_BeginLoadingStyle();
 assert(!AW_LoadingDelayed());AW_EndLoadingStyle();
 delay_parameter->value=-1;AW_SetNextLoadingDelay();AW_BeginLoadingStyle();
 assert(!AW_LoadingDelayed());AW_EndLoadingStyle();
 delay_parameter->value=1000;AW_SetNextLoadingDelay();AW_BeginLoadingStyle();
 loading_clock=159.999;assert(!AW_LoadingDelayExpired());
 loading_clock=160;assert(AW_LoadingDelayExpired());AW_EndLoadingStyle();delay_parameter->value=2;
 /* Automatic black mode gains its indicator after the deadline while
  * explicit/movie blank mode below retains a completely black palette. */
 memset(vid.buffer,137,64000);loading_clock=200;
 AW_SetNextLoadingStyle(AW_LOADING_BLANK);AW_SetNextLoadingDelay();AW_BeginLoadingStyle();
 AW_UILoading();for(i=0;i<64000;i++)assert(vid.buffer[i]==137);
 loading_clock=202;assert(AW_LoadingDelayExpired());AW_UILoading();
 assert(AW_UIMenuPalette()==host_basepal && vid.buffer[150*320+88]==0);
 for(i=0;i<64000 && !vid.buffer[i];i++){}assert(i<64000);AW_EndLoadingStyle();
 /* Blank is a complete black frame/palette, then normal art resumes. */
 assert(loading_parameter && !strcmp(loading_parameter->string,"normal"));
 AW_SetNextLoadingStyle(AW_LOADING_BLANK);AW_BeginLoadingStyle();AW_BeginLoadingStyle();AW_UILoading();
 for(i=0;i<64000;i++)assert(!vid.buffer[i]);
 assert(AW_UIMenuPalette());for(i=0;i<768;i++)assert(!AW_UIMenuPalette()[i]);
 assert(frame[0]==137 && frame[64003]==137);
 AW_EndLoadingStyle();AW_BeginLoadingStyle();AW_UILoading();assert(!AW_UIMenuPalette());
 for(i=0;i<64000 && !vid.buffer[i];i++){}assert(i<64000);
 AW_EndLoadingStyle();loading_parameter->string="blank";AW_BeginLoadingStyle();AW_UILoading();
 for(i=0;i<64000;i++)assert(!vid.buffer[i]);
 AW_EndLoadingStyle();AW_SetNextLoadingStyle(AW_LOADING_NORMAL);AW_BeginLoadingStyle();assert(!AW_UIMenuPalette());
 /* Movie finish may draw before its queued map command. Even an earlier
  * normal plaque must not leak artwork into that frame. */
 AW_IntroBegin();assert(queued_prison);AW_UILoading();
 for(i=0;i<64000;i++)assert(!vid.buffer[i]);
 for(i=0;i<768;i++)assert(!AW_UIMenuPalette()[i]);
 AW_BeginLoadingStyle();AW_UILoading();
 for(i=0;i<64000;i++)assert(!vid.buffer[i]);
 check_cursor(argc>1 && !strcmp(argv[1],"nocursor")?0:argc>1 && !strcmp(argv[1],"badcursor")?-1:1);
 sprintf(path,"%s/gfx/magic14.awf",directory);unlink(path);sprintf(path,"%s/gfx/book12.awf",directory);unlink(path);
 sprintf(path,"%s/gfx",directory);rmdir(path);rmdir(directory);return 0;
}

double AW_SpeechRemaining(void){return 0;}
int AW_PhotoModeActive(void){return 0;}
