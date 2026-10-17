; AmiWind engine selector (AmiWindCPU). GPL-2.0-or-later.
; Created by FlyingFathead a.k.a. Horstator. Thanks to ChaosWhisperer.
;
; The game disk carries two engines: AmiWind, built for the 68040 (the
; baseline, also used on a 68060 when asked), and AmiWind060, the same source
; compiled for the 68060 (no FScc and no 64-bit MULS.L/DIVS.L, which the 68060
; leaves to its support library; it uses FINTRZ, which a 68040 does not have).
; See docs/68060.md. The startup sequence runs this after AmiWindCheck:
;
;   SYS:AmiWindCPU
;   If WARN
;     SYS:AmiWind060
;   Else
;     SYS:AmiWind
;   EndIf
;
; It returns 5 (WARN) on a 68060 when SYS:AmiWind060 is on the disk and the
; file S:AmiWind-68040 is not (that file asks for the 68040 engine on a 68060,
; e.g. to compare both); otherwise 0. A 68060 is AFF_68060 in AttnFlags, or on
; Kickstart 3.1 (which reports a 68060 as a 68040 until its library runs) the
; 68060-only PCR register. On a 68060 without a running 68060.library it
; prints a notice set apart by dashed lines and counts down 10 seconds before
; the game starts; S stops the countdown (then Return starts the game).
; Prints one line naming the CPU and the engine it picked.
        include "exec/execbase.i"
        include "exec/libraries.i"
        include "lvo/exec_lib.i"
        include "lvo/dos_lib.i"

ACCESS_READ     equ -2
COUNTDOWN       equ 10

        section code,code
cpusel_start:
        movem.l d2-d7/a2-a6,-(sp)
        moveq   #0,d7                   ; return code
        move.l  4.w,a6
        lea     dos_name(pc),a1
        moveq   #36,d0
        jsr     _LVOOpenLibrary(a6)
        move.l  d0,dos_base
        beq     .finish
        move.l  d0,a6
        jsr     _LVOOutput(a6)
        move.l  d0,output_handle
        jsr     _LVOInput(a6)
        move.l  d0,input_handle
        ; which CPU
        move.l  4.w,a6
        move.w  AttnFlags(a6),d0
        btst    #AFB_68060,d0
        bne.s   .is060
        btst    #AFB_68040,d0
        beq     .not060
        bsr     probe_68060
        tst.l   d0
        beq     .not060
.is060:
        ; a running 68060.library?
        bsr     find_fpu_library
        tst.l   d0
        beq.s   .nolib
        lea     fpu_name_060(pc),a0
        cmp.l   a0,a1
        beq.s   .haslib
.nolib: bsr     notice
.haslib:
        ; the 68060 engine, unless asked for the 68040 one
        lea     forced_name(pc),a0
        bsr     exists
        tst.l   d0
        bne.s   .forced
        lea     engine060_name(pc),a0
        bsr     exists
        tst.l   d0
        beq.s   .no060
        lea     picked_060(pc),a0
        bsr     puts
        moveq   #5,d7
        bra.s   .close
.forced:
        lea     picked_forced(pc),a0
        bsr     puts
        bra.s   .close
.no060:
        lea     picked_missing(pc),a0
        bsr     puts
        bra.s   .close
.not060:
        lea     picked_040(pc),a0
        bsr     puts
.close:
        move.l  4.w,a6
        move.l  dos_base,a1
        jsr     _LVOCloseLibrary(a6)
.finish:
        move.l  d7,d0
        movem.l (sp)+,d2-d7/a2-a6
        rts

; d0 = 1 when the file named at a0 exists
exists:
        movem.l d1-d2/a0-a1/a6,-(sp)
        move.l  dos_base,a6
        move.l  a0,d1
        moveq   #ACCESS_READ,d2
        jsr     _LVOLock(a6)
        tst.l   d0
        beq.s   .no
        move.l  d0,d1
        jsr     _LVOUnLock(a6)
        moveq   #1,d0
.no:    movem.l (sp)+,d1-d2/a0-a1/a6
        rts

; The notice with a countdown; S stops it, then Return goes on.
notice:
        movem.l d0-d4/a0-a1/a6,-(sp)
        lea     notice_text(pc),a0
        bsr     puts
        move.l  dos_base,a6
        move.l  input_handle,d1
        beq     .done
        moveq   #1,d2
        jsr     _LVOSetMode(a6)         ; raw: single keys, no Return needed
        moveq   #COUNTDOWN,d4
.tick:  move.l  d4,d0
        bsr     put_count
        move.l  input_handle,d1
        move.l  #1000000,d2
        jsr     _LVOWaitForChar(a6)
        tst.l   d0
        beq.s   .next
        move.l  input_handle,d1
        lea     key,a0
        move.l  a0,d2
        moveq   #1,d3
        jsr     _LVORead(a6)
        move.b  key,d0
        or.b    #$20,d0
        cmp.b   #'s',d0
        beq.s   .stopped
.next:  subq.l  #1,d4
        bne.s   .tick
        bra.s   .restore
.stopped:
        lea     stopped_text(pc),a0
        bsr     puts
.wait:  move.l  input_handle,d1
        lea     key,a0
        move.l  a0,d2
        moveq   #1,d3
        jsr     _LVORead(a6)
        tst.l   d0
        ble.s   .restore
        move.b  key,d0
        cmp.b   #13,d0
        beq.s   .restore
        cmp.b   #10,d0
        bne.s   .wait
.restore:
        move.l  input_handle,d1
        moveq   #0,d2
        jsr     _LVOSetMode(a6)
        lea     go_text(pc),a0
        bsr     puts
.done:  movem.l (sp)+,d0-d4/a0-a1/a6
        rts

; Print " N " at the line start (d0 = 1..99).
put_count:
        movem.l d0-d1/a0,-(sp)
        lea     count_text+3,a0
        divu.w  #10,d0
        move.l  d0,d1
        swap    d1
        add.b   #'0',d1
        move.b  d1,(a0)
        subq.l  #1,a0
        tst.w   d0
        bne.s   .tens
        move.b  #' ',(a0)
        bra.s   .out
.tens:  add.b   #'0',d0
        move.b  d0,(a0)
.out:   lea     count_text,a0
        bsr     puts
        movem.l (sp)+,d0-d1/a0
        rts

puts:
        movem.l d0-d3/a0-a1/a6,-(sp)
        move.l  output_handle,d1
        beq.s   .done
        move.l  a0,d2
        moveq   #0,d3
.length:
        tst.b   (a0)+
        beq.s   .write
        addq.l  #1,d3
        bra.s   .length
.write:
        move.l  dos_base,a6
        jsr     _LVOWrite(a6)
.done:
        movem.l (sp)+,d0-d3/a0-a1/a6
        rts

        include "fpu_support_inc.asm"

dos_name:       dc.b "dos.library",0
forced_name:    dc.b "S:AmiWind-68040",0
engine060_name: dc.b "SYS:AmiWind060",0
; Each line fits the boot console (48 columns, as AmiWindCheck's lines).
picked_040:     dc.b "Engine: AmiWind (68040 build)",10,0
picked_060:     dc.b "Engine: AmiWind060 (68060 build, CPU 68060)",10,0
picked_forced:  dc.b "Engine: AmiWind (68040 build, S:AmiWind-68040)",10,0
picked_missing: dc.b "Engine: AmiWind (68040 build; no AmiWind060)",10,0
notice_text:
        dc.b    "------------------------------------------------",10
        dc.b    "68060 found, but no 68060.library is running:",10
        dc.b    "the game stops at the first instruction the",10
        dc.b    "68060 leaves to that library. Copy your card's",10
        dc.b    "68060.library to LIBS: (docs: FPU support",10
        dc.b    "library) or build with --amiga-libs.",10
        dc.b    "Press S to stop the countdown.",10
        dc.b    "------------------------------------------------",10,0
stopped_text:   dc.b 10,"Stopped. Press Return to start the game.",10,0
go_text:        dc.b 10,0
        even
        section storage,data
count_text:     dc.b 13," 10 s ",0
        section storage2,bss
dos_base:       ds.l 1
output_handle:  ds.l 1
input_handle:   ds.l 1
key:            ds.b 2
