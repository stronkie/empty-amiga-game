# Building a game

## Project layout (one GitHub repo per game: stronkie/<repo>)
```
README.md            what it is, files, controls, changelog ("Not yet on itch" section for builds waiting for Sunday)
ReadMe.txt           the ReadMe that goes on the disk
src/                 main.s (the game), loader.s (optional: loading picture, memory check, picks normal/Enhanced),
                     install.s (hard disk installer), whdload.s (the WHDLoad slave)
tools/build.sh       from templates/build.sh
art/  screenshots/  print/  previous versions/  itch/
```

## Tools (after `. setup.sh`)
- Assemble: `vasmm68k_mot -quiet -Fhunkexe -kick1hunks -nosym -o build/Game src/main.s` (`-DDEMO=1` / `-DENHANCED` for the other builds). `tools/asm68k.py` works too and needs no build.
- Icons: `python3 $AMIGA_TK/tools/make_icon.py build/Game.info` (see `make_disk.py` for drawer / disk / WHDLoad project icons).
- Disk: put the files in a folder with `s/startup-sequence`, then
  `python3 $AMIGA_TK/tools/adf.py build out.adf "Volume Name" folder $AMIGA_TK/tools/bootblock.bin`.
  Read a disk: `adf.py list disk.adf`, `adf.py get disk.adf path out`.
- Replace one file on an existing disk: `adfput.Disk(path).put(name, data)` then `.save(out)`.
- Loading screen: `make_loading.py picture.png out.bin out_gen.s preview.png`.

## Packing the floppy build (always)
`python3 $AMIGA_TK/tools/pack/crunch.py build/Game build/disk/Game`
- Packs every code/data hunk (about 35-55 % of the size), adds a small unpacker hunk; unpacking takes 1-3.5 s on a 7 MHz A500 and the game starts about twice as fast from floppy.
- Works with DOS LoadSeg and with the games' own hunk loaders (the unpacker finds the hunks through relocations), costs only a few KB of memory.
- It runs the unpacker on the 68000 interpreter and stops with an error unless the unpacked program is byte for byte what LoadSeg gives for the original. Still boot the new disk once (TESTING.md).
- Only the ADF gets the packed file; the hard drive zip and WHDLoad keep the plain program (the WHDLoad slaves load hunks without an OS).
- `make_release.py` is an example that packs the game files on existing ADFs and bumps the version strings.

## Delivering a build
- ADF(s) + WHDLoad + hard drive zip to `C:\Users\mstro\Downloads\Stronkie Soft\Amiga Games\<game folder>` (move the builds they replace into its old-versions folder) and to `C:\Users\mstro\Dropbox\Amiga\<Game name>` (device_commit_files from `/mnt/user-data/outputs/`). See RELEASE.md for all of Mark's folders.
- Push to the game's repo (README changelog under "Not yet on itch" unless Mark asked to publish now).
