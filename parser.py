# Copyright (C) 2016, CERN
# This software is distributed under the terms of the GNU General Public
# Licence version 3 (GPL Version 3), copied verbatim in the file "COPYING".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from oletools.olevba import VBA_Parser
from subprocess import Popen, PIPE
import inspect
import os.path
import json

class Parser(object):

    def _parse(self, data):
        jars = ['VBA.jar','antlr4-4.5.3.jar','gson-2.7.jar']
        jars = [os.path.join(self._path, 'parser', jar) for jar in jars]
        proc = Popen(['java', '-cp', ':'.join(jars), 'VBA'], stdin=PIPE, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        (out, err) = proc.communicate(input=data)
        if proc.returncode != 0:
            return None
        return json.loads(out)

    @classmethod
    def _get_text(cls, node):
        ret = []
        if node['name'] == 'EOF':
            return ret
        if 'value' in node:
            ret.append(node['value'])
        if 'children' in node:
            for child in node['children']:
                ret.extend(cls._get_text(child))
        return ret

    @classmethod
    def xpath(cls, node, path):
        if not path:
            return [node]
        if 'children' not in node:
            return []
        name, path = path[0], path[1:]
        if name == '*':
            return [elt for child in node['children'] for elt in cls.xpath(child, path)]
        ret = []
        for child in node['children']:
            if child['name'] == name:
                ret.extend(cls.xpath(child, path))
        return ret

    @classmethod
    def findall(cls, node, node_name):
        ret = []
        if node['name'] == node_name:
            ret.append(node)
        if 'children' not in node:
            return ret
        for child in node['children']:
            ret.extend(cls.findall(child, node_name))
        return ret

    @classmethod
    def getallclasses(cls, node, acc=None):
        if acc is None:
            acc = set()
        acc.add(node['name'])
        if 'children' in node:
            for child in node['children']:
                cls.getallclasses(child, acc=acc)
        return acc

    @classmethod
    def identifier_name(cls, node):
        try:
            return cls.xpath(node, ['ambiguousIdentifier', 'IDENTIFIER'])[0]['value']
        except IndexError:
            pass
        try:
            return cls.xpath(node, ['certainIdentifier', 'IDENTIFIER'])[0]['value']
        except IndexError:
            pass
        try:
            return cls.xpath(node, ['ambiguousIdentifier', 'ambiguousKeyword', '*'])[0]['value']
        except IndexError:
            pass
        # Might be a "iCS_S_MembersCall", but we don't want those
        return None


    def __init__(self, file, data=None):
        if data:
            vbaparser = VBA_Parser(file, data=data)
        else:
            vbaparser = VBA_Parser(file)
        self._raw = [code for (_f, _p, _name, code) in vbaparser.extract_macros()]
        self._path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        contents = [self._parse(data) for data in self._raw]
        self._content = contents
        self.attr = {'name': 'moduleAttributes', 'children': []}
        self.decl = {'name': 'moduleDeclarations', 'children': []}
        self.body = {'name': 'moduleBody', 'children': []}
        for content in contents:
            attrs = self.xpath(content, ['module', 'moduleAttributes', '*'])
            self.attr['children'].extend(attrs)
            decls = self.xpath(content, ['module', 'moduleDeclarations', '*'])
            self.decl['children'].extend(decls)
            bodys = self.xpath(content, ['module', 'moduleBody', '*'])
            self.body['children'].extend(bodys)

    def get_text(self, node=None):
        if node is None:
            attrs = self._get_text(self.attr)
            decls = self._get_text(self.decl)
            body = self._get_text(self.body)
            return ''.join([''.join(attrs), ''.join(decls), ''.join(body)])
        else:
            return ''.join(self._get_text(node))


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print('Expected 1 argument: file to analyse')
        sys.exit(-1)
    d = Parser(sys.argv[1])
    print(d.get_text())

