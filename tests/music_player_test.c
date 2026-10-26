/* SPDX-License-Identifier: GPL-2.0-or-later
 * Host oracle: generated samples only. Included player is the runtime source.
 */
#include "aw_music.c"
#include <assert.h>
/* One game frame at 20 fps: the main loop's service call, then the mixer.
 * Returns the frames with sound. Nothing in here may wait for a read. */
static portable_samplepair_t frame_buffer[551];
static int game_frame(void) {
    int i,heard=0;
    memset(frame_buffer,0,sizeof(frame_buffer));test_now+=0.05;
    CDAudio_Update();AW_MusicPaint(frame_buffer,551);
    for(i=0;i<551;i++)if(frame_buffer[i].left || frame_buffer[i].right)heard++;
    return heard;
}
/* HANG-IDLE-DUSK-35: the stream's reads are held unanswered (late or never). */
static int stall_case(const char *which) {
    int j,heard,silent=0,loops=0;
    assert(open_track(11,"stall-test"));
    for(j=0;j<20;j++)CDAudio_Update();
    assert(valid[0]==8192 && valid[1]==8192 && valid[2]==8192 && valid[3]==8192);
    aw_aread_hold=1;
    /* About 3 s of buffered music plays on, then silence; the loop goes on. */
    for(j=0;j<80;j++){if(!game_frame())silent++;loops++;}
    assert(silent>0 && underruns>0 && stalls==1 && stall_notices==1);
    assert(available && music && current==11 && abandons==0);
    if(!strcmp(which,"late")) {
        /* The reply comes back before the stream is given up: music resumes
         * from where it stopped, no frame of the stream is lost. */
        unsigned long before=played;
        aw_aread_hold=0;
        for(j=0,heard=0;j<10;j++)heard+=game_frame();
        assert(recoveries==1 && heard>0 && played>before && current==11 && abandons==0);
        assert(stall_notices==1);CDAudio_Shutdown();return 0;
    }
    /* Never answered: after 6 s the stream is abandoned and the next track
     * opened on a free reader; with every reader waiting the music goes off. */
    for(j=0;j<600 && available;j++){heard=game_frame();assert(!heard);loops++;}
    assert(!available && stall_off && abandons==3 && stalls==3 && stall_notices==1);
    for(j=0;j<100;j++){assert(!game_frame());loops++;}
    assert(loops>=400 && test_now>=18.0); /* about 20 s of game frames, none waited */
    /* The late replies finally arrive: the readers close and the music returns. */
    aw_aread_hold=0;
    for(j=0,heard=0;j<20;j++)heard+=game_frame();
    assert(available && !stall_off && heard>0 && stall_notices==1);
    CDAudio_Shutdown();return 0;
}
/* ENGINE-MUSIC-NO-OFF-SWITCH-36: dbg music off closes the stream; a read that is
 * still outstanding is abandoned (never waited for) and closes when its reply
 * comes; no new stream or read until dbg music on, which plays again. */
static int switch_case(void) {
    int j,heard;unsigned long opened_before,reads_before;
    assert(music_switch.value==1 && !muted);           /* default on */
    assert(open_track(11,"switch-test"));
    for(j=0,heard=0;j<20;j++)heard+=game_frame();
    assert(heard>0 && music);
    aw_aread_hold=1;                                    /* play until a refill read is held */
    for(j=0;j<40 && AW_AReadPoll(music)!=AW_AREAD_PENDING;j++)game_frame();
    assert(music && AW_AReadPoll(music)==AW_AREAD_PENDING);
    Cvar_SetValue("aw_music",0);
    for(j=0;j<40;j++)assert(!game_frame());            /* silent, the loop goes on */
    assert(muted && !music && available);
    assert(AW_AReadService()==1);                      /* the abandoned read keeps its reader */
    opened_before=opens;reads_before=reads;
    AW_MusicCombat(1);AW_MusicCombat(0);AW_MusicDeath();
    assert(!music && opens==opened_before);           /* nothing opens while off */
    aw_aread_hold=0;
    for(j=0;j<20;j++)assert(!game_frame());
    assert(AW_AReadService()==0 && reads==reads_before && opens==opened_before);
    Cvar_SetValue("aw_music",1);
    for(j=0,heard=0;j<40;j++)heard+=game_frame();
    assert(!muted && music && available && heard>0 && opens==opened_before+1);
    CDAudio_Shutdown();return 0;
}
int main(int argc,char **argv) {
    portable_samplepair_t sample;
    unsigned long position=0, old_total=0, offset;
    int track=-1, j, k, loops=0;
    FILE *check;
    byte *raw=NULL;
    long size;
    char path[1200];
    assert(argc==3);strcpy(com_gamedir,argv[1]);
    if(!strcmp(argv[2],"invalid")) {assert(CDAudio_Init()==-1);return 0;}
    assert(CDAudio_Init()==0);rng=42;
    if(!strcmp(argv[2],"stall-late"))return stall_case("late");
    if(!strcmp(argv[2],"stall-never"))return stall_case("never");
    if(!strcmp(argv[2],"switch"))return switch_case();
    if(!strcmp(argv[2],"buffered")) {
        unsigned long initial_reads;
        assert(MUSIC_BLOCKS==4 && sizeof(blocks)==65536);
        assert(open_track(11,"buffer-test"));
        for(j=0;j<20;j++)CDAudio_Update();
        assert(valid[0]==8192 && valid[1]==8192 && valid[2]==8192 && valid[3]==8192);
        /* One 16 KiB block per asynchronous read (HANG-IDLE-DUSK-35). */
        initial_reads=reads;assert(initial_reads==4 && bytes_read==4*16384);
        /* Three full blocks plus the fourth tail play with no filesystem read. */
        for(j=0;j<30000;j++){
            memset(&sample,0,sizeof(sample));AW_MusicPaint(&sample,1);
            assert(sample.left==((signed char)((j*3+11*17)%256))*256);
            assert(sample.right==((signed char)((j*7+11*31)%256))*256);
        }
        assert(reads==initial_reads && sync_fills==0 && errors==0);
        CDAudio_Shutdown();return 0;
    }
    if(!strcmp(argv[2],"loadpump")) {
        /* AUDIO-LOAD-29: a track opened as a load begins (the first load after the intro movie) gets no frame
         * service; the loading screen's mixer updates pump its reads, so the four blocks fill ahead with no
         * CDAudio_Update and no emergency fill in the painter. */
        assert(open_track(11,"load-test"));
        assert(!valid[0] && !valid[1] && !valid[2] && !valid[3]);
        for(j=0;j<20;j++)AW_MusicLoadPump();
        assert(valid[0]==8192 && valid[1]==8192 && valid[2]==8192 && valid[3]==8192);
        for(j=0;j<20000;j++){memset(&sample,0,sizeof(sample));AW_MusicPaint(&sample,1);}
        assert(sync_fills==0 && underruns==0 && errors==0);
        /* paused (the movie, the title hold) or switched off: the pump does nothing */
        CDAudio_Pause();k=(int)reads;for(j=0;j<20;j++)AW_MusicLoadPump();assert((int)reads==k);
        CDAudio_Shutdown();return 0;
    }
    if(!strcmp(argv[2],"notifications")) {
        assert(track_notices==0);
        music_next();music_previous();music_mode();assert(track_notices==0);
        debug_overlay=1;music_next();assert(track_notices==1);
        /* Natural completion obeys the same switch as manual changes. */
        for(j=0;j<20000 && completions<2;j++){
            memset(&sample,0,sizeof(sample));AW_MusicPaint(&sample,1);
        }
        assert(completions>=2 && track_notices>=3);
        debug_overlay=0;k=track_notices;music_next();music_previous();music_mode();
        assert(track_notices==k);music_status();assert(status_queries==1);
        CDAudio_Shutdown();return 0;
    }
    if(!strcmp(argv[2],"menu")) {
        /* MUSIC-STARTUP-TRACK-31: with a title track nothing plays before the menu. */
        assert(paused && !music && opens==0);
        memset(&sample,0,sizeof(sample));AW_MusicPaint(&sample,1);assert(!sample.left && !sample.right);
        AW_MusicTitle();assert(title_playing && current==83 && !paused);
        for(j=0;j<35;j++){memset(&sample,0,sizeof(sample));AW_MusicPaint(&sample,1);}
        assert(current==83 && completions>=3);
        position=played;offset=opens;AW_MusicTitle();
        assert(played==position && opens==offset && !paused); /* logo -> menu continuity */
        music_next();music_previous();music_mode();assert(current==83);
        assert(AW_MusicStartTrack(4));assert(!title_playing && current==4 && played==0);
        for(j=0;j<10;j++)AW_MusicPaint(&sample,1);
        assert(AW_MusicStartTrack(4) && played==0);AW_MusicTitle();assert(current==83);
        /* MUSIC-OPENING-CLIP-31: the hold is silent and flushed; a map-load CD
         * resume cannot restart it; the opening track ends the hold. */
        AW_MusicHold();assert(paused && !music && !title_playing);
        CDAudio_Play(1,1);CDAudio_Resume();assert(paused);
        memset(&sample,0,sizeof(sample));AW_MusicPaint(&sample,1);assert(!sample.left && !sample.right);
        assert(AW_MusicStartTrack(4) && !paused && current==4);
        CDAudio_Pause();CDAudio_Resume();assert(!paused);
        CDAudio_Shutdown();return 0;
    }
    if(!strcmp(argv[2],"demo-missing")) {
        assert(!AW_MusicStartTrack(4));assert(available && music && current!=4);
        CDAudio_Shutdown();return 0;
    }
    if(!strcmp(argv[2],"demo")) {
        assert(AW_MusicStartTrack(4));assert(current==4 && mode==0 && !paused && played==0);
        assert(length[0]==1 && cursor[0]==0 && history[0][0]==4);
        assert(left[0]==counts[0]-1);
        for(j=0;j<left[0];j++)assert(bags[0][j]!=4);
        assert(!AW_MusicStartTrack(98));assert(current==4);
    }
    if(!strcmp(argv[2],"truncated")) {
        memset(&sample,0,sizeof(sample));AW_MusicPaint(&sample,1);
        assert(errors==1 && !available && !music);
        assert(sample.left==0 && sample.right==0);CDAudio_Shutdown();return 0;
    }
    while(completions<18) {
        for(k=0;k<3;k++)CDAudio_Update();
        for(k=0;k<997;k++) {
            memset(&sample,0,sizeof(sample));AW_MusicPaint(&sample,1);
            if(track!=current) {
                if(raw) {assert(position==old_total);free(raw);}
                track=current;old_total=total;position=0;
                sprintf(path,"%s/music/track%02d.mws",com_gamedir,track);
                check=fopen(path,"rb");assert(check);fseek(check,0,SEEK_END);
                size=ftell(check);rewind(check);raw=malloc(size);assert(raw);
                assert(fread(raw,1,size,check)==(size_t)size);fclose(check);
            }
            offset=position/8192*16384+16+position%8192;
            assert(sample.left==((signed char)raw[offset+8192])*256);
            assert(sample.right==((signed char)raw[offset])*256);
            position++;assert(position==played);
        }
        assert(++loops<100000);
    }
    assert(errors==0 && manual_changes==0);
    assert(track_notices==0); /* Startup and 18 natural changes stay silent. */
    for(j=1;j<opened_count;j++)assert(opened[j]!=opened[j-1]);
    {int a=current,b;music_next();b=current;music_previous();assert(current==a);music_next();assert(current==b);}
    music_mode();assert(mode==1);
    for(j=0;j<30;j++){int old=current;music_next();assert(current!=old);}
    music_mode();assert(mode==0);
    if(!strcmp(argv[2],"demo")) {
        music_mode();assert(mode==1);CDAudio_Pause();
        assert(AW_MusicStartTrack(4));assert(current==4 && mode==0 && !paused);
    }
    assert(reads*16384==bytes_read && stalls==0 && abandons==0);
    CDAudio_Shutdown();free(raw);return 0;
}
