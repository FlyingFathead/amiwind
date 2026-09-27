; Front-to-back heightfield columns, four horizontal pixels per sample.
; Occlusion uses a per-column horizon. Pitch is a vertical horizon shift.
        section code,code

update_walk_mode:
        tst.b   keys+$01            ; 1 / 2 / 3: dense / medium / long fog
        beq.s   .medium
        move.w  #128,solid_view_limit
.medium:
        tst.b   keys+$02
        beq.s   .long
        move.w  #192,solid_view_limit
.long:
        tst.b   keys+$03
        beq.s   .fog
        move.w  #320,solid_view_limit
.fog:
        move.w  solid_view_limit(pc),d0
        lsr.w   #1,d0
        move.w  d0,fog_start
        lsr.w   #1,d0
        add.w   fog_start(pc),d0
        move.w  d0,fog_full
        tst.b   keys+$42            ; Tab: edge-triggered solid/wire toggle
        beq.s   .released
        tst.w   tab_held
        bne.s   .done
        move.w  #1,tab_held
        eori.w  #1,solid_mode
        bsr     set_walk_palette
        rts
.released:
        clr.w   tab_held
.done:
        rts

set_walk_palette:
        lea     solid_palette,a0
        lea     copper_colours+2,a1
        moveq   #15,d0
.colour:
        move.w  (a0)+,(a1)
        addq.l  #4,a1
        dbra    d0,.colour
        move.w  #$678,horizon_colour+2
        tst.w   solid_mode
        bne.s   .done
        move.w  #$cb9,copper_colours+6
.done:
        rts

render_solid:
        lea     column_tops,a0
        lea     terrain_horizons,a1
        moveq   #39,d0
.reset:
        move.l  #$00ae00ae,(a0)+     ; Exclusive bottom at row 174
        move.l  #$00ae00ae,(a1)+
        dbra    d0,.reset
        move.l  a1,horizon_cursor
.wait_blit:
        btst    #6,2(a5)
        bne.s   .wait_blit
        move.w  #$03fa,$40(a5)       ; C OR constant A -> D; C/D DMA only
        clr.w   $42(a5)
        move.w  #38,$60(a5)          ; One word wide, next screen row = 40 bytes
        move.w  #38,$66(a5)
        lea     solid_depths,a0
        move.l  a0,depth_cursor
        ; The fully fogged region is the cleared sky colour. Do not sample it.
        move.w  fog_full(pc),d7
        lsr.w   #3,d7
        subq.w  #3,d7
.depth:
        bsr     stream_render_service
        move.l  depth_cursor(pc),a0
        move.w  (a0)+,d4
        move.w  d4,current_depth
        move.w  (a0)+,depth_reciprocal
        move.l  (a0)+,depth_heights
        move.l  a0,depth_cursor
        ; Q8 ray endpoints. Left edge is -160/128 times depth.
        move.w  yaw_sine(pc),d0
        muls.w  d4,d0
        move.w  yaw_cosine(pc),d1
        muls.w  d4,d1
        move.l  d1,d2
        asr.l   #5,d2
        move.l  d2,ray_step_x
        move.l  d0,d2
        neg.l   d2
        asr.l   #5,d2
        move.l  d2,ray_step_y
        move.l  d1,d2
        asr.l   #2,d2
        add.l   d1,d2
        move.l  camera_x(pc),d3
        add.l   d0,d3
        sub.l   d2,d3
        move.l  d3,a6
        move.l  d0,d2
        asr.l   #2,d2
        add.l   d0,d2
        move.l  camera_y(pc),d3
        add.l   d1,d3
        add.l   d2,d3
        move.l  d3,a4
        lea     solid_heights,a3
        lea     column_tops,a2
        moveq   #0,d6
.column:
        cmp.w   #32,(a2)
        ble     .next
        move.l  a6,d0
        cmp.l   #1536*256,d0
        bhi     .next              ; Unsigned also rejects negative coordinates
        move.l  a4,d1
        cmp.l   #1536*256,d1
        bhi     .next
        ; Bounded nonnegative Q8 coordinates: low word after swap = value >> 12.
        lsl.l   #4,d0
        swap    d0
        lsl.l   #4,d1
        swap    d1
        add.w   d1,d1
        lea     solid_rows,a0
        move.w  0(a0,d1.w),d1
        add.w   d0,d1
        add.w   d1,d1
        move.w  0(a3,d1.w),d0
        sub.w   camera_height(pc),d0
        add.w   #SOLID_DELTA_BIAS,d0
        add.w   d0,d0
        move.l  depth_heights(pc),a0
        move.w  0(a0,d0.w),d0
        neg.w   d0
        add.w   solid_horizon(pc),d0
        cmp.w   (a2),d0
        bge.s   .next
        cmp.w   #32,d0
        bge.s   .visible
        moveq   #32,d0
.visible:
        move.w  d1,d2
        lsr.w   #1,d2
        lea     solid_colours,a0
        moveq   #0,d3
        move.b  0(a0,d2.w),d3
        move.w  (a2),d1
        move.w  d0,(a2)
        move.w  d6,d2
        move.w  current_depth(pc),d4
        cmp.w   fog_start(pc),d4
        blo.s   .draw
        moveq   #4,d3              ; Reduced contrast in the fog band
        cmp.w   fog_full(pc),d4
        blo.s   .draw
        moveq   #6,d3              ; Fully opaque fog matches the sky exactly
.draw:
        bsr     solid_span
.next:
        adda.l  ray_step_x(pc),a6
        adda.l  ray_step_y(pc),a4
        addq.l  #2,a2
        addq.w  #1,d6
        cmp.w   #80,d6
        blo     .column
        lea     column_tops,a0
        move.l  horizon_cursor,a1
        moveq   #39,d0
.save_horizon:
        move.l  (a0)+,(a1)+
        dbra    d0,.save_horizon
        move.l  a1,horizon_cursor
        dbra    d7,.depth
.finish_blit:
        btst    #6,2(a5)
        bne.s   .finish_blit
        rts

; d0 top, d1 bottom exclusive, d2 column, d3 palette index.
; Each pixel is written at most once, so set only the selected planes.
; Preserves d6-d7/a2-a6 (the ray traversal state).
solid_span:
        ; Previous long span may overlap projection, but never another writer.
.wait_previous:
        btst    #6,2(a5)
        bne.s   .wait_previous
        sub.w   d0,d1
        subq.w  #1,d1
        mulu.w  #40,d0
        cmp.w   #7,d1
        bge     blit_solid_span
        move.w  d2,d4
        lsr.w   #1,d4
        add.w   d4,d0
        move.l  walk_draw_buffer(pc),a0
        adda.w  d0,a0
        and.w   #1,d2
        lea     column_masks(pc),a1
        move.b  0(a1,d2.w),d5
        btst    #0,d3
        beq.s   .plane1
        move.l  a0,a1
        move.w  d1,d4
.pixels0:
        or.b    d5,(a1)
        adda.w  #40,a1
        dbra    d4,.pixels0
.plane1:
        adda.w  #8000,a0
        btst    #1,d3
        beq.s   .plane2
        move.l  a0,a1
        move.w  d1,d4
.pixels1:
        or.b    d5,(a1)
        adda.w  #40,a1
        dbra    d4,.pixels1
.plane2:
        adda.w  #8000,a0
        btst    #2,d3
        beq.s   .done
        move.w  d1,d4
.pixels2:
        or.b    d5,(a0)
        adda.w  #40,a0
        dbra    d4,.pixels2
.done:
        rts

; Long spans use the blitter's masked OR operation, avoiding CPU pixel writes.
; Short spans keep the CPU path because setting up several blits costs more.
blit_solid_span:
        move.w  d2,d4
        lsr.w   #2,d4
        add.w   d4,d4
        add.w   d4,d0
        move.l  walk_draw_buffer(pc),a0
        adda.w  d0,a0
        and.w   #3,d2
        add.w   d2,d2
        lea     blit_column_masks(pc),a1
        move.w  0(a1,d2.w),$74(a5)    ; BLTADAT, repeated constant nibble mask
        addq.w  #1,d1
        lsl.w   #6,d1
        addq.w  #1,d1                ; Height x 1 word
        btst    #0,d3
        beq.s   .plane1
        move.l  a0,$48(a5)
        move.l  a0,$54(a5)
        move.w  d1,$58(a5)
.plane1:
        adda.w  #8000,a0
        btst    #1,d3
        beq.s   .plane2
.wait1:
        btst    #6,2(a5)
        bne.s   .wait1
        move.l  a0,$48(a5)
        move.l  a0,$54(a5)
        move.w  d1,$58(a5)
.plane2:
        adda.w  #8000,a0
        btst    #2,d3
        beq.s   .done
.wait2:
        btst    #6,2(a5)
        bne.s   .wait2
        move.l  a0,$48(a5)
        move.l  a0,$54(a5)
        move.w  d1,$58(a5)
.done:
        rts

solid_mode: dc.w 1
tab_held: dc.w 0
solid_horizon: dc.w 100
solid_view_limit: dc.w 128
fog_start: dc.w 64
fog_full: dc.w 96
current_depth: dc.w 16
depth_reciprocal: dc.w 2048
depth_cursor: dc.l 0
depth_heights: dc.l 0
ray_step_x: dc.l 0
ray_step_y: dc.l 0
column_masks: dc.b $f0,$0f
blit_column_masks: dc.w $f000,$0f00,$00f0,$000f

; Count presented-frame intervals, including input/vblank work between frames.
; Cap each mode's sample at 60,000 PAL/NTSC ticks to keep the report bounded.
record_frame:
        bsr     read_ticks
        move.l  d0,d1
        sub.l   frame_last_tick(pc),d0
        and.l   #$ffffff,d0
        move.l  d1,frame_last_tick
        lea     solid_stats(pc),a0
        tst.w   solid_mode
        bne.s   .mode
        lea     wire_stats(pc),a0
.mode:
        move.l  4(a0),d1
        add.l   d0,d1
        cmp.l   #60000,d1
        bhi.s   .done
        move.l  d1,4(a0)
        addq.l  #1,(a0)
        bsr     profile_frame
.done:
        rts

report_frames:
        tst.w   walk_active
        beq     .done
        lea     solid_stats(pc),a2
        lea     solid_frame_text(pc),a3
        bsr     format_stats
        lea     wire_stats(pc),a2
        lea     wire_frame_text(pc),a3
        bsr     format_stats
        move.l  4.w,a6
        lea     dos_name(pc),a1
        moveq   #0,d0
        jsr     -552(a6)             ; OpenLibrary
        tst.l   d0
        beq.s   .done
        move.l  d0,a4
        move.l  d0,a6
        jsr     -60(a6)              ; Output
        move.l  d0,d1
        beq.s   .close
        move.l  #stats_text,d2
        move.l  #stats_text_end-stats_text,d3
        jsr     -48(a6)              ; Write
.close:
        move.l  a4,a1
        move.l  4.w,a6
        jsr     -414(a6)
.done:
        rts

; a2: frames,ticks; a3: "00000 frames / 00000 ticks = 0000.0 fps".
format_stats:
        move.l  (a2),d0
        move.l  a3,a0
        bsr     decimal5
        move.l  4(a2),d0
        lea     15(a3),a0
        bsr     decimal5
        moveq   #0,d0
        tst.l   4(a2)
        beq.s   .fps
        move.l  (a2),d0
        move.w  video_hz(pc),d1
        mulu.w  #10,d1
        mulu.w  d1,d0
        divu.w  6(a2),d0
        and.l   #$ffff,d0
.fps:
        lea     30(a3),a0
        bsr     decimal5
        move.b  4(a0),5(a0)
        move.b  #'.',4(a0)
        rts

decimal5:
        adda.w  #5,a0
        moveq   #4,d5
.digit:
        divu.w  #10,d0
        move.l  d0,d1
        swap    d1
        add.b   #'0',d1
        move.b  d1,-(a0)
        and.l   #$ffff,d0
        dbra    d5,.digit
        rts

frame_last_tick: dc.l 0
solid_stats: dc.l 0,0
wire_stats: dc.l 0,0
dos_name: dc.b "dos.library",0
stats_text:
        dc.b 10,"Morrowind demo: presented frames, capped sample",10,"Solid: "
solid_frame_text:
        dc.b "00000 frames / 00000 ticks =  0000.0 fps",10,"Wire:  "
wire_frame_text:
        dc.b "00000 frames / 00000 ticks =  0000.0 fps",10
stats_text_end:
        even
        section solid_work,bss
column_tops: ds.w 80
terrain_horizons: ds.w 29*80
horizon_cursor: ds.l 1
