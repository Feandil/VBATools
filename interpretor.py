OBJECT_CALL = '''
def object_call(x, y):
  try:
    return x(y)
  except TypeError:
    return x[y]
'''

OBJECT_ACCESS = '''
def object_access(x):
  try:
    return x()
  except TypeError:
    return x
'''

class Interpretor(object):

    def __init__(self):
        self._globals = { '__builtins__': {
                                            'set': __builtins__['set'],
                                            'chr': __builtins__['chr'],
                                            'len': __builtins__['len'],
                        } }
        self.add_fun('object_call', OBJECT_CALL)
        self.add_fun('object_access', OBJECT_ACCESS)

    def add_fun(self, name, code):
        tmp_locals = {}
        exec(code, self._globals, tmp_locals)
        self._globals[name] = tmp_locals[name]

    def eval(self, code, locals):
        return eval(code, self._globals, locals)
