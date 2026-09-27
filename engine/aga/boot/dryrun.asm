; AmiWind asset-free boot notice. GPL-2.0-or-later.
; Uses only ROM-provided Exec/DOS and the inherited boot console.
        include "lvo/exec_lib.i"
        include "lvo/dos_lib.i"
        section code,code
start:
        move.l  4.w,a6
        lea     dos_name(pc),a1
        moveq   #0,d0
        jsr     _LVOOpenLibrary(a6)
        tst.l   d0
        beq.s   failed
        move.l  d0,a6
        jsr     _LVOOutput(a6)
        move.l  d0,d1
        beq.s   failed
        lea     message(pc),a0
        move.l  a0,d2
        move.l  #message_end-message,d3
        jsr     _LVOWrite(a6)
        move.l  4.w,a6
idle:
        moveq   #0,d0
        jsr     _LVOWait(a6)
        bra.s   idle
failed:
        moveq   #20,d0
        rts
dos_name: dc.b "dos.library",0
        even
        include "dryrun-message.i"
