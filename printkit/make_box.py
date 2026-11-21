#!/usr/bin/env python3
"""A fold-up 3D box for Stronkie's Blocks, in the style of the Amiga big boxes.
Writes print/StronkiesBlocks_Box.pdf:
  page 1: full size box on A3 (140 x 180 x 35 mm)
  page 2: mini box on A4 (about 100 x 129 x 25 mm)
  page 3: the five faces flat, for checking / showing off
Solid lines: cut.  Dashed lines: fold (score them first with a blunt knife)."""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from printkit import *
from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

OUT = os.path.join(ROOT, 'print', 'StronkiesBlocks_Box.pdf')
ART = os.path.join(ROOT, 'art')
BOXBLUE = HexColor('#02148e')
BW, BH, BD = 140 * mm, 180 * mm, 35 * mm
GL, TK = 12 * mm, 15 * mm

c = canvas.Canvas(OUT, pagesize=landscape(A3))
c.setTitle("Stronkie's Blocks - Fold-up box")
c.setAuthor('Mark Stronks - Stronkie Soft')


def clip_rect(x, y, w, h):
    p = c.beginPath(); p.rect(x, y, w, h); c.clipPath(p, stroke=0, fill=0)


def starburst(cx, cy, r, lines, rot=12, fill=RED, edge=YELLOW, px=1.6):
    pts = []
    for k in range(36):
        rr = r if k % 2 == 0 else r * 0.8
        a = math.pi * 2 * k / 36
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    p = c.beginPath(); p.moveTo(*pts[0])
    for q in pts[1:]: p.lineTo(*q)
    p.close()
    c.setFillColor(fill); c.setStrokeColor(edge); c.setLineWidth(2); c.drawPath(p, stroke=1, fill=1)
    c.saveState(); c.translate(cx, cy); c.rotate(rot)
    n = len(lines)
    for i, (t, col) in enumerate(lines):
        pixtext(c, t, 0, (n / 2 - i - 1) * 10 * px / 1.0 + 1, px, col, center=True, shadow=HexColor('#00000080', hasAlpha=True), sdx=0.6, sdy=0.6)
    c.restoreState()


def amiga_band(x, y, w, h):
    """The black top band with the rainbow stripes, like the boxes of 1988."""
    c.setFillColor(HexColor('#050505')); c.rect(x, y, w, h, stroke=0, fill=1)
    for i, col in enumerate([RED, ORANGE, YELLOW, GREEN, CYAN, BLUE]):
        c.setFillColor(col)
        c.rect(x + w - 70 - i * 0, y + 3 + i * (h - 6) / 6, 70, (h - 6) / 6, stroke=0, fill=1)
    pixtext(c, 'AMIGA', x + 10, y + h / 2 - 7, 1.9, white)
    c.setFillColor(GREY); c.setFont('PopB', 6); c.drawString(x + 110, y + h / 2 - 2, '500  •  500+  •  600  •  1200')


# ------------------------------------------------------------------ faces
def face_front(x, y, w, h):
    c.saveState(); clip_rect(x, y, w, h)
    for i in range(100):
        t = i / 99
        c.setFillColor(HexColor('#%02x%02x%02x' % (int(2 + 30 * t), int(20 + 8 * t), int(142 - 80 * t))))
        c.rect(x, y + h * (1 - (i + 1) / 100), w, h / 100 + 0.5, stroke=0, fill=1)
    # faint well grid
    c.setStrokeColor(HexColor('#ffffff14', hasAlpha=True)); c.setLineWidth(0.4)
    for gx in range(0, int(w), 14): c.line(x + gx, y, x + gx, y + h)
    for gy in range(0, int(h), 14): c.line(x, y + gy, x + w, y + gy)
    amiga_band(x, y + h - 30, w, 30)
    # the logo from the loading picture
    lw = w * 0.92
    lh = lw * 540 / 1240
    c.drawImage(ImageReader(os.path.join(ART, 'box_logo.png')), x + (w - lw) / 2, y + h - 36 - lh, lw, lh)
    c.setFillColor(YELLOW); c.setFont('PopB', 9)
    c.drawCentredString(x + w / 2, y + h - 48 - lh, 'TEN WORLDS.  SEVEN BLOCKS.  ZERO MERCY.')
    # the game, tilted, with a backdrop behind it
    c.saveState(); c.translate(x + w / 2 + 10, y + 168); c.rotate(-5)
    sw = w * 0.70
    sh = sw * 0.8
    c.setFillColor(HexColor('#00000070', hasAlpha=True)); c.rect(-sw / 2 + 6, -sh / 2 - 6, sw, sh, stroke=0, fill=1)
    c.setFillColor(white); c.rect(-sw / 2 - 5, -sh / 2 - 5, sw + 10, sh + 10, stroke=0, fill=1)
    c.drawImage(ImageReader(os.path.join(SHOTS, 'v12_space_super.png')), -sw / 2, -sh / 2, sw, sh)
    c.restoreState()
    c.saveState(); c.translate(x + 74, y + 112); c.rotate(7)
    sw2 = w * 0.36
    c.setFillColor(white); c.rect(-sw2 / 2 - 4, -sw2 * 0.4 - 4, sw2 + 8, sw2 * 0.8 + 8, stroke=0, fill=1)
    c.drawImage(ImageReader(os.path.join(SHOTS, 'v14_world9.png')), -sw2 / 2, -sw2 * 0.4, sw2, sw2 * 0.8)
    c.restoreState()
    starburst(x + w - 62, y + 248, 52, [('INCLUDES', YELLOW), ('ENHANCED', white), ('EDITION!', white)], px=1.45)
    # bottom: banner and publisher
    c.setFillColor(HexColor('#000000a0', hasAlpha=True)); c.rect(x, y, w, 46, stroke=0, fill=1)
    block_row(c, x, y + 46, w, w / 40)
    pixtext(c, 'STRONKIE SOFT', x + 12, y + 22, 1.6, rows=CHROME, shadow=black)
    c.setFillColor(lighten(GREY, 0.4)); c.setFont('PopM', 6.2)
    c.drawString(x + 12, y + 10, 'Standard: A500, 512 KB chip RAM  •  Enhanced: 1 MB chip RAM')
    c.drawImage(ImageReader(os.path.join(ART, 'box_mascot.png')), x + w - 48, y + 4, 40, 33, mask='auto')
    c.restoreState()


def face_back(x, y, w, h):
    c.saveState(); clip_rect(x, y, w, h)
    c.setFillColor(NAVY); c.rect(x, y, w, h, stroke=0, fill=1)
    c.setStrokeColor(NAVY2); c.setLineWidth(0.4)
    for gx in range(0, int(w), 14): c.line(x + gx, y, x + gx, y + h)
    for gy in range(0, int(h), 14): c.line(x, y + gy, x + w, y + gy)
    M = 14
    top = y + h - 14
    pixtext(c, "STRONKIE'S BLOCKS", x + w / 2, top - 18, 2.2, center=True, rows=CHROME, shadow=black)
    block_row(c, x, top - 30, w, w / 40)
    yy = para(c, '<b>The blocks are falling. Only you can stop them.</b> Move them, turn them, drop them - and fill the rows before the well '
              'fills up! Travel from the snow of <b>Red Square</b> to the <b>Northern Lights</b>, the <b>Deep Sea</b>, <b>Neon City</b> and '
              'all the way to <b>Outer Space</b>. Clear four rows at once for a <b>SUPER!</b> - and watch the screen shake.',
              x + M, top - 38, w - 2 * M, 8.2, color=white, align=1)
    # three screenshots
    sw = (w - 2 * M - 16) / 3
    sh = sw * 0.8
    shots = [('v12_space_super.png', 'Four rows: SUPER! Boom. Shake.'), ('v12_mountains.png', 'Snow made of sprites'),
             ('v14_world6.png', 'Enhanced: the Volcano')]
    for i, (s, cap) in enumerate(shots):
        sx = x + M + i * (sw + 8)
        sy = yy - 12 - sh
        c.setFillColor(white); c.rect(sx - 2.5, sy - 2.5, sw + 5, sh + 5, stroke=0, fill=1)
        c.drawImage(ImageReader(os.path.join(SHOTS, s)), sx, sy, sw, sh)
        c.setFillColor(lighten(CYAN, 0.3)); c.setFont('PopI', 6.4); c.drawCentredString(sx + sw / 2, sy - 10, cap)
    yy = yy - 12 - sh - 22
    yy -= 4
    # features
    feats = ['32 colours, five pixel-art worlds and sprite weather', 'Glass blocks, particles, chrome panels, screen shake',
             'Two tunes with drums plus real sampled sound effects', 'The computer plays a demo game - it plans every move',
             'High scores saved on the disk  •  manual in the game']
    for i, f in enumerate(feats):
        cell(c, x + M, yy - 8, 7, RAINBOW[(i * 2) % 8])
        c.setFillColor(white); c.setFont('PopM', 8.2); c.drawString(x + M + 13, yy - 7, f)
        yy -= 14
    # the Enhanced box
    bh = 70
    by = yy - 10 - bh
    c.setFillColor(HexColor('#3a0610')); c.setStrokeColor(YELLOW); c.setLineWidth(1.5)
    c.rect(x + M, by, w - 2 * M, bh, stroke=1, fill=1)
    c.setFillColor(RED); c.rect(x + M, by + bh - 15, w - 2 * M, 15, stroke=0, fill=1)
    pixtext(c, 'ALSO ON THIS DISK: THE ENHANCED EDITION', x + w / 2, by + bh - 11.5, 1.05, YELLOW, center=True)
    para(c, 'Got an Amiga with <b>1 MB of chip RAM</b>? The loader spots it and starts the Enhanced edition all by itself: '
         '<b>TEN worlds</b> (new: the Pyramids, a Volcano, a Tropical Island, a Haunted Castle and Candy Land) and a third tune, '
         '<b>"In the Hall of the Mountain King"</b>. Needs an ECS "Fat Agnus" with 1 MB chip RAM: A500 (8372A + trapdoor), A500+, A600, A3000, A1200.',
         x + M + 6, by + bh - 20, w - 2 * M - 12, 7.0, color=white)
    # the seven pieces, in a row
    px0 = x + (w - 7 * 46 + 10) / 2
    for i, n in enumerate('IOTSZJL'):
        piece(c, n, px0 + i * 46 + (6 if n == 'O' else 0), (by + y + 44) / 2 + 8, 9 if n != 'I' else 8.5)
    # bottom strip
    c.setFillColor(HexColor('#05070f')); c.rect(x, y, w, 44, stroke=0, fill=1)
    c.drawImage(ImageReader(os.path.join(ART, 'box_mascot.png')), x + 10, y + 5, 40, 33, mask='auto')
    pixtext(c, 'STRONKIE SOFT', x + 58, y + 24, 1.3, ORANGE)
    c.setFillColor(GREY); c.setFont('Pop', 5.6)
    c.drawString(x + 58, y + 14, "© 2026 Mark Stronks - Stronkie Soft. Programming AI: Claude.")
    c.drawString(x + 58, y + 7, 'stronkie.itch.io/stronkies-blocks')
    # 'ages' badge
    c.setFillColor(YELLOW); c.circle(x + w - 26, y + 22, 16, stroke=0, fill=1)
    pixtext(c, 'AGES', x + w - 26, y + 25, 0.8, INK, center=True)
    pixtext(c, '8-88', x + w - 26, y + 14, 1.0, INK, center=True)
    c.restoreState()


def face_spine(x, y, w, h):
    """The side you see on the shelf: the name, along the length."""
    c.saveState(); clip_rect(x, y, w, h)
    c.setFillColor(NAVY); c.rect(x, y, w, h, stroke=0, fill=1)
    c.setFillColor(HexColor('#050505')); c.rect(x, y + h - 52, w, 52, stroke=0, fill=1)
    for i, col in enumerate([RED, ORANGE, YELLOW, GREEN, CYAN, BLUE]):
        c.setFillColor(col); c.rect(x, y + h - 52 + 6 + i * 4, w, 4, stroke=0, fill=1)
    pixtext(c, 'AMIGA', x + w / 2, y + h - 18, 1.3, white, center=True)
    c.translate(x + w / 2, y + (h - 52) / 2 + 4); c.rotate(90)
    pixtext(c, "STRONKIE'S BLOCKS", 0, 2, 2.2, center=True, rows=CHROME, shadow=black)
    c.setFillColor(YELLOW); c.setFont('PopB', 6.5); c.drawCentredString(0, -14, 'STANDARD + ENHANCED EDITION')
    c.restoreState()
    c.saveState()
    for i in range(3):
        cell(c, x + w / 2 - 6, y + 10 + i * 13, 12, RAINBOW[i * 2])
    c.restoreState()


def face_specs(x, y, w, h):
    """The other side: what you need to run it - the standard game and the Enhanced edition."""
    c.saveState(); clip_rect(x, y, w, h)
    c.setFillColor(HexColor('#e9e4d4')); c.rect(x, y, w, h, stroke=0, fill=1)
    c.translate(x + w, y); c.rotate(90)          # now width = h, height = w
    L, T = h, w
    c.setFillColor(NAVY); c.rect(0, T - 16, L, 16, stroke=0, fill=1)
    pixtext(c, 'SYSTEM REQUIREMENTS', 10, T - 12, 1.2, YELLOW)
    pixtext(c, 'STRONKIE SOFT', L - 10, T - 12, 1.0, ORANGE, right=True)
    colw = (L - 30) / 2
    blocks = [('STANDARD GAME', CYAN, ['Amiga 500 (PAL) or any later Amiga', 'Kickstart / Workbench 1.3 or higher', '512 KB chip RAM (uses 135 KB chip + 100 KB other)', 'Joystick in port 2 or keyboard  •  1 player']),
              ('ENHANCED EDITION', RED, ['ECS "Fat Agnus" with 1 MB chip RAM', 'A500 (8372A + trapdoor), A500+, A600, A3000, A1200', '10 worlds  •  3 tunes  •  picked automatically', 'Hold fire while loading for the standard game'])]
    for k, (t, col, ls) in enumerate(blocks):
        bx = 10 + k * (colw + 10)
        c.setFillColor(col); c.rect(bx, T - 31, colw, 11, stroke=0, fill=1)
        pixtext(c, t, bx + 4, T - 28.5, 0.9, white if k else INK)
        for j, l in enumerate(ls):
            c.setFillColor(INK); c.setFont('PopM', 6.3); c.drawString(bx + 2, T - 42 - j * 9.5, l)
    c.setFillColor(GREY); c.setFont('Pop', 5.2)
    c.drawString(10, 5, '1 × 3½" double-density disk (880 KB)  •  hard drive installable  •  high scores saved to disk  •  V1.4')
    c.restoreState()


def face_top(x, y, w, h):
    c.saveState(); clip_rect(x, y, w, h)
    c.setFillColor(NAVY); c.rect(x, y, w, h, stroke=0, fill=1)
    block_row(c, x, y, w, w / 40)
    block_row(c, x, y + h - w / 40, w, w / 40, 3)
    pixtext(c, "STRONKIE'S BLOCKS", x + w / 2, y + h / 2 - 7, 2.0, center=True, rows=CHROME, shadow=black)
    c.restoreState()


def face_bottom(x, y, w, h):
    c.saveState(); clip_rect(x, y, w, h)
    c.setFillColor(NAVY); c.rect(x, y, w, h, stroke=0, fill=1)
    pixtext(c, 'STRONKIE SOFT', x + w / 2, y + h / 2 + 4, 1.4, ORANGE, center=True)
    c.setFillColor(GREY); c.setFont('PopM', 6)
    c.drawCentredString(x + w / 2, y + h / 2 - 10, '1 DISK  •  STANDARD + ENHANCED  •  V1.4  •  MADE IN 2026')
    c.restoreState()


# ------------------------------------------------------------------ the dieline
def tuck(x, y, w, h, up=True):
    """A tuck flap: rounded at the free corners."""
    p = c.beginPath()
    r = min(h * 0.9, 10 * mm)
    if up:
        p.moveTo(x, y); p.lineTo(x + 2, y + h - r); p.curveTo(x + 2, y + h, x + r, y + h, x + r + 2, y + h)
        p.lineTo(x + w - r - 2, y + h); p.curveTo(x + w - r, y + h, x + w - 2, y + h, x + w - 2, y + h - r); p.lineTo(x + w, y)
    else:
        p.moveTo(x, y + h); p.lineTo(x + 2, y + r); p.curveTo(x + 2, y, x + r, y, x + r + 2, y)
        p.lineTo(x + w - r - 2, y); p.curveTo(x + w - r, y, x + w - 2, y, x + w - 2, y + r); p.lineTo(x + w, y + h)
    p.close()
    return p


def dust(x, y, w, h, up=True):
    p = c.beginPath()
    if up:
        p.moveTo(x, y); p.lineTo(x + 1, y + h * 0.55); p.lineTo(x + w * 0.35, y + h); p.lineTo(x + w - 1, y + h); p.lineTo(x + w, y)
    else:
        p.moveTo(x, y + h); p.lineTo(x + 1, y + h * 0.45); p.lineTo(x + w * 0.35, y); p.lineTo(x + w - 1, y); p.lineTo(x + w, y + h)
    p.close()
    return p


def dieline(ox, oy, s, page_w, page_h, label):
    c.saveState(); c.translate(ox, oy); c.scale(s, s)
    yb = BD + TK
    xg, xl, xf, xr, xb = 0, GL, GL + BD, GL + BD + BW, GL + 2 * BD + BW
    # artwork (with 2 mm bleed under the cut lines)
    B = 2 * mm
    c.setFillColor(HexColor('#cfcfd6'))
    p = c.beginPath(); p.moveTo(xl, yb + 4 * mm); p.lineTo(xg, yb + 8 * mm); p.lineTo(xg, yb + BH - 8 * mm); p.lineTo(xl, yb + BH - 4 * mm); p.close()
    c.drawPath(p, stroke=0, fill=1)
    c.saveState(); c.translate(xg + GL / 2, yb + BH / 2); c.rotate(90)
    c.setFillColor(GREY); c.setFont('PopB', 7); c.drawCentredString(0, -2, 'GLUE  •  GLUE  •  GLUE')
    c.restoreState()
    face_specs(xl, yb, BD, BH)
    face_front(xf, yb, BW, BH)
    face_spine(xr, yb, BD, BH)
    face_back(xb, yb, BW, BH)
    # top lid on the back, bottom lid on the front (drawn so they read from the front)
    c.saveState(); c.translate(xb + BW, yb + BH + BD); c.rotate(180); face_top(0, 0, BW, BD); c.restoreState()
    face_bottom(xf, yb - BD, BW, BD)
    # tucks and dust flaps
    c.setFillColor(NAVY2)
    c.drawPath(tuck(xb, yb + BH + BD, BW, TK, True), stroke=0, fill=1)
    c.drawPath(tuck(xf, yb - BD - TK, BW, TK, False), stroke=0, fill=1)
    for xx in (xl, xr):
        c.drawPath(dust(xx, yb + BH, BD, BD * 0.85, True), stroke=0, fill=1)
        c.drawPath(dust(xx, yb - BD * 0.85, BD, BD * 0.85, False), stroke=0, fill=1)
    # cut lines
    c.setStrokeColor(black); c.setLineWidth(0.6 / s)
    c.drawPath(tuck(xb, yb + BH + BD, BW, TK, True), stroke=1, fill=0)
    c.drawPath(tuck(xf, yb - BD - TK, BW, TK, False), stroke=1, fill=0)
    for xx in (xl, xr):
        c.drawPath(dust(xx, yb + BH, BD, BD * 0.85, True), stroke=1, fill=0)
        c.drawPath(dust(xx, yb - BD * 0.85, BD, BD * 0.85, False), stroke=1, fill=0)
    c.drawPath(p, stroke=1, fill=0)          # the glue flap
    c.line(xf, yb + BH, xf, yb + BH + 0.01)
    # outer edges of the body
    c.line(xb + BW, yb, xb + BW, yb + BH)
    c.line(xb, yb + BH, xb, yb + BH + BD); c.line(xb + BW, yb + BH, xb + BW, yb + BH + BD)   # top lid sides
    c.line(xf, yb - BD, xf, yb); c.line(xf + BW, yb - BD, xf + BW, yb)                       # bottom lid sides
    c.line(xf, yb + BH, xf + BW, yb + BH)    # top of front
    c.line(xb, yb, xb + BW, yb)              # bottom of back
    # fold lines
    c.setDash(3 / s, 2 / s); c.setStrokeColor(HexColor('#ffffff')); c.setLineWidth(0.5 / s)
    for xx in (xl, xf, xr, xb):
        c.line(xx, yb, xx, yb + BH)
    c.line(xb, yb + BH, xb + BW, yb + BH); c.line(xb, yb + BH + BD, xb + BW, yb + BH + BD)
    c.line(xf, yb, xf + BW, yb); c.line(xf, yb - BD, xf + BW, yb - BD)
    c.line(xl, yb + BH, xl + BD, yb + BH); c.line(xr, yb + BH, xr + BD, yb + BH)
    c.line(xl, yb, xl + BD, yb); c.line(xr, yb, xr + BD, yb)
    c.setDash()
    # instructions in the empty corner above the front
    ix, iy = xf + 4 * mm, yb + BH + BD + TK
    pixtext(c, 'FOLD-UP BOX', ix, iy - 9, 1.5, NAVY)
    lines = [label, 'Print at 100% on thick paper (200-300 g/m²).',
             'Cut the solid lines, score and fold the dashed ones.',
             'Glue the grey flap behind the back panel, then fold',
             'the dust flaps in and tuck the lids.']
    c.setFillColor(INK); c.setFont('Pop', 6.3 / max(s, 0.85))
    for i, l in enumerate(lines):
        c.drawString(ix, iy - 20 - i * 8.5 / max(s, 0.85), l)
    c.restoreState()


# ---- page 1: A3, full size
PW, PH = landscape(A3)
TOTW = GL + 2 * BD + 2 * BW
TOTH = BH + 2 * (BD + TK)
dieline((PW - TOTW) / 2, (PH - TOTH) / 2, 1.0, PW, PH, 'Full size: 140 × 180 × 35 mm (A3 paper).')
c.showPage()

# ---- page 2: A4, mini
c.setPageSize(landscape(A4))
PW, PH = landscape(A4)
s = min((PW - 14 * mm) / TOTW, (PH - 10 * mm) / TOTH)
dieline((PW - TOTW * s) / 2, (PH - TOTH * s) / 2, s, PW, PH,
        'Mini: %d × %d × %d mm (A4 paper).' % (round(140 * s), round(180 * s), round(35 * s)))
c.showPage()

# ---- page 3: the faces flat (A3)
c.setPageSize(landscape(A3))
PW, PH = landscape(A3)
c.setFillColor(HexColor('#2b2b33')); c.rect(0, 0, PW, PH, stroke=0, fill=1)
gx = (PW - (BD + BW + BD + BW + 3 * 8 * mm)) / 2
y0 = (PH - BH) / 2 - 8 * mm
face_specs(gx, y0, BD, BH)
face_front(gx + BD + 8 * mm, y0, BW, BH)
face_spine(gx + BD + BW + 16 * mm, y0, BD, BH)
face_back(gx + 2 * BD + BW + 24 * mm, y0, BW, BH)
face_top(gx + BD + 8 * mm, y0 + BH + 8 * mm, BW, BD)
face_bottom(gx + 2 * BD + BW + 24 * mm, y0 + BH + 8 * mm, BW, BD)
pixtext(c, "STRONKIE'S BLOCKS - THE BOX", PW / 2, PH - 18 * mm, 2.4, center=True, rows=CHROME, shadow=black)
c.setFillColor(GREY); c.setFont('PopM', 8)
c.drawCentredString(PW / 2, 10 * mm, 'Left to right: specs side, front, spine, back.  Top: lid and bottom.  This page is for previews; build the box from page 1 or 2.')
c.showPage()
c.save()
print('wrote', OUT)
