from django.core.management.base import BaseCommand

from time import sleep
from ...daemons import SampleDeobfuscator
from ...daemons import SampleDecoder

class Command(BaseCommand):
    help = 'Process raw VBAs completely'

    def handle(self, *args, **options):
        decoder = SampleDecoder()
        deobf = SampleDeobfuscator()
        while True:
            decoder.process()
            deobf.process()
            sleep(60)

