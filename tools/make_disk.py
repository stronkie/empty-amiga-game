#!/usr/bin/env python3
"""make_disk.py - builds the release files for Stronkie's Slot Machine:

  build/StronkiesSlotMachine_V<ver>.adf            bootable OFS disk (Gotek / WinUAE)
  build/StronkiesSlotMachine_V<ver>_harddrive.zip  drawer for hard drive / CF card

Writes its own Kickstart 1.3 bootblock, OFS file system and Workbench icons.
Usage: python3 tools/make_disk.py 1.0
"""
import os, struct, subprocess, sys, zipfile
from PIL import Image, ImageDraw

VER = sys.argv[1] if len(sys.argv) > 1 else '1.0'
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
B = os.path.join(ROOT, os.environ.get('DISK_BUILD', 'build'))
GAME = 'SSlots'
DRAWER = os.environ.get('DISK_DRAWER', 'StronkiesSlotMachine')
VOLUME = os.environ.get('DISK_VOLUME', 'SlotMachine')

# ---------------------------------------------------------------- icons
WB13 = [(0x00, 0x55, 0xaa), (0xff, 0xff, 0xff), (0x00, 0x00, 0x00), (0xff, 0x88, 0x00)]

def icon_image():
    """52x30, 2 planes, Workbench 1.3 colours: 0 blue, 1 white, 2 black, 3 orange."""
    W, H = 52, 30
    im = Image.new('P', (W, H), 0); d = ImageDraw.Draw(im)
    d.rectangle([6, 2, 41, 27], fill=3, outline=2)          # cabinet
    d.rectangle([9, 5, 38, 8], fill=2)                     # top strip
    d.rectangle([9, 11, 38, 21], fill=1, outline=2)        # reel window
    for x in (18, 28): d.line([x, 11, x, 21], fill=2)
    for k, x in enumerate((11, 21, 31)):                   # three sevens
        d.line([x, 13, x + 5, 13], fill=2); d.line([x + 5, 13, x + 2, 19], fill=2)
    d.rectangle([12, 23, 35, 25], fill=2)                  # coin tray
    d.line([43, 6, 47, 6], fill=2); d.line([47, 6, 47, 16], fill=2)   # lever
    d.ellipse([45, 2, 49, 6], fill=3, outline=2)
    d.line([42, 16, 47, 16], fill=2)
    return im

def install_image():
    """52x30: a floppy, an arrow and a hard disk - the installer."""
    W, H = 52, 30
    im = Image.new('P', (W, H), 0); d = ImageDraw.Draw(im)
    d.rectangle([2, 2, 17, 17], fill=2)                    # floppy
    d.rectangle([5, 2, 14, 7], fill=1); d.rectangle([11, 3, 13, 6], fill=2)
    d.rectangle([5, 11, 14, 17], fill=1)
    d.line([20, 10, 28, 10], fill=3); d.line([20, 11, 28, 11], fill=3)    # arrow
    d.polygon([(28, 6), (33, 10), (28, 15)], fill=3)
    d.rectangle([24, 17, 49, 27], fill=1, outline=2)       # hard disk
    d.line([26, 22, 40, 22], fill=2)
    d.rectangle([44, 21, 46, 23], fill=3)
    return im

def drawer_image():
    W, H = 52, 24
    im = Image.new('P', (W, H), 0); d = ImageDraw.Draw(im)
    d.rectangle([4, 3, 47, 21], fill=3, outline=2)
    d.rectangle([4, 3, 47, 8], fill=1, outline=2)
    d.rectangle([20, 12, 31, 15], fill=2)
    d.text((14, 9), '', fill=2)
    return im

def planes(im, depth=2):
    W, H = im.size; px = im.load(); wpr = (W + 15) // 16
    out = bytearray()
    for p in range(depth):
        for y in range(H):
            for w in range(wpr):
                v = 0
                for i in range(16):
                    x = w * 16 + i
                    if x < W and (px[x, y] >> p) & 1: v |= 0x8000 >> i
                out += struct.pack('>H', v)
    return bytes(out)

def diskobject(kind, im, stack=8192):
    """kind: 3 = WBTOOL, 2 = WBDRAWER."""
    W, H = im.size
    o = struct.pack('>HH', 0xe310, 1)
    # Gadget
    o += struct.pack('>IhhhhHHHIIIiIHI', 0, 0, 0, W, H, 5, 3, 1, 1, 0, 0, 0, 0, 0, 0)
    o += struct.pack('>BB', kind, 0)
    o += struct.pack('>IIiiIIi', 0, 0, -0x80000000, -0x80000000, 1 if kind == 2 else 0, 0, stack)
    assert len(o) == 78
    if kind == 2:
        nw = struct.pack('>hhhhBBIIIIIIIhhhhH', 50, 30, 360, 120, 255, 255, 0, 0x5f, 0, 0, 0, 0, 0, 90, 40, -1, -1, 1)
        o += nw + struct.pack('>ii', 0, 0)
    o += struct.pack('>hhhhhIBBI', 0, 0, W, H, 2, 1, 3, 0, 0)
    o += planes(im)
    return o

# ---------------------------------------------------------------- OFS
BS = 512
NBLK = 1760

def csum(block):
    s = 0
    for i in range(0, BS, 4):
        s = (s + struct.unpack('>I', block[i:i + 4])[0]) & 0xffffffff
    return (-s) & 0xffffffff

def bootsum(bb):
    s = 0
    for i in range(0, 1024, 4):
        s += struct.unpack('>I', bb[i:i + 4])[0]
        if s > 0xffffffff: s = (s + 1) & 0xffffffff
    return (~s) & 0xffffffff

def name_hash(name):
    h = len(name)
    for c in name.upper():
        h = (h * 13 + ord(c)) & 0x7ff
    return h % 72

def bcpl(name, n=31):
    b = name.encode('latin-1')[:n - 1]
    return bytes([len(b)]) + b + bytes(n - 1 - len(b))

class ADF:
    def __init__(self, volume):
        self.img = bytearray(NBLK * BS)
        self.used = {0, 1, 880, 881}
        self.next = 882
        self.dirs = {880: {}}     # dir block -> {hash: [entry blocks]}
        self.headers = {}         # block -> bytearray
        self.volume = volume

    def alloc(self):
        while self.next in self.used:
            self.next += 1
            if self.next >= NBLK: self.next = 2
        b = self.next; self.used.add(b); return b

    def put(self, blk, data):
        self.img[blk * BS:(blk + 1) * BS] = data

    def link(self, parent, name, blk):
        self.dirs[parent].setdefault(name_hash(name), []).append(blk)

    def mkdir(self, parent, name):
        blk = self.alloc()
        h = bytearray(BS)
        struct.pack_into('>II', h, 0, 2, blk)
        h[432:432 + 31] = bcpl(name)
        struct.pack_into('>I', h, 500, parent)
        struct.pack_into('>i', h, 508, 2)
        self.headers[blk] = h; self.dirs[blk] = {}
        self.link(parent, name, blk)
        return blk

    def addfile(self, parent, name, data):
        hdr = self.alloc()
        chunks = [data[i:i + 488] for i in range(0, len(data), 488)] or [b'']
        dblocks = [self.alloc() for _ in chunks]
        for i, (blk, c) in enumerate(zip(dblocks, chunks)):
            d = bytearray(BS)
            nxt = dblocks[i + 1] if i + 1 < len(dblocks) else 0
            struct.pack_into('>IIIII', d, 0, 8, hdr, i + 1, len(c), nxt)
            d[24:24 + len(c)] = c
            struct.pack_into('>I', d, 20, csum(d))
            self.put(blk, d)
        # header + extension blocks, 72 data pointers each, stored backwards
        groups = [dblocks[i:i + 72] for i in range(0, len(dblocks), 72)]
        h = bytearray(BS)
        struct.pack_into('>IIII', h, 0, 2, hdr, len(groups[0]), 0)
        struct.pack_into('>I', h, 16, dblocks[0])
        for i, b in enumerate(groups[0]):
            struct.pack_into('>I', h, 24 + (71 - i) * 4, b)
        struct.pack_into('>I', h, 324, len(data))
        h[432:432 + 31] = bcpl(name)
        struct.pack_into('>I', h, 500, parent)
        struct.pack_into('>i', h, 508, -3)
        prev = h; exts = []
        for g in groups[1:]:
            eb = self.alloc(); e = bytearray(BS)
            struct.pack_into('>III', e, 0, 16, eb, len(g))
            for i, b in enumerate(g):
                struct.pack_into('>I', e, 24 + (71 - i) * 4, b)
            struct.pack_into('>I', e, 500, hdr)
            struct.pack_into('>i', e, 508, -3)
            struct.pack_into('>I', prev, 504, eb)
            exts.append((eb, e)); prev = e
        for eb, e in exts:
            struct.pack_into('>I', e, 20, 0); struct.pack_into('>I', e, 20, csum(e)); self.put(eb, e)
        self.headers[hdr] = h
        self.link(parent, name, hdr)
        return hdr

    def finish(self, bootcode):
        # hash tables and chains
        root = bytearray(BS)
        struct.pack_into('>IIIII', root, 0, 2, 0, 0, 72, 0)
        tables = {880: root}
        for dblk, table in self.dirs.items():
            t = tables.get(dblk) or self.headers[dblk]
            for hsh, entries in table.items():
                struct.pack_into('>I', t, 24 + hsh * 4, entries[0])
                for a, b in zip(entries, entries[1:]):
                    struct.pack_into('>I', self.headers[a], 496, b)
        for blk, h in self.headers.items():
            struct.pack_into('>I', h, 20, 0); struct.pack_into('>I', h, 20, csum(h)); self.put(blk, h)
        # bitmap (1 = free), blocks 2..1759
        bm = bytearray(BS)
        for blk in range(2, NBLK):
            if blk not in self.used:
                i = blk - 2
                w = 4 + (i // 32) * 4
                v = struct.unpack('>I', bm[w:w + 4])[0] | (1 << (i % 32))
                struct.pack_into('>I', bm, w, v)
        struct.pack_into('>I', bm, 0, csum(bm))
        self.put(881, bm)
        struct.pack_into('>i', root, 312, -1)
        struct.pack_into('>I', root, 316, 881)
        days, mins = 17485, 20 * 60      # 14 Nov 2025-ish, constant so builds are reproducible
        struct.pack_into('>III', root, 420, days, mins, 0)
        root[432:432 + 31] = bcpl(self.volume)
        struct.pack_into('>III', root, 472, days, mins, 0)
        struct.pack_into('>III', root, 484, days, mins, 0)
        struct.pack_into('>I', root, 508, 1)
        struct.pack_into('>I', root, 20, csum(root))
        self.put(880, root)
        # bootblock
        bb = bytearray(1024)
        bb[0:4] = b'DOS\0'
        struct.pack_into('>I', bb, 8, 880)
        bb[12:12 + len(bootcode)] = bootcode
        struct.pack_into('>I', bb, 4, bootsum(bb))
        self.img[0:1024] = bb
        return bytes(self.img)

BOOT_SRC = """
; Kickstart 1.3 bootblock code: find dos.library and start it
	lea	dosname(pc),a1
	jsr	-96(a6)			; FindResident
	tst.l	d0
	beq.s	.err
	move.l	d0,a0
	move.l	22(a0),a0		; RT_INIT
	moveq	#0,d0
	rts
.err	moveq	#-1,d0
	rts
dosname	dc.b	'dos.library',0
	even
"""

def main():
    exe = open(os.path.join(B, GAME), 'rb').read()
    game = open(os.path.join(B, GAME + '.game'), 'rb').read()
    readme = open(os.path.join(ROOT, os.environ.get('DISK_README', 'ReadMe.txt')), 'rb').read().replace(b'\r\n', b'\n')
    bsrc = os.path.join(B, 'boot.s')
    open(bsrc, 'w').write(BOOT_SRC)
    subprocess.check_call([sys.executable, os.path.join(ROOT, 'tools', 'asm68k.py'), bsrc, '-raw', '-o', os.path.join(B, 'boot.bin')], stdout=subprocess.DEVNULL)
    boot = open(os.path.join(B, 'boot.bin'), 'rb').read()
    tool_icon = diskobject(3, icon_image())
    drawer_icon = diskobject(2, drawer_image())
    open(os.path.join(B, GAME + '.info'), 'wb').write(tool_icon)

    adf = ADF(VOLUME)
    adf.addfile(880, GAME, exe)
    adf.addfile(880, GAME + '.game', game)
    adf.addfile(880, GAME + '.info', tool_icon)
    adf.addfile(880, 'ReadMe.txt', readme)
    if os.environ.get('DISK_INSTALL', '1') == '1':     # the hard disk installer (full game only)
        adf.addfile(880, 'Install', open(os.path.join(B, 'Install'), 'rb').read())
        adf.addfile(880, 'Install.info', diskobject(3, install_image(), stack=8192))
        idata = adf.mkdir(880, 'InstallData')
        adf.addfile(idata, 'Drawer.info', drawer_icon)
    s = adf.mkdir(880, 'S')
    adf.addfile(s, 'Startup-Sequence', b'SSlots\n')
    img = adf.finish(boot)
    NAME = os.environ.get('DISK_NAME', 'StronkiesSlotMachine_V%s' % VER)
    adfname = os.path.join(B, NAME + '.adf')
    open(adfname, 'wb').write(img)

    zname = os.path.join(B, NAME + '_harddrive.zip')
    with zipfile.ZipFile(zname, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr(DRAWER + '/' + GAME, exe)
        z.writestr(DRAWER + '/' + GAME + '.game', game)
        z.writestr(DRAWER + '/' + GAME + '.info', tool_icon)
        z.writestr(DRAWER + '/ReadMe.txt', readme)
        z.writestr(DRAWER + '.info', drawer_icon)
    used = len(adf.used)
    print('%s: %d of %d blocks used; %s' % (os.path.basename(adfname), used, NBLK, os.path.basename(zname)))
    # preview of the icon
    ic = icon_image().convert('RGB')
    pal = icon_image().copy(); pal.putpalette(sum(WB13, ()) + (0, 0, 0) * 252)
    pal.convert('RGB').resize((52 * 4, 30 * 4), Image.NEAREST).save(os.path.join(B, 'icon_preview.png'))

if __name__ == '__main__':
    main()
