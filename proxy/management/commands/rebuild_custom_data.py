import importlib

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from proxy.models import Chunk
from proxy.utils import bytes_to_rich_data


class Command(BaseCommand):
    help = 'Rebuilds custom data of Chunks'

    def handle(self, *args, **options):
        # Get custom function
        func_path = getattr(settings, 'CUSTOM_CHUNK_SERIALIZATION_FUNCTION', None)
        if not func_path:
            raise CommandError('"CUSTOM_CHUNK_SERIALIZATION_FUNCTION" is not defined in settings!')
        mod_name, func_name = func_path.rsplit('.', 1)
        mod = importlib.import_module(mod_name)
        func = getattr(mod, func_name)

        chunks_size = Chunk.objects.count()

        min_id = 0
        chunks_rebuilt = 0
        while True:

            # Iterate bunch of chunks
            chunks = []
            for chunk in Chunk.objects.filter(id__gt=min_id).order_by('id')[0:100]:
                # Rebuild custom data
                chunk.custom_data = func(bytes_to_rich_data(chunk.data))
                chunks.append(chunk)

                # Update counters and flags
                min_id = chunk.id
                chunks_found = True
                chunks_rebuilt += 1

            # Bulk update
            if chunks:
                Chunk.objects.bulk_update(chunks, ['custom_data'])

            # Display progress
            self.stdout.write(self.style.SUCCESS('{:.0f} % ready'.format(chunks_rebuilt / chunks_size * 100)))

            # Check if job is done
            if not chunks:
                break
