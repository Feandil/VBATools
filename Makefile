
all: VBALexer.py  VBALexer.tokens VBAParser.py  VBAParser.tokens

%.py %.tokens: %.g4
	antlr4 -no-listener  -Dlanguage=Python2 $*.g4



