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
#
# This Makefile uses the general preprocessor GPP 2.24 for macro processing.
# It also requires the ini2acf.pl Perl script for creating an Archon acf file.
#
# -----------------------------------------------------------------------------
#

GPP       = /usr/local/bin/gpp
WDLPATH   = /home/ztf/devel/wdl
ACFPATH   = /home/ztf/Software/acf

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
	@scp -p $(@F).acf 192.168.1.2:$(ACFPATH)
	@scp -p $(@F).acf 192.168.1.3:$(ACFPATH)
	@scp -p $(@F).acf 192.168.1.4:$(ACFPATH)
	@scp -p $(@F).acf 192.168.1.5:$(ACFPATH)
	@scp -p $(@F).acf 192.168.1.6:$(ACFPATH)
