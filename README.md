# wdl
waveform definition language for Archons


Requirements:
 - any version of make
 - GPP (https://logological.org/gpp)
 
Instructions:

 - It is advised that wdl be in a separate directory from you ACF source files.
 - Copy the Makefile from the wdl directory to the directory which contains your ACF source files.
 - Edit the following three lines in your Makefile to indicate the correct locations of
 GPP, the path to your WDL directory (this directory), and the path to your ACF source files.
 
GPP       = /usr/local/bin/gpp
WDLPATH   = $(HOME)/Software/wdl
ACFPATH   = $(HOME)/Software/acf


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
