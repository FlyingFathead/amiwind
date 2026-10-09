/* SPDX-License-Identifier: GPL-2.0-or-later
 * Space-separated diagnostics and an opaque palette-based console backdrop.
 * Background: no disk reads, alpha blending or extra framebuffer.
 * Explicit font changes read one atlas from disk.
 */
#include "quakedef.h"
static cvar_t colour={"_aw_console_colour","255",true};
extern int scr_copyeverything;
extern byte *draw_chars;
/* Command/help metadata belongs on disk, not in a permanently resident table.
 * Read on submitted dbg commands/help only; opening/typing does no catalogue I/O.
 * Handler code and Quake's small registered-command list remain resident.
 * Honor COM_FOpenFile's member size: FILE may point inside a larger PAK. */
#define DEBUG_LINE 384
#define DEBUG_BYTES 65536
extern int con_linewidth;
typedef struct {char *group,*words,*command,*arguments;} route_t;
static int catalogue_line(FILE *f,int *left,char *line) {
    int n=0,c;
    if(!*left)return 0;
    while(*left>0){
        c=fgetc(f);--*left;
        if(c==EOF)return -1;
        if(c=='\n'){line[n]=0;return 1;}
        if(c=='\r')continue;
        if(c<32 || c>126 || n>=DEBUG_LINE-1)return -1;
        line[n++]=(char)c;
    }
    line[n]=0;return 1;
}
static FILE *catalogue_open(int *left,char *line) {
    FILE *f=NULL;*left=COM_FOpenFile("debug-commands.txt",&f);
    if(!f || *left<6 || *left>DEBUG_BYTES ||
       catalogue_line(f,left,line)!=1 || strcmp(line,"AWDC1")){
        if(f)fclose(f);
        return NULL;
    }
    return f;
}
static int catalogue_route(char *line,route_t *r) {
    char *p,*fields[4];int i,n;
    fields[0]=line;
    for(i=1;i<4;i++){
        p=strchr(fields[i-1],'|');if(!p)return 0;
        *p=0;fields[i]=p+1;
    }
    if(strchr(fields[3],'|') || !*fields[0] || strlen(fields[0])>31 ||
       !*fields[1] || strlen(fields[1])>63 || !*fields[2] || strlen(fields[2])>63)return 0;
    /* Catalogue command text cannot inject separators, quotes or new commands. */
    for(i=1;i<=2;i++){
        n=(int)strlen(fields[i]);
        for(p=fields[i];*p;p++)if(!((*p>='a'&&*p<='z') ||
            (*p>='0'&&*p<='9') || *p=='_' || (i==1 && *p==' ')))return 0;
        if(fields[i][0]==' ' || fields[i][n-1]==' ' || strstr(fields[i],"  "))return 0;
    }
    r->group=fields[0];r->words=fields[1];r->command=fields[2];r->arguments=fields[3];
    return 1;
}
static int route_match(char *words,int argc,char **argv,int start) {
    int j=start,n;
    while(*words && j<argc){
        n=0;while(words[n] && words[n]!=' ')n++;
        if((int)strlen(argv[j])!=n || Q_strncasecmp(words,argv[j],n))return 0;
        words+=n;if(*words==' ')words++;j++;
    }
    return *words?0:j;
}
static int route_format(route_t *r,int argc,char **argv,int j,char *out,int capacity) {
    int used,n,k,setting;char *token;
    if(!strcmp(r->command,"aw_teleport") && argc-j>3)return 0;   /* dbg tp X Y [Z] */
    if(!strcmp(r->command,"aw_shroomtracker") && argc!=j)return 0;
    if(!strcmp(r->command,"aw_shroompicker")){
        if(argc-j>1)return 0;
        if(argc>j && strcmp(argv[j],"list")){
            n=0;
            for(token=argv[j];*token;token++){
                if(*token<'0'||*token>'9' || n>10)return 0;
                n=n*10+*token-'0';
            }
            if(n<1 || n>10)return 0;
        }
    }
    used=(int)strlen(r->command);if(used+2>capacity)return 0;
    strcpy(out,r->command);
    setting=Cvar_FindVar(r->command)!=NULL;
    for(;j<argc;j++){
        token=argv[j];
        /* A route straight onto a setting gets 1/0 for the toggle words the
         * help promises; Quake would read "on" as 0 (DBG-TOGGLE-WORDS-31). */
        if(setting && argc-j==1){
            if(!Q_strcasecmp(token,"on") || !Q_strcasecmp(token,"true") || !Q_strcasecmp(token,"yes"))token="1";
            else if(!Q_strcasecmp(token,"off") || !Q_strcasecmp(token,"false") || !Q_strcasecmp(token,"no"))token="0";
        }
        n=(int)strlen(token);
        if(!n || used+n+3>capacity)return 0;
        for(k=0;k<n;k++)if(!((token[k]>='a'&&token[k]<='z') ||
            (token[k]>='A'&&token[k]<='Z') || (token[k]>='0'&&token[k]<='9') ||
            token[k]=='-' || token[k]=='+' || token[k]=='.' || token[k]=='_'))return 0;
        out[used++]=' ';memcpy(out+used,token,n);used+=n;
    }
    out[used++]='\n';out[used]=0;return 1;
}
/* Return -1 for missing/invalid catalogue, 0 for bad command, 1 translated,
 * 2 help. Do not queue anything until the complete bounded scan validates. */
int AW_DebugTranslate(int argc,char **argv,char *out,int capacity) {
    int start=1,left,status,j,best=0,valid=0;FILE *f;route_t r;
    char line[DEBUG_LINE],candidate[160];
    if(capacity>0)out[0]=0;
    if(argc<1)return 0;
    if(!Q_strcasecmp(argv[0],"amiwind")){
        if(argc<2 || Q_strcasecmp(argv[1],"debug"))return 0;
        start=2;
    }else if(Q_strcasecmp(argv[0],"debug") && Q_strcasecmp(argv[0],"dbg"))return 0;
    if(argc==start || (argc==start+1 && !Q_strcasecmp(argv[start],"help")))return 2;
    f=catalogue_open(&left,line);if(!f)return -1;
    while((status=catalogue_line(f,&left,line))>0){
        if(!*line || *line=='#')continue;
        if(!catalogue_route(line,&r)){status=-1;break;}
        j=route_match(r.words,argc,argv,start);
        if(!j || j<best)continue;
        if(j==best){status=-1;break;}
        best=j;valid=route_format(&r,argc,argv,j,candidate,sizeof(candidate));
    }
    fclose(f);
    if(status<0)return -1;
    if(!valid || (int)strlen(candidate)+1>capacity)return 0;
    strcpy(out,candidate);return 1;
}
/* A --no-npc-gallery image lists the gallery's commands as absent. The marker
 * is checked once per listing (dbg help, dbg help <word>), never on dispatch.
 * dbg combattest enters the Vivec Arena now, which needs no gallery (its
 * floor test, dbg combattest gallery, explains itself when used). */
static const char *availability(int omitted,const route_t *r) {
    return omitted && !strcmp(r->command,"aw_charplane")?" (not in this build)":"";
}
static void catalogue_error(void) {
    Con_Printf("Debug catalogue missing/invalid: debug-commands.txt\n");
    Con_Printf("Restore the matching build's file; legacy command names still work.\n");
}
static void help(void) {
    FILE *f;route_t r;int left,status,width=con_linewidth,omitted;
    char line[DEBUG_LINE],group[32],separator[129];
    f=catalogue_open(&left,line);if(!f){catalogue_error();return;}
    omitted=AW_GalleryOmitted();
    if(width<1)width=38;
    if(width>128)width=128;
    memset(separator,'-',width);separator[width]=0;group[0]=0;
    Con_Printf("AmiWind debug commands (PageUp scrolls)\n");
    Con_Printf("Prefix: debug / dbg / amiwind debug\n");
    while((status=catalogue_line(f,&left,line))>0){
        if(!*line || *line=='#')continue;
        if(!catalogue_route(line,&r)){status=-1;break;}
        if(strcmp(group,r.group)){
            strcpy(group,r.group);Con_Printf("\n%s\n%s\n",group,separator);
        }
        Con_Printf(" %s %s%s\n",r.words,r.arguments,availability(omitted,&r));
    }
    fclose(f);if(status<0){catalogue_error();return;}
    Con_Printf(" help: this list; old names still work\n");
    Con_Printf("Toggle values: on/off true/false 1/0\n");
    Con_Printf("Noclip: look+WASD, E/Q vertical, Shift\n");
}
/* dbg help <word>: only the catalogue lines whose command starts with that word,
 * streamed from the disk file like the full list. */
static void help_for(char *word) {
    FILE *f;route_t r;int left,status,n=strlen(word),shown=0,omitted;char line[DEBUG_LINE];
    f=catalogue_open(&left,line);if(!f){catalogue_error();return;}
    omitted=AW_GalleryOmitted();
    while((status=catalogue_line(f,&left,line))>0){
        if(!*line || *line=='#')continue;
        if(!catalogue_route(line,&r)){status=-1;break;}
        if(Q_strncasecmp(r.words,word,n) || (r.words[n] && r.words[n]!=' '))continue;
        Con_Printf(" dbg %s %s%s\n",r.words,r.arguments,availability(omitted,&r));shown++;
    }
    fclose(f);if(status<0){catalogue_error();return;}
    if(!shown)Con_Printf("No debug command starts with \"%s\"; use debug help\n",word);
}
static void dispatch(void) {
    char *argv[12],out[160];int i,n=Cmd_Argc(),r;
    if(n>12){Con_Printf("Too many arguments; use debug help\n");return;}
    for(i=0;i<n;i++)argv[i]=Cmd_Argv(i);
    if(n==3 && Q_strcasecmp(argv[0],"amiwind") && !Q_strcasecmp(argv[1],"help")){help_for(argv[2]);return;}
    r=AW_DebugTranslate(n,argv,out,sizeof(out));
    if(r<0)catalogue_error();else if(r==2)help();else if(r==1)Cbuf_InsertText(out);
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
    if(lines<0)return;
    if(lines>vid.conheight)lines=vid.conheight;
    if(ink<0||ink>255)ink=255;
    for(y=0;y<lines;y++)
        memset(vid.conbuffer+y*vid.conrowbytes,ink,vid.conwidth);
    scr_copyeverything=1;
}
static void heap_audit(void){AW_HeapAuditReport(sv.worldmodel?sv.worldmodel->name:sv.name);}
void AW_ConsoleInit(void) {
    Cvar_RegisterVariable(&colour);
    Cmd_AddCommand("aw_heap_audit",heap_audit);
    Cmd_AddCommand("debug",dispatch);Cmd_AddCommand("dbg",dispatch);
    Cmd_AddCommand("amiwind",dispatch);
    Cmd_AddCommand("aw_console_color",set_colour);
    Cmd_AddCommand("aw_console_font",set_font);
    Cmd_AddCommand("aw_console_size",set_size);
}
