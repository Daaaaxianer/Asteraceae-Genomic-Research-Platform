#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author :yzj
# @FileName :urls.py
# @Time :2022/1/14 22:03

from django.contrib import admin
from django.urls import path, include
from tools.offline_views.BB_Dotter import views as bb_views
from tools.offline_views.block_number_count import views as block_number_count_views
from tools.offline_views.NG_KaKs_Cal import views as zu_ks_calculate_views
from tools.offline_views.Paleo_gene_identifer import views as paleo_gene_identifer_views
from tools.offline_views.Collinearity_generator import views as collinearity_generator_views
from tools.offline_views.Paleo_gene_RI import views as paleo_gene_ri_views
from tools.offline_views.Paleo_gene_RII import views as paleo_gene_rii_views
from tools.offline_views.P_index_calculator import views as p_index_calculator_views
from tools.offline_views.Draw_list_trees import views as draw_list_trees_views
from tools.offline_views.Genome_Mount_Rate_Calculator import views as genome_mount_rate_calculator_views
from tools.offline_views.GF_Circos import views as gf_circos_views
from tools.offline_views.Heatmap import views as heatmap_views
from tools.offline_views.Gene_structure import views as gene_structure_views
from tools.offline_views.Species_classification import views as species_classification_views
from tools.offline_views.BDI_deduplicator import views as bdi_deduplicator_views
from tools.offline_views.Subtree_extractor import views as subtree_extractor_views
from tools.offline_views.blast_match import views as blast_match_views
from tools.offline_views.codonw import views as codonw_views
from tools.offline_views.cpgfinder import views as cpgfinder_views
from tools.offline_views.meme import views as meme_views
from tools.offline_views.hmmer import views as hmmer_views
from tools.offline_views.pfam import views as pfam_views
from tools.offline_views.Interproscan import views as interproscan_views
from tools.offline_views.sequence_alignment import views as sequence_alignment_views
from tools.offline_views.fasttree import views as fasttree_views
from tools.offline_views.iTAK import views as iTAK_views
from tools import urls
from . import views

urlpatterns = [
    # 基因组同源性搜索 - 4
    path('all_tools', views.all_tools, name='all_tools_url'),
    path('tool-usage-record', views.tool_usage_record, name='tool_usage_record_url'),
    path('example-download/<str:tool_name>/<str:filename>', views.tool_example_download, name='tool_example_download_url'),
    path('blast', views.blast, name='blast_url'),
    path('blast_run', views.blast_run, name='blast_run_url'),
    path('diamond', views.diamond, name='diamond_url'),
    path('diamond_run', views.diamond_run, name='diamond_run_url'),
    path('blast_match', blast_match_views.blast_match, name='blast_match_url'),
    path('blast_match_run', blast_match_views.blast_match_run, name='blast_match_run_url'),
    path('sequenceserver', views.sequenceserver, name='sequenceserver_url'),
    path('sequence_fetch', views.sequence_fetch, name='sequence_fetch_url'),
    path('sequence_fetch_run', views.sequence_fetch_run, name='sequence_fetch_run_url'),

    # 共线性鉴定 - 6 = 10
    path('mcscanx', views.mcscanx, name='mcscanx_url'),
    path('mcscanx_run', views.mcscanx_run, name='mcscanx_run_url'),
    path('colinearscan', views.colinearscan, name='colinearscan_url'),
    path('colinearscan_run', views.colinearscan_run, name='colinearscan_run_url'),
    path('wgdimcs', views.wgdimcs, name='wgdimcs_url'),
    path('wgdimcs_run', views.wgdimcs_run, name='wgdimcs_run_url'),
    path('wgdimcs_status/<str:place>', views.wgdimcs_status, name='wgdimcs_status_url'),
    path('wgdimcs_result_download/<str:place>', views.wgdimcs_result_download, name='wgdimcs_result_download_url'),
    path('synvisio', views.synvisio, name='synvisio_url'),
    path('synvisio_run', views.synvisio_run, name='synvisio_run_url'),
    path('dupgen_finder', views.dupgen_finder, name='dupgen_finder_url'),
    path('dupgene_finder_tools', views.dupgene_finder_tools, name='dupgene_finder_tools_url'),
    path('dupgen_finder_run', views.dupgen_finder_run_tools, name='dupgen_finder_run_url'),
    path('block_number_count', block_number_count_views.block_number_count, name='block_number_count_url'),
    path('block_number_count_example_download', block_number_count_views.block_number_count_example_download, name='block_number_count_example_download_url'),
    path('block_number_count_run', block_number_count_views.block_number_count_run, name='block_number_count_run_url'),

    # 进化速率比较 - 4 = 14
    path('paraat', views.paraat, name='paraat_url'),
    path('paraat_run', views.paraat_run, name='paraat_run_url'),
    path('kaks_calculator', views.kaks_calculator, name='kaks_calculator_url'),
    path('kaks_calculator_run', views.kaks_calculator_run, name='kaks_calculator_run_url'),
    path('zu_ks_calculate', zu_ks_calculate_views.zu_ks_calculate, name='zu_ks_calculate_url'),
    path('zu_ks_calculate_run', zu_ks_calculate_views.zu_ks_calculate_run, name='zu_ks_calculate_run_url'),
    path('wgdikaks', views.wgdikaks, name='wgdikaks_url'),
    path('wgdikaks_run', views.wgdikaks_run, name='wgdikaks_run_url'),
    path('wgdikaks_status/<str:place>', views.wgdikaks_status, name='wgdikaks_status_url'),

    # 点图绘制 - 5 = 19
    path('zu_blast_dotplot', views.zu_blast_dotplot, name='zu_blast_dotplot_url'),
    path('zu_blast_dotplot_run', views.zu_blast_dotplot_run, name='zu_blast_dotplot_run_url'),
    path('zu_block_dotplot', bb_views.index, name='zu_block_dotplot_url'),
    path('zu_block_dotplot_url', bb_views.zu_block_dotplot_run, name='zu_block_dotplot'),
    path('zu_ks_dotplot', views.zu_ks_dotplot, name='zu_ks_dotplot_url'),
    path('zu_ks_dotplot_run', views.zu_ks_dotplot_run, name='zu_ks_dotplot_run_url'),
    path('wgdi_dotplot', views.wgdi_dotplot, name='wgdi_dotplot_url'),
    path('wgdi_dotplot_run', views.wgdi_dotplot_run, name='wgdi_dotplot_run_url'),
    path('wgdikaks_dot', views.wgdikaks_dot, name='wgdikaks_dot_url'),
    path('wgdikaks_dot_run', views.wgdikaks_dot_run, name='wgdikaks_dot_run_url'),
    path('wgdi_result_download/<str:tool_name>/<str:place>', views.wgdi_result_download, name='wgdi_result_download_url'),

    # 组-基因分馏 - 8 = 27
    path('zu_correspondence_mc_run', paleo_gene_identifer_views.zu_correspondence_mc_run, name='zu_correspondence_mc_run_url'),
    path('collinearity_generator', collinearity_generator_views.collinearity_generator, name='collinearity_generator_url'),
    path('collinearity_generator_run', collinearity_generator_views.collinearity_generator_run, name='collinearity_generator_run_url'),
    path('zu_retention', paleo_gene_ri_views.zu_retention_run, name='zu_retention_url'),
    path('zu_loss_run', paleo_gene_rii_views.zu_loss_run, name='zu_loss_run_url'),
    path('zu_loss', paleo_gene_rii_views.index, name='zu_loss_url'),
    path('zu_pindex', p_index_calculator_views.zu_pindex_run, name='zu_pindex_url'),
    path('draw_list_tree', draw_list_trees_views.draw_list_tree, name='draw_list_tree_url'),
    path('draw_list_tree_run', draw_list_trees_views.draw_list_tree_run, name='draw_list_tree_run_url'),
    path('wgdi_blockinfo', views.wgdi_blockinfo, name='wgdi_blockinfo_url'),
    path('wgdi_blockinfo_run', views.wgdi_blockinfo_run, name='wgdi_blockinfo_run_url'),
    path('wgdi_blockinfo_download/<str:place>', views.wgdi_blockinfo_download, name='wgdi_blockinfo_download_url'),
    path('wgdi_correspondence', views.wgdi_correspondence, name='wgdi_correspondence_url'),
    path('wgdi_correspondence_run', views.wgdi_correspondence_run, name='wgdi_correspondence_run_url'),
    path('wgdi_correspondence_status/<str:place>', views.wgdi_correspondence_status, name='wgdi_correspondence_status_url'),

    # 基因组相关 - 4 = 31   --- 没问题，不用测试了
    path('GC_calculation', views.GC_calculation, name='GC_calculation_url'),
    path('GC_calculation_run', views.GC_calculation_run, name='GC_calculation_run_url'),
    path('chromosome_length', views.chromosome_length, name='chromosome_length_url'),
    path('chromosome_length_run', views.chromosome_length_run, name='chromosome_length_run_url'),
    path('geme_cds_exon_counter', views.geme_cds_exon_counter, name='geme_cds_exon_counter_url'),
    path('geme_cds_exon_counter_run', views.geme_cds_exon_counter_run, name='geme_cds_exon_counter_run_url'),
    path('GenomeMountRateCalculator', genome_mount_rate_calculator_views.GenomeMountRateCalculator, name='GenomeMountRateCalculator_url'),
    path('GenomeMountRateCalculator_run', genome_mount_rate_calculator_views.GenomeMountRateCalculator_run, name='GenomeMountRateCalculator_run_url'),
    # path('wgdi_correspondence', views.wgdi_correspondence, name='wgdi_correspondence_url'),
    # path('wgdi_correspondence_run', views.wgdi_correspondence_run, name='wgdi_correspondence_run_url'),

    # 基因家族 - 12 = 43
    path('GF_ks_circos', gf_circos_views.GF_ks_circos, name='GF_ks_circos_url'),
    path('GF_ks_circos_run', gf_circos_views.GF_ks_circos_run, name='GF_ks_circos_run_url'),
    path('codonw', codonw_views.codonw, name='codonw_url'),
    path('codonw_run', codonw_views.codonw_run, name='codonw_run_url'),
    path('cpgfinder', cpgfinder_views.cpgfinder, name='cpgfinder_url'),
    path('cpgfinder_run', cpgfinder_views.cpgfinder_run, name='cpgfinder_run_url'),
    path('meme_suit', meme_views.meme_suit, name='meme_suit_url'),
    path('meme_suit_run', meme_views.meme_suit_run, name='meme_suit_run_url'),
    path('gsds', views.gsds, name='gsds_url'),
    path('hmmer', hmmer_views.hmmer, name='hmmer_url'),
    path('hmmer_run', hmmer_views.hmmer_run, name='hmmer_run_url'),
    path('pfam', pfam_views.pfam, name='pfam_url'),
    path('pfam_run', pfam_views.pfam_run, name='pfam_run_url'),
    path('interproscan', interproscan_views.interproscan, name='interproscan_url'),
    path('interproscan_run', interproscan_views.interproscan_run, name='interproscan_run_url'),
    path('interproscan_result', interproscan_views.interproscan_result, name='interproscan_result'),
    path('interproscan_download', interproscan_views.interproscan_download, name='interproscan_download'),
    path('sequence_alignment', sequence_alignment_views.sequence_alignment, name='sequence_alignment_url'),
    path('sequence_alignment_run', sequence_alignment_views.sequence_alignment_run, name='sequence_alignment_run_url'),
    path('fasttree', fasttree_views.fasttree, name='fasttree_url'),
    path('fasttree_run', fasttree_views.fasttree_run, name='fasttree_run_url'),
    path('iq_tree', views.iq_tree, name='iq_tree_url'),
    path('iq_tree_run', views.iq_tree_run, name='iq_tree_run_url'),
    path('iTAK', iTAK_views.iTAK, name='iTAK_url'),
    path('iTAK_run', iTAK_views.iTAK_run, name='iTAK_run_url'),
    path('phyml', views.phyml, name='phyml_url'),
    path('phyml_run', views.phyml_run, name='phyml_run_url'),

    # 绘图模块
    path('draw_heatmap', heatmap_views.draw_heatmap, name='draw_heatmap_url'),
    path('draw_heatmap_run', heatmap_views.draw_heatmap_run, name='draw_heatmap_run_url'),
    path('lollipop_chart', views.lollipop_chart, name='lollipop_chart_url'),
    path('lollipop_chart_run', views.lollipop_chart_run, name='lollipop_chart_run_url'),
    path('draw_gene_structure', gene_structure_views.draw_gene_structure, name='draw_gene_structure_url'),
    path('draw_gene_structure_run', gene_structure_views.draw_gene_structure_run, name='draw_gene_structure_run_url'),
    path('extract_chromosomes/', gene_structure_views.extract_chromosomes, name='extract_chromosomes_url'),

    # Other 工具 - 10 = 53
    path('circos', views.circos, name='circos_url'),
    path('species_classification', species_classification_views.species_classification, name='species_classification_url'),
    path('species_classification_run', species_classification_views.species_classification_run, name='species_classification_run_url'),
    path('sequence_screening', views.sequence_screening, name='sequence_screening_url'),
    path('sequence_screening_run', views.sequence_screening_run, name='sequence_screening_run_url'),
    path('formatTofasta', views.formatTofasta, name='formatTofasta_url'),
    path('formatTofasta_run', views.formatTofasta_run, name='formatTofasta_run_url'),
    path('find_replace', views.find_replace, name='find_replace_url'),
    path('find_replace_run', views.find_replace_run, name='find_replace_run_url'),
    path('duplicate_removal', bdi_deduplicator_views.duplicate_removal, name='quchong_url'),
    path('duplicate_removal_run', bdi_deduplicator_views.duplicate_removal_run, name='duplicate_removal_run_url'),
    path('extract_row', views.extract_row, name='extract_row_url'),
    path('extract_column_run', views.extract_column_run, name='extract_column_run_url'),
    path('file_merge', views.file_merge, name='file_merge_url'),
    path('file_merge_run', views.file_merge_run, name='file_merge_run_url'),
    path('deal_star', views.deal_star, name='deal_star_url'),
    path('deal_star_run', views.deal_star_run, name='deal_star_run_url'),
    path('subtree_extractor', subtree_extractor_views.subtree_extractor, name='subtree_extractor_url'),
    path('subtree_extractor_run', subtree_extractor_views.subtree_extractor_run, name='subtree_extractor_run_url'),

    # 圈图、jbrowse - 2 = 55
    path('jbrowse', views.jbrowse, name='jbrowse_url'),
    path('docker', views.docker, name='docker_url'),

    ## Caculation Tools
    path('bio_tools/web_tools/calculation/bdi_finder/', views.bdi_finder_view, name='bdi_finder_url'),
    path('bio_tools/web_tools/calculation/bdi_extractor/', views.bdi_extractor_view, name='bdi_extractor_url'),
    path('bio_tools/web_tools/calculation/bdi_combiner/', views.bdi_combiner_view, name='bdi_combiner_url'),
    path('bio_tools/web_tools/calculation/bdi_deduplicator/', views.bdi_deduplicator_view, name='bdi_deduplicator_url'),
    path('bio_tools/web_tools/calculation/ss_extractor/', views.sequence_screening_view, name='sequence_screening_url'),
    path('bio_tools/web_tools/calculation/saf_converter/', views.saf_converter_view, name='saf_converter_url'),
    path('bio_tools/web_tools/calculation/bbm_extraction/', views.bbm_extraction_view, name='bbm_extraction_url'),
    path('bio_tools/web_tools/calculation/deal_stars/', views.deal_stars_view, name='deal_stars_url'),
    path('bio_tools/web_tools/calculation/gene_stats/', views.gene_stats_view, name='gene_stats_url'),
    path('bio_tools/web_tools/phylo/lollipop/', views.lollipop_chart_view, name='lollipop_chart_url'),
    path('bio_tools/web_tools/phylo/iq_tree/', views.iq_tree_view, name='iq_tree_url'),
    path('bio_tools/web_tools/phylo/ks_distriplot/', views.ks_distriplot_view, name='ks_distriplot_url'),
    path('bio_tools/web_tools/homology/cds2geno_dotplot/', views.cds2geno_dotplot_view, name='cds2geno_dotplot_url'),
    path('bio_tools/web_tools/synteny/mga_circos/', views.mga_circos_view, name='mga_circos_url'),

    path('zu_ks_circos', views.zu_ks_circos, name='zu_ks_circos_url'),
    path('index_email', views.index_email, name='index_email_url'),

    # karyotype_html 文件夹内的内容信息
    path('f_blast_html', views.f_blast_html, name='f_blast_url_html'),
    path('colinearscan_html', views.colinearscan_html, name='colinearscan_url_html'),
    path('synvisio_html', views.synvisio_html, name='synvisio_url_html'),
    path('zu_correspondence_mc', paleo_gene_identifer_views.zu_correspondence_mc_html, name='zu_correspondence_mc_url'),
    # 比较特殊
    path('karyotype_in_html', views.karyotype_in_html, name='karyotype_in_url_html'),

    # path('karyotype/Step1.html', views.Step1, name='Step1_url'),
    # path('blast_results', views.blast_results_run, name='blast_results'),
    # path('dotplot_run', views.dotplot_run, name='dotplot_run_url'),
    # path('karyotype_in', views.karyotype_in, name='karyotype_in_url'),

    # AKRUP
    path('akrup_run_blast', views.akrup_run_blast, name='akrup_run_blast_url'),
    path('akrup_run_blast_run', views.akrup_run_blast_run, name='akrup_run_blast_run_url'),
    # path('hmmer_run', views.hmmer_run, name='hmmer_run_url'),
    # path('cpgfinder_run', views.cpgfinder_run, name='cpgfinder_run_url'),
    # path('sequence_alignment_run', views.sequence_alignment_run, name='sequence_alignment_run_url'),
    # path('phyml_run', views.phyml_run, name='phyml_run_url'),
    # path('codonw_run', views.codonw_run, name='codonw_run_url'),
    # path('blast_results', views.blast_results_run, name='blast_results'),

    path('zu_diushi', views.zu_diushi, name='zu_diushi_url'),
    path('f_blast', views.f_blast, name='f_blast_url'),


    # Analysis Pipelines
    path('pipelines/wgd_identification', views.pipeline_wgd_identification, name='pipeline_wgd_identification_url'),
    path('pipelines/aags_reconstruction', views.pipeline_aags_reconstruction, name='pipeline_aags_reconstruction_url'),
    path('pipelines/trait_associated', views.pipeline_trait_associated, name='pipeline_trait_associated_url'),
    path('pipelines/go_annotation', views.pipeline_go_annotation, name='pipeline_go_annotation_url'),
    path('pipelines/kegg_annotation', views.pipeline_kegg_annotation, name='pipeline_kegg_annotation_url'),
    path('pipelines/identification_of_rps', views.pipeline_identification_of_rps, name='pipeline_identification_of_rps_url'),
    path('pipelines/m6a_identification', views.pipeline_m6a_identification, name='pipeline_m6a_identification_url'),
    path('pipelines/gene_duplication_types', views.pipeline_gene_duplication_types, name='pipeline_gene_duplication_types_url'),
    path('pipelines/transposable_elements', views.pipeline_transposable_elements, name='pipeline_transposable_elements_url'),


    path('encyclopedia', views.encyclopedia, name='encyclopedia_url'),
    path('agroecology/', views.agroecology, name='agroecology_url'),
]
