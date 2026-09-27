; Bounded first-person terrain experiment. 68000 only; baked town views.
; Included by opening.asm. Hardware is already owned by the opening runtime.
        section code,code

read_ticks:
        moveq   #0,d0
        move.b  $bfea01,d0           ; High read latches the 24-bit TOD counter
        lsl.l   #8,d0
        move.b  $bfe901,d0
        lsl.l   #8,d0
        move.b  $bfe801,d0           ; Low read releases the latch
        rts

update_ticks:
        bsr     read_ticks
        move.l  d0,d1
        sub.l   last_ticks(pc),d0
        and.l   #$ffffff,d0
        move.l  d1,last_ticks
        cmp.l   #50,d0
        bls.s   .bounded
        moveq   #50,d0
.bounded:
        move.w  d0,elapsed_ticks
        rts

start_walk:
        bsr     read_ticks
        move.l  d0,frame_last_tick
        move.w  #1,walk_active
        move.w  $0a(a5),last_mouse
        move.w  #$4200,copper+2      ; Four planes, sixteen colours
        bsr     set_walk_palette
        move.w  #$8040,$96(a5)       ; Blitter DMA
        move.l  #walk_buffer_a,walk_draw_buffer
        bsr     update_camera
        bsr     render_walk
        rts

update_camera:
        move.w  $0a(a5),d0
        move.w  d0,d1
        sub.b   last_mouse+1,d1
        ext.w   d1
        asr.w   #1,d1
        add.w   d1,camera_yaw
        and.w   #255,camera_yaw
        move.w  d0,d1
        lsr.w   #8,d1
        sub.b   last_mouse,d1
        ext.w   d1
        asr.w   #1,d1
        sub.w   d1,camera_pitch
        move.w  d0,last_mouse
        cmp.w   #-40,camera_pitch
        bge.s   .pitch_max
        move.w  #-40,camera_pitch
.pitch_max:
        cmp.w   #40,camera_pitch
        ble.s   .trig
        move.w  #40,camera_pitch
.trig:
        lea     walk_sines,a0
        move.w  camera_yaw(pc),d0
        add.w   d0,d0
        move.w  0(a0,d0.w),yaw_sine
        add.w   #128,d0
        and.w   #511,d0
        move.w  0(a0,d0.w),yaw_cosine
        move.w  camera_pitch(pc),d0
        and.w   #255,d0
        add.w   d0,d0
        move.w  0(a0,d0.w),pitch_sine
        add.w   #128,d0
        and.w   #511,d0
        move.w  0(a0,d0.w),pitch_cosine
        ; Camera positions use eight fractional bits.
        moveq   #0,d4
        moveq   #0,d5
        tst.b   keys+$11            ; W
        beq.s   .s
        addq.w  #1,d4
.s:
        tst.b   keys+$21            ; S
        beq.s   .d
        subq.w  #1,d4
.d:
        tst.b   keys+$22            ; D
        beq.s   .a
        addq.w  #1,d5
.a:
        tst.b   keys+$20            ; A
        beq.s   .vectors
        subq.w  #1,d5
.vectors:
        move.w  yaw_sine(pc),d0
        muls.w  d4,d0
        move.w  yaw_cosine(pc),d1
        muls.w  d5,d1
        add.l   d1,d0
        move.w  yaw_cosine(pc),d1
        muls.w  d4,d1
        move.w  yaw_sine(pc),d2
        muls.w  d5,d2
        sub.l   d2,d1
        tst.w   d4
        beq.s   .speed
        tst.w   d5
        beq.s   .speed
        muls.w  #181,d0             ; Normalize diagonal movement
        asr.l   #8,d0
        muls.w  #181,d1
        asr.l   #8,d1
.speed:
        muls.w  elapsed_ticks(pc),d0
        muls.w  elapsed_ticks(pc),d1
        tst.b   keys+$60            ; Left Shift runs
        bne.s   .apply
        asr.l   #1,d0
        asr.l   #1,d1
.apply:
        bsr     town_move
        lea     camera_x,a0
        moveq   #1,d2
.bound:
        cmp.l   #32*256,(a0)
        bge.s   .upper
        move.l  #32*256,(a0)
.upper:
        cmp.l   #1504*256,(a0)
        ble.s   .next
        move.l  #1504*256,(a0)
.next:
        addq.l  #4,a0
        dbra    d2,.bound
        move.l  camera_x(pc),d0
        asr.l   #8,d0
        move.w  d0,camera_whole_x
        move.l  camera_y(pc),d1
        asr.l   #8,d1
        move.w  d1,camera_whole_y
        ; Nearest fine height; no character physics.
        lsr.w   #4,d0
        lsr.w   #4,d1
        mulu.w  #97,d1
        add.w   d0,d1
        add.w   d1,d1
        lea     solid_heights,a0
        move.w  0(a0,d1.w),d0
        add.w   #9,d0
        move.w  d0,camera_height
        ; Change the background palette at the projected horizon.
        move.w  pitch_sine(pc),d0
        ext.l   d0
        asl.l   #7,d0
        divs.w  pitch_cosine(pc),d0
        add.w   #100,d0
        move.w  d0,solid_horizon
        cmp.w   #32,d0
        bge.s   .hmax
        move.w  #32,d0
.hmax:
        cmp.w   #173,d0
        ble.s   .hset
        move.w  #173,d0
.hset:
        add.w   #44,d0
        lsl.w   #8,d0
        or.w    #1,d0
        move.w  d0,horizon_wait
        rts

render_walk:
        ; Blitter clears the back buffer by copying a static one-plane HUD.
.wait_clear:
        btst    #6,2(a5)
        bne.s   .wait_clear
        move.w  #$09f0,$40(a5)
        clr.w   $42(a5)
        move.l  #$ffffffff,$44(a5)
        clr.w   $64(a5)
        clr.w   $66(a5)
        move.l  #walk_hud,$50(a5)
        move.l  walk_draw_buffer(pc),$54(a5)
        move.w  #800*64+20,$58(a5)
        tst.w   solid_mode
        beq.s   .wire
        bsr     render_solid
        bsr     render_town
        bra     flip_walk
.wire:
        ; Projection can overlap the asynchronous blitter copy.
        bsr     project_vertices
.wait_lines:
        btst    #6,2(a5)
        bne.s   .wait_lines
        lea     projected_vertices,a3
        moveq   #32,d7
.horizontal_row:
        bsr     stream_render_service
        moveq   #31,d6
.horizontal:
        tst.w   4(a3)
        beq.s   .hnext
        tst.w   10(a3)
        beq.s   .hnext
        move.w  (a3),d0
        move.w  2(a3),d1
        move.w  6(a3),d2
        move.w  8(a3),d3
        movem.l d6-d7/a3,-(sp)
        bsr     draw_walk_line
        movem.l (sp)+,d6-d7/a3
.hnext:
        addq.l  #6,a3
        dbra    d6,.horizontal
        addq.l  #6,a3
        dbra    d7,.horizontal_row
        lea     projected_vertices,a3
        move.w  #1055,d7
.vertical:
        tst.w   4(a3)
        beq.s   .vnext
        tst.w   202(a3)
        beq.s   .vnext
        move.w  (a3),d0
        move.w  2(a3),d1
        move.w  198(a3),d2
        move.w  200(a3),d3
        movem.l d7/a3,-(sp)
        bsr     draw_walk_line
        movem.l (sp)+,d7/a3
.vnext:
        addq.l  #6,a3
        dbra    d7,.vertical
flip_walk:
        bsr     wait_frame
        move.l  walk_draw_buffer(pc),d0
        move.l  d0,d1
        lea     plane_pointers+2,a0
        moveq   #3,d2
.planes:
        swap    d1
        move.w  d1,(a0)
        swap    d1
        move.w  d1,4(a0)
        add.l   #8000,d1
        addq.l  #8,a0
        dbra    d2,.planes
        cmp.l   #walk_buffer_a,d0
        bne.s   .buffer_a
        move.l  #walk_buffer_b,walk_draw_buffer
        bra.s   .done
.buffer_a:
        move.l  #walk_buffer_a,walk_draw_buffer
.done:
        addq.l  #1,walk_frames
        bsr     record_frame
        rts

project_vertices:
        lea     walk_vertices,a3
        lea     projected_vertices,a4
        move.w  #1088,d7
.point:
        clr.w   4(a4)
        move.w  (a3)+,d0
        sub.w   camera_whole_x(pc),d0
        move.w  (a3)+,d1
        sub.w   camera_whole_y(pc),d1
        move.w  (a3)+,d2
        sub.w   camera_height(pc),d2
        cmp.w   #-480,d0
        blt     .next
        cmp.w   #480,d0
        bgt     .next
        cmp.w   #-480,d1
        blt     .next
        cmp.w   #480,d1
        bgt     .next
        move.w  d0,d3
        muls.w  yaw_cosine(pc),d3
        move.w  d1,d4
        muls.w  yaw_sine(pc),d4
        sub.l   d4,d3
        asr.l   #8,d3               ; Side coordinate
        muls.w  yaw_sine(pc),d0
        muls.w  yaw_cosine(pc),d1
        add.l   d1,d0
        asr.l   #8,d0               ; Forward coordinate
        move.w  d2,d1
        muls.w  pitch_cosine(pc),d1
        move.w  d0,d4
        muls.w  pitch_sine(pc),d4
        sub.l   d4,d1
        asr.l   #8,d1               ; Camera vertical
        muls.w  pitch_cosine(pc),d0
        muls.w  pitch_sine(pc),d2
        add.l   d2,d0
        asr.l   #8,d0               ; Camera depth
        cmp.w   #16,d0
        blt.s   .next
        cmp.w   fog_full(pc),d0
        bgt.s   .next
        move.w  d0,d4
        add.w   d4,d4
        cmp.w   d4,d3
        bgt.s   .next
        neg.w   d4
        cmp.w   d4,d3
        blt.s   .next
        asl.l   #7,d3
        divs.w  d0,d3
        add.w   #160,d3
        asl.l   #7,d1
        divs.w  d0,d1
        neg.w   d1
        add.w   #100,d1
        cmp.w   #-256,d1
        blt.s   .next
        cmp.w   #384,d1
        bgt.s   .next
        move.w  d3,(a4)
        move.w  d1,2(a4)
        move.w  #1,4(a4)
.next:
        addq.l  #6,a4
        dbra    d7,.point
        rts

; Bresenham with per-pixel viewport clipping and bounded projected coordinates.
draw_walk_line:
        tst.w   d0
        bge.s   .right
        tst.w   d2
        blt     .done
.right:
        cmp.w   #319,d0
        ble.s   .top
        cmp.w   #319,d2
        bgt     .done
.top:
        cmp.w   #32,d1
        bge.s   .bottom
        cmp.w   #32,d3
        blt     .done
.bottom:
        cmp.w   #173,d1
        ble.s   .setup
        cmp.w   #173,d3
        bgt     .done
.setup:
        move.w  d2,line_end_x
        move.w  d3,line_end_y
        move.w  d2,d4
        sub.w   d0,d4
        move.w  #1,line_step_x
        tst.w   d4
        bge.s   .dy
        neg.w   d4
        move.w  #-1,line_step_x
.dy:
        move.w  d3,d5
        sub.w   d1,d5
        move.w  #1,line_step_y
        tst.w   d5
        bge.s   .error
        neg.w   d5
        move.w  #-1,line_step_y
.error:
        neg.w   d5
        move.w  d4,d6
        add.w   d5,d6
        move.l  walk_draw_buffer(pc),a1
.pixel:
        cmp.w   #319,d0
        bhi.s   .advance
        cmp.w   #32,d1
        blt.s   .advance
        cmp.w   #173,d1
        bgt.s   .advance
        move.w  d1,d2
        mulu.w  #40,d2
        move.w  d0,d3
        lsr.w   #3,d3
        add.w   d3,d2
        lea     0(a1,d2.w),a0
        move.w  d0,d3
        not.w   d3
        bset    d3,(a0)
.advance:
        cmp.w   line_end_x(pc),d0
        bne.s   .step
        cmp.w   line_end_y(pc),d1
        beq.s   .done
.step:
        move.w  d6,d2
        add.w   d2,d2
        cmp.w   d5,d2
        blt.s   .ystep
        add.w   d5,d6
        add.w   line_step_x(pc),d0
.ystep:
        cmp.w   d4,d2
        bgt.s   .pixel
        add.w   d4,d6
        add.w   line_step_y(pc),d1
        bra.s   .pixel
.done:
        rts

        section code,code
walk_active: dc.w 0
last_ticks: dc.l 0
elapsed_ticks: dc.w 1
last_mouse: dc.w 0
camera_x: dc.l 836*256
camera_y: dc.l 651*256
camera_yaw: dc.w 0
camera_pitch: dc.w 0
camera_whole_x: dc.w 836
camera_whole_y: dc.w 651
camera_height: dc.w 9
yaw_sine: dc.w 0
yaw_cosine: dc.w 256
pitch_sine: dc.w 0
pitch_cosine: dc.w 256
walk_draw_buffer: dc.l 0
walk_frames: dc.l 0
line_step_x: dc.w 0
line_step_y: dc.w 0
line_end_x: dc.w 0
line_end_y: dc.w 0
keys: dcb.b 128,0
        even

        section walk_work,bss
projected_vertices: ds.w 1089*3
        section walk_screens,bss_c
walk_buffer_a: ds.b 32000
walk_buffer_b: ds.b 32000
        include "walking-assets.i"
