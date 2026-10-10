/* SPDX-License-Identifier: GPL-2.0-or-later
 * A partial-area playtest build (the repository builder's AmiWind "MiniWind"
 * Playtester Build, tools/build.py --miniwind) ships id1/miniwind.txt, written
 * by the builder from the stages it ran (tools/miniwind.py data_file):
 *   AWMW1
 *   town <town table name: where the game starts>
 *   title <notice title>
 *   features <FEATURES ONLY: what the build holds>
 *   [start town NAME | start map MAP X Y Z YAW]      a direct start (tools/direct_start.py)
 *   [character RACE|CLASS|BIRTHSIGN|m or f|NAME]     its ready-made character
 *   [header TEXT]                                     the main menu's top line (test builds)
 * Every normal build lacks the file, so nothing here changes a normal game.
 * An invalid file is reported once and ignored. The notice is drawn with the
 * game's own message box (AW_UISubtitle) when the quick start arrives
 * (aw_scene.c), and printed to the console at start-up.
 */
#include "quakedef.h"
#include "aw_miniwind.h"
#include "aw_town.h"

static aw_miniwind_t miniwind;

/* One "key value\n" line into out: 1..size-1 printable ASCII characters.
 * Returns the next line, or NULL. */
static const char *field(const char *p,const char *end,const char *key,char *out,int size)
{
    int n=(int)strlen(key),i=0;
    if(end-p<n+1 || memcmp(p,key,n) || p[n]!=' ')return NULL;
    p+=n+1;
    while(p<end && *p!='\n'){
        if((unsigned char)*p<32 || (unsigned char)*p>126 || i>=size-1)return NULL;
        out[i++]=*p++;
    }
    if(p>=end || !i)return NULL;
    out[i]=0;return p+1;
}
int AW_MiniwindParse(const char *text,int size,aw_miniwind_t *out)
{
    const char *p,*end;int i;
    memset(out,0,sizeof(*out));
    if(!text || size<6 || size>1024 || memcmp(text,"AWMW1\n",6))return 0;
    end=text+size;p=text+6;
    if(!(p=field(p,end,"town",out->town,sizeof(out->town))) ||
       !(p=field(p,end,"title",out->title,sizeof(out->title))) ||
       !(p=field(p,end,"features",out->features,sizeof(out->features))))goto bad;
    if(p<end && end-p>6 && !memcmp(p,"start ",6) && !(p=field(p,end,"start",out->start,sizeof(out->start))))goto bad;
    if(p<end && end-p>10 && !memcmp(p,"character ",10) &&
       !(p=field(p,end,"character",out->character,sizeof(out->character))))goto bad;
    if(p<end && end-p>7 && !memcmp(p,"header ",7) && !(p=field(p,end,"header",out->header,sizeof(out->header))))goto bad;
    if(p<end && end-p>5 && !memcmp(p,"boot ",5) && !(p=field(p,end,"boot",out->boot,sizeof(out->boot))))goto bad;
    /* boot: dbg commands only, each after a ";" or at the start (tools/miniwind.py boot_line). */
    {const char *b=out->boot;
     while(*b){if(strncmp(b,"dbg ",4))goto bad;while(*b && *b!=';')b++;if(*b==';')b++;}}
    if(p!=end)goto bad;
    if(out->start[0]){aw_quick_start_t s;if(!AW_MiniwindStart(out,&s))goto bad;}
    if(out->character[0]){
        char r[32],c[32],b[32],n[32];int f;
        if(!AW_MiniwindCharacter(out,r,c,b,&f,n,32))goto bad;
    }
    for(i=0;out->town[i];i++)
        if(!((out->town[i]>='a' && out->town[i]<='z') || (out->town[i]>='0' && out->town[i]<='9') || out->town[i]=='_'))goto bad;
    if(AW_TownFind(out->town)<0)goto bad;
    out->valid=1;return 1;
bad:
    memset(out,0,sizeof(*out));return 0;
}
void AW_MiniwindInit(void)
{
    FILE *f=NULL;char text[1024];int size;
    memset(&miniwind,0,sizeof(miniwind));
    size=COM_FOpenFile(AW_MINIWIND_FILE,&f);
    if(!f)return;
    if(size<1 || size>(int)sizeof(text) || fread(text,1,size,f)!=(size_t)size || !AW_MiniwindParse(text,size,&miniwind)){
        fclose(f);memset(&miniwind,0,sizeof(miniwind));
        Con_Printf("Invalid " AW_MINIWIND_FILE "; running as a normal build.\n");return;
    }
    fclose(f);
    Con_Printf("%s\n%s\n",miniwind.title,miniwind.features);
}
static int map_name(const char *s){
    int i;
    for(i=0;s[i];i++)if(!((s[i]>='a' && s[i]<='z') || (s[i]>='0' && s[i]<='9') || s[i]=='_' || s[i]=='-') || i>=31)return 0;
    return i>0;
}
int AW_MiniwindStart(const aw_miniwind_t *m,aw_quick_start_t *out)
{
    char kind[8],name[40],extra;int n;
    memset(out,0,sizeof(*out));
    if(!m || !m->start[0])return 0;
    n=Q_sscanf(m->start,"%7s %39s %f %f %f %f %c",kind,name,&out->point[0],&out->point[1],&out->point[2],&out->yaw,&extra);
    if(!strcmp(kind,"town") && n==2 && map_name(name) && AW_TownFind(name)>=0){out->kind=1;strcpy(out->map,name);return 1;}
    if(!strcmp(kind,"map") && n==6 && map_name(name) &&
       fabs(out->point[0])<65536 && fabs(out->point[1])<65536 && fabs(out->point[2])<65536 &&
       out->yaw>=0 && out->yaw<360){out->kind=2;strcpy(out->map,name);return 1;}
    memset(out,0,sizeof(*out));return 0;
}
int AW_MiniwindCharacter(const aw_miniwind_t *m,char *race,char *clas,char *birth,int *female,char *name,int size)
{
    char *field[5];char copy[AW_MINIWIND_CHARACTER];int i,count=0;char *p;
    if(!m || !m->character[0] || strlen(m->character)>=sizeof(copy))return 0;
    strcpy(copy,m->character);field[count++]=copy;
    for(p=copy;*p;p++)if(*p=='|'){*p=0;if(count==5)return 0;field[count++]=p+1;}
    if(count!=5)return 0;
    for(i=0;i<5;i++)if(!field[i][0] || (int)strlen(field[i])>=size)return 0;
    if(strcmp(field[3],"m") && strcmp(field[3],"f"))return 0;
    strcpy(race,field[0]);strcpy(clas,field[1]);strcpy(birth,field[2]);*female=field[3][0]=='f';strcpy(name,field[4]);
    return 1;
}
int AW_MiniwindActive(void){return miniwind.valid;}
const aw_miniwind_t *AW_Miniwind(void){return &miniwind;}
const char *AW_MiniwindAfterLogo(void){return miniwind.valid?"aw_quick_start\n":"aw_main_menu\n";}
/* A test build's header line (id1/miniwind.txt "header", e.g. "MINIWIND TEST UNIT:
 * <description>") at the top of the title screen: word-wrapped to the width, at most
 * two lines; a longer text ends in "..." on the second line. Normal builds: nothing. */
int AW_MenuHeaderLines(const char *text,int width,char lines[2][AW_MINIWIND_HEADER]){
    int n=0,len,cut;const char *p=text;char trial[AW_MINIWIND_HEADER];
    lines[0][0]=lines[1][0]=0;
    while(*p==' ')p++;
    while(*p && n<2){
        len=(int)strlen(p);if(len>AW_MINIWIND_HEADER-1)len=AW_MINIWIND_HEADER-1;
        memcpy(trial,p,len);trial[len]=0;
        if(AW_UIWidth(trial)<=width){strcpy(lines[n++],trial);p+=len;break;}
        if(n==1){
            /* The last line: as many characters as fit with "...". */
            for(cut=len>AW_MINIWIND_HEADER-4?AW_MINIWIND_HEADER-4:len;cut>0;cut--){memcpy(trial,p,cut);strcpy(trial+cut,"...");if(AW_UIWidth(trial)<=width)break;}
            strcpy(lines[n++],trial);break;
        }
        for(cut=len;cut>0;cut--){
            if(p[cut]!=' ' && p[cut]!=0)continue;
            memcpy(trial,p,cut);trial[cut]=0;
            if(AW_UIWidth(trial)<=width)break;
        }
        if(cut<=0){for(cut=len;cut>1;cut--){memcpy(trial,p,cut);trial[cut]=0;if(AW_UIWidth(trial)<=width)break;}}
        memcpy(lines[n],p,cut);lines[n][cut]=0;n++;p+=cut;
        while(*p==' ')p++;
    }
    return n;
}
