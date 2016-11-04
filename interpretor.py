# Copyright (C) 2016, CERN
# This software is distributed under the terms of the GNU General Public
# Licence version 3 (GPL Version 3), copied verbatim in the file "COPYING".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import print_function


UNKNOWN_METHOD_CALL='''
def method_call(obj, meth, args):
    global Error_code, Error_source, Error_pass
    if obj != 'Err':
        raise(NotImplementedError("Methods {1} of object {0} not implemented".format(obj, meth)))
    if not Error_pass:
        raise(NotImplementedError("Cannot handle errors if errors were not disabled"))
    if meth == 'Raise' and len(args) == 2:
        Error_code = args[0]
        Error_source = args[1]
        return
    if Error_code is False or Error_source is False:
        raise(NotImplementedError("Default error handling not implemented"))
    if meth == 'Number':
        return Error_code
    if meth == 'Source':
        return Error_source
    raise(NotImplementedError("Methods '{1}' of object '{0}' not implemented for {2} arguments".format(obj, meth, len(args))))
'''

DISABLE_ERRORS='''
def disable_errors():
    global Error_pass
    Error_pass = True
'''

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
                                            'NotImplementedError': __builtins__['NotImplementedError'],
                        },
                        'Error_pass': False,
                        'Error_code': False,
                        'Error_source': False,
        }
        self.add_fun('disable_errors', DISABLE_ERRORS)
        self.add_fun('method_call', UNKNOWN_METHOD_CALL)

    def _reset_errors(self):
        self._globals['Error_code'] = False
        self._globals['Error_source'] = False

    def add_fun(self, name, code):
        self._reset_errors()
        tmp_locals = {}
        exec(code, self._globals, tmp_locals)
        self._globals[name] = tmp_locals[name]

    def eval(self, code, known_locals):
        self._reset_errors()
        return eval(code, self._globals, known_locals)
