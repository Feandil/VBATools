# Copyright (C) 2016, CERN
# This software is distributed under the terms of the GNU General Public
# Licence version 3 (GPL Version 3), copied verbatim in the file "COPYING".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from django.conf import settings
from django.db import transaction

from deobfuscator import Deobfuscator

from ..models import Sample, RawVBA, DecodedVBA
from ..utils import hash

class SampleDecoder(object):

    def __init__(self, remote=False):
        if remote:
            raise NotImplementedError

    def _get(self):
        return Sample.objects.all().filter(decoded__isnull=True)

    def _process(self, sample):
        rawvbas = RawVBA.objects.all().filter(sample__exact=sample)
        raws = map(lambda x: x.content, rawvbas)
        try:
            deob = Deobfuscator(raws)
        except RuntimeError:
            print('Unable to process sample {0}'.format(sample.id))
            return
        deob.clean_attr()
        deob.clean_arithmetic()
        deob.clean_whitespaces()
        deob.clean_newlines()
        deob.clean_ids()
        deob.clean_functions()
        decoded = deob.get_text()
        hashes = hash(decoded)
        with transaction.atomic():
            try:
                decodedvba = DecodedVBA.objects.all().get(**hashes)
            except DecodedVBA.DoesNotExist:
                decodedvba = DecodedVBA(content=decoded, **hashes)
                decodedvba.save()
            sample.decoded = decodedvba
            sample.save()

    def process(self):
        with transaction.atomic():
            samples = self._get()
        for sample in samples:
            self._process(sample)
