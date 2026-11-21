# Packer for the floppy builds (Stronkie Soft)

Makes the game file on the disk smaller so the game loads about twice as fast
from floppy. The packed file starts with a small unpacker (stub.s) that unpacks
every hunk in place, relocates and jumps into the game - it works with DOS
LoadSeg and with the games' own hunk loaders. Only the ADF builds use it; the
hard drive and WHDLoad builds stay unpacked.

    gcc -O2 -o lz lz.c
    gcc -O2 -o harness harness.c m68k.c
    python3 asm68k.py stub.s -o stub.exe -map stub.map   (asm68k.py from tools/)
    python3 crunch.py Game.game Game.packed

crunch.py also runs the stub on the 68000 interpreter (harness.c + m68k.c) and
checks that the unpacked program is byte for byte what LoadSeg gives for the
original file. adfput.py replaces a file inside an OFS .adf in place (keeps
protection bits, icons and the boot block). make_release.py is the script that
made the 21-11-2026 fast-loading releases.
