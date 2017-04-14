"""
The Character class will wrap a single character that the scanner retrieves 
from the source text. In addition to holding the character itself (its cargo)
it will hold information about the location of the character in the source text.
"""

ENDMARK = "\0"  # aka "lowvalues"

#-----------------------------------------------------------------------
#
#               Character
#
#-----------------------------------------------------------------------
class Character:
	"""
	A Character object holds
		- one character (self.cargo)
		- the index of the character's position in the sourceText.
		- the index of the line where the character was found in the sourceText.
		- the index of the column in the line where the character was found in the sourceText.
		- (a reference to) the entire sourceText (self.sourceText)

	This information will be available to a token that uses this character.
	If an error occurs, the token can use this information to report the
	line/column number where the error occurred, and to show an image of the
	line in sourceText where the error occurred.
	"""

	#-------------------------------------------------------------------
	#
	#-------------------------------------------------------------------
	def __init__(self, c, lineIndex, colIndex, sourceIndex, sourceText):
		"""
		In Python, the __init__ method is the constructor.
		"""
		self.cargo          = c
		self.sourceIndex    = sourceIndex
		self.lineIndex      = lineIndex
		self.colIndex       = colIndex
		self.sourceText     = sourceText


	#-------------------------------------------------------------------
	# return a displayable string representation of the Character object
	#-------------------------------------------------------------------
	def __str__(self):
		"""
		In Python, the __str__ method returns a string representation
		of an object.  In Java, this would be the toString() method.
		"""
		cargo = self.cargo
		if   cargo == " "     : cargo = "   space"
		elif cargo == "\n"    : cargo = "   newline"
		elif cargo == "\t"    : cargo = "   tab"
		elif cargo == ENDMARK : cargo = "   eof"

		return (
			  str(self.lineIndex).rjust(6)
			+ str(self.colIndex).rjust(4)
			+ "  "
			+ cargo
			)

