#!/usr/bin/env python
# -----------------------------------------------------------------------------
# @file     wavgenDriver.py
# @brief    driver script for PHM.wavgen
# @author   David Hale
# @date     2016-xx-xx
# @modified 2016-03-29 DH
# 
# This script invokes the PHM wavgen.
# -----------------------------------------------------------------------------

import sys
sys.dont_write_bytecode = True
sys.tracebacklimit=0
import fileinput
import wavgen
import matplotlib.pyplot as plt

# -----------------------------------------------------------------------------
# @fn     main
# @brief  
# @param  source, name of the input .wdl file without the .wdl part
# @return none
# -----------------------------------------------------------------------------
def main(source):
    """
    """
    input  = source+".wdl"
    output = source
    wavgen.GenerateFigs = False
    wavgen.loadWDL(input, output)
    plt.show(block=True)

# -----------------------------------------------------------------------------
#           __main__
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    if len(sys.argv) == 2:
        main(sys.argv[1])

