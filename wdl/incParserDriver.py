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

#hack to allow both modern style import and direct script execution
if __package__ != "wdl":
    import os
    import warnings
    basen = os.path.basename(__file__)
    warnings.warn(f"detected running a script directly, consider using python -m wdl.{basen}")
    import wdlParser as Parser
else:
    from . import wdlParser as Parser

import fileinput
import sys

sys.dont_write_bytecode = True
sys.tracebacklimit = 0


# -----------------------------------------------------------------------------
# @fn     main
# @brief
# @param  source_text
# @return none
# -----------------------------------------------------------------------------
def main(input_source_text):
    """ """
    # global token
    Parser.make_include(input_source_text)


# -----------------------------------------------------------------------------
#           __main__
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    source_text = ""
    for line in fileinput.input():
        source_text += line
    main(source_text)
