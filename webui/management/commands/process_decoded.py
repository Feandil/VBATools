from django.core.management.base import BaseCommand

from ...daemons import SampleDeobfuscator

class Command(BaseCommand):
    help = 'Process raw VBAs'

    def handle(self, *args, **options):
        deobf = SampleDeobfuscator()
        deobf.process()
