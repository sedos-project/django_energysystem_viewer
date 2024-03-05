from data_adapter import main, settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Closes the specified poll for voting"

    def add_arguments(self, parser):
        parser.add_argument("collection_url", type=str)

    def handle(self, *args, **options):
        collection_url = options["collection_url"]
        main.download_collection(collection_url)
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully downloaded collection from "{collection_url}" into folder "{settings.COLLECTIONS_DIR}".'
            )
        )
