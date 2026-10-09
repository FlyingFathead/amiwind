/* SPDX-License-Identifier: GPL-2.0-or-later
 * A partial-area playtest build (the repository builder's AmiWind "MiniWind"
 * Playtester Build, tools/build.py --miniwind) ships id1/miniwind.txt, written
 * by the builder from the stages it ran (tools/miniwind.py data_file):
 *   AWMW1
 *   town <town table name: where the game starts>
 *   title <notice title>
 *   features <FEATURES ONLY: what the build holds>
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
       !(p=field(p,end,"features",out->features,sizeof(out->features))) || p!=end)goto bad;
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
int AW_MiniwindActive(void){return miniwind.valid;}
const aw_miniwind_t *AW_Miniwind(void){return &miniwind;}
const char *AW_MiniwindAfterLogo(void){return miniwind.valid?"aw_quick_start\n":"aw_main_menu\n";}
