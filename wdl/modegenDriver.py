#!/usr/bin/env python
# -----------------------------------------------------------------------------
# @file     modegenDriver.py
# @brief    driver script for PHM's Modegen
# @author   David Hale
# @date     2017-02-08
# @modified 2017-02-08 DH
#
# This script invokes the PHM Modegen.
# -----------------------------------------------------------------------------

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

# import fileinput
import matplotlib.pyplot as plt
import wavgen
import modegen
import sys

sys.dont_write_bytecode = True


# -----------------------------------------------------------------------------
# @fn     main
# @brief
# @param  source, name of the input .wdl file without the .wdl part
# @return none
# -----------------------------------------------------------------------------
def main(source, toplot):
    """ """
    input_file = source + ".wdl"
    output = source
    if (
        toplot.upper() == "FALSE"
        or toplot.upper() == "NO"
        or toplot.upper() == "F"
        or toplot.upper() == "N"
        or toplot.upper() == "0"
    ):
        wavgen.GenerateFigs = False
    elif (
        toplot.upper() == "TRUE"
        or toplot.upper() == "YES"
        or toplot.upper() == "T"
        or toplot.upper() == "Y"
        or toplot.upper() == "1"
    ):
        wavgen.GenerateFigs = True
    else:
        print("warning: invalid plotting option specified, defaulting to True")
        wavgen.GenerateFigs = True

    wavgen.loadWDL(input_file, output)
    plt.show(block=True)


# -----------------------------------------------------------------------------
#           __main__
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # check for correct number of args passed
    # don't count the zeroeth arg, as it is my name
    if len(sys.argv[1:]) == 2:
        # main(sys.argv[1], sys.argv[2])
        modegen.Modegen(sys.argv[1], sys.argv[2]).write("a")
        sys.exit(0)
    else:
        print(
            "error: wavgenDriver.py got %d argument(s) but expecting 2"
            % (len(sys.argv[1:]))
        )
        sys.exit(1)
