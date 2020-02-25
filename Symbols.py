"""
These are the allowed symbols for the WDL.
An identifier can contain letters, digits and underscores.
An identifier must start with a letter.
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

#----------------------------------------------------------
# a list of keywords -- must be defined here as UPPERCASE
#----------------------------------------------------------
Keywords = """
WAVEFORM
SEQUENCE
SIGNALS
SET
TO
IF
GOTO
CALL
RETURN
PARAM
CONST
PRINT
SLOT
DRV
HVLC
HVHC
LVLC
LVHC
CLAMP
PREAMPGAIN
DIO
DIOPOWER
CDS_FILE
MODULE_FILE
WAVEFORM_FILE
SIGNAL_FILE
SEQUENCE_FILE
INCLUDE_FILE
MODE_FILE
SLOW
FAST
"""
Keywords = Keywords.split()

#----------------------------------------------------------
# a list of symbols that require a leading space and no trailing space
#----------------------------------------------------------
PreSpaceSymbols = """
!
"""
PreSpaceSymbols = PreSpaceSymbols.split()

#----------------------------------------------------------
# a list of symbols that are one character long
#----------------------------------------------------------
OneCharacterSymbols = """
=
( )
[ ]
{ }
/ * + -
. : , ;
"""
OneCharacterSymbols = OneCharacterSymbols.split()

#----------------------------------------------------------
# a list of symbols that are two characters long
#----------------------------------------------------------
TwoCharacterSymbols = """
.+
++
--
"""
TwoCharacterSymbols = TwoCharacterSymbols.split()

import string

IDENTIFIER_STARTCHARS = string.letters
IDENTIFIER_CHARS      = string.letters + string.digits + "_"

NUMBER_STARTCHARS     = string.digits
NUMBER_CHARS          = string.digits + "."

STRING_STARTCHARS = "'" + '"'
WHITESPACE_CHARS  = " \t\n"

#-----------------------------------------------------------------------
# TokenTypes for things other than symbols and keywords
#-----------------------------------------------------------------------
STRING             = "String"
IDENTIFIER         = "Identifier"
NUMBER             = "Number"
WHITESPACE         = "Whitespace"
COMMENT            = "Comment"
EOF                = "Eof"
