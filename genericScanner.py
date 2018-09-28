"""
The scanner's job is to read the source file one character at a time. For 
each character, it keeps track of the line and character position where the 
character was found. Each time the scanner is called, it reads the next 
character from the file and returns it.
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

from genericCharacter import *

"""
A Scanner object reads through the sourceText
and returns one character at a time.
"""
#-------------------------------------------------------------------
#
#-------------------------------------------------------------------
def initialize(sourceTextArg):
	"""
	
	"""
	global sourceText, lastIndex, sourceIndex, lineIndex, colIndex
	sourceText = sourceTextArg
	lastIndex    = len(sourceText) - 1
	sourceIndex  = -1
	lineIndex    =  0
	colIndex     = -1


#-------------------------------------------------------------------
#
#-------------------------------------------------------------------
def get():
	"""
	Return the next character in sourceText.
	"""
	global lastIndex, sourceIndex, lineIndex, colIndex

	sourceIndex += 1    # increment the index in sourceText

	# maintain the line count
	if sourceIndex > 0:
		if sourceText[sourceIndex - 1] == "\n":
			#-------------------------------------------------------
			# The previous character in sourceText was a newline
			# character.  So... we're starting a new line.
			# Increment lineIndex and reset colIndex.
			#-------------------------------------------------------
			lineIndex +=1
			colIndex  = -1

	colIndex += 1

	if sourceIndex > lastIndex:
		# We've read past the end of sourceText.
		# Return the ENDMARK character.
		char = Character(ENDMARK, lineIndex, colIndex, sourceIndex,sourceText)
	else:
		c    = sourceText[sourceIndex]
		char = Character(c, lineIndex, colIndex, sourceIndex, sourceText)

	return char


#-------------------------------------------------------------------
#
#-------------------------------------------------------------------
def lookahead(offset=1):
	"""
	Return a string (not a Character object) containing the character
	at position:
			sourceIndex + offset
	Note that we do NOT move our current position in the sourceText.
	That is,  we do NOT change the value of sourceIndex.
	"""
	index = sourceIndex + offset

	if index > lastIndex:
		# We've read past the end of sourceText.
		# Return the ENDMARK character.
		return ENDMARK
	else:
		return sourceText[index]
