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

from . import Lexer
from .Symbols import EOF
import fileinput


# -----------------------------------------------------------------------
#
#                    main
#
# -----------------------------------------------------------------------
def main(input_source_text):
    # -------------------------------------------------
    # support for writing output to a file
    # -------------------------------------------------

    f = open(outputFilename, "w")

    def writeln(*args):
        for arg in args:
            f.write(str(arg))
        f.write("\n")

    writeln("Here are the tokens returned by the Lexer:")

    # create an instance of a Lexer
    Lexer.initialize(input_source_text)

    # ------------------------------------------------------------------
    # use the Lexer.getlist() method repeatedly to get the tokens in
    # the source_text. Then print the tokens.
    # ------------------------------------------------------------------
    while True:
        token = Lexer.get()
        writeln(token.show(True))
        if token.type == EOF:
            break
    f.close()


# -----------------------------------------------------------------------------
#           __main__
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    source_text = ""
    outputFilename = "LexerDriver_output.txt"
    for line in fileinput.input():
        source_text += line
    main(source_text)
    print(open(outputFilename).read())
