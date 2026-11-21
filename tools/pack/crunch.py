#!/usr/bin/env python3
"""crunch.py - pack an Amiga hunk executable with the Stronkie Soft unpacker
and prove the packed file gives exactly the same program in memory.

  crunch.py in.exe out.exe
"""
import os, struct, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hunk

HERE = os.path.dirname(os.path.abspath(__file__))
LZ = os.path.join(HERE, 'lz')
HARN = os.path.join(HERE, 'harness')


def stubcode():
    hs = hunk.parse(open(os.path.join(HERE, 'stub.exe'), 'rb').read())
    code = [h for h in hs if h.data][0]
    assert not code.relocs
    syms = {}
    for line in open(os.path.join(HERE, 'stub.map')):
        f = line.split()
        if len(f) == 3 and f[0] == 'stub':
            syms[f[2]] = int(f[1], 16)
    assert syms['Table'] == len(code.data)
    return code.data, syms['bases']


def r4(n):
    return (n + 3) & ~3


def pack(data):
    with tempfile.TemporaryDirectory() as t:
        a, b = os.path.join(t, 'a'), os.path.join(t, 'b')
        open(a, 'wb').write(data)
        p, margin = map(int, subprocess.check_output([LZ, a, b]).split())
        packed = open(b, 'rb').read()
        subprocess.check_call([LZ, '-d', b, a + '.u', str(len(data))])
        assert open(a + '.u', 'rb').read() == data, 'packer round trip failed'
    return packed, margin


def relocstream(hunks):
    out = bytearray()
    for i, h in enumerate(hunks):
        for tgt, offs in sorted(h.relocs.items()):
            if not offs:
                continue
            out += struct.pack('>HHI', i, tgt, len(offs))
            cur = 0
            for o in offs:
                assert o % 2 == 0, 'odd relocation offset'
                d = o - cur
                if 0 < d <= 510 and d % 2 == 0:
                    out.append(d // 2)
                else:
                    out += b'\0' + struct.pack('>I', o)
                cur = o
            if len(out) % 2:
                out.append(0)
    out += b'\xff\xff'
    return bytes(out)


def build(orig_bytes):
    hs = hunk.parse(orig_bytes)
    assert len(hs) <= 64, 'too many hunks for the stub'
    table = bytearray(struct.pack('>H', len(hs)))
    newh = []
    info = []
    for h in hs:
        mode, P, U, S = 0, 0, len(h.data), r4(h.alloc)
        if h.kind != hunk.HUNK_BSS and len(h.data) >= 1024:
            packed, margin = pack(h.data)
            if len(packed) < 0.92 * len(h.data):
                mode = 1
                P = r4(len(packed))
                S = max(r4(h.alloc), r4(len(h.data)), r4(P + margin + 4))
                data = packed + b'\0' * (P - len(packed))
        if mode == 0:
            P = 0
            data = h.data
        table += struct.pack('>HIII', mode, P, U, S)
        newh.append({'kind': h.kind if h.kind != hunk.HUNK_BSS else hunk.HUNK_BSS, 'memflags': h.memflags,
                     'alloc': S, 'data': data})
        info.append((mode, len(h.data), P, S))
    table += relocstream(hs)
    code, bases = stubcode()
    stub = code + bytes(table)
    # the loader fills in the start of every game hunk (works with any hunk loader)
    first = {'kind': hunk.HUNK_CODE, 'memflags': 0, 'alloc': r4(len(stub)), 'data': stub,
             'relocs': {i + 1: [bases + 4 * i] for i in range(len(hs))}}
    return hunk.write([first] + newh), hs, info


def verify(orig_hunks, packed_bytes):
    """Load the packed file the way any hunk loader does (allocate every hunk,
    copy its data, relocate), run the stub on the 68000 interpreter and check
    that the game hunks are exactly what the original file gives."""
    ph = hunk.parse(packed_bytes)
    mem = bytearray(4 << 20)
    eb = 0x1000  # a fake ExecBase: Kickstart 1.3 (version 34), plain 68000
    struct.pack_into('>I', mem, 4, eb)
    struct.pack_into('>H', mem, eb + 20, 34)
    addr = 0x4000
    pb = []
    for h in ph:
        pb.append(addr)
        addr = (addr + r4(h.alloc) + 72) & ~7
    assert addr < (4 << 20) - 0x10000
    img = hunk.loadseg(ph, pb)
    for i, h in enumerate(ph):
        m = img[i]
        # garbage past the data, as a loader without MEMF_CLEAR leaves it
        for k in range(len(h.data), len(m)):
            m[k] = (k * 37 + 11) & 255
        mem[pb[i]:pb[i] + len(m)] = m
    bases = pb[1:]
    sp = (4 << 20) - 0x100
    struct.pack_into('>I', mem, sp, 0xC0DE0000)
    with tempfile.TemporaryDirectory() as t:
        mi, mo = os.path.join(t, 'm'), os.path.join(t, 'o')
        open(mi, 'wb').write(mem)
        res = subprocess.run([HARN, mi, str(pb[0]), str(sp), '0x1234', '0x5678', str(bases[0]), mo],
                             capture_output=True, text=True)
        if res.returncode:
            raise SystemExit('harness failed: ' + res.stderr + res.stdout)
        out = open(mo, 'rb').read()
    f = res.stdout.split()
    regs = dict(zip(f[0::2], f[1::2]))
    assert regs['d0'] == '1234' and regs['a0'] == '5678', regs
    assert int(regs['a7'], 16) == sp, regs
    want = hunk.loadseg(orig_hunks, bases)
    for i, h in enumerate(orig_hunks):
        if h.kind == hunk.HUNK_BSS:
            continue
        got = out[bases[i]:bases[i] + h.alloc]
        if got != bytes(want[i][:h.alloc]):
            bad = next(k for k in range(h.alloc) if got[k] != want[i][k])
            raise SystemExit('hunk %d differs at offset %d' % (i, bad))
    return int(regs['cycles'])


def main():
    src, dst = sys.argv[1], sys.argv[2]
    orig = open(src, 'rb').read()
    packed, hs, info = build(orig)
    cyc = verify(hs, packed)
    open(dst, 'wb').write(packed)
    mem_before = sum(r4(h.alloc) for h in hs)
    mem_after = sum(r4(h['alloc']) if False else 0 for h in []) + sum(i[3] for i in info) + r4(len(packed) and 0)
    ph = hunk.parse(packed)
    mem_after = sum(r4(h.alloc) for h in ph)
    print('%s: %d -> %d bytes (%.0f%%), memory %d -> %d (+%d), unpack %.2f s on a 7 MHz 68000'
          % (os.path.basename(src), len(orig), len(packed), 100.0 * len(packed) / len(orig),
             mem_before, mem_after, mem_after - mem_before, cyc / 7.09e6))


if __name__ == '__main__':
    main()
