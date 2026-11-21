/* harness.c - run the unpacker stub on the 68000 interpreter.
 * usage: harness mem.bin pc sp d0 a0 stoppc out.bin
 * mem.bin is a flat 4 MB image; runs until PC == stoppc. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include "m68k.h"

#define MEMSZ (4u << 20)
static uint8_t *M;
static unsigned stoppc;
static int hit;
static long long total;

unsigned int m68k_read_memory_8(unsigned int a) { a &= 0xffffff; return a < MEMSZ ? M[a] : 0; }
unsigned int m68k_read_memory_16(unsigned int a) {
	if (a & 1) { fprintf(stderr, "odd word read %x\n", a); exit(3); }
	return m68k_read_memory_8(a) << 8 | m68k_read_memory_8(a + 1);
}
unsigned int m68k_read_memory_32(unsigned int a) { return m68k_read_memory_16(a) << 16 | m68k_read_memory_16(a + 2); }
void m68k_write_memory_8(unsigned int a, unsigned int v) { a &= 0xffffff; if (a < MEMSZ) M[a] = v; else { fprintf(stderr, "write out of memory %x\n", a); exit(3); } }
void m68k_write_memory_16(unsigned int a, unsigned int v) {
	if (a & 1) { fprintf(stderr, "odd word write %x\n", a); exit(3); }
	m68k_write_memory_8(a, v >> 8); m68k_write_memory_8(a + 1, v);
}
void m68k_write_memory_32(unsigned int a, unsigned int v) { m68k_write_memory_16(a, v >> 16); m68k_write_memory_16(a + 2, v); }
unsigned int m68k_read_disassembler_16(unsigned int a) { return m68k_read_memory_16(a); }
unsigned int m68k_read_disassembler_32(unsigned int a) { return m68k_read_memory_32(a); }
static unsigned R[16];
static unsigned ring[64], ring2[64]; static int rp;
void hook(unsigned int pc) {
	ring[rp++&63]=pc; ring2[(rp-1)&63]=m68k_get_reg(0,M68K_REG_A7);
	if (pc == stoppc && !hit) { hit = 1; for (int r=0;r<16;r++) R[r]=m68k_get_reg(0,r); m68k_end_timeslice(); }
	if (pc < 0x400) { fprintf(stderr, "jump to low memory %x\n", pc); exit(3); }
}
int illg(int op) { fprintf(stderr, "illegal op %04x at %x\n", op, m68k_get_reg(0, M68K_REG_PPC)); exit(4); }

int main(int argc, char **argv) {
	M = calloc(MEMSZ, 1);
	FILE *f = fopen(argv[1], "rb"); size_t r = fread(M, 1, MEMSZ, f); fclose(f); (void)r;
	m68k_pulse_reset();
	m68k_set_reg(M68K_REG_SR, 0x0000);
	m68k_set_reg(M68K_REG_PC, strtoul(argv[2], 0, 0));
	m68k_set_reg(M68K_REG_A7, strtoul(argv[3], 0, 0));
	m68k_set_reg(M68K_REG_D0, strtoul(argv[4], 0, 0));
	m68k_set_reg(M68K_REG_A0, strtoul(argv[5], 0, 0));
	stoppc = strtoul(argv[6], 0, 0);
	for (int i = 0; i < 4000 && !hit; i++) total += m68k_execute(1000000);
	if (getenv("TRACE")) for (int i=0;i<64;i++) fprintf(stderr,"%x:%x ",ring[(rp+i)&63],ring2[(rp+i)&63]);
	if (!hit) { fprintf(stderr, "did not reach the game\n"); return 5; }
	f = fopen(argv[7], "wb"); fwrite(M, 1, MEMSZ, f); fclose(f);
	printf("ppc %x cycles %lld d0 %x a0 %x a7 %x d2 %x a6 %x\n", stoppc, total, R[0], R[8], R[15], R[2], R[14]);
	return 0;
}
