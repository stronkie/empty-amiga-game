#!/usr/bin/env python3
"""adf.py - read and write AmigaDOS OFS floppy images (880 KB, DD).

  adf.py list  disk.adf
  adf.py get   disk.adf path out
  adf.py build out.adf "Volume Name" srcdir [bootblock_from.adf]

The image is written the way Kickstart 1.3's 'format' + 'install' leave a
disk (OFS, not international mode), so it boots on a stock A500.
"""
import struct, sys, os, time

BS = 512
NBLOCKS = 1760
ROOT = 880
HT = 72  # hash table size

T_HEADER, T_DATA, T_LIST = 2, 8, 16
ST_ROOT, ST_DIR, ST_FILE = 1, 2, -3


def u32(b, i): return struct.unpack_from('>I', b, i * 4)[0]
def s32(b, i): return struct.unpack_from('>i', b, i * 4)[0]


def checksum(blk, at=5):
    s = 0
    for i in range(128):
        if i != at:
            s = (s + u32(blk, i)) & 0xffffffff
    return (-s) & 0xffffffff


def boot_checksum(bb):
    s = 0
    for i in range(256):
        if i == 1:
            continue
        s += u32(bb, i)
        if s > 0xffffffff:
            s = (s + 1) & 0xffffffff
    return (~s) & 0xffffffff


def hashname(name):
    h = len(name)
    for c in name.upper():
        h = (h * 13 + ord(c)) & 0x7ff
    return h % HT


# ------------------------------------------------------------- reading
class Reader:
    def __init__(self, path):
        self.d = open(path, 'rb').read()

    def blk(self, n):
        return self.d[n * BS:(n + 1) * BS]

    def name(self, b):
        l = b[432]
        return b[433:433 + l].decode('latin1')

    def walk(self, n=ROOT, path=''):
        b = self.blk(n)
        for i in range(HT):
            e = u32(b, 6 + i)
            while e:
                eb = self.blk(e)
                nm = self.name(eb)
                st = s32(eb, 127)
                p = path + nm
                if st == ST_DIR:
                    yield p + '/', e, 0
                    yield from self.walk(e, p + '/')
                else:
                    yield p, e, u32(eb, 81)
                e = u32(eb, 124)

    def read(self, hdr):
        b = self.blk(hdr)
        size = u32(b, 81)
        out = bytearray()
        blocks = []
        h = hdr
        while h:
            hb = self.blk(h)
            cnt = u32(hb, 2)
            for i in range(cnt):
                blocks.append(u32(hb, 77 - i))
            h = u32(hb, 126)
        for d in blocks:
            db = self.blk(d)
            n = u32(db, 3)
            out += db[24:24 + n]
        return bytes(out[:size])


# ------------------------------------------------------------- writing
class Writer:
    def __init__(self, volname, bootblock=None):
        self.img = bytearray(NBLOCKS * BS)
        self.used = [False] * NBLOCKS
        self.used[0] = self.used[1] = True
        self.used[ROOT] = True
        self.used[ROOT + 1] = True  # bitmap
        self.nextfree = ROOT + 2
        self.dirs = {'': ROOT}
        self.entries = {ROOT: []}
        self.volname = volname
        self.boot = bootblock

    def alloc(self):
        # allocate after the root first (like the file system), then wrap
        order = list(range(self.nextfree, NBLOCKS)) + list(range(2, ROOT))
        for n in order:
            if not self.used[n]:
                self.used[n] = True
                self.nextfree = n + 1
                return n
        raise RuntimeError('disk full')

    def put(self, n, b):
        assert len(b) == BS
        self.img[n * BS:(n + 1) * BS] = b

    @staticmethod
    def stamp(b, at):
        # days since 1.1.1978, minutes, ticks
        t = time.time()
        days = int(t // 86400) - 2922
        mins = int((t % 86400) // 60)
        struct.pack_into('>III', b, at * 4, days, mins, 0)

    def header(self, n, name, stype, parent):
        b = bytearray(BS)
        struct.pack_into('>I', b, 0, T_HEADER)
        struct.pack_into('>I', b, 4, n)
        nm = name.encode('latin1')
        b[432] = len(nm)
        b[433:433 + len(nm)] = nm
        self.stamp(b, 105)
        struct.pack_into('>I', b, 125 * 4, parent)
        struct.pack_into('>i', b, 127 * 4, stype)
        return b

    def mkdir(self, path):
        parent = self.dirs[os.path.dirname(path)]
        n = self.alloc()
        self.entries[parent].append((os.path.basename(path), n, None))
        self.dirs[path] = n
        self.entries[n] = []
        self.pending_dir = getattr(self, 'pending_dir', [])
        self.pending_dir.append((n, os.path.basename(path), parent))

    def addfile(self, path, data):
        parent = self.dirs[os.path.dirname(path)]
        name = os.path.basename(path)
        hdr = self.alloc()
        nblk = (len(data) + 487) // 488
        datablocks = [self.alloc() for _ in range(nblk)]
        # header + extension blocks, 72 pointers each
        chunks = [datablocks[i:i + 72] for i in range(0, max(nblk, 1), 72)] or [[]]
        exts = [self.alloc() for _ in range(len(chunks) - 1)]
        hb = self.header(hdr, name, ST_FILE, parent)
        for ci, chunk in enumerate(chunks):
            b = hb if ci == 0 else bytearray(BS)
            if ci > 0:
                struct.pack_into('>I', b, 0, T_LIST)
                struct.pack_into('>I', b, 4, exts[ci - 1])
                struct.pack_into('>i', b, 127 * 4, ST_FILE)
                struct.pack_into('>I', b, 125 * 4, hdr)
            struct.pack_into('>I', b, 8, len(chunk))
            if chunk:
                struct.pack_into('>I', b, 16, chunk[0])
            for i, d in enumerate(chunk):
                struct.pack_into('>I', b, (77 - i) * 4, d)
            if ci + 1 < len(chunks):
                struct.pack_into('>I', b, 126 * 4, exts[ci])
            if ci == 0:
                struct.pack_into('>I', b, 81 * 4, len(data))
                self.file_hdr = b
            else:
                struct.pack_into('>I', b, 5 * 4, checksum(b))
                self.put(exts[ci - 1], bytes(b))
        for i, d in enumerate(datablocks):
            db = bytearray(BS)
            part = data[i * 488:(i + 1) * 488]
            struct.pack_into('>IIIIII', db, 0, T_DATA, hdr, i + 1, len(part),
                             datablocks[i + 1] if i + 1 < nblk else 0, 0)
            db[24:24 + len(part)] = part
            struct.pack_into('>I', db, 20, checksum(db))
            self.put(d, bytes(db))
        self.entries[parent].append((name, hdr, hb))

    def finish(self, path):
        # directories: build hash chains
        allhdrs = {}
        for n, name, parent in getattr(self, 'pending_dir', []):
            allhdrs[n] = self.header(n, name, ST_DIR, parent)
        for parent, ents in self.entries.items():
            table = [0] * HT
            # chains: newest first is fine; keep sorted for determinism
            for name, n, hb in sorted(ents, key=lambda e: e[0].lower(), reverse=True):
                h = hashname(name)
                b = hb if hb is not None else allhdrs[n]
                struct.pack_into('>I', b, 124 * 4, table[h])
                table[h] = n
            if parent == ROOT:
                pb = self.rootblk = bytearray(BS)
                struct.pack_into('>I', pb, 0, T_HEADER)
                struct.pack_into('>I', pb, 12, HT)
                struct.pack_into('>i', pb, 78 * 4, -1)  # bm_flag valid
                struct.pack_into('>I', pb, 79 * 4, ROOT + 1)
                self.stamp(pb, 105)
                self.stamp(pb, 121)
                self.stamp(pb, 123)
                nm = self.volname.encode('latin1')
                pb[432] = len(nm)
                pb[433:433 + len(nm)] = nm
                struct.pack_into('>i', pb, 127 * 4, ST_ROOT)
            else:
                pb = allhdrs[parent]
            for i, v in enumerate(table):
                struct.pack_into('>I', pb, (6 + i) * 4, v)
        for parent, ents in self.entries.items():
            for name, n, hb in ents:
                b = hb if hb is not None else allhdrs[n]
                struct.pack_into('>I', b, 20, 0)
                struct.pack_into('>I', b, 20, checksum(b))
                self.put(n, bytes(b))
        rb = self.rootblk
        struct.pack_into('>I', rb, 20, checksum(rb))
        self.put(ROOT, bytes(rb))
        # bitmap: bit set = free, blocks 2..1759
        bm = bytearray(BS)
        words = [0] * 55
        for n in range(2, NBLOCKS):
            if not self.used[n]:
                i = n - 2
                words[i // 32] |= 1 << (i % 32)
        for i, w in enumerate(words):
            struct.pack_into('>I', bm, 4 + i * 4, w)
        struct.pack_into('>I', bm, 0, checksum(bm, 0))
        self.put(ROOT + 1, bytes(bm))
        # boot block
        if self.boot:
            bb = bytearray(self.boot[:1024])
        else:
            bb = bytearray(1024)
            bb[0:4] = b'DOS\0'
            struct.pack_into('>I', bb, 8, ROOT)
            code = bytes.fromhex('43fa001e4eaeffa04a80670a20402068001670004e7570ff4e75') + b'dos.library\0'
            bb[12:12 + len(code)] = code
        struct.pack_into('>I', bb, 4, 0)
        struct.pack_into('>I', bb, 4, boot_checksum(bb))
        self.img[0:1024] = bb
        open(path, 'wb').write(self.img)
        free = sum(1 for n in range(2, NBLOCKS) if not self.used[n])
        return free


def build(out, vol, src, bootfrom=None):
    boot = open(bootfrom, 'rb').read(1024) if bootfrom else None
    w = Writer(vol, boot)
    for root, dirs, files in os.walk(src):
        dirs.sort()
        rel = os.path.relpath(root, src)
        rel = '' if rel == '.' else rel
        for d in dirs:
            w.mkdir(os.path.join(rel, d) if rel else d)
        for f in sorted(files):
            w.addfile(os.path.join(rel, f) if rel else f, open(os.path.join(root, f), 'rb').read())
    free = w.finish(out)
    return free


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'list':
        r = Reader(sys.argv[2])
        for p, n, s in r.walk():
            print('%-40s %7d  (block %d)' % (p, s, n))
    elif cmd == 'get':
        r = Reader(sys.argv[2])
        for p, n, s in r.walk():
            if p == sys.argv[3]:
                open(sys.argv[4], 'wb').write(r.read(n))
    elif cmd == 'build':
        free = build(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else None)
        print('free blocks:', free, '(%d KB)' % (free * 488 // 1024))
