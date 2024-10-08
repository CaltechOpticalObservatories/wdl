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

	@cat $(MODFILE) | $(GPP) $(GFLAGS) $(INCL) | $(MODPARSER) -
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
