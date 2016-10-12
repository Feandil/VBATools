
all: gson-2.7.jar antlr4-4.5.3.jar VBA.jar

gson-2.7.jar:
	wget https://repo1.maven.org/maven2/com/google/code/gson/gson/2.7/gson-2.7.jar

antlr4-4.5.3.jar:
	wget https://repo1.maven.org/maven2/org/antlr/antlr4/4.5.3/antlr4-4.5.3.jar

%.java %.tokens: %.g4 antlr4-4.5.3.jar
	java -jar antlr4-4.5.3.jar -no-listener $*.g4

__class__:
	mkdir __class__

__class__/%.class: %.java __class__ antlr4-4.5.3.jar gson-2.7.jar
	javac -cp antlr4-4.5.3.jar:gson-2.7.jar:__class__ -d __class__ $*.java

__class__/VBAParser.class: __class__/VBALexer.class
__class__/VBA.class: __class__/VBALexer.class __class__/VBAParser.class

VBA.jar: __class__/VBALexer.class __class__/VBAParser.class __class__/VBA.class
	(cd __class__; jar -cfe ../VBA.jar VBA *.class)
