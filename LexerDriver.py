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

import Lexer   as     lexer
from   Symbols import EOF
import fileinput


#-------------------------------------------------
# support for writing output to a file
#-------------------------------------------------
def writeln(*args):
    for arg in args:
        f.write(str(arg))
    f.write("\n")

#-----------------------------------------------------------------------
#
#                    main
#
#-----------------------------------------------------------------------
def main(sourceText):
    global f
    f = open(outputFilename, "w")
    writeln("Here are the tokens returned by the lexer:")

    # create an instance of a lexer
    lexer.initialize(sourceText)

    #------------------------------------------------------------------
    # use the lexer.getlist() method repeatedly to get the tokens in
    # the sourceText. Then print the tokens.
    #------------------------------------------------------------------
    while True:
        token = lexer.get()
        writeln(token.show(True))
        if token.type == EOF: break
    f.close()

# -----------------------------------------------------------------------------
#           __main__
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    sourceText=""
    outputFilename = "LexerDriver_output.txt"
    for line in fileinput.input():
        sourceText += line
    main(sourceText)
    print(open(outputFilename).read())

