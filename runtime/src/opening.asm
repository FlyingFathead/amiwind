; 68000 / OCS opening vignette. Launch from an AmigaDOS CLI.
; Assets are generated externally by tools/build_opening.py.
        section code,code
entry:
        movem.l d2-d7/a2-a6,-(sp)
        bsr     system_open
        tst.l   d0
        beq     failed
        ; CLI boot banner is generated from the builder's release version.
        move.l  stream_dos,a6
        jsr     -60(a6)             ; Output
        move.l  d0,d1
        beq.s   .no_banner
        move.l  #loading_text,d2
        move.l  #loading_text_end-loading_text,d3
        jsr     -48(a6)             ; Write
.no_banner:
        move.l  4.w,a6
        lea     graphics_name(pc),a1
        moveq   #0,d0
        jsr     -552(a6)             ; OpenLibrary
        tst.l   d0
        beq     failed
        move.l  d0,graphics_base
        move.l  d0,a6
        move.l  34(a6),old_view
        suba.l  a1,a1
        jsr     -222(a6)             ; LoadView(NULL)
        jsr     -270(a6)             ; WaitTOF twice for interlace
        jsr     -270(a6)
        jsr     -456(a6)             ; OwnBlitter after OS display shutdown
        jsr     -228(a6)             ; WaitBlit
        lea     $dff000,a5
        bsr     wait_frame
.detect:
        move.l  4(a5),d0
        and.l   #$1ff00,d0
        cmp.l   #$12c00,d0           ; PAL reaches scanline 300
        bhs.s   .pal
        cmp.l   #$fa00,d0
        bhs.s   .detect
        move.w  #325,audio_period
        move.w  #60,video_hz
.pal:
        move.l  4.w,a6
        jsr     -120(a6)             ; Brief display-register critical section
        move.w  2(a5),old_dma
        move.w  $1c(a5),old_intena
        move.w  $10(a5),old_adkcon
        move.b  $bfe001,old_cia
        move.w  #$01e0,$96(a5)       ; Display DMA only; OS disk/audio stays live
        bset    #1,$bfe001           ; Disable low-pass filter
        clr.w   scene
        clr.w   frame_count
        clr.w   voice_remaining
        clr.w   cue_started
        move.w  #1,mouse_was_down
        bsr     select_scene
        move.l  #copper,$80(a5)
        move.w  #0,$88(a5)
        move.w  #$8380,$96(a5)       ; Master, bitplanes, copper
        move.w  #1,input_active
        move.l  4.w,a6
        jsr     -126(a6)             ; Enable disk, audio and input interrupts
        bsr     read_ticks
        or.w    #1,d0
        move.w  d0,music_rng
        bsr     stream_begin
        bsr     read_ticks
        move.l  d0,last_ticks
        move.l  d0,benchmark_start
        tst.l   benchmark_limit
        beq.s   .loop
        bsr     start_walk
.loop:
        tst.w   walk_active
        bne.s   .timing             ; Walking already waits when presenting
        bsr     wait_frame
.timing:
        bsr     stream_pump
        bsr     music_keys
        bsr     update_ticks
        tst.l   benchmark_limit
        beq.s   .manual
        move.l  last_ticks,d0
        sub.l   benchmark_start,d0
        and.l   #$ffffff,d0
        cmp.l   benchmark_limit,d0
        bhs     restore
.manual:
        tst.b   keys+$45            ; Escape
        bne     restore
        tst.w   walk_active
        bne.s   .walking
        tst.b   keys+$44            ; Return enters the terrain experiment
        beq.s   .still
        bsr     start_walk
        bra.s   .clock
.still:
        bsr     fade_palette
        bra.s   .clock
.walking:
        bsr     update_walk_mode
        bsr     update_camera
        bsr     render_walk
.clock:
        move.w  elapsed_ticks,d0
        add.w   d0,frame_count
        tst.w   cue_started
        bne.s   .voice_tick
        move.w  video_hz(pc),d0
        add.w   d0,d0
        cmp.w   frame_count(pc),d0
        bhi.s   .voice_tick
        bsr     start_voice
        move.w  #1,cue_started
.voice_tick:
        bsr     voice_poll
.input:
        tst.w   walk_active
        bne     .loop
        btst    #10,$16(a5)          ; Right mouse exits
        beq     restore
        btst    #6,$bfe001           ; Left mouse advances on press
        bne.s   .released
        tst.w   mouse_was_down
        bne     .loop
        move.w  #1,mouse_was_down
        addq.w  #1,scene
        cmp.w   #SCENE_COUNT,scene
        blo.s   .next
        clr.w   scene
.next:
        bsr     select_scene
        bra     .loop
.released:
        clr.w   mouse_was_down
        bra     .loop

; Update only the copper pointers/palette, never copy the whole screen per frame.
select_scene:
        moveq   #0,d0
        move.w  scene(pc),d0
        lsl.w   #2,d0
        lea     scene_table,a0
        move.l  0(a0,d0.w),d1
        lea     plane_pointers+2,a1
        moveq   #3,d2
.plane:
        swap    d1
        move.w  d1,(a1)
        swap    d1
        move.w  d1,4(a1)
        add.l   #8000,d1
        addq.l  #8,a1
        dbra    d2,.plane
        clr.w   fade_level
        bsr     fade_palette
        rts

fade_palette:
        moveq   #0,d0
        move.w  scene(pc),d0
        lsl.w   #5,d0
        lea     palettes,a0
        adda.w  d0,a0
        lea     copper_colours+2,a1
        move.w  fade_level(pc),d4
        lsr.w   #1,d4
        moveq   #15,d5
.colour:
        move.w  (a0)+,d0
        move.w  d0,d1
        and.w   #$f00,d1
        mulu.w  d4,d1
        lsr.l   #4,d1
        and.w   #$f00,d1
        move.w  d0,d2
        and.w   #$0f0,d2
        mulu.w  d4,d2
        lsr.l   #4,d2
        and.w   #$0f0,d2
        or.w    d2,d1
        and.w   #$00f,d0
        mulu.w  d4,d0
        lsr.l   #4,d0
        or.w    d0,d1
        move.w  d1,(a1)
        cmp.w   #15,d5
        bne.s   .not_background
        move.w  d1,horizon_colour+2
.not_background:
        addq.l  #4,a1
        dbra    d5,.colour
        cmp.w   #32,fade_level
        bhs.s   .done
        addq.w  #1,fade_level
.done:
        rts

wait_frame:
        move.l  4(a5),d0
        and.l   #$1ff00,d0
        cmp.l   #$fa00,d0
        beq.s   wait_frame
.wait:
        move.l  4(a5),d0
        and.l   #$1ff00,d0
        cmp.l   #$fa00,d0
        bne.s   .wait
        rts

restore:
        bsr     stream_stop
        bsr     voice_stop
        move.l  4.w,a6
        jsr     -120(a6)
        move.w  #$01e0,$96(a5)
        btst    #1,old_cia
        beq.s   .filter_on
        bset    #1,$bfe001
        bra.s   .filter_done
.filter_on:
        bclr    #1,$bfe001
.filter_done:
        move.l  graphics_base(pc),a6
        move.l  38(a6),$80(a5)       ; System copper list
        move.w  #0,$88(a5)
        move.w  old_dma(pc),d0
        and.w   #$01e0,d0
        or.w    #$8200,d0
        move.w  d0,$96(a5)
        move.l  4.w,a6
        jsr     -126(a6)
        move.l  graphics_base(pc),a6
        move.l  old_view(pc),a1
        jsr     -222(a6)
        jsr     -270(a6)
        jsr     -270(a6)
        jsr     -462(a6)             ; DisownBlitter
        move.l  a6,a1
        move.l  4.w,a6
        jsr     -414(a6)             ; CloseLibrary
        bsr     report_frames
        bsr     report_stream
        bsr     profile_save
        bsr     system_close
        movem.l (sp)+,d2-d7/a2-a6
        moveq   #0,d0
        rts
failed:
        bsr     system_close
        movem.l (sp)+,d2-d7/a2-a6
        moveq   #20,d0
        rts

graphics_name: dc.b "graphics.library",0
        even
graphics_base: dc.l 0
old_view: dc.l 0
old_dma: dc.w 0
old_intena: dc.w 0
old_adkcon: dc.w 0
old_cia: dc.w 0
scene: dc.w 0
fade_level: dc.w 0
frame_count: dc.w 0
voice_remaining: dc.w 0
cue_started: dc.w 0
mouse_was_down: dc.w 0
audio_period: dc.w 322
video_hz: dc.w 50

        section display,data_c
copper:
        dc.w $100,$4200             ; 4 bitplanes, colour, low resolution
        dc.w $102,0,$104,0
        dc.w $108,0,$10a,0           ; Plane modulos
        dc.w $08e,$2c81,$090,$f4c1   ; 320 x 200, PAL and NTSC
        dc.w $092,$0038,$094,$00d0
plane_pointers:
        dc.w $0e0,0,$0e2,0,$0e4,0,$0e6,0
        dc.w $0e8,0,$0ea,0,$0ec,0,$0ee,0
copper_colours:
        dc.w $180,0,$182,0,$184,0,$186,0
        dc.w $188,0,$18a,0,$18c,0,$18e,0
        dc.w $190,0,$192,0,$194,0,$196,0
        dc.w $198,0,$19a,0,$19c,0,$19e,0
horizon_wait:
        dc.w $9001,$fffe
horizon_colour:
        dc.w $180,0
        dc.w $ffff,$fffe
silence: dc.w 0
        include "opening-assets.i"
        include "walking.asm"
        include "solid.asm"
        include "town.asm"
        include "streaming.asm"
        include "profiling.asm"
