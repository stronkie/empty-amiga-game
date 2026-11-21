;=====================================================================
;
;   SBaseball.slave - WHDLoad slave for Stronkie's Baseball Enhanced
;   (V2.0 Final Release)
;
;   The game normally runs with the Amiga OS (exec, graphics and dos for
;   a few things: the memory, the files, the start).  Under WHDLoad there
;   is no OS, so this slave gives the game a tiny one of its own:
;     - fake exec, graphics and dos libraries; only the few calls the
;       game makes do something
;     - AllocMem / AvailMem hand out the memory WHDLoad gave us: chip
;       memory above the game, and the expansion memory (the cache for
;       the ballparks and the pictures wants fast memory)
;     - dos Open/Read/Write/Close become WHDLoad file calls; the files
;       (and the records, the season) are in the data directory
;   It loads SBaseballE.game (an ordinary Amiga program) itself: the chip
;   memory hunks into chip memory, the others into the expansion memory.
;   The game is started with "SBWH" and an address: it then leaves the
;   OS alone, and F10 (or QUIT on the title screen) ends WHDLoad.
;
;   Based on the slave of Ghost Zappers: Tycoon.
;   Build: vasmm68k_mot -Fhunkexe -nosym -o SBaseball.slave slave.s
;
;   (c) 2026 Stronkie Soft - Mark Stronks
;=====================================================================
	ifd	STD
; (V3.1) the standard game: assembled with -DSTD=1 -> SBaseballS.slave
BASEMEM		equ	$80000			; chip: 512 KB (the game ~260 KB)
EXPMEM		equ	$90000			; other: the game ~540 KB, our stack
	else
BASEMEM		equ	$d0000			; chip: 832 KB (the game ~690 KB, its mirror cache 66 KB)
EXPMEM		equ	$140000			; other: the game 240 KB, its caches 750 KB, our stack
	endc
CHIPSTART	equ	$1000
STACKSIZE	equ	$2000
MAXHUNKS	equ	96			; (the game has 60)

WHDLF_NoError	equ	2
WHDLF_ClearMem	equ	$1000
resload_Abort		equ	4
resload_LoadFile	equ	8
resload_SaveFile	equ	12
resload_FlushCache	equ	32
resload_GetFileSize	equ	36
resload_LoadFileOffset	equ	76
TDREASON_OK	equ	-1
TDREASON_FAILMSG equ	43

	section	slave,code
;---------------------------------------------------------------------
; the slave header (version 10)
;---------------------------------------------------------------------
_base:	moveq	#-1,d0				; ws_Security
	rts
	dc.b	'WHDLOADS'			; ws_ID
	dc.w	10				; ws_Version
	dc.w	WHDLF_NoError|WHDLF_ClearMem	; ws_Flags
	dc.l	BASEMEM				; ws_BaseMemSize
	dc.l	0				; ws_ExecInstall
	dc.w	_start-_base			; ws_GameLoader
	dc.w	_dir-_base			; ws_CurrentDir
	dc.w	0				; ws_DontCache
	dc.b	0				; ws_keydebug
	dc.b	$59				; ws_keyexit (F10)
_expmem:	dc.l	EXPMEM				; ws_ExpMem
	dc.w	_name-_base			; ws_name
	dc.w	_copy-_base			; ws_copy
	dc.w	_info-_base			; ws_info

_dir:	dc.b	'data',0
	ifd	STD
_name:	dc.b	"Stronkie's Baseball",0
	else
_name:	dc.b	"Stronkie's Baseball Enhanced",0
	endc
_copy:	dc.b	'2026 Stronkie Soft',0
_info:	dc.b	'Created by Mark Stronks',10
	ifd	STD
	dc.b	'Version 3.1 (20.11.2026)',10
	else
	dc.b	'Version 2.1 (20.11.2026)',10
	endc
	dc.b	'F10 quits',0
	ifd	STD
GameName:	dc.b	'SBaseball.game',0
MsgNoGame:	dc.b	'SBaseball.game is missing or broken',0
	else
GameName:	dc.b	'SBaseballE.game',0
MsgNoGame:	dc.b	'SBaseballE.game is missing or broken',0
	endc
	even

;---------------------------------------------------------------------
; start: a0 = resident loader
;---------------------------------------------------------------------
_start:
	lea	V(pc),a5
	move.l	a0,Resload-V(a5)
	move.l	_expmem(pc),d0			; our stack at the top of the expansion memory
	add.l	#EXPMEM,d0
	move.l	d0,a7
	sub.l	#STACKSIZE,d0
	move.l	d0,FastEnd-V(a5)
	move.l	_expmem(pc),FastPtr-V(a5)
	move.l	#CHIPSTART,ChipPtr-V(a5)
	move.l	#BASEMEM,ChipEnd-V(a5)
	bsr	MakeOS
	bsr	LoadGame
	; start the game: a0 -> "SBWH", the quit address
	lea	GameArg(pc),a0
	lea	Quit(pc),a1
	move.l	a1,4(a0)
	moveq	#8,d0
	move.l	GameStart-V(a5),a1
	move.l	4.w,a6
	jsr	(a1)
Quit:	pea	TDREASON_OK
	move.l	Resload(pc),-(a7)
	addq.l	#resload_Abort,(a7)
	rts

LoadFail:	pea	MsgNoGame(pc)
	pea	TDREASON_FAILMSG
	move.l	Resload(pc),-(a7)
	addq.l	#resload_Abort,(a7)
	rts

;---------------------------------------------------------------------
; MakeOS: the fake libraries.  Every call does nothing (d0 = 0), apart
; from the ones set below.
;---------------------------------------------------------------------
MakeOS:
	lea	ExecBase(pc),a0
	move.w	#100,d0
	bsr	FillLib
	lea	GfxBase(pc),a0
	move.w	#60,d0
	bsr	FillLib
	lea	DosBase(pc),a0
	move.w	#40,d0
	bsr	FillLib
	lea	IntBase(pc),a0
	move.w	#80,d0
	bsr	FillLib
	lea	ExecBase(pc),a0
	move.w	#34,20(a0)			; lib_Version
	lea	DosBase(pc),a0
	move.w	#34,20(a0)
	lea	GfxBase(pc),a0
	move.w	#34,20(a0)
	lea	Process(pc),a0
	move.l	#1,172(a0)			; pr_CLI: not from Workbench
	; exec
	lea	ExecBase(pc),a0
	lea	FindTask(pc),a1
	move.l	a1,-294+2(a0)
	lea	OpenLib(pc),a1
	move.l	a1,-408+2(a0)			; OldOpenLibrary
	move.l	a1,-552+2(a0)			; OpenLibrary
	lea	AllocSignal(pc),a1
	move.l	a1,-330+2(a0)
	lea	AllocMem(pc),a1
	move.l	a1,-198+2(a0)
	lea	AvailMem(pc),a1
	move.l	a1,-216+2(a0)
	; graphics
	lea	GfxBase(pc),a0
	lea	WaitTOF(pc),a1
	move.l	a1,-270+2(a0)
	lea	WaitBlit(pc),a1
	move.l	a1,-228+2(a0)
	; dos
	lea	DosBase(pc),a0
	lea	DosOpen(pc),a1
	move.l	a1,-30+2(a0)
	lea	DosClose(pc),a1
	move.l	a1,-36+2(a0)
	lea	DosRead(pc),a1
	move.l	a1,-42+2(a0)
	lea	DosWrite(pc),a1
	move.l	a1,-48+2(a0)
	; exec base at 4
	lea	ExecBase(pc),a0
	move.l	a0,4.w
	rts

; FillLib: a0 base, d0 vectors - every vector: jmp Ret0
FillLib:
	lea	Ret0(pc),a1
	move.l	a0,a2
	subq.w	#1,d0
.l:	subq.l	#6,a2
	move.w	#$4ef9,(a2)
	move.l	a1,2(a2)
	dbf	d0,.l
	rts

Ret0:	moveq	#0,d0
	rts
FindTask:
	lea	Process(pc),a0
	move.l	a0,d0
	rts
AllocSignal:
	moveq	#12,d0
	rts
OpenLib:	; a1 name -> d0 base
	moveq	#0,d0
	move.b	(a1),d1
	cmp.b	#'g',d1
	bne.s	.d
	lea	GfxBase(pc),a0
	bra.s	.ok
.d:	cmp.b	#'d',d1
	bne.s	.i
	lea	DosBase(pc),a0
	bra.s	.ok
.i:	cmp.b	#'i',d1
	bne.s	.x
	lea	IntBase(pc),a0
.ok:	move.l	a0,d0
.x:	rts
WaitTOF:	; wait for the next frame: until the beam is back at the top
	move.l	d1,-(sp)			; (PAL and NTSC alike)
	move.l	$dff004,d0
	and.l	#$1ff00,d0
.w:	move.l	d0,d1
	move.l	$dff004,d0
	and.l	#$1ff00,d0
	cmp.l	d1,d0
	bhs.s	.w
	move.l	(sp)+,d1
	moveq	#0,d0
	rts
WaitBlit:
	tst.w	$dff002				; (the first read can be early)
.w:	btst	#6,$dff002
	bne.s	.w
	moveq	#0,d0
	rts

; AllocMem: d0 size, d1 flags (MEMF_CHIP 2, MEMF_CLEAR $10000) -> d0
; Chip memory above the game, everything else from the expansion
; memory (or chip, when that is full).  FreeMem does nothing: the game
; frees its memory only when it quits.
AllocMem:
	movem.l	d1-d2/a0-a1,-(sp)
	addq.l	#7,d0
	and.l	#-8,d0
	move.l	d0,d2
	lea	FastPtr(pc),a0
	lea	FastEnd(pc),a1
	btst	#1,d1
	bne.s	.chip
	move.l	(a0),d0
	add.l	d2,d0
	cmp.l	(a1),d0
	bls.s	.ok
.chip:	lea	ChipPtr(pc),a0
	lea	ChipEnd(pc),a1
	move.l	(a0),d0
	add.l	d2,d0
	cmp.l	(a1),d0
	bhi.s	.no
.ok:	move.l	(a0),a1				; the block
	move.l	d0,(a0)
	move.l	a1,d0
	btst	#16,d1				; MEMF_CLEAR
	beq.s	.x
	move.l	d2,d1
	lsr.l	#2,d1
	bra.s	.c2
.c1:	clr.l	(a1)+
.c2:	subq.l	#1,d1
	bpl.s	.c1
	bra.s	.x
.no:	moveq	#0,d0
.x:	movem.l	(sp)+,d1-d2/a0-a1
	rts

; AvailMem: d1 flags -> d0 free bytes (chip, fast, or both)
AvailMem:
	move.l	d2,-(sp)
	moveq	#0,d0
	btst	#2,d1				; not MEMF_FAST: the chip memory counts
	bne.s	.f
	move.l	ChipEnd(pc),d0
	sub.l	ChipPtr(pc),d0
.f:	btst	#1,d1				; not MEMF_CHIP: the expansion memory
	bne.s	.x
	move.l	FastEnd(pc),d2
	sub.l	FastPtr(pc),d2
	add.l	d2,d0
.x:	move.l	(sp)+,d2
	rts

;---------------------------------------------------------------------
; dos: files become WHDLoad files.  Two files can be open; a file being
; written is saved at Close.
;---------------------------------------------------------------------
FH_USED		equ	0
FH_MODE		equ	2
FH_POS		equ	4
FH_SIZE		equ	8
FH_BUF		equ	12
FH_NAME		equ	16
FH_LEN		equ	16+64

; DosOpen: d1 name, d2 mode -> d0 handle (0 = no)
DosOpen:
	movem.l	d1-d3/a0-a3,-(sp)
	lea	Files(pc),a2
	tst.w	FH_USED(a2)
	beq.s	.got
	lea	FH_LEN(a2),a2
	tst.w	FH_USED(a2)
	bne	.no
.got:	; the name without a volume ("PROGDIR:x", "df0:x" -> "x"); the
	; drawers stay ("Parks/park3.dat" is in data/Parks)
	move.l	d1,a0
	move.l	a0,a1
.sc:	move.b	(a0)+,d0
	beq.s	.se
	cmp.b	#':',d0
	bne.s	.sc
	move.l	a0,a1
	bra.s	.sc
.se:	lea	FH_NAME(a2),a0
	moveq	#62,d3
.cp:	move.b	(a1)+,(a0)+
	dbeq	d3,.cp
	clr.b	(a0)
	move.w	d2,FH_MODE(a2)
	clr.l	FH_POS(a2)
	clr.l	FH_SIZE(a2)
	cmp.w	#1006,d2			; MODE_NEWFILE
	beq.s	.ok
	lea	FH_NAME(a2),a0			; an old file: is it there?
	move.l	Resload(pc),a3
	jsr	resload_GetFileSize(a3)
	tst.l	d0
	beq.s	.no
	move.l	d0,FH_SIZE(a2)
.ok:	move.w	#1,FH_USED(a2)
	move.l	a2,d0
	bra.s	.x
.no:	moveq	#0,d0
.x:	movem.l	(sp)+,d1-d3/a0-a3
	rts

; DosRead: d1 handle, d2 buffer, d3 length -> d0 bytes read
DosRead:
	movem.l	d1-d3/a0-a3,-(sp)
	move.l	d1,a2
	move.l	FH_SIZE(a2),d0
	sub.l	FH_POS(a2),d0
	cmp.l	d3,d0
	bls.s	.n
	move.l	d3,d0
.n:	tst.l	d0
	ble.s	.zero
	move.l	d0,-(sp)
	move.l	FH_POS(a2),d1
	lea	FH_NAME(a2),a0
	move.l	d2,a1
	move.l	Resload(pc),a3
	jsr	resload_LoadFileOffset(a3)
	move.l	(sp)+,d0
	add.l	d0,FH_POS(a2)
	bra.s	.x
.zero:	moveq	#0,d0
.x:	movem.l	(sp)+,d1-d3/a0-a3
	rts

; DosWrite: d1 handle, d2 buffer, d3 length -> d0 bytes written.  The
; game writes each file with one Write: the data is saved from its own
; buffer at Close (any size; a second Write is refused).
DosWrite:
	move.l	a2,-(sp)
	move.l	d1,a2
	tst.l	FH_POS(a2)
	bne.s	.no
	move.l	d2,FH_BUF(a2)
	move.l	d3,FH_POS(a2)
	move.l	d3,FH_SIZE(a2)
	move.l	d3,d0
	bra.s	.x
.no:	moveq	#-1,d0
.x:	move.l	(sp)+,a2
	rts

; DosClose: d1 handle - a new file is saved now
DosClose:
	movem.l	d0-d3/a0-a3,-(sp)
	move.l	d1,a2
	tst.w	FH_USED(a2)
	beq.s	.x
	cmp.w	#1006,FH_MODE(a2)
	bne.s	.f
	move.l	FH_SIZE(a2),d0
	beq.s	.f
	lea	FH_NAME(a2),a0
	move.l	FH_BUF(a2),a1
	move.l	Resload(pc),a3
	jsr	resload_SaveFile(a3)
.f:	clr.w	FH_USED(a2)
.x:	movem.l	(sp)+,d0-d3/a0-a3
	moveq	#-1,d0
	rts

;---------------------------------------------------------------------
; LoadGame: load and relocate the hunks of GZTycoon.game
;---------------------------------------------------------------------
LoadGame:
	lea	GameName(pc),a0
	move.l	Resload(pc),a3
	jsr	resload_GetFileSize(a3)
	move.l	d0,FileSize-V(a5)
	beq	LoadFail
	clr.l	CurOff-V(a5)
	clr.l	BufStart-V(a5)
	clr.l	BufLen-V(a5)
	bsr	GetL
	cmp.l	#$3f3,d0			; HUNK_HEADER
	bne	LoadFail
.res:	bsr	GetL				; resident library names: none
	tst.l	d0
	beq.s	.tab
	lsl.l	#2,d0
	add.l	d0,CurOff-V(a5)
	bra.s	.res
.tab:	bsr	GetL				; table size
	bsr	GetL				; first
	move.l	d0,d6
	bsr	GetL				; last
	sub.l	d6,d0
	addq.l	#1,d0
	cmp.l	#MAXHUNKS,d0
	bhi	LoadFail
	move.l	d0,d7				; hunks
	move.w	d7,HunkN-V(a5)
	; the memory for every hunk
	lea	HunkAddr-V(a5),a2
	lea	HunkSize-V(a5),a4
	subq.w	#1,d7
.al:	bsr	GetL
	move.l	d0,d1
	and.l	#$3fffffff,d0
	lsl.l	#2,d0
	move.l	d0,(a4)+
	addq.l	#7,d0
	and.l	#-8,d0
	btst	#30,d1
	beq.s	.fast
	move.l	ChipPtr-V(a5),(a2)+
	add.l	d0,ChipPtr-V(a5)
	cmp.l	#BASEMEM,ChipPtr-V(a5)
	bhi	LoadFail
	bra.s	.an
.fast:	move.l	FastPtr-V(a5),(a2)+
	add.l	d0,FastPtr-V(a5)
	move.l	FastPtr-V(a5),d1
	cmp.l	FastEnd-V(a5),d1
	bhi	LoadFail
.an:	dbf	d7,.al
	; clear all hunks (BSS and the ends of the others)
	lea	HunkAddr-V(a5),a2
	lea	HunkSize-V(a5),a4
	move.w	HunkN-V(a5),d7
	subq.w	#1,d7
.cl:	move.l	(a2)+,a0
	move.l	(a4)+,d0
	lsr.l	#2,d0
	bra.s	.cl2
.cl1:	clr.l	(a0)+
.cl2:	subq.l	#1,d0
	bpl.s	.cl1
	dbf	d7,.cl
	; the hunks themselves
	moveq	#0,d7				; hunk
.hunk:	move.l	CurOff-V(a5),d0
	cmp.l	FileSize-V(a5),d0
	bhs	.done
	bsr	GetL
	and.l	#$3fffffff,d0
	cmp.l	#$3e9,d0			; HUNK_CODE
	beq.s	.data
	cmp.l	#$3ea,d0			; HUNK_DATA
	beq.s	.data
	cmp.l	#$3eb,d0			; HUNK_BSS
	beq.s	.bss
	cmp.l	#$3ec,d0			; HUNK_RELOC32
	beq.s	.reloc
	cmp.l	#$3f0,d0			; HUNK_SYMBOL
	beq	.sym
	cmp.l	#$3f1,d0			; HUNK_DEBUG
	beq.s	.skip
	cmp.l	#$3e8,d0			; HUNK_NAME
	beq.s	.skip
	cmp.l	#$3f2,d0			; HUNK_END
	bne	LoadFail
	addq.w	#1,d7
	cmp.w	HunkN-V(a5),d7
	blo	.hunk
	bra	.done
.data:	bsr	GetL
	and.l	#$3fffffff,d0
	lsl.l	#2,d0
	move.w	d7,d1
	lsl.w	#2,d1
	lea	HunkAddr-V(a5),a1
	move.l	(a1,d1.w),a1
	bsr	ReadData
	bra	.hunk
.bss:	bsr	GetL				; (cleared already)
	bra	.hunk
.skip:	bsr	GetL
	lsl.l	#2,d0
	add.l	d0,CurOff-V(a5)
	bra	.hunk
.reloc:	bsr	GetL				; offsets in this block
	tst.l	d0
	beq	.hunk
	move.l	d0,d5
	bsr	GetL				; to which hunk
	lsl.w	#2,d0
	lea	HunkAddr-V(a5),a1
	move.l	(a1,d0.w),d4			; its address
	move.w	d7,d1
	lsl.w	#2,d1
	move.l	(a1,d1.w),a2			; this hunk
.rl:	bsr	GetL
	add.l	d4,(a2,d0.l)
	subq.l	#1,d5
	bne.s	.rl
	bra.s	.reloc
.sym:	bsr	GetL
	tst.l	d0
	beq	.hunk
	addq.l	#1,d0				; name + value
	lsl.l	#2,d0
	add.l	d0,CurOff-V(a5)
	bra.s	.sym
.done:	move.l	HunkAddr-V(a5),GameStart-V(a5)
	move.l	Resload(pc),a3
	jsr	resload_FlushCache(a3)
	rts

; GetL -> d0 the next long of the file
GetL:	movem.l	d1/a0-a1/a3,-(sp)
	move.l	CurOff-V(a5),d0
	addq.l	#4,d0
	move.l	BufStart-V(a5),d1
	add.l	BufLen-V(a5),d1
	cmp.l	d1,d0
	bls.s	.in
	; fill the buffer from here
	move.l	CurOff-V(a5),d1
	move.l	d1,BufStart-V(a5)
	move.l	FileSize-V(a5),d0
	sub.l	d1,d0
	cmp.l	#RBUFSIZE,d0
	bls.s	.s
	move.l	#RBUFSIZE,d0
.s:	move.l	d0,BufLen-V(a5)
	cmp.l	#4,d0
	blo	LoadFail
	lea	GameName(pc),a0
	lea	RBuf(pc),a1
	move.l	Resload(pc),a3
	jsr	resload_LoadFileOffset(a3)
.in:	move.l	CurOff-V(a5),d0
	sub.l	BufStart-V(a5),d0
	lea	RBuf(pc),a0
	move.l	(a0,d0.l),d0
	addq.l	#4,CurOff-V(a5)
	movem.l	(sp)+,d1/a0-a1/a3
	rts

; ReadData: a1 destination, d0 bytes - straight from the file
ReadData:
	movem.l	d0-d1/a0-a1/a3,-(sp)
	tst.l	d0
	beq.s	.x
	move.l	d0,-(sp)
	move.l	CurOff-V(a5),d1
	lea	GameName(pc),a0
	move.l	Resload(pc),a3
	jsr	resload_LoadFileOffset(a3)
	move.l	(sp)+,d0
	add.l	d0,CurOff-V(a5)
.x:	movem.l	(sp)+,d0-d1/a0-a1/a3
	rts

;---------------------------------------------------------------------
; variables
;---------------------------------------------------------------------
	cnop	0,4
GameArg:	dc.b	'SBWH'
	dc.l	0
V:
Resload:	dc.l	0
ChipPtr:	dc.l	0
ChipEnd:	dc.l	0
FastPtr:	dc.l	0
FastEnd:	dc.l	0
GameStart:	dc.l	0
FileSize:	dc.l	0
CurOff:		dc.l	0
BufStart:	dc.l	0
BufLen:		dc.l	0
HunkN:		dc.w	0
	cnop	0,4
HunkAddr:	ds.l	MAXHUNKS
HunkSize:	ds.l	MAXHUNKS
Files:		ds.b	FH_LEN*2
RBUFSIZE	equ	2048
RBuf:		ds.b	RBUFSIZE
		ds.b	100*6
ExecBase:	ds.b	600
		ds.b	60*6
GfxBase:	ds.b	128
		ds.b	40*6
DosBase:	ds.b	64
		ds.b	80*6
IntBase:	ds.b	64
Process:	ds.b	256

