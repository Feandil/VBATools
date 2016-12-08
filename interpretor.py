# Copyright (C) 2016, CERN
# This software is distributed under the terms of the GNU General Public
# Licence version 3 (GPL Version 3), copied verbatim in the file "COPYING".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import print_function


UNKNOWN_METHOD_CALL='''
def method_call(obj, meth, args):
    global Error_code, Error_source, Error_pass, Error_description
    if obj == 'Application' and meth == 'CleanString' and len(args) == 1:
        return clean_string(args[0])
    if obj != 'Err':
        raise(NotImplementedError("Methods {1} of object {0} not implemented".format(obj, meth)))
    if not Error_pass:
        raise(NotImplementedError("Cannot handle errors if errors were not disabled"))
    if meth == 'Raise':
        isdict = False
        isval = False
        for arg in args:
          if isinstance(arg, dict):
              isdict = True
          else:
              isval = True
        if isdict and isval:
            raise(NotImplementedError("Err.Raise can't support both vals and dicts"))
        if isval:
            Error_code = args[0]
            if len(args) > 1:
                Error_source = args[1]
            if len(args) > 2:
                Error_description = args[2]
            if len(args) > 3:
                raise(NotImplementedError("Err.Raise does not support HelpFile/HelpContext"))
        else:
            content = {}
            for arg in args:
                content.update(arg)
            if 'Number' not in content:
                raise(NotImplementedError("Err.Raise needs a Number"))
            Error_code = content['Number']
            if 'Source' in content:
                Error_source = content['Source']
            if 'Description' in content:
                Error_description = content['Description']
        return
    if meth == 'Number':
        if Error_code is False:
            raise(NotImplementedError("Default error handling not implemented"))
        return Error_code
    if meth == 'Source':
        if Error_source is False:
            raise(NotImplementedError("Default error handling not implemented"))
        return Error_source
    if meth == 'Description':
        if Error_description is False:
            raise(NotImplementedError("Default error handling not implemented"))
        return Error_description
    raise(NotImplementedError("Methods '{1}' of object '{0}' not implemented for {2} arguments".format(obj, meth, len(args))))
'''

DISABLE_ERRORS='''
def disable_errors():
    global Error_pass
    Error_pass = True
'''

CLEAN_STRING='''
def clean_string(raw):
    ret = ""
    for char in raw:
        o = ord(char)
        if o == 7:
            if len(ret) and ret[-1] == chr(9):
                ret += chr(9)
            else:
                continue
        elif o == 10:
            if len(ret) and ret[-1] == chr(13):
                ret += chr(9)
            else:
                continue
        elif o == 13:
            ret += char
        elif o in [31, 172, 182] or o <= 29:
            continue
        elif o in [160, 176, 182]:
            ret += ' '
        else:
            ret += char
    return ret
'''

class Interpretor(object):

    def __init__(self):
        self._globals = { '__builtins__': {
                                            'isinstance': __builtins__['isinstance'],
                                            'set': __builtins__['set'],
                                            'list': __builtins__['list'],
                                            'dict': __builtins__['dict'],
                                            'ord': __builtins__['ord'],
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
                        'Error_description': False,
        }
        self.add_fun('disable_errors', DISABLE_ERRORS)
        self.add_fun('method_call', UNKNOWN_METHOD_CALL)
        self.add_fun('clean_string', CLEAN_STRING)

    def _reset_errors(self):
        self._globals['Error_pass'] = False
        self._globals['Error_code'] = False
        self._globals['Error_source'] = False
        self._globals['Error_description'] = False


    def add_fun(self, name, code):
        self._reset_errors()
        tmp_locals = {}
        exec(code, self._globals, tmp_locals)
        self._globals[name] = tmp_locals[name]

    def eval(self, code, known_locals):
        self._reset_errors()
        return eval(code, self._globals, known_locals)
