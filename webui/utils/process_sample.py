# Copyright (C) 2016, CERN
# This software is distributed under the terms of the GNU General Public
# Licence version 3 (GPL Version 3), copied verbatim in the file "COPYING".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from django.db import transaction
from extractor import Extractor

from ..models import RawVBA, Sample
from ..serializers import SampleSerializer
from .hasher import hash
from .kafka_sample import submit_sample

def process_file(raw_data, filename=None, email=None):
    vbas = list(Extractor(filename, data=raw_data))
    if not vbas:
        return
    content = {
        'filename': filename,
    }
    content.update(hash(raw_data))
    with transaction.atomic():
        try:
            sample = Sample.objects.all().get(**content)
        except:
            sample = Sample(**content)
            sample.save()
            for (pos, vba) in enumerate(vbas):
                RawVBA(sample=sample, position=pos, content=vba).save()
        if email is not None:
            email.save()
            sample.email.add(email)
    submit_sample(sample)
    return sample.id
