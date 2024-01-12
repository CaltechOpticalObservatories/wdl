#!/usr/bin/env python

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

from __future__ import print_function
import sys
sys.dont_write_bytecode = True
sys.tracebacklimit=0
import fileinput
import wdlParser as parser

subroutines=[]

# -----------------------------------------------------------------------------
# @fn     main
# @brief  
# @param  source_text
# @return none
# -----------------------------------------------------------------------------
def main(sourceText):
    """
    """
    global token
    global subroutines

    # sequences and waveforms both wind up as callable subroutines
    # get a list of the names of sequences and waveforms
    subroutines = parser.get_subroutines(sourceText)

    parser.get_params(sourceText)

    wdlOutput = parser.parse(sourceText)

    print(wdlOutput)

# -----------------------------------------------------------------------------
#           __main__
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    source_text= ""
    for line in fileinput.input():
        source_text += line
    main(source_text)
