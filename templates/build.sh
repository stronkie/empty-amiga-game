#!/bin/sh
# build.sh template for a new Stronkie Soft Amiga 500 game.
# Copy to <game>/tools/build.sh and fill in NAME / EXE / VOL.
# Needs: . $AMIGA_TK/setup.sh   (vasm, packer)
set -e
cd "$(dirname "$0")/.."
TK=${AMIGA_TK:?run . amiga-toolkit/setup.sh first}
NAME=StronkiesGame          # file names: ${NAME}_V${VER}.adf ...
EXE=SGame                   # the program on the disk (+ loader if any)
VOL="Stronkies Game"        # disk name
VER=${VER:-0.1}
mkdir -p build
# 1. assemble (68000 only, Kickstart 3.1 target, no symbols in the release build)
vasmm68k_mot -quiet -m68000 -Fhunkexe -kick1hunks -nosym -o build/$EXE src/main.s
# 2. icon
python3 $TK/tools/make_icon.py build/$EXE.info
# 3. the floppy: packed program (loads ~2x faster), startup-sequence, ReadMe
rm -rf build/disk && mkdir -p build/disk/s
python3 $TK/tools/pack/crunch.py build/$EXE build/disk/$EXE
cp build/$EXE.info build/disk/; cp ReadMe.txt build/disk/ReadMe
printf '%s\n' "$EXE" > build/disk/s/startup-sequence
python3 $TK/tools/adf.py build build/${NAME}_V$VER.adf "$VOL" build/disk $TK/tools/bootblock.bin
# 4. hard drive / CF card zip (unpacked program)
rm -rf build/hd && mkdir -p build/hd/$NAME
cp build/$EXE build/$EXE.info build/hd/$NAME/; cp ReadMe.txt build/hd/$NAME/ReadMe
(cd build/hd && rm -f ../${NAME}_V${VER}_harddrive.zip && zip -qr ../${NAME}_V${VER}_harddrive.zip $NAME)
# 5. WHDLoad: own slave (no Kickstart image), see $TK/templates/whdload and docs/WHDLOAD.md
echo "built build/${NAME}_V$VER.adf"
