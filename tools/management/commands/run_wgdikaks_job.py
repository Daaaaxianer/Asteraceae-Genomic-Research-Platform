from django.core.management.base import BaseCommand

from tools.views import run_wgdikaks_job


class Command(BaseCommand):
    help = 'Run a WGDI KaKs job in the background.'

    def add_arguments(self, parser):
        parser.add_argument('place')

    def handle(self, *args, **options):
        run_wgdikaks_job(place=options['place'])
