from django.core.management.base import BaseCommand
from django.db import transaction

from ...models import Sample

class Command(BaseCommand):
    help = 'Remove all decoded VBAs'

    def handle(self, *args, **options):
        to_delete = set()
        with transaction.atomic():
            for sample in Sample.objects.all().filter(decoded__isnull=False).select_related('decoded'):
                to_delete.add(sample.decoded)
                sample.decoded = None
                sample.save()
            for decoded in to_delete:
                decoded.delete()
