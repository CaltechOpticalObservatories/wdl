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
A Scanner object reads through the source_text
and returns one character at a time.
"""
source_text = ""
last_index = -1
source_index = -1
line_index = -1
col_index = -1


# -------------------------------------------------------------------
#
# -------------------------------------------------------------------
def initialize(source_text_arg):
	"""
	
	"""
	global source_text, last_index, source_index, line_index, col_index
	source_text = source_text_arg
	last_index = len(source_text) - 1
	source_index = -1
	line_index = 0
	col_index = -1


# -------------------------------------------------------------------
#
# -------------------------------------------------------------------
def get():
	"""
	Return the next character in source_text.
	"""
	global last_index, source_index, line_index, col_index

	source_index += 1    # increment the index in source_text

	# maintain the line count
	if source_index > 0:
		if source_text[source_index - 1] == "\n":
			# -------------------------------------------------------
			# The previous character in source_text was a newline
			# character.  So... we're starting a new line.
			# Increment line_index and reset col_index.
			# -------------------------------------------------------
			line_index += 1
			col_index = -1

	col_index += 1

	if source_index > last_index:
		# We've read past the end of source_text.
		# Return the ENDMARK character.
		char = Character(ENDMARK, line_index, col_index, source_index, source_text)
	else:
		c = source_text[source_index]
		char = Character(c, line_index, col_index, source_index, source_text)

	return char


# -------------------------------------------------------------------
#
# -------------------------------------------------------------------
def lookahead(offset=1):
	"""
	Return a string (not a Character object) containing the character
	at position:
			source_index + offset
	Note that we do NOT move our current position in the source_text.
	That is,  we do NOT change the value of source_index.
	"""
	index = source_index + offset

	if index > last_index:
		# We've read past the end of source_text.
		# Return the ENDMARK character.
		return ENDMARK
	else:
		return source_text[index]
