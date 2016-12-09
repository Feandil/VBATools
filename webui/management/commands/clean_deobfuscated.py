from django.core.management.base import BaseCommand
from django.db import transaction

from ...models import Sample

class Command(BaseCommand):
    help = 'Remove all deobfuscated VBAs'

    def handle(self, *args, **options):
        to_delete = set()
        with transaction.atomic():
            for sample in Sample.objects.all().filter(deobfuscated__isnull=False).select_related('deobfuscated'):
                to_delete.add(sample.deobfuscated)
                sample.deobfuscated = None
                sample.save()
            for deob in to_delete:
                deob.delete()
