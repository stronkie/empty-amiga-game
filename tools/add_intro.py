#!/usr/bin/env python3
"""add_intro.py - put the Stronkie Soft boot intro (SSIntro) on a game floppy.

  add_intro.py game.adf out.adf [SSIntro]

Copies every file of the disk, adds the (packed) SSIntro to the root and puts
"SSIntro" as the first line of s/startup-sequence. The boot block and the
volume name of the old disk are kept; the game files are not touched.
Default SSIntro: build it first with intro/build.sh (uses intro/disk/SSIntro,
the packed one)."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adf

src, out = sys.argv[1], sys.argv[2]
tk = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
intro = sys.argv[3] if len(sys.argv) > 3 else os.path.join(tk, 'intro', 'disk', 'SSIntro')
r = adf.Reader(src)
vol = r.name(r.blk(adf.ROOT))
tmp = tempfile.mkdtemp()
seq = None
for p, n, s in r.walk():
    dst = os.path.join(tmp, p)
    if p.endswith('/'):
        os.makedirs(dst, exist_ok=True)
        continue
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(r.read(n))
    if p.lower() == 's/startup-sequence':
        seq = dst
if seq is None:
    raise SystemExit('no s/startup-sequence on ' + src)
if any(p.lower() == 'ssintro' for p, n, s in r.walk()):
    print('SSIntro was already on the disk: replaced')
txt = open(seq, 'rb').read()
lines = [l for l in txt.split(b'\n') if l.strip().lower() != b'ssintro']
open(seq, 'wb').write(b'SSIntro\n' + b'\n'.join(lines))
open(os.path.join(tmp, 'SSIntro'), 'wb').write(open(intro, 'rb').read())
free = adf.build(out, vol, tmp, src)          # boot block from the old disk
print('%s -> %s  (volume "%s", %d KB free)' % (os.path.basename(src), os.path.basename(out), vol, free * 488 // 1024))
