from oletools.olevba import VBA_Parser
import hashlib
import string
import sys
import re

class Extractor(object):

    def __init__(self, file):
        vbaparser = VBA_Parser(file)
        self._raw = [code for (_f, _p, _name, code) in vbaparser.extract_macros()]
        self._content = [line for data in self._raw for line in data.splitlines(True)]
        self._index = -1

    def _next_name(self):
        self._index +=1
        if (self._index < len(string.ascii_letters)):
            return '_{0}_'.format(string.ascii_letters[self._index])
        if (self._index < len(string.ascii_letters) * len(string.ascii_letters)):
            return '_{0}{1}_'.format(string.ascii_letters[self._index / len(string.ascii_letters)],
                                     string.ascii_letters[self._index % len(string.ascii_letters)])
        sys.exit(-1)

    def _next_valid_name(self):
        name = self._next_name()
        for line in self._content:
            if name in line:
                return self._next_valid_name()
        return name

    def startswith(self, val, index=0):
        try:
            return self._content[index].startswith(val)
        except KeyError:
            return False

    def remove_attributes(self):
        while self.startswith('Attribute'):
            self._content.pop(0)

    def _rename(self, var):
        if var.startswith('_'):
            return
        src = r'\b{0}\b'.format(var)
        dst = self._next_valid_name()
        self._content = [re.sub(src,dst, line) for line in self._content]

    def _rename_block(self, start, end):
        index = start
        while index <= end:
            if self.startswith('Set ', index):
                self._rename(self._content[index].split()[1])
            elif re.match('^([^ ]*):[\n\r]*$', self._content[index]):
                self._rename(self._content[index].split(':')[0])
            elif re.match('([^ ]*) = ', self._content[index]):
                self._rename(self._content[index].split()[0])
            elif re.match('For Each ([^ ]*) In ', self._content[index]):
                self._rename(self._content[index].split()[2])
            index += 1

    def _rename_args(self, args):
        if not args:
             return
        for arg in args.split(','):
             self._rename(arg.split()[1])

    def check_funsub(self, index, reg_start, str_end):
        x = re.match(reg_start, self._content[index])
        if not x:
            return 0
        self._rename(x.group(1))
        self._rename_args(x.group(2))
        index += 1
        start = index
        while not self.startswith(str_end, index):
            index += 1
        self._rename_block(start, index - 1)
        return index

    def rename_all(self):
        index = 0
        while self.startswith('Dim', index):
            line = self._content[index]
            var = line.split()[1]
            self._rename(var)
            index += 1
        max = len(self._content)
        while index < max:
            fun = self.check_funsub(index, r'(?:Public )?Function ([^(]*).*\((.*)\)', 'End Function')
            if fun:
                 index = fun + 1
                 continue
            sub = self.check_funsub(index, r'(?:Public )?Sub ([^(]*).*\((.*)\)', 'End Sub')
            if sub:
                 index = sub + 1
                 continue
            index +=1

    def get_content(self):
        return ''.join(self._content)

    def __str__(self):
        return self.get_content()

    def get_hash(self, algo='sha1'):
        m = hashlib.new(algo)
        m.update(self.get_content())
        m.update("\n")
        return m.hexdigest()

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print('Expected 1 argument: file to analyse (got {0})'.format(sys.argv))
        sys.exit(-1)
    if len(sys.argv) == 3:
        if sys.argv[2] != '-v' and sys.argv[3] != '-v':
            print('Expected 1 argument: file to analyse (got {0})'.format(sys.argv))
            sys.exit(-1)
    ext = Extractor(sys.argv[1])
    ext.remove_attributes()
    ext.rename_all()
    if len(sys.argv) == 3:
        print(str(ext))
    else:
        print('{0}: {1}'.format(sys.argv[1], ext.get_hash()))
