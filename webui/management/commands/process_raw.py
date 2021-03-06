from django.core.management.base import BaseCommand

from time import sleep
from ...daemons import SampleDecoder

class Command(BaseCommand):
    help = 'Decode raw VBAs'

    def handle(self, *args, **options):
        decoder = SampleDecoder()
        while True:
            decoder.process()
            sleep(60)
