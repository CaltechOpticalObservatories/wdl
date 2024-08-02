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
GPP       = /usr/local/bin/gpp
# set to path to wdl code
WDLPATH   = ..
# output for *.acf file
ACFPATH   = ./

PLOT      = False # True   # show waveform plots by default, True | False
GFLAGS    = +c "/*" "*/" +c "//" "\n" +c "\\\n" ""
SEQPARSER = $(WDLPATH)/seqParserDriver.py
INCPARSER = $(WDLPATH)/incParserDriver.py
WDLPARSER = $(WDLPATH)/wdlParserDriver.py
MODPARSER = $(WDLPATH)/modParserDriver.py
WAVGEN    = $(WDLPATH)/wavgenDriver.py
MODEGEN   = $(WDLPATH)/modegenDriver.py
I2A       = $(WDLPATH)/ini2acf.pl
INCL      = -I$(CURDIR)

SCAN_CDSFILE	= cat $(@F).conf | $(GPP) $(GFLAGS) $(INCL) | \
		awk -F= '{gsub(" |\t","",$$1)} $$1=="CDS_FILE"{print $$2}' | cut -d'"' -f2
SCAN_MODFILE	= cat $(@F).conf | $(GPP) $(GFLAGS) $(INCL) | \
		awk -F= '{gsub(" |\t","",$$1)} $$1=="MODULE_FILE"{print $$2}' | cut -d'"' -f2
SCAN_MODEFILE	= cat $(@F).conf | $(GPP) $(GFLAGS) $(INCL) | \
		awk -F= '{gsub(" |\t","",$$1)} $$1=="MODE_FILE"{print $$2}' | cut -d'"' -f2

F_TMP = $(@F)_TMP

%:	;
	$(eval MODFILE := $(shell $(SCAN_MODFILE)))
	@echo looking for MODULE_FILE = $(MODFILE) ...
	@test -f $(@F).conf || echo $(@F).conf does not exist
	@echo making $(F_TMP).wdl from $(@F).conf ...
	@test -f $(@F).conf && cat $(@F).conf | $(SEQPARSER) - | $(GPP) $(GFLAGS) $(INCL) |  $(WDLPARSER) - > $(F_TMP).wdl
	@echo making $(F_TMP).script, $(F_TMP).states from $(F_TMP).wdl ...
	@test -f $(MODFILE) || echo $(MODFILE) does not exist
	@test -f $(MODFILE) && echo $(F_TMP) | cat  - $(MODFILE) | $(GPP) $(GFLAGS) $(INCL) |  $(MODPARSER) -
	@$(WAVGEN) $(F_TMP) $(PLOT)
	@if [ $$? -eq 1 ]; then exit 1; fi
	@echo assembling $(@F).acf ...
	$(eval CDSFILE := $(shell $(SCAN_CDSFILE)))
	@echo looking for CDS_FILE = $(CDSFILE) ...
	@test -f $(CDSFILE) || echo $(CDSFILE) does not exist
	@echo assembling $(@F).acf file ...
	@test -f $(CDSFILE) && cat $(@F).conf | $(INCPARSER) - | cat - $(CDSFILE) | $(GPP) $(GFLAGS) $(INCL) | \
		cat - $(F_TMP).script $(F_TMP).modules $(F_TMP).states $(F_TMP).system | \
		$(I2A) - > $(@F).acf
	$(eval MODEFILE := $(shell $(SCAN_MODEFILE)))
	@$(MODEGEN) $(MODEFILE) $(@F).acf
	@if [ -d ".git" ]; \
	then echo "inserting REV keyword ..."; $(WDLPATH)/insert_hash $(@F).acf; \
	else echo "not a git archive, skipping REV keyword"; \
	fi
	@echo "done"
