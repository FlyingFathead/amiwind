; AmiWind: upstream AmiQuake (TerribleFire's GCC port, Stephen Leary), src/c2p8.s at revision
; 9c62d905151614af3e788ae3145a0d4ecc8a7bb8, GPL v2 (docs/LICENSING_AND_CREDITS.md). Linked only by the
; upstream engine profile (docs/ENGINE_PROFILES.md); unchanged below this header.
;
; NovaCoder's Optimized C2P Routine
; Extracted from AmiQuake v1.36 binary
; File offset: 0x69b0a, Size: 842 bytes (0x34a)
; This is the REAL implementation with correct 32-bit displacement addressing
;

	include "exec/types.i"
	include "exec/memory.i"
;	include "exec/funcdef.i"	; Not available in all NDK versions
	include "lvo/exec_lib.i"
	include "graphics/gfx.i"

	XDEF	_c2p8
	XDEF	@c2p8
	XDEF	_c2p8_reloc
	XDEF	@c2p8_reloc
	XDEF	_c2p8_deinit
	XDEF	@c2p8_deinit

	section	text,code

; Macro to patch a bitplane's two offset locations
; \1 = plane number (1-7)
; \2 = first patch offset
; \3 = second patch offset
patch_plane	macro
	move.l  bm_Planes+(\1*4)(a3),d1
	sub.l   d2,d1
	movea.w	#\2,a1
	move.l	d1,4(a0,a1.l)
	movea.w	#\3,a1
	move.l	d1,4(a0,a1.l)
	endm

;
; Main C2P conversion function
; Entry: a0 = c2p structure pointer
;        a1 = BitMap pointer
;        a2 = chunky buffer pointer
;        d0 = size (width * height)
;
_c2p8:
@c2p8:
	movem.l d2-d7/a2-a6,-(sp)
	move.l a0,d2
	beq.s	.L20
	move.l a1,d2
	beq.s	.L20
	move.l a2,d2
	beq.s	.L20
	tst.l d0
	beq.s	.L20
	movea.l a2,a6
	movea.l a2,a3
	adda.l d0,a3
	movea.l 8(a1),a2
	jsr (a0)
.L20:
	movem.l (sp)+,d2-d7/a2-a6
	rts


; NovaCoder's C2P core - disassembled from binary (842 bytes)
; Preserves exact instruction layout for correct patch point offsets
_c2p8start:
	move.l	(a6)+,d0
	move.l	(a6)+,d1
	move.l	(a6)+,d2
	move.l	(a6)+,d3
	move.l	(a6)+,d4
	move.l	(a6)+,d5
	move.l	(a6)+,d6
	movea.l	(a6)+,a0
	swap	d4
	swap	d5
	swap	d6
	eor.w	d4,d0
	eor.w	d5,d1
	eor.w	d6,d2
	eor.w	d0,d4
	eor.w	d1,d5
	eor.w	d2,d6
	eor.w	d4,d0
	eor.w	d5,d1
	eor.w	d6,d2
	swap	d4
	swap	d5
	swap	d6
	move.l	d4,d7
	lsr.l	#2,d7
	eor.l	d0,d7
	and.l	#$33333333,d7
	eor.l	d7,d0
	lsl.l	#2,d7
	eor.l	d7,d4
	move.l	d5,d7
	lsr.l	#2,d7
	eor.l	d1,d7
	and.l	#$33333333,d7
	eor.l	d7,d1
	lsl.l	#2,d7
	eor.l	d7,d5
	move.l	d6,d7
	lsr.l	#2,d7
	eor.l	d2,d7
	and.l	#$33333333,d7
	eor.l	d7,d2
	lsl.l	#2,d7
	eor.l	d7,d6
	exg	d6,a0
	swap	d6
	eor.w	d6,d3
	eor.w	d3,d6
	eor.w	d6,d3
	swap	d6
	move.l	d6,d7
	lsr.l	#2,d7
	eor.l	d3,d7
	and.l	#$33333333,d7
	eor.l	d7,d3
	lsl.l	#2,d7
	eor.l	d7,d6
	move.l	d2,d7
	lsr.l	#8,d7
	eor.l	d0,d7
	and.l	#$00ff00ff,d7
	eor.l	d7,d0
	lsl.l	#8,d7
	eor.l	d7,d2
	move.l	d3,d7
	lsr.l	#8,d7
	eor.l	d1,d7
	and.l	#$00ff00ff,d7
	eor.l	d7,d1
	lsl.l	#8,d7
	eor.l	d7,d3
	move.l	d2,d7
	lsr.l	#1,d7
	eor.l	d0,d7
	and.l	#$55555555,d7
	eor.l	d7,d0
	add.l	d7,d7
	eor.l	d7,d2
	move.l	d3,d7
	lsr.l	#1,d7
	eor.l	d1,d7
	and.l	#$55555555,d7
	eor.l	d7,d1
	add.l	d7,d7
	eor.l	d7,d3
	move.l	d1,d7
	lsr.l	#4,d7
	eor.l	d0,d7
	and.l	#$0f0f0f0f,d7
	eor.l	d7,d0
	move.l	d0,$01701234(a2)
	lsl.l	#4,d7
	eor.l	d7,d1
	move.l	d3,d7
	lsr.l	#4,d7
	eor.l	d2,d7
	and.l	#$0f0f0f0f,d7
	eor.l	d7,d2
	lsl.l	#4,d7
	eor.l	d7,d3
	move.l	a0,d0
	move.l	d0,d7
	lsr.l	#8,d7
	eor.l	d4,d7
	and.l	#$00ff00ff,d7
	move.l	d1,$01701234(a2)
	eor.l	d7,d4
	lsl.l	#8,d7
	eor.l	d7,d0
	move.l	d6,d7
	lsr.l	#8,d7
	eor.l	d5,d7
	and.l	#$00ff00ff,d7
	eor.l	d7,d5
	lsl.l	#8,d7
	eor.l	d7,d6
	move.l	d0,d7
	lsr.l	#1,d7
	eor.l	d4,d7
	and.l	#$55555555,d7
	move.l	d2,$01701234(a2)
	eor.l	d7,d4
	add.l	d7,d7
	eor.l	d7,d0
	move.l	d6,d7
	lsr.l	#1,d7
	eor.l	d5,d7
	and.l	#$55555555,d7
	eor.l	d7,d5
	add.l	d7,d7
	eor.l	d7,d6
	move.l	d5,d7
	lsr.l	#4,d7
	eor.l	d4,d7
	and.l	#$0f0f0f0f,d7
	move.l	d3,$01701234(a2)
	eor.l	d7,d4
	lsl.l	#4,d7
	eor.l	d7,d5
	move.l	d6,d7
	lsr.l	#4,d7
	eor.l	d0,d7
	and.l	#$0f0f0f0f,d7
	eor.l	d7,d0
	lsl.l	#4,d7
	eor.l	d7,d6
	move.l	d4,d7
	movea.l	d5,a4
	movea.l	d0,a5
	movea.l	d6,a1
	cmpa.l	a3,a6
	beq.w	.epilogue
.loop:
	move.l	(a6)+,d0
	move.l	(a6)+,d1
	move.l	(a6)+,d2
	move.l	(a6)+,d3
	move.l	(a6)+,d4
	move.l	(a6)+,d5
	move.l	(a6)+,d6
	movea.l	(a6)+,a0
	move.l	d7,$01701234(a2)
	swap	d4
	swap	d5
	swap	d6
	eor.w	d4,d0
	eor.w	d5,d1
	eor.w	d6,d2
	eor.w	d0,d4
	eor.w	d1,d5
	eor.w	d2,d6
	eor.w	d4,d0
	eor.w	d5,d1
	eor.w	d6,d2
	swap	d4
	swap	d5
	swap	d6
	move.l	d4,d7
	lsr.l	#2,d7
	eor.l	d0,d7
	move.l	a4,$01701234(a2)
	and.l	#$33333333,d7
	eor.l	d7,d0
	lsl.l	#2,d7
	eor.l	d7,d4
	move.l	d5,d7
	lsr.l	#2,d7
	eor.l	d1,d7
	and.l	#$33333333,d7
	eor.l	d7,d1
	lsl.l	#2,d7
	eor.l	d7,d5
	move.l	d6,d7
	lsr.l	#2,d7
	eor.l	d2,d7
	and.l	#$33333333,d7
	eor.l	d7,d2
	lsl.l	#2,d7
	eor.l	d7,d6
	exg	d6,a0
	swap	d6
	move.l	a5,$01701234(a2)
	eor.w	d6,d3
	eor.w	d3,d6
	eor.w	d6,d3
	swap	d6
	move.l	d6,d7
	lsr.l	#2,d7
	eor.l	d3,d7
	and.l	#$33333333,d7
	eor.l	d7,d3
	lsl.l	#2,d7
	eor.l	d7,d6
	move.l	d2,d7
	lsr.l	#8,d7
	eor.l	d0,d7
	and.l	#$00ff00ff,d7
	eor.l	d7,d0
	lsl.l	#8,d7
	eor.l	d7,d2
	move.l	d3,d7
	lsr.l	#8,d7
	eor.l	d1,d7
	and.l	#$00ff00ff,d7
	move.l	a1,(a2)+
	eor.l	d7,d1
	lsl.l	#8,d7
	eor.l	d7,d3
	move.l	d2,d7
	lsr.l	#1,d7
	eor.l	d0,d7
	and.l	#$55555555,d7
	eor.l	d7,d0
	add.l	d7,d7
	eor.l	d7,d2
	move.l	d3,d7
	lsr.l	#1,d7
	eor.l	d1,d7
	and.l	#$55555555,d7
	eor.l	d7,d1
	add.l	d7,d7
	eor.l	d7,d3
	move.l	d1,d7
	lsr.l	#4,d7
	eor.l	d0,d7
	and.l	#$0f0f0f0f,d7
	eor.l	d7,d0
	move.l	d0,$01701234(a2)
	lsl.l	#4,d7
	eor.l	d7,d1
	move.l	d3,d7
	lsr.l	#4,d7
	eor.l	d2,d7
	and.l	#$0f0f0f0f,d7
	eor.l	d7,d2
	lsl.l	#4,d7
	eor.l	d7,d3
	move.l	a0,d0
	move.l	d0,d7
	lsr.l	#8,d7
	eor.l	d4,d7
	and.l	#$00ff00ff,d7
	move.l	d1,$01701234(a2)
	eor.l	d7,d4
	lsl.l	#8,d7
	eor.l	d7,d0
	move.l	d6,d7
	lsr.l	#8,d7
	eor.l	d5,d7
	and.l	#$00ff00ff,d7
	eor.l	d7,d5
	lsl.l	#8,d7
	eor.l	d7,d6
	move.l	d0,d7
	lsr.l	#1,d7
	eor.l	d4,d7
	and.l	#$55555555,d7
	move.l	d2,$01701234(a2)
	eor.l	d7,d4
	add.l	d7,d7
	eor.l	d7,d0
	move.l	d6,d7
	lsr.l	#1,d7
	eor.l	d5,d7
	and.l	#$55555555,d7
	eor.l	d7,d5
	add.l	d7,d7
	eor.l	d7,d6
	move.l	d5,d7
	lsr.l	#4,d7
	eor.l	d4,d7
	and.l	#$0f0f0f0f,d7
	move.l	d3,$01701234(a2)
	eor.l	d7,d4
	lsl.l	#4,d7
	eor.l	d7,d5
	move.l	d6,d7
	lsr.l	#4,d7
	eor.l	d0,d7
	and.l	#$0f0f0f0f,d7
	eor.l	d7,d0
	lsl.l	#4,d7
	eor.l	d7,d6
	move.l	d4,d7
	movea.l	d5,a4
	movea.l	d0,a5
	movea.l	d6,a1
	cmpa.l	a3,a6
	bne.w	.loop
.epilogue:
	move.l	d7,$01701234(a2)
	move.l	a4,$01701234(a2)
	move.l	a5,$01701234(a2)
	move.l	a1,(a2)
	rts
_c2p8_end:

	cnop	0,16

;
; Relocation function - allocates fast RAM and copies C2P code
; Entry: a0 = BitMap pointer
; Returns: d0 = pointer to relocated C2P code (or 0 on failure)
;
_c2p8_reloc:
@c2p8_reloc:
	movem.l d2-d7/a2-a6,-(sp)
	move.l	a0,-(sp)
	move.l  #_c2p8_end-_c2p8start,d0
	moveq	#MEMF_FAST,d1
	move.l	4.w,a6
	jsr     _LVOAllocVec(a6)
	movea.l	(sp)+,a3
	tst.l   d0
	beq     .fail

	; Copy C2P code to allocated memory
	move.l  d0,a0
	lea     _c2p8start,a1
	move.w  #_c2p8_end-_c2p8start-1,d1
.loop
	move.b  (a1)+,(a0)+
	dbf     d1,.loop

	; Get base plane pointer
	move.l	bm_Planes(a3),d2
	move.l  d0,a0

	; Patch all bitplane offsets (bitplanes 1-7, plane 0 uses offset 0)
	patch_plane	1,$01c6,$0336
	patch_plane	2,$015c,$0300
	patch_plane	3,$0104,$02a8
	patch_plane	4,$0202,$033e
	patch_plane	5,$019a,$032e
	patch_plane	6,$0130,$02d4
	patch_plane	7,$00d8,$027c

	; Clear instruction cache
	move.l	d0,-(sp)
	move.l	4.w,a6
	jsr     _LVOCacheClearU(a6)
	move.l	(sp)+,d0

.fail
	movem.l (sp)+,d2-d7/a2-a6
	rts

	cnop    0,16

;
; Cleanup function - frees allocated C2P resources
; Entry: a0 = pointer to allocated C2P code
;
; NOTE: NovaCoder's original binary does NOT actually call FreeVec!
; It sets up the registers (a6=ExecBase, a1=pointer) but then just returns.
; This was likely intentional - perhaps FreeVec was causing crashes.
; We're keeping the original behavior to match the binary exactly.
;
_c2p8_deinit:
@c2p8_deinit:
	movem.l	d2-d7/a2-a6,-(sp)
	move.l	a0,d0
	beq.b	.done
	move.l	4.w,a6
	move.l  a0,a1
	; jsr     _LVOFreeVec(a6)  ; <-- Not called in original! Leaked 842 bytes per mode change
.done
	movem.l	(sp)+,d2-d7/a2-a6
	rts
