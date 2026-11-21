/* m68k.h - the interface of tools/m68k.c, a small 68000 core for the test
 * harness (the same calls as the Musashi core, so amiga.c works with both) */
#ifndef M68K_H
#define M68K_H
#define M68K_CPU_TYPE_68000 1
enum {
	M68K_REG_D0, M68K_REG_D1, M68K_REG_D2, M68K_REG_D3, M68K_REG_D4, M68K_REG_D5, M68K_REG_D6, M68K_REG_D7,
	M68K_REG_A0, M68K_REG_A1, M68K_REG_A2, M68K_REG_A3, M68K_REG_A4, M68K_REG_A5, M68K_REG_A6, M68K_REG_A7,
	M68K_REG_PC, M68K_REG_SR, M68K_REG_SP, M68K_REG_USP, M68K_REG_ISP, M68K_REG_PPC
};
void m68k_init(void);
void m68k_set_cpu_type(int t);
void m68k_pulse_reset(void);
int m68k_execute(int cycles);
int m68k_cycles_run(void);
void m68k_end_timeslice(void);
unsigned int m68k_get_reg(void *ctx, int reg);
void m68k_set_reg(int reg, unsigned int v);
/* supplied by the harness */
unsigned int m68k_read_memory_8(unsigned int a);
unsigned int m68k_read_memory_16(unsigned int a);
unsigned int m68k_read_memory_32(unsigned int a);
void m68k_write_memory_8(unsigned int a, unsigned int v);
void m68k_write_memory_16(unsigned int a, unsigned int v);
void m68k_write_memory_32(unsigned int a, unsigned int v);
unsigned int m68k_read_disassembler_16(unsigned int a);
unsigned int m68k_read_disassembler_32(unsigned int a);
void hook(unsigned int pc);
int illg(int op);
#endif
