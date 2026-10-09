/* SPDX-License-Identifier: GPL-2.0-or-later
 * Quick test builds: content the builder left out (tools/build.py --exclude,
 * tools/build_exclusions.py). Such an image carries id1/excluded-content.txt:
 *
 *   AWX1
 *   <group> <notice words>
 *   ...
 *
 * A complete image has no such file. The file is read once, on the first
 * question; the places that notice missing content (the intro movie, the
 * music, a door to a left-out room) then print one friendly line instead of a
 * repair message: "This build was made without <notice> (quick test build)."
 */
#include "quakedef.h"

#define EXCLUDED_MAX 12
#define EXCLUDED_NAME 24
#define EXCLUDED_NOTICE 64
static int loaded,count;
static char names[EXCLUDED_MAX][EXCLUDED_NAME];
static char notices[EXCLUDED_MAX][EXCLUDED_NOTICE];
static int told[EXCLUDED_MAX];

static int name_char(int c){return (c>='a'&&c<='z')||(c>='0'&&c<='9')||c=='-';}
/* One "<group> <notice>" line: lower-case group name, printable ASCII notice. */
static int parse_line(const char *line,char *name,char *notice) {
    int i=0,j=0;
    while(name_char((unsigned char)line[i])){if(i>=EXCLUDED_NAME-1)return 0;name[i]=line[i];i++;}
    if(!i || line[i]!=' ')return 0;
    name[i++]=0;
    while(line[i] && line[i]!='\n'){
        if((unsigned char)line[i]<' ' || (unsigned char)line[i]>'~' || j>=EXCLUDED_NOTICE-1)return 0;
        notice[j++]=line[i++];
    }
    notice[j]=0;
    return j>0 && line[i]=='\n' && !line[i+1];
}
static void load(void) {
    FILE *f=NULL;char line[128];int n;
    if(loaded)return;
    loaded=1;count=0;
    n=COM_FOpenFile("excluded-content.txt",&f);
    if(!f)return;
    if(n<5 || n>4096 || !fgets(line,sizeof(line),f) || strcmp(line,"AWX1\n")){fclose(f);return;}
    while(count<EXCLUDED_MAX && fgets(line,sizeof(line),f)){
        if(!parse_line(line,names[count],notices[count])){count=0;break;} /* invalid file: trust none of it */
        told[count]=0;count++;
    }
    fclose(f);
}
static int find(const char *group) {
    int i;load();
    for(i=0;i<count;i++)if(!strcmp(names[i],group))return i;
    return -1;
}
/* Forget the cached file (a new game directory; host tests). */
void AW_ExcludedReset(void){loaded=count=0;}
int AW_ContentExcluded(const char *group){return find(group)>=0;}
const char *AW_ContentExcludedNotice(const char *group){int i=find(group);return i<0?NULL:notices[i];}
/* The console line for a left-out group: once per group for automatic events
 * (always=0), every time for an explicit command (always=1). Returns 1 when the
 * group was left out (the caller skips its own repair message). */
int AW_ContentExcludedSay(const char *group,int always) {
    int i=find(group);
    if(i<0)return 0;
    if(always || !told[i]){told[i]=1;Con_Printf("This build was made without %s (quick test build).\n",notices[i]);}
    return 1;
}
/* At startup: one line naming everything the build left out (nothing in a complete build). */
void AW_ContentExcludedStartup(void) {
    char line[EXCLUDED_MAX*(EXCLUDED_NOTICE+2)+64];int i;
    load();
    if(!count)return;
    strcpy(line,"Quick test build, made without ");
    for(i=0;i<count;i++){
        if(i)strcat(line,i==count-1?" and ":", ");
        strcat(line,notices[i]);
    }
    strcat(line,".\n");
    Con_Printf("%s",line);
}
