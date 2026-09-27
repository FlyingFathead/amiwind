; Eight-view original-model impostors, back-to-front over terrain horizons.
; 68000, four-pixel columns, four OCS bitplanes. All scenery is resident.
        section code,code
render_town:
        clr.w   town_visible_count
        lea     town_refs,a4
        move.w  #TOWN_COUNT-1,d7
.reference:
        move.w  (a4),d0
        sub.w   camera_whole_x,d0
        move.w  2(a4),d1
        sub.w   camera_whole_y,d1
        move.w  d0,d2
        muls.w  yaw_sine,d2
        move.w  d1,d3
        muls.w  yaw_cosine,d3
        add.l   d3,d2
        asr.l   #8,d2
        cmp.w   #8,d2
        blt     .next
        cmp.w   fog_full,d2
        bge     .next
        muls.w  yaw_cosine,d0
        muls.w  yaw_sine,d1
        sub.l   d1,d0
        asr.l   #8,d0
        move.w  d0,d1
        bpl.s   .positive
        neg.w   d1
.positive:
        move.w  d2,d3
        lsr.w   #2,d3
        add.w   d2,d3
        move.w  8(a4),d4
        lsr.w   #1,d4
        add.w   d4,d3
        cmp.w   d3,d1
        bgt.s   .next
        ; Insertion sort of visible records: depth, side, reference pointer.
        move.w  town_visible_count,d4
        cmp.w   #TOWN_COUNT,d4
        bhs.s   .next
        addq.w  #1,town_visible_count
        lsl.w   #3,d4
        lea     town_visible,a0
        adda.w  d4,a0
.sort:
        tst.w   d4
        beq.s   .insert
        cmp.w   -8(a0),d2
        ble.s   .insert
        move.l  -8(a0),(a0)
        move.l  -4(a0),4(a0)
        subq.l  #8,a0
        subq.w  #8,d4
        bra.s   .sort
.insert:
        move.w  d2,(a0)
        move.w  d0,2(a0)
        move.l  a4,4(a0)
.next:
        adda.w  #16,a4
        dbra    d7,.reference
        move.w  town_visible_count,d0
        add.l   #1,town_frame_count
        cmp.w   town_visible_max,d0
        bls.s   .counted
        move.w  d0,town_visible_max
.counted:
        subq.w  #1,d0
        bmi.s   .done
        move.w  d0,town_draw_remaining
        move.l  #town_visible,town_draw_cursor
.draw:
        bsr     stream_render_service
        move.l  town_draw_cursor,a0
        move.w  (a0)+,d6
        move.w  (a0)+,d7
        move.l  (a0)+,a4
        move.l  a0,town_draw_cursor
        bsr     town_draw_object
        subq.w  #1,town_draw_remaining
        bpl.s   .draw
.done:
        rts

; d6 forward distance, d7 side, a4 reference. Pitch matches terrain horizon.
town_draw_object:
        move.w  d6,town_depth
        move.w  d7,d0
        ext.l   d0
        asl.l   #7,d0
        divs.w  d6,d0
        add.w   #160,d0
        moveq   #0,d1
        move.w  8(a4),d1
        lsl.l   #7,d1
        divu.w  d6,d1
        and.l   #$ffff,d1
        cmp.w   #4,d1
        blo     .done
        move.w  d1,town_screen_width
        lsr.w   #1,d1
        sub.w   d1,d0
        move.w  d0,town_screen_left
        move.w  6(a4),d0
        sub.w   camera_height,d0
        ext.l   d0
        asl.l   #7,d0
        divs.w  d6,d0
        neg.w   d0
        add.w   solid_horizon,d0
        move.w  d0,town_screen_top
        moveq   #0,d1
        move.w  6(a4),d1
        sub.w   4(a4),d1
        lsl.l   #7,d1
        divu.w  d6,d1
        and.l   #$ffff,d1
        beq     .done
        move.w  d0,d2
        add.w   d1,d2
        cmp.w   #32,d2
        ble     .done
        cmp.w   #174,d0
        bge     .done
        ; 65 source-row edges, accumulated Q6: no divide inside the run loop.
        ext.l   d0
        asl.l   #6,d0
        lea     town_yedges,a0
        moveq   #64,d2
.edge:
        move.l  d0,d3
        asr.l   #6,d3
        move.w  d3,(a0)+
        add.l   d1,d0
        dbra    d2,.edge
        ; Closest of eight world camera-to-object azimuths, then local rotation.
        move.w  (a4),d0
        sub.w   camera_whole_x,d0
        move.w  2(a4),d1
        sub.w   camera_whole_y,d1
        bsr     town_azimuth
        add.w   10(a4),d0
        add.w   #16,d0
        and.w   #224,d0
        lsr.w   #3,d0             ; view * 4
        move.l  12(a4),a0
        move.l  0(a0,d0.w),town_image
        ; Horizon at the last terrain slice no farther than the object plane.
        move.w  town_depth,d0
        sub.w   #16,d0
        bpl.s   .history
        moveq   #-8,d0
.history:
        asr.w   #3,d0
        addq.w  #1,d0
        mulu.w  #160,d0
        lea     terrain_horizons,a0
        adda.l  d0,a0
        move.l  a0,town_horizon_row
        move.w  town_screen_left,d0
        add.w   town_screen_width,d0
        addq.w  #1,d0
        asr.w   #2,d0
        cmp.w   #80,d0
        ble.s   .right
        moveq   #80,d0
.right:
        move.w  d0,town_column_end
        move.w  town_screen_left,d0
        asr.w   #2,d0
        bpl.s   .left
        moveq   #0,d0
.left:
        move.w  d0,town_column
.column:
        move.w  town_column,d2
        cmp.w   town_column_end,d2
        bge     .done
        move.w  d2,d0
        add.w   d0,d0
        move.l  town_horizon_row,a0
        move.w  0(a0,d0.w),town_column_bottom
        move.w  d2,d0
        lsl.w   #2,d0
        addq.w  #2,d0             ; four-pixel sample centre
        sub.w   town_screen_left,d0
        bmi     .next_column
        cmp.w   town_screen_width,d0
        bhs     .next_column
        and.l   #$ffff,d0
        lsl.l   #5,d0
        divu.w  town_screen_width,d0
        and.w   #31,d0
        add.w   d0,d0
        move.l  town_image,a0
        moveq   #0,d1
        move.w  0(a0,d0.w),d1
        adda.l  d1,a0
        move.l  a0,town_run
.run:
        move.l  town_run,a0
        moveq   #0,d0
        move.b  (a0)+,d0
        cmp.w   #255,d0
        beq.s   .next_column
        moveq   #0,d1
        move.b  (a0)+,d1
        moveq   #0,d3
        move.b  (a0)+,d3
        move.l  a0,town_run
        add.w   d0,d0
        add.w   d1,d1
        lea     town_yedges,a0
        move.w  0(a0,d0.w),d0
        move.w  0(a0,d1.w),d1
        cmp.w   #32,d0
        bge.s   .clip_bottom
        moveq   #32,d0
.clip_bottom:
        cmp.w   town_column_bottom,d1
        ble.s   .clipped
        move.w  town_column_bottom,d1
.clipped:
        cmp.w   d1,d0
        bge.s   .run
        move.w  town_depth,d4
        cmp.w   fog_start,d4
        blo.s   .colour
        lea     town_fog_map,a0
        move.b  0(a0,d3.w),d3
.colour:
        move.w  town_column,d2
        bsr     town_span
        addq.l  #1,town_span_count
        bra.s   .run
.next_column:
        addq.w  #1,town_column
        bsr     stream_render_service
        bra     .column
.done:
        rts

; dx=d0, dy=d1; return angle in 256-turn units. Quantized atan octants.
town_azimuth:
        move.w  d0,d2
        move.w  d1,d3
        bpl.s   .absx
        neg.w   d3
.absx:
        tst.w   d2
        bpl.s   .ratio
        neg.w   d2
.ratio:
        move.w  d2,d4
        mulu.w  #106,d4
        moveq   #0,d5
        move.w  d3,d5
        lsl.l   #8,d5
        cmp.l   d5,d4
        bhi.s   .east
        move.w  d3,d4
        mulu.w  #106,d4
        moveq   #0,d5
        move.w  d2,d5
        lsl.l   #8,d5
        cmp.l   d5,d4
        bhi.s   .north
        moveq   #32,d4
        bra.s   .quadrant
.east:
        moveq   #64,d4
        bra.s   .quadrant
.north:
        moveq   #0,d4
.quadrant:
        tst.w   d1
        bpl.s   .west
        neg.w   d4
        add.w   #128,d4
.west:
        tst.w   d0
        bpl.s   .angle
        neg.w   d4
.angle:
        move.w  d4,d0
        and.w   #255,d0
        rts

; Replace a four-pixel vertical span; terrain and farther scenery already exist.
town_span:
        sub.w   d0,d1
        subq.w  #1,d1
        mulu.w  #40,d0
        move.w  d2,d4
        lsr.w   #1,d4
        add.w   d4,d0
        move.l  walk_draw_buffer,a0
        adda.w  d0,a0
        and.w   #1,d2
        lea     column_masks,a1
        move.b  0(a1,d2.w),d4
        not.b   d4
        lsl.w   #2,d2
        lsl.w   #3,d3
        add.w   d2,d3
        lea     town_inks,a1
        move.l  0(a1,d3.w),d5
.row:
        and.b   d4,(a0)
        or.b    d5,(a0)
        ror.l   #8,d5
        and.b   d4,8000(a0)
        or.b    d5,8000(a0)
        ror.l   #8,d5
        and.b   d4,16000(a0)
        or.b    d5,16000(a0)
        ror.l   #8,d5
        and.b   d4,24000(a0)
        or.b    d5,24000(a0)
        ror.l   #8,d5
        adda.w  #40,a0
        dbra    d1,.row
        rts

; Q8 displacement d0,d1. Substeps <=32 world units prevent wall tunnelling.
town_move:
        movem.l d2-d7/a0-a4,-(sp)
        move.l  d0,d2
        bpl.s   .ay
        neg.l   d2
.ay:
        move.l  d1,d3
        bpl.s   .max
        neg.l   d3
.max:
        cmp.l   d3,d2
        bhs.s   .steps
        move.l  d3,d2
.steps:
        lsr.l   #8,d2
        lsr.w   #1,d2
        addq.w  #1,d2
        move.w  d2,town_move_steps
        divs.w  d2,d0
        divs.w  d2,d1
        ext.l   d0
        ext.l   d1
        move.l  d0,town_move_x
        move.l  d1,town_move_y
.step:
        move.l  camera_x,d6
        add.l   town_move_x,d6
        move.l  camera_y,d7
        bsr     town_blocked
        tst.w   d0
        bne.s   .y
        move.l  d6,camera_x
.y:
        move.l  camera_x,d6
        move.l  camera_y,d7
        add.l   town_move_y,d7
        bsr     town_blocked
        tst.w   d0
        bne.s   .next
        move.l  d7,camera_y
.next:
        subq.w  #1,town_move_steps
        bne.s   .step
        movem.l (sp)+,d2-d7/a0-a4
        rts

; Test candidate Q8 x=d6,y=d7 against expanded upright building footprints.
town_blocked:
        lea     town_boxes,a0
        move.w  #TOWN_BOXES-1,d5
.box:
        move.l  d6,d1
        asr.l   #8,d1
        sub.w   (a0),d1
        move.l  d7,d2
        asr.l   #8,d2
        sub.w   2(a0),d2
        move.w  d1,d3
        muls.w  8(a0),d3
        move.w  d2,d4
        muls.w  10(a0),d4
        sub.l   d4,d3
        asr.l   #8,d3
        bpl.s   .x
        neg.w   d3
.x:
        cmp.w   4(a0),d3
        bgt.s   .next
        muls.w  10(a0),d1
        muls.w  8(a0),d2
        add.l   d2,d1
        asr.l   #8,d1
        bpl.s   .y
        neg.w   d1
.y:
        cmp.w   6(a0),d1
        bgt.s   .next
        addq.l  #1,town_collision_hits
        moveq   #1,d0
        rts
.next:
        adda.w  #12,a0
        dbra    d5,.box
        moveq   #0,d0
        rts

        section town_state,data
town_fog_map: dc.b 0,1,2,3,4,5,6,7,4,4,4,4,13,15,4,15
town_visible_count: dc.w 0
town_visible_max: dc.w 0
town_frame_count: dc.l 0
town_span_count: dc.l 0
town_collision_hits: dc.l 0
town_draw_cursor: dc.l 0
town_draw_remaining: dc.w 0
town_depth: dc.w 0
town_image: dc.l 0
town_run: dc.l 0
town_screen_width: dc.w 0
town_screen_left: dc.w 0
town_screen_top: dc.w 0
town_horizon_row: dc.l 0
town_column: dc.w 0
town_column_end: dc.w 0
town_column_bottom: dc.w 0
town_move_x: dc.l 0
town_move_y: dc.l 0
town_move_steps: dc.w 0
        section town_work,bss
town_visible: ds.b TOWN_COUNT*8
town_yedges: ds.w 65
        include "town-assets.i"
