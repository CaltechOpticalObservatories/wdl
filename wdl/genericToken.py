"""
The Token class will wrap its cargo -- a string of characters that is the text
of the token. In addition to holding its cargo, the token will hold information
about the location of the token (actually, the location of its first character)
in the source text.
"""

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

# from genericScanner import *


class LexerError(Exception):
    pass


# -----------------------------------------------------------------------
#
#               Token
#
# -----------------------------------------------------------------------
class Token:
    """
    A Token object is the kind of thing that the Lexer returns.
    It holds:
    - the text of the token... self.cargo
    - the type of token that it is... self.type
    - the line number and column index where the token starts... self.show(True)
    """

    # -------------------------------------------------------------------
    #
    # -------------------------------------------------------------------
    def __init__(self, start_char):
        """
        The constructor of the Token class
        """
        self.cargo = start_char.cargo

        # ----------------------------------------------------------
        # The token picks up information
        # about its location in the source_text
        # ----------------------------------------------------------
        self.source_text = start_char.source_text
        self.line_index = start_char.line_index
        self.col_index = start_char.col_index

        # ----------------------------------------------------------
        # We won't know what kind of token we have until we have
        # finished processing all the characters in the token.
        # So when we start, the token.type is None (aka null).
        # ----------------------------------------------------------
        self.type = None

    # -------------------------------------------------------------------
    #  return a displayable string representation of the token
    # -------------------------------------------------------------------
    def show(self, show_line_numbers=False, **kwargs):
        """
        align=True shows token type left justified with dot leaders.
        Specify align=False to turn this feature OFF.
        """
        align = kwargs.get("align", True)
        if align:
            token_type_len = 12
            space = " "
        else:
            token_type_len = 0
            space = ""

        if show_line_numbers:
            s = str(self.line_index).rjust(6) + str(self.col_index).rjust(4) + "  "
        else:
            s = ""

        if self.type == self.cargo:
            s = s + "Symbol".ljust(token_type_len, ".") + ":" + space + self.type
        elif self.type == "Whitespace":
            s = (
                s
                + "Whitespace".ljust(token_type_len, ".")
                + ":"
                + space
                + repr(self.cargo)
            )
        else:
            s = s + self.type.ljust(token_type_len, ".") + ":" + space + self.cargo
        return s

    guts = property(show)

    # -------------------------------------------------------------------
    #
    # -------------------------------------------------------------------
    def abort(self, msg):
        """ """
        lines = self.source_text.split("\n")
        source_line = lines[self.line_index]
        raise LexerError(
            "\nIn line "
            + str(self.line_index + 1)
            + " near column "
            + str(self.col_index + 1)
            + ":\n\n"
            + source_line.replace("\t", " ")
            + "\n"
            + " " * self.col_index
            + "^\n\n"
            + msg
        )
