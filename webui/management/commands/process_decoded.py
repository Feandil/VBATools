from django.core.management.base import BaseCommand

from time import sleep
from ...daemons import SampleDeobfuscator

class Command(BaseCommand):
    help = 'Deobfucate decoded VBAs'

    def handle(self, *args, **options):
        deobf = SampleDeobfuscator()
        while True:
            deobf.process()
            sleep(60)
