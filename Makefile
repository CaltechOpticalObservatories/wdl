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
#
# This Makefile uses the general preprocessor GPP 2.24 for macro processing.
# It also requires the ini2acf.pl Perl script for creating an Archon acf file.
#
# -----------------------------------------------------------------------------
#

GPP       = /usr/local/bin/gpp
GFLAGS    = +c "/*" "*/" +c "//" "\n" +c "\\\n" ""
INCPARSER = /home/ztf/devel/wdl/incParserDriver.py
WDLPARSER = /home/ztf/devel/wdl/wdlParserDriver.py
MODPARSER = /home/ztf/devel/wdl/modParserDriver.py
WAVGEN    = /home/ztf/devel/wdl/wavgenDriver.py
I2A       = /home/ztf/devel/perl/ini2acf.pl
INCL      = -I$(CURDIR)

%:	;
	@test -f $(@F).conf || echo $(@F).conf does not exist
	@echo making $(@F).wdl ...
	@test -f $(@F).conf && cat $(@F).conf | $(INCPARSER) - | $(GPP) $(GFLAGS) $(INCL) |  $(WDLPARSER) - > $(@F).wdl
	@echo making $(@F).script, $(@F).states ...
	@test -f $(@F).mod || echo $(@F).mod does not exist
	@test -f $(@F).mod && echo $(@F) | cat  - $(@F).mod | $(GPP) $(GFLAGS) $(INCL) |  $(MODPARSER) -
	@$(WAVGEN) $(@F)
	@echo making $(@F).acf ...
	@test -f $(@F).cds || echo $(@F).cds does not exist
	@test -f $(@F).cds && echo "[CONFIG]" | \
		cat - $(@F).cds | $(GPP) $(GFLAGS) $(INCL) | \
		cat - $(@F).script $(@F).modules $(@F).states $(@F).system | \
		$(I2A) - > $(@F).acf
