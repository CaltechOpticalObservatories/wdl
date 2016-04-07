#!/usr/bin/env python
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
# @param  sourceText
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
    sourceText=""
    for line in fileinput.input():
        sourceText += line
    main(sourceText)
