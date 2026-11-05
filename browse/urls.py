#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author        : yuzijian
# @Email         : yuzijian1010@163.com
# @FileName :urls.py
# @Time :2022/1/14 22:03

from django.contrib import admin
from django.urls import path, include
from tools import urls
from . import views
from django.conf import settings
from django.conf.urls.static import static
import os
from django.urls import path
from . import views


urlpatterns = [
    path('genome', views.genome, name='genome_url'),
    path('genome/scaffolds', views.genome_scaffolds, name='genome_scaffolds_url'),
    path('gene_<str:geneid>/', views.gene_detail, name='gene_detail'),
    path('dupgen_finders', views.dupgen_finders, name='dupgen_finders_url'),
    path('dupgen_job_status/<str:job_id>', views.dupgen_job_status, name='dupgen_job_status_url'),
    path('dupgen_job_download/<str:job_id>', views.dupgen_job_download, name='dupgen_job_download_url'),
    path('dupgen_job_blast_download/<str:job_id>', views.dupgen_job_blast_download, name='dupgen_job_blast_download_url'),
    path('dupgen_job_result/<str:job_id>', views.dupgen_job_result, name='dupgen_job_result_url'),
    path('pvu_syntenic', views.pvu_syntenic, name='pvu_syntenic_url'),
    path('Eupl_syntenic', views.Eupl_syntenic, name='Eupl_syntenic_url'),

    path('ECH_event', views.ECH_event, name='ECH_event_url'),
    path('PCT_event', views.PCT_event, name='PCT_event_url'),
    path('CCT_event', views.CCT_event, name='CCT_event_url'),
    path('LSH_event', views.LSH_event, name='LSH_event_url'),
    path('GST_event', views.GST_event, name='GST_event_url'),
    path('B_WGD_event', views.B_WGD_event, name='B_WGD_event_url'),
    path('hybridization_Genes', views.hybridization_Genes, name='hybridization_Genes_url'),
    # hybridization_Genes
    path('karyotype', views.karyotype, name='karyotype_url'),


    # 花青素的基因
    path('anthocyanin_genes_index1', views.anthocyanin_genes_index1, name='anthocyanin_genes_index_url1'),
    path('anthocyanin_genes_index2', views.anthocyanin_genes_index2, name='anthocyanin_genes_index_url2'),
    path('anthocyanin_genes_index3', views.anthocyanin_genes_index3, name='anthocyanin_genes_index_url3'),
    # 花青素的基因---页面
    path('Anthocyaningenes/<str:title>/', views.Anthocyaningenes, name='Anthocyaningenes'),

    path('mc_result', views.mc_result, name='mc_result_url'),
    path('mc_result_run/<str:title>/', views.mc_result_run, name='mc_result_run_url'),

    # 生长素基因
    path('Auxin_genes_index1', views.Auxin_genes_index1, name='Auxin_genes_index_url1'),
    path('Auxin_genes_index2', views.Auxin_genes_index2, name='Auxin_genes_index_url2'),
    path('Auxin_genes_index3', views.Auxin_genes_index3, name='Auxin_genes_index_url3'),
    # 生长素基因---页面
    path('Auxin/<str:title>/', views.Auxin, name='Auxin'),

    # 花发育 基因
    path('flower_development_index1', views.flower_development_index1, name='flower_development_index_url1'),
    path('flower_development_index2', views.flower_development_index2, name='flower_development_index_url2'),
    path('flower_development_index3', views.flower_development_index3, name='flower_development_index_url3'),
    # 花发育 基因---页面
    path('flower_development/<str:title>/', views.flower_development, name='flower_development'),

    # 待定花期 基因
    path('pending_flowler_time_index1', views.pending_flowler_time_index1, name='pending_flowler_time_index_url1'),
    path('pending_flowler_time_index2', views.pending_flowler_time_index2, name='pending_flowler_time_index_url2'),
    path('pending_flowler_time_index3', views.pending_flowler_time_index3, name='pending_flowler_time_index_url3'),
    # 待定花期 基因---页面
    path('pending_flowler_time/<str:title>/', views.pending_flowler_time, name='pending_flowler_time'),

    # 开花时间 基因
    path('flowler_time_index1', views.flowler_time_index1, name='flowler_time_index_url1'),
    path('flowler_time_index2', views.flowler_time_index2, name='flowler_time_index_url2'),
    path('flowler_time_index3', views.flowler_time_index3, name='flowler_time_index_url3'),
    # 开花时间 基因---页面
    path('flowler_time/<str:title>/', views.flowler_time, name='flowler_time'),

    # TF 转录因子基因家族-相关基因 --- 页面
    path('Resistencegenes_genes', views.Resistencegenes_genes_index, name='Resistencegenes_genes_index_url'),
    path('Resistencegenes_genes/<str:title>/', views.Resistencegenes_genes, name='Resistencegenes_genes'),

    # 脂肪酸-相关基因 --- 页面
    path('Fatty_acid_genes', views.Fatty_acid_genes_index, name='Fatty_acid_genes_index_url'),
    path('Fatty_acid_genes/<str:title>/', views.Fatty_acid_genes, name='Fatty_acid_genes'),

    # 固氮-相关基因 --- 页面
    path('Nitrogen_fixation_genes', views.Nitrogen_fixation_genes_index, name='Nitrogen_fixation_genes_index_url'),
    path('Nitrogen_fixation_genes/<str:title>/', views.Nitrogen_fixation_genes, name='Nitrogen_fixation_genes'),

    # m6a-Wirters 相关基因 --- 页面
    path('m6a_wirters_genes', views.m6a_wirters_genes_index, name='m6a_wirters_genes_index_url'),
    path('m6a_wirters_genes/<str:title>/', views.m6a_wirters_genes, name='m6a_wirters_genes'),
    # m6a-Wirters 相关基因 --- 页面
    path('m6a_readers_genes', views.m6a_readers_genes, name='m6a_readers_genes_url'),
    # m6a-Erasers 相关基因 --- 页面
    path('m6a_erasers_genes', views.m6a_erasers_genes, name='m6a_erasers_genes_url'),

    # m6a-Wirters 相关基因 --- 页面
    path('L_pathway', views.L_pathway_index, name='L_pathway_index_url'),
    path('L_pathway/<str:title>/', views.L_pathway, name='L_pathway'),

    # ncRNA 12 个
    path('ncRNA', views.ncRNA, name='ncRNA_url'),
    path('ncRNA_run', views.ncRNA_run, name='ncRNA_run_url'),

    # TE 12 个
    path('TE_index1', views.TE_index1, name='TE_index_url1'),
    path('TE_index2', views.TE_index2, name='TE_index_url2'),
    path('TE_index3', views.TE_index3, name='TE_index_url3'),
    path('TE/<str:sp_name>', views.TE_sp, name='TE'),
    path('TE_type/<str:sp_name>/<str:type>', views.TE_type, name='TE_type'),
    # gene type
    path('collinear_kaks', views.collinear_kaks, name='collinear_kaks_url'),
    path('collinear_kaks/data/', views.collinear_kaks_data, name='collinear_kaks_data_url'),
    path('collinear_kaks_file', views.collinear_kaks_file, name='collinear_kaks_file_url'),
    path('collinear_kaks_run', views.collinear_kaks_run, name='collinear_kaks_run_url'),
    path('kegg_index', views.kegg_index, name='kegg_index_url'),
    path('kegg_job_status/<str:job_id>', views.kegg_job_status, name='kegg_job_status_url'),
    path('kegg_job_download/<str:job_id>', views.kegg_job_download, name='kegg_job_download_url'),
    path('kegg_job_blast_download/<str:job_id>', views.kegg_job_blast_download, name='kegg_job_blast_download_url'),
    path('kegg_job_result/<str:job_id>', views.kegg_job_result, name='kegg_job_result_url'),
    path('geneExpression', views.geneExpression, name='geneExpression_url'),
    path('transcriptome', views.transcriptome, name='transcriptome_url'),
    path('transcriptome_run', views.transcriptome_run, name='transcriptome_run_url'),
    path('transcriptome_run/data/', views.transcriptome_run_data, name='transcriptome_run_data_url'),
    path('function_gene', views.function_gene, name='function_gene_url'),
    path('function_gene_job_status/<str:job_id>', views.function_gene_job_status, name='function_gene_job_status_url'),
    path('function_gene_job_download/<str:job_id>', views.function_gene_job_download, name='function_gene_job_download_url'),
    path('function_gene_job_blast_download/<str:job_id>', views.function_gene_job_blast_download, name='function_gene_job_blast_download_url'),
    path('function_gene_job_result/<str:job_id>', views.function_gene_job_result, name='function_gene_job_result_url'),
    path('build-ortho-tree/', views.build_ortho_tree, name='build_ortho_tree'),
    path('rubber_gene', views.rubber_gene, name='rubber_gene_url'),
    path('inulin_gene', views.inulin_gene, name='inulin_gene_url'),
    path('draw_tree', views.draw_tree, name='draw_tree'),
    path('tree_img', views.tree_img, name='tree_img'),
    path('function_gene_v2', views.function_gene_v2, name='function_gene_v2_url'),
    path('TF_genes', views.TF_genes_index, name='TF_genes_index_url'),
    path('TF_genes_run_index', views.TF_genes_run_index, name='TF_genes_run_index_url'),
    path('TF_genes/<str:title>/', views.TF_genes, name='TF_genes'),
    path('TF_gene_v2', views.TF_gene_v2, name='TF_gene_v2_url'),
    path('tf/<str:TF_name>/', views.TF_gene_v2, name='TF_gene_v2_select_function'),
    path('m6A_gene', views.m6A_gene, name='m6A_gene_url'),
    path('orthologous', views.orthologous, name='orthologous_url'),
    path('hierarchical_alignments_Hean', views.hierarchical_alignments_Hean, name='hierarchical_alignments_Hean_url'),
    path('hierarchical_alignments_Lssa_all', views.hierarchical_alignments_Lssa_all, name='hierarchical_alignments_Lssa_all_url'),
    path('hierarchical_alignments_Vivi', views.hierarchical_alignments_Vivi, name='hierarchical_alignments_Vivi_url'),
    path('hierarchical_alignments_Eupl', views.hierarchical_alignments_Eupl, name='hierarchical_alignments_Eupl_url'),
    path('hierarchical_alignments/<str:reference>/data/', views.hierarchical_alignments_table_data, name='hierarchical_alignments_table_data'),
    # Compatibility for cached/older pages that request data under the page URL.
    path('hierarchical_alignments_Hean/data/', views.hierarchical_alignments_table_data, {'reference': 'Hean'}, name='hierarchical_alignments_Hean_table_data'),
    path('hierarchical_alignments_Lssa_all/data/', views.hierarchical_alignments_table_data, {'reference': 'Lssa_all'}, name='hierarchical_alignments_Lssa_all_table_data'),
    path('hierarchical_alignments_Vivi/data/', views.hierarchical_alignments_table_data, {'reference': 'Vivi'}, name='hierarchical_alignments_Vivi_table_data'),
    path('hierarchical_alignments_Eupl/data/', views.hierarchical_alignments_table_data, {'reference': 'Eupl'}, name='hierarchical_alignments_Eupl_table_data'),
    path('event_gene', views.event_gene, name='event_gene_url'),
    path('te_information', views.te_information, name='te_information_url'),
    path('te_information/page<int:page>/', views.te_information, name='te_information_with_page'),
    # path('gene/<str:geneid>/', views.gene_detail, name='gene_detail'),
    path('collinear_dotplot', views.collinear_dotplot, name='collinear_dotplot_url'),
    path('chromosome_rearrangement', views.chromosome_rearrangement, name='chromosome_rearrangement_url'),
    path('ancestral_chromosome', views.ancestral_chromosome, name='ancestral_chromosome_url'),
    path('ancestral_chromosome_run/<str:c>', views.ancestral_chromosome_run, name='ancestral_chromosome_run'),
    path('ancestral_ks_dotplot', views.ancestral_ks_dotplot, name='ancestral_ks_dotplot_url'),
    path('ancestral_ks_dotplot_status/<str:job_id>', views.ancestral_ks_dotplot_status, name='ancestral_ks_dotplot_status_url'),
    path('ancestral_ks_dotplot_download/<str:job_id>', views.ancestral_ks_dotplot_download, name='ancestral_ks_dotplot_download_url'),
    path('dotplot', views.dotplot, name='dotplot_url'),
    path('dotplot/data/', views.dotplot_data, name='dotplot_data_url'),
    path('genome_synteny_viewer/<str:sp_data_1>_<str:sp_data_2>/', views.genome_synteny_viewer, name='genome_synteny_viewer'),
    path('draw_ks_peak', views.draw_ks_peak, name='draw_ks_peak'),
    path('ks_peak_img', views.ks_peak_img, name='ks_peak_img'),
    path('draw_ks_circos', views.draw_ks_circos, name='draw_ks_circos'),
    path('ks_circos_img', views.ks_circos_img, name='ks_circos_img'),
    path('kegg', views.kegg, name='kegg_url'),
    path('paper', views.paper, name='paper_url'),
    path('Pfam_index', views.Pfam_index, name='pfam_index_url'),
    path('pfam_index_run', views.pfam_index_run, name='pfam_index_run_url'),
    path('interproscan_index', views.interproscan_index, name='interproscan_index_url'),
    path('interproscan_job_status/<str:job_id>', views.interproscan_job_status, name='interproscan_job_status_url'),
    path('interproscan_job_download/<str:job_id>', views.interproscan_job_download, name='interproscan_job_download_url'),
    path('interproscan_job_blast_download/<str:job_id>', views.interproscan_job_blast_download, name='interproscan_job_blast_download_url'),
    path('interproscan_job_result/<str:job_id>', views.interproscan_job_result, name='interproscan_job_result_url'),
    path('gene_family', views.gene_family, name='gene_family_url'),
    path('search_api', views.search_api, name='search_api_url'),
    path('vvi_syntenic', views.vvi_syntenic, name='vvi_syntenic_url'),
    path('ACH_event', views.ACH_event, name='ACH_event_url'),
    path('AST_event', views.AST_event, name='AST_event_url'),
    path('Metabolomics', views.Metabolomics, name='Metabolomics_url'),
    path('karyotype/Deinandra_increscens', views.Deinandra_increscens, name='Deinandra_increscens_url'),
    path('karyotype/Taraxacum_mongolicum', views.Taraxacum_mongolicum, name='Taraxacum_mongolicum_url'),
    path('karyotype/ASAK_III', views.ASAK_III, name='ASAK_III_url'),
    path('karyotype/Saussurea_involucrata', views.Saussurea_involucrata, name='Saussurea_involucrata_url'),
    path('karyotype/CAAK_II', views.CAAK_II, name='CAAK_II_url'),
    path('karyotype/AAK_II', views.AAK_II, name='AAK_II_url'),
    path('karyotype/ASAK_XIII', views.ASAK_XIII, name='ASAK_XIII_url'),
    path('karyotype/Stevia_rebaudiana', views.Stevia_rebaudiana, name='Stevia_rebaudiana_url'),
    path('karyotype/ASAK_VIII', views.ASAK_VIII, name='ASAK_VIII_url'),
    path('karyotype/ASAK_IV', views.ASAK_IV, name='ASAK_IV_url'),
    path('karyotype/Erigeron_canadensis', views.Erigeron_canadensis, name='Erigeron_canadensis_url'),
    path('karyotype/CAAK_I', views.CAAK_I, name='CAAK_I_url'),
    path('karyotype/ASAK_XI', views.ASAK_XI, name='ASAK_XI_url'),
    path('karyotype/Senecio_squalidus', views.Senecio_squalidus, name='Senecio_squalidus_url'),
    path('karyotype/Bidens_alba', views.Bidens_alba, name='Bidens_alba_url'),
    path('karyotype/ASAK_XVII', views.ASAK_XVII, name='ASAK_XVII_url'),
    path('karyotype/Lactuca_sativa', views.Lactuca_sativa, name='Lactuca_sativa_url'),
    path('karyotype/Chrysanthemum_lavandulifolium', views.Chrysanthemum_lavandulifolium,name='Chrysanthemum_lavandulifolium_url'),
    path('karyotype/Cosmos_bipinnatus', views.Cosmos_bipinnatus, name='Cosmos_bipinnatus_url'),
    path('karyotype/ASAK_VII', views.ASAK_VII, name='ASAK_VII_url'),
    path('karyotype/ASAK_VI', views.ASAK_VI, name='ASAK_VI_url'),
    path('karyotype/ASAK_XIX', views.ASAK_XIX, name='ASAK_XIX_url'),
    path('karyotype/Solidago_canadensis', views.Solidago_canadensis, name='Solidago_canadensis_url'),
    path('karyotype/Logfia_minima', views.Logfia_minima, name='Logfia_minima_url'),
    path('karyotype/ASAK_X', views.ASAK_X, name='ASAK_X_url'),
    path('karyotype/Arctium_lappa', views.Arctium_lappa, name='Arctium_lappa_url'),
    path('karyotype/Smallanthus_sonchifolius', views.Smallanthus_sonchifolius, name='Smallanthus_sonchifolius_url'),
    path('karyotype/Solidago_caesia', views.Solidago_caesia, name='Solidago_caesia_url'),
    path('karyotype/ASAK_II', views.ASAK_II, name='ASAK_II_url'),
    path('karyotype/Flaveria_linearis', views.Flaveria_linearis, name='Flaveria_linearis_url'),
    path('karyotype/Pseudognaphalium_luteoalbum', views.Pseudognaphalium_luteoalbum,name='Pseudognaphalium_luteoalbum_url'),
    path('karyotype/ASAK_XII', views.ASAK_XII, name='ASAK_XII_url'),
    path('karyotype/Cynara_cardunculus', views.Cynara_cardunculus, name='Cynara_cardunculus_url'),
    path('karyotype/AAK_I', views.AAK_I, name='AAK_I_url'),
    path('karyotype/ASAK_XVI', views.ASAK_XVI, name='ASAK_XVI_url'),
    path('karyotype/CAAK_III', views.CAAK_III, name='CAAK_III_url'),
    path('karyotype/Pulicaria_dysenterica', views.Pulicaria_dysenterica, name='Pulicaria_dysenterica_url'),
    path('karyotype/ASAK_XV', views.ASAK_XV, name='ASAK_XV_url'),
    path('karyotype/Tagetes_erecta', views.Tagetes_erecta, name='Tagetes_erecta_url'),
    path('karyotype/ASAK_XVIII', views.ASAK_XVIII, name='ASAK_XVIII_url'),
    path('karyotype/Helianthus_annuus', views.Helianthus_annuus, name='Helianthus_annuus_url'),
    path('karyotype/ASAK_IX', views.ASAK_IX, name='ASAK_IX_url'),
    path('karyotype/CAAK_IV', views.CAAK_IV, name='CAAK_IV_url'),
    path('karyotype/Carthamus_tinctorius', views.Carthamus_tinctorius, name='Carthamus_tinctorius_url'),
    path('karyotype/ASAK_I', views.ASAK_I, name='ASAK_I_url'),
    path('karyotype/Cichorium_intybus', views.Cichorium_intybus, name='Cichorium_intybus_url'),
    path('karyotype/Glebionis_coronaria', views.Glebionis_coronaria, name='Glebionis_coronaria_url'),
    path('karyotype/ACAK', views.ACAK, name='ACAK_url'),
    path('karyotype/ASAK_V', views.ASAK_V, name='ASAK_V_url'),
    path('karyotype/Dahlia_pinnata', views.Dahlia_pinnata, name='Dahlia_pinnata_url'),
    path('karyotype/ASAK_XIV', views.ASAK_XIV, name='ASAK_XIV_url'),
    path('karyotype/CIAK_II', views.CIAK_II, name='CIAK_II_url'),
    path('karyotype/Centaurea_solstitialis', views.Centaurea_solstitialis, name='Centaurea_solstitialis_url'),
    path('karyotype/CIAK_I', views.CIAK_I, name='CIAK_I_url'),
    path('karyotype/Mikania_micrantha', views.Mikania_micrantha, name='Mikania_micrantha_url'),
    path('karyotype/Ambrosia_trifida', views.Ambrosia_trifida, name='Ambrosia_trifida_url'),
    # Keep this catch-all route last so it does not swallow specific browse URLs.
    path('<str:function_name>/', views.function_gene_v2, name='select_function'),

]

