# Copyright (C) 2016, CERN
# This software is distributed under the terms of the GNU General Public
# Licence version 3 (GPL Version 3), copied verbatim in the file "COPYING".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import print_function

from copy import copy,deepcopy
from parser import Parser

class Cleaner(object):

    NO_SIDE_EFFECT = [
        'HEXLITERAL', 'OCTLITERAL', 'DOUBLELITERAL', 'INTEGERLITERAL',
        'SHORTLITERAL', 'STRINGLITERAL', 'TRUE', 'FALSE',
        'endOfStatement', 'DIM', "'='", 'WS', 'AS', 'END_IF', 'CONST',
        "'('", "')'", 'IF', "'<'",  "'<>'", 'THEN', 'BOOLEAN', 'LONG',
        'BYTE', 'INTEGER', 'DATE', 'DOUBLE', 'FOR', 'TO', 'LEN',
        'STRING', 'NEXT', 'SINGLE', "','", "XOR", "'&'", "'>'", "'.'",
    ]

    NO_SIDE_EFFECT_IDENTIFIER = [
        'Sgn', 'LCase', 'LTrim', 'Asc', 'AscW', 'Trim', 'Month', 'Round'
        'Weekday', 'UBound', 'StrConv', 'vbUpperCase', 'UCase', 'vbLowerCase',
        'Chr', 'Day', 'Split', 'Round', 'Int', 'Weekday', 'Val', 'RTrim', 'Year',
        'Int', 'AscB', 'vbSunday', 'vbMonday', 'vbTuesday', 'vbWednesday', 'vbThursday',
        'vbFriday', 'vbSaturday', 'Fix', 'vbNullString', 'vbProperCase'
    ]

    PASS_THROUGH = [
        'implicitCallStmt_InStmt', 'literal', 'ifConditionStmt', 'argList',
        'arg', 'constStmt', 'valueStmt', 'implicitCallStmt_InBlock',
        'blockStmt', 'variableStmt', 'ifThenElseStmt', 'variableListStmt',
        'ambiguousIdentifier', 'subscript', 'ifBlockStmt',
        'iCS_S_VariableOrProcedureCall', 'asTypeClause', 'subscripts',
        'ambiguousKeyword', 'type', 'baseType',
        'iCS_S_MembersCall', 'iCS_B_ProcedureCall', 'iCS_S_MemberCall',
        'iCS_B_MemberProcedureCall', 'certainIdentifier', 'argsCall',
        'argCall',
    ]

    SIDE_EFFECT = [
        'VARIANT', 'onErrorStmt',
    ]

    def __init__(self, known_var=[], known_functions={}, debug=False):
        self._functions = known_functions
        self._changed = True
        self._external_vars = set()
        self._var_set = set()
        self._variable_unused = set()
        self._debug = debug
        self._failed = False

    def debug(self, line):
        if self._debug:
            print('Cleaner: {0}'.format(line))

    def clean(self, node, name):
        self._failed = False
        while self._changed:
            self._changed = False
            (sideeffects, var_used, _) = self._handle(node)
            if self._failed:
                self.debug('Cannot handle script, failing through')
                return (False, [], [])
            set_external_vars = set()
            previous_unused = copy(self._variable_unused)
            for var in self._var_set:
                if var in var_used:
                    continue
                if var in self._external_vars:
                    set_external_vars.add(var)
                    continue
                if var == name:
                    continue
                self.debug('{0} set but not used: ignoring'.format(var))
                self._variable_unused.add(var)
            if previous_unused != self._variable_unused:
                self._changed = True
            used_external_vars = self._external_vars.intersection(var_used)
            self._var_set = set()
        return (True, set_external_vars, used_external_vars)

    def __handle_and_combine(self, nodes):
        children = [self._handle(child) for child in nodes]
        sideeffect = any(child[0] for child in children)
        var_read = list(set(item for child in children for item in child[1]))
        var_set = list(set(item for child in children for item in child[2]))
        return (sideeffect, var_read, var_set)

    def _pass_though(self, node):
        if 'children' not in node:
            return (False, [], [])
        return self.__handle_and_combine(node['children'])

    def _handle(self, node):
        if node['name'] in self.NO_SIDE_EFFECT:
            return (False, [], [])
        if node['name'] in self.PASS_THROUGH:
            return self._pass_though(node)
        if node['name'] in self.SIDE_EFFECT:
            return (True, [], [])
        try:
            func = getattr(self, '_handle_{0}'.format(node['name']))
        except AttributeError:
            self._failed = True
            self.debug("Can't handle: " + node['name'])
            return (True, [], [])
        return func(node)

    def __check_and_remove(self, node, children):
        res = []
        vars_set = set()
        vars_read = set()
        for child in children:
            (sideeffect, var_read, var_set) = self._handle(child)
            if not sideeffect:
                child_text = Parser.get_node_text(child)
                if child_text == ['\n']:
                    continue
                self._changed = True
                self.debug('Removing {0}'.format(child_text))
                continue
            vars_set.update(var_set)
            vars_read.update(var_read)
            res.append(child)
        if len(res) == 0:
            node['children'] = []
            return (False, [], [])
        node['children'] =  [item for child in res for item in (child, Parser.newline())]
        return (True, list(vars_read), list(vars_set))

    def _handle_block(self, node):
        if 'children' in node:
            return self.__check_and_remove(node, node['children'])

    def _handle_subcalls(self, node):
        children =  Parser.xpath(node, ['block'])
        return self.__handle_and_combine(children)

    _handle_functionStmt = _handle_subcalls
    _handle_subStmt = _handle_subcalls

    def _handle_IDENTIFIER(self, node):
        if node['value'] in self.NO_SIDE_EFFECT_IDENTIFIER:
            return (False, [], [])
        if node['value'] in self._variable_unused or node['value'] in self._var_set:
            return (False, [node['value']], [])
        return (True, [node['value']], [])

    def __handle_setter(self, node):
        variable = value = type = None
        for child in node['children']:
            if child['name'] in ['implicitCallStmt_InStmt', 'ambiguousIdentifier']:
                variable = self._handle(child)
            elif child['name'] in ["WS", "'='", "'+='", "'-='", 'SET', 'LET']:
                pass
            elif child['name'] == 'asTypeClause':
                type = self._handle(child)
            elif child['name'] == 'valueStmt':
                value = self._handle(child)
            else:
                self.debug("Setter, can't handle {0}".format(child['name']))
                self._failed = True
        if variable is None or value is None:
            self.debug("Badly formated setter: {0}, {1}".format(str(variable), str(value)))
            self._failed = True
        if self._failed:
            return (True, [], [])
        if len(variable[1]) != 1 or len(variable[2]) != 0:
            self.debug("Unsupported setter: : {0}, {1}".format(str(variable), str(value)))
            return (True, variable[1] + value[1], variable[2] + value[2])
        var = list(variable[1])[0]
        self._var_set.add(var)
        if type is not None and type[0]:
            return (True, value[1] + [var],  value[2] + [var])
        if var in self._variable_unused:
            return (value[0], value[1], value[2] + [var])
        return (True, value[1], value[2] + [var])

    _handle_setStmt = __handle_setter
    _handle_letStmt = __handle_setter
    _handle_constSubStmt = __handle_setter

    def _handle_variableSubStmt(self, node):
        identifiers = Parser.xpath(node, ['ambiguousIdentifier'])
        if len(identifiers) != 1:
            self.debug("Bad variableSubStmt")
            self._failed = True
            return (True, [], [])
        variables = self._handle(identifiers[0])[1]
        if len(variables) != 1:
            self.debug("Bad variableSubStmt: {0}".format(str(variables)))
            self._failed = True
            return (True, variables, [])
        var = variables[0]
        if var in self._variable_unused:
            return (False, [], [])
        return (True, [], [var])

    def __handle_loop(self, node):
        identifiers = Parser.xpath(node, ['ambiguousIdentifier'])
        (_, variables, _) =  self.__handle_and_combine(identifiers)
        if len(variables) != 1:
            self.debug("Bad loop: {0}".format(str(variables)))
            self._failed = True
            return (True, variables, [])
        var = variables[0]
        self._var_set.add(var)
        rest = [child for child in node['children'] if child['name'] != 'ambiguousIdentifier']
        (sideeffect, var_used, var_set) = self.__handle_and_combine(rest)
        return (sideeffect, var_used, var_set + [var])

    _handle_forEachStmt = __handle_loop
    _handle_forNextStmt = __handle_loop
