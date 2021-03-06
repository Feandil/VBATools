# Copyright (C) 2016, CERN
# This software is distributed under the terms of the GNU General Public
# Licence version 3 (GPL Version 3), copied verbatim in the file "COPYING".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import print_function

from functools import wraps
import re

from parser import Parser

IDENT = 2
VALUEOPERATION = {
    "'>='": [(2, '{0} >= {1}'),],
    "'>'": [(2, '{0} > {1}'),],
    "'<='": [(2, '{0} <= {1}'),],
    "'<'": [(2, '{0} < {1}'),],
    "'<>'": [(2, '{0} != {1}'),],
    "'='": [(2, '{0} == {1}'),],
    "DIV": [(2, '{0} / {1}'),],
    "'/'": [(2, '{0} / {1}'),],
    "'*'": [(2, '{0} * {1}'),],
    "MOD": [(2, '{0} % {1}'),],
    "'+'": [(2, '{0} + {1}'), (1, '+{0}')],
    "'-'": [(2, '{0} - {1}'), (1, '-{0}')],
    "XOR": [(2, 'int({0}) ^ int({1})'),],
    "'&'": [(2, 'str({0}) + str({1})'),],
    "':='": [],
}

FUN_REPLACEMENTS = {
    "UBound": [(1, 'len({0}) - 1')],
    "Chr": [(1, 'chr({0})')],
    "Len": [(1, 'len({0})')],
    "Mid": [(3, '(lambda x: {0}[(x-1):(x-1+{2})])({1})'), (2, '{0}[({1}-1):]')],
    "Left": [(2, '{0}[:{1}]')],
    "Right": [(2, '{0}[-{1}:]')],
    "Sgn": [(1, '(lambda x: (0 if x == 0 else (1 if x > 0 else -1)))({0})')],
    "Split": [(2, 'str({0}).split(str({1}))')],
}

KEYWORDS_OK = ['Err', 'Source', 'Number', 'Description', 'Raise', 'Application', 'CleanString', 'Module0', 'Module1', 'Module2', 'Module3', 'vbLowerCase', 'vbUpperCase']

PROC_OK = set(['Array'])
PROC_OK.update(FUN_REPLACEMENTS)
PROC_OK.update(KEYWORDS_OK)

def return_only(func):
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        if (('left' in kwargs and kwargs ['left']) or
                ('ret' not in kwargs and not kwargs['ret'])):
            self._failed = True
            self.debug('Calling error (return_only: {0} {1}'.format(str(kwargs['left']), str(kwargs['ret'])))
        else:
            return func(self, *args, **kwargs)
    return wrapped

def return_or_block(func):
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        val = func(self, *args, **kwargs)
        if self._failed:
            if 'raw' in kwargs and kwargs['raw']:
                return (None, None)
            if 'formatted' in kwargs and not kwargs['formatted']:
                return []
            return
        if 'ret' in kwargs and kwargs['ret']:
            return val
        self._add_line(val)
    return wrapped

def block_only(func):
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        if (('left' in kwargs and kwargs ['left']) or
                ('ret' in kwargs and kwargs['ret'])):
            self._failed = True
            self.debug('Calling error (block_only: {0} {1}'.format(str(kwargs['left']), str(kwargs['ret'])))
        else:
            func(self, *args, **kwargs)
    return wrapped


class Translator(object):

    def __init__(self, node, known_variables=[], known_functions=[], ret=False, debug=False):
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

    def _handle(self, node, **kwargs):
        try:
            func = getattr(self, '_handle_{0}'.format(node['name']))
        except AttributeError:
            self._failed = True
            self.debug("Can't handle: " + node['name'])
            return
        return func(node, **kwargs)

    def __pass(self, node, ret=False, left=False):
        pass

    _handle_endOfStatement = __pass

    def __pass_through(self, node, **kwargs):
        assert(len(node['children']) == 1)
        return self._handle(node['children'][0], **kwargs)

    _handle_implicitCallStmt_InStmt = __pass_through
    _handle_literal = __pass_through
    _handle_implicitCallStmt_InBlock = __pass_through
    _handle_ifConditionStmt = __pass_through

    @block_only
    def __run_all(self, node, ret=False, left=False):
        if 'children' in node:
            for child in node['children']:
                self._handle(child)

    _handle_block = __run_all
    _handle_blockStmt = __run_all

    @return_or_block
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
                 'BYTE': '(lambda x: ((1/0) if int(x) < 0 else ((1/0) if int(x) > 255 else int(x))))({0})',
        }
        try:
            return TYPES[node['children'][0]['name']]
        except KeyError:
            self._failed = True
            self.debug("baseType, can't handle {0}".format(node['children'][0]['name']))

    @return_or_block
    def _handle_ambiguousKeyword(self, node, ret=False, left=False):
        if 'children' not in node or len(node['children']) != 1:
            self.debug('ambiguousKeyword: invalid number of children')
            self._failed = True
            return
        return self.__return(node['children'][0], ret=ret, left=left)

    @return_or_block
    def __handle_identifier(self, node, ret=False, left=False):
        if 'children' not in node or len(node['children']) != 1:
            self.debug('identifier: non-supported number of children')
            self._failed = True
            return
        return self._handle(node['children'][0], ret=ret, left=left)

    _handle_certainIdentifier = __handle_identifier
    _handle_ambiguousIdentifier = __handle_identifier

    @block_only
    def _handle_proc(self, node, ret=False, left=False):
        name = Parser.identifier_name(node)
        self._name = name
        self._functions.add(name)
        raw_args = Parser.xpath(node, ['argList'])
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
            blocks = Parser.xpath(node, ['block'])
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

    @block_only
    def _handle_letStmt(self, node, ret=False, left=False):
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

    @block_only
    def _handle_constSubStmt(self, node, ret=False, left=False):
        variable = value = type = None
        for child in node['children']:
            if child['name'] == 'ambiguousIdentifier':
                variable = self._handle(child, ret=True, left=True)
            elif child['name'] in ["'='", "WS"]:
                pass
            elif child['name'] == 'asTypeClause':
                type = self._handle(child, ret=True)
            elif child['name'] == 'valueStmt':
                value = self._handle(child, ret=True)
            else:
                self.debug("constSubStmt, can't handle {0}".format(child['name']))
                self._failed = True
        if variable is None or value is None:
            self._failed = True
        if self._failed:
            return
        if type is not None:
            self._add_line(' = '.join([variable, type.format(value)]))
        else:
            self._add_line(' = '.join([variable, value]))
        if variable == self._name:
            self._overriden_functions.add(variable)
            self._ret = True


    @block_only
    def _handle_constStmt(self, node, ret=False, left=False):
        for child in node['children']:
            if child['name'] == 'constSubStmt':
                self._handle(child, ret=ret, left=left)
            elif child['name'] in ['visibility', 'WS', 'CONST', 'WS']:
                pass
            else:
                self.debug("constStmt, can't handle {0}".format(child['name']))
                self._failed = True

    @return_or_block
    def _handle_valueStmt(self, node, ret=False, left=False):
        values = []
        operation = None
        parenthesis = False
        for child in node['children']:
            if child['name'] in ['valueStmt', 'literal', 'implicitCallStmt_InStmt']:
                values.append(self._handle(child, ret=True, left=left))
            elif child['name'] in VALUEOPERATION:
                operation = child['name']
            elif child['name'] == "WS":
                pass
            elif child['name'] in ["'('", "')'", "','"]:
                parenthesis = True
            else:
                self.debug("ValueStmt, can't handle {0}".format(child['name']))
                self._failed = True
        if self._failed:
            return
        if operation is None:
            if parenthesis:
                return '({0})'.format(', '.join(values))
            elif len(values) == 1:
                return values[0]
            else:
                self.debug("ValueStmt, unsuported number of values without an operation: {0}".format(len(values)))
                self._failed = True
        elif operation == "':='":
            if len(values) == 2 and values[0].startswith("'") and values[0].endswith("'"):
                return '{{{0}: {1}}}'.format(values[0], values[1])
            else:
                self.debug("ValueStmt, unsuported assignmend")
                self._failed = True
        else:
            for (length, format) in VALUEOPERATION[operation]:
                if len(values) == length:
                    return format.format(*values)
            self.debug('Wrong number of arguments for {0} ({1}): {2}'.format(operation, len(values), values))
            self._failed = True

    def __validate_keywork(self, name):
        if name in self._functions:
            if name == self._name and self._expect_args:
                self._functions.discard(name)
                self._variables.add(name)
                self._overriden_functions.add(name)
                return name
            return '{0}()'.format(name)
        elif name in self._variables:
            return name
        elif name in KEYWORDS_OK:
            return "'{0}'".format(name)
        else:
            self.debug('Unknown keyword "{0}"'.format(name))
            self._failed = True

    def __handle_procedure_call(self, name, raw_arguments, left=False, raw=False, formatted=True):
        if self._failed or not name:
            self._failed = True
            return (None, None)
        if formatted:
            arguments = ', '.join(raw_arguments)
        else:
            arguments = raw_arguments
        if raw:
            return (name, arguments)
        if name in FUN_REPLACEMENTS and arguments:
            for (length, format) in FUN_REPLACEMENTS[name]:
                if len(raw_arguments) == length:
                    return format.format(*raw_arguments)
            self.debug('Wrong number of arguments for {0} ({1}): {2}'.format(name, len(raw_arguments), raw_arguments))
            self._failed = True
        elif left:
            self._functions.discard(name)
            self._variables.add(name)
            if arguments:
                self._overriden_functions_array.add(name)
                return '{0}[{1}]'.format(name, arguments)
            else:
                self._overriden_functions.add(name)
                return name
        elif arguments:
            if name in self._variables:
                return '{0}[{1}]'.format(name, arguments)
            elif left:
                self.debug('Function ({0}) cannot be used in a left statement'.format(name))
                self._failed = True
            elif name == 'Array':
                return '[{0}]'.format(arguments)
            elif name in self._functions:
                return '{0}({1})'.format(name, arguments)
            elif name == 'StrConv':
                args = arguments.split(',')
                if len(args) != 2:
                    self.debug("Procedure_call: wrong number of arguments for StrConv: {0}".format(len(args)))
                    self._failed = True
                    return
                if args[1] == "'vbLowerCase'":
                    return 'str({0}).lower()'.format(args[0])
                elif args[1] == "'vbUpperCase'":
                    return 'str({0}).upper()'.format(args[0])
                else:
                    self.debug("Procedure_call: StrConv doesn't support {0}".format(args[1]))
                    self._failed = True
                    return
            else:
                self.debug("Procedure_call: can't handle {0}".format(name))
                self._failed = True
                return
        else:
            return self.__validate_keywork(name)

    @return_or_block
    def _handle_iCS_S_VariableOrProcedureCall(self, node, ret=False, left=False, raw=False, formatted=True):
        name = None
        subscript = []
        for child in node['children']:
            if child['name'] == 'ambiguousIdentifier':
                name = self._handle(child, ret=True)
            elif child['name'] == 'subscripts':
                subscript = self._handle(child, ret=True, formatted=False)
            elif child['name'] in ["'('", "')'"]:
                pass
            else:
                self.debug("iCS_S_VariableOrProcedureCall, can't handle {0}".format(child['name']))
                self._failed = True
        return self.__handle_procedure_call(name, subscript, left=left, raw=raw, formatted=formatted)

    @return_or_block
    def _handle_iCS_B_ProcedureCall(self, node, ret=False, left=False, raw=False, formatted=True):
        name = None
        subscript = []
        for child in node['children']:
            if child['name'] == 'certainIdentifier':
                name = self._handle(child, ret=True)
            elif child['name'] in ['subscripts', 'argsCall']:
                subscript.extend(self._handle(child, ret=True, formatted=False))
            elif child['name'] in ["'('", "')'", 'WS']:
                pass
            else:
                self.debug("iCS_S_VariableOrProcedureCall, can't handle {0}".format(child['name']))
                self._failed = True
        return self.__handle_procedure_call(name, subscript, left=left, raw=raw, formatted=formatted)

    @return_or_block
    def _handle_iCS_S_ProcedureOrArrayCall(self, node, ret=False, left=False, raw=False, formatted=True):
        name = None
        subscript = []
        for child in node['children']:
            if child['name'] == 'ambiguousIdentifier':
                name = self._handle(child, ret=True)
            elif child['name'] in ['subscripts', 'argsCall']:
                subscript.extend(self._handle(child, ret=True, formatted=False))
            elif child['name'] in ["'('", "')'", 'WS']:
                pass
            else:
                self.debug("iCS_S_ProcedureOrArrayCall, can't handle {0}".format(child['name']))
                self._failed = True
        return self.__handle_procedure_call(name, subscript, left=left, raw=raw, formatted=formatted)

    @return_only
    def _handle_iCS_S_MemberCall(self, node, ret=False, left=False, raw=False, formatted=True):
        res = (None, None)
        for child in node['children']:
            if child['name'] in ['iCS_S_VariableOrProcedureCall', 'iCS_S_ProcedureOrArrayCall']:
                res = self._handle(child, ret=True, left=left, raw=True, formatted=formatted)
            elif child['name'] == "'.'":
                pass
            else:
                self.debug("iCS_S_MemberCall, can't handle {0}".format(child['name']))
                self._failed = True
        if res is None or res[0] is None:
            self._failed = True
            return (None, None)
        return res

    def __handle_membercall(self, name, member, arguments):
        if not name:
             self.debug("iCS_S_MembersCall, empty name".format(name))
             self._failed = True
             return
        name = self.__validate_keywork(name)
        if not member:
             self.debug("iCS_S_MembersCall, empty member".format(member))
             self._failed = True
             return
        member = self.__validate_keywork(member)
        if self._failed:
             return
        if re.match("'Module[0-9]*'", name):
            if member.endswith('()'):
                member = member.rstrip('()')
            return self.__handle_procedure_call(member, arguments)
        if arguments:
            return "method_call({0}, {1}, [{2}])".format(name, member, ', '.join(arguments))
        else:
            return "method_call({0}, {1}, [])".format(name, member)

    @return_or_block
    def _handle_iCS_S_MembersCall(self, node, ret=False, left=False):
        name = None
        member = None
        arguments = []
        for child in node['children']:
            if child['name'] in ['iCS_S_VariableOrProcedureCall', 'iCS_S_ProcedureOrArrayCall']:
                if name:
                    self.debug("iCS_S_MembersCall, dupplicate name")
                    self._failed = True
                    return
                (name, empty) = self._handle(child, ret=True, left=left, raw=True)
                if empty:
                    self.debug("iCS_S_MembersCall, arguments present for name: {0}".format(empty))
            elif child['name'] == 'iCS_S_MemberCall':
                if member:
                    self.debug("iCS_S_MembersCall, dupplicate member")
                    self._failed = True
                    return
                (member, arguments) = self._handle(child, ret=True, left=left, formatted=False)
            elif child['name'] == 'subscripts':
                if arguments:
                    self.debug("iCS_S_MembersCall, dupplicate member")
                    self._failed = True
                    return
                arguments = self._handle(child, ret=True, formatted=False)
            elif child['name'] in ["'('", "')'", 'WS']:
                pass
            else:
                self.debug("iCS_S_MembersCall, can't handle {0}".format(child['name']))
                self._failed = True
        return self.__handle_membercall(name, member, arguments)

    @return_or_block
    def _handle_iCS_B_MemberProcedureCall(self, node, ret=False, left=False):
        name = None
        member = None
        arguments = []
        for child in node['children']:
            if child['name'] == 'implicitCallStmt_InStmt':
                (name, empty) = self._handle(child, ret=True, left=left, raw=True)
                if empty:
                    self.debug("iCS_B_MemberProcedureCall, arguments present for name: {0}".format(empty))
            elif child['name'] == 'ambiguousIdentifier':
                member = self._handle(child, ret=True, left=left)
            elif child['name'] in ['subscripts', 'argsCall']:
                arguments.extend(self._handle(child, ret=True, formatted=False))
        if self._failed:
            return (None, None)
        return self.__handle_membercall(name, member, arguments)

    @block_only
    def _handle_whileWendStmt(self, node, ret=False, left=False):
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

    @return_or_block
    def _handle_subscripts(self, node, ret=False, left=False, formatted=True):
        subs = []
        for child in node['children']:
            if child['name'] == 'subscript':
                subs.append(self._handle(child, ret=True, left=left))
            elif child['name'] == "','":
                if formatted:
                    subs.append(',')
            elif child['name'] == 'WS':
                pass
            else:
                self.debug("subscripts, can't handle {0}".format(child['name']))
                self._failed = True
        if self._failed:
            return
        if not formatted:
            return subs
        return ''.join(subs)

    @return_only
    def _handle_subscript(self, node, ret=False, left=False):
        if len(node['children']) == 1:
            return self._handle(node['children'][0], ret=ret, left=left)
        self.debug("subscript, can't handle 'TO': {0}".format(str(node)))
        self._failed = True

    @return_or_block
    def _handle_argsCall(self, node, ret=False, left=False, formatted=True):
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
        if not formatted:
            return args
        return ', '.join(args)

    @return_or_block
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

    @block_only
    def _handle_variableStmt(self, node, ret=False, left=False):
        for child in Parser.xpath(node, ['variableListStmt', 'variableSubStmt']):
            self._handle(child, ret=False, left=False)

    @block_only
    def _handle_variableSubStmt(self, node, ret=False, left=False):
        for child in node['children']:
            if child['name'] == 'ambiguousIdentifier':
                var = self._handle(child, ret=True)
                self._variables.add(var)
            elif child['name'] in ['WS', "'('", "')'", 'typeHint', 'asTypeClause']:
                pass
            else:
                self.debug("variableSubStmt, can't handle {0}".format(child['name']))
                self._failed = True

    @block_only
    def _handle_doLoopStmt(self, node, ret=False, left=False):
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
        valueStmts = Parser.xpath(node, ['valueStmt'])
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
            for block in Parser.xpath(node, ['block']):
                self._handle(block)
            if self._failed:
                return
            if dowhile is False:
                self._add_line('if({0}):'.format(condition))
                with self:
                    self._add_line('break')
        if self._failed:
            return

    @block_only
    def _handle_onErrorStmt(self, node, ret=False, left=False):
        for child in node['children']:
            if child['name'] in ['ON_ERROR', 'WS', 'RESUME', 'NEXT']:
                pass
            else:
                self.debug("onErrorStmt, can't handle {0}".format(child['name']))
                self._failed = True
        if not self._failed:
            self._add_line('disable_errors()')

    @block_only
    def _handle_ifElseIfBlockStmt(self, node, ret=False, left=False):
        condition = None
        position = 0
        for (pos, child) in enumerate(node['children']):
            if child['name'] in ['ELSEIF', 'WS']:
                pass
            elif child['name'] == 'ifConditionStmt':
                condition = self._handle(child, ret = True)
                position = pos
                break
            else:
                self.debug("ifElseIfBlockStmt, can't handle {0} early".format(child['name']))
                self._failed = True
        if self._failed:
             return
        self._add_line('elif({0}):'.format(condition))
        with self:
            for child in node['children'][position:]:
                if child['name'] in ['THEN', 'WS', 'endOfStatement']:
                    pass
                elif child['name'] == 'block':
                    self._handle(child)
                else:
                    self.debug("ifElseIfBlockStmt, can't handle {0} late".format(child['name']))
                    self._failed = True

    def __handle_ifStmt(self, node, operator):
        condition = None
        position = 0
        for (pos, child) in enumerate(node['children']):
            if child['name'] in ['IF', 'ELSEIF', 'WS']:
                pass
            elif child['name'] == 'ifConditionStmt':
                condition = self._handle(child, ret = True)
                position = pos + 1
                break
            else:
                self.debug("ifElseIfBlockStmt, can't handle {0} early".format(child['name']))
                self._failed = True
        if self._failed:
             return
        self._add_line('{0} ({1}):'.format(operator, condition))
        with self:
            for child in node['children'][position:]:
                if child['name'] in ['THEN', 'WS', 'endOfStatement']:
                    pass
                elif child['name'] == 'block':
                    self._handle(child)
                else:
                    self.debug("ifElseIfBlockStmt, can't handle {0} late".format(child['name']))
                    self._failed = True

    @block_only
    def _handle_ifBlockStmt(self, node, ret=False, left=False):
        self.__handle_ifStmt(node, 'if')

    @block_only
    def _handle_ifElseIfBlockStmt(self, node, ret=False, left=False):
        self.__handle_ifStmt(node, 'elseif')

    @block_only
    def _handle_ifElseBlockStmt(self, node, ret=False, left=False):
        self._add_line('else:')
        with self:
            for child in node['children']:
                if child['name'] in ['ELSE', 'WS']:
                    pass
                elif child['name'] == 'block':
                    self._handle(child)
                else:
                    self.debug("ifElseBlockStmt, can't handle {0}".format(child['name']))
                    self._failed = True

    @block_only
    def _handle_ifThenElseStmt(self, node, ret=False, left=False):
        if len(node['children']) == 0:
            self._failed = True
            return
        child = node['children'][0]
        if child['name'] == 'ifBlockStmt':
            for child in node['children']:
                if child['name'] in ['ifBlockStmt', 'ifElseIfBlockStmt', 'ifElseBlockStmt']:
                    self._handle(child)
                elif child['name'] == 'END_IF':
                    pass
                else:
                    self.debug("ifThenElseStmt, can't handle {0}".format(child['name']))
                    self._failed = True
        elif child['name'] == 'IF':
            self.debug("ifThenElseStmt, too lazy")
            self._failed = True
        else:
            self.debug("ifThenElseStmt, can't handle {0}".format(child['name']))
            self._failed = True

    @block_only
    def _handle_forNextStmt(self, node, ret=False, left=False):
        if len(node['children']) == 0:
            self._failed = True
            return
        var = set()
        type = None
        values = []
        blocks = []
        for child in node['children']:
            if child['name'] in ['FOR', 'WS', "'='", 'TO', 'STEP', 'NEXT', 'endOfStatement']:
                pass
            elif child['name'] == 'ambiguousIdentifier':
                var.add(self._handle(child, ret=True, left=True))
            elif child['name'] == 'valueStmt':
                values.append(self._handle(child, ret=True))
            elif child['name'] == 'block':
                blocks.append(child)
            elif child['name'] == 'asTypeClause':
                type = self._handle(child, ret=True)
            else:
                self.debug("forNextStmt, can't handle {0}".format(child['name']))
                self._failed = True
        if len(var) != 1:
            self.debug('forNextStmt, error in the loop variable: {0}'.format(var))
            self._failed = True
        var = list(var)[0]
        if len(values) == 2:
            (start, end) = values
            step = '1'
        elif len(values) == 3:
            (start, end, step) = values
        else:
            self.debug('forNextStmt, wrong number of values: {0}'.format(len(values)))
            self._failed = True
        if self._failed:
            return
        if not type:
            type = '{0}'
        self._add_line('{0} = {1}'.format(var, type.format(start)))
        self._add_line('{0}__end = {1}'.format(var, type.format(end)))
        self._add_line('{0}__step = {1}'.format(var, type.format(step)))
        self._add_line('while True:')
        with self:
            self._add_line('if ({0}__step > 0 and {0} > {0}__end) or ({0}__step < 0 and {0} < {0}__end):'.format(var))
            with self:
                self._add_line('break')
            for block in blocks:
                self._handle(block)
            self._add_line('if {0}__step > 0:'.format(var))
            with self:
                self._add_line('{0} = {1}'.format(var, type.format('{0} + {0}__step'.format(var))))
            self._add_line('else:')
            with self:
                self._add_line('{0} = {1}'.format(var, type.format('{0} - {0}__step'.format(var))))


    def parsed(self):
        return not self._failed

    def __str__(self):
        return self._code
