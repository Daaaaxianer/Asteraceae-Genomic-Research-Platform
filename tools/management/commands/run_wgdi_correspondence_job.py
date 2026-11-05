from django.core.management.base import BaseCommand

from tools.views import run_wgdi_correspondence_job


class Command(BaseCommand):
    help = 'Run a WGDI correspondence job in the background.'

    def add_arguments(self, parser):
        parser.add_argument('place')
        parser.add_argument('tandem_length')
        parser.add_argument('pvalue')
        parser.add_argument('block_length')

    def handle(self, *args, **options):
        run_wgdi_correspondence_job(
            place=options['place'],
            tandem_length=options['tandem_length'],
            pvalue=options['pvalue'],
            block_length=options['block_length'],
        )
