# SPDX-License-Identifier: GPL-3.0-only
"""MWScript compiled by the builder (docs/MWSCRIPT_BYTECODE.md).

The game's scripts (SCPT records) are parsed once at build time and written as compact bytecode for the engine's
small interpreter (engine/aga/src/aw_mwvm.c). The language rules (argument kinds per function, the scanner's
tolerances) were learned from reading OpenMW's script compiler (GPL-3.0, components/compiler); this is our own
implementation, no code copied.

  lexer     tokens, with the original editor's tolerances
  functions every function and instruction of the language: return type, arguments, group, engine support
  parser    statements and expressions (an AST of tuples)
  codegen   typed stack bytecode (opcodes.py; the shared table with the NPC greeting conditions)
  awms      the AWMS1 file: writer, reader, disassembler
  media     script sound, voice and music names to the media catalogue's converted files
"""
