# Copyright (C) 2016, CERN
# This software is distributed under the terms of the GNU General Public
# Licence version 3 (GPL Version 3), copied verbatim in the file "COPYING".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from django.conf import settings
from django.db import transaction

from deobfuscator import Deobfuscator

from ..models import Sample, DecodedVBA, DeobfuscatedVBA
from ..utils import hash

class SampleDeobfuscator(object):

    def __init__(self, remote=False):
        if remote:
            raise NotImplementedError

    def _get(self):
        return Sample.objects.all().filter(deobfuscated__isnull=True, decoded__isnull=False).select_related('decoded')

    def _process(self, sample):
        similar = Sample.objects.all().filter(deobfuscated__isnull=False, decoded__exact=sample.decoded).first()
        if similar:
            sample.deobfuscated = similar.deobfuscated
            sample.save()
            return
        deob = Deobfuscator([sample.decoded.content])
        deob.clean_resolvable()
        deob.inline_functions()
        deobfuscated = deob.get_text()
        hashes = hash(deobfuscated)
        with transaction.atomic():
            try:
                deobfuscatedvba = DeobfuscatedVBA.objects.all().get(**hashes)
            except DeobfuscatedVBA.DoesNotExist:
                deobfuscatedvba = DeobfuscatedVBA(content=deobfuscated, **hashes)
                deobfuscatedvba.save()
            sample.deobfuscated = deobfuscatedvba
            sample.save()

    def process(self):
        with transaction.atomic():
            samples = self._get()
        for sample in samples:
            self._process(sample)
