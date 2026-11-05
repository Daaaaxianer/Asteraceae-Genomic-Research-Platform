from django.core.management.base import BaseCommand, CommandError

from browse.views import (
    _dupgen_job_is_valid,
    _function_gene_job_is_valid,
    _interproscan_job_is_valid,
    _kegg_job_is_valid,
    run_dupgen_all_species_job,
    run_function_gene_all_species_job,
    run_interproscan_all_species_job,
    run_kegg_all_species_job,
)


JOB_HANDLERS = {
    'dupgen': (_dupgen_job_is_valid, run_dupgen_all_species_job, 'DupGen'),
    'function_gene': (_function_gene_job_is_valid, run_function_gene_all_species_job, 'Function gene'),
    'interproscan': (_interproscan_job_is_valid, run_interproscan_all_species_job, 'InterProScan'),
    'kegg': (_kegg_job_is_valid, run_kegg_all_species_job, 'KEGG'),
}


class Command(BaseCommand):
    help = 'Run a submitted all-species background job.'

    def add_arguments(self, parser):
        parser.add_argument('job_type', choices=sorted(JOB_HANDLERS.keys()))
        parser.add_argument('job_id')

    def handle(self, *args, **options):
        job_type = options['job_type']
        job_id = options['job_id']
        is_valid, runner, label = JOB_HANDLERS[job_type]

        if not is_valid(job_id):
            raise CommandError(f'Invalid {label} job id.')

        runner(job_id)
