# Copyright (C) 2016, CERN
# This software is distributed under the terms of the GNU General Public
# Licence version 3 (GPL Version 3), copied verbatim in the file "COPYING".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import print_function

from functools import wraps

from parser import Parser

IDENT = 2
REPLACEMENTS = {
    "'('": '(',
    "')'": ')',
    "','": ',',
    "'>='": '>=',
    "'>'": '>',
    "'<='": '<=',
    "'<'": '<',
    "'<>'": '!=',
    "'='": '==',
    "DIV": "/",
    "'/'": "/",
    "'*'": "*",
    "MOD": "%",
    "'+'": "+",
    "'-'": '-',
    "XOR": '^',
    "'&'": '+',
}

FUN_REPLACEMENTS = {
    "UBound": 'len({0}) - 1',
    "Chr": 'chr({0})',
    "Len": 'len({0})'
}

PROC_OK = set(['Array', 'Mid'])
PROC_OK.update(FUN_REPLACEMENTS)

def return_only(func):
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        if kwargs['left'] or not kwargs['ret']:
            self._failed = True
            self.debug('Calling error')
        else:
            return func(self, *args, **kwargs)
    return wrapped

def return_or_add(func):
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        val = func(self, *args, **kwargs)
        if self._failed:
            return
        if kwargs['ret']:
            return val
        self._add_line(val)
    return wrapped

class Translator(object):

    def __init__(self, parser, node, known_variables=[], known_functions=[], ret=False, debug=False):
        self._parser = parser
        self._ident = 0
        self._name = None
        self._expect_args = False
        self._overriden_functions = set()
        self._overriden_functions_array = set()
        self._code = ""
        self._ret = False
        self._failed = False
        self._variables = set(known_variables)
        self._functions = set(known_functions)
        self._debug = debug
        self._handle(node, ret=ret)

    def debug(self, line):
        if self._debug:
            print('Translation error: {0}'.format(line))

    def _add_line(self, line):
        self._code += ' ' * self._ident
        self._code += line
        self._code += '\n'

    def __enter__(self):
        self._ident += IDENT

    def __exit__(self, _ex_type, _ex_value, _tb):
        self._ident -= IDENT

    def _handle(self, node, ret=False, left=False):
        try:
            func = getattr(self, '_handle_{0}'.format(node['name']))
        except AttributeError:
            self._failed = True
            self.debug("Can't handle: " + node['name'])
            return
        return func(node, ret=ret, left=left)

    def __pass(self, node, ret=False, left=False):
        pass

    _handle_endOfStatement = __pass

    def __pass_through(self, node, ret=False, left=False):
        assert(len(node['children']) == 1)
        return self._handle(node['children'][0], ret=ret, left=left)

    _handle_implicitCallStmt_InStmt = __pass_through
    _handle_literal = __pass_through
    _handle_implicitCallStmt_InBlock = __pass_through

    def __run_all(self, node, ret=False, left=False):
        if 'children' in node:
            for child in node['children']:
                if ret or left:
                    self._failed = True
                    return
                self._handle(child)

    _handle_block = __run_all
    _handle_blockStmt = __run_all

    @return_or_add
    def __return(self, node, ret=False, left=False):
        if 'children' in node or 'value' not in node:
            self._failed = True
            return
        return node['value']

    _handle_HEXLITERAL = __return
    _handle_OCTLITERAL = __return
    _handle_DOUBLELITERAL = __return
    _handle_INTEGERLITERAL = __return
    _handle_SHORTLITERAL = __return
    _handle_STRINGLITERAL = __return
    _handle_IDENTIFIER = __return

    @return_only
    def _handle_bool(self, node, ret=False, left=False):
        return str(node['name'] == 'TRUE')

    _handle_TRUE = _handle_bool
    _handle_FALSE = _handle_bool

    @return_only
    def _handle_argList(self, node, ret=False, left=False):
        args = []
        for child in node['children']:
            if child['name'] == 'arg':
                args.append(self._handle(child, ret=True))
            elif child['name'] in ['WS', "'('", "')'", "','"]:
                pass
            else:
                self.debug("argList, can't handle {0}".format(child['name']))
                self._failed = True
        return args

    @return_only
    def _handle_arg(self, node, ret=False, left=False):
        name = None
        type = None
        paramarray = False
        for child in node['children']:
            if child['name'] == 'ambiguousIdentifier':
                name = self._handle(child, ret=True)
            elif child['name'] in ['WS', "BYVAL", "BYREF", "typeHint", "'('", "')'"]:
                pass
            elif child['name'] == 'asTypeClause':
                type = self._handle(child, ret=True)
            elif child['name'] == 'PARAMARRAY':
                paramarray = True
            else:
                self.debug("arg, can't handle {0}".format(child['name']))
                self._failed = True
        if paramarray:
            if type is not None:
                self.debug("arg, PARAMARRAY can only be untyped or Varriant")
                self._failed = True
                return (None, None)
            type = 'list(args)'
        if not name:
            self._failed = True
        return (name, type)

    @return_only
    def _handle_asTypeClause(self, node, ret=False, left=False):
        type = None
        for child in node['children']:
            if child['name'] == 'type':
                type = self._handle(child, ret=True)
            elif child['name'] in ['AS', 'WS']:
                pass
            else:
                self.debug("asTypeClause, can't handle {0}".format(child['name']))
                self._failed = True
        return type

    @return_only
    def _handle_type(self, node, ret=False, left=False):
        type = None
        for child in node['children']:
            if child['name'] == 'baseType':
                type = self._handle(child, ret=True)
            elif child['name'] in ['WS', "'('", "')'"]:
                pass
            else:
                self.debug("type, can't handle {0}".format(child['name']))
                self._failed = True
        return type

    @return_only
    def _handle_baseType(self, node, ret=False, left=False):
        if 'children' not in node or len(node['children']) != 1:
            self._failed = True
            return
        TYPES = {'BOOLEAN': 'bool({0})',
                 'DOUBLE': 'float({0})',
                 'INTEGER': 'int({0})',
                 'LONG': 'long({0})',
                 'STRING': 'str({0})',
                 'VARIANT': '{0}',
        }
        try:
            return TYPES[node['children'][0]['name']]
        except KeyError:
            self._failed = True
            self.debug("baseType, can't handle {0}".format(node['children'][0]['name']))

    @return_or_add
    def _handle_ambiguousKeyword(self, node, ret=False, left=False):
        if 'children' not in node or len(node['children']) != 1:
            self.debug('ambiguousKeyword: invalid number of children')
            self._failed = True
            return
        return self.__return(node['children'][0], ret=ret, left=left)

    @return_or_add
    def __handle_identifier(self, node, ret=False, left=False):
        if 'children' not in node or len(node['children']) != 1:
            self.debug('identifier: non-supported number of children')
            self._failed = True
            return
        return self._handle(node['children'][0], ret=ret, left=left)

    _handle_certainIdentifier = __handle_identifier
    _handle_ambiguousIdentifier = __handle_identifier

    def _handle_proc(self, node, ret=False, left=False):
        name = self._parser.identifier_name(node)
        self._name = name
        self._functions.add(name)
        raw_args = self._parser.xpath(node, ['argList'])
        if raw_args:
            arguments = self._handle(raw_args[0], ret=True)
        else:
            arguments = []
        if self._failed:
            return
        if arguments:
            self._expect_args = True
        self._variables.update(x for (x, y) in arguments)
        types = [y for (x, y) in arguments]
        if 'list(args)' in types:
            if len(types) != 1:
                self.debug("proc, we don't support more than 'PARAMARRAY'")
                self._failed = True
                return
            self._add_line("def {0}(*args):".format(name))
        else:
            self._add_line("def {0}({1}):".format(name, ', '.join(x for (x, y) in arguments)))
        with self:
            for (arg, type) in arguments:
                if type:
                    self._add_line('{0} = {1}'.format(arg, type.format(arg)))
            orig_code = self._code
            self._code = ""
            blocks = self._parser.xpath(node, ['block'])
            if not blocks:
                self._add_line('pass')
            else:
                for block in blocks:
                    self._handle(block)
                if self._ret:
                    self._add_line('return {0}'.format(name))
            proc_code = self._code
            self._code = orig_code
            for var in self._overriden_functions:
                self._add_line('{0} = ""'.format(var))
            for arr in self._overriden_functions_array:
                self._add_line('{0} = []'.format(var))
            self._code += proc_code


    _handle_subStmt = _handle_proc
    _handle_functionStmt = _handle_proc

    def _handle_letStmt(self, node, ret=False, left=False):
        if ret or left:
            self._failed = True
            return
        variable = value = operation = None
        for child in node['children']:
            if child['name'] == 'implicitCallStmt_InStmt':
                variable = self._handle(child, ret=True, left=True)
            elif child['name'] in ["'='", "'+='", "'-='"]:
                operation = child['value']
            elif child['name'] == 'valueStmt':
                value = self._handle(child, ret=True)
            elif child['name'] in ['WS', 'SET', 'LET']:
                pass
            else:
                self.debug("letStmt, can't handle {0}".format(child['name']))
                self._failed = True
        if self._failed:
            return
        self._add_line(' '.join([variable, operation, value]))
        if variable == self._name:
            self._overriden_functions.add(variable)
            self._ret = True

    _handle_setStmt = _handle_letStmt

    @return_or_add
    def _handle_valueStmt(self, node, ret=False, left=False):
        values = []
        for child in node['children']:
            if child['name'] in ['valueStmt', 'literal', 'implicitCallStmt_InStmt']:
                values.append(self._handle(child, ret=True, left=left))
            elif child['name'] in REPLACEMENTS:
                values.append(REPLACEMENTS[child['name']])
            elif child['name'] == "WS":
                values.append(' ')
            else:
                self.debug("ValueStmt, can't handle {0}".format(child['name']))
                self._failed = True
        if self._failed:
            return
        return ''.join(values)

    @return_or_add
    def __handle_procedure_call(self, name, arguments, ret=False, left=False):
        if name in FUN_REPLACEMENTS:
            code = FUN_REPLACEMENTS[name].format(arguments)
        elif left:
            self._functions.discard(name)
            self._variables.add(name)
            if arguments:
                self._overriden_functions_array.add(name)
                code = '{0}[{1}]'.format(name, arguments)
            else:
                self._overriden_functions.add(name)
                code = name
        elif name in self._functions:
            if name == self._name and self._expect_args and not arguments:
                self._functions.discard(name)
                self._variables.add(name)
                self._overriden_functions.add(name)
                code = name
            else:
                code = '{0}({1})'.format(name, arguments)
        elif name in self._variables:
            if arguments:
                code = '{0}[{1}]'.format(name, arguments)
            else:
                code = name
        elif name == 'Array':
            if left:
                self._failed = True
                return
            code = '[{0}]'.format(arguments)
        elif name == 'Mid':
            if left:
                self._failed = True
                return
            args = arguments.split(',')
            if len(args) == 3:
                code = '{0}[({1}-1):({1}-1+{2})]'.format(args[0], args[1], args[2])
            elif len(args) == 2:
                code = '{0}[({1}-1):]'.format(args[0], args[1])
            else:
                self._failed = True
                return
        elif arguments:
            self.debug("Procedure_call: can't handle {0}".format(name))
            self._failed = True
            return
        else:
            self._failed = True
            return
        return code

    def _handle_iCS_S_VariableOrProcedureCall(self, node, ret=False, left=False):
        name = None
        subscript = ""
        for child in node['children']:
            if child['name'] == 'ambiguousIdentifier':
                name = self._handle(child, ret=True)
            elif child['name'] == 'subscripts':
                subscript = self._handle(child, ret=True)
            elif child['name'] in ["'('", "')'"]:
                pass
            else:
                self.debug("iCS_S_VariableOrProcedureCall, can't handle {0}".format(child['name']))
                self._failed = True
        if self._failed or not name:
            return
        return self.__handle_procedure_call(name, subscript, ret=ret, left=left)

    def _handle_iCS_B_ProcedureCall(self, node, ret=False, left=False):
        name = None
        subscript = []
        for child in node['children']:
            if child['name'] == 'certainIdentifier':
                name = self._handle(child, ret=True)
            elif child['name'] in ['subscripts', 'argsCall']:
                subscript.append(self._handle(child, ret=True))
            elif child['name'] in ["'('", "')'", 'WS']:
                pass
            else:
                self.debug("iCS_S_VariableOrProcedureCall, can't handle {0}".format(child['name']))
                self._failed = True
        if self._failed or not name:
            return
        return self.__handle_procedure_call(name, ', '.join(subscript), ret=ret, left=left)

    def _handle_iCS_S_ProcedureOrArrayCall(self, node, ret=False, left=False):
        name = None
        subscript = []
        for child in node['children']:
            if child['name'] == 'ambiguousIdentifier':
                name = self._handle(child, ret=True)
            elif child['name'] in ['subscripts', 'argsCall']:
                subscript.append(self._handle(child, ret=True))
            elif child['name'] in ["'('", "')'", 'WS']:
                pass
            else:
                self.debug("iCS_S_ProcedureOrArrayCall, can't handle {0}".format(child['name']))
                self._failed = True
        if self._failed or not name:
            return
        return self.__handle_procedure_call(name, ', '.join(subscript), ret=ret, left=left)

    def _handle_whileWendStmt(self, node, ret=False, left=False):
        if ret or left:
            self._failed = True
            return
        loop = 'True'
        blocks = []
        for child in node['children']:
            if child['name'] == 'valueStmt':
                loop = self._handle(child, ret=True)
            elif child['name'] == 'block':
                blocks.append(child)
            elif child['name'] in ['WHILE', 'WS', 'endOfStatement', 'WEND']:
                pass
            else:
                self.debug("whileWendStmt, can't handle {0}".format(child['name']))
                self._failed = True
        if self._failed:
            return
        self._add_line('while ({0}):'.format(loop))
        with self:
            for block in blocks:
                self._handle(block)

    @return_or_add
    def _handle_subscripts(self, node, ret=False, left=False):
        subs = []
        for child in node['children']:
            if child['name'] == 'subscript':
                subs.append(self._handle(child, ret=True, left=left))
            elif child['name'] == "','":
                subs.append(',')
            elif child['name'] == 'WS':
                pass
            else:
                self.debug("subscripts, can't handle {0}".format(child['name']))
                self._failed = True
        if self._failed:
            return
        return ''.join(subs)

    def _handle_subscript(self, node, ret=False, left=False):
        if len(node['children']) == 1:
            return self._handle(node['children'][0], ret=ret, left=left)
        self.debug("subscript, can't handle 'TO': {0}".format(str(node)))
        self._failed = True

    @return_or_add
    def _handle_argsCall(self, node, ret=False, left=False):
        args = []
        for child in node['children']:
            if child['name'] == 'argCall':
                args.append(self._handle(child, ret=True, left=left))
            elif child['name'] in ['WS', "','", "';'"]:
                pass
            else:
                self.debug("_handle_argsCall, can't handle {0}".format(child['name']))
                self._failed = True
        if self._failed:
            return
        return ', '.join(args)

    @return_or_add
    def _handle_argCall(self, node, ret=False, left=False):
        val = None
        for child in node['children']:
            if child['name'] == 'valueStmt':
                if val:
                    self._failed = True
                    return
                val = self._handle(child, ret=True, left=left)
            elif child['name'] == 'WS':
                pass
            else:
                self.debug("argCall, can't handle {0}".format(child['name']))
                self._failed = True
        if self._failed or val is None:
            self._failed = True
            return
        return val

    def _handle_variableStmt(self, node, ret=False, left=False):
        if ret or left:
            self._failed = True
            return
        for child in self._parser.xpath(node, ['variableListStmt', 'variableSubStmt']):
            self._handle(child, ret=False, left=False)

    def _handle_variableSubStmt(self, node, ret=False, left=False):
        if ret or left:
            self._failed = True
            return
        for child in node['children']:
            if child['name'] == 'ambiguousIdentifier':
                var = self._handle(child, ret=True)
                self._variables.add(var)
            elif child['name'] in ['WS', "'('", "')'", 'typeHint', 'asTypeClause']:
                pass
            else:
                self.debug("variableSubStmt, can't handle {0}".format(child['name']))
                self._failed = True

    def _handle_doLoopStmt(self, node, ret=False, left=False):
        if ret or left:
            self._failed = True
            return
        dowhile = None
        for child in node['children']:
            if child['name'] in ['DO', 'WS', 'endOfStatement']:
                pass
            elif child['name'] in ['WHILE', 'UNTIL']:
                dowhile = child['name']
                break
            elif child['name'] == 'block':
                dowhile = True
                break
            else:
                self.debug("doLoopStmt, can't handle {0} early".format(child['name']))
                self._failed = True
                return
        if dowhile is None:
            self.debug("doLoopStmt, nothing?")
            self._failed = True
            return
        valueStmts = self._parser.xpath(node, ['valueStmt'])
        if not valueStmts or len(valueStmts) != 1:
            self.debug("doLoopStmt, bad valueStmt: {0}".format(valueStmts))
            self._failed = True
            return
        condition = self._handle(valueStmts[0], ret=True)
        if dowhile == 'UNTIL':
            condition = 'not ({0})'.format(condition)
        if self._failed:
            return
        if dowhile is False:
            self._add_line('while True:')
        else:
            self._add_line('while ({0}):'.format(condition))
        with self:
            for block in self._parser.xpath(node, ['block']):
                self._handle(block)
            if self._failed:
                return
            if dowhile is False:
                self._add_line('if({0}):'.format(condition))
                with self:
                    self._add_line('break')
        if self._failed:
            return


    def parsed(self):
        return not self._failed

    def __str__(self):
        return self._code
