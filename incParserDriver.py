#!/usr/bin/python
from __future__ import print_function
import fileinput
import wdlParser as parser
import sys
sys.tracebacklimit=0

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
    parser.make_include(sourceText)

# -----------------------------------------------------------------------------
#           __main__
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    sourceText=""
    for line in fileinput.input():
        sourceText += line
    main(sourceText)
