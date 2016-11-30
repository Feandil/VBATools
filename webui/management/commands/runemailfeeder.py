from django.core.management.base import BaseCommand

from ...daemons import EmailFeeder

class Command(BaseCommand):
    help = 'Run the email feeder locally'

    def handle(self, *args, **options):
        if args:
            feeder = EmailFeeder(url=args[0])
        else:
            feeder = EmailFeeder()
        feeder.run()
