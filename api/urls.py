from django.urls import path
from . import views
from . import downloads

app_name = 'api'

urlpatterns = [
    path('download/public/<str:source>/<path:path>', downloads.public_file, name='public_download'),
    path('files/public/<str:source>/<path:path>', downloads.public_file, {'download': False}, name='public_file'),
    path('download/result/<path:path>', downloads.result_file, name='result_download'),
    path('files/result/<path:path>', downloads.result_file, {'download': False}, name='result_file'),
    path('download/export/', downloads.browser_export, name='browser_export'),
    path('download/service/<str:service>/<path:path>', downloads.service_download, name='service_download'),
    path('ping/', views.ping, name='ping'),
    path('whoami/', views.whoami, name='whoami'),

    # Genomics: genome files
    path('genomics/species/', views.genomics_species_list, name='genomics_species_list'),
    path('files/genome/species/', views.genome_species_list, name='genome_species_list'),
    path('files/genome/', views.genome_file_check, name='genome_file_check'),
    path('download/genome/', views.genome_file_download, name='genome_file_download'),

    # Geno-Syn: ancestral genome files
    path('genosyn/ancestral-genomes/', views.ancestral_genomes_list, name='ancestral_genomes_list'),
    path('files/ancestral/', views.ancestral_file_check, name='ancestral_file_check'),
    path('download/ancestral/', views.ancestral_file_download, name='ancestral_file_download'),


    # Geno-Syn: static JSON resources
    path('genosyn/collinear-kaks/', views.collinear_kaks_api, name='collinear_kaks_api'),
    path('genosyn/dotplots/', views.dotplots_api, name='dotplots_api'),

    # Multi-Omics: static JSON resources
    path('multiomics/pangenome/', views.pangenome_api, name='pangenome_api'),
    path('multiomics/transcriptome/samples/', views.transcriptome_samples_api, name='transcriptome_samples_api'),
    path('multiomics/transcriptome/sample/', views.transcriptome_sample_api, name='transcriptome_sample_api'),


    # Genomics: database-backed annotation resources
    path('genomics/interproscan/', views.interproscan_api, name='interproscan_api'),
    path('genomics/kegg/', views.kegg_api, name='kegg_api'),
    path('genomics/regulatory-proteins/', views.regulatory_proteins_api, name='regulatory_proteins_api'),
    path('genomics/m6a/', views.m6a_api, name='m6a_api'),
    path('genomics/duplication-types/', views.duplication_types_api, name='duplication_types_api'),

    # Multi-Omics: database-backed query resources
    path('multiomics/transcriptome/expression/', views.transcriptome_expression_api, name='transcriptome_expression_api'),
    path('multiomics/metabolomics/plant/', views.metabolomics_plant_api, name='metabolomics_plant_api'),
    path('multiomics/metabolomics/scent/', views.metabolomics_scent_api, name='metabolomics_scent_api'),

    # Genomics: remaining static resources
    path('genomics/transposable-elements/species/', views.transposable_elements_species_api, name='transposable_elements_species_api'),
    path('genomics/transposable-elements/', views.transposable_elements_api, name='transposable_elements_api'),

    # Geno-Syn: remaining database-backed resources
    path('genosyn/blocks/', views.genosyn_blocks_api, name='genosyn_blocks_api'),
    path('genosyn/block-details/', views.genosyn_block_details_api, name='genosyn_block_details_api'),
    path('genosyn/hierarchical-alignments/', views.hierarchical_alignments_api, name='hierarchical_alignments_api'),
    path('genosyn/hierarchical-genes/', views.hierarchical_genes_api, name='hierarchical_genes_api'),
    path('genosyn/evogenes/', views.evogenes_api, name='evogenes_api'),
    path('genosyn/orthologous/', views.orthologous_api, name='orthologous_api'),
    path('genosyn/gene-families/', views.gene_families_api, name='gene_families_api'),
    path('genosyn/rubber-genes/', views.rubber_genes_api, name='rubber_genes_api'),
    path('genosyn/inulin-genes/', views.inulin_genes_api, name='inulin_genes_api'),

]
