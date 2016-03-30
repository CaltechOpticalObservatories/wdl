#!/usr/bin/python
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
    parser.parse_modules(sourceText)

# -----------------------------------------------------------------------------
#           __main__
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    sourceText=""
    for line in fileinput.input():
        sourceText += line
    main(sourceText)
