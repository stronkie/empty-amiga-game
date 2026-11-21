; stub.s - Stronkie Soft unpacker, the first hunk of a packed game file.
;
; LoadSeg (DOS, or the game's own loader) has loaded the game's hunks as
; usual, but each packed hunk holds its packed data at its start and no
; relocation table.  This stub unpacks every packed hunk in place, applies
; all the relocations, clears the caches and jumps to the game's first hunk
; with the registers it was started with (d0/a0 = arguments), so the game
; returns straight to whoever started it.
;
; Table (after the code): word number of hunks, then per hunk:
;   word mode (0 = loaded as it is, 1 = packed), long packed size (x4),
;   long unpacked size, long alloc size (x4)
; then the relocations: word source hunk ($ffff = end), word target hunk,
;   long count, count offset codes (byte d>0: offset += 2*d, byte 0 + long:
;   offset = that long), padded to an even address.

	section	stub,code

start:
	movem.l	d0-d7/a0-a6,-(sp)
	lea	bases(pc),a4
	lea	Table(pc),a5
	move.w	(a5)+,d6
	move.w	d6,d5
	move.l	a4,a3
	move.w	d5,d6
	subq.w	#1,d6
.hunk:	move.l	(a3)+,a1		; hunk start
	move.w	(a5)+,d5		; mode
	move.l	(a5)+,d2		; packed size
	move.l	(a5)+,d3		; unpacked size
	move.l	(a5)+,d4		; alloc size
	tst.w	d5
	beq.s	.next
	lea	0(a1,d2.l),a0		; end of the packed data
	lea	0(a1,d4.l),a2		; end of the hunk
	move.l	a2,d4			; d4 = end of the hunk
	move.l	d2,d1
	lsr.l	#2,d1
.move:	move.l	-(a0),-(a2)		; packed data up to the end of the hunk
	subq.l	#1,d1
	bne.s	.move
	move.l	a2,a0			; source
	lea	0(a1,d3.l),a2		; end of the output
	bsr	unpack
.clr:	cmp.l	d4,a1			; zero the rest of the hunk
	bhs.s	.next
	clr.b	(a1)+
	bra.s	.clr
.next:	dbf	d6,.hunk

.rel:	move.w	(a5)+,d0		; source hunk
	bmi.s	.reldone
	move.w	(a5)+,d1		; target hunk
	lsl.w	#2,d0
	lsl.w	#2,d1
	move.l	0(a4,d0.w),a0
	move.l	0(a4,d1.w),d2
	move.l	(a5)+,d3		; count
	moveq	#0,d4			; offset
.rr:	moveq	#0,d5
	move.b	(a5)+,d5
	beq.s	.abs
	add.l	d5,d4
	add.l	d5,d4
	bra.s	.apply
.abs:	move.b	(a5)+,d4
	lsl.l	#8,d4
	move.b	(a5)+,d4
	lsl.l	#8,d4
	move.b	(a5)+,d4
	lsl.l	#8,d4
	move.b	(a5)+,d4
.apply:	add.l	d2,0(a0,d4.l)
	subq.l	#1,d3
	bne.s	.rr
	move.l	a5,d0
	addq.l	#1,d0
	and.w	#$fffe,d0
	move.l	d0,a5
	bra.s	.rel
.reldone:

	move.l	4.w,a6			; caches: the game's code was written as data
	cmp.w	#37,20(a6)
	blo.s	.old
	jsr	-636(a6)		; CacheClearU (Kickstart 2.0+)
	bra.s	.go
.old:	btst	#1,297(a6)		; AttnFlags: a 68020 or better?
	beq.s	.go
	lea	.sup(pc),a5
	jsr	-30(a6)			; Supervisor
	bra.s	.go
.sup:	dc.w	$4e7a,$0002		; movec cacr,d0
	or.w	#$0808,d0		; clear the instruction and data cache
	dc.w	$4e7b,$0002		; movec d0,cacr
	rte
.go:	movem.l	(sp)+,d0-d7/a0-a6
	move.l	bases(pc),-(sp)
	rts				; into the game

; unpack: a0 = packed data, a1 = output, a2 = end of the output
unpack:	moveq	#-128,d7		; empty bit buffer (only the stop bit)
.next:	cmp.l	a2,a1
	bhs.s	.done
	add.b	d7,d7
	bne.s	.bit
	move.b	(a0)+,d7
	dc.w	$df07			; addx.b d7,d7 (shift the stop bit in)
.bit:	bcs.s	.match
	move.b	(a0)+,(a1)+
	bra.s	.next
.match:	moveq	#0,d0
	moveq	#0,d1
	move.b	(a0)+,d0
	bmi.s	.long
	move.b	d0,d1			; short: length (b>>4)+3, 12 bit offset
	lsr.b	#4,d0
	and.w	#15,d1
	lsl.w	#8,d1
	move.b	(a0)+,d1
	bra.s	.copy
.long:	and.w	#$7f,d0			; long: length (b&$7f)+3, 16 bit offset
	move.b	(a0)+,d1
	lsl.w	#8,d1
	move.b	(a0)+,d1
.copy:	addq.l	#1,d1
	move.l	a1,a6
	sub.l	d1,a6
	addq.w	#2,d0			; dbf: length-1
.cp:	move.b	(a6)+,(a1)+
	dbf	d0,.cp
	bra.s	.next
.done:	rts

	cnop	0,4
bases:	ds.l	64		; relocated by the loader: the start of every game hunk
Table:
