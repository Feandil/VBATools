# Copyright (C) 2016, CERN
# This software is distributed under the terms of the GNU General Public
# Licence version 3 (GPL Version 3), copied verbatim in the file "COPYING".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

import string

from parser import Parser

class Deobfuscator(Parser):

    def __init__(self, file, data=None):
        super(Deobfuscator, self).__init__(file, data=data)
        self._index = -1
        self._known_identifier = None
        self._identifier_order = []
        self._deps = {}
        self._var = {}
        self._proc = {}
        self._populate_vars()
        self._populate_proc()
        self._build_dependency_tree()

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

    def _populate_identifiers(self):
        if self._known_identifier is None:
            self._known_identifier = set()
            for identifier in self.findall(self.decl, 'IDENTIFIER'):
                self._known_identifier.add(identifier['value'])
            for identifier in self.findall(self.body, 'IDENTIFIER'):
                self._known_identifier.add(identifier['value'])

    def _build_dependency_tree(self):
        self._deps = {}
        for proc in self._proc:
            for proccall in self.findall(self._proc[proc], 'iCS_B_ProcedureCall'):
                name = self.identifier_name(proccall)
                try:
                    self._deps[name].add(proc)
                except KeyError:
                    self._deps[name] = set([proc])
            for procvar in self.findall(self._proc[proc], 'iCS_S_VariableOrProcedureCall'):
                name = self.identifier_name(procvar)
                try:
                    self._deps[name].add(proc)
                except KeyError:
                    self._deps[name] = set([proc])

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

    def _rename(self, node, oldname, newname):
        for identifier in self.findall(node, 'IDENTIFIER'):
            if identifier['value'] == oldname:
                identifier['value'] = newname

    def rename(self, oldname, node=None):
        newname = self._next_valid_name()
        if node is None:
            self._rename(self.decl, oldname, newname)
            self._rename(self.body, oldname, newname)
            self._known_identifier.remove(oldname)
        else:
            self._rename(node, oldname, newname)

    def clean_proc_variables(self, proc_name):
        proc = self._proc[proc_name]
        for argument in self.xpath(proc,['argList', 'arg']):
            name = self.identifier_name(argument)
            if name:
                self.rename(name, proc)
        for node_type in ['lineLabel', 'forEachStmt', 'forNextStmt']:
            for stmt in self.findall(proc, node_type):
                name = self.identifier_name(stmt)
                if name and name != proc_name and name not in self._identifier_order:
                    self.rename(name, proc)
        for node_type in ['setStmt', 'letStmt']:
            for setstmt in self.findall(proc, node_type):
                var = self.xpath(setstmt, ['implicitCallStmt_InStmt', '*'])[0]
                name = self.identifier_name(var)
                if name and name != proc_name and name not in self._identifier_order:
                    self.rename(name, proc)

    def clean_ids(self):
        for id in self._identifier_order:
           if id in self._proc:
               self.clean_proc_variables(id)
        for id in self._identifier_order:
           if id in d._deps:
               self.rename(id)


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print('Expected 1 argument: file to analyse')
        sys.exit(-1)
    d = Deobfuscator(sys.argv[1])
    d.clean_ids()
    print(d.get_text())
