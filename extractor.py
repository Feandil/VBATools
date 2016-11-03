# Copyright (C) 2016, CERN
# This software is distributed under the terms of the GNU General Public
# Licence version 3 (GPL Version 3), copied verbatim in the file "COPYING".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from oletools.olevba import VBA_Parser
from collections import Sequence

class Extractor(Sequence):

    def __init__(self, file, data=None):
        if data:
            vbaparser = VBA_Parser(file, data=data)
        else:
            vbaparser = VBA_Parser(file)
        self.data = [code for (_f, _p, _name, code) in vbaparser.extract_macros()]

    def __getitem__(self, index):
        return self.data[index]

    def __len__(self):
        return len(self.data)

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print('Expected 1 argument: file to analyse')
        sys.exit(-1)
    for blob in Extractor(sys.argv[1]):
        print(blob)
