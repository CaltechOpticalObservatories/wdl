# -----------------------------------------------------------------------------
# @file     Makefile
# @brief    Makefile for Software/Config/Archon/Build/
# @author   David Hale
# @date     2015-xx-xx
# @modified 2016-01-14
# @modified 2016-01-27 added fixrawendline (special case for Peter)
# @modified 2016-01-28 removed clean. Use @F.h instead of HFILE=archon.h
# @modified 2016-03-31 change how .mod is parsed
#
# This Makefile uses the general preprocessor GPP 2.24 for macro processing.
# It also requires the ini2acf.pl Perl script for creating an Archon acf file.
#
# -----------------------------------------------------------------------------
#

GPP	= /usr/local/bin/gpp
GFLAGS	= +c "/*" "*/" +c "//" "\n" +c "\\\n" ""
WDLPARSER	= /home/ztf/devel/wdl/wdlParserDriver.py
MODPARSER	= /home/ztf/devel/wdl/modParserDriver.py
WAVGEN	= /home/ztf/devel/wdl/wavgenDriver.py
I2A	= /home/ztf/devel/perl/ini2acf.pl

INCL	= -I$(CURDIR)

%:	;
	@echo making $(@F).wdl ...
	@echo "signalfile $(@F).signals" > $(@F).wdl
	@cat $(@F).waveform $(@F).seq | $(GPP) $(GFLAGS) $(INCL) |  $(WDLPARSER) - >> $(@F).wdl
	@echo making $(@F).script, $(@F).states ...
	@echo $(@F) | cat  - $(@F).mod | $(GPP) $(GFLAGS) $(INCL) |  $(MODPARSER) -
	@$(WAVGEN) $(@F)
#	@echo "[CONFIG]" | cat - $(@F).script $(@F).modules $(@F).states $(@F).system | $(I2A) - > $(@F).acf
	@echo making $(@F).acf ...
	@echo "[CONFIG]" | \
		cat - $(@F).cds | $(GPP) $(GFLAGS) $(INCL) | \
		cat - $(@F).script $(@F).modules $(@F).states $(@F).system | \
		$(I2A) - > $(@F).acf
