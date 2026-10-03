/* SPDX-License-Identifier: GPL-2.0-or-later
 * AWV1: desktop-decoded indexed video and mono PCM. No Bink decoder on Amiga.
 * 160x100 or 320x200 at 10 fps; one frame and a 4 KiB audio cache.
 */
#include "quakedef.h"
#include "sound.h"
#define MAX_PIXELS 64000
#define RATE 11025
#define DATA_START 800
extern int soundtime;
typedef struct {byte palette[768],frame[MAX_PIXELS];signed char pcm[4096];} movie_buffers_t;
static movie_buffers_t *buffers;
/* A single optional host-rasterized opening quote. No text/owned pixels in source. */
static byte *opening_card;
static long card_first,card_end;
static cvar_t intro_text_overlay={"aw_intro_text_overlay","1",true};
static void playvid(void);
void AW_MovieInit(void){Cvar_RegisterVariable(&intro_text_overlay);}
static FILE *video,*audio;
static long frames,samples,audio_start,clock_start,shown,pcm_start,pcm_count;
static int broken,branding,width,height,pixels;
static int debug_return_dest,debug_music_paused;
static long pictures,dropped;
static double started;
static unsigned long be32(byte *p){return ((unsigned long)p[0]<<24)|((unsigned long)p[1]<<16)|((unsigned long)p[2]<<8)|p[3];}
static void close_movie(void){
    if(video)fclose(video);if(audio)fclose(audio);video=audio=NULL;
    if(buffers)free(buffers);buffers=NULL;
    if(opening_card)free(opening_card);
    opening_card=NULL;
}
int AW_MovieActive(void){return buffers!=NULL;}
int AW_MovieDebugActive(void){return buffers!=NULL && branding==2;}
static int card_visible(void){return buffers && opening_card && intro_text_overlay.value && shown>=card_first && shown<card_end;}
byte *AW_MoviePalette(void){return card_visible()?opening_card:(buffers?buffers->palette:NULL);}
static void load_opening_card(void){
    FILE *f=NULL;byte h[16];long n;
    n=COM_FOpenFile("intro/opening.awt",&f);if(!f)return;
    if(n!=16+768+MAX_PIXELS || fread(h,1,16,f)!=16 || memcmp(h,"AWT1",4))goto done;
    card_first=be32(h+4);card_end=be32(h+8);
    if(card_first<0 || card_end<=card_first || card_end>frames || be32(h+12))goto done;
    opening_card=malloc(768+MAX_PIXELS);
    if(opening_card && fread(opening_card,1,768+MAX_PIXELS,f)!=768+MAX_PIXELS){free(opening_card);opening_card=NULL;}
done:
    fclose(f);
}
static void finish(const char *why){
    Con_Printf("Movie profile: %ld ms, %ld pictures, %ld skipped pictures.\n",
        (long)((Sys_FloatTime()-started)*1000),pictures,dropped);
    close_movie();
    if(branding==2){
        IN_AWClearButtons();Key_ClearStates();
        key_dest=debug_return_dest;
        CDAudio_Resume();
        V_UpdatePalette();
        Con_Printf("Debug video ended (%s); returned to the current scene.\n",why);
        return;
    }
    if(!branding)S_StopAllSounds(true);IN_AWClearButtons();
    if(branding==1)Cbuf_AddText("aw_main_menu\n");else AW_IntroBegin();
    /* Con_Printf may refresh a disconnected client's screen. Select the
     * intro loading style before that refresh can request normal artwork. */
    Con_Printf("Intro movie: %s.\n",why);
}
static int start_movie(char *path,int brand){
    byte h[32];long size,audio_size,expected;int i;
    close_movie();
    branding=brand;size=COM_FOpenFile(path,&video);
    if(!video){Con_Printf("Video not found; skipping optional movie.\n");return 0;}
    if(fread(h,1,32,video)!=32 || memcmp(h,"AWV1",4) ||
       h[8] || h[9]!=10 || h[10]!=43 || h[11]!=17)goto invalid;
    width=h[4]*256+h[5];height=h[6]*256+h[7];
    if(!((width==160 && height==100) || (width==320 && height==200)))goto invalid;
    pixels=width*height;
    for(i=20;i<32;i++)if(h[i])goto invalid;
    frames=be32(h+12);samples=be32(h+16);
    if(frames<1 || frames>18000 || samples!=(frames*RATE+9)/10)goto invalid;
    expected=DATA_START+frames*pixels+samples;
    if(size!=expected || !shm || shm->speed!=RATE)goto invalid;
    buffers=malloc(sizeof(*buffers));if(!buffers)goto invalid;
    if(fread(buffers->palette,1,768,video)!=768 || fread(buffers->frame,1,pixels,video)!=pixels)goto invalid;
    audio_size=COM_FOpenFile(path,&audio);
    audio_start=DATA_START+frames*pixels;
    if(!audio || audio_size!=expected || fseek(audio,audio_start,SEEK_SET))goto invalid;
    if(branding!=2)S_StopAllSounds(true);
    if(branding==1)AW_MusicTitle();
    else if(branding==0){CDAudio_Pause();load_opening_card();}
    else {debug_music_paused=0;CDAudio_Pause();}
    clock_start=paintedtime;
    shown=0;pcm_start=pcm_count=0;broken=0;pictures=1;dropped=0;started=Sys_FloatTime();
    Con_Printf("Video: %ld frames; %s skips.\n",frames,branding==1?"Space/Enter/Esc":"Esc");return 1;
invalid:
    close_movie();Con_Printf("Video invalid or unavailable; skipping optional movie.\n");return 0;
}
int AW_MovieStart(void){return start_movie("intro/mw_intro.awv",0);}
void AW_MovieStartup(void){
    IN_AWClearButtons();key_dest=key_game;
    if(!start_movie("intro/amiwind.awv",1))Cbuf_AddText("aw_main_menu\n");
}
static int catalogue_path(const char *request,char *out,int capacity){
    FILE *f=NULL;char line[128],name[32],file[64],expected[64];int size,id,n,previous=0,wanted=-1,i,numeric=1;
    if(!request || !*request)return 0;
    for(i=0;request[i];i++)if(request[i]<'0'||request[i]>'9'){numeric=0;break;}
    if(numeric){wanted=0;for(i=0;request[i];i++){wanted=wanted*10+request[i]-'0';if(wanted>17)return 0;}if(wanted<1)return 0;}
    size=COM_FOpenFile("intro/videos.awl",&f);
    if(!f || size<6 || size>4096){if(f)fclose(f);return 0;}
    if(!fgets(line,sizeof(line),f) || strcmp(line,"AWVC1\n")){fclose(f);return 0;}
    while(fgets(line,sizeof(line),f)){
        n=-1;
        if(sscanf(line,"%d %31s %63s%n",&id,name,file,&n)!=3 || n<0 || line[n]!='\n' || line[n+1])goto bad;
        if(id<1 || id>17 || id<=previous)goto bad;
        for(i=0;name[i];i++)if(!((name[i]>='a'&&name[i]<='z')||(name[i]>='0'&&name[i]<='9')||name[i]=='_'))goto bad;
        if(id==15)strcpy(expected,"intro/mw_intro.awv");
        else {strcpy(expected,"intro/video/00.awv");expected[12]='0'+id/10;expected[13]='0'+id%10;}
        if(strcmp(file,expected))goto bad;
        if((numeric && id==wanted) || (!numeric && !Q_strcasecmp(request,name))){
            if(strlen(file)+1>capacity)goto bad;strcpy(out,file);
        }
        previous=id;
    }
    if(ferror(f))goto bad;
    fclose(f);return out[0]!=0;
bad:
    fclose(f);out[0]=0;return 0;
}
static void playvid(void){
    char path[64];
    if(Cmd_Argc()!=2){Con_Printf("Usage: dbg playvid <1..17 / 01..17 / catalogue name>\n");return;}
    path[0]=0;
    if(!catalogue_path(Cmd_Argv(1),path,sizeof(path))){Con_Printf("Video is absent or the optional catalogue is invalid.\n");return;}
    debug_return_dest=key_dest;
    if(!start_movie(path,2))return;
    IN_AWClearButtons();Key_ClearStates();key_dest=key_game;
}
void AW_MovieUpdate(void){
    long position,frame;if(!buffers)return;
    if(broken){finish("read error");return;}
    position=soundtime-clock_start;if(position<0)position=0;
    if(position>=samples){finish("complete");return;}
    frame=position*10/RATE;
    if(frame==shown)return;
    if(frame>=frames)frame=frames-1;
    /* Drop late pictures without delaying the narration. Seek only on skips. */
    if((frame!=shown+1 && fseek(video,DATA_START+frame*pixels,SEEK_SET)) ||
       fread(buffers->frame,1,pixels,video)!=pixels){finish("video read error");return;}
    if(frame>shown+1)dropped+=frame-shown-1;pictures++;shown=frame;
}
void AW_MoviePaint(portable_samplepair_t *dst,int count,int first_sample){
    long position=first_sample-clock_start,take;int i,gain=(int)(volume.value*256);
    if(!buffers || broken)return;
    if(branding==1){AW_MusicPaint(dst,count);return;}
    while(count>0 && position<samples){
        if(position<0){dst++;position++;count--;continue;}
        if(position<pcm_start || position>=pcm_start+pcm_count){
            pcm_start=position;pcm_count=samples-position;if(pcm_count>4096)pcm_count=4096;
            if(fseek(audio,audio_start+position,SEEK_SET) || fread(buffers->pcm,1,pcm_count,audio)!=(size_t)pcm_count){broken=1;return;}
        }
        take=pcm_start+pcm_count-position;if(take>count)take=count;
        for(i=0;i<take;i++){int value=buffers->pcm[position-pcm_start+i]*gain;dst[i].left+=value;dst[i].right+=value;}
        position+=take;dst+=take;count-=take;
    }
}
void AW_MovieDraw(void){
    int x,y;byte *row,*src;
    if(!buffers || !vid.buffer || vid.width!=320 || vid.height!=200)return;
    for(y=0;y<200;y++){
        row=vid.buffer+y*vid.rowbytes;
        if(card_visible()){memcpy(row,opening_card+768+y*320,320);continue;}
        src=buffers->frame+(y*height/200)*width;
        if(width==320)memcpy(row,src,320);
        else for(x=0;x<160;x++)row[x*2]=row[x*2+1]=src[x];
    }
}
int AW_MovieKey(int key,int down){
    if(!buffers)return 0;
    if(down && (key==K_ESCAPE || (branding==1 && (key==K_ENTER || key==K_SPACE))))finish("skipped");
    return 1;
}
