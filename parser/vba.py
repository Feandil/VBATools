from antlr4 import *
from .VBALexer import VBALexer
from .VBAParser import VBAParser

class VBA(object):

    VAR_DECL_XPATH = ['ModuleSimpleContext', 'ModuleDeclarationsContext',
                      'ModuleDeclarationsElementContext', 'VariableStmtContext']
    VAR_IDENT_XPATH = ['VariableListStmtContext', 'VariableSubStmtContext', 'IdentifierContext']
    SUB_DECL_XPATH = ['ModuleSimpleContext', 'ModuleBodyContext', 'ModuleBodyElementContext', 'SubStmtContext']
    SUB_IDENT_XPATH = ['SubroutineNameContext', 'IdentifierContext', '*', 'IdentifierValueContext']
    FUN_DECL_XPATH = ['ModuleSimpleContext', 'ModuleBodyContext', 'ModuleBodyElementContext', 'FunctionStmtContext']
    FUN_IDENT_XPATH = ['FunctionNameContext', 'IdentifierContext', '*', 'IdentifierValueContext']
    ARG_XPATH = ['ArgListContext', 'ArgContext', '*', 'IdentifierContext', '*', 'IdentifierValueContext']

    @classmethod
    def xpath(cls, node, path):
        if isinstance(node, tree.Tree.TerminalNodeImpl):
            return []
        if not path:
            return [node]
        if not node.getChildCount():
            return []
        name, path = path[0], path[1:]
        if name == '*':
            return [ret for elt in node.children for ret in cls.xpath(elt, path)]
        req_cls = getattr(VBAParser, name)
        ret = []
        for child in node.children:
            if isinstance(child, req_cls):
                ret.extend(cls.xpath(child, path))
        return ret

    @classmethod
    def _extract_part(cls, content, name):
        decl_xpath = getattr(cls, '{0}_DECL_XPATH'.format(name))
        ident_xpath = getattr(cls, '{0}_IDENT_XPATH'.format(name))
        ret = {}
        for elt in cls.xpath(content, decl_xpath):
            names = cls.xpath(elt, ident_xpath)
            assert(len(names) == 1)
            ret[names[0].getText()] = elt
        return ret

    @classmethod
    def extract_var(cls, content):
        return cls._extract_part(content, 'VAR')

    @classmethod
    def extract_sub(cls, content):
        return cls._extract_part(content, 'SUB')

    @classmethod
    def extract_fun(cls, content):
        return cls._extract_part(content, 'FUN')

    @staticmethod
    def parse(vba):
        lexer = VBALexer(InputStream(vba))
        stream = CommonTokenStream(lexer)
        parser = VBAParser(stream)
        content = parser.startRuleSimple()
        assert(isinstance(content, VBAParser.StartRuleSimpleContext))
        assert(isinstance(content.children[0], VBAParser.ModuleSimpleContext))
        return content

    @classmethod
    def findall(cls, node, req_cls):
        if isinstance(node, tree.Tree.TerminalNodeImpl):
            return []
        if not node.getChildCount():
            return []
        if isinstance(req_cls, basestring):
            req_cls = getattr(VBAParser, req_cls)
        if isinstance(node, req_cls):
            return [node]
        return [e for c in node.children for e in cls.findall(c, req_cls)]
