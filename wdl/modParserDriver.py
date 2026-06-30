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



import fileinput
import sys

#hack to allow both modern style import and direct script execution
if __package__ in (None, ""):
    import sys
    import warnings
    from pathlib import Path

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

# -----------------------------------------------------------------------------
# @fn     main
# @brief
# @param  source_text
# @return none
# -----------------------------------------------------------------------------
def main(input_source_name, sourceText):
    """ """

    # create the .modules file
    modOutput = Parser.parse_modules(sourceText)
    modulesFilename = input_source_name.strip() + ".modules"
    f = open(modulesFilename, "w")
    f.write("[CONFIG]\n")
    f.write(modOutput)
    f.close()

    # create the .system file
    systemOutput = Parser.parse_system()
    systemFilename = input_source_name.strip() + ".system"
    f = open(systemFilename, "w")
    f.write("[SYSTEM]\n")
    f.write(systemOutput)
    f.close()


# -----------------------------------------------------------------------------
#           __main__
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    source_text = ""
    source_name = ""
    for line in fileinput.input():
        if fileinput.isfirstline():
            # the first line of the input must be
            # the name of the project to build
            source_name = line
        else:
            source_text += line
    main(source_name, source_text)
