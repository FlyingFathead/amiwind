/* SPDX-License-Identifier: GPL-2.0-or-later
 * Host oracle: generated samples only. Included player is the runtime source.
 */
#include "aw_music.c"
#include <assert.h>
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
    if(!strcmp(argv[2],"buffered")) {
        unsigned long initial_reads;
        assert(MUSIC_BLOCKS==4 && sizeof(blocks)==65536);
        assert(open_track(11,"buffer-test"));
        for(j=0;j<20;j++)CDAudio_Update();
        assert(valid[0]==8192 && valid[1]==8192 && valid[2]==8192 && valid[3]==8192);
        initial_reads=reads;assert(initial_reads==16);
        /* Three full blocks plus the fourth tail play with no filesystem read. */
        for(j=0;j<30000;j++){
            memset(&sample,0,sizeof(sample));AW_MusicPaint(&sample,1);
            assert(sample.left==((signed char)((j*3+11*17)%256))*256);
            assert(sample.right==((signed char)((j*7+11*31)%256))*256);
        }
        assert(reads==initial_reads && sync_fills==0 && errors==0);
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
    assert(reads*4096==bytes_read);
    CDAudio_Shutdown();free(raw);return 0;
}
