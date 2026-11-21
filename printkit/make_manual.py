#!/usr/bin/env python3
"""The printed manual: a 16 page A5 booklet in the style of an old box manual.
Writes print/StronkiesBlocks_Manual.pdf.  Print it double-sided, or as a
booklet (most printers: 'booklet' in the print dialog), fold and staple."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from printkit import *
from reportlab.lib.pagesizes import A5
from reportlab.pdfgen import canvas

OUT = os.path.join(ROOT, 'print', 'StronkiesBlocks_Manual.pdf')
os.makedirs(os.path.dirname(OUT), exist_ok=True)
W, H = A5
M = 30
c = canvas.Canvas(OUT, pagesize=A5)
c.setTitle("Stronkie's Blocks - Instruction Manual")
c.setAuthor('Mark Stronks - Stronkie Soft')
c.setSubject('Amiga 500 falling-blocks game, V1.4 with the Enhanced edition')
PAGE = [0]


def page(title, sub=None):
    """An inside page: paper, the title band, the block row, the page number."""
    PAGE[0] += 1
    c.setFillColor(PAPER); c.rect(0, 0, W, H, stroke=0, fill=1)
    # a faint grid, like the well
    c.setStrokeColor(PAPER2); c.setLineWidth(0.35)
    for gx in range(0, int(W) + 1, 14): c.line(gx, 0, gx, H)
    for gy in range(0, int(H) + 1, 14): c.line(0, gy, W, gy)
    c.setFillColor(NAVY); c.rect(0, H - 62, W, 62, stroke=0, fill=1)
    for i in range(6):
        c.setFillColor(HexColor(['#2a1a5e', '#3d1f6e', '#5a2277', '#7a2577', '#a02a6e', '#c93462'][i]))
        c.rect(0, H - 62 + i * 1.6, W, 1.6, stroke=0, fill=1)
    px = 2.6 if pixwidth(title, 2.6) < W - 2 * M else (W - 2 * M) / (len(title) * 8)
    pixtext(c, title, M, H - 40, px, rows=CHROME, shadow=HexColor('#000000'), sdx=1, sdy=1)
    if sub:
        c.setFillColor(lighten(CYAN, 0.3)); c.setFont('PopM', 7.5); c.drawString(M, H - 54, sub)
    block_row(c, 0, H - 72, W + 10, 10, PAGE[0])
    # footer
    c.setFillColor(NAVY); c.rect(0, 0, W, 20, stroke=0, fill=1)
    pixtext(c, "STRONKIE'S BLOCKS", M, 7, 1.1, lighten(GREY, 0.3))
    pixtext(c, 'AMIGA', W - M, 7, 1.1, ORANGE, right=True)
    n = str(PAGE[0])
    bx = W / 2 - 10
    cell(c, bx, 2, 16, RAINBOW[PAGE[0] % 8])
    pixtext(c, n, bx + 8, 6.5, 1.0 if len(n) == 1 else 0.85, INK, center=True)
    return H - 88


def heading(text, x, y, col=MAGENTA, px=1.6):
    pixtext(c, text, x, y - 8 * px, px, col, shadow=HexColor('#00000040', hasAlpha=True))
    return y - 8 * px - 6


def two_shots(a, b, y, ca, cb):
    w2 = (W - 2 * M) / 2 - 8
    y1 = shot(c, a, M + 4, y, w2, ca)
    y2 = shot(c, b, W / 2 + 4, y, w2, cb)
    return min(y1, y2)


def entry(v, d, t, s, img, y):
    c.setFillColor(NAVY); c.roundRect(M, y - 20, 50, 20, 3, stroke=0, fill=1)
    pixtext(c, v, M + 25, y - 14, 1.4, YELLOW, center=True)
    pixtext(c, d, M + 58, y - 8, 1.0, GREY)
    pixtext(c, t, M + 58, y - 19, 1.2, MAGENTA)
    tw = (W - 2 * M) * 0.60
    yt = para(c, s, M, y - 28, tw, 7.6)
    yi = shot(c, img, M + tw + 12, y - 30, W - 2 * M - tw - 14)
    return min(yt, yi) - 14


def end():
    c.showPage()


# ===================================================================== 1 cover
PAGE[0] += 1
c.setFillColor(NAVY); c.rect(0, 0, W, H, stroke=0, fill=1)
# copper bars
for i in range(60):
    t = i / 59
    c.setFillColor(HexColor('#%02x%02x%02x' % (int(18 + 120 * t), int(23 + 10 * t), int(53 + 60 * (1 - t)))))
    c.rect(0, H * 0.42 + i * 3.2, W, 3.3, stroke=0, fill=1)
c.setFillColor(NAVY); c.rect(0, 0, W, H * 0.42, stroke=0, fill=1)
image(c, os.path.join(ROOT, 'art', 'loading_screen.jpg'), 0, H * 0.42 - 210, W, 300, keep=False) if False else None
# the big screenshot, tilted a little like on an old box
c.saveState(); c.translate(W / 2, H * 0.40); c.rotate(-4)
sw = W * 0.80
shot(c, 'v12_mountains.png', -sw / 2, sw * 0.8 / 2 + 6, sw)
c.restoreState()
# falling pieces
piece(c, 'T', 22, H - 30, 13); piece(c, 'I', W - 62, H - 172, 11); piece(c, 'S', 30, H - 190, 11); piece(c, 'L', W - 50, H - 40, 11)
pixtext(c, "STRONKIE'S", W / 2, H - 92, 4.2, center=True, rows=CHROME, shadow=HexColor('#000000'), sdx=1.2, sdy=1.2)
pixtext(c, 'BLOCKS', W / 2, H - 150, 6.8, center=True, rows=CHROME, shadow=HexColor('#000000'), sdx=1.2, sdy=1.2)
c.setFillColor(YELLOW); c.setFont('PopB', 9.5)
c.drawCentredString(W / 2, H - 170, 'THE STACKING GAME FROM BEHIND THE IRON CURTAIN (OF YOUR TV)')
# the Enhanced starburst
cx, cy, r = W - 70, H * 0.40 + 132, 47
import math
pts = []
for k in range(32):
    rr = r if k % 2 == 0 else r * 0.78
    a = math.pi * 2 * k / 32
    pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
p = c.beginPath(); p.moveTo(*pts[0])
for q in pts[1:]: p.lineTo(*q)
p.close()
c.setFillColor(RED); c.setStrokeColor(YELLOW); c.setLineWidth(2); c.drawPath(p, stroke=1, fill=1)
c.saveState(); c.translate(cx, cy); c.rotate(14)
pixtext(c, 'PLUS', 0, 10, 1.3, YELLOW, center=True)
pixtext(c, 'ENHANCED', 0, -2, 1.1, white, center=True)
pixtext(c, 'EDITION!', 0, -14, 1.1, white, center=True)
c.restoreState()
# bottom strip
c.setFillColor(HexColor('#0a0d20')); c.rect(0, 0, W, 64, stroke=0, fill=1)
block_row(c, 0, 64, W + 10, 9)
pixtext(c, 'INSTRUCTION MANUAL', W / 2, 38, 2.0, white, center=True, shadow=MAGENTA)
c.setFillColor(GREY); c.setFont('PopM', 7.5)
c.drawCentredString(W / 2, 22, 'AMIGA 500  •  KICKSTART 1.3  •  1 PLAYER (PLUS BACKSEAT ADVICE)')
pixtext(c, 'STRONKIE SOFT', W / 2, 8, 1.2, ORANGE, center=True)
end()

# ===================================================================== 2 contents
y = page('CONTENTS', 'Welcome, stacker. Please read this before you touch the joystick. Or after. We are not your mum.')
toc = [('Welcome', 3), ('Loading the game', 4), ('The controls', 5), ('How to play', 6), ('Scoring and levels', 7),
       ('The worlds', 8), ('The Enhanced edition', 9), ('Music and sound', 10), ('Tips from the masters', 11),
       ('Funny facts', 12), ('The developer diary', 13), ('Credits', 15)]
yy = y - 4
for i, (t, n) in enumerate(toc):
    cell(c, M, yy - 9, 10, RAINBOW[i % 8])
    c.setFillColor(INK); c.setFont('PopM', 10); c.drawString(M + 18, yy - 7.5, t)
    c.setStrokeColor(GREY); c.setDash(1, 2); c.line(M + 22 + c.stringWidth(t, 'PopM', 10), yy - 6, W - M - 22, yy - 6); c.setDash()
    pixtext(c, str(n), W - M, yy - 9, 1.25, NAVY, right=True)
    yy -= 21
yy -= 8
yy = factbox(c, M, yy, W - 2 * M, 'WARNING!',
             'Stronkie\'s Blocks is <b>highly habit-forming</b>. Side effects may include: seeing falling blocks when you close your eyes, '
             'rearranging the shopping in the fridge so that the rows are complete, and humming a Russian folk song in public. '
             'Take a break every hour. Your joystick needs rest too.', ORANGE)
yy -= 12
para(c, '<b>Contents of this box:</b> one 3½" disk (both games on it), this manual, a disk label you have to cut out yourself '
     'because it is 2026, and a box you have to fold yourself because see previous point.', M, yy, W - 2 * M, 8)
end()

# ===================================================================== 3 welcome
y = page('WELCOME!', 'Congratulations on your excellent choice of software.')
y = para(c, '<b>Thank you for buying Stronkie\'s Blocks</b>, the falling-blocks game made for the Commodore Amiga 500 in the year 2026 - '
         'which, as everybody knows, is the best year to release an Amiga 500 game, because there is hardly any competition.', M, y, W - 2 * M, 9)
y = para(c, 'The idea is simple. Blocks made of four squares fall into a well. You move them and turn them so that they form <b>full rows</b>. '
         'A full row disappears, and everything above it drops down. Clear four rows at once and the game shouts <b>SUPER!</b>, '
         'the screen shakes, and you feel like a genius for exactly 1.4 seconds until the next piece arrives.', M, y - 6, W - 2 * M, 9)
y = para(c, 'Every ten rows the level goes up, the blocks fall faster, and you travel to a new world: from Red Square to the bottom of the sea '
         'and on into outer space. When the blocks pile up to the top of the well, the game is over. It is always over eventually. That is the deal.', M, y - 6, W - 2 * M, 9)
y = shot(c, 'v12_title.png', M + 40, y - 12, W - 2 * M - 80, 'The title screen: chrome logo, copper bars, the five best stackers and a wobbly rainbow scroll text.')
factbox(c, M, y - 10, W - 2 * M, 'DID YOU KNOW?',
        'The whole game - code, five pixel-art worlds, the music and the sampled sounds - is 159 KB. '
        'That is smaller than one photo of your lunch on a modern phone, and much more fun.', CYAN)
end()

# ===================================================================== 4 loading
y = page('LOADING', 'Getting the game from the disk into the machine (the exciting part).')
steps = [
    ('FROM FLOPPY DISK', 'Switch off your Amiga for ten seconds (it likes a little nap). Put the Stronkie\'s Blocks disk in the internal drive '
     'and switch on. The game boots by itself. While it loads you see the <b>loading picture</b> with a progress bar. '
     'When the bar is full, press <b>SPACE</b>, <b>fire</b> or click - or just wait three seconds.'),
    ('FROM WORKBENCH', 'Open the disk icon and double-click <b>SBlocks</b>. Or type <font face="PopB">SBlocks</font> in the CLI. '
     'ESC on the title screen takes you back to Workbench, exactly where you left it.'),
    ('FROM A HARD DRIVE', 'Unpack the hard drive zip and copy the drawer <b>StronkiesBlocks</b> anywhere you like. '
     'Keep SBlocks, SBlocks.game and SBlocksE.game together in that drawer.'),
    ('ENHANCED OR STANDARD?', 'The loader looks at your machine. With <b>1 MB of chip RAM</b> it starts the <b>Enhanced edition</b> by itself; '
     'otherwise the standard game. Want the standard game on a big machine? <b>Hold fire</b> (or the left mouse button) while it loads.'),
]
for i, (t, s) in enumerate(steps):
    cell(c, M, y - 18, 18, RAINBOW[i * 2 % 8])
    pixtext(c, str(i + 1), M + 9, y - 13, 1.2, INK, center=True)
    pixtext(c, t, M + 26, y - 10, 1.25, NAVY)
    y = para(c, s, M + 26, y - 14, W - 2 * M - 26, 8.2) - 9
y = shot(c, 'v13_loading.png', M + 50, y - 2, W - 2 * M - 100, 'The loading screen. The bar is honest: it really fills up while the game loads.')
para(c, '<b>High scores</b> are saved on the disk in the file SBlocks.scores, so keep the disk <b>write-enabled</b> (the little tab closed). '
     'Leaving it locked will not hurt anything - except your chance of eternal fame.', M, y - 8, W - 2 * M, 7.8)
end()

# ===================================================================== 5 controls
y = page('THE CONTROLS', 'Joystick in port 2, or the keyboard. Both work. Both at once also works, but why.')
# a joystick drawing
jx, jy = M + 72, y - 112
c.setFillColor(HexColor('#2a2a33')); c.roundRect(jx - 46, jy - 22, 92, 40, 8, stroke=0, fill=1)
c.setFillColor(HexColor('#444452')); c.roundRect(jx - 46, jy - 14, 92, 32, 8, stroke=0, fill=1)
c.setFillColor(HexColor('#111')); c.ellipse(jx - 14, jy + 4, jx + 14, jy + 14, stroke=0, fill=1)
c.setStrokeColor(HexColor('#222')); c.setLineWidth(7); c.line(jx, jy + 9, jx, jy + 60)
c.setFillColor(RED); c.circle(jx, jy + 64, 10, stroke=0, fill=1)
c.setFillColor(lighten(RED, 0.6)); c.circle(jx - 3, jy + 67, 3, stroke=0, fill=1)
c.setFillColor(ORANGE); c.ellipse(jx + 22, jy + 10, jx + 38, jy + 18, stroke=0, fill=1)
lab = [('UP', 'HARD DROP', jx, jy + 92, 1), ('DOWN', 'SOFT DROP', jx, jy - 42, 1), ('LEFT', 'MOVE', jx - 66, jy + 40, 1), ('RIGHT', 'MOVE', jx + 66, jy + 40, 1)]
for a, b, lx, ly, _ in lab:
    pixtext(c, a, lx, ly, 1.3, MAGENTA, center=True)
    c.setFillColor(INK); c.setFont('PopM', 7); c.drawCentredString(lx, ly - 9, b)
c.setStrokeColor(MAGENTA); c.setLineWidth(1.2)
c.line(jx, jy + 78, jx, jy + 88); c.line(jx - 18, jy + 46, jx - 40, jy + 46); c.line(jx + 18, jy + 46, jx + 40, jy + 46)
pixtext(c, 'FIRE', jx + 74, jy + 12, 1.3, ORANGE, center=True)
c.setFillColor(INK); c.setFont('PopM', 7); c.drawCentredString(jx + 74, jy + 3, 'TURN')
# keyboard table on the right
tx = M + 168
rows = [('Move', 'cursor left / right'), ('Soft drop', 'cursor down'), ('Hard drop', 'SPACE / RETURN'), ('Turn', 'cursor up or X'),
        ('Turn back', 'Z'), ('Pause', 'P'), ('Music on/off', 'M'), ('The manual', 'HELP'), ('To the title', 'ESC')]
pixtext(c, 'KEYBOARD', tx, y - 12, 1.4, NAVY)
ty = y - 22
for i, (a, b) in enumerate(rows):
    c.setFillColor(PAPER2 if i % 2 else lighten(PAPER2, 0.5)); c.rect(tx, ty - 13, W - M - tx, 13, stroke=0, fill=1)
    c.setFillColor(INK); c.setFont('Pop', 7.6); c.drawString(tx + 4, ty - 9.5, a)
    c.setFont('PopB', 7.6); c.drawRightString(W - M - 4, ty - 9.5, b)
    ty -= 13
y = min(jy - 60, ty) - 6
y = heading('ON THE TITLE SCREEN', M, y)
y = para(c, 'Up and down pick a line, left and right change it: the <b>start level</b> (0 to 9) and the <b>music</b> - TUNE A, TUNE B, '
         '(Enhanced: TUNE C) or OFF. <b>Fire starts the game.</b> HOW TO PLAY (or the HELP key) opens the manual inside the game: four pages, '
         'left and right to turn them. Leave the title alone for a while and the game shows the manual by itself and then '
         '<b>plays a demo game</b> to show off. Touch anything to take over.', M, y, W - 2 * M, 8.2)
factbox(c, M, y - 10, W - 2 * M, 'PRO TIP',
        'A block that lands on the floor can still be moved and turned for a short moment (the "lock delay"). '
        'Slide it under an overhang at the last second and feel very clever.', GREEN)
shot(c, 'v12_manual.png', M + 100, y - 66, W - 2 * M - 200, 'The manual inside the game: four pages, in case you lose this booklet behind the sofa.')
end()

# ===================================================================== 6 how to play
y = page('HOW TO PLAY', 'Seven pieces. One well. No mercy.')
y = para(c, 'There are seven pieces, each made of four squares. They come in a "bag": all seven appear once (in a random order) before any '
         'piece repeats, so you never wait for ever for the long one. Well - at most 12 pieces. It only <i>feels</i> like for ever.', M, y, W - 2 * M, 8.4)
names = [('I', 'THE LONG ONE', 'Four rows in one go'), ('O', 'THE SQUARE', 'Does not turn. Proud of it'), ('T', 'THE T', 'Fits almost anywhere'),
         ('S', 'THE S', 'Leaves holes if you let it'), ('Z', 'THE Z', 'S, but in a mirror'), ('J', 'THE J', 'Loves a left wall'), ('L', 'THE L', 'Loves a right wall')]
px0, py0 = M, y - 14
for i, (n, t, d) in enumerate(names):
    col, row = i % 2, i // 2
    x = px0 + col * ((W - 2 * M) / 2)
    yy = py0 - row * 44
    piece(c, n, x, yy - 12, 11)
    pixtext(c, t, x + 52, yy - 10, 1.15, NAVY)
    c.setFillColor(INK); c.setFont('Pop', 7.2); c.drawString(x + 52, yy - 21, d)
y = py0 - 4 * 44 + 6
y = heading('THE RULES', M, y)
rules = ['Move and turn the falling block. <b>Fire</b> turns it; <b>Z</b> turns it back. Near a wall the block hops sideways to make room ("wall kick").',
         'The <b>outline</b> at the bottom shows where the block will land. Trust the outline.',
         'Fill a row from wall to wall and it flashes, bursts into pieces and is gone.',
         'The <b>NEXT</b> box shows the block after this one. Plan ahead. Like a chess grandmaster. With squares.',
         'When the stack reaches the top of the well, the game is over. The well fills up with grey and a sad little tune plays.']
for r in rules:
    cell(c, M, y - 8, 7, ORANGE)
    y = para(c, r, M + 13, y, W - 2 * M - 13, 8) - 4
shot(c, 'v12_demo.png', M + 115, y - 4, W - 2 * M - 230, 'The computer playing its demo game. It plans every piece - and still loses eventually.')
end()

# ===================================================================== 7 scoring
y = page('SCORING', 'How to get rich in points (real money not included).')
tab = [('1 row', '40'), ('2 rows', '100'), ('3 rows', '300'), ('4 rows - SUPER!', '1200')]
c.setFillColor(NAVY); c.rect(M, y - 18, W - 2 * M, 18, stroke=0, fill=1)
pixtext(c, 'ROWS AT ONCE', M + 6, y - 13, 1.25, CYAN)
pixtext(c, 'X (LEVEL + 1)', W - M - 6, y - 13, 1.25, CYAN, right=True)
yy = y - 18
for i, (a, b) in enumerate(tab):
    c.setFillColor(lighten(RAINBOW[i * 2], 0.7)); c.rect(M, yy - 18, W - 2 * M, 18, stroke=0, fill=1)
    c.setFillColor(INK); c.setFont('PopB', 9.5); c.drawString(M + 8, yy - 12.5, a)
    pixtext(c, b, W - M - 8, yy - 13, 1.4, INK, right=True)
    yy -= 18
y = para(c, '<b>Soft drop</b> (joystick down): 1 point for every row the block falls. <b>Hard drop</b> (joystick up): 2 points a row - '
         'and a satisfying thud and screen shake for free. So: 4 rows at once on level 9 is 1200 × 10 = <b>12,000 points</b>. '
         'Do that a few times and the high score table is yours.', M, yy - 10, W - 2 * M, 8.4)
y = heading('LEVELS', M, y - 8)
y = para(c, 'You start on the level you picked on the title (0-9). Every <b>10 rows</b> the level goes up, a bell rings, the blocks fall faster '
         'and the game takes you to the next world. After level 19 the speed stops increasing, which is more than can be said for your heart rate. '
         'When the stack gets near the top, <b>the music speeds up</b> and you hear a heartbeat. That is not a bug. That is drama.', M, y, W - 2 * M, 8.4)
y = two_shots('v12_space_super.png', 'v12_highscore.png', y - 10, 'SUPER! Four rows, a big bang and screen shake.', 'A new high score: three letters, up and down, fire.')
y2 = y - 8
factbox(c, M, y2, W - 2 * M, 'RECORD!',
        'Pass the best score in the table during a game and a RECORD! banner pops up with a coin sound. '
        'Nobody has ever been sad hearing a coin sound.', YELLOW)
end()

# ===================================================================== 8 worlds
y = page('THE WORLDS', 'Every level takes you somewhere new. No passport needed.')
worlds = [('v12_title.png', None)]
std = [('RED SQUARE', 'Kremlin towers, onion domes, snow.', 'game.png'),
       ('NORTHERN LIGHTS', 'Aurora over snowy mountains.', 'v12_mountains.png'),
       ('DEEP SEA', 'Light rays, seaweed, treasure.', None),
       ('NEON CITY', 'Skyscrapers, neon, rain.', None),
       ('OUTER SPACE', 'A ringed planet and nebulae.', 'v12_space_super.png')]
# backdrop previews straight from the asset generator
import subprocess, tempfile
tmp = tempfile.mkdtemp()
subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'make_assets.py'), '--preview', tmp], check=True, stdout=subprocess.DEVNULL)
allw = std + [('PYRAMIDS', 'Desert night and the sphinx.', None), ('VOLCANO', 'Lava, smoke and an eruption.', None),
              ('TROPICAL ISLAND', 'Palm trees, sea and a boat.', None), ('HAUNTED CASTLE', 'Bats, ghosts, a full moon.', None),
              ('CANDY LAND', 'Candy canes and gingerbread.', None)]
tw = (W - 2 * M - 16) / 3
th = tw * 0.8
for i, (n, d, _) in enumerate(allw):
    col, row = i % 3, i // 3
    x = M + col * (tw + 8)
    yy = y - 4 - row * (th + 28)
    c.setFillColor(NAVY); c.rect(x - 2, yy - th - 2, tw + 4, th + 4, stroke=0, fill=1)
    c.drawImage(ImageReader(os.path.join(tmp, f'scene{i}.png')), x, yy - th, tw, th)
    if i >= 5:
        c.setFillColor(RED); c.rect(x + tw - 46, yy - 11, 46, 11, stroke=0, fill=1)
        pixtext(c, 'ENHANCED', x + tw - 23, yy - 9, 0.68, white, center=True)
    pixtext(c, f'{i + 1}. {n}', x, yy - th - 11, 0.72, NAVY)
    c.setFillColor(INK); c.setFont('Pop', 5.8); c.drawString(x, yy - th - 19.5, d)
factbox(c, M + tw + 8, y - 4 - 3 * (th + 28), 2 * tw + 8, 'WORLD TOUR',
        'The standard game has worlds 1 to 5 and starts again at level 5. The Enhanced edition goes through all ten '
        'before Red Square comes round again. Every world has its own weather: snow, bubbles, rain or stars.', CYAN, 6.8)
end()

# ===================================================================== 9 enhanced
y = page('ENHANCED EDITION', 'For the Amiga with a little extra under the bonnet.')
y = para(c, 'Inside the box - well, on the disk - there is a <b>second version of the game</b>: the Enhanced edition. '
         'You do not have to do anything to get it. The loader checks how much <b>chip RAM</b> your Amiga has, and if it finds a full '
         'megabyte it starts the Enhanced game all by itself.', M, y, W - 2 * M, 8.6)
y = heading('WHAT IS EXTRA?', M, y - 6)
extra = ['<b>TEN worlds instead of five.</b> New: the Pyramids, a Volcano, a Tropical Island, a Haunted Castle and Candy Land.',
         '<b>A third tune, TUNE C:</b> "In the Hall of the Mountain King" by Edvard Grieg (1875). Perfect for when the stack gets high.',
         '<b>A longer journey:</b> the worlds only repeat after level 9 instead of level 4.',
         'An <b>ENHANCED</b> label on the title screen, so you can show off to your friends.']
for i, e in enumerate(extra):
    cell(c, M, y - 9, 8, RAINBOW[(i * 3) % 8])
    y = para(c, e, M + 14, y, W - 2 * M - 14, 8.2) - 4
y = heading('WHAT DO I NEED?', M, y - 6)
c.setFillColor(NAVY); c.rect(M, y - 92, W - 2 * M, 92, stroke=0, fill=1)
specs = [('STANDARD', ['Amiga 500 (PAL)', 'Kickstart 1.3 or higher', '512 KB chip RAM', '(135 KB chip + 100 KB other used)', 'Joystick or keyboard']),
         ('ENHANCED', ['Any Amiga with ECS "Fat Agnus"', '1 MB chip RAM', 'A500 (8372A + trapdoor), A500+,', 'A600, A3000, A1200', 'Kickstart 1.3 or higher'])]
for k, (t, ls) in enumerate(specs):
    x = M + 10 + k * ((W - 2 * M) / 2)
    pixtext(c, t, x, y - 16, 1.35, YELLOW if k else CYAN)
    for j, l in enumerate(ls):
        c.setFillColor(white); c.setFont('Pop', 7.2); c.drawString(x, y - 30 - j * 11.5, l)
y -= 100
two_shots('v14_world8.png', 'v14_world9.png', y - 4, 'The Haunted Castle (Enhanced).', 'Candy Land (Enhanced).')
end()

# ===================================================================== 10 music
y = page('MUSIC & SOUND', 'Four channels of Paula. All of them busy.')
y = para(c, 'The Amiga has a sound chip called <b>Paula</b>, with four channels. Stronkie\'s Blocks uses two of them for the music '
         '(a lead and a bass) with drums squeezed in, and keeps the other two for the sound effects - so a SUPER! never cuts the music off.', M, y, W - 2 * M, 8.6)
tunes = [('TUNE A', 'Korobeiniki', 'Russian folk song, after a poem by Nikolay Nekrasov, 1861. A song about a travelling peddler. '
          'Now mostly a song about long blocks.'),
         ('TUNE B', 'Minuet in G', 'From Anna Magdalena Bach\'s notebook, 1725. Polite, elegant, and totally unaware of the falling blocks.'),
         ('TUNE C', 'In the Hall of the Mountain King', 'Edvard Grieg, from Peer Gynt, 1875. Enhanced edition only. It starts quietly. It does not end quietly.')]
for i, (a, b, d) in enumerate(tunes):
    c.setFillColor(lighten(RAINBOW[i * 3 % 8], 0.75)); c.setStrokeColor(INK); c.setLineWidth(0.8)
    c.rect(M, y - 52, W - 2 * M, 46, stroke=1, fill=1)
    pixtext(c, a, M + 8, y - 20, 1.4, NAVY)
    c.setFillColor(INK); c.setFont('PopB', 9); c.drawString(M + 84, y - 19.5, b)
    para(c, d, M + 8, y - 25, W - 2 * M - 16, 7.2)
    y -= 54
y = heading('SOUND EFFECTS', M, y - 6)
y = para(c, 'Real <b>samples</b>: breaking glass when a row clears, an explosion for four rows, a thud for a hard drop, a bell for a new level, '
         'a heartbeat when the stack is high, a whoosh and a coin. Plus little synth sounds for bumping a wall, a turn that does not fit, '
         'the soft drop, pause, and a rumble when the game is over. Press <b>M</b> to switch the music off and on - the effects stay.', M, y, W - 2 * M, 8.4)
factbox(c, M, y - 10, W - 2 * M, 'FUNNY FACT',
        'Grieg himself was not a fan of his Mountain King. He wrote that he could hardly bear to listen to it, '
        'and complained that it smelled of cow dung and trollish self-satisfaction. He never heard it with drums, of course.', PURPLE)
end()

# ===================================================================== 11 tips
y = page('TIPS', 'Wisdom collected from the high score table.')
tips = [('KEEP IT FLAT', 'A flat stack takes any piece. A stack like a mountain range only takes the piece you do not have.'),
        ('LEAVE A WELL', 'Keep one column open at the side, stack the rest neatly, and wait for the long one: SUPER! 1200 points times the level.'),
        ('WATCH NEXT', 'Look at the NEXT box while the current block falls. Decide where both go.'),
        ('NO HOLES', 'A covered hole costs you a whole row until you dig it out. The S and the Z are the usual suspects.'),
        ('HARD DROP', 'When you know where it goes, push up. Faster game, double the drop points, and a nice thud.'),
        ('SLIDE IN', 'Use the lock delay: drop a block next to an overhang and slide it underneath before it locks.'),
        ('DO NOT PANIC', 'When the heartbeat starts, breathe. Clear a row or two near the top first, then rebuild.')]
for i, (t, d) in enumerate(tips):
    piece(c, 'IOTSZJL'[i], M, y - 6, 6.5)
    pixtext(c, t, M + 36, y - 9, 1.3, MAGENTA)
    y = para(c, d, M + 36, y - 13, W - 2 * M - 36, 8) - 9
factbox(c, M, y - 4, W - 2 * M, 'WATCH THE COMPUTER',
        'The demo player scores every possible spot for a piece: <b>76</b> points for each full row, minus <b>51</b> for height, '
        '<b>36</b> for each hole and <b>18</b> for bumpiness. Copy its homework.', CYAN)
end()

# ===================================================================== 12 funny facts
y = page('FUNNY FACTS', 'Things you did not need to know, now in print.')
facts = [
    ('7.09 MHZ', 'The Amiga 500\'s 68000 processor runs at 7.09 MHz (in Europe). Your toaster may have more computing power. Your toaster cannot play Stronkie\'s Blocks.'),
    ('5,629 LINES', 'The game is written in 68000 assembly language: 5,629 lines of it, plus 1,600 lines of Python tools that draw the backdrops and write the music tables.'),
    ('ONE SNOWFLAKE, MANY TIMES', 'The Amiga has only eight hardware sprites. The snow, bubbles and stars re-use them again and again down the screen, so there seem to be dozens.'),
    ('NOT BY BACH', 'The famous Minuet in G (TUNE B) was thought to be by J.S. Bach for 250 years. It is now believed to be by Christian Petzold. Bach is fine about it.'),
    ('ROBOT TESTERS', 'Before release every version was played by a robot in a home-made Amiga emulator: thousands of frames of random joystick waggling, without one crash.'),
    ('48 HOURS', 'Version 1.0 and the "final" V1.1 both came out on the same day. Then came V1.2, V1.3 and V1.4. The word "final" has lost all meaning.'),
    ('THE DISK', 'Both games, the loader, the picture and the manual text fit on one 880 KB floppy with more than 400 KB to spare.'),
]
for i, (t, d) in enumerate(facts):
    col = RAINBOW[(i * 3) % 8]
    c.setFillColor(col); c.circle(M + 9, y - 9, 9, stroke=0, fill=1)
    pixtext(c, '!', M + 9, y - 13, 1.1, INK, center=True)
    pixtext(c, t, M + 26, y - 10, 1.2, NAVY)
    y = para(c, d, M + 26, y - 14, W - 2 * M - 26, 7.8) - 9
end()

# ===================================================================== 13-14 dev diary
y = page('DEVELOPER DIARY', 'How a game is made in two days, told by the people who made it.')
diary = [
    ('V1.0', '14 NOV 2026', 'THE BEGINNING', 'Mark: "I want a Tetris clone for my Amiga 500 with the 512 KB trapdoor and Workbench 1.3." '
     'And so it began. Seven pieces with proper turning and wall kicks, the bag randomizer, the ghost outline, lock delay, '
     'a high score table saved on the disk and Korobeiniki on two channels. Everything tested in a home-made emulator before it touched real metal.',
     'StronkiesBlocks_V1.0_screenshots.png'),
    ('V1.1', '14 NOV 2026', 'MUSIC, SOUND, SHINE', 'A second tune (the Minuet), drums, jingles for game over and high scores, new sound effects, '
     'colour skies for every level, copper bars, stars and banners. First release on itch.io, for the price of one euro. A bargain. '
     'A steal. Practically charity.', 'StronkiesBlocks_V1.1_screenshots.png'),
    ('V1.2', '15 NOV 2026', '"THE GRAPHICS ARE BORING"', 'Mark said the graphics looked boring and the manual was missing. Ouch. Answer: 32 colours, '
     'five pixel-art worlds, sprite weather that flashes on the kick drum, glass blocks, chrome panels, particles, screen shake, '
     'a chrome logo with a moving shine, a rainbow scroll text, the manual in the game, a computer player for the demo, and real samples.',
     'StronkiesBlocks_V1.2_screenshots.png'),
]
for v, d, t, s, img in diary:
    y = entry(v, d, t, s, img, y)
end()

y = page('DIARY, PART 2', 'Wherein the word "final" is used again.')
diary2 = [
    ('V1.3', '15 NOV 2026', 'A LOADING SCREEN', 'Mark sent a picture and said: "Add this as loading screen." The loader now shows it in 32 Amiga colours '
     'while the game loads, with a progress bar that really knows how far it is. Then the text in the picture got fixed to say '
     'Kickstart 1.3, 512K chip RAM, Workbench 1.3 - because details matter.', 'v13_loading.png'),
    ('V1.4', '15 NOV 2026', 'THE ENHANCED EDITION', 'Box time! For the boxed release came this manual, disk labels and a fold-up box - '
     'and because the box says there is an Enhanced edition inside, there had to be one: ten worlds, a third tune by Grieg, and a loader '
     'clever enough to pick the right game for your Amiga. Honesty in advertising. In 2026. Imagine that.', 'v14_world6.png'),
]
for v, d, t, s, img in diary2:
    y = entry(v, d, t, s, img, y)
factbox(c, M, y, W - 2 * M, 'FROM THE DEVELOPERS',
        'The hardest bug? The loading bar stopping at 68% with ugly seams in the picture. The fix: tiling the picture properly. '
        'The best moment? Watching the computer play its first demo game and clear four rows at once. '
        'It did not celebrate. We did.', ORANGE)
end()

# ===================================================================== 15 credits
y = page('CREDITS', 'The people (and the machine) behind the blocks.')
cred = [('CREATED BY', 'Mark Stronks'), ('PUBLISHED BY', 'Stronkie Soft © 2026'), ('PROGRAMMING AI', 'Claude (Anthropic)'),
        ('MUSIC', 'Traditional (1861), Petzold (1725), Grieg (1875) - arranged for Paula'),
        ('GRAPHICS', 'Pixel art drawn in code, one block at a time'), ('TESTING', 'A robot in an emulator, and Mark Stronks'),
        ('SPECIAL THANKS', 'Everybody who still switches on an Amiga')]
for t, n in cred:
    pixtext(c, t, W / 2, y - 10, 1.3, MAGENTA, center=True)
    y = para(c, n, M, y - 14, W - 2 * M, 9.5, font='PopM', align=1) - 10
y = heading('TECHNICAL NOTES', M, y - 2, NAVY, 1.4)
y = para(c, 'Written in 68000 assembly, assembled with vasm. 32 colours on a 320×256 PAL screen (5 bitplanes), copper lists for the skies, '
         'eight hardware sprites for the weather, the blitter left in peace and the CPU doing the drawing. The OS stays alive while loading, '
         'so you return to Workbench when you quit. Source code: github.com/stronkie/Tetris-for-amiga-500', M, y, W - 2 * M, 7.6)
factbox(c, M, y - 10, W - 2 * M, 'GET IT',
        'stronkie.itch.io/stronkies-blocks - the latest version costs 1 euro; all older versions stay free to play, always.', GREEN)
end()

# ===================================================================== 16 back
PAGE[0] += 1
c.setFillColor(NAVY); c.rect(0, 0, W, H, stroke=0, fill=1)
for gx in range(0, int(W) + 1, 14):
    c.setStrokeColor(NAVY2); c.setLineWidth(0.4); c.line(gx, 0, gx, H)
for gy in range(0, int(H) + 1, 14): c.line(0, gy, W, gy)
block_row(c, 0, H - 40, W + 10, 12)
pixtext(c, 'LIMITED WARRANTY', W / 2, H - 80, 2.0, YELLOW, center=True, shadow=MAGENTA)
para(c, 'Stronkie Soft guarantees that this disk will be free of defects in material and workmanship for a period of 90 seconds from the date '
     'of purchase, or until you drop it in your tea, whichever comes first. Stronkie Soft is not responsible for lost sleep, missed buses, '
     'sore thumbs, or arguments about whose turn it is. Do not store the disk near magnets, televisions, radiators, dogs or younger brothers.',
     M + 10, H - 96, W - 2 * M - 20, 8.2, color=white, align=1)
# a tall stack of pieces
s = 15
stack = ['IIII.Z', 'OO.ZZT', 'OOSZTT', 'LSSJJT', 'LLLJ..']
cols = {'I': CYAN, 'O': YELLOW, 'T': PURPLE, 'S': GREEN, 'Z': RED, 'J': BLUE, 'L': ORANGE}
sx = W / 2 - 3 * s
for r, line in enumerate(stack):
    for k, ch in enumerate(line):
        if ch != '.': cell(c, sx + k * s, 250 - r * s, s, cols[ch])
pixtext(c, 'STRONKIE SOFT', W / 2, 115, 2.8, center=True, rows=CHROME, shadow=HexColor('#000000'))
c.setFillColor(GREY); c.setFont('PopM', 7.5)
c.drawCentredString(W / 2, 98, 'Software for machines that boot in two seconds and never ask to update.')
c.drawCentredString(W / 2, 60, "Stronkie's Blocks © 2026 Mark Stronks - Stronkie Soft. Programming AI: Claude.")
c.drawCentredString(W / 2, 49, 'Amiga is a trademark of its respective owner. Made with love for the Amiga 500.')
pixtext(c, 'MADE ON EARTH. PLAYED IN SPACE.', W / 2, 24, 1.1, CYAN, center=True)
end()

c.save()
print('wrote', OUT, PAGE[0], 'pages')
