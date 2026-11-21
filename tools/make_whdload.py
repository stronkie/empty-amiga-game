#!/usr/bin/env python3
"""make_whdload.py - the WHDLoad install of Stronkie's Slot Machine.

  build/whdload/StronkiesSlotMachine/            the drawer
      StronkiesSlotMachine.slave                 src/whdload_slave.s
      StronkiesSlotMachine.info                  project icon: default tool WHDLoad
      SSlots.game                                the game (the slave loads it)
      ReadMe.txt
  build/whdload/StronkiesSlotMachine.info        the drawer's icon
  build/StronkiesSlotMachine_V<ver>_WHDLoad.lha  all of it in an LhA archive

The archive is written here, without an LhA program: level 2 headers, method
-lh0- (stored).  Every LhA unpacks it (lha x, LhA on the Amiga, 7-Zip...).
Usage: make_whdload.py <version>"""
import os, sys, struct, time, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from make_disk import icon_image, drawer_image, planes

VER = sys.argv[1] if len(sys.argv) > 1 else '2.7'
B = os.path.join(ROOT, 'build')
DRAWER = 'StronkiesSlotMachine'
SLAVE = DRAWER + '.slave'

# ---------------------------------------------------------------- icons
def bstr(s):
    b = s.encode('latin-1') + b'\0'
    return struct.pack('>I', len(b)) + b

def diskobject(kind, im, tool=None, tooltypes=(), stack=8192):
    """kind: 4 = WBPROJECT, 2 = WBDRAWER.  Written like make_disk.diskobject, with
    a default tool and tool types."""
    W, H = im.size
    o = struct.pack('>HH', 0xe310, 1)
    o += struct.pack('>IhhhhHHHIIIiIHI', 0, 0, 0, W, H, 5, 3, 1, 1, 0, 0, 0, 0, 0, 0)
    o += struct.pack('>BB', kind, 0)
    o += struct.pack('>IIiiIIi', 1 if tool else 0, 1 if tooltypes else 0,
                     -0x80000000, -0x80000000, 1 if kind == 2 else 0, 0, stack)
    assert len(o) == 78
    if kind == 2:
        nw = struct.pack('>hhhhBBIIIIIIIhhhhH', 50, 30, 360, 120, 255, 255, 0, 0x5f, 0, 0, 0, 0, 0, 90, 40, -1, -1, 1)
        o += nw + struct.pack('>ii', 0, 0)
    o += struct.pack('>hhhhhIBBI', 0, 0, W, H, 2, 1, 3, 0, 0)
    o += planes(im)
    if tool:
        o += bstr(tool)
    if tooltypes:
        o += struct.pack('>I', (len(tooltypes) + 1) * 4)
        for t in tooltypes:
            o += bstr(t)
    return o

# ---------------------------------------------------------------- LhA
def crc16(data, crc=0):
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc

def lha_entry(path, data, mtime, is_dir=False):
    """One level 2 header (+ the data).  path uses '/'; a directory ends with '/'."""
    parts = path.rstrip('/').split('/')
    if is_dir:
        dirname, fname = parts, []
    else:
        dirname, fname = parts[:-1], parts[-1]
    ext = b''
    def exth(t, payload):
        return struct.pack('<B', t) + payload
    exts = [exth(0x00, b'\0\0')]                       # header CRC, filled in below
    if fname:
        exts.append(exth(0x01, fname.encode('latin-1')))
    if dirname:
        exts.append(exth(0x02, b''.join(d.encode('latin-1') + b'\xff' for d in dirname)))
    # every extended header: type, data, size of the next one (2 bytes)
    blob = b''
    sizes = [len(e) + 2 for e in exts]
    for i, e in enumerate(exts):
        nxt = sizes[i + 1] if i + 1 < len(exts) else 0
        blob += e + struct.pack('<H', nxt)
    method = b'-lhd-' if is_dir else b'-lh0-'
    body = data if not is_dir else b''
    total = 26 + len(blob)
    h = struct.pack('<H5sIIIBBHBH', total, method, len(body), len(body), int(mtime),
                    0x20, 2, crc16(body), ord('A'), sizes[0])
    h = bytearray(h + blob)
    assert len(h) == total
    hc = crc16(bytes(h))                              # the header CRC: over the whole header
    h[26 + 1:26 + 3] = struct.pack('<H', hc)
    return bytes(h) + body

def write_lha(path, entries):
    with open(path, 'wb') as f:
        for e in entries:
            f.write(e)
        f.write(b'\0')

def read_lha(path):
    """A small independent reader, to check what was written: [(name, data)]."""
    d = open(path, 'rb').read(); p = 0; out = []
    while d[p] != 0:
        total, method, csize, osize, mtime, attr, level, crc, osid, nxt = struct.unpack('<H5sIIIBBHBH', d[p:p + 26])
        assert level == 2 and method in (b'-lh0-', b'-lhd-')
        q = p + 26; fname = ''; dname = ''; hcrc = None
        while nxt:
            t = d[q]; payload = d[q + 1:q + nxt - 2]
            if t == 0: hcrc = struct.unpack('<H', payload)[0]; hcrc_at = q + 1
            elif t == 1: fname = payload.decode('latin-1')
            elif t == 2: dname = '/'.join(x.decode('latin-1') for x in payload.split(b'\xff') if x)
            nxt = struct.unpack('<H', d[q + nxt - 2:q + nxt])[0]; q += len(payload) + 3
        assert q - p == total, 'header size'
        hb = bytearray(d[p:p + total]); hb[hcrc_at - p:hcrc_at - p + 2] = b'\0\0'
        assert crc16(bytes(hb)) == hcrc, 'header CRC'
        body = d[p + total:p + total + csize]
        assert csize == osize and crc16(body) == crc, 'data CRC'
        name = (dname + '/' if dname else '') + fname
        out.append((name if method == b'-lh0-' else dname + '/', body))
        p += total + csize
    return out

# ---------------------------------------------------------------- the install
def main():
    out = os.path.join(B, 'whdload'); shutil.rmtree(out, ignore_errors=True)
    dr = os.path.join(out, DRAWER); os.makedirs(dr)
    readme = open(os.path.join(ROOT, 'whdload', 'ReadMe.txt'), encoding='latin-1').read().replace('{VER}', VER)
    files = {
        SLAVE: open(os.path.join(B, SLAVE), 'rb').read(),
        DRAWER + '.info': diskobject(4, icon_image(), tool='WHDLoad',
                                     tooltypes=('SLAVE=' + SLAVE, 'PRELOAD', 'NOWRITECACHE')),
        'SSlots.game': open(os.path.join(B, 'SSlots.game'), 'rb').read(),
        'ReadMe.txt': readme.replace('\r\n', '\n').encode('latin-1'),
    }
    for n, b in files.items():
        open(os.path.join(dr, n), 'wb').write(b)
    drawer_info = diskobject(2, drawer_image())
    open(os.path.join(out, DRAWER + '.info'), 'wb').write(drawer_info)
    now = time.time()
    entries = [lha_entry(DRAWER + '/', b'', now, is_dir=True)]
    for n, b in files.items():
        entries.append(lha_entry(DRAWER + '/' + n, b, now))
    entries.append(lha_entry(DRAWER + '.info', drawer_info, now))
    arc = os.path.join(B, 'StronkiesSlotMachine_V%s_WHDLoad.lha' % VER)
    write_lha(arc, entries)
    back = dict(read_lha(arc))
    for n, b in files.items():
        assert back[DRAWER + '/' + n] == b, n
    assert back[DRAWER + '.info'] == drawer_info
    print('%s: %d bytes, %d entries (checked)' % (os.path.basename(arc), os.path.getsize(arc), len(entries)))

if __name__ == '__main__':
    main()
