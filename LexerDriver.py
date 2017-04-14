#!/usr/bin/env python
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

