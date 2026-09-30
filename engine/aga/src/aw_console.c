/* SPDX-License-Identifier: GPL-2.0-or-later
 * Space-separated diagnostics and an opaque palette-based console backdrop.
 * Background: no disk reads, alpha blending or extra framebuffer.
 * Explicit font changes read one atlas from disk.
 */
#include "quakedef.h"
static cvar_t colour={"_aw_console_colour","255",true};
extern int scr_copyeverything;
extern byte *draw_chars;
typedef struct {char *words,*command,*arguments;} route_t;
static route_t routes[]={
    {"gallery","aw_charplane","[number/name/ID; next/previous/body/browse/help/exit]"},
    {"aw charplane","aw_charplane","[number/name/ID; next/previous/body/exit]"},
    {"modelgallery","aw_charplane","[number/name/ID]"},
    {"npcgallery","aw_charplane","[number/name/ID]"},
    {"reset location","amiwind_debug_reset_location","0"},
    {"ui font","aw_ui_select","16/14/12/fallback"},
    {"ui ink","aw_ui_ink","original/readable"},
    {"timeofday","aw_timeofday","[0..23.999 or morning/night/midday/day/evening/sunset/sunrise]"},
    {"ui preview","aw_ui_preview",""},
    {"ui layout","aw_dialogue_layout","1 legacy / 2 full width / 3 padded content (default)"},
    {"ui dialogue","aw_dialogue_method","1/2/3/4 (default 3)"},
    {"ui labels","aw_label_style","below/topright/hudleft"},
    {"ui targetplace","aw_target_place","below/topright/hudleft"},
    {"ui targetnames","aw_target_names_set","on/off (after creation)"},
    {"show fps","amiwind_debug_showfps","[on/off]"},
    {"coords","amiwind_debug_coords","on/off"},
    {"fps","amiwind_debug_fps","on/off"},
    {"all","amiwind_show_debug","on/off"},
    {"overlay","amiwind_show_debug","on/off true/false 1/0"},
    {"input trace","aw_input_trace","on/off (raw keys and mouse events)"},
    {"door sounds","aw_door_sounds","on/off (default on)"},
    {"hud type","aw_debug_hud_type","1 original / 2 compact (default)"},
    {"render order","aw_surface_order","1 legacy / 2 mesh intersections (default)"},
    {"aw hors","aw_debug_hors","0 (new Hors, Nord / Barbarian / Steed, after Census)"},
    {"hud","amiwind_show_debug","on/off true/false 1/0 (overlay alias)"},
    {"showram","amiwind_debug_showram","on/off"},
    {"sealevel","amiwind_debug_sealevel","on/off"},
    {"scene change","aw_scene_menu","(scene picker)"},
    {"scene","aw_scene","ship/town/balmora/<map name>"},
    {"tp menu","aw_scene_menu","(teleport picker)"},
    {"tp","aw_teleport","[balmora/seydaneen/prisonship/<map name>; no argument opens menu]"},
    {"eyeheight","aw_eyeheight","[offset above player origin]"},
    {"dimensions","aw_dimensions",""},
    {"pos","aw_pos",""},{"blockers","aw_blockers",""},
    {"npcs","aw_npcs",""},{"hands","aw_hands",""},
    {"npcfloors","aw_npc_floors","(read-only ground-contact report)"},
    {"view","aw_view","x y z yaw pitch"},
    {"probe","aw_probe","(slow floor audit)"},
    {"noclip","noclip",""},{"recover","aw_recover",""},
    {"fog distance","aw_fog_distance","[128..1400 local units; default 540]"},
    {"draw distance","aw_fog_distance","[128..1400 local units; default 540]"},
    {"drawdistance","aw_fog_distance","[128..1400 local units; default 540]"},
    {"fog","aw_fog","0/1"},{"cull","aw_cull","0/1"},
    {"console bg color","aw_console_color","black/blue/gray or R G B"},
    {"font","aw_console_font","readable/retro"},
    {"console font","aw_console_size","small/normal"},
    {NULL,NULL,NULL}
};

/* Validated tokens only; never splice arbitrary quoted command text. */
int AW_DebugTranslate(int argc,char **argv,char *out,int capacity) {
    int start=1,i,j,n,k,used;char *word,*token;
    if(argc<1)return 0;
    if(!Q_strcasecmp(argv[0],"amiwind")) {
        if(argc<2 || Q_strcasecmp(argv[1],"debug"))return 0;
        start=2;
    } else if(Q_strcasecmp(argv[0],"debug") && Q_strcasecmp(argv[0],"dbg"))return 0;
    if(argc==start || (argc==start+1 && !Q_strcasecmp(argv[start],"help")))return 2;
    for(i=0;routes[i].words;i++) {
        word=routes[i].words;j=start;
        while(*word && j<argc) {
            n=0;while(word[n] && word[n]!=' ')n++;
            if((int)strlen(argv[j])!=n || Q_strncasecmp(word,argv[j],n))break;
            word+=n;if(*word==' ')word++;j++;
        }
        if(*word)continue;
        used=(int)strlen(routes[i].command);
        if(used+2>capacity)return 0;
        strcpy(out,routes[i].command);
        for(;j<argc;j++) {
            token=argv[j];n=(int)strlen(token);
            if(!n || used+n+3>capacity)return 0;
            for(k=0;k<n;k++)if(!((token[k]>='a'&&token[k]<='z') ||
                (token[k]>='A'&&token[k]<='Z') || (token[k]>='0'&&token[k]<='9') ||
                token[k]=='-' || token[k]=='+' || token[k]=='.' || token[k]=='_'))return 0;
            out[used++]=' ';memcpy(out+used,token,n);used+=n;
        }
        out[used++]='\n';out[used]=0;return 1;
    }
    return 0;
}
static void help(void) {
    int i;Con_Printf("AmiWind debug commands (PageUp scrolls)\n");
    Con_Printf("Prefix: debug / dbg / amiwind debug\n");
    for(i=0;routes[i].words;i++)Con_Printf(" %s %s\n",routes[i].words,routes[i].arguments);
    Con_Printf(" help: this list; old names still work\n");
    Con_Printf("Toggle values: on/off true/false 1/0\n");
    Con_Printf("Noclip: look+WASD, E/Q vertical, Shift\n");
}
static void dispatch(void) {
    char *argv[12],out[160];int i,n=Cmd_Argc(),r;
    if(n>12){Con_Printf("Too many arguments; use debug help\n");return;}
    for(i=0;i<n;i++)argv[i]=Cmd_Argv(i);
    r=AW_DebugTranslate(n,argv,out,sizeof(out));
    if(r==2)help();else if(r==1)Cbuf_InsertText(out);
    else Con_Printf("Unknown debug command; use debug help\n");
}
static int integer(char *s,int maximum,int *out) {
    int n=0;if(!*s)return 0;
    while(*s){if(*s<'0'||*s>'9')return 0;n=n*10+*s++-'0';if(n>maximum)return 0;}
    *out=n;return 1;
}
static void set_colour(void) {
    int rgb[3],i,best=255;long distance,best_distance=0x7fffffff;char *s=Cmd_Argv(1);
    if(Cmd_Argc()==1) {
        i=(int)colour.value;if(i<0||i>255)i=255;
        Con_Printf("console bg palette %ld / RGB %ld %ld %ld\n",(long)i,
            (long)host_basepal[i*3],(long)host_basepal[i*3+1],(long)host_basepal[i*3+2]);return;
    }
    if(Cmd_Argc()==2 && !Q_strcasecmp(s,"black"))rgb[0]=rgb[1]=rgb[2]=0;
    else if(Cmd_Argc()==2 && !Q_strcasecmp(s,"blue")){rgb[0]=16;rgb[1]=24;rgb[2]=48;}
    else if(Cmd_Argc()==2 && (!Q_strcasecmp(s,"gray")||!Q_strcasecmp(s,"grey")))rgb[0]=rgb[1]=rgb[2]=48;
    else if(Cmd_Argc()==4 && integer(Cmd_Argv(1),255,&rgb[0]) &&
        integer(Cmd_Argv(2),255,&rgb[1]) && integer(Cmd_Argv(3),255,&rgb[2])){}
    else {Con_Printf("Color: black/blue/gray, or R G B (0..255)\n");return;}
    for(i=0;i<256;i++) {
        long r=host_basepal[i*3]-rgb[0],g=host_basepal[i*3+1]-rgb[1],b=host_basepal[i*3+2]-rgb[2];
        distance=r*r+g*g+b*b;if(distance<best_distance){best=i;best_distance=distance;}
    }
    Cvar_SetValue(colour.name,best);
    Con_Printf("Console color uses nearest palette entry.\n");
}
static void set_size(void) {
    char *s=Cmd_Argv(1);
    if(Cmd_Argc()!=2 || (Q_strcasecmp(s,"small") && Q_strcasecmp(s,"normal"))) {
        Con_Printf("Usage: debug console font small/normal\n");return;
    }
    AW_ConsoleSetSmall(!Q_strcasecmp(s,"small"));
    Con_CheckResize();scr_copyeverything=1;
    Con_Printf("Console font: %s\n",s);
}
static void set_font(void) {
    byte data[16384];char *path,*name=Cmd_Argv(1);FILE *f=NULL;int size;
    if(Cmd_Argc()!=2 || (Q_strcasecmp(name,"readable") && Q_strcasecmp(name,"retro"))) {
        Con_Printf("Usage: debug font readable/retro (all UI text)\n");return;
    }
    path=!Q_strcasecmp(name,"retro")?"gfx/font-retro.lmp":"gfx/font-readable.lmp";
    size=COM_FOpenFile(path,&f);
    if(size!=sizeof(data) || !f){if(f)fclose(f);Con_Printf("Font missing or wrong size.\n");return;}
    if(fread(data,1,sizeof(data),f)!=sizeof(data)){fclose(f);Con_Printf("Font read failed.\n");return;}
    fclose(f);memcpy(draw_chars,data,sizeof(data));
    scr_copyeverything=1;Con_Printf("Font: %s\n",name);
}
void AW_ConsoleBackground(int lines) {
    int y,ink=(int)colour.value;
    if(lines<0)return;if(lines>vid.conheight)lines=vid.conheight;
    if(ink<0||ink>255)ink=255;
    for(y=0;y<lines;y++)
        memset(vid.conbuffer+y*vid.conrowbytes,ink,vid.conwidth);
    scr_copyeverything=1;
}
void AW_ConsoleInit(void) {
    Cvar_RegisterVariable(&colour);
    Cmd_AddCommand("debug",dispatch);Cmd_AddCommand("dbg",dispatch);
    Cmd_AddCommand("amiwind",dispatch);
    Cmd_AddCommand("aw_console_color",set_colour);
    Cmd_AddCommand("aw_console_font",set_font);
    Cmd_AddCommand("aw_console_size",set_size);
}
