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
# No sin/cos builtins: GCC otherwise merges a sin(a)+cos(a) pair into
# cexp(i*a), whose C library code executes 68040-unimplemented FPU
# instructions (ENGINE-FPU-UNIMPL-31). The engine uses Q_SinCosDeg instead.
MATH_FLAGS = -fno-builtin-sin -fno-builtin-cos -fno-builtin-sinf -fno-builtin-cosf
# NOTE: Using -O1 globally due to GCC optimizer bugs (culling, FP math)
# NOTE: cvar.c contains workaround for AmigaOS sprintf lacking %f support
# Warnings (ENGINE-STRICT-WARNINGS-36, docs/DEVELOPMENT.md): every file builds with -Wall -Wextra and
# -Wformat-security, less three checks that are noise in the inherited Quake code: unused code,
# partly initialised structs (the cvar_t definitions) and signed/unsigned comparisons. AmiWind's own
# files (aw_*.c and chim/*.c, OWN_FILES below) get those back (unused parameters excepted), plus
# shadowed names and missing prototypes. The builder fails on any warning (tools/build_aga.py), so a
# new warning in either set stops the build. Warning flags do not change the generated code.
WARN_FLAGS = -Wall -Wextra -Wformat-security -Wno-unused -Wno-missing-field-initializers -Wno-sign-compare
OWN_WARN_FLAGS = -Wunused -Wno-unused-parameter -Wsign-compare -Wshadow -Wmissing-prototypes
# EXTRA_DEFINES: experimental engine switches, off by default (docs/EXPERIMENTAL_FLAGS.md), e.g.
# make EXTRA_DEFINES=-DAW_EXP_WIDECOORD (24-bit coordinates, aw_coord.h)
EXTRA_DEFINES ?=
DEFINES = -DAMIGA -DFALSE=0 -DTRUE=1 -DUSE_ASM_SPANS=0 -DUSE_FAST_RECIPROCAL=1 $(EXTRA_DEFINES)
# USE_ASM_SPANS stays 0: the C span code is always compiled; the engine profile (ENGINE_ASM below)
# links upstream's span assembly beside it.
# USE_FAST_RECIPROCAL=1: Use fast 1/x approximation in Turbulent8 (saves ~15 cycles per division)
# Note: Defining FALSE/TRUE as this GCC SDK doesn't provide them
# Note: id68k is for SAS/C compiler, we use GCC so keep it undefined
INCLUDES = -I. -Isrc -ICDPlayerSDK -Ibuild/version

PYTHON ?= python3
VERSION_FILE ?= $(if $(wildcard VERSION),VERSION,../../VERSION)
VERSION_GENERATOR ?= $(if $(wildcard tools/project_version.py),tools/project_version.py,../../tools/project_version.py)
# CHIM's own version, beside VERSION (tools/project_version.py)
CHIM_VERSION_FILE ?= $(wildcard $(dir $(VERSION_FILE))CHIM_VERSION)

# Engine profile (docs/ENGINE_PROFILES.md; tools/build_aga.py engine --engine-profile c|upstream,
# --engine-asm, --engine-opt). ENGINE_ASM names the upstream AmiQuake 68k assembly units linked
# instead of the C paths (TerribleFire's AmiQuake GCC port, Stephen Leary, including NovaCoder's
# original routines; revision 9c62d90):
#   spans  d_scan_68k.s D_DrawSpans8 (the 68020 build: d_scan_68k_nofpu.s)
#   turb   d_scan_68k.s D_DrawTurbulent8Span, the water/lava span loop (same files)
#   maths  mathlib_68k.s AngleVectors (68040 build only)
#   c2p    c2p8.s chunky-to-planar
#   fixed  fixedpoint_asm.s (68020 build only: the no-FPU spans call it)
# ENGINE_OPT: o1 = -O1 everywhere (as upstream's Makefile builds too); o2 = the selective -O2 experiment
# upstream's README describes (everything at -O2 except mathlib.c and in_amiga.c at -O1; d_sprite.c
# stays -O0 either way).
# Empty ENGINE_ASM with ENGINE_OPT=o1 is the c profile: exactly the C build's commands and binary.
ENGINE_ASM ?=
ENGINE_OPT ?= o1
ENGINE_ASM_UNITS = spans turb maths c2p fixed
ifneq ($(filter-out $(ENGINE_ASM_UNITS),$(ENGINE_ASM)),)
$(error ENGINE_ASM: unknown unit(s) $(filter-out $(ENGINE_ASM_UNITS),$(ENGINE_ASM)); known: $(ENGINE_ASM_UNITS))
endif
ifneq ($(filter-out o1 o2,$(ENGINE_OPT)),)
$(error ENGINE_OPT must be o1 or o2, not $(ENGINE_OPT))
endif
# ENGINE_CPU: the CPU the engine code is compiled for (docs/68060.md). 68040 (default) is the baseline:
# -m68040 -m68881, the command line unchanged. 68060 is the experimental 68060-targeted build: GCC's
# 68060 instruction selection with the hardware FPU (no FScc, no 64-bit MULS.L/DIVS.L, FINTRZ in
# hardware); -m68060 alone means soft float in this SDK, and its 68060 libraries are soft-float, so it
# links the 68040 build's hard-float libraries. The result runs on a 68060 only (FINTRZ traps on a 68040).
ENGINE_CPU ?= 68040
ifneq ($(filter-out 68040 68060,$(ENGINE_CPU)),)
$(error ENGINE_CPU must be 68040 or 68060, not $(ENGINE_CPU))
endif
FPU_ARCH_FLAGS = $(if $(filter 68060,$(ENGINE_CPU)),-m68060 -mhard-float,-m68040 -m68881)
ENGINE_DEFINES =
ENGINE_ASM_SRCS =
ifneq ($(filter spans turb,$(ENGINE_ASM)),)
ENGINE_DEFINES += -DAW_ASM_DSCAN=1
ENGINE_ASM_SRCS += $(if $(filter obj-nofpu,$(OBJDIR)),d_scan_68k_nofpu.s,d_scan_68k.s)
endif
ENGINE_DEFINES += $(if $(filter spans,$(ENGINE_ASM)),-DAW_ASM_SPANS=1) $(if $(filter turb,$(ENGINE_ASM)),-DAW_ASM_TURB=1)
ifneq ($(filter maths,$(ENGINE_ASM)),)
ENGINE_DEFINES += -DAW_ASM_MATHS=1
ENGINE_ASM_SRCS += mathlib_68k.s
endif
ifneq ($(filter c2p,$(ENGINE_ASM)),)
ENGINE_DEFINES += -DAW_ASM_C2P=1
ENGINE_ASM_SRCS += c2p8.s
endif
ifneq ($(filter fixed,$(ENGINE_ASM)),)
ENGINE_ASM_SRCS += $(if $(filter obj-nofpu,$(OBJDIR)),fixedpoint_asm.s)
endif
ifeq ($(ENGINE_OPT),o2)
OPT_FLAGS = -O2 -fno-strict-aliasing
endif

CFLAGS = $(ARCH_FLAGS) $(OPT_FLAGS) $(MATH_FLAGS) $(WARN_FLAGS) $(DEFINES) $(ENGINE_DEFINES) $(INCLUDES)

# Linker flags
LDFLAGS = $(ARCH_FLAGS) -s
LIBS = -lm -lamiga
# The printf family is Q_vsnprintf (aw_format.c): the C library's float
# formatting executes 68040-unimplemented FPU instructions
# (ENGINE-FPSP-MISSING-31), so its printf code is not linked at all.
FORMAT_WRAPS = -Wl,--wrap=sprintf -Wl,--wrap=snprintf -Wl,--wrap=vsprintf -Wl,--wrap=vsnprintf \
	-Wl,--wrap=fprintf -Wl,--wrap=vfprintf -Wl,--wrap=printf -Wl,--wrap=vprintf

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
	aw_debug.c aw_cam_rules.c aw_cam.c aw_clock.c aw_wait.c \
	aw_ui.c aw_icons.c aw_excluded.c aw_movie.c aw_speech.c aw_intro.c aw_story.c aw_state.c aw_harvest.c aw_harvest_runtime.c aw_harvest_proxy.c aw_opening.c aw_barrier.c aw_character.c aw_head.c aw_reader.c aw_worldui.c aw_statswin.c aw_inventory.c aw_debug_torch.c aw_save_codec.c aw_save.c aw_savemenu.c aw_nav.c aw_npcpath.c aw_companion.c aw_combat_rules.c aw_combat.c aw_items.c aw_arena.c aw_actors.c aw_view_rules.c aw_view.c aw_console.c aw_console_glyphs.c aw_door_audio.c aw_hinged_door.c aw_mwvm.c aw_mwhost.c aw_msgbox_rules.c aw_msgbox.c aw_scene.c aw_hand_sprites.c aw_anim.c aw_animkit_rules.c aw_animkit.c aw_skel.c aw_skel_load.c aw_skel_release.c aw_fastrelease.c aw_tryalloc.c aw_glut.c aw_lava_rules.c aw_lava.c \
	aw_spawn.c aw_scenery.c aw_region.c aw_section.c aw_mappath.c aw_gallery.c aw_stream.c aw_spike.c aw_heapsize.c \
	aw_walk.c aw_move_rules.c aw_move.c aw_world.c aw_bounds_rules.c aw_bounds.c aw_torch.c aw_guard_torch.c aw_lamps.c aw_remote.c aw_fog_location.c aw_weather_rules.c aw_weather.c aw_hand_models.c aw_npc_lod.c \
	aw_music.c aw_aread.c aw_log.c \
	aw_profile.c aw_render_ranges.c aw_fpu_status.c aw_photo.c aw_miniwind.c aw_quickchar.c aw_testbox.c \
	aw_platform.c \
	aw_fog.c aw_horizon.c \
	chase.c \
	cl_demo.c \
	cl_input.c \
	cl_main.c \
	cl_parse.c \
	cl_tent.c \
	cmd.c \
	common.c aw_format.c aw_rcount.c \
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
	aw_hud.c aw_inspect.c \
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

# CHIM world streamer: part of this one engine tree (src/chim/), active only
# for maps that name a CHIM frame when the CHIM data exists.
CHIM_SRCS = \
	chim/chim_format.c \
	chim/chim_zone.c \
	chim/chim_models.c \
	chim/chim_chunks.c \
	chim/chim_world.c \
	chim/chim_graft.c \
	chim/chim_statics.c \
	chim/chim_far.c \
	chim/chim_cuts.c \
	chim/chim_prefetch.c \
	chim/chim_placed_clip.c \
	chim/chim_actor_table.c \
	chim/chim_terc.c \
	chim/chim_thgt.c \
	chim/chim_room.c

SRCS += $(CHIM_SRCS)

# AmiWind's own files: the stricter warning set (WARN_FLAGS above).
OWN_FILES = $(filter aw_%.c chim/%.c,$(SRCS))
$(OWN_FILES:%.c=$(OBJDIR)/%.o): WARN_FLAGS += $(OWN_WARN_FLAGS)

# The c profile links no assembly: GPL C spans and the independent C2P (aw_c2p.c). The upstream
# profile adds the ENGINE_ASM units above.
OBJS = $(SRCS:%.c=$(OBJDIR)/%.o)
ALLOBJS = $(OBJS) $(ENGINE_ASM_SRCS:%.s=$(OBJDIR)/%.o)

# Default target: verified CPU class; nofpu is an explicit experiment
.PHONY: all fpu nofpu
all: fpu

# The game heap in MiB (the builder's --heap-mb); empty = the engine source's AMIWIND_HEAP_MB.
HEAP_MB ?=
build/version/amiwind_version.h: $(VERSION_FILE) $(CHIM_VERSION_FILE) $(VERSION_GENERATOR)
	$(PYTHON) "$(VERSION_GENERATOR)" --version-file "$(VERSION_FILE)" --out build/version $(if $(HEAP_MB),--heap-mb $(HEAP_MB))

# amiwind_heap.h follows HEAP_MB on every make: the generator rewrites it only when
# the size changed, so a new size rebuilds what includes it and nothing else.
build/version/amiwind_heap.h: build/version/amiwind_version.h heap-size-check
	$(PYTHON) "$(VERSION_GENERATOR)" --version-file "$(VERSION_FILE)" --out build/version $(if $(HEAP_MB),--heap-mb $(HEAP_MB))
heap-size-check:
$(OBJDIR)/sys_amiga.o: build/version/amiwind_heap.h

# chim_version.h (CHIM's own version) comes from the same command
build/version/chim_version.h: build/version/amiwind_version.h

$(ALLOBJS): build/version/amiwind_version.h | $(OBJDIR)

# FPU target (68040 with FPU)
# Uses Quake III fast InvSqrt for math (2.3x faster than hardware sqrt on real 68040)
fpu: ARCH_FLAGS = $(FPU_ARCH_FLAGS)
fpu: DEFINES = -DAMIGA -DFALSE=0 -DTRUE=1 -DUSE_ASM_SPANS=0 -DUSE_FAST_RECIPROCAL=1 $(EXTRA_DEFINES)
fpu: TARGET = build/AmiQuakeGCC
fpu: OBJDIR = obj
fpu: LDFLAGS = -m68040 -m68881 -s -Wl,-Map,build/AmiQuakeGCC.map
fpu: $(TARGET)

# NOFPU target (soft-float for 68020+ without FPU)
nofpu:
	@$(MAKE) build/AmiQuakeGCC-NoFPU ARCH_FLAGS="-m68020 -msoft-float" TARGET="build/AmiQuakeGCC-NoFPU" OBJDIR="obj-nofpu" LDFLAGS="-m68020 -msoft-float -s"

# Create directories
$(OBJDIR):
	@mkdir -p $(OBJDIR) $(OBJDIR)/chim

# Link
$(TARGET): $(OBJDIR) $(ALLOBJS)
	@mkdir -p build
	$(CC) $(LDFLAGS) $(FORMAT_WRAPS) -o $(TARGET) $(ALLOBJS) $(LIBS)

	@echo "Build complete: $(TARGET)"

# Compile C files
$(OBJDIR)/model.o: $(SRCDIR)/model_alias_stream.inc

$(OBJDIR)/%.o: $(SRCDIR)/%.c
	$(CC) $(CFLAGS) -c -o $@ $<

# Upstream's assembly units, assembled exactly as upstream does (68040 for the C2P patch offsets).
ENGINE_AS_FLAGS = -Fhunk -m68040 -phxass -quiet
$(OBJDIR)/%.o: $(SRCDIR)/%.s
	$(AS) $(ENGINE_AS_FLAGS) -I$(NDK_INC) -I$(NDK_INC)/lvo -o $@ $<

# ENGINE_OPT=o2: upstream's two -O1 files (GCC's -O2 floating-point optimiser broke angles and mouse input)
ifeq ($(ENGINE_OPT),o2)
$(OBJDIR)/mathlib.o $(OBJDIR)/in_amiga.o: OPT_FLAGS = -O1 -fno-strict-aliasing
endif

# Special rule for net_amigaudp.c (needs additional include path)
$(OBJDIR)/net_amigaudp.o: $(SRCDIR)/net_amigaudp.c
	$(CC) $(CFLAGS) -c -o $@ $<

# mathlib.c uses default -O1 flags (no special rule needed)

# Special rule for d_sprite.c (disable optimization to prevent FPU precision issues)
$(OBJDIR)/d_sprite.o: $(SRCDIR)/d_sprite.c
	$(CC) $(ARCH_FLAGS) -O0 $(MATH_FLAGS) $(WARN_FLAGS) $(DEFINES) $(ENGINE_DEFINES) $(INCLUDES) -c -o $@ $<

# Hardware benchmark for owners (docs/HARDWARE-BENCHMARK.md): asset-free,
# 68020+ (the FPU loop runs only when an FPU is present).
.PHONY: bench
bench: build/awbench
build/awbench: bench/awbench.c
	@mkdir -p build
	$(CC) -m68020 -m68881 -O1 -Wall -s -o $@ $< -lamiga

# Trap counter for the 68060 work (docs/68060.md "Counting trapped instructions"): asset-free,
# a measurement tool only (never on a game disk).
.PHONY: traps
traps: build/awtraps
build/awtraps: bench/awtraps.asm
	@mkdir -p build
	$(AS) -m68040 -Fhunkexe -kick1hunks -nosym -quiet -I$(NDK_INC) -o $@ $<

# Clean
clean:
	rm -rf obj obj-nofpu
	rm -f build/AmiQuakeGCC build/AmiQuakeGCC-NoFPU build/awbench build/awtraps
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
