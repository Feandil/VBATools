# Copyright (C) 2016, CERN
# This software is distributed under the terms of the GNU General Public
# Licence version 3 (GPL Version 3), copied verbatim in the file "COPYING".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import print_function

import copy
import re
import string

from parser import Parser
from cleaner import Cleaner
from translator import PROC_OK, Translator
from interpretor import Interpretor

class Deobfuscator(Parser):
    BASE_ATTR = set(['VB_Base', 'VB_Creatable', 'VB_Customizable', 'VB_Exposed', 'VB_GlobalNameSpace', 'VB_Name', 'VB_PredeclaredId', 'VB_TemplateDerived'])
    ARITHM = set(['literal', 'valueStmt', 'SHORTLITERAL', 'WS', "'-'", "'+'", "'('", "')'"])

    def __init__(self, data, debug=False):
        super(Deobfuscator, self).__init__(data)
        self._index = -1
        self._known_identifier = None
        self._identifier_order = []
        self._resolvable = set()
        self._resolved = set()
        self._var = {}
        self._proc = {}
        self._populate_vars()
        self._populate_proc()
        self._interpretor = Interpretor()
        self._debug = debug

    def debug(self, lines, ident=0):
        if self._debug:
            for line in lines.splitlines():
                print('{0}{1}'.format(' '*ident, line))


    def _populate_vars(self):
        for varst in self.findall(self.decl, 'variableSubStmt'):
            name = self.identifier_name(varst)
            self._var[name] = varst
            self._identifier_order.append(name)

    def _populate_proc(self):
        for subst in self.findall(self.body, 'subStmt'):
            name = self.identifier_name(subst)
            self._proc[name] = subst
            self._identifier_order.append(name)
        for funst in self.findall(self.body, 'functionStmt'):
            name = self.identifier_name(funst)
            self._proc[name] = funst
            self._identifier_order.append(name)

    def __remove_proc(self, node):
        moduleBodyElement = node['parent']
        assert(len(moduleBodyElement['children']) == 1)
        parent_children = moduleBodyElement['parent']['children']
        del moduleBodyElement['parent']
        index = parent_children.index(moduleBodyElement)
        parent_children.pop(index)
        if len(parent_children) > index and parent_children[index]['name'] == 'endOfLine':
            parent_children.pop(index)

    def _remove_proc(self, proc_name):
        for subst in self.findall(self.body, 'subStmt'):
            name = self.identifier_name(subst)
            if name == proc_name:
                self.__remove_proc(subst)
        for funst in self.findall(self.body, 'functionStmt'):
            name = self.identifier_name(funst)
            if name == proc_name:
                self.__remove_proc(funst)

    def _populate_identifiers(self):
        if self._known_identifier is None:
            self._known_identifier = set()
            self.getallidentifiers(self.decl, acc=self._known_identifier)
            self.getallidentifiers(self.body, acc=self._known_identifier)

    def _proc_deps(self, proc_name):
        proc = self._proc[proc_name]
        ids = self.getallidentifiers(proc)
        deps = set()
        ids.discard(proc_name)
        for id in self._var:
            if id in ids:
                deps.add(id)
        for lst in [self.proc_arguments(proc), self.local_variables(proc)]:
            for id in lst:
                ids.discard(id)
        for id in self._proc:
            if id in ids:
                deps.add(id)
        return (ids, deps)

    def _build_deps(self):
        proc_dep = {}
        reverse_dep = {}
        var_dep = {}
        for proc in self._proc:
            (all_deps, proc_deps) = self._proc_deps(proc)
            proc_dep[proc] = set(all_deps)
            for dep in proc_deps:
                try:
                    reverse_dep[dep].add(proc)
                except KeyError:
                    reverse_dep[dep] = set([proc])
            for var in self._var:
                if var in all_deps:
                    try:
                        var_dep[var].add(proc)
                    except KeyError:
                        var_dep[var] = set([proc])
        return (proc_dep, reverse_dep, var_dep)

    def _next_name(self):
        self._index +=1
        if (self._index < len(string.ascii_letters)):
            return '_{0}_'.format(string.ascii_letters[self._index])
        if (self._index < len(string.ascii_letters) * (len(string.ascii_letters) + 1)):
            return '_{0}{1}_'.format(string.ascii_letters[self._index / len(string.ascii_letters) - 1],
                                     string.ascii_letters[self._index % len(string.ascii_letters)])
        sys.exit(-1)

    def _next_valid_name(self):
        self._populate_identifiers()
        name = self._next_name()
        while name in self._known_identifier:
            name = self._next_name()
        self._known_identifier.add(name)
        return name

    def _update_global_id(self, oldname, newname):
        for dic in [self._proc, self._var]:
            if oldname in dic:
                dic[newname] = dic[oldname]
                del dic[oldname]

    def _rename(self, node, oldname, newname, update_global_id=False):
        for identifier in self.findall(node, 'IDENTIFIER'):
            if identifier['value'] == oldname:
                identifier['value'] = newname
            elif update_global_id:
                parts = identifier['value'].split('_')
                if parts[0] == oldname:
                    parts[0] = newname
                    self._known_identifier.remove(identifier['value'])
                    self._update_global_id(identifier['value'], '_'.join(parts))
                    identifier['value'] = '_'.join(parts)

    def rename(self, oldname, node=None):
        newname = self._next_valid_name()
        self.debug('Renaming {0} as {1}'.format(oldname, newname))
        if node is None:
            self._update_global_id(oldname, newname)
            self._rename(self.attr, oldname, newname, update_global_id=True)
            self._rename(self.decl, oldname, newname, update_global_id=True)
            self._rename(self.body, oldname, newname, update_global_id=True)
        else:
            self._rename(node, oldname, newname)
        self._known_identifier.discard(oldname)
        return newname

    def clean_ids(self):
        for id in self._identifier_order:
            if id in self._proc:
                proc = self._proc[id]
                arguments = self.proc_arguments(proc)
                variables = self.local_variables(proc)
                for argument in arguments:
                    self.rename(argument, proc)
                for variable in variables:
                    if (variable != id and
                            variable not in arguments and
                            variable not in self._identifier_order):
                        self.rename(variable, proc)
        (_, reverse_dep, var_dep) = self._build_deps()
        for id in self._identifier_order:
            if id in reverse_dep or id in var_dep:
                new_name = self.rename(id)

    def clean_arithmetic(self):
        for node in [self.attr, self.decl, self.body]:
            valuestmts = self.findall(node, 'valueStmt')
            for stmt in valuestmts:
                classes = self.getallclasses(stmt)
                if classes.issubset(self.ARITHM):
                    val = None
                    try:
                        val = eval(self.get_text(stmt))
                    except:
                        raise
                    stmt['children'] = [{'name': 'literal', 'children': [{'name': 'SHORTLITERAL', 'value': str(val)}]}]

    def clean_whitespaces(self):
        for node in [self.attr, self.decl, self.body]:
            for ws in self.findall(node, 'WS'):
                ws['value'] = ' '

    def clean_newlines(self):
        for node in [self.attr, self.decl, self.body]:
            for newline in self.findall(node, 'endOfStatement'):
                newline.clear()
                newline.update(self.newline())

    def _useless_attr(self, attrst):
        simple_attr = self.xpath(attrst, ['implicitCallStmt_InStmt', 'iCS_S_VariableOrProcedureCall'])
        if not simple_attr:
            return False
        name = self.identifier_name(simple_attr[0])
        if name in self.BASE_ATTR:
            return True
        else:
            return False

    def clean_attr(self):
        self.attr['children'] = [attr for attr in self.attr['children'] if not self._useless_attr(attr)]
        attrs = []
        newline = True
        for attr in self.attr['children']:
            if newline and attr['name'] == 'endOfLine':
                continue
            attrs.append(attr)
            newline = (attr['name'] == 'endOfLine')
        self.attr['children'] = attrs

    def __format_value(self, value):
        if isinstance(value, int):
            return {"name": "literal", "children": [{ 'name': 'SHORTLITERAL', 'value': str(value)}]}
        elif isinstance(value, basestring):
            return {"name": "literal", "children": [ { 'name': 'STRINGLITERAL', 'value': '"{0}"'.format(value.replace('"', '""'))}]}
        elif isinstance(value, list):
            if len(value) > 0:
                literal_list = [self.__format_value(val) for val in value]
                valueStmt_list = [{"name": "valueStmt", "children": [literal]} for literal in literal_list]
                subscript_list = [{"name": "subscript", "children": [subscript]} for subscript in valueStmt_list]
                subscripts = [subscript_list[0]]
                for subscript in subscript_list[1:]:
                    subscripts.append({"name": "','","value": ","})
                    subscripts.append({"name": "WS","value": " "})
                    subscripts.append(subscript)
                values = [{"name": "subscripts", "children": subscripts}]
            else:
                values = []
            name = {
                       "name": "ambiguousIdentifier",
                       "children": [{
                           "name": "IDENTIFIER",
                            "value": "Array"
                       }]
                    }
            return  {
                 "name": "implicitCallStmt_InStmt",
                 "children": [{
                     "name": "iCS_S_VariableOrProcedureCall",
                     "children": (
                         [name] +
                         [{"name": "'('", "value": "("}] +
                         values +
                         [{"name": "')'", "value": ")"}]
                     )
                 }]
            }
        else:
            self.debug("__format_value, unsupported type {0}".format(type(value)))
        return None


    def _replace_call(self, proc, node, known_functions):
        replaced = True
        for proccall in (self.findall(node, 'iCS_B_ProcedureCall') + self.findall(node, 'iCS_S_VariableOrProcedureCall')):
            name = self.identifier_name(proccall)
            if name == proc:
                translator = Translator(proccall['parent'], known_functions=known_functions, debug=self._debug)
                if not translator.parsed():
                    replaced = False
                    continue
                try:
                    value = self._interpretor.eval(str(translator), {})
                except NotImplementedError as e:
                    self.debug(str(e))
                    replaced = False
                    continue
                except Exception as e:
                    self.debug(str(e))
                    replaced = False
                    continue
                try:
                    parent = proccall['parent']['parent']
                except Exception as e:
                    replaced = False
                    self.debug(str(e))
                    continue
                if parent['name'] != 'valueStmt':
                    self.debug("_replace_call, can't handle {0}".format(parent['name']))
                    replaced = False
                    continue
                newval = self.__format_value(value)
                if newval is None:
                    replaced = False
                    continue
                self.debug("Replacing:")
                self.debug(self.get_text(parent['children'][0]), ident=2)
                self.debug("With:")
                self.debug(str(value), ident=2)
                self.debug("\n")
                parent['children'] = [newval]
        return replaced

    def _clean_up_function(self, touched, proc_dep, reverse_dep):
        done = False
        while not done:
            done = True
            removed = set()
            for proc in touched:
                if proc in reverse_dep:
                    if len(reverse_dep[proc]) == 0:
                        self.debug('Removing {0}: unused'.format(proc))
                        del self._proc[proc]
                        if proc in reverse_dep:
                            del reverse_dep[proc]
                        self._remove_proc(proc)
                        if proc in proc_dep:
                            for called in proc_dep[proc]:
                                if called in reverse_dep:
                                    reverse_dep[called].discard(proc)
                                    done = False
                        del proc_dep[proc]
                    else:
                        self.debug('Not removing {0}, still used by ({1}): {2}'.format(proc, len(reverse_dep[proc]), ', '.join(reverse_dep[proc])))

    def clean_resolvable(self):
        (proc_dep, reverse_dep, _) = self._build_deps()
        done = False
        non_translatable = set()
        translated = set()
        while not done:
            done = True
            good = set(list(PROC_OK) + list(non_translatable) + list(translated))
            for proc in proc_dep:
                if proc in non_translatable or proc in translated:
                    continue
                if proc_dep[proc].issubset(good):
                    translator = Translator(self._proc[proc], known_functions=translated, debug=self._debug)
                    if not translator.parsed():
                        self.debug("Can't translate {0}".format(proc))
                        non_translatable.add(proc)
                        continue
                    code = str(translator)
                    self.debug("Emulating:")
                    self.debug(self.get_text(self._proc[proc]), ident=2)
                    self.debug("With:")
                    self.debug(code, ident=2)
                    self.debug("\n")
                    done = False
                    self._interpretor.add_fun(proc, code)
                    translated.add(proc)
                    if proc in reverse_dep:
                        for caller in list(reverse_dep[proc]):
                            if self._replace_call(proc, self._proc[caller], translated):
                                reverse_dep[proc].remove(caller)
        for proc in translated:
            if proc in reverse_dep:
                for caller in list(reverse_dep[proc]):
                    if self._replace_call(proc, self._proc[caller], translated):
                        reverse_dep[proc].remove(caller)
        self._clean_up_function(translated, proc_dep, reverse_dep)
        self.debug('Unsolved dependencies:')
        for proc in proc_dep:
            if proc not in translated:
                self.debug('{0}: {1}'.format(proc, sorted(proc_dep[proc])))

    def _inline_function(self, proc_name, block, target_name):
        proc = self._proc[proc_name]
        if self.proc_arguments(proc):
            self.debug('Cannot inline {0} in {1}: arguments required'.format(proc_name, target_name))
            return False
        proc_block = self.xpath(proc, ['block'])
        if len(proc_block) != 1:
            self.debug('Cannot inline {0} in {1}: invalid function (more than one block)'.format(proc_name, target_name))
            return False
        proc_blocks = proc_block[0]['children']
        while proc_blocks[-1]['name'] == 'endOfStatement':
            proc_blocks.pop()
        self.debug('Inlining {0} in {1}'.format(proc_name, target_name))
        parent = block['parent']
        del block['parent']
        index = parent['children'].index(block)
        new_children = copy.deepcopy(proc_blocks)
        for child in new_children:
            child['parent'] = parent
        parent['children'] = parent['children'][:index] + new_children + parent['children'][(index + 1):]
        return True

    def _is_simple_callout(self, node):
        while node['name'] != 'IDENTIFIER':
            if 'children' not in node or len(node['children']) != 1:
                return False
            node = node['children'][0]
        return node['value']

    def inline_functions(self):
        (proc_dep, reverse_dep, _) = self._build_deps()
        work_deps = copy.deepcopy(proc_dep)
        for caller in work_deps:
            work_deps[caller] = [callee for callee in work_deps[caller] if callee in self._proc]
        todo = list(self._proc)
        inlined = set()
        while todo:
            for proc in list(todo):
                if proc not in work_deps or not work_deps[proc]:
                    blocks = self.findall(self._proc[proc], 'blockStmt')
                    for block in blocks:
                        callout = self._is_simple_callout(block)
                        if (not callout) or callout not in self._proc:
                            continue
                        if self._inline_function(callout, block, proc):
                            inlined.add(callout)
                    todo.remove(proc)
                    if proc in reverse_dep:
                        for caller in reverse_dep[proc]:
                            work_deps[caller].remove(proc)
        (_, new_reverse_dep, _) = self._build_deps()
        for proc in reverse_dep:
            if proc not in new_reverse_dep:
                reverse_dep[proc] = set([])
        self._clean_up_function(inlined, proc_dep, reverse_dep)

    def clean_functions(self):
        for proc in self._proc:
            Cleaner(known_var=self._var, debug=self._debug).clean(self._proc[proc], proc)

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2 and (len(sys.argv) != 3 or sys.argv[1] != '-d'):
        print('Expected 1-2 argument: file to analyse or -d file to analyse')
        sys.exit(-1)
    from extractor import Extractor
    if len(sys.argv) == 2:
        vbas = Extractor(sys.argv[1])
        debug = False
    else:
        vbas = Extractor(sys.argv[2])
        debug = True
    deob = Deobfuscator(vbas, debug=debug)
    deob.clean_attr()
    deob.clean_arithmetic()
    deob.clean_whitespaces()
    deob.clean_newlines()
    deob.clean_ids()
    deob.clean_functions()
    deob.clean_resolvable()
    deob.inline_functions()
    print(deob.get_text())
