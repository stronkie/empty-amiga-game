#!/usr/bin/env python3
"""make_icon.py - Workbench 1.3 tool icon (52x26, 2 planes) for Stronkie's Blocks.
Colours of Workbench 1.3: 0 blue, 1 white, 2 black, 3 orange."""
import sys
from PIL import Image, ImageDraw

HDR = bytes.fromhex(
    'e310000100000000000000000034001b0005000300010000000100000000000000000000000000000000000000000000'
    '030000000000000000008000000080000000000000000000000000002000000000000034001a000200000001030000000000')
W, H = 52, 26

im = Image.new('P', (W, H), 0)
d = ImageDraw.Draw(im)
# falling blocks: a small stack and a T coming down (WB colours only)
def block(cx, cy, c):
    x, y = 4 + cx * 7, 2 + cy * 6
    d.rectangle([x, y, x + 6, y + 5], fill=c, outline=2)
    d.point((x + 1, y + 1), fill=1)
for cx, cy in ((2, 0), (1, 1), (2, 1), (3, 1)):          # the T, orange
    block(cx, cy, 3)
for cx, cy, c in ((0, 3, 1), (1, 3, 1), (4, 3, 3), (5, 3, 3), (6, 3, 3),
                  (0, 2, 1), (5, 2, 1), (6, 2, 1)):
    block(cx, cy, c)
data = bytearray()
for p in range(2):
    for y in range(H):
        for wd in range(4):
            v = 0
            for b in range(16):
                x = wd * 16 + b
                if x < W and (im.getpixel((x, y)) >> p) & 1:
                    v |= 0x8000 >> b
            data += v.to_bytes(2, 'big')
hdr = bytearray(HDR)
tail = b''
if len(sys.argv) > 3 and sys.argv[2] == 'project':
    # a project icon: double click starts the default tool (WHDLoad)
    # with these tool types
    tool = sys.argv[3].encode() + b'\0'
    tts = [t.encode() + b'\0' for t in sys.argv[4:]]
    hdr[48] = 4                                  # WBPROJECT
    hdr[50:54] = (1).to_bytes(4, 'big')          # do_DefaultTool (any non-zero)
    hdr[54:58] = (1).to_bytes(4, 'big')          # do_ToolTypes
    hdr[74:78] = (16384).to_bytes(4, 'big')      # stack
    tail += len(tool).to_bytes(4, 'big') + tool
    tail += ((len(tts) + 1) * 4).to_bytes(4, 'big')
    for t in tts:
        tail += len(t).to_bytes(4, 'big') + t
open(sys.argv[1], 'wb').write(bytes(hdr) + bytes(data) + tail)
pal = [0x00, 0x55, 0xaa, 0xff, 0xff, 0xff, 0, 0, 0, 0xff, 0x88, 0]
im.putpalette(pal + [0] * (768 - len(pal)))
im.convert('RGB').resize((W * 4, H * 4 * 2), Image.NEAREST).save(sys.argv[1] + '.png')
