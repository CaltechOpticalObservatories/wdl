"""
A Lexer (aka: Tokenizer, Lexical Analyzer) for the waveform development
language. When we instantiate the Lexer class, we will pass the constructor a
string containing the source text. The Lexer object will create a scanner
object and pass the source text to it. Then the Lexer will get characters
from the scanner, which will get them from the source text. The result will
be a Lexer object that is ready to return the tokens in the source text.
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

from . import genericScanner as Scanner
from .genericToken import *
from .Symbols import *
from .genericCharacter import *

character = ''
c1 = ''
c2 = ''


class LexerError(Exception):
	pass


def dq(s):
	"""
	enclose string s in double quotes
	"""
	return '"%s"' % s


# -------------------------------------------------------------------
#
# -------------------------------------------------------------------
def initialize(source_text):
	"""
	"""
	# global scanner

	# initialize the scanner with the source_text
	Scanner.initialize(source_text)

	# use the scanner to read the first character from the source_text
	get_char()


# -------------------------------------------------------------------
#
# -------------------------------------------------------------------
def get():
	"""
	Construct and return the next token in the source_text.
	"""

	# --------------------------------------------------------------------------------
	# read past and ignore any whitespace characters or any comments -- START
	# --------------------------------------------------------------------------------
	while c1 in WHITESPACE_CHARS or c2 == "/*":

		# process whitespace
		while c1 in WHITESPACE_CHARS:
			token = Token(character)
			token.type = WHITESPACE
			get_char()

			while c1 in WHITESPACE_CHARS:
				token.cargo += c1
				get_char()
						
			# return token  # only if we want the Lexer to return whitespace

		# process comments
		while c2 == "/*":
			# we found comment start
			token = Token(character)
			token.type = COMMENT
			token.cargo = c2

			get_char()  # read past the first  character of a 2-character token
			get_char()  # read past the second character of a 2-character token

			while not (c2 == "*/"):
				if c1 == ENDMARK:
					token.abort("Found end of file before end of comment")
				token.cargo += c1
				get_char()

			token.cargo += c2  # append the */ to the token cargo

			get_char()  # read past the first  character of a 2-character token
			get_char()  # read past the second character of a 2-character token
			
			# return token  # only if we want the Lexer to return comments
	# --------------------------------------------------------------------------------
	# read past and ignore any whitespace characters or any comments -- END
	# --------------------------------------------------------------------------------

	# Create a new token.  The token will pick up
	# its line and column information from the character.
	token = Token(character)

	if c1 == ENDMARK:
		token.type = EOF
		return token

	if c1 in IDENTIFIER_STARTCHARS:
		token.type = IDENTIFIER
		get_char()

		while c1 in IDENTIFIER_CHARS:
			token.cargo += c1
			get_char()

		if token.cargo.upper() in Keywords:
			token.type = token.cargo.upper()
		return token

	if c1 in NUMBER_STARTCHARS:
		token.type = NUMBER
		get_char()
		
		while c1 in NUMBER_CHARS:
			token.cargo += c1
			get_char()
		return token

	if c1 in STRING_STARTCHARS:
		# remember the quote_char (single or double quote)
		# so we can look for the same character to terminate the quote.
		quote_char = c1

		get_char()

		while c1 != quote_char:
			if c1 == ENDMARK:
				token.abort("Found end of file before end of string literal")

			token.cargo += c1  # append quoted character to text
			get_char()

		token.cargo += c1      # append close quote to text
		get_char()
		token.type = STRING
		return token

	if c2 in TwoCharacterSymbols:
		token.cargo = c2
		token.type = token.cargo  # for symbols, the token type is same as the cargo
		get_char()  # read past the first  character of a 2-character token
		get_char()  # read past the second character of a 2-character token
		return token

	if c1 in OneCharacterSymbols or c1 in PreSpaceSymbols:
		token.type = token.cargo  # for symbols, the token type is same as the cargo
		get_char()  # read past the symbol
		return token

	# else.... We have encountered something that we don't recognize.
	print(OneCharacterSymbols)
	print(TwoCharacterSymbols)
	print(PreSpaceSymbols)
	print((hex(ord(c1))))
	token.abort("I found a character or symbol that I do not recognize: " + dq(c1))


# -------------------------------------------------------------------
#
# -------------------------------------------------------------------
def get_char():
	"""
	get the next character
	"""
	global c1, c2, character
	character = Scanner.get()
	c1 = character.cargo
	# ---------------------------------------------------------------
	# Every time we get a character from the scanner, we also  
	# lookahead to the next character and save the results in c2.
	# This makes it easy to lookahead 2 characters.
	# ---------------------------------------------------------------
	c2 = c1 + Scanner.lookahead(1)


	
