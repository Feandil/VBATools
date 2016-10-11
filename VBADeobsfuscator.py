from oletools.olevba import VBA_Parser
from antlr4 import *
from parser import VBA
from extractor import Extractor

class VBADeobsfuscator(object):

    def __init__(self, file):
        vbaparser = VBA_Parser(file)
        self._raw = [code for (_f, _p, _name, code) in vbaparser.extract_macros()]
        self._content = []
        self._var = {}
        self._fun = {}
        self._sub = {}


    def parse(self):
        for vba in self._raw:
            content = VBA.parse(vba)
            self._content.append(content)
            self._var.update(VBA.extract_var(content))
            self._fun.update(VBA.extract_fun(content))
            self._sub.update(VBA.extract_sub(content))

    @staticmethod
    def _check_arguments(name, fun):
      raw_arguments = VBA.xpath(fun, VBA.ARG_XPATH)
      text_args = [e.getText() for e in raw_arguments]
      blocks = VBA.xpath(fun, ['BlockContext'])
      assert(len(blocks) == 1)
      raw_identifiers = set(VBA.findall(blocks[0], 'IdentifierValueContext'))
      text_ids = [e.getText() for e in raw_identifiers]
      for arg in text_args:
          if arg not in text_ids:
              print('{0}: {1} not used'.format(name, arg))

    def check_funsub(self):
       for fun in self._fun:
           self._check_arguments(fun, self._fun[fun])
       for sub in self._sub:
           self._check_arguments(sub, self._sub[sub])

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print('Expected 1 argument: file to analyse')
        sys.exit(-1)
    d = VBADeobsfuscator(sys.argv[1])
    d.parse()
