class Interpretor(object):

    def __init__(self):
        self._globals = { '__builtins__': {
                                            'set': __builtins__['set'],
                                            'list': __builtins__['list'],
                                            'chr': __builtins__['chr'],
                                            'len': __builtins__['len'],
                                            'bool': __builtins__['bool'],
                                            'float': __builtins__['float'],
                                            'int': __builtins__['int'],
                                            'long': __builtins__['long'],
                                            'str': __builtins__['str'],
                                            'False': __builtins__['False'],
                                            'True': __builtins__['True'],
                        } }

    def add_fun(self, name, code):
        tmp_locals = {}
        exec(code, self._globals, tmp_locals)
        self._globals[name] = tmp_locals[name]

    def eval(self, code, known_locals):
        return eval(code, self._globals, known_locals)
