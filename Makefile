# -----------------------------------------------------------------------------
# @file     Makefile
# @brief    Makefile for Software/Config/Archon/Build/
# @author   David Hale
# @date     2015-xx-xx
# @modified 2016-01-14
# @modified 2016-01-27 added fixrawendline (special case for Peter)
# @modified 2016-01-28 removed clean. Use @F.h instead of HFILE=archon.h
#
# This Makefile uses the general preprocessor GPP 2.24 for macro processing.
# It also requires the ini2acf.pl Perl script for creating an Archon acf file.
#
# -----------------------------------------------------------------------------
#

# set FIXRAW = yes to run "fixrawendline.pl" script on resultant .acf file
#
FIXRAW	= no

GPP	= /usr/local/bin/gpp
GFLAGS	= +c "/*" "*/" +c "//" "\n" +c "\\\n" ""
PARSER	= /home/ztf/devel/wdl/ParserDriver.py
I2A	= /home/ztf/devel/perl/ini2acf.pl
FRE	= /home/ztf/devel/perl/fixrawendline.pl

INCL	= -I$(CURDIR)

TMPFILE	:= $(shell mktemp)

all:	;
	@echo "please specify an instrument name (corresponding to a .def file)"

%:	;
	@echo making $(@F)...
	@echo "signalfile $(@F).signals" > $(@F).wdl
	@cat $(@F).waveform $(@F).seq | $(GPP) $(GFLAGS) $(INCL) |  $(PARSER) - >> $(@F).wdl
