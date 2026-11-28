#!/bin/sh
# build.sh - the Stronkie Soft boot intro (SSIntro) + its test disk
set -e
cd "$(dirname "$0")"
: "${AMIGA_TK:=$(cd .. && pwd)}"
python3 make_assets.py                       # pictures, palette, tables -> build/, src/tables_gen.s
(cd src && "$AMIGA_TK/bin/vasmm68k_mot" -m68000 -quiet -Fhunkexe -kick1hunks -nosym -o ../build/SSIntro intro.s)
mkdir -p disk/s
python3 "$AMIGA_TK/tools/pack/crunch.py" build/SSIntro disk/SSIntro
printf 'SSIntro\necho "Stronkie Soft boot intro V1.0 - done, the game would start now."\n' > disk/s/startup-sequence
python3 "$AMIGA_TK/tools/adf.py" build build/StronkieSoftIntro_V1.0.adf "Stronkie Soft Intro" disk "$AMIGA_TK/tools/bootblock.bin"
