from django.core.management.base import BaseCommand

from ...daemons import SampleDecoder

class Command(BaseCommand):
    help = 'Process raw VBAs'

    def handle(self, *args, **options):
        decoder = SampleDecoder()
        decoder.process()
