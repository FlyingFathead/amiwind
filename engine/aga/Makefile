# Makefile for AmiQuake - GCC m68k-amigaos build
# Based on awinquake 0.9 source
# AmiWind checkpoint: 68040/FPU reference build; experimental 68020 build

# Toolchain
CC = m68k-amigaos-gcc
AS = vasmm68k_mot
AR = m68k-amigaos-ar
RANLIB = m68k-amigaos-ranlib

# NDK includes (can be overridden)
NDK_INC ?= /opt/amiga/m68k-amigaos/ndk-include

# Compiler flags
ARCH_FLAGS = -m68040 -m68881
OPT_FLAGS = -O1 -fno-strict-aliasing
# NOTE: Using -O1 globally due to GCC optimizer bugs (culling, FP math)
# NOTE: cvar.c contains workaround for AmigaOS sprintf lacking %f support
WARN_FLAGS = -Wall -Wno-unused
DEFINES = -DAMIGA -DFALSE=0 -DTRUE=1 -DUSE_ASM_SPANS=0 -DUSE_FAST_RECIPROCAL=1
# USE_ASM_SPANS=1: Use optimized 68k assembly for span drawing (d_scan_68k.s)
# USE_FAST_RECIPROCAL=1: Use fast 1/x approximation in Turbulent8 (saves ~15 cycles per division)
# Note: Defining FALSE/TRUE as this GCC SDK doesn't provide them
# Note: id68k is for SAS/C compiler, we use GCC so keep it undefined
INCLUDES = -I. -Isrc -ICDPlayerSDK -Ibuild/version

PYTHON ?= python3
VERSION_FILE ?= $(if $(wildcard VERSION),VERSION,../../VERSION)
VERSION_GENERATOR ?= $(if $(wildcard tools/project_version.py),tools/project_version.py,../../tools/project_version.py)

CFLAGS = $(ARCH_FLAGS) $(OPT_FLAGS) $(WARN_FLAGS) $(DEFINES) $(INCLUDES)

# Linker flags
LDFLAGS = $(ARCH_FLAGS) -s
LIBS = -lm -lamiga

# Source directory
SRCDIR = src

# Output
TARGET = build/AmiQuakeGCC
OBJDIR = obj

# Source files (from OBJSGCC in smakefile)
# Note: amiga_stubs.c provides stub implementations for assembly functions (timer, unlink)
# Display conversion is implemented independently in aw_c2p.c.
SRCS = \
	amiga_stubs.c \
	aw_debug.c aw_clock.c aw_wait.c \
	aw_ui.c aw_movie.c aw_speech.c aw_intro.c aw_story.c aw_state.c aw_opening.c aw_barrier.c aw_character.c aw_head.c aw_reader.c aw_save_codec.c aw_save.c aw_savemenu.c aw_nav.c aw_console.c aw_console_glyphs.c aw_scene.c aw_hand_sprites.c \
	aw_spawn.c \
	aw_walk.c \
	aw_music.c \
	aw_profile.c \
	aw_platform.c \
	aw_fog.c \
	chase.c \
	cl_demo.c \
	cl_input.c \
	cl_main.c \
	cl_parse.c \
	cl_tent.c \
	cmd.c \
	common.c \
	console.c \
	crc.c \
	cvar.c \
	d_edge.c \
	d_fill.c \
	d_init.c \
	d_modech.c \
	d_part.c \
	d_polyse.c \
	d_scan.c \
	d_sky.c \
	d_sprite.c \
	d_surf.c \
	d_vars.c \
	d_zpoint.c \
	draw.c \
	host.c \
	host_cmd.c \
	in_amiga.c \
	keys.c \
	mathlib.c \
	aw_menu.c \
	model.c \
	net_dgrm.c \
	net_loop.c \
	net_main.c \
	net_bsd.c \
	net_amigaudp.c \
	net_vcr.c \
	nonintel.c \
	pr_cmds.c \
	pr_edict.c \
	pr_exec.c \
	r_aclip.c \
	r_alias.c \
	r_bsp.c \
	r_draw.c \
	r_edge.c \
	r_efrag.c \
	r_light.c \
	r_main.c \
	r_misc.c \
	r_part.c \
	r_sky.c \
	r_sprite.c \
	r_surf.c \
	r_vars.c \
	aw_hud.c \
	aw_c2p.c \
	screen.c \
	snd_dma.c \
	snd_mem.c \
	snd_mix.c \
	snd_amiga.c \
	sv_main.c \
	sv_move.c \
	sv_phys.c \
	sv_user.c \
	sys_amiga.c \
	sys_file_amiga.c \
	vid_amiga.c \
	view.c \
	wad.c \
	world.c \
	zone.c

# Release builds use GPL C spans and independent C2P; no extracted assembly.
OBJS = $(SRCS:%.c=$(OBJDIR)/%.o)
ALLOBJS = $(OBJS)

# Default target: verified CPU class; nofpu is an explicit experiment
.PHONY: all fpu nofpu
all: fpu

build/version/amiwind_version.h: $(VERSION_FILE) $(VERSION_GENERATOR)
	$(PYTHON) "$(VERSION_GENERATOR)" --version-file "$(VERSION_FILE)" --out build/version

$(ALLOBJS): build/version/amiwind_version.h | $(OBJDIR)

# FPU target (68040 with FPU)
# Uses Quake III fast InvSqrt for math (2.3x faster than hardware sqrt on real 68040)
fpu: ARCH_FLAGS = -m68040 -m68881
fpu: DEFINES = -DAMIGA -DFALSE=0 -DTRUE=1 -DUSE_ASM_SPANS=0 -DUSE_FAST_RECIPROCAL=1
fpu: TARGET = build/AmiQuakeGCC
fpu: OBJDIR = obj
fpu: LDFLAGS = -m68040 -m68881 -s
fpu: $(TARGET)

# NOFPU target (soft-float for 68020+ without FPU)
nofpu:
	@$(MAKE) build/AmiQuakeGCC-NoFPU ARCH_FLAGS="-m68020 -msoft-float" TARGET="build/AmiQuakeGCC-NoFPU" OBJDIR="obj-nofpu" LDFLAGS="-m68020 -msoft-float -s"

# Create directories
$(OBJDIR):
	@mkdir -p $(OBJDIR)

# Link
$(TARGET): $(OBJDIR) $(ALLOBJS)
	@mkdir -p build
	$(CC) $(LDFLAGS) -o $(TARGET) $(ALLOBJS) $(LIBS)

	@echo "Build complete: $(TARGET)"

# Compile C files
$(OBJDIR)/%.o: $(SRCDIR)/%.c
	$(CC) $(CFLAGS) -c -o $@ $<

# Special rule for net_amigaudp.c (needs additional include path)
$(OBJDIR)/net_amigaudp.o: $(SRCDIR)/net_amigaudp.c
	$(CC) $(CFLAGS) -c -o $@ $<

# mathlib.c uses default -O1 flags (no special rule needed)

# Special rule for d_sprite.c (disable optimization to prevent FPU precision issues)
$(OBJDIR)/d_sprite.o: $(SRCDIR)/d_sprite.c
	$(CC) $(ARCH_FLAGS) -O0 $(WARN_FLAGS) $(DEFINES) $(INCLUDES) -c -o $@ $<

# Clean
clean:
	rm -rf obj obj-nofpu
	rm -f build/AmiQuakeGCC build/AmiQuakeGCC-NoFPU
	rm -f build/test_*
	rm -f tests/*.o

# Rebuild
rebuild: clean all

# Show configuration
config:
	@echo "Compiler: $(CC)"
	@$(CC) --version
	@echo ""
	@echo "Flags: $(CFLAGS)"
	@echo "Source files: $(words $(SRCS))"
	@echo "Object files: $(words $(OBJS))"
