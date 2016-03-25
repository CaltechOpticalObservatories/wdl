#!/usr/bin/python
import fileinput
import PHM.wavgen
import matplotlib.pyplot as plt
import sys
sys.tracebacklimit=0

# -----------------------------------------------------------------------------
# @fn     main
# @brief  
# @param  sourceText
# @return none
# -----------------------------------------------------------------------------
def main():
    """
    """
    PHM.wavgen.loadWDL("test.wdl", "test")
    plt.show(block=True)

# -----------------------------------------------------------------------------
#           __main__
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    main()

