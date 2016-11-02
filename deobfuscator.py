# Copyright (C) 2016, CERN
# This software is distributed under the terms of the GNU General Public
# Licence version 3 (GPL Version 3), copied verbatim in the file "COPYING".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

import re
import string

from parser import Parser
from translator import PROC_OK, Translator
from interpretor import Interpretor

class Deobfuscator(Parser):
    BASE_ATTR = set(['VB_Base', 'VB_Creatable', 'VB_Customizable', 'VB_Exposed', 'VB_GlobalNameSpace', 'VB_Name', 'VB_PredeclaredId', 'VB_TemplateDerived'])
    ARITHM = set(['literal', 'valueStmt', 'SHORTLITERAL', 'WS', "'-'", "'+'", "'('", "')'"])

    def __init__(self, file, data=None, debug=False):
        super(Deobfuscator, self).__init__(file, data=data)
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
        for lst in [self.proc_arguments(proc), self.local_variables(proc)]:
            for id in lst:
                ids.discard(id)
        for lst in [self._var, self._proc]:
            for id in lst:
                if id in ids:
                    deps.add(id)
        return (ids, deps)

    def _build_deps(self):
        proc_dep = {}
        reverse_dep = {}
        for proc in self._proc:
            (all_deps, proc_deps) = self._proc_deps(proc)
            proc_dep[proc] = all_deps
            for dep in proc_deps:
                try:
                    reverse_dep[dep].add(proc)
                except KeyError:
                    reverse_dep[dep] = set([proc])
        return (proc_dep, reverse_dep)

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
        if self._debug:
            print('Renaming {0} as {1}'.format(oldname, newname))
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
        (_, reverse_dep) = self._build_deps()
        for id in self._identifier_order:
           if id in reverse_dep:
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
                    except e:
                        raise e
                        continue
                    stmt['children'] = [{'name': 'literal', 'children': [{'name': 'SHORTLITERAL', 'value': str(val)}]}]

    def clean_whitespaces(self):
        for node in [self.attr, self.decl, self.body]:
            for ws in self.findall(node, 'WS'):
                ws['value'] = ' '

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
            return {"name": "literal", "children": [ { 'name': 'STRINGLITERAL', 'value': '"{0}"'.format(value)}]}
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
        elif self._debug:
            print("__format_value, unsupported type {0}".format(type(value)))
        return None


    def _replace_call(self, proc, node, known_functions):
        replaced = True
        for proccall in (self.findall(node, 'iCS_B_ProcedureCall') + self.findall(node, 'iCS_S_VariableOrProcedureCall')):
            name = self.identifier_name(proccall)
            if name == proc:
                translator = Translator(self, proccall['parent'], known_functions=known_functions, debug=self._debug)
                if not translator.parsed():
                    replaced = False
                    continue
                try:
                    value = self._interpretor.eval(str(translator), {})
                except Exception as e:
                    if self._debug:
                        print(e)
                    replaced = False
                    continue
                if self._debug:
                    print("Replacing:")
                    print(self.get_text(proccall['parent']))
                    print("With:")
                    print(str(value))
                    print("\n")
                try:
                    parent = proccall['parent']['parent']
                except Exception as e:
                    replaced = False
                    if self._debug:
                        print(e)
                    continue
                if parent['name'] != 'valueStmt':
                    if self._debug:
                        print("_replace_call, can't handle {0}".format(parent['name']))
                    replaced = False
                    continue
                newval = self.__format_value(value)
                if newval is None:
                    replaced = False
                    continue
                parent['children'] = [newval]
        return replaced

    def clean_resolvable(self):
        (proc_dep, reverse_dep) = self._build_deps()
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
                    translator = Translator(self, self._proc[proc], known_functions=translated, debug=self._debug)
                    if not translator.parsed():
                        non_translatable.add(proc)
                        continue
                    code = str(translator)
                    if self._debug:
                        print("Emulating:")
                        print(self.get_text(self._proc[proc]))
                        print("With:")
                        print(code)
                        print("\n")
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
        for proc in translated:
            if proc in reverse_dep and len(reverse_dep[proc]) == 0:
                del self._proc[proc]
                self._remove_proc(proc)

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2 and (len(sys.argv) != 3 or sys.argv[1] != '-d'):
        print('Expected 1-2 argument: file to analyse or -d file to analyse')
        sys.exit(-1)
    if len(sys.argv) == 2:
        d = Deobfuscator(sys.argv[1])
    else:
        d = Deobfuscator(sys.argv[2], debug=True)
    d.clean_attr()
    d.clean_arithmetic()
    d.clean_whitespaces()
    d.clean_ids()
    d.clean_resolvable()
    print(d.get_text())
