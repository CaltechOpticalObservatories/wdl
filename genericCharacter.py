"""
The Character class will wrap a single character that the scanner retrieves 
from the source text. In addition to holding the character itself (its cargo)
it will hold information about the location of the character in the source text.
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
# 

ENDMARK = "\0"  # aka "lowvalues"


# -----------------------------------------------------------------------
#
#               Character
#
# -----------------------------------------------------------------------
class Character:
	"""
	A Character object holds
		- one character (self.cargo)
		- the index of the character's position in the source_text.
		- the index of the line where the character was found in the source_text.
		- the index of the column where the character was found in the source_text.
		- (a reference to) the entire source_text (self.source_text)

	This information will be available to a token that uses this character.
	If an error occurs, the token can use this information to report the
	line/column number where the error occurred, and to show an image of the
	line in source_text where the error occurred.
	"""

	# -------------------------------------------------------------------
	#
	# -------------------------------------------------------------------
	def __init__(self, c, line_index, col_index, source_index, source_text):
		"""
		In Python, the __init__ method is the constructor.
		"""
		self.cargo = c
		self.source_index = source_index
		self.line_index = line_index
		self.col_index = col_index
		self.source_text = source_text

	# -------------------------------------------------------------------
	# return a displayable string representation of the Character object
	# -------------------------------------------------------------------
	def __str__(self):
		"""
		In Python, the __str__ method returns a string representation
		of an object.  In Java, this would be the toString() method.
		"""
		cargo = self.cargo
		if cargo == " ":
			cargo = "   space"

		elif cargo == "\n":
			cargo = "   newline"

		elif cargo == "\t":
			cargo = "   tab"

		elif cargo == ENDMARK:
			cargo = "   eof"

		return (
				str(self.line_index).rjust(6)
				+ str(self.col_index).rjust(4)
				+ "  "
				+ cargo
		)
