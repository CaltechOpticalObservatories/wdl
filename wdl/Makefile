# -----------------------------------------------------------------------------
# @file     Makefile
# @brief    Makefile for Software/Config/Archon/Build/
# @author   David Hale
# @date     2015-xx-xx
# @modified 2016-01-14
# @modified 2016-01-27 added fixrawendline (special case for Peter)
# @modified 2016-01-28 removed clean. Use @F.h instead of HFILE=archon.h
# @modified 2016-03-31 change how .mod is parsed
# @modified 2016-04-04 add INCPARSER and checks for file existence
# @modified 2016-04-07 add plotting option and check for WAVGEN exit code
# @modified 2016-04-19 changes to implement INCLUDE_FILE= in *.conf
# @modified 2016-04-20 read CDS_FILE and MODULE_FILE from .conf
# @modified 2017-02-08 added modegen
# @modified 2017-11-09 remove copying of acf files to camera computers
# @modified 2020-12-21 added insert_hash
#
# This Makefile uses the general preprocessor GPP 2.24 for macro processing.
# It also requires the ini2acf.pl Perl script for creating an Archon acf file.
#
# -----------------------------------------------------------------------------
#

# Copyright (C) <2018> California Institute of Technology
# Software written by: <Dave Hale and Peter Mao>
# 
#     This program is part of the Waveform Definition Language (WDL) developed
#     for ZTF.  This program is free software: you can redistribute it and/or
#     modify it under the terms of the GNU General Public License as published
#     by the Free Software Foundation, either version 3 of the License, or
#     any later version.
# 
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
# 
#     Please see the GNU General Public License at:
#     <http://www.gnu.org/licenses/>.
# 
#     Report any bugs or suggested improvements to:
# 
#     David Hale <dhale@caltech.edu> or
#     Stephen Kaye <skaye@caltech.edu>

# -----------------------------------------------------------------------------
# @file     Makefile
# @brief    Makefile for Software/wdl/demo
# @author   David Hale
# @date     2015-xx-xx
# @modified 2024-08-02 made generic for demo
#
# This Makefile uses the general preprocessor GPP 2.24 for macro processing.
# It also requires the ini2acf.pl Perl script for creating an Archon acf file.
#
# -----------------------------------------------------------------------------
#

# set to path to gpp
GPP       = /usr/bin/gpp
# set to path to wdl code
WDLPATH   = ..
# output for *.acf file
ACFPATH   = ./

PLOT      = False # True   # show waveform plots by default, True | False
GFLAGS    = +c "/*" "*/" +c "//" "\n" +c "\\\n" ""
SEQPARSER = $(WDLPATH)/wdl/seqParserDriver.py
INCPARSER = $(WDLPATH)/wdl/incParserDriver.py
WDLPARSER = $(WDLPATH)/wdl/wdlParserDriver.py
MODPARSER = $(WDLPATH)/wdl/modParserDriver.py
WAVGEN    = $(WDLPATH)/wdl/wavgenDriver.py
MODEGEN   = $(WDLPATH)/wdl/modegenDriver.py
I2A       = $(WDLPATH)/wdl/ini2acf.pl
INCL      = -I$(CURDIR)

# Global variable to store the filename
FILE_NAME :=

SCAN_CDSFILE = cat $(FILE_NAME).conf | $(GPP) $(GFLAGS) $(INCL) | \
		awk -F= '{gsub(" |\t","",$$1)} $$1=="CDS_FILE"{print $$2}' | cut -d'"' -f2
SCAN_MODFILE = cat $(FILE_NAME).conf | $(GPP) $(GFLAGS) $(INCL) | \
		awk -F= '{gsub(" |\t","",$$1)} $$1=="MODULE_FILE"{print $$2}' | cut -d'"' -f2
SCAN_MODEFILE = cat $(FILE_NAME).conf | $(GPP) $(GFLAGS) $(INCL) | \
		awk -F= '{gsub(" |\t","",$$1)} $$1=="MODE_FILE"{print $$2}' | cut -d'"' -f2

F_TMP = $(FILE_NAME)_TMP

DEBUG ?= 0

ifeq ($(DEBUG), 1)
    debug_message = @echo "Debug: $(1)"
else
    debug_message = @true
endif

# Main rule for building the target
%:
	$(eval FILE_NAME := $(@F)) 
	$(call debug_message, "Current filename: $(FILE_NAME)")
	@$(MAKE) generate_wdl FILE_NAME=$(@F)
	@$(MAKE) generate_script_states FILE_NAME=$(@F)
	@$(MAKE) assemble_acf FILE_NAME=$(@F)

# Rule for generating WDL
generate_wdl: 
	$(eval MODFILE := $(shell $(SCAN_MODFILE)))
	@echo "Looking for MODULE_FILE = $(MODFILE) ..."
	@test -f $(FILE_NAME).conf || { echo "$(FILE_NAME).conf does not exist"; exit 1; }
	$(call debug_message, "Found configuration file: $(FILE_NAME).conf")

	@echo "Making $(F_TMP).wdl from $(FILE_NAME).conf ..."
	@cat $(FILE_NAME).conf | $(SEQPARSER) - | $(GPP) $(GFLAGS) $(INCL) | $(WDLPARSER) - > $(F_TMP).wdl
	$(call debug_message, "Created WDL file: $(F_TMP).wdl")

	@echo "Making $(F_TMP).script and $(F_TMP).states from $(F_TMP).wdl ..."
	@test -f $(MODFILE) || { echo "$(MODFILE) does not exist"; exit 1; }
	$(call debug_message, "Found MODULE_FILE: $(MODFILE)")

	@cat $(MODFILE) | $(GPP) $(GFLAGS) $(INCL) | $(MODPARSER)
	@test -f .modules && mv .modules $(F_TMP).modules || echo "No .modules file created"
	@test -f .system && mv .system $(F_TMP).system || echo "No .system file created"
	$(call debug_message, "Processed MODULE_FILE: $(MODFILE)")

	@$(WAVGEN) $(F_TMP) $(PLOT) || { echo "Waveform generation failed"; exit 1; }
	$(call debug_message, "Finished waveform generation for $(F_TMP) with plot: $(PLOT)")

# Rule for generating script states
generate_script_states:
	@echo "Assembling $(FILE_NAME).acf ..."
	$(eval CDSFILE := $(shell $(SCAN_CDSFILE)))
	$(call debug_message, "Looking for CDS_FILE = $(CDSFILE) ...")
	@test -f $(CDSFILE) || { echo "$(CDSFILE) does not exist"; exit 1; }
	$(call debug_message, "Preparing to assemble $(FILE_NAME).acf file using:")
	$(call debug_message, "INCPARSER: $(INCPARSER)")
	$(call debug_message, "CDSFILE: $(CDSFILE)")
	$(call debug_message, "GPP Flags: $(GFLAGS)")
	@echo "Assembling $(FILE_NAME).acf file ..."
	@cat $(FILE_NAME).conf | $(INCPARSER) - | cat - $(CDSFILE) | $(GPP) $(GFLAGS) $(INCL) | \
		cat - $(F_TMP).script $(F_TMP).modules $(F_TMP).states $(F_TMP).system | \
		$(I2A) - > $(FILE_NAME).acf

# Rule for assembling the ACF
assemble_acf:
	$(eval MODEFILE := $(shell $(SCAN_MODEFILE)))
	@$(MODEGEN) $(MODEFILE) $(FILE_NAME).acf
	@if [ -d ".git" ]; then \
		echo "Inserting REV keyword ..."; $(WDLPATH)/insert_hash $(FILE_NAME).acf; \
	else \
		echo "Not a git archive, skipping REV keyword"; \
	fi
	@echo "Done"
