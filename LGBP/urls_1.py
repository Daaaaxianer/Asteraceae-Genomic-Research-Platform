#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author        : yuzijian
# @Email         : yuzijian1010@163.com
# @FileName :urls.py
# @Time :2022/1/14 22:03

"""LGBP URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from tools import urls, views
from django.conf import settings
from django.conf.urls.static import static

from django.shortcuts import redirect

def redirect_karyotype(request, old_name):
    # 将连字符转换为下划线
    new_name = old_name.replace('-', '_')
    return redirect(f'/browse/karyotype/{new_name}')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index),
    # path('all_tools', views.all_tools, name='all_tools_url'),
    path('index', views.index, name='index_url'),
    path('tools', views.tools, name='tools_url'),
    path('browse', views.Browse, name='Browse_url'),
    path('browse/', include('browse.urls')),
    path('download/', views.download_file_view, name='download_file'),
    path('sp_tree', views.sp_tree_chart, name='sp_tree_chart_url'),
    path('gene_replication_type', views.gene_replication_type, name='gene_replication_type_url'),
    path('p_index', views.p_index, name='p_index_url'),
    path('gene_annotation_chart', views.gene_annotation_chart, name='gene_annotation_chart_url'),
    path('function_gene_chart', views.function_gene_chart, name='function_gene_chart_url'),
    path('transcription_factor_chart', views.transcription_factor_chart, name='transcription_factor_chart_url'),
    path('m6a_chart', views.m6a_chart, name='m6A_chart_url'),
    path('species_data', views.species_data, name='species_data_url'),
    path('sp_introduce', views.sp_introduce, name='sp_introduce_url'),
    path('sp_introduce2', views.sp_introduce2, name='sp_introduce2_url'),
    path('sp_introduce3', views.sp_introduce3, name='sp_introduce3_url'),
    path('database', views.database, name='database_url'),
    path('submit', views.submit, name='submit_url'),
    path('Referenced_our', views.Referenced_our, name='Referenced_our_url'),
    path('documentation', views.documentation, name='documentation_url'),
    path('documentation_tools', views.documentation_tools, name='documentation_tools_url'),
    path('software_tools', views.software_tools, name='software_tools_url'),
    path('contact', views.contact, name='contact_url'),
    path('pan_genome', views.pan_genome, name='pan_genome_url'),
    path('karyotype/<str:old_name>', redirect_karyotype),
    path('gfca', views.gfca, name='gfca_url'),
    path('karyotype', views.karyotype, name='karyotype_url'),
    path('database', views.database, name='database_url'),
    path('about', views.about, name='about_url'),
    path('references', views.references, name='references_url'),
    path('new', views.new, name='new_url'),
    path('statistics', views.statistics, name='statistics_url'),
    path('user_manual', views.user_manual, name='user_manual_url'),
    path('article', views.article, name='article_url'),
    path('genome_information', views.genome_information, name='genome_information_url'),
    path('metabolomics_plant', views.metabolomics_plant, name='metabolomics_plant_url'),
    path('metabolomics_scent', views.metabolomics_scent, name='metabolomics_scent_url'),
    path('JBrowse_index', views.JBrowse_index, name='JBrowse_index_url'),
    path('successful', views.successful, name='successful_url'),
    path('index_email', views.index_email, name='index_email_url'),
    path('tools/', include('tools.urls')),
    # path('browse/', include('browse.urls')),
    # introduce
    path("common_pests", views.common_pests, name="common_pests_url"),
    path("diseases", views.diseases, name="diseases_url"),
    path("ecology", views.ecology, name="ecology_url"),
    path('economic_value', views.economic_value, name="economic_value_url"),
    path("method_planting", views.method_planting, name="method_planting_url"),
    path('search_fabaceae', views.search_fabaceae_taxa, name='search_fabaceae_taxa_url'),
    path('get_tribes/', views.get_tribes, name='get_tribes_url'),
    path('get_genera/', views.get_genera, name='get_genera_url'),
    path('load_genera/', views.load_genera, name='load_genera_url'),
    path('transcriptome2', views.transcriptome2, name='transcriptome2_url'),
    path('chart', views.chart, name='chart_url'),
    path('m6a_chart', views.m6a_chart, name='m6a_chart_url'),
    path('transcription_regulation_chart', views.transcription_factor_chart, name='TR_chart_url'),
    path('epigenetics_chromatin_chart', views.chart, name='ECR_chart_url'),
    path('metabolism_related_chart', views.chart, name='MR_chart_url'),
    path('transposable_elements_chart', views.transposable_elements_view, name='TE_chart_url'),
    path('protein_synthesis_modification_chart', views.chart, name='PSM_chart_url'),
    path('development_differentiation_chart', views.chart, name='DD_chart_url'),
    path('hormone_response_signaling_chart', views.chart, name='HRS_chart_url'),
    path('cell_wall_membrane_chart', views.chart, name='CWCM_chart_url'),
    path('cell_structure_cycle_chart', views.chart, name='CSCC_chart_url'),
    path('coercion_response_defense_chart', views.chart, name='CRD_chart_url'),
    path('signal_transduction_kinase_chart', views.chart, name='STK_chart_url'),
    path('regulatory_proteins_chart', views.regulatory_proteins_view, name='RPS_chart_url'),
    path('pathway_chart', views.chart, name='Pathway_url'),
    path('m6A_gene_chart/', views.m6A_gene_chart_view, name='m6A_gene_chart_url'),
    path('transposable_elements/', views.transposable_elements_view, name='transposable_elements_url'),
    path('regulatory_proteins/', views.regulatory_proteins_view, name='regulatory_proteins_url'),
    path('floral_morphology/', views.floral_morphology_view, name='floral_morphology_url'),
    path('terpenoid_biosynthesis/', views.terpenoid_biosynthesis_view, name='terpenoid_biosynthesis_url'),
    path('heat_stress/', views.heat_stress_view, name='heat_stress_url'),
    path('salt_resistance/', views.salt_resistance_view, name='salt_resistance_url'),
    path('drought_tolerance/', views.drought_tolerance_view, name='drought_tolerance_url'),
    path('rubber_synthesis/', views.rubber_synthesis_view, name='rubber_synthesis_url'),
    path('inulin_related_family/', views.inulin_related_family_view, name='inulin_related_family_url'),
    path('mgas_eupl_reference/', views.mgas_eupl_ref_view, name='mgas_eupl_ref_url'),
    path('mgas_vitis_reference/', views.mgas_vitis_ref_view, name='mgas_vitis_ref_url'),
    path('mgas_arctium_reference/', views.mgas_arctium_ref_view, name='mgas_arctium_ref_url'),
    path('mgas_helianthus_reference/', views.mgas_helianthus_ref_view, name='mgas_helianthus_ref_url'),
    path('hierarchical_alignments_eupl', views.hierarchical_alignments_eupl, name='hierarchical_alignments_eupl_url'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
