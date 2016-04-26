"""
These are the allowed symbols for the WDL.
An identifier can contain letters, digits and underscores.
An identifier must start with a letter.
"""


#----------------------------------------------------------
# a list of keywords -- must be defined here as UPPERCASE
#----------------------------------------------------------
Keywords = """
WAVEFORM
SET
TO
IF
GOTO
CALL
RETURN
PARAM
SLOT
DRV
HVLC
HVHC
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
SLOW
FAST
"""
Keywords = Keywords.split()

#----------------------------------------------------------
# a list of symbols that are one character long
#----------------------------------------------------------
OneCharacterSymbols = """
! =
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
