/* SPDX-License-Identifier: GPL-2.0-or-later
 * Original AmiWind MWA1 player. Two bounded PCM blocks, independent shuffled
 * groups and Previous/Next history. Owned audio remains outside the source tree.
 */
#include "quakedef.h"
#include "sound.h"
#define FRAMES 8192
#define BYTES (FRAMES*2)
#define HISTORY 128
static FILE *music;
static signed char blocks[2][BYTES];
static int active, at, valid[2], loading, loaded;
static unsigned long remaining, total, played, reads, bytes_read, errors, opens;
static unsigned long completions, manual_changes, sync_fills;
static int current=-1, mode, paused, available;
static int title_track=-1, title_playing;
static int groups[2][100], counts[2], bags[2][100], left[2];
static int history[2][HISTORY], length[2], cursor[2]={-1,-1};
static int opened[256], opened_count;
static unsigned int rng=0x41c64e6dU;
static int fade, previous_l, previous_r;
static FILE *events;
static char opened_file[12]="none";
static unsigned long be32(byte *p) { return ((unsigned long)p[0]<<24)|((unsigned long)p[1]<<16)|((unsigned long)p[2]<<8)|p[3]; }
static int random_bounded(int n) { rng=rng*1664525U+1013904223U;return (rng>>16)%n; }
static void log_event(const char *why) {
    /* Buffer diagnostic writes; synchronous flushes do not belong in the mixer. */
    if(events) fprintf(events,"%ld,%s,%d,%d,%s,%lu,%lu\n",(long)(Sys_FloatTime()*1000),why,mode,current,opened_file,played,total);
}
void AW_MusicSceneEvent(const char *why) {log_event(why);}
static void close_music(void) {
    if(music)fclose(music);music=NULL;at=0;valid[0]=valid[1]=0;loaded=0;loading=-1;
}
static int open_track(int id,const char *reason) {
    byte h[16];char path[MAX_OSPATH+64];unsigned long count;
    close_music();
    if(id<0 || id>98 || strlen(com_gamedir)+24>=sizeof(path)){errors++;return 0;}
    /* The selected Amiga sprintf reads %d as a word: it opened track00 for
     * every small 32-bit id. Build fixed-width digits without varargs. */
    strcpy(opened_file,"track00.mws");opened_file[5]='0'+id/10;opened_file[6]='0'+id%10;
    strcpy(path,com_gamedir);strcat(path,"/music/");strcat(path,opened_file);
    music=fopen(path,"rb");
    if(!music){errors++;return 0;}
    if(fread(h,1,16,music)!=16 || memcmp(h,"MWA1",4) || h[6]!=32 || h[7]!=0 || (((int)h[4]<<8)|h[5])!=11015) {errors++;close_music();return 0;}
    total=remaining=be32(h+8);count=be32(h+12);
    if(!total || count!=(total+FRAMES-1)/FRAMES){errors++;close_music();return 0;}
    current=id;played=0;opens++;active=0;
    if(opened_count<256)opened[opened_count++]=id;
    log_event(reason);
    /* Routine track notices belong to the optional debug layer. Keep the
     * event log independent and leave explicit music_status queries visible. */
    if(AW_DebugOverlaysEnabled())
        Con_Printf("OST %s: track %02ld (%s)\n",mode?"battle":"explore",(long)id,reason);
    return 1;
}
static int shuffled(void) {
    int i,j,t;
    if(!left[mode]) {
        left[mode]=counts[mode];for(i=0;i<left[mode];i++)bags[mode][i]=groups[mode][i];
        for(i=left[mode]-1;i>0;i--){j=random_bounded(i+1);t=bags[mode][i];bags[mode][i]=bags[mode][j];bags[mode][j]=t;}
        if(left[mode]>1 && bags[mode][left[mode]-1]==current){t=bags[mode][0];bags[mode][0]=current;bags[mode][left[mode]-1]=t;}
    }
    return bags[mode][--left[mode]];
}
static int advance(const char *reason) {
    int id,tries;
    if(title_playing){if(open_track(title_track,reason))return 1;available=0;return 0;}
    for(tries=0;tries<counts[mode];tries++) {
        if(cursor[mode]+1<length[mode])id=history[mode][++cursor[mode]];
        else {
            id=shuffled();
            if(length[mode]==HISTORY){memmove(history[mode],history[mode]+1,(HISTORY-1)*sizeof(int));length[mode]--;}
            cursor[mode]=length[mode];history[mode][length[mode]++]=id;
        }
        if(open_track(id,reason))return 1;
    }
    available=0;return 0;
}
/* One 4 KiB read per service call. No heap allocation and no decoder on Amiga. */
static int refill(void) {
    int target,take;
    if(!music || !remaining)return 0;
    target=valid[active]?1-active:active;
    if(valid[target])return 0;
    if(loading<0){loading=target;loaded=0;}
    take=BYTES-loaded;if(take>4096)take=4096;
    if(fread(blocks[loading]+loaded,1,take,music)!=(size_t)take){errors++;log_event("read-error");close_music();available=0;return 0;}
    reads++;bytes_read+=take;loaded+=take;
    if(loaded==BYTES){valid[loading]=remaining>FRAMES?FRAMES:(int)remaining;remaining-=valid[loading];loading=-1;loaded=0;}
    return 1;
}
void CDAudio_Update(void) {if(available && !paused)refill();}
void AW_MusicPaint(portable_samplepair_t *dst,int n) {
    int i,take,l,r,gain=(int)(bgmvolume.value*256);
    if(!available || paused)return;
    while(n>0) {
        if(at>=valid[active]) {
            valid[active]=0;at=0;
            if(valid[1-active] || loading==1-active)active=1-active;
            else if(!remaining && loading<0){completions++;log_event("complete");if(!advance("eof"))return;}
            if(!valid[active]) {sync_fills++;while(!valid[active] && refill()){}if(!valid[active])return;}
        }
        take=valid[active]-at;if(take>n)take=n;
        for(i=0;i<take;i++) {
            l=blocks[active][FRAMES+at+i]*gain;r=blocks[active][at+i]*gain;
            if(fade){l=(l*(128-fade)+previous_l*fade)/128;r=(r*(128-fade)+previous_r*fade)/128;fade--;}
            dst[i].left+=l;dst[i].right+=r;previous_l=l;previous_r=r;
        }
        at+=take;played+=take;dst+=take;n-=take;
    }
}
static void music_next(void) {if(available && !title_playing){manual_changes++;fade=128;advance("next");}}
static void music_previous(void) {
    if(!available || title_playing)return;manual_changes++;fade=128;
    if(cursor[mode]>0)cursor[mode]--;
    open_track(history[mode][cursor[mode]],"previous");
}
static void music_mode(void) {if(title_playing)return;mode=!mode;if(available){manual_changes++;fade=128;advance("mode");}}
static void music_status(void) {Con_Printf("OST group=%s track=%02ld played=%lu/%lu frames eof=%lu reads=%lu errors=%lu\n",title_playing?"title":mode?"battle":"explore",(long)current,played,total,completions,reads,errors);}
void AW_MusicTitle(void) {
    if(!available)return;
    /* Startup branding and its destination menu share the same title stream. */
    if(title_playing && music && current==title_track && !paused)return;
    title_playing=1;
    if(title_track<0 || !open_track(title_track,"main-menu")){paused=1;return;}
    paused=0;fade=0;previous_l=previous_r=0;
}
/* A deliberate demo opening followed by the remaining exploration shuffle.
 * Keep the chosen track in Previous/Next history and out of the first bag. */
int AW_MusicStartTrack(int id) {
    int i,j,t,n=0;
    if(!available)return 0;
    for(i=0;i<counts[0];i++)if(groups[0][i]==id)break;
    if(i==counts[0])return 0;
    mode=0;title_playing=0;
    if(current==id && played==0 && music)log_event("early_game_demo_start_1");
    else if(!open_track(id,"early_game_demo_start_1")) {
        advance("demo-track-fallback");return 0;
    }
    paused=0;fade=0;previous_l=previous_r=0;
    length[0]=1;cursor[0]=0;history[0][0]=id;
    for(i=0;i<counts[0];i++)if(groups[0][i]!=id)bags[0][n++]=groups[0][i];
    for(i=n-1;i>0;i--){j=random_bounded(i+1);t=bags[0][i];bags[0][i]=bags[0][j];bags[0][j]=t;}
    left[0]=n;
    return 1;
}
void CDAudio_Play(byte track,qboolean looping) {(void)track;(void)looping;paused=0;}
void CDAudio_Stop(void) {paused=1;}
void CDAudio_Pause(void) {paused=1;}
void CDAudio_Resume(void) {paused=0;}
int CDAudio_Init(void) {
    FILE *f;char path[MAX_OSPATH+64];int g,n,i,j,id;
    sprintf(path,"%s/music/playlist.txt",com_gamedir);f=fopen(path,"r");if(!f)return -1;
    for(g=0;g<2;g++) {
        if(fscanf(f,"%d",&n)!=1 || n<1 || n>99){fclose(f);return -1;}
        counts[g]=0;
        for(i=0;i<n;i++) {
            if(fscanf(f,"%d",&id)!=1 || id<0 || id>98){fclose(f);return -1;}
            for(j=0;j<counts[g];j++)if(groups[g][j]==id)break;
            if(j==counts[g])groups[g][counts[g]++]=id;
        }
    }
    /* Optional third line: converter-resolved canonical title track. Old
     * two-line playlists retain world playback without assuming track 00. */
    title_track=-1;title_playing=0;
    if(fscanf(f,"%d",&id)==1 && id>=0 && id<=98)title_track=id;
    fclose(f);available=1;paused=0;mode=0;loading=-1;
    rng^=(unsigned int)(Sys_FloatTime()*1000000.0);
    events=fopen("music-events.csv","w");if(events)fprintf(events,"time_ms,event,mode,track,file,played_frames,total_frames\n");
    Cmd_AddCommand("aw_music_next",music_next);Cmd_AddCommand("aw_music_previous",music_previous);
    Cmd_AddCommand("aw_music_mode",music_mode);Cmd_AddCommand("aw_music_status",music_status);
    return advance("start")?0:-1;
}
void CDAudio_Shutdown(void) {
    FILE *f;int i;log_event("shutdown");close_music();if(events){fclose(events);events=NULL;}
    f=fopen("music-profile.txt","w");
    if(f){fprintf(f,"read_slices=%lu\nbytes_read=%lu\nread_errors=%lu\ntrack_opens=%lu\nlast_track=%d\nnatural_completions=%lu\nmanual_changes=%lu\nsynchronous_fills=%lu\n",reads,bytes_read,errors,opens,current,completions,manual_changes,sync_fills);fprintf(f,"track_history=");for(i=0;i<opened_count;i++)fprintf(f,"%s%d",i?",":"",opened[i]);fprintf(f,"\n");fclose(f);}
}
