from oletools.olevba import VBA_Parser
from antlr4 import *
from VBALexer import VBALexer
from VBAParser import VBAParser

class VBADeobsfuscator(object):

    VAR_DECL_XPATH = ['ModuleSimpleContext', 'ModuleDeclarationsContext',
                      'ModuleDeclarationsElementContext', 'VariableStmtContext']
    VAR_IDENT_XPATH = ['VariableListStmtContext', 'VariableSubStmtContext', 'IdentifierContext']
    SUB_DECL_XPATH = ['ModuleSimpleContext', 'ModuleBodyContext', 'ModuleBodyElementContext', 'SubStmtContext']
    SUB_IDENT_XPATH = ['SubroutineNameContext', 'IdentifierContext', '*', 'IdentifierValueContext']
    FUN_DECL_XPATH = ['ModuleSimpleContext', 'ModuleBodyContext', 'ModuleBodyElementContext', 'FunctionStmtContext']
    FUN_IDENT_XPATH = ['FunctionNameContext', 'IdentifierContext', '*', 'IdentifierValueContext']
    ARG_XPATH = ['ArgListContext', 'ArgContext', '*', 'IdentifierContext', '*', 'IdentifierValueContext']

    def __init__(self, file):
        vbaparser = VBA_Parser(file)
        self._raw = [code for (_f, _p, _name, code) in vbaparser.extract_macros()]
        self._content = []
        self._var = {}
        self._fun = {}
        self._sub = {}

    @staticmethod
    def _xpath(node, path):
        if isinstance(node, tree.Tree.TerminalNodeImpl):
            return []
        if not path:
            return [node]
        if not node.getChildCount():
            return []
        name = path[0]
        path = path[1:]
        if name == '*':
            return [ret for elt in node.children for ret in VBADeobsfuscator._xpath(elt, path)]
        cls = getattr(VBAParser, name)
        ret = []
        for child in node.children:
            if isinstance(child, cls):
                ret.extend(VBADeobsfuscator._xpath(child, path))
        return ret

    def _extract_part(self, name):
        decl_xpath = getattr(self, '{0}_DECL_XPATH'.format(name.upper()))
        ident_xpath = getattr(self, '{0}_IDENT_XPATH'.format(name.upper()))
        dic = getattr(self, '_{0}'.format(name.lower()))
        for content in self._content:
            for elt in VBADeobsfuscator._xpath(content, decl_xpath):
                names = VBADeobsfuscator._xpath(elt, ident_xpath)
                assert(len(names) == 1)
                dic[names[0].getText()] = elt

    def parse(self):
        for vba in self._raw:
            lexer = VBALexer(InputStream(vba))
            stream = CommonTokenStream(lexer)
            parser = VBAParser(stream)
            content = parser.startRuleSimple()
            assert(isinstance(content, VBAParser.StartRuleSimpleContext))
            assert(isinstance(content.children[0], VBAParser.ModuleSimpleContext))
            self._content.append(content)
        self._extract_part('var')
        self._extract_part('sub')
        self._extract_part('fun')

    @staticmethod
    def _findall(node, cls):
        if isinstance(node, tree.Tree.TerminalNodeImpl):
            return []
        if not node.getChildCount():
            return []
        if isinstance(cls, basestring):
            cls = getattr(VBAParser, cls)
        if isinstance(node, cls):
            return [node]
        return [e for c in node.children for e in VBADeobsfuscator._findall(c, cls)]

    @staticmethod
    def _check_arguments(name, fun):
      raw_arguments = VBADeobsfuscator._xpath(fun, VBADeobsfuscator.ARG_XPATH)
      text_args = [e.getText() for e in raw_arguments]
      blocks = VBADeobsfuscator._xpath(fun, ['BlockContext'])
      assert(len(blocks) == 1)
      raw_identifiers = set(VBADeobsfuscator._findall(blocks[0], 'IdentifierValueContext'))
      text_ids = [e.getText() for e in raw_identifiers]
      for arg in text_args:
          if arg not in text_ids:
              print('{0}: {1} not used'.format(name, arg))

    def check_funsub(self):
       for fun in self._fun:
           self._check_arguments(fun, self._fun[fun])
       for sub in self._sub:
           self._check_arguments(sub, self._sub[sub])
