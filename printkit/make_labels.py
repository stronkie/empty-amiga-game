#!/usr/bin/env python3
"""3.5" disk labels for Stronkie's Blocks on an A4 sheet.
Writes print/StronkiesBlocks_DiskLabels.pdf.  Print at 100% (no 'fit to
page'), cut along the marks, fold the flap over the top edge of the disk."""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from printkit import *
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

OUT = os.path.join(ROOT, 'print', 'StronkiesBlocks_DiskLabels.pdf')
PW, PH = A4
LW, FRONT, FLAP = 70 * mm, 55 * mm, 20 * mm
LH = FRONT + FLAP
c = canvas.Canvas(OUT, pagesize=A4)
c.setTitle("Stronkie's Blocks - Disk labels")
c.setAuthor('Mark Stronks - Stronkie Soft')


def crop(x, y, w, h):
    c.setStrokeColor(HexColor('#888888')); c.setLineWidth(0.3)
    L = 4 * mm
    for (px, py, dx, dy) in ((x, y, -1, -1), (x + w, y, 1, -1), (x, y + h, -1, 1), (x + w, y + h, 1, 1)):
        c.line(px + dx * 1.5 * mm, py, px + dx * (1.5 * mm + L), py)
        c.line(px, py + dy * 1.5 * mm, px, py + dy * (1.5 * mm + L))


def front_dark(x, y, title2='DISK 1 OF 1'):
    w, h = LW, FRONT
    c.setFillColor(NAVY); c.rect(x, y, w, h, stroke=0, fill=1)
    for i in range(18):
        c.setFillColor(HexColor('#%02x%02x%02x' % (40 + i * 9, 20 + i * 2, 90 - i * 2)))
        c.rect(x, y + h - 26 - i * 0.9, w, 0.95, stroke=0, fill=1)
    c.setFillColor(NAVY); c.rect(x, y, w, h - 42, stroke=0, fill=1)
    pixtext(c, "STRONKIE'S", x + w / 2, y + h - 15, 1.45, center=True, rows=CHROME, shadow=black, sdx=0.8, sdy=0.8)
    pixtext(c, 'BLOCKS', x + w / 2, y + h - 37, 2.55, center=True, rows=CHROME, shadow=black, sdx=0.8, sdy=0.8)
    block_row(c, x, y + h - 47, w, w / 36)
    # a screenshot on the left, text on the right
    sw = 30 * mm
    sh = sw * 0.8
    c.setFillColor(black); c.rect(x + 4, y + 8 - 1, sw + 2, sh + 2, stroke=0, fill=1)
    c.drawImage(ImageReader(os.path.join(SHOTS, 'v12_mountains.png')), x + 5, y + 8, sw, sh)
    tx = x + sw + 12
    pixtext(c, title2, tx, y + 62, 1.05, YELLOW)
    lines = [('AMIGA 500', white), ('KICKSTART 1.3+', white), ('512K CHIP RAM', white)]
    for i, (t, col) in enumerate(lines):
        pixtext(c, t, tx, y + 50 - i * 9, 0.82, col)
    c.setFillColor(RED); c.rect(tx - 2, y + 11, w - (tx - x) - 3, 10, stroke=0, fill=1)
    pixtext(c, '+ ENHANCED 1MB', tx + 1, y + 13.5, 0.78, white)
    c.setFillColor(GREY); c.setFont('PopM', 4.6)
    c.drawString(x + 5, y + 2.6, "© 2026 MARK STRONKS • STRONKIE SOFT • V1.4")
    c.drawRightString(x + w - 4, y + 2.6, 'STRONKIE.ITCH.IO')


def front_classic(x, y):
    """A white label with a colour band, like the publishers' labels of 1989."""
    w, h = LW, FRONT
    c.setFillColor(white); c.rect(x, y, w, h, stroke=0, fill=1)
    c.setFillColor(NAVY); c.rect(x, y + h - 30, w, 30, stroke=0, fill=1)
    for i, col in enumerate([RED, ORANGE, YELLOW, GREEN, CYAN, BLUE, PURPLE]):
        c.setFillColor(col); c.rect(x, y + h - 33 - i * 1.6, w, 1.6, stroke=0, fill=1)
    pixtext(c, "STRONKIE'S BLOCKS", x + w / 2, y + h - 19, 1.38, center=True, rows=CHROME, shadow=black, sdx=0.7, sdy=0.7)
    c.setFillColor(lighten(CYAN, 0.2)); c.setFont('PopB', 5)
    c.drawCentredString(x + w / 2, y + h - 27, 'THE FALLING-BLOCKS GAME FOR YOUR AMIGA')
    ty = y + 64
    pixtext(c, 'DISK 1 OF 1', x + 8, y + 88, 1.0, MAGENTA)
    c.setFillColor(RED); c.rect(x + w - 76, y + 85, 70, 13, stroke=0, fill=1)
    pixtext(c, '+ ENHANCED', x + w - 41, y + 88.5, 0.85, white, center=True)
    for name in 'TLSZJOI':
        pass
    piece(c, 'T', x + 8, ty + 4, 7); piece(c, 'L', x + 34, ty + 4, 7); piece(c, 'I', x + 60, ty + 4, 7)
    piece(c, 'S', x + 94, ty + 4, 7); piece(c, 'O', x + 124, ty + 4, 7); piece(c, 'Z', x + 145, ty + 4, 7); piece(c, 'J', x + 172, ty + 4, 7)
    pixtext(c, 'GAME DISK', x + 8, y + 38, 1.4, NAVY)
    c.setFillColor(INK); c.setFont('Pop', 5.6)
    c.drawString(x + 8, y + 29.5, 'Amiga 500 • Kickstart 1.3 or higher • 512 KB chip RAM')
    c.drawString(x + 8, y + 21.5, 'Enhanced edition on 1 MB chip RAM (ECS) - automatic')
    c.drawString(x + 8, y + 14, 'Keep write-enabled to save your high scores')
    c.setFillColor(NAVY); c.rect(x, y, w, 9, stroke=0, fill=1)
    pixtext(c, 'STRONKIE SOFT', x + 6, y + 2.5, 0.78, ORANGE)
    c.setFillColor(white); c.setFont('PopM', 4.6); c.drawRightString(x + w - 5, y + 3, '© 2026  •  V1.4')


def front_enhanced(x, y):
    w, h = LW, FRONT
    c.setFillColor(HexColor('#2a0a12')); c.rect(x, y, w, h, stroke=0, fill=1)
    c.drawImage(ImageReader(os.path.join(ROOT, 'art', 'backdrops', 'scene6.png')), x, y, w, h, preserveAspectRatio=False)
    c.setFillColor(HexColor('#000000')); c.setFillAlpha(0.35); c.rect(x, y, w, h, stroke=0, fill=1); c.setFillAlpha(1)
    pixtext(c, "STRONKIE'S", x + w / 2, y + h - 16, 1.45, center=True, rows=CHROME, shadow=black, sdx=0.8, sdy=0.8)
    pixtext(c, 'BLOCKS', x + w / 2, y + h - 38, 2.55, center=True, rows=CHROME, shadow=black, sdx=0.8, sdy=0.8)
    c.setFillColor(RED); c.rect(x, y + 50, w, 14, stroke=0, fill=1)
    pixtext(c, 'ENHANCED EDITION', x + w / 2, y + 53.5, 1.15, YELLOW, center=True, shadow=black, sdx=0.6, sdy=0.6)
    pixtext(c, '10 WORLDS  3 TUNES', x + w / 2, y + 36, 0.95, white, center=True, shadow=black, sdx=0.6, sdy=0.6)
    pixtext(c, '1 MB CHIP RAM', x + w / 2, y + 25, 0.95, CYAN, center=True, shadow=black, sdx=0.6, sdy=0.6)
    c.setFillColor(lighten(GREY, 0.4)); c.setFont('PopM', 4.6)
    c.drawCentredString(x + w / 2, y + 4, "© 2026 MARK STRONKS • STRONKIE SOFT • STANDARD GAME INCLUDED")


def flap(x, y, dark=True):
    """The part that folds over the top of the disk onto the back - drawn
    upside down, so it reads the right way on the back."""
    w, h = LW, FLAP
    c.saveState(); c.translate(x + w, y + h); c.rotate(180)
    c.setFillColor(NAVY if dark else white); c.rect(0, 0, w, h, stroke=0, fill=1)
    block_row(c, 0, h - 5, w, w / 40)
    col = white if dark else INK
    pixtext(c, "STRONKIE'S BLOCKS", 5, h - 15, 0.85, YELLOW if dark else NAVY)
    c.setFillColor(col); c.setFont('Pop', 4.4)
    c.drawString(5, h - 23, 'Boot from this disk, or double-click SBlocks on Workbench.')
    c.drawString(5, h - 29, 'Hold fire while loading for the standard game on a 1 MB chip machine.')
    c.drawString(5, h - 35, 'Do not touch the magnetic surface. Do not feed to the dog.')
    c.setFont('PopB', 4.4); c.drawString(5, 6, 'GAME DISK  •  V1.4')
    c.drawRightString(w - 5, 6, 'STRONKIE SOFT 2026')
    c.restoreState()


def label(x, y, kind):
    flap(x, y + FRONT, dark=(kind != 'classic'))
    {'dark': front_dark, 'classic': front_classic, 'enh': front_enhanced}[kind](x, y)
    c.setStrokeColor(HexColor('#ffffff')); c.setDash(2, 2); c.setLineWidth(0.5)
    c.line(x + 2, y + FRONT, x + LW - 2, y + FRONT); c.setDash()
    crop(x, y, LW, LH)


# ---- the sheet
c.setFillColor(NAVY); c.rect(0, PH - 26 * mm, PW, 26 * mm, stroke=0, fill=1)
pixtext(c, "STRONKIE'S BLOCKS - DISK LABELS", 14 * mm, PH - 13 * mm, 2.1, rows=CHROME, shadow=black)
c.setFillColor(white); c.setFont('Pop', 7.5)
c.drawString(14 * mm, PH - 20 * mm, 'Print at 100% (actual size) on white paper or A4 sticker sheets. Cut on the marks. The dashed line is the top edge of the disk:')
c.drawString(14 * mm, PH - 23.5 * mm, 'stick the big part on the front of the disk and fold the flap over onto the back. Label size 70 × 75 mm (front 70 × 55 mm).')
gx = (PW - 2 * LW - 16 * mm) / 2
kinds = [('dark', 'dark'), ('classic', 'classic'), ('enh', 'enh')]
top = PH - 34 * mm
for r, (k1, k2) in enumerate(kinds):
    yy = top - (r + 1) * LH - r * 10 * mm
    label(gx, yy, k1)
    label(gx + LW + 16 * mm, yy, k2)
c.setFillColor(GREY); c.setFont('PopM', 6.5)
c.drawCentredString(PW / 2, 8 * mm, "Three styles: the box-art label, the classic white publisher's label, and the Enhanced edition label. © 2026 Mark Stronks - Stronkie Soft")
c.showPage()

# ---- page 2: the square labels (no fold) for disk boxes and cases, plus a spine strip
c.setFillColor(NAVY); c.rect(0, PH - 20 * mm, PW, 20 * mm, stroke=0, fill=1)
pixtext(c, 'FLAT LABELS AND SPINE STRIPS', 14 * mm, PH - 13 * mm, 2.1, rows=CHROME, shadow=black)
c.setFillColor(GREY); c.setFont('Pop', 7); c.setFillColor(white)
c.drawString(14 * mm, PH - 17.5 * mm, 'Front-only labels (70 × 55 mm, no flap) and spine strips for a disk box. Print at 100%.')
gx = (PW - 2 * LW - 16 * mm) / 2
for r in range(2):
    for k, fn in enumerate((front_dark, front_classic, front_enhanced)):
        col = k % 2
        pass
pos = []
for r in range(3):
    for col in range(2):
        pos.append((gx + col * (LW + 16 * mm), PH - 30 * mm - (r + 1) * FRONT - r * 10 * mm))
for i, (x, y) in enumerate(pos):
    (front_dark, front_classic, front_enhanced)[i % 3](x, y)
    crop(x, y, LW, FRONT)
# spine strips
for i in range(3):
    x, y = gx, 20 * mm + i * 14 * mm
    w = 2 * LW + 16 * mm
    c.setFillColor(NAVY); c.rect(x, y, w, 9 * mm, stroke=0, fill=1)
    block_row(c, x + 1.5, y + 1.5, 9 * mm * 2, 9 * mm - 3)
    pixtext(c, "STRONKIE'S BLOCKS", x + 30 * mm, y + 9, 1.6, rows=CHROME, shadow=black)
    pixtext(c, 'AMIGA', x + w - 34 * mm, y + 9, 1.4, ORANGE)
    pixtext(c, 'SOFT', x + w - 12 * mm, y + 9, 1.1, white)
    crop(x, y, w, 9 * mm)
c.showPage()
c.save()
print('wrote', OUT)
