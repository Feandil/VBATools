from oletools.olevba import VBA_Parser
from antlr4 import *
from VBALexer import VBALexer
from VBAParser import VBAParser

class VBADeobsfuscator(object):

    VAR_DECL_XPATH = ['ModuleSimpleContext', 'ModuleDeclarationsContext',
                      'ModuleDeclarationsElementContext', 'VariableStmtContext',
                      'VariableListStmtContext', 'VariableSubStmtContext', 'IdentifierContext']
    SUB_DECL_XPATH = ['ModuleSimpleContext', 'ModuleBodyContext', 'ModuleBodyElementContext', 'SubStmtContext']
    SUB_IDENT_XPATH = ['SubroutineNameContext', 'IdentifierContext', '*', 'IdentifierValueContext']
    FUN_DECL_XPATH = ['ModuleSimpleContext', 'ModuleBodyContext', 'ModuleBodyElementContext', 'FunctionStmtContext']
    FUN_IDENT_XPATH = ['FunctionNameContext', 'IdentifierContext', '*', 'IdentifierValueContext']

    @staticmethod
    def get_vba(file):
        vbaparser = VBA_Parser(file)
        return [code for (_f, _p, _name, code) in vbaparser.extract_macros()]

    @staticmethod
    def parse_vba(vba):
        lexer = VBALexer(InputStream(vba))
        stream = CommonTokenStream(lexer)
        parser = VBAParser(stream)
        return parser.startRuleSimple()

    @staticmethod
    def _xpath(path, node):
        if not path:
            return [node]
        name = path[0]
        path = path[1:]
        if name == '*':
            return [ret for elt in node.children for ret in VBADeobsfuscator._xpath(path, elt)]
        cls = getattr(VBAParser, name)
        ret = []
        for child in node.children:
            if isinstance(child, cls):
                ret.extend(VBADeobsfuscator._xpath(path, child))
        return ret

    @staticmethod
    def _extract_base(content):
        assert(isinstance(content, VBAParser.StartRuleSimpleContext))
        assert(isinstance(content.children[0], VBAParser.ModuleSimpleContext))
        variables = []
        functions = {}
        subs = {}
        for elt in VBADeobsfuscator._xpath(VBADeobsfuscator.VAR_DECL_XPATH, content):
            variables.append(elt.getText())
        for fun in VBADeobsfuscator._xpath(VBADeobsfuscator.FUN_DECL_XPATH, content):
            names = VBADeobsfuscator._xpath(VBADeobsfuscator.FUN_IDENT_XPATH, fun)
            assert(len(names) == 1)
            functions[names[0].getText()] = fun
        for sub in VBADeobsfuscator._xpath(VBADeobsfuscator.SUB_DECL_XPATH, content):
            names = VBADeobsfuscator._xpath(VBADeobsfuscator.SUB_IDENT_XPATH, sub)
            assert(len(names) == 1)
            subs[names[0].getText()] = sub

        return (variables, functions, subs)

    def __init__(self, file):
        vbas = self.get_vba(file)
        self._content = [self.parse_vba(vba) for vba in vbas]

