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

GPP       = /usr/local/bin/gpp
WDLPATH   = $(HOME)/Software/wdl
ACFPATH   = $(HOME)/Software/acf

PLOT      = False   # show waveform plots by default, True | False
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

