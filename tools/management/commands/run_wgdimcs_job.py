from django.core.management.base import BaseCommand

from tools.views import run_wgdimcs_job


class Command(BaseCommand):
    help = 'Run a WGDI MCS job in the background.'

    def add_arguments(self, parser):
        parser.add_argument('place')
        parser.add_argument('evalue')
        parser.add_argument('score')

    def handle(self, *args, **options):
        run_wgdimcs_job(
            place=options['place'],
            evalue=options['evalue'],
            score=options['score'],
        )
