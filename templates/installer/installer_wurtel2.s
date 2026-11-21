;=====================================================================
; installer.s : the hard disk installer of Wurtel Tiel 2 (V1.5)
; Double-click "Install" on the game disk (or run it from the CLI).
; It asks where to install (for example DH0: or Work:Games), makes a
; drawer "Wurtel2" there with its icon and copies the game into it.
; Only dos.library is used, so it works on Workbench 1.3 and up.
;=====================================================================

ExecBase	equ	4
SRC		equ	0			; the files on the game disk

	section	code,code

Start:
	move.l	ExecBase,a6
	sub.l	a1,a1
	jsr	-294(a6)			; FindTask(0)
	move.l	d0,a4
	clr.l	WbMsg
	tst.l	172(a4)				; pr_CLI: started from the CLI?
	bne.s	.cli
	lea	92(a4),a0			; pr_MsgPort: the Workbench message
	jsr	-384(a6)			; WaitPort
	lea	92(a4),a0
	jsr	-372(a6)			; GetMsg
	move.l	d0,WbMsg
.cli:	lea	DosName,a1
	jsr	-408(a6)			; OldOpenLibrary
	move.l	d0,DosBase
	beq	.exit
	move.l	d0,a6
	move.l	#ConName,d1			; our own window
	move.l	#1006,d2
	jsr	-30(a6)				; Open
	move.l	d0,Con
	beq	.nodos

	lea	TxtHello,a0
	bsr	Print
.ask:	lea	TxtAsk,a0
	bsr	Print
	bsr	ReadLine			; -> Line
	lea	Line,a0
	cmp.b	#'q',(a0)
	beq	.quit
	cmp.b	#'Q',(a0)
	beq	.quit
	tst.b	(a0)
	bne.s	.got
	lea	DefDest,a1			; just RETURN: DH0:
.cd:	move.b	(a1)+,(a0)+
	bne.s	.cd
.got:	bsr	MakePaths			; DestDir, DestIcon
	move.l	#Line,d1			; is it there?
	moveq	#-2,d2
	jsr	-84(a6)				; Lock
	tst.l	d0
	bne.s	.there
	lea	TxtNoDest,a0
	bsr	Print
	bra	.ask
.there:	move.l	d0,d1
	jsr	-90(a6)				; UnLock
	lea	TxtMaking,a0
	bsr	Print
	lea	DestDir,a0
	bsr	Print
	lea	TxtNl,a0
	bsr	Print
	move.l	#DestDir,d1			; the drawer
	jsr	-120(a6)			; CreateDir
	tst.l	d0
	bne.s	.made
	move.l	#DestDir,d1			; already there? fine
	moveq	#-2,d2
	jsr	-84(a6)				; Lock
	tst.l	d0
	bne.s	.made
	lea	TxtNoDir,a0
	bsr	Print
	bra	.ask
.made:	move.l	d0,d1
	jsr	-90(a6)				; UnLock

	lea	Files,a3			; the files
.f:	move.l	(a3)+,d0			; the name on the disk
	beq.s	.icon
	move.l	d0,a0
	move.l	(a3)+,d0			; 1 = it must be there
	bsr	SrcPath				; -> SrcName
	lea	DestDir,a0			; -> DstName = drawer/name
	lea	DstName,a1
.c1:	move.b	(a0)+,(a1)+
	bne.s	.c1
	move.b	#'/',-1(a1)
	move.l	-8(a3),a0
.c2:	move.b	(a0)+,(a1)+
	bne.s	.c2
	bsr	CopyFile
	bra.s	.f
.icon:	lea	DrawerIcon,a0			; the icon of the drawer
	moveq	#1,d0
	bsr	SrcPath
	lea	DestIcon,a0
	lea	DstName,a1
.c3:	move.b	(a0)+,(a1)+
	bne.s	.c3
	bsr	CopyFile
	tst.w	Failed
	bne.s	.bad
	lea	TxtDone1,a0
	bsr	Print
	lea	DestDir,a0
	bsr	Print
	lea	TxtDone2,a0
	bsr	Print
	bra.s	.wait
.bad:	lea	TxtFailed,a0
	bsr	Print
.wait:	bsr	ReadLine			; RETURN closes the window
.quit:	move.l	Con,d1
	jsr	-36(a6)				; Close
.nodos:	move.l	a6,a1
	move.l	ExecBase,a6
	jsr	-414(a6)			; CloseLibrary
.exit:	move.l	ExecBase,a6
	tst.l	WbMsg
	beq.s	.r
	jsr	-132(a6)			; Forbid
	move.l	WbMsg,a1
	jsr	-378(a6)			; ReplyMsg
.r:	moveq	#0,d0
	rts

; MakePaths: Line = where -> DestDir = where(/)Wurtel2, DestIcon = DestDir.info
MakePaths:
	lea	Line,a0
	lea	DestDir,a1
.c:	move.b	(a0)+,(a1)+
	bne.s	.c
	subq.l	#1,a1
	move.b	-1(a1),d0
	cmp.b	#':',d0
	beq.s	.n
	cmp.b	#'/',d0
	beq.s	.n
	move.b	#'/',(a1)+
.n:	lea	DrawerName,a0
.c2:	move.b	(a0)+,(a1)+
	bne.s	.c2
	lea	DestDir,a0
	lea	DestIcon,a1
.c3:	move.b	(a0)+,(a1)+
	bne.s	.c3
	subq.l	#1,a1
	lea	TxtInfo,a0
.c4:	move.b	(a0)+,(a1)+
	bne.s	.c4
	rts

; SrcPath: a0 = name, d0 = needed -> SrcName = "Wurtel Tiel 2:" + name
SrcPath:
	move.w	d0,Needed
	lea	SrcVol,a1
	lea	SrcName,a2
.c:	move.b	(a1)+,(a2)+
	bne.s	.c
	subq.l	#1,a2
.c2:	move.b	(a0)+,(a2)+
	bne.s	.c2
	rts

; CopyFile: SrcName -> DstName (prints it); a missing file that is not
; needed is skipped
CopyFile:
	movem.l	d2-d6/a3,-(sp)
	move.l	#SrcName,d1
	move.l	#1005,d2
	jsr	-30(a6)				; Open (old)
	move.l	d0,d5
	bne.s	.src
	tst.w	Needed
	beq	.x
	lea	TxtNoSrc,a0
	bsr	Print
	lea	SrcName,a0
	bsr	Print
	lea	TxtNl,a0
	bsr	Print
	move.w	#1,Failed
	bra	.x
.src:	lea	TxtCopy,a0
	bsr	Print
	lea	DstName,a0
	bsr	Print
	lea	TxtNl,a0
	bsr	Print
	move.l	#DstName,d1
	move.l	#1006,d2
	jsr	-30(a6)				; Open (new)
	move.l	d0,d6
	bne.s	.l
	lea	TxtNoWrite,a0
	bsr	Print
	move.w	#1,Failed
	bra.s	.cs
.l:	move.l	d5,d1
	move.l	#Buffer,d2
	move.l	#BUFSIZE,d3
	jsr	-42(a6)				; Read
	tst.l	d0
	ble.s	.e
	move.l	d0,d3
	move.l	d6,d1
	move.l	#Buffer,d2
	jsr	-48(a6)				; Write
	cmp.l	d3,d0
	beq.s	.l
	lea	TxtNoWrite,a0			; disk full?
	bsr	Print
	move.w	#1,Failed
.e:	move.l	d6,d1
	jsr	-36(a6)				; Close
.cs:	move.l	d5,d1
	jsr	-36(a6)				; Close
.x:	movem.l	(sp)+,d2-d6/a3
	rts

; Print: a0 = text (0 at the end) into the window
Print:
	movem.l	d0-d3/a0-a1,-(sp)
	move.l	a0,d2
	moveq	#-1,d3
.n:	addq.l	#1,d3
	tst.b	(a0)+
	bne.s	.n
	move.l	Con,d1
	jsr	-48(a6)				; Write
	movem.l	(sp)+,d0-d3/a0-a1
	rts

; ReadLine: a line from the window -> Line (without the RETURN, 0 at the end)
ReadLine:
	movem.l	d0-d3/a0,-(sp)
	move.l	Con,d1
	move.l	#Line,d2
	moveq	#LINELEN-1,d3
	jsr	-42(a6)				; Read
	lea	Line,a0
	tst.l	d0
	bpl.s	.ok
	moveq	#0,d0
.ok:	clr.b	(a0,d0.l)
.s:	move.b	(a0),d0			; cut at the RETURN
	beq.s	.x
	cmp.b	#10,d0
	beq.s	.cut
	cmp.b	#13,d0
	beq.s	.cut
	addq.l	#1,a0
	bra.s	.s
.cut:	clr.b	(a0)
.x:	movem.l	(sp)+,d0-d3/a0
	rts

;---------------------------------------------------------------------
DosName:	dc.b	'dos.library',0
ConName:	dc.b	'CON:20/16/600/170/Wurtel Tiel 2 - Hard Disk Installer',0
SrcVol:		dc.b	'Wurtel Tiel 2:',0
DefDest:	dc.b	'DH0:',0
DrawerName:	dc.b	'Wurtel2',0
TxtInfo:	dc.b	'.info',0
DrawerIcon:	dc.b	'Wurtel2Drawer.icon',0	; (not .info: so it is no icon on the game disk)
FGame:		dc.b	'Wurtel2',0
FIcon:		dc.b	'Wurtel2.info',0
FReadMe:	dc.b	'ReadMe',0
FScores:	dc.b	'Wurtel2.scores',0
TxtHello:	dc.b	10,' WURTEL TIEL 2 AMIGA PORT - HARD DISK INSTALLER',10
		dc.b	' (c) Mark Stronks, Stronkie Soft',10,10
		dc.b	' This copies the game into a new drawer "Wurtel2".',10,0
TxtAsk:		dc.b	10,' Install where? (for example DH0: or Work:Games)',10
		dc.b	' RETURN = DH0:   Q = quit',10,' > ',0
TxtNoDest:	dc.b	' I can',39,'t find that place - please try again.',10,0
TxtNoDir:	dc.b	' I can',39,'t make the drawer there - please try again.',10,0
TxtMaking:	dc.b	10,' Installing into ',0
TxtCopy:	dc.b	'   copying ',0
TxtNoSrc:	dc.b	' Missing on the game disk: ',0
TxtNoWrite:	dc.b	' Can',39,'t write the file (disk full or write-protected?)',10,0
TxtDone1:	dc.b	10,' Done! Open ',0
TxtDone2:	dc.b	' and double-click Wurtel2.',10
		dc.b	' Your best scores and medals are saved there too.',10,10
		dc.b	' Press RETURN to close this window.',0
TxtFailed:	dc.b	10,' Something went wrong - see above.',10
		dc.b	' Press RETURN to close this window.',0
TxtNl:		dc.b	10,0
	even
Files:		dc.l	FGame,1,FIcon,1,FReadMe,0,FScores,0,0

	section	bss,bss
BUFSIZE		equ	8192
LINELEN		equ	120
DosBase:	ds.l	1
Con:		ds.l	1
WbMsg:		ds.l	1
Needed:		ds.w	1
Failed:		ds.w	1
Line:		ds.b	LINELEN+4
DestDir:	ds.b	LINELEN+16
DestIcon:	ds.b	LINELEN+24
SrcName:	ds.b	64
DstName:	ds.b	LINELEN+40
Buffer:		ds.b	BUFSIZE
