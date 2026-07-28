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
if __package__ in (None, ""):
    import sys
    import warnings
    from pathlib import Path

    # Add the repo/package parent directory so `import wdl...` works
    # even when this file is run directly.
    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root))

    module_name = Path(__file__).stem
    warnings.warn(
        f"Detected direct script execution. "
        f"Consider using: python -m wdl.{module_name}",
        RuntimeWarning,
        stacklevel=2,
    )

    from wdl import wdlParser as Parser
else:
    from . import wdlParser as Parser

import fileinput
import sys

sys.dont_write_bytecode = True
sys.tracebacklimit = 0

subroutines = None


# -----------------------------------------------------------------------------
# @fn     main
# @brief
# @param  source_text
# @return none
# -----------------------------------------------------------------------------
def main(input_source_text):
    """ """
    global subroutines

    # sequences and waveforms both wind up as callable subroutines
    # get a list of the names of sequences and waveforms
    subroutines = Parser.get_subroutines(input_source_text)

    Parser.get_params(input_source_text)

    wdl_output = Parser.parse(input_source_text)

    print(wdl_output)


# -----------------------------------------------------------------------------
#           __main__
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    source_text = ""
    for line in fileinput.input():
        source_text += line
    main(source_text)
