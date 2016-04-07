#!/usr/bin/env python
from __future__ import print_function
import fileinput
import wdlParser as parser
import sys
sys.dont_write_bytecode = True
sys.tracebacklimit=0

# -----------------------------------------------------------------------------
# @fn     main
# @brief  
# @param  sourceText
# @return none
# -----------------------------------------------------------------------------
def main(sourceName, sourceText):
    """
    """

    # create the .modules file
    modOutput       = parser.parse_modules(sourceText)
    modulesFilename = sourceName.strip() + ".modules"
    f = open(modulesFilename, "w")
    f.write("[CONFIG]\n")
    f.write(modOutput)
    f.close()

    # create the .system file
    systemOutput   = parser.parse_system()
    systemFilename = sourceName.strip() + ".system"
    f = open(systemFilename, "w")
    f.write("[SYSTEM]\n")
    f.write(systemOutput)
    f.close()

# -----------------------------------------------------------------------------
#           __main__
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    sourceText=""
    for line in fileinput.input():
        if fileinput.isfirstline():
            # the first line of the input must be the name of the project to build
            sourceName = line
        else:
            sourceText += line
    main(sourceName, sourceText)
