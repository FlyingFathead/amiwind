; awtraps: count the instructions the CPU traps to its support library, and the frames shown.
; GPL-2.0-or-later. Created by FlyingFathead a.k.a. Horstator. Thanks to ChaosWhisperer.
; An asset-free measurement tool for the 68060 work (docs/68060.md, ENGINE-060-FSCC-41); not
; part of the game disk.
;
;   awtraps            install (once; after the CPU library has installed its handlers):
;                      a counting entry in front of the exception vectors a 68060 or 68040
;                      support library handles (11 F-line: unimplemented floating-point
;                      instructions, including FScc/FDBcc/FTRAPcc on a 68060; 55 unimplemented
;                      data type; 60 unimplemented effective address; 61 unimplemented integer
;                      instruction), each passing on to the handler that was there, plus a
;                      counter in front of intuition's ChangeScreenBuffer (one call per frame
;                      the engine shows). Trap addresses are counted in a table (1,024 slots).
;                      The block stays in memory, published as the semaphore "AmiWindTraps".
;   awtraps reset      zero the counters and the table.
;   awtraps watch FILE every second write FILE (default AWCTL:traps.txt): the counters and the
;                      table as hex text, ending with "end". Ctrl-C stops it.
;   awtraps show       print the counters.
; Traps per frame = difference of the trap counts / difference of "frames" between two
; snapshots. The counts include every task's traps (the engine is the only busy one).
        machine 68040
        include "exec/execbase.i"
        include "lvo/exec_lib.i"
        include "lvo/dos_lib.i"
        include "lvo/intuition_lib.i"

MEMF_PUBLIC_CLEAR equ $10001
MODE_NEWFILE    equ 1006
SIGBREAKF_CTRL_C equ $1000
HSLOTS          equ 1024            ; trap address table slots (power of two)
HMASK           equ HSLOTS-1
PROBES          equ 16
NVEC            equ 4
SS_SIZE         equ 46

        section code,code
start:
        movem.l d2-d7/a2-a6,-(sp)
        move.l  a0,arg_ptr
        move.l  d0,arg_len
        moveq   #20,d7
        move.l  4.w,a6
        lea     dos_name(pc),a1
        moveq   #36,d0
        jsr     _LVOOpenLibrary(a6)
        move.l  d0,dos_base
        beq     exit_now
        move.l  d0,a6
        jsr     _LVOOutput(a6)
        move.l  d0,out_handle
        bsr     find_block
        move.l  d0,a2                   ; a2 = installed block or 0
        bsr     first_word              ; d0 = first character of the argument (lower case) or 0
        cmp.b   #'w',d0
        beq     cmd_watch
        cmp.b   #'r',d0
        beq     cmd_reset
        cmp.b   #'s',d0
        beq     cmd_show
        ; install
        move.l  a2,d0
        beq.s   .install
        lea     msg_already(pc),a0
        bsr     puts
        moveq   #0,d7
        bra     close_exit
.install:
        bsr     install
        move.l  d0,d7
close_exit:
        move.l  4.w,a6
        move.l  dos_base,a1
        jsr     _LVOCloseLibrary(a6)
exit_now:
        move.l  d7,d0
        movem.l (sp)+,d2-d7/a2-a6
        rts

; d0 = the installed block (its semaphore) or 0
find_block:
        movem.l a1/a6,-(sp)
        move.l  4.w,a6
        jsr     _LVOForbid(a6)
        lea     sem_name(pc),a1
        jsr     _LVOFindSemaphore(a6)
        move.l  d0,-(sp)
        jsr     _LVOPermit(a6)
        move.l  (sp)+,d0
        movem.l (sp)+,a1/a6
        rts

; d0 = first non-blank character of the argument line, lower-cased, or 0; a0 = there
first_word:
        move.l  arg_ptr,a0
        move.l  arg_len,d1
        moveq   #0,d0
.skip:  subq.l  #1,d1
        bmi.s   .none
        move.b  (a0)+,d0
        cmp.b   #' ',d0
        beq.s   .skip
        cmp.b   #9,d0
        beq.s   .skip
        cmp.b   #10,d0
        beq.s   .none
        subq.l  #1,a0
        or.b    #$20,d0
        rts
.none:  moveq   #0,d0
        rts

; Install the block: returns d0 = 0 (done) or 20.
install:
        movem.l d2-d3/a2-a3/a6,-(sp)
        move.l  4.w,a6
        move.l  #res_end-res_blk,d0
        move.l  #MEMF_PUBLIC_CLEAR,d1
        jsr     _LVOAllocMem(a6)
        tst.l   d0
        beq     .nomem
        move.l  d0,a2                   ; a2 = the copy
        lea     res_blk(pc),a0
        move.l  a2,a1
        move.l  #res_end-res_blk,d0
        jsr     _LVOCopyMem(a6)
        jsr     _LVOCacheClearU(a6)
        ; the vector base (VBR) in supervisor mode
        lea     get_vbr(pc),a5
        jsr     _LVOSupervisor(a6)
        move.l  d0,a3                   ; a3 = VBR
        move.l  d0,vbr_value
        jsr     _LVODisable(a6)
        lea     vec_offsets(pc),a0
        moveq   #NVEC-1,d2
        moveq   #0,d3
.vec:   move.w  (a0)+,d0                ; vector offset
        move.l  (a3,d0.w),d1            ; the handler there now (the CPU library's)
        lea     o_vec-res_blk(a2),a1
        move.l  d1,(a1,d3.w)
        lea     stub_table-res_blk(a2),a1
        move.l  (a1,d3.w),d1            ; stub offset in the block
        add.l   a2,d1
        move.l  d1,(a3,d0.w)
        addq.w  #4,d3
        dbf     d2,.vec
        jsr     _LVOEnable(a6)
        jsr     _LVOCacheClearU(a6)
        ; intuition's ChangeScreenBuffer: one call per frame shown
        lea     intuition_name(pc),a1
        moveq   #39,d0
        jsr     _LVOOpenLibrary(a6)     ; kept open: the patch stays
        tst.l   d0
        beq.s   .nointuition
        move.l  d0,a1
        jsr     _LVOForbid(a6)
        move.w  #_LVOChangeScreenBuffer,a0
        lea     csb_stub-res_blk(a2),a3
        move.l  a3,d0
        jsr     _LVOSetFunction(a6)
        lea     o_csb-res_blk(a2),a0
        move.l  d0,(a0)
        jsr     _LVOPermit(a6)
.nointuition:
        lea     sem_name_copy-res_blk(a2),a0
        move.l  a0,10(a2)               ; ln_Name
        move.l  a2,a1
        jsr     _LVOAddSemaphore(a6)
        lea     vbr_value,a1
        lea     msg_installed(pc),a0
        bsr     report
        moveq   #0,d0
        bra.s   .done
.nomem: lea     msg_nomem(pc),a0
        bsr     puts
        moveq   #20,d0
.done:  movem.l (sp)+,d2-d3/a2-a3/a6
        rts

get_vbr:
        movec   vbr,d0
        rte

cmd_reset:
        move.l  a2,d0
        beq     not_installed
        move.l  4.w,a6
        jsr     _LVOForbid(a6)
        lea     d_counts-res_blk(a2),a0
        move.w  #(res_end-d_counts)/4-1,d0
.clr:   clr.l   (a0)+
        dbf     d0,.clr
        jsr     _LVOPermit(a6)
        lea     msg_reset(pc),a0
        bsr     puts
        moveq   #0,d7
        bra     close_exit

cmd_show:
        move.l  a2,d0
        beq     not_installed
        bsr     snapshot
        lea     snap,a1
        lea     msg_show(pc),a0
        bsr     report
        moveq   #0,d7
        bra     close_exit

not_installed:
        lea     msg_not_installed(pc),a0
        bsr     puts
        moveq   #10,d7
        bra     close_exit

; Copy counters and table into snap (under Forbid).
snapshot:
        movem.l d0-d1/a0-a1/a6,-(sp)
        move.l  4.w,a6
        jsr     _LVOForbid(a6)
        lea     d_counts-res_blk(a2),a0
        lea     snap,a1
        move.l  #res_end-d_counts,d0
        jsr     _LVOCopyMem(a6)
        jsr     _LVOPermit(a6)
        movem.l (sp)+,d0-d1/a0-a1/a6
        rts

cmd_watch:
        move.l  a2,d0
        beq     not_installed
        ; file name: the second word, else the default
        lea     default_file(pc),a3
        move.l  a0,a1                   ; a0 = first word
.word:  move.b  (a1)+,d0
        beq.s   .named
        cmp.b   #' ',d0
        beq.s   .space
        cmp.b   #10,d0
        beq.s   .named
        bra.s   .word
.space: cmp.b   #' ',(a1)
        bne.s   .start
        addq.l  #1,a1
        bra.s   .space
.start: cmp.b   #10,(a1)
        beq.s   .named
        tst.b   (a1)
        beq.s   .named
        lea     file_name,a0
        move.l  a0,a3
.copy:  move.b  (a1)+,d0
        cmp.b   #' ',d0
        bls.s   .end
        move.b  d0,(a0)+
        bra.s   .copy
.end:   clr.b   (a0)
.named: move.l  a3,file_ptr
        lea     msg_watch(pc),a0
        lea     file_ptr,a1
        bsr     report
.loop:  bsr     snapshot
        addq.l  #1,snap_seq
        bsr     write_snapshot
        move.l  dos_base,a6
        moveq   #50,d1
        jsr     _LVODelay(a6)
        move.l  4.w,a6
        moveq   #0,d0
        move.l  #SIGBREAKF_CTRL_C,d1
        jsr     _LVOSetSignal(a6)
        btst    #12,d0
        beq.s   .loop
        moveq   #0,d7
        bra     close_exit

; Format snap as text and write it to the file.
write_snapshot:
        movem.l d2-d4/a2-a4/a6,-(sp)
        lea     out_text,a4                 ; output position
        lea     snap_seq,a1
        lea     fmt_head(pc),a0
        bsr     format
        lea     snap,a1
        lea     fmt_counts(pc),a0
        bsr     format
        lea     snap+(d_hist-d_counts),a2
        move.w  #HSLOTS-1,d4
.h:     tst.l   (a2)
        beq.s   .next
        move.l  a2,a1
        lea     fmt_hist(pc),a0
        bsr     format
.next:  addq.l  #8,a2
        dbf     d4,.h
        lea     fmt_end(pc),a0
        sub.l   a1,a1
        bsr     format
        move.l  dos_base,a6
        move.l  file_ptr,d1
        move.l  #MODE_NEWFILE,d2
        jsr     _LVOOpen(a6)
        move.l  d0,d4
        beq.s   .fail
        move.l  d4,d1
        lea     out_text,a0
        move.l  a0,d2
        move.l  a4,d3
        sub.l   a0,d3
        jsr     _LVOWrite(a6)
        move.l  d4,d1
        jsr     _LVOClose(a6)
.fail:  movem.l (sp)+,d2-d4/a2-a4/a6
        rts

; RawDoFmt a0 with the data at a1, appended at a4 (a4 advances, no terminating zero kept)
format:
        movem.l d0-d1/a0-a3/a6,-(sp)
        move.l  4.w,a6
        lea     put_char(pc),a2
        move.l  a4,a3
        jsr     _LVORawDoFmt(a6)
        movem.l (sp)+,d0-d1/a0-a3/a6
.len:   tst.b   (a4)+
        bne.s   .len
        subq.l  #1,a4
        rts

; Format a0 with a1 and print it.
report:
        movem.l d0-d1/a0-a4/a6,-(sp)
        lea     out_text,a4
        bsr     format
        lea     out_text,a0
        bsr     puts
        movem.l (sp)+,d0-d1/a0-a4/a6
        rts

put_char:
        move.b  d0,(a3)+
        rts

puts:
        movem.l d0-d3/a0-a1/a6,-(sp)
        move.l  out_handle,d1
        beq.s   .done
        move.l  a0,d2
        moveq   #0,d3
.l:     tst.b   (a0)+
        beq.s   .w
        addq.l  #1,d3
        bra.s   .l
.w:     move.l  dos_base,a6
        jsr     _LVOWrite(a6)
.done:  movem.l (sp)+,d0-d3/a0-a1/a6
        rts

vec_offsets:    dc.w 11*4,55*4,60*4,61*4

dos_name:       dc.b "dos.library",0
intuition_name: dc.b "intuition.library",0
sem_name:       dc.b "AmiWindTraps",0
default_file:   dc.b "AWCTL:traps.txt",0
msg_already:    dc.b "awtraps: already installed",10,0
msg_nomem:      dc.b "awtraps: no memory",10,0
msg_not_installed: dc.b "awtraps: not installed (run awtraps first)",10,0
msg_reset:      dc.b "awtraps: counters reset",10,0
msg_installed:  dc.b "awtraps: installed, vectors 11 55 60 61 at VBR $%08lx, frames from ChangeScreenBuffer",10,0
msg_watch:      dc.b "awtraps: writing %s every second",10,0
msg_show:       dc.b "awtraps: frames %ld fline %ld unimpdata %ld unimpea %ld unimpint %ld",10,0
fmt_head:       dc.b "awtraps 1",10,"seq %ld",10,0
fmt_counts:     dc.b "frames %ld",10,"v11 %ld",10,"v55 %ld",10,"v60 %ld",10,"v61 %ld",10,"overflow %ld",10,0
fmt_hist:       dc.b "pc %08lx %ld",10,0
fmt_end:        dc.b "end",10,0
        even

; ---- the resident block: copied to public memory; everything in it is position independent ----
        cnop    0,4
res_blk:
d_sem:          ds.b SS_SIZE            ; SignalSemaphore (named in the copy)
        cnop    0,4
o_vec:          ds.l NVEC               ; the handlers that were there (11, 55, 60, 61)
o_csb:          ds.l 1                  ; intuition's ChangeScreenBuffer
stub_table:     dc.l stub11-res_blk,stub55-res_blk,stub60-res_blk,stub61-res_blk
sem_name_copy:  dc.b "AmiWindTraps",0
        cnop    0,4
stub11: movem.l d0-d2/a0-a1,-(sp)
        moveq   #0,d1
        bsr.s   count
        movem.l (sp)+,d0-d2/a0-a1
        move.l  o_vec+0(pc),-(sp)
        rts
stub55: movem.l d0-d2/a0-a1,-(sp)
        moveq   #1,d1
        bsr.s   count
        movem.l (sp)+,d0-d2/a0-a1
        move.l  o_vec+4(pc),-(sp)
        rts
stub60: movem.l d0-d2/a0-a1,-(sp)
        moveq   #2,d1
        bsr.s   count
        movem.l (sp)+,d0-d2/a0-a1
        move.l  o_vec+8(pc),-(sp)
        rts
stub61: movem.l d0-d2/a0-a1,-(sp)
        moveq   #3,d1
        bsr.s   count
        movem.l (sp)+,d0-d2/a0-a1
        move.l  o_vec+12(pc),-(sp)
        rts
; d1 = counter index; the exception frame's PC is at 4 (return) + 20 (registers) + 2 (SR)
count:  lea     d_vec(pc),a1
        add.w   d1,d1
        add.w   d1,d1
        addq.l  #1,(a1,d1.w)
        move.l  26(sp),d0
        lea     d_hist(pc),a1
        move.l  d0,d1
        lsr.l   #1,d1
        and.l   #HMASK,d1
        moveq   #PROBES-1,d2
.probe: lea     (a1,d1.l*8),a0
        cmp.l   (a0),d0
        beq.s   .hit
        tst.l   (a0)
        beq.s   .new
        addq.l  #1,d1
        and.l   #HMASK,d1
        dbf     d2,.probe
        lea     d_over(pc),a1
        addq.l  #1,(a1)
        rts
.new:   move.l  d0,(a0)
.hit:   addq.l  #1,4(a0)
        rts
csb_stub:
        move.l  a0,-(sp)
        lea     d_frames(pc),a0
        addq.l  #1,(a0)
        move.l  (sp)+,a0
        move.l  o_csb(pc),-(sp)
        rts
        cnop    0,4
d_counts:
d_frames:       ds.l 1
d_vec:          ds.l NVEC
d_over:         ds.l 1
d_hist:         ds.l HSLOTS*2           ; (address, count)
res_end:

        section data,bss
dos_base:       ds.l 1
out_handle:     ds.l 1
arg_ptr:        ds.l 1
arg_len:        ds.l 1
file_ptr:       ds.l 1
vbr_value:      ds.l 1
snap_seq:            ds.l 1
file_name:      ds.b 256
snap:           ds.b res_end-d_counts
out_text:           ds.b 32768
