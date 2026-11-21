#!/usr/bin/env python3
"""Build the fast-loading releases: pack the game files on each disk."""
import os, subprocess, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '/home/claude/sun/blocks/tools')
import adfput, crunch, hunk, adf

U = '/mnt/user-data/uploads/Amiga/'
OUT = '/home/claude/vcheck/crunch/out/'
os.makedirs(OUT, exist_ok=True)

NOTE = {
 'bs': ("V2.1  21 November 2026  Faster loading from floppy: the game file is packed\n"
        "      (674 KB -> 271 KB) and unpacks itself in about 3 seconds. Nothing\n"
        "      else changed: the same game as V2.0.\n"),
 'pd': ("V2.1  21 November 2026  Faster loading from floppy: the game file is packed\n"
        "      (542 KB -> 248 KB) and unpacks itself in about 3 seconds. Nothing\n"
        "      else changed: the same game as V2.0.\n"),
 'bb': ("V3.2 / Enhanced V2.2  21 November 2026  Faster loading from floppy: the\n"
        "      game files are packed (500 KB -> 225 KB, Enhanced 332 KB -> 279 KB)\n"
        "      and unpack themselves in a few seconds. Nothing else changed.\n"),
 'sl': ("V2.8  21 November 2026  Faster loading from floppy: the game file is packed\n"
        "      (521 KB -> 273 KB) and unpacks itself in about 3 seconds. Nothing\n"
        "      else changed: the same game as V2.7.\n"),
 'wc': ("V1.1  21 November 2026  Faster loading from floppy: the three games are\n"
        "      packed (779 KB -> 291 KB, the disk now has room to spare) and\n"
        "      unpack themselves in about a second. Nothing else changed.\n"),
}

JOBS = [
 # src adf, out adf, [(file, patches)], readme, note
 ("Stronkie's Battleships/StronkiesBattleships_V2.0.adf", 'StronkiesBattleships_V2.1.adf',
  [('SBattle.game', [(b'V2.0 FINAL RELEASE', b'V2.1 FINAL RELEASE')])], 'ReadMe.txt', 'bs'),
 ("Battleships/StronkiesBattleships_V2.0_Enhanced.adf", 'StronkiesBattleships_V2.1_Enhanced.adf',
  [('SBattle.game', [(b'V2.0 ENHANCED: ACA500', b'V2.1 ENHANCED: ACA500'),
                     (b'PLEASE PLAY THE NORMAL V2.0', b'PLEASE PLAY THE NORMAL V2.1')])], 'ReadMe.txt', 'bs'),
 ("Stronkie's Pipedream/StronkiesPipedream_V2.0.adf", 'StronkiesPipedream_V2.1.adf',
  [('Pipedream.game', [(b'\0V2.0\0', b'\0V2.1\0')])], 'ReadMe.txt', 'pd'),
 ("Stronkie's Baseball/StronkiesBaseball_V3.1.adf", 'StronkiesBaseball_V3.2.adf',
  [('SBaseball.game', [])], 'ReadMe', 'bb'),
 ("Stronkie's Baseball/StronkiesBaseball_Enhanced_V2.1_disk1.adf", 'StronkiesBaseball_Enhanced_V2.2_disk1.adf',
  [('SBaseball.game', [])], 'ReadMe', 'bb'),
 ("Stronkie's Baseball/StronkiesBaseball_Enhanced_V2.1_disk2.adf", 'StronkiesBaseball_Enhanced_V2.2_disk2.adf',
  [('SBaseballE.game', [])], 'ReadMe', 'bb'),
 ("Stronkie's Slot Machine/StronkiesSlotMachine_V2.7.adf", 'StronkiesSlotMachine_V2.8.adf',
  [('SSlots.game', [])], 'ReadMe.txt', 'sl'),
 ("The Wurtel Collection/The_Wurtel_Collection_V1.0.adf", 'The_Wurtel_Collection_V1.1.adf',
  [('Wurtel1', []), ('Wurtel2', []), ('Wurtel3', [])], 'ReadMe', 'wc'),
]


VER = {'bs': [('V2.0', 'V2.1')], 'pd': [('V2.0', 'V2.1')], 'bb': [('V3.1', 'V3.2'), ('Enhanced V2.1', 'Enhanced V2.2')],
       'sl': [('V2.6', 'V2.8'), ('V2.7', 'V2.8')], 'wc': []}


def readme_note(text, note, nk=None):
    lines = text.split('\n')
    for i in range(min(4, len(lines))):
        for a, b in VER.get(nk, []):
            lines[i] = lines[i].replace(a, b)
    # put the note after the first block (title lines) - simply at the top, after line 1
    k = 1
    if len(lines) > 1 and lines[1].strip() and set(lines[1].strip()) <= set('=-'):
        k = 2
    return '\n'.join(lines[:k] + ['', 'NEW: ' + note.rstrip('\n'), ''] + lines[k:])


report = []
for src, dst, files, readme, nk in JOBS:
    dk = adfput.Disk(U + src)
    before = dk.freecount()
    for name, patches in files:
        data = dk.read(name)
        for a, b in patches:
            assert len(a) == len(b) and data.count(a) == 1, (name, a, data.count(a))
            data = data.replace(a, b)
        packed, hs, info = crunch.build(data)
        cyc = crunch.verify(hs, packed)
        dk.put(name, packed)
        report.append((dst, name, len(data), len(packed), round(cyc / 7.09e6, 2)))
    if readme:
        t = dk.read(readme).decode('latin1')
        t2 = readme_note(t, NOTE[nk], nk).replace('\n', '\n')
        if t.find('\r\n') >= 0:
            t2 = t2.replace('\r\n', '\n').replace('\n', '\r\n')
        dk.put(readme, t2.encode('latin1'))
    dk.save(OUT + dst)
    # check: every file reads back with the reference reader
    r = adf.Reader(OUT + dst)
    for p, h, s in r.walk():
        if not p.endswith('/'):
            assert len(r.read(h)) == s
    for name, patches in files:
        d = [r.read(h) for p, h, s in r.walk() if p == name][0]
        hunk.parse(d)
    report.append((dst, 'free KB', before // 2, dk.freecount() // 2, ''))
for r in report:
    print(r)
json.dump(report, open(OUT + 'report.json', 'w'))
