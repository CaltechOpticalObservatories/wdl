"""
The Token class will wrap its cargo -- a string of characters that is the text
of the token. In addition to holding its cargo, the token will hold information
about the location of the token (actually, the location of its first character)
in the source text.
"""

from genericScanner import *

class LexerError(Exception): pass

#-----------------------------------------------------------------------
#
#               Token
#
#-----------------------------------------------------------------------
class Token:
	"""
	A Token object is the kind of thing that the Lexer returns.
	It holds:
	- the text of the token... self.cargo
	- the type of token that it is... self.type
	- the line number and column index where the token starts... self.show(True)
	"""

	#-------------------------------------------------------------------
	#
	#-------------------------------------------------------------------
	def __init__(self, startChar):
		"""
		The constructor of the Token class
		"""
		self.cargo     = startChar.cargo

		#----------------------------------------------------------
		# The token picks up information
		# about its location in the sourceText
		#----------------------------------------------------------
		self.sourceText = startChar.sourceText
		self.lineIndex  = startChar.lineIndex
		self.colIndex   = startChar.colIndex

		#----------------------------------------------------------
		# We won't know what kind of token we have until we have
		# finished processing all of the characters in the token.
		# So when we start, the token.type is None (aka null).
		#----------------------------------------------------------
		self.type      = None

	#-------------------------------------------------------------------
	#  return a displayable string representation of the token
	#-------------------------------------------------------------------
	def show(self,showLineNumbers=False,**kwargs):
		"""
		align=True shows token type left justified with dot leaders.
		Specify align=False to turn this feature OFF.		
		"""
		align = kwargs.get("align",True)
		if align: 
			tokenTypeLen = 12
			space = " "
		else: 
			tokenTypeLen = 0
			space = ""
			
		if showLineNumbers:
			s = str(self.lineIndex).rjust(6) + str(self.colIndex).rjust(4) + "  "
		else:
			s = ""
			
		if self.type == self.cargo: 
			s = s + "Symbol".ljust(tokenTypeLen,".") + ":" + space + self.type
		elif self.type == "Whitespace": 
			s = s + "Whitespace".ljust(tokenTypeLen,".") + ":" + space + repr(self.cargo)
		else:
			s = s + self.type.ljust(tokenTypeLen,".") + ":" + space + self.cargo
		return s
			
	guts = property(show)


	#-------------------------------------------------------------------
	#
	#-------------------------------------------------------------------
	def abort(self,msg):
		"""
		"""
		lines = self.sourceText.split("\n")
		sourceLine = lines[self.lineIndex]
		raise LexerError("\nIn line "      + str(self.lineIndex + 1)
			   + " near column " + str(self.colIndex + 1) + ":\n\n"
			   + sourceLine.replace("\t"," ") + "\n"
			   + " "* self.colIndex
			   + "^\n\n"
			   + msg)
