#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author        : yuzijian
# @Email         : yuzijian1010@163.com
# @FileName :urls.py
# @Time :2022/1/14 22:03

import os
import re
import sys
import glob
import json
import csv
import html
import time
import uuid
import base64
import mimetypes
import subprocess
import threading
from urllib.parse import quote, unquote
import numpy as np
import zipfile
import pandas as pd
from io import BytesIO

from LGBP import settings
from LGBP.tools import *
from functools import reduce
from django.db.models import Q
import matplotlib.pyplot as plt
from multiprocessing import Pool
from django.db import connection, close_old_connections
import plotly.graph_objects as go
from django.shortcuts import render
from scipy.stats import gaussian_kde
from wsgiref.util import FileWrapper
from django.http import JsonResponse
from django.http import HttpResponse
from django.http import FileResponse
# from .models import CollinearBlockPairs
from django.http import StreamingHttpResponse
from django.template.loader import render_to_string

from tools.views import get_gene_ids, compile_gene_info, extract_sequences_by_id
# from .models import HierarchicalAlignment_Hean, HierarchicalGene_Hean, HierarchicalAlignment_Eupl, HierarchicalGene_Eupl,HierarchicalAlignment_Lssa_all,HierarchicalGene_Lssa_all,HierarchicalAlignment_Lssa_part,HierarchicalGene_Lssa_part,HierarchicalAlignment_Vivi,HierarchicalGene_Vivi
from .models import HierarchicalAlignment_Eupl, HierarchicalAlignment_Hean, HierarchicalAlignment_Vivi, HierarchicalAlignment_Lssa_all, HierarchicalGene
from django.urls import path, reverse
from . import views

path_get = os.getcwd()

INTERPROSCAN_SPECIES = (
    'Aann', 'Aary', 'Amar', 'Amtr', 'Arla', 'Armi', 'Artr', 'Bial', 'Busi',
    'Ccar', 'Ceso', 'Chla', 'Chma', 'Chmo', 'Chna', 'Cich', 'Cien', 'Cind',
    'Cobi', 'Cpa', 'Cati', 'Dapi', 'Desu', 'Ecan', 'Enbr', 'Eupl', 'Fbi',
    'Fbr', 'Ffl', 'Fli', 'Fra', 'Fro', 'Fso', 'Ftr', 'Gehy', 'Glco', 'Hean',
    'Hetu', 'Heub', 'Laca', 'Lomi', 'Lssa', 'Mimi', 'Nenu', 'Nin', 'Pin',
    'Pdy', 'Pslu', 'Sain', 'Scae', 'Sesq', 'Smso', 'Soca', 'Stre', 'Taer',
    'Tako', 'Tamo', 'Tesi', 'Vivi',
)

ALL_INTERPROSCAN_SPECIES_VALUE = 'ALL_SPECIES'
INTERPROSCAN_RESULT_LIMIT = 5000
INTERPROSCAN_ALL_SPECIES_BLAST_MAX_TARGETS = 50000
INTERPROSCAN_FALLBACK_SPECIES_BLAST_MAX_TARGETS = 1000
KEGG_RESULT_LIMIT = 5000
KEGG_ALL_SPECIES_BLAST_MAX_TARGETS = 50000
KEGG_FALLBACK_SPECIES_BLAST_MAX_TARGETS = 1000
DUPGEN_ALL_SPECIES_BLAST_MAX_TARGETS = 50000
DUPGEN_FALLBACK_SPECIES_BLAST_MAX_TARGETS = 1000
PAGE_ALL_SPECIES_BLAST_MAX_TARGETS = 5000
FUNCTION_GENE_RESULT_LIMIT = 2000
FUNCTION_GENE_ALL_SPECIES_BLAST_MAX_TARGETS = 1000
JOB_RESULT_TABLE_LIMIT = 5000

INTERPROSCAN_DATABASES = (
    'ProSitePatterns', 'PANTHER', 'Coils', 'Pfam', 'Gene3D', 'PRINTS',
    'SUPERFAMILY', 'ProSiteProfiles', 'PIRSF', 'CDD', 'TIGRFAM', 'Hamap',
    'MobiDBLite', 'SMART', 'SFLD', 'AntiFam',
)


def _read_tsv_result_table(result_path, limit=JOB_RESULT_TABLE_LIMIT):
    if not os.path.isfile(result_path):
        return [], [], False, 0

    rows = []
    total_rows = 0
    with open(result_path, 'r', encoding='utf-8', newline='', errors='replace') as result_file:
        reader = csv.reader(result_file, delimiter='\t')
        headers = next(reader, [])
        for row in reader:
            total_rows += 1
            if len(rows) < limit:
                rows.append(row)

    return headers, rows, total_rows > len(rows), total_rows

ANCESTRAL_DATASETS = (
    'AAKI', 'AAKII', 'AAKIII', 'ACAK',
    'ASAKI', 'ASAKII', 'ASAKIII', 'ASAKIV', 'ASAKV', 'ASAKVI', 'ASAKVII',
    'ASAKVIII', 'ASAKIX', 'ASAKX', 'ASAKXI', 'ASAKXII', 'ASAKXIII',
    'ASAKXIV', 'ASAKXV', 'ASAKXVI', 'ASAKXVII', 'ASAKXVIII', 'ASAKXIX',
    'CAAKI', 'CAAKII', 'CAAKIII', 'CAAKIV', 'CIAKI', 'CIAKII',
)

ALL_ANCESTRAL_DATASETS_VALUE = 'ALL_ANCESTRAL_DATASETS'

ANCESTRAL_SEARCH_MODE_CANDIDATE = 'candidate'
ANCESTRAL_SEARCH_MODE_TRACE = 'best_hit_trace'
ANCESTRAL_SEARCH_MODE_LABELS = {
    ANCESTRAL_SEARCH_MODE_CANDIDATE: 'Ancestral Candidate Search',
    ANCESTRAL_SEARCH_MODE_TRACE: 'Ancestral Gene Tracing',
}
SEQUENCE_TYPE_PROTEIN = 'prot'
SEQUENCE_TYPE_NUCLEOTIDE = 'nucl'

COMBINED_TRACE_TABLES = {
    'Fli': 'Fli_all_with_combined.txt',
    'Gehy': 'Gehy_all_with_combined.txt',
    'Arla': 'Arla_all_with_combined.txt',
}

TRACEABLE_EXTANT_SPECIES = tuple(COMBINED_TRACE_TABLES.keys())
TRACEABLE_EXTANT_SPECIES_LABEL = 'Traceable extant species with available ancestral chromosome relationships'

_COMBINED_TRACE_INDEX_CACHE = {
    'signature': None,
    'index': None,
    'tables': None,
}

ANCESTRAL_DISPLAY_LABELS = {
    'AAKI': 'AAK-I',
    'AAKII': 'AAK-II',
    'AAKIII': 'AAK-III',
    'ACAK': 'ACAK',
    'ASAKI': 'ASAK-I',
    'ASAKII': 'ASAK-II',
    'ASAKIII': 'ASAK-III',
    'ASAKIV': 'ASAK-IV',
    'ASAKV': 'ASAK-V',
    'ASAKVI': 'ASAK-VI',
    'ASAKVII': 'ASAK-VII',
    'ASAKVIII': 'ASAK-VIII',
    'ASAKIX': 'ASAK-IX',
    'ASAKX': 'ASAK-X',
    'ASAKXI': 'ASAK-XI',
    'ASAKXII': 'ASAK-XII',
    'ASAKXIII': 'ASAK-XIII',
    'ASAKXIV': 'ASAK-XIV',
    'ASAKXV': 'ASAK-XV',
    'ASAKXVI': 'ASAK-XVI',
    'ASAKXVII': 'ASAK-XVII',
    'ASAKXVIII': 'ASAK-XVIII',
    'ASAKXIX': 'ASAK-XIX',
    'CAAKI': 'CAAK-I',
    'CAAKII': 'CAAK-II',
    'CAAKIII': 'CAAK-III',
    'CAAKIV': 'CAAK-IV',
    'CIAKI': 'CIAK-I',
    'CIAKII': 'CIAK-II',
}


def _normalize_ancestor_code(value):
    return re.sub(r'[^A-Z0-9]', '', str(value or '').upper())


def _ancestor_label(code):
    normalized = _normalize_ancestor_code(code)
    return ANCESTRAL_DISPLAY_LABELS.get(normalized, code or normalized)


def ancestral_context(extra=None):
    context = {
        'ancestral_options': [
            {
                'code': code,
                'name': code,
                'cds_url': f'/static/ancestral_data/{code}/{code}.cds',
                'pep_url': f'/static/ancestral_data/{code}/{code}.pep',
                'lens_url': f'/static/ancestral_data/{code}/{code}.lens',
                'gff_url': f'/static/ancestral_data/{code}/{code}.new.gff',
            }
            for code in ANCESTRAL_DATASETS
        ]
    }
    if extra:
        context.update(extra)
    return context


def _is_interpro_gene_id(term, species_code):
    return bool(term) and term.startswith(species_code) and re.fullmatch(r"[A-Za-z0-9_.-]+", term) is not None


def _format_interproscan_result_row(species_code, row):
    return (species_code,) + tuple(row[1:9])


GENE_ID_ALLOWED_RE = re.compile(r'^[A-Za-z][A-Za-z0-9_.:-]{1,120}$')


def _resolve_gene_species(geneid):
    for species in sorted(INTERPROSCAN_SPECIES, key=len, reverse=True):
        if geneid.startswith(species):
            return species
    return None


def _resolve_blast_subject_gene(subject_id):
    subject_id = str(subject_id or '').strip()
    candidates = [subject_id]
    candidates.extend(part for part in re.split(r'[|\s,;]+', subject_id) if part)
    candidates.extend(re.findall(r'[A-Za-z][A-Za-z0-9_.:-]{1,120}', subject_id))

    for candidate in candidates:
        species = _resolve_gene_species(candidate)
        if species:
            return candidate, species
    return subject_id, None


def _blast_db_exists(db_path, db_type=None):
    if os.path.exists(db_path):
        return True
    protein_extensions = ('.pin', '.phr', '.psq', '.pdb', '.pot', '.ptf', '.pto', '.pjs')
    nucleotide_extensions = ('.nin', '.nhr', '.nsq', '.ndb', '.not', '.ntf', '.nto', '.njs')
    if db_type == SEQUENCE_TYPE_PROTEIN or db_type == 'prot':
        extensions = protein_extensions
    elif db_type == SEQUENCE_TYPE_NUCLEOTIDE or db_type == 'nucl':
        extensions = nucleotide_extensions
    else:
        extensions = protein_extensions + nucleotide_extensions
    return any(os.path.exists(f"{db_path}{extension}") for extension in extensions)


def _all_species_db_paths(sequence_type):
    sequence_type = SEQUENCE_TYPE_NUCLEOTIDE if sequence_type == SEQUENCE_TYPE_NUCLEOTIDE else SEQUENCE_TYPE_PROTEIN
    db_paths = []
    for species_code in INTERPROSCAN_SPECIES:
        db_path = os.path.join(path_get, 'static', 'blast_match_database', sequence_type, species_code)
        if _blast_db_exists(db_path, sequence_type):
            db_paths.append(db_path)
    return db_paths or [
        os.path.join(path_get, 'static', 'blast_match_database', sequence_type, species_code)
        for species_code in INTERPROSCAN_SPECIES
    ]


def _all_species_protein_db_paths():
    return _all_species_db_paths(SEQUENCE_TYPE_PROTEIN)


def _traceable_species_db_paths(sequence_type):
    sequence_type = SEQUENCE_TYPE_NUCLEOTIDE if sequence_type == SEQUENCE_TYPE_NUCLEOTIDE else SEQUENCE_TYPE_PROTEIN
    db_paths = []
    missing_species = []
    for species_code in TRACEABLE_EXTANT_SPECIES:
        db_path = os.path.join(path_get, 'static', 'blast_match_database', sequence_type, species_code)
        if _blast_db_exists(db_path, sequence_type):
            db_paths.append(db_path)
        else:
            missing_species.append(species_code)
    if missing_species:
        raise FileNotFoundError(
            'Missing traceable species BLAST database(s): ' + ', '.join(missing_species)
        )
    return db_paths


def _normalize_blast_geneids(geneids):
    normalized_geneids = []
    seen_geneids = set()
    for item in geneids:
        gene_id, _species_code = _resolve_blast_subject_gene(item)
        gene_id = (gene_id or '').strip()
        if gene_id and gene_id not in seen_geneids:
            seen_geneids.add(gene_id)
            normalized_geneids.append(gene_id)
    return normalized_geneids


def _run_selected_species_blast(query_sequence, output_directory, species_data, output_name='result.txt', max_target_seqs=PAGE_ALL_SPECIES_BLAST_MAX_TARGETS):
    temp_fasta_file = write_fasta_file(query_sequence, output_directory)
    blast_result_file = os.path.join(output_directory, output_name)
    if species_data == ALL_INTERPROSCAN_SPECIES_VALUE:
        blast_return_code = run_blastp(
            temp_fasta_file,
            'prot',
            ALL_INTERPROSCAN_SPECIES_VALUE,
            '1e-5',
            blast_result_file,
            db_paths=_all_species_protein_db_paths(),
            max_target_seqs=max_target_seqs,
        )
        if blast_return_code != 0 or not os.path.exists(blast_result_file):
            per_species_target_count = max(1, min(50, max_target_seqs // max(1, len(INTERPROSCAN_SPECIES))))
            with open(blast_result_file, 'w', encoding='utf-8') as combined_output:
                for species_code in INTERPROSCAN_SPECIES:
                    species_output = os.path.join(output_directory, f"{species_code}_{output_name}")
                    species_return_code = run_blastp(
                        temp_fasta_file,
                        'prot',
                        species_code,
                        '1e-5',
                        species_output,
                        max_target_seqs=per_species_target_count,
                    )
                    if species_return_code != 0 or not os.path.exists(species_output):
                        continue
                    with open(species_output, 'r', encoding='utf-8') as species_input:
                        combined_output.write(species_input.read())
    else:
        blast_return_code = run_blastp(temp_fasta_file, 'prot', species_data, '1e-5', blast_result_file)
        if blast_return_code != 0 or not os.path.exists(blast_result_file):
            return [], []
    blast_results, geneids = parse_blastp_result(blast_result_file)
    return blast_results, _normalize_blast_geneids(geneids)


def _interproscan_job_is_valid(job_id):
    return re.fullmatch(r'[A-Za-z0-9_-]{8,80}', str(job_id or '')) is not None


def _interproscan_jobs_root():
    return os.path.join(path_get, 'file_keep', 'interproscan_jobs')


def _interproscan_job_dir(job_id):
    return os.path.join(_interproscan_jobs_root(), str(job_id))


def _interproscan_job_status_path(job_id):
    return os.path.join(_interproscan_job_dir(job_id), 'status.json')


def _interproscan_job_request_path(job_id):
    return os.path.join(_interproscan_job_dir(job_id), 'request.json')


def _interproscan_job_result_path(job_id):
    return os.path.join(_interproscan_job_dir(job_id), 'interproscan_all_species_annotations.tsv')


def _interproscan_job_blast_path(job_id):
    return os.path.join(_interproscan_job_dir(job_id), 'blast_hits.tsv')


def _write_interproscan_job_status(job_id, status, message='', extra=None):
    job_dir = _interproscan_job_dir(job_id)
    os.makedirs(job_dir, exist_ok=True)
    payload = {
        'status': status,
        'message': str(message or ''),
        'updated_at': time.time(),
    }
    if extra:
        payload.update(extra)
    with open(_interproscan_job_status_path(job_id), 'w', encoding='utf-8') as status_file:
        json.dump(payload, status_file, ensure_ascii=False)


def _read_interproscan_job_status(job_id):
    status_path = _interproscan_job_status_path(job_id)
    if not os.path.isfile(status_path):
        return {'status': 'queued', 'message': 'Waiting to start.'}
    try:
        with open(status_path, 'r', encoding='utf-8') as status_file:
            return json.load(status_file)
    except Exception as exc:
        return {'status': 'error', 'message': f'Could not read job status: {exc}'}


def _create_interproscan_all_species_job(query_sequence, selected_databases):
    job_id = uuid.uuid4().hex
    job_dir = _interproscan_job_dir(job_id)
    from api.download_access import create_job_directory
    create_job_directory(job_dir)
    payload = {
        'query_sequence': query_sequence,
        'selected_databases': selected_databases,
        'created_at': time.time(),
    }
    with open(_interproscan_job_request_path(job_id), 'w', encoding='utf-8') as request_file:
        json.dump(payload, request_file, ensure_ascii=False)
    _write_interproscan_job_status(job_id, 'queued', 'Job submitted.')
    return job_id


def _write_interproscan_blast_hits(job_id, blast_results, genes_by_species):
    with open(_interproscan_job_blast_path(job_id), 'w', encoding='utf-8') as blast_file:
        blast_file.write(
            'query_id\tsubject_id\tmatched_gene_id\tspecies\tidentity\talignment_length\t'
            'mismatches\tgap_opens\tq_start\tq_end\ts_start\ts_end\tevalue\tbit_score\n'
        )
        for row in blast_results:
            matched_gene_id, species_code = _resolve_blast_subject_gene(row[1])
            blast_file.write('\t'.join([
                str(row[0]),
                str(row[1]),
                matched_gene_id,
                species_code or '',
                str(row[2]),
                str(row[3]),
                str(row[4]),
                str(row[5]),
                str(row[6]),
                str(row[7]),
                str(row[8]),
                str(row[9]),
                str(row[10]),
                str(row[11]),
            ]) + '\n')


def run_interproscan_all_species_job(job_id):
    if not _interproscan_job_is_valid(job_id):
        return

    close_old_connections()
    try:
        _write_interproscan_job_status(job_id, 'running', 'Preparing all-species BLAST job.', {
            'progress': 1,
        })
        with open(_interproscan_job_request_path(job_id), 'r', encoding='utf-8') as request_file:
            payload = json.load(request_file)

        selected_databases = [
            db_name for db_name in payload.get('selected_databases', [])
            if db_name in INTERPROSCAN_DATABASES
        ]
        query_sequence = (payload.get('query_sequence') or '').strip()
        if not selected_databases:
            raise RuntimeError('No valid analysis databases were selected.')
        if not query_sequence:
            raise RuntimeError('No query sequence was submitted.')

        job_dir = _interproscan_job_dir(job_id)
        temp_fasta_file = write_fasta_file(query_sequence, job_dir)
        blast_result_file = os.path.join(job_dir, 'result_all_species.txt')
        db_paths = [
            f"{path_get}/static/blast_match_database/prot/{species_code}"
            for species_code in INTERPROSCAN_SPECIES
        ]

        _write_interproscan_job_status(job_id, 'running', 'Running all-species BLAST.', {
            'progress': 10,
        })
        blast_return_code = run_blastp(
            temp_fasta_file,
            'prot',
            ALL_INTERPROSCAN_SPECIES_VALUE,
            '1e-5',
            blast_result_file,
            db_paths=db_paths,
            max_target_seqs=INTERPROSCAN_ALL_SPECIES_BLAST_MAX_TARGETS,
        )
        fallback_failures = []
        fallback_used = not (blast_return_code == 0 and os.path.exists(blast_result_file))
        if not fallback_used:
            blast_results, geneids = parse_blastp_result(blast_result_file)
        else:
            _write_interproscan_job_status(job_id, 'running', 'Combined BLAST database failed; running per-species BLAST fallback.', {
                'progress': 12,
            })
            blast_results = []
            geneids = []
            with open(blast_result_file, 'w', encoding='utf-8') as combined_blast_file:
                for species_index, species_code in enumerate(INTERPROSCAN_SPECIES, start=1):
                    species_result_file = os.path.join(job_dir, f'result_{species_code}.txt')
                    progress = 12 + int(35 * species_index / len(INTERPROSCAN_SPECIES))
                    _write_interproscan_job_status(job_id, 'running', f'Running BLAST fallback for {species_code}.', {
                        'progress': progress,
                        'failed_species_count': len(fallback_failures),
                        'failed_species': fallback_failures,
                    })
                    species_return_code = run_blastp(
                        temp_fasta_file,
                        'prot',
                        species_code,
                        '1e-5',
                        species_result_file,
                        max_target_seqs=INTERPROSCAN_FALLBACK_SPECIES_BLAST_MAX_TARGETS,
                    )
                    if species_return_code != 0:
                        fallback_failures.append(species_code)
                        continue
                    if not os.path.exists(species_result_file):
                        continue
                    with open(species_result_file, 'r', encoding='utf-8', errors='ignore') as species_blast_file:
                        for line in species_blast_file:
                            combined_blast_file.write(line)
                    species_blast_results, species_geneids = parse_blastp_result(species_result_file)
                    blast_results.extend(species_blast_results)
                    geneids.extend(species_geneids)

            if not blast_results and fallback_failures:
                raise RuntimeError(
                    'All-species BLAST failed. Combined database and per-species fallback both failed. '
                    f'Failed species count: {len(fallback_failures)}.'
                )

        genes_by_species = {}
        for item in geneids:
            gene_id, species_code = _resolve_blast_subject_gene(item)
            if species_code in INTERPROSCAN_SPECIES:
                species_terms = genes_by_species.setdefault(species_code, [])
                if gene_id not in species_terms:
                    species_terms.append(gene_id)

        _write_interproscan_blast_hits(job_id, blast_results, genes_by_species)

        result_path = _interproscan_job_result_path(job_id)
        result_count = 0
        recognized_gene_count = sum(len(gene_ids) for gene_ids in genes_by_species.values())
        analysis_placeholders = ','.join(['%s'] * len(selected_databases))
        species_total = len(INTERPROSCAN_SPECIES)
        annotation_progress_base = 50 if fallback_used else 25
        annotation_progress_span = 45 if fallback_used else 70

        _write_interproscan_job_status(job_id, 'running', 'Looking up InterProScan annotations.', {
            'progress': annotation_progress_base,
            'blast_hit_count': len(blast_results),
            'recognized_gene_count': recognized_gene_count,
            'failed_species_count': len(fallback_failures),
            'failed_species': fallback_failures,
        })

        with connection.cursor() as cursor, open(result_path, 'w', encoding='utf-8') as result_file:
            result_file.write('species\tseq_id\tlength\tanalysis\tdescription\tstart\tend\tipr\tgo\n')
            for species_index, species_code in enumerate(INTERPROSCAN_SPECIES, start=1):
                gene_ids = genes_by_species.get(species_code, [])
                if not gene_ids:
                    progress = annotation_progress_base + int(annotation_progress_span * species_index / species_total)
                    _write_interproscan_job_status(job_id, 'running', f'Checking {species_code}.', {
                        'progress': progress,
                        'result_count': result_count,
                        'blast_hit_count': len(blast_results),
                        'recognized_gene_count': recognized_gene_count,
                        'failed_species_count': len(fallback_failures),
                        'failed_species': fallback_failures,
                    })
                    continue

                table_name = f"{species_code}_interproscan_table"
                for start_index in range(0, len(gene_ids), 200):
                    gene_chunk = gene_ids[start_index:start_index + 200]
                    gene_placeholders = ','.join(['%s'] * len(gene_chunk))
                    sql_query = (
                        f"SELECT * FROM {table_name} "
                        f"WHERE analysis IN ({analysis_placeholders}) "
                        f"AND gene_id IN ({gene_placeholders})"
                    )
                    cursor.execute(sql_query, selected_databases + gene_chunk)
                    for row in cursor.fetchall():
                        formatted_row = _format_interproscan_result_row(species_code, row)
                        result_file.write('\t'.join(str(value) if value is not None else '' for value in formatted_row) + '\n')
                        result_count += 1

                progress = annotation_progress_base + int(annotation_progress_span * species_index / species_total)
                _write_interproscan_job_status(job_id, 'running', f'Checked {species_code}.', {
                    'progress': progress,
                    'result_count': result_count,
                    'blast_hit_count': len(blast_results),
                    'recognized_gene_count': recognized_gene_count,
                    'failed_species_count': len(fallback_failures),
                    'failed_species': fallback_failures,
                })

        _write_interproscan_job_status(job_id, 'done', 'All-species InterProScan annotation file is ready.', {
            'progress': 100,
            'result_count': result_count,
            'blast_hit_count': len(blast_results),
            'recognized_gene_count': recognized_gene_count,
            'failed_species_count': len(fallback_failures),
            'failed_species': fallback_failures,
        })
    except Exception as exc:
        _write_interproscan_job_status(job_id, 'error', exc, {
            'progress': 100,
        })
    finally:
        close_old_connections()


def _start_interproscan_all_species_job(job_id):
    from api.compute_limits import launch_background
    job_dir = _interproscan_job_dir(job_id)
    command = [get_real_python_executable(), os.path.join(str(settings.BASE_DIR), 'manage.py'),
               'run_all_species_job', 'interproscan', str(job_id)]
    launch_background(command, cwd=str(settings.BASE_DIR),
                      log_path=os.path.join(job_dir, 'background.log'),
                      status_path=_interproscan_job_status_path(job_id))


FUNCTION_GENE_RESULT_HEADERS = (
    'Gene', 'Event_type', 'S_start', 'S_end', 'Function',
    'Ath_gene', 'Identity(%)', 'E-value', 'Score',
)

FUNCTION_GENE_RESULT_COLUMN_INDEXES = (2, 14, 9, 10, 13, 1, 3, 11, 12)


def _function_gene_job_is_valid(job_id):
    return re.fullmatch(r'[A-Za-z0-9_-]{8,80}', str(job_id or '')) is not None


def _function_gene_jobs_root():
    return os.path.join(path_get, 'file_keep', 'function_gene_jobs')


def _function_gene_job_dir(job_id):
    return os.path.join(_function_gene_jobs_root(), str(job_id))


def _function_gene_job_status_path(job_id):
    return os.path.join(_function_gene_job_dir(job_id), 'status.json')


def _function_gene_job_request_path(job_id):
    return os.path.join(_function_gene_job_dir(job_id), 'request.json')


def _function_gene_job_result_path(job_id):
    return os.path.join(_function_gene_job_dir(job_id), 'function_gene_all_species.tsv')


def _function_gene_job_blast_path(job_id):
    return os.path.join(_function_gene_job_dir(job_id), 'blast_hits.tsv')


def _write_function_gene_job_status(job_id, status, message='', extra=None):
    job_dir = _function_gene_job_dir(job_id)
    os.makedirs(job_dir, exist_ok=True)
    payload = {
        'status': status,
        'message': str(message or ''),
        'updated_at': time.time(),
    }
    if extra:
        payload.update(extra)
    with open(_function_gene_job_status_path(job_id), 'w', encoding='utf-8') as status_file:
        json.dump(payload, status_file, ensure_ascii=False)


def _read_function_gene_job_status(job_id):
    status_path = _function_gene_job_status_path(job_id)
    if not os.path.isfile(status_path):
        return {'status': 'queued', 'message': 'Waiting to start.'}
    try:
        with open(status_path, 'r', encoding='utf-8') as status_file:
            return json.load(status_file)
    except Exception as exc:
        return {'status': 'error', 'message': f'Could not read job status: {exc}'}


def _create_function_gene_all_species_job(query_sequence):
    job_id = uuid.uuid4().hex
    job_dir = _function_gene_job_dir(job_id)
    from api.download_access import create_job_directory
    create_job_directory(job_dir)
    payload = {
        'query_sequence': query_sequence,
        'created_at': time.time(),
    }
    with open(_function_gene_job_request_path(job_id), 'w', encoding='utf-8') as request_file:
        json.dump(payload, request_file, ensure_ascii=False)
    _write_function_gene_job_status(job_id, 'queued', 'Job submitted.')
    return job_id


def _write_function_gene_blast_hits(job_id, blast_results):
    with open(_function_gene_job_blast_path(job_id), 'w', encoding='utf-8', newline='') as blast_file:
        writer = csv.writer(blast_file, delimiter='\t')
        writer.writerow([
            'Query ID', 'Subject ID', 'Identity', 'Length', 'Mismatch', 'Gapopen',
            'Qstart', 'Qend', 'Sstart', 'Send', 'E-value', 'Bit Score',
        ])
        for row in blast_results:
            writer.writerow([str(value) if value is not None else '' for value in row[:12]])


def _function_gene_result_values(row):
    values = []
    for index in FUNCTION_GENE_RESULT_COLUMN_INDEXES:
        values.append(row[index] if index < len(row) and row[index] is not None else '')
    return values


def _read_function_gene_result_rows(result_path):
    if not os.path.isfile(result_path):
        return []
    rows = []
    with open(result_path, 'r', encoding='utf-8', newline='') as result_file:
        reader = csv.DictReader(result_file, delimiter='\t')
        for row in reader:
            rows.append([row.get(header, '') for header in FUNCTION_GENE_RESULT_HEADERS])
    return rows


def run_function_gene_all_species_job(job_id):
    if not _function_gene_job_is_valid(job_id):
        return

    close_old_connections()
    try:
        _write_function_gene_job_status(job_id, 'running', 'Preparing all-species BLAST job.', {
            'progress': 1,
        })
        with open(_function_gene_job_request_path(job_id), 'r', encoding='utf-8') as request_file:
            payload = json.load(request_file)

        query_sequence = (payload.get('query_sequence') or '').strip()
        if not query_sequence:
            raise RuntimeError('No query sequence was submitted.')

        job_dir = _function_gene_job_dir(job_id)
        _write_function_gene_job_status(job_id, 'running', 'Running all-species BLAST.', {
            'progress': 10,
        })
        blast_results, geneids = _run_selected_species_blast(
            query_sequence,
            job_dir,
            ALL_INTERPROSCAN_SPECIES_VALUE,
            output_name='result_all_species.txt',
            max_target_seqs=FUNCTION_GENE_ALL_SPECIES_BLAST_MAX_TARGETS,
        )
        _write_function_gene_blast_hits(job_id, blast_results)

        unique_geneids = []
        seen_geneids = set()
        for geneid in geneids:
            if geneid and geneid not in seen_geneids:
                seen_geneids.add(geneid)
                unique_geneids.append(geneid)

        _write_function_gene_job_status(job_id, 'running', 'Looking up Aster-Genefamiles records.', {
            'progress': 55,
            'blast_hit_count': len(blast_results),
            'recognized_gene_count': len(unique_geneids),
        })

        result_path = _function_gene_job_result_path(job_id)
        result_count = 0
        rows_by_geneid = {geneid: [] for geneid in unique_geneids}

        with connection.cursor() as cursor:
            for start_index in range(0, len(unique_geneids), 200):
                gene_chunk = unique_geneids[start_index:start_index + 200]
                if not gene_chunk:
                    continue
                placeholders = ','.join(['%s'] * len(gene_chunk))
                cursor.execute(
                    f"SELECT * FROM function_GF_table WHERE gene_id IN ({placeholders})",
                    gene_chunk,
                )
                for row in cursor.fetchall():
                    if len(row) > 2 and row[2] in rows_by_geneid:
                        rows_by_geneid[row[2]].append(row)

        with open(result_path, 'w', encoding='utf-8', newline='') as result_file:
            writer = csv.writer(result_file, delimiter='\t')
            writer.writerow(FUNCTION_GENE_RESULT_HEADERS)
            for geneid in unique_geneids:
                for row in rows_by_geneid.get(geneid, []):
                    writer.writerow([str(value) if value is not None else '' for value in _function_gene_result_values(row)])
                    result_count += 1

        _write_function_gene_job_status(job_id, 'done', 'All-species function gene result file is ready.', {
            'progress': 100,
            'result_count': result_count,
            'blast_hit_count': len(blast_results),
            'recognized_gene_count': len(unique_geneids),
        })
    except Exception as exc:
        _write_function_gene_job_status(job_id, 'error', exc, {
            'progress': 100,
        })
    finally:
        close_old_connections()


def _start_function_gene_all_species_job(job_id):
    from api.compute_limits import launch_background
    job_dir = _function_gene_job_dir(job_id)
    command = [get_real_python_executable(), os.path.join(str(settings.BASE_DIR), 'manage.py'),
               'run_all_species_job', 'function_gene', str(job_id)]
    launch_background(command, cwd=str(settings.BASE_DIR),
                      log_path=os.path.join(job_dir, 'background.log'),
                      status_path=_function_gene_job_status_path(job_id))


def _kegg_job_is_valid(job_id):
    return re.fullmatch(r'[A-Za-z0-9_-]{8,80}', str(job_id or '')) is not None


def _kegg_jobs_root():
    return os.path.join(path_get, 'file_keep', 'kegg_jobs')


def _kegg_job_dir(job_id):
    return os.path.join(_kegg_jobs_root(), str(job_id))


def _kegg_job_status_path(job_id):
    return os.path.join(_kegg_job_dir(job_id), 'status.json')


def _kegg_job_request_path(job_id):
    return os.path.join(_kegg_job_dir(job_id), 'request.json')


def _kegg_job_result_path(job_id):
    return os.path.join(_kegg_job_dir(job_id), 'kegg_all_species_annotations.tsv')


def _kegg_job_blast_path(job_id):
    return os.path.join(_kegg_job_dir(job_id), 'blast_hits.tsv')


def _write_kegg_job_status(job_id, status, message='', extra=None):
    job_dir = _kegg_job_dir(job_id)
    os.makedirs(job_dir, exist_ok=True)
    payload = {
        'status': status,
        'message': str(message or ''),
        'updated_at': time.time(),
    }
    if extra:
        payload.update(extra)
    with open(_kegg_job_status_path(job_id), 'w', encoding='utf-8') as status_file:
        json.dump(payload, status_file, ensure_ascii=False)


def _read_kegg_job_status(job_id):
    status_path = _kegg_job_status_path(job_id)
    if not os.path.isfile(status_path):
        return {'status': 'queued', 'message': 'Waiting to start.'}
    try:
        with open(status_path, 'r', encoding='utf-8') as status_file:
            return json.load(status_file)
    except Exception as exc:
        return {'status': 'error', 'message': f'Could not read job status: {exc}'}


def _create_kegg_all_species_job(query_sequence):
    job_id = uuid.uuid4().hex
    job_dir = _kegg_job_dir(job_id)
    from api.download_access import create_job_directory
    create_job_directory(job_dir)
    payload = {
        'query_sequence': query_sequence,
        'created_at': time.time(),
    }
    with open(_kegg_job_request_path(job_id), 'w', encoding='utf-8') as request_file:
        json.dump(payload, request_file, ensure_ascii=False)
    _write_kegg_job_status(job_id, 'queued', 'Job submitted.')
    return job_id


def _write_kegg_blast_hits(job_id, blast_results):
    with open(_kegg_job_blast_path(job_id), 'w', encoding='utf-8') as blast_file:
        blast_file.write(
            'query_id\tsubject_id\tmatched_gene_id\tspecies\tidentity\talignment_length\t'
            'mismatches\tgap_opens\tq_start\tq_end\ts_start\ts_end\tevalue\tbit_score\n'
        )
        for row in blast_results:
            matched_gene_id, species_code = _resolve_blast_subject_gene(row[1])
            blast_file.write('\t'.join([
                str(row[0]),
                str(row[1]),
                matched_gene_id,
                species_code or '',
                str(row[2]),
                str(row[3]),
                str(row[4]),
                str(row[5]),
                str(row[6]),
                str(row[7]),
                str(row[8]),
                str(row[9]),
                str(row[10]),
                str(row[11]),
            ]) + '\n')


def run_kegg_all_species_job(job_id):
    if not _kegg_job_is_valid(job_id):
        return

    close_old_connections()
    try:
        _write_kegg_job_status(job_id, 'running', 'Preparing all-species KEGG BLAST job.', {
            'progress': 1,
        })
        with open(_kegg_job_request_path(job_id), 'r', encoding='utf-8') as request_file:
            payload = json.load(request_file)

        query_sequence = (payload.get('query_sequence') or '').strip()
        if not query_sequence:
            raise RuntimeError('No query sequence was submitted.')

        job_dir = _kegg_job_dir(job_id)
        temp_fasta_file = write_fasta_file(query_sequence, job_dir)
        blast_result_file = os.path.join(job_dir, 'result_all_species.txt')
        db_paths = [
            f"{path_get}/static/blast_match_database/prot/{species_code}"
            for species_code in INTERPROSCAN_SPECIES
        ]

        _write_kegg_job_status(job_id, 'running', 'Running all-species BLAST.', {
            'progress': 10,
        })
        blast_return_code = run_blastp(
            temp_fasta_file,
            'prot',
            ALL_INTERPROSCAN_SPECIES_VALUE,
            '1e-5',
            blast_result_file,
            db_paths=db_paths,
            max_target_seqs=KEGG_ALL_SPECIES_BLAST_MAX_TARGETS,
        )

        fallback_failures = []
        fallback_used = not (blast_return_code == 0 and os.path.exists(blast_result_file))
        if not fallback_used:
            blast_results, geneids = parse_blastp_result(blast_result_file)
        else:
            _write_kegg_job_status(job_id, 'running', 'Combined BLAST database failed; running per-species BLAST fallback.', {
                'progress': 12,
            })
            blast_results = []
            geneids = []
            with open(blast_result_file, 'w', encoding='utf-8') as combined_blast_file:
                for species_index, species_code in enumerate(INTERPROSCAN_SPECIES, start=1):
                    species_result_file = os.path.join(job_dir, f'result_{species_code}.txt')
                    progress = 12 + int(35 * species_index / len(INTERPROSCAN_SPECIES))
                    _write_kegg_job_status(job_id, 'running', f'Running BLAST fallback for {species_code}.', {
                        'progress': progress,
                        'failed_species_count': len(fallback_failures),
                        'failed_species': fallback_failures,
                    })
                    species_return_code = run_blastp(
                        temp_fasta_file,
                        'prot',
                        species_code,
                        '1e-5',
                        species_result_file,
                        max_target_seqs=KEGG_FALLBACK_SPECIES_BLAST_MAX_TARGETS,
                    )
                    if species_return_code != 0:
                        fallback_failures.append(species_code)
                        continue
                    if not os.path.exists(species_result_file):
                        continue
                    with open(species_result_file, 'r', encoding='utf-8', errors='ignore') as species_blast_file:
                        for line in species_blast_file:
                            combined_blast_file.write(line)
                    species_blast_results, species_geneids = parse_blastp_result(species_result_file)
                    blast_results.extend(species_blast_results)
                    geneids.extend(species_geneids)

            if not blast_results and fallback_failures:
                raise RuntimeError(
                    'All-species BLAST failed. Combined database and per-species fallback both failed. '
                    f'Failed species count: {len(fallback_failures)}.'
                )

        matched_gene_ids = []
        seen_gene_ids = set()
        for item in geneids:
            gene_id, species_code = _resolve_blast_subject_gene(item)
            if species_code in INTERPROSCAN_SPECIES and gene_id not in seen_gene_ids:
                seen_gene_ids.add(gene_id)
                matched_gene_ids.append(gene_id)

        _write_kegg_blast_hits(job_id, blast_results)

        result_path = _kegg_job_result_path(job_id)
        result_count = 0
        lookup_progress_base = 50 if fallback_used else 25
        _write_kegg_job_status(job_id, 'running', 'Looking up KEGG annotations.', {
            'progress': lookup_progress_base,
            'blast_hit_count': len(blast_results),
            'recognized_gene_count': len(matched_gene_ids),
            'failed_species_count': len(fallback_failures),
            'failed_species': fallback_failures,
        })

        with connection.cursor() as cursor, open(result_path, 'w', encoding='utf-8') as result_file:
            result_file.write('species\tgene_id\tko\tdefinition\n')
            for start_index in range(0, len(matched_gene_ids), 500):
                gene_chunk = matched_gene_ids[start_index:start_index + 500]
                if not gene_chunk:
                    continue
                gene_placeholders = ','.join(['%s'] * len(gene_chunk))
                cursor.execute(
                    f"SELECT * FROM kegg_table WHERE gene_id IN ({gene_placeholders})",
                    gene_chunk,
                )
                for row in cursor.fetchall():
                    result_file.write('\t'.join([
                        str(row[1]) if len(row) > 1 and row[1] is not None else '',
                        str(row[2]) if len(row) > 2 and row[2] is not None else '',
                        str(row[3]) if len(row) > 3 and row[3] is not None else '',
                        str(row[4]) if len(row) > 4 and row[4] is not None else '',
                    ]) + '\n')
                    result_count += 1

                progress = lookup_progress_base + int(45 * min(start_index + len(gene_chunk), len(matched_gene_ids)) / max(len(matched_gene_ids), 1))
                _write_kegg_job_status(job_id, 'running', 'Looking up KEGG annotations.', {
                    'progress': progress,
                    'result_count': result_count,
                    'blast_hit_count': len(blast_results),
                    'recognized_gene_count': len(matched_gene_ids),
                    'failed_species_count': len(fallback_failures),
                    'failed_species': fallback_failures,
                })

        _write_kegg_job_status(job_id, 'done', 'All-species KEGG annotation file is ready.', {
            'progress': 100,
            'result_count': result_count,
            'blast_hit_count': len(blast_results),
            'recognized_gene_count': len(matched_gene_ids),
            'failed_species_count': len(fallback_failures),
            'failed_species': fallback_failures,
        })
    except Exception as exc:
        _write_kegg_job_status(job_id, 'error', exc, {
            'progress': 100,
        })
    finally:
        close_old_connections()


def _start_kegg_all_species_job(job_id):
    from api.compute_limits import launch_background
    job_dir = _kegg_job_dir(job_id)
    command = [get_real_python_executable(), os.path.join(str(settings.BASE_DIR), 'manage.py'),
               'run_all_species_job', 'kegg', str(job_id)]
    launch_background(command, cwd=str(settings.BASE_DIR),
                      log_path=os.path.join(job_dir, 'background.log'),
                      status_path=_kegg_job_status_path(job_id))


def _dupgen_job_is_valid(job_id):
    return bool(re.fullmatch(r'[0-9a-f]{32}', str(job_id or '')))


def _dupgen_jobs_root():
    return os.path.join(path_get, 'file_keep', 'dupgen_jobs')


def _dupgen_job_dir(job_id):
    return os.path.join(_dupgen_jobs_root(), str(job_id))


def _dupgen_job_status_path(job_id):
    return os.path.join(_dupgen_job_dir(job_id), 'status.json')


def _dupgen_job_request_path(job_id):
    return os.path.join(_dupgen_job_dir(job_id), 'request.json')


def _dupgen_job_result_path(job_id):
    return os.path.join(_dupgen_job_dir(job_id), 'dupgen_all_species_results.tsv')


def _dupgen_job_blast_path(job_id):
    return os.path.join(_dupgen_job_dir(job_id), 'blast_hits.tsv')


def _write_dupgen_job_status(job_id, status, message='', extra=None):
    job_dir = _dupgen_job_dir(job_id)
    os.makedirs(job_dir, exist_ok=True)
    payload = {
        'status': status,
        'message': str(message or ''),
        'updated_at': time.time(),
    }
    if extra:
        payload.update(extra)
    with open(_dupgen_job_status_path(job_id), 'w', encoding='utf-8') as status_file:
        json.dump(payload, status_file, ensure_ascii=False)


def _read_dupgen_job_status(job_id):
    status_path = _dupgen_job_status_path(job_id)
    if not os.path.isfile(status_path):
        return {'status': 'queued', 'message': 'Waiting to start.'}
    try:
        with open(status_path, 'r', encoding='utf-8') as status_file:
            return json.load(status_file)
    except Exception as exc:
        return {'status': 'error', 'message': f'Could not read job status: {exc}'}


def _create_dupgen_all_species_job(query_sequence):
    job_id = uuid.uuid4().hex
    job_dir = _dupgen_job_dir(job_id)
    from api.download_access import create_job_directory
    create_job_directory(job_dir)
    with open(_dupgen_job_request_path(job_id), 'w', encoding='utf-8') as request_file:
        json.dump({
            'query_sequence': query_sequence,
            'created_at': time.time(),
        }, request_file, ensure_ascii=False)
    _write_dupgen_job_status(job_id, 'queued', 'Job submitted.')
    return job_id


def _write_dupgen_blast_hits(job_id, blast_results):
    with open(_dupgen_job_blast_path(job_id), 'w', encoding='utf-8') as blast_file:
        blast_file.write(
            'query_id\tsubject_id\tmatched_gene_id\tspecies\tidentity\talignment_length\t'
            'mismatches\tgap_opens\tq_start\tq_end\ts_start\ts_end\tevalue\tbit_score\n'
        )
        for row in blast_results:
            matched_gene_id, species_code = _resolve_blast_subject_gene(row[1])
            blast_file.write('\t'.join([
                str(row[0]),
                str(row[1]),
                matched_gene_id,
                species_code or '',
                str(row[2]),
                str(row[3]),
                str(row[4]),
                str(row[5]),
                str(row[6]),
                str(row[7]),
                str(row[8]),
                str(row[9]),
                str(row[10]),
                str(row[11]),
            ]) + '\n')


def run_dupgen_all_species_job(job_id):
    if not _dupgen_job_is_valid(job_id):
        return

    close_old_connections()
    try:
        _write_dupgen_job_status(job_id, 'running', 'Preparing all-species DupGen BLAST job.', {
            'progress': 1,
        })
        with open(_dupgen_job_request_path(job_id), 'r', encoding='utf-8') as request_file:
            payload = json.load(request_file)

        query_sequence = (payload.get('query_sequence') or '').strip()
        if not query_sequence:
            raise RuntimeError('No query sequence was submitted.')

        job_dir = _dupgen_job_dir(job_id)
        temp_fasta_file = write_fasta_file(query_sequence, job_dir)
        blast_result_file = os.path.join(job_dir, 'result_all_species.txt')
        db_paths = [
            f"{path_get}/static/blast_match_database/prot/{species_code}"
            for species_code in INTERPROSCAN_SPECIES
        ]

        _write_dupgen_job_status(job_id, 'running', 'Running all-species BLAST.', {
            'progress': 10,
        })
        blast_return_code = run_blastp(
            temp_fasta_file,
            'prot',
            ALL_INTERPROSCAN_SPECIES_VALUE,
            '1e-5',
            blast_result_file,
            db_paths=db_paths,
            max_target_seqs=DUPGEN_ALL_SPECIES_BLAST_MAX_TARGETS,
        )

        fallback_failures = []
        fallback_used = not (blast_return_code == 0 and os.path.exists(blast_result_file))
        if not fallback_used:
            blast_results, geneids = parse_blastp_result(blast_result_file)
        else:
            _write_dupgen_job_status(job_id, 'running', 'Combined BLAST database failed; running per-species BLAST fallback.', {
                'progress': 12,
            })
            blast_results = []
            geneids = []
            with open(blast_result_file, 'w', encoding='utf-8') as combined_blast_file:
                for species_index, species_code in enumerate(INTERPROSCAN_SPECIES, start=1):
                    species_result_file = os.path.join(job_dir, f'result_{species_code}.txt')
                    progress = 12 + int(35 * species_index / len(INTERPROSCAN_SPECIES))
                    _write_dupgen_job_status(job_id, 'running', f'Running BLAST fallback for {species_code}.', {
                        'progress': progress,
                        'failed_species_count': len(fallback_failures),
                        'failed_species': fallback_failures,
                    })
                    species_return_code = run_blastp(
                        temp_fasta_file,
                        'prot',
                        species_code,
                        '1e-5',
                        species_result_file,
                        max_target_seqs=DUPGEN_FALLBACK_SPECIES_BLAST_MAX_TARGETS,
                    )
                    if species_return_code != 0:
                        fallback_failures.append(species_code)
                        continue
                    if not os.path.exists(species_result_file):
                        continue
                    with open(species_result_file, 'r', encoding='utf-8', errors='ignore') as species_blast_file:
                        for line in species_blast_file:
                            combined_blast_file.write(line)
                    species_blast_results, species_geneids = parse_blastp_result(species_result_file)
                    blast_results.extend(species_blast_results)
                    geneids.extend(species_geneids)

            if not blast_results and fallback_failures:
                raise RuntimeError(
                    'All-species BLAST failed. Combined database and per-species fallback both failed. '
                    f'Failed species count: {len(fallback_failures)}.'
                )

        matched_gene_ids = []
        seen_gene_ids = set()
        for item in geneids:
            gene_id, species_code = _resolve_blast_subject_gene(item)
            if species_code in INTERPROSCAN_SPECIES and gene_id not in seen_gene_ids:
                seen_gene_ids.add(gene_id)
                matched_gene_ids.append(gene_id)

        _write_dupgen_blast_hits(job_id, blast_results)

        result_path = _dupgen_job_result_path(job_id)
        result_count = 0
        lookup_progress_base = 50 if fallback_used else 25
        _write_dupgen_job_status(job_id, 'running', 'Looking up DupGen records.', {
            'progress': lookup_progress_base,
            'blast_hit_count': len(blast_results),
            'recognized_gene_count': len(matched_gene_ids),
            'failed_species_count': len(fallback_failures),
            'failed_species': fallback_failures,
        })

        with connection.cursor() as cursor, open(result_path, 'w', encoding='utf-8') as result_file:
            result_file.write('species\tgene1\tlocation1\tgene2\tlocation2\te_value\ttype\n')
            for start_index in range(0, len(matched_gene_ids), 500):
                gene_chunk = matched_gene_ids[start_index:start_index + 500]
                if not gene_chunk:
                    continue
                gene_placeholders = ','.join(['%s'] * len(gene_chunk))
                cursor.execute(
                    f"SELECT * FROM Genetype_table WHERE gene1 IN ({gene_placeholders})",
                    gene_chunk,
                )
                for row in cursor.fetchall():
                    result_file.write('\t'.join([
                        str(row[1]) if len(row) > 1 and row[1] is not None else '',
                        str(row[2]) if len(row) > 2 and row[2] is not None else '',
                        str(row[3]) if len(row) > 3 and row[3] is not None else '',
                        str(row[4]) if len(row) > 4 and row[4] is not None else '',
                        str(row[5]) if len(row) > 5 and row[5] is not None else '',
                        str(row[6]) if len(row) > 6 and row[6] is not None else '',
                        str(row[7]) if len(row) > 7 and row[7] is not None else '',
                    ]) + '\n')
                    result_count += 1

                progress = lookup_progress_base + int(45 * min(start_index + len(gene_chunk), len(matched_gene_ids)) / max(len(matched_gene_ids), 1))
                _write_dupgen_job_status(job_id, 'running', 'Looking up DupGen records.', {
                    'progress': progress,
                    'result_count': result_count,
                    'blast_hit_count': len(blast_results),
                    'recognized_gene_count': len(matched_gene_ids),
                    'failed_species_count': len(fallback_failures),
                    'failed_species': fallback_failures,
                })

        _write_dupgen_job_status(job_id, 'done', 'All-species DupGen result file is ready.', {
            'progress': 100,
            'result_count': result_count,
            'blast_hit_count': len(blast_results),
            'recognized_gene_count': len(matched_gene_ids),
            'failed_species_count': len(fallback_failures),
            'failed_species': fallback_failures,
        })
    except Exception as exc:
        _write_dupgen_job_status(job_id, 'error', exc, {
            'progress': 100,
        })
    finally:
        close_old_connections()


def _start_dupgen_all_species_job(job_id):
    from api.compute_limits import launch_background
    job_dir = _dupgen_job_dir(job_id)
    command = [get_real_python_executable(), os.path.join(str(settings.BASE_DIR), 'manage.py'),
               'run_all_species_job', 'dupgen', str(job_id)]
    launch_background(command, cwd=str(settings.BASE_DIR),
                      log_path=os.path.join(job_dir, 'background.log'),
                      status_path=_dupgen_job_status_path(job_id))


def index(request):
    return render(request, 'index.html')


def collinear_kaks(request):
    return render(request, 'collinear_kaks.html')


def collinear_kaks_file(request):
    return render(request, 'collinear_kaks_file.html')


def mc_result(request):
    return render(request, 'mc_data/mc_result.html')


def mc_result_run(request, title):
    name = title
    return render(request, f'mc_data/mc_run.html', {"name": name})


def pvu_syntenic(request):
    return render(request, 'pvu_syntenic.html')


def Eupl_syntenic(request):
    return render(request, 'Eupl_syntenic.html')


def karyotype(request):
    return render(request, 'karyotype.html')


def chromosome_rearrangement(request):
    return render(request, 'chromosome_rearrangement.html')


def kegg(request):
    return render(request, 'kegg_Adu.html')


def paper(request):
    return render(request, 'paper.html')


def duplicate_removal(request):
    return render(request, 'quchong.html')


def ECH_event(request):
    return event_gene(request)



from django.core.paginator import Paginator
from django.shortcuts import render
# from .models import TEModel







def PCT_event(request):
    return render(request, 'PCT_event_genes.html')


def CCT_event(request):
    return render(request, 'CCT_event_genes.html')


def LSH_event(request):
    return render(request, 'LSH_event_genes.html')


def GST_event(request):
    return render(request, 'GST_event_genes.html')


def B_WGD_event(request):
    return render(request, 'B_WGD_event_genes.html')


def hybridization_Genes(request):
    return render(request, 'hybridization_Genes.html')



def gene_family(request):
    return orthologous(request)



import json
import os
import subprocess
import tempfile
import shutil
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import time
import glob


# 假设 path_get 是您定义的路径变量，类似于 ECH_event 中的使用
# 如果 path_get 没有在当前文件中定义，请确保导入或定义它
# 例如：path_get = settings.BASE_DIR 或某个具体路径

@csrf_exempt
def build_ortho_tree(request):
    """构建系统发育树"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # 解析 JSON 数据
        data = json.loads(request.body)
        selected_genes = data.get('selected_genes', [])
        orthogroup = data.get('orthogroup', '')
        
        if not selected_genes:
            return JsonResponse({'error': 'No genes selected'}, status=400)
        
        # 创建临时文件夹名称
        c = name_set()
        output_directory = f"{path_get}/file_keep/{c}"
        os.makedirs(output_directory, exist_ok=True)
        
        print(f"Output directory: {output_directory}")
        
        # 1. 提取序列到 all.pep
        all_pep_path = os.path.join(output_directory, 'all.pep')
        extracted_count = 0
        sequence_names = []
        
        with open(all_pep_path, 'w') as outfile:
            for gene in selected_genes:
                species = gene.get('species')
                gene_id = gene.get('gene_id')
                
                if not species or not gene_id:
                    continue
                
                pep_file = f"{path_get}/file_keep/species_data/{species}.pep"
                
                if os.path.exists(pep_file):
                    extracted_seq = extract_sequence_from_fasta(pep_file, gene_id)
                    if extracted_seq:
                        outfile.write(extracted_seq)
                        extracted_count += 1
                        sequence_names.append(gene_id)
                        print(f"Extracted {gene_id} from {pep_file}")
                else:
                    print(f"Species file not found: {pep_file}")
        
        if extracted_count == 0:
            return JsonResponse({'error': 'No sequences could be extracted.'}, status=500)
        
        print(f"Extracted {extracted_count} sequences to {all_pep_path}")
        
        # 2. 直接创建 tree 文件（不依赖 draw_tree.py）
        tree_file_path = os.path.join(output_directory, 'all.tree')
        with open(tree_file_path, 'w') as f:
            tree_str = "(" + ",".join([f"'{name}'" for name in sequence_names]) + ");"
            f.write(tree_str)
        print(f"Tree file created: {tree_file_path}")
        
        # 3. 尝试运行 draw_tree2.py 来画图
        draw_tree2_script = os.path.join(output_directory, 'draw_tree2.py')
        
        # 如果 draw_tree2.py 不存在或有问题，直接在 Python 中画图
        image_file = None
        
        if os.path.exists(draw_tree2_script):
            print(f"Trying to run draw_tree2.py...")
            python_exe = sys.executable
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['LANG'] = 'en_US.UTF-8'
            env['LC_ALL'] = 'en_US.UTF-8'
            
            try:
                result = subprocess.run(
                    [python_exe, draw_tree2_script],
                    cwd=output_directory,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    env=env
                )
                
                print(f"draw_tree2.py stdout: {result.stdout}")
                if result.stderr:
                    print(f"draw_tree2.py stderr: {result.stderr}")
                
                # 检查是否生成了图片
                result_png = os.path.join(output_directory, 'result.png')
                if os.path.exists(result_png):
                    image_file = result_png
                    print(f"Found image: {result_png}")
                    
            except Exception as e:
                print(f"Error running draw_tree2.py: {str(e)}")
        
        # 4. 如果 draw_tree2.py 没有生成图片，使用 matplotlib 直接画图
        if not image_file or not os.path.exists(image_file):
            print("draw_tree2.py failed or not found, creating image with matplotlib...")
            try:
                import matplotlib
                matplotlib.use('Agg')
                import matplotlib.pyplot as plt
                from Bio import Phylo
                from io import StringIO
                
                # 读取 tree 文件
                with open(tree_file_path, 'r') as f:
                    newick_str = f.read().strip()
                
                # 解析树
                tree = Phylo.read(StringIO(newick_str), "newick")
                
                # 画图
                fig = plt.figure(figsize=(12, 8), dpi=300)
                ax = fig.add_subplot(1, 1, 1)
                
                # 绘制树
                Phylo.draw(tree, axes=ax, branch_labels=lambda c: f"{c.branch_length:.3f}" if c.branch_length else None)
                
                plt.title(f"Phylogenetic Tree ({extracted_count} sequences)")
                plt.tight_layout()
                
                # 保存图片
                image_file = os.path.join(output_directory, 'result.png')
                plt.savefig(image_file, bbox_inches='tight', dpi=300)
                plt.close()
                print(f"Image created with matplotlib: {image_file}")
                
            except ImportError as e:
                print(f"Matplotlib or Bio not available: {e}")
                # 如果 matplotlib 不可用，创建简单的文本图片
                image_file = create_simple_image(output_directory, sequence_names, extracted_count)
            except Exception as e:
                print(f"Error creating image: {e}")
                image_file = create_simple_image(output_directory, sequence_names, extracted_count)
        
        if not image_file or not os.path.exists(image_file):
            return JsonResponse({'error': 'Failed to generate image'}, status=500)
        
        # 5. 保存图片到 static 目录
        timestamp = int(time.time())
        orthogroup_name = orthogroup if orthogroup else 'ortho_tree'
        orthogroup_name = "".join(c for c in orthogroup_name if c.isalnum() or c in '._-')
        img_filename = f'ortho_tree_{orthogroup_name}_{timestamp}.png'
        
        static_img_dir = os.path.join(settings.BASE_DIR, 'static', 'ortho_trees')
        os.makedirs(static_img_dir, exist_ok=True)
        
        target_img_path = os.path.join(static_img_dir, img_filename)
        shutil.copy2(image_file, target_img_path)
        
        image_url = f'/static/ortho_trees/{img_filename}'
        
        print(f"Tree image saved to: {target_img_path}")
        print(f"Image URL: {image_url}")
        
        # 保存到 session
        request.session['tree_img_png'] = image_url
        request.session.save()  # 强制保存 session
        print(f"Session saved: tree_img_png = {image_url}")

        return JsonResponse({
            'success': True,
            'image_url': image_url,  # 直接返回图片 URL
            'message': 'Tree built successfully'
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error: {error_details}")
        return JsonResponse({'error': str(e), 'details': error_details}, status=500)


def create_simple_image(output_directory, sequence_names, seq_count):
    """创建简单的图片（当 matplotlib 不可用时）"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # 创建图片
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)
        
        # 绘制标题
        draw.text((50, 50), f"Phylogenetic Tree (Simple Mode)", fill='black')
        draw.text((50, 100), f"Total sequences: {seq_count}", fill='black')
        draw.text((50, 130), "Tree structure:", fill='black')
        
        # 绘制树结构（简单的括号表示）
        tree_str = "(" + ",".join(sequence_names[:10]) + ")"
        if len(sequence_names) > 10:
            tree_str += f", ... and {len(sequence_names) - 10} more"
        tree_str += ");"
        
        # 分行显示树字符串
        y = 160
        line_width = 70
        for i in range(0, len(tree_str), line_width):
            draw.text((50, y), tree_str[i:i+line_width], fill='blue')
            y += 20
        
        # 显示基因列表
        y += 20
        draw.text((50, y), "Gene list:", fill='black')
        y += 25
        
        for name in sequence_names[:20]:
            draw.text((50, y), f"  - {name[:60]}", fill='black')
            y += 18
        
        if len(sequence_names) > 20:
            draw.text((50, y), f"  ... and {len(sequence_names) - 20} more", fill='black')
        
        # 保存图片
        img_path = os.path.join(output_directory, 'result.png')
        img.save(img_path)
        print(f"Simple image created: {img_path}")
        return img_path
        
    except ImportError:
        print("PIL not available, cannot create image")
        return None


def extract_sequence_from_fasta(fasta_file, gene_id):
    """从FASTA文件中提取指定基因的序列"""
    try:
        with open(fasta_file, 'r') as f:
            lines = f.readlines()

        sequence_lines = []
        found = False

        for line in lines:
            if line.startswith('>'):
                if found:
                    break
                # 检查是否匹配目标基因ID
                if gene_id in line:
                    found = True
                    sequence_lines.append(line)
            elif found:
                sequence_lines.append(line)

        if sequence_lines:
            return ''.join(sequence_lines)
        return None

    except Exception as e:
        print(f"Error extracting sequence from {fasta_file}: {e}")
        return None


def extract_sequence_from_fasta(fasta_file, gene_id):
    """从FASTA文件中提取指定基因的序列"""
    with open(fasta_file, 'r') as f:
        content = f.read()

    # 支持 >gene_id 或 >sp|gene_id 格式
    lines = content.split('\n')
    sequence_lines = []
    found = False

    for i, line in enumerate(lines):
        if line.startswith('>'):
            if found:
                break
            # 检查是否匹配目标基因ID
            if gene_id in line:
                found = True
                sequence_lines.append(line)
        elif found:
            sequence_lines.append(line)

    if sequence_lines:
        return '\n'.join(sequence_lines) + '\n'
    return None





def search_api(request):
    return render(request, 'search_api.html')


# 花青素的基因
def anthocyanin_genes_index1(request):
    return render(request, 'anthocyanin_genes_index1.html')


def anthocyanin_genes_index2(request):
    return render(request, 'anthocyanin_genes_index2.html')


def anthocyanin_genes_index3(request):
    return render(request, 'anthocyanin_genes_index3.html')


def Anthocyaningenes(request, title):
    name = title
    # return render(request, f'Anthocyanin_genes/anthocyanin_{name}.html', {"name": name})
    return render(request, f'function_genes/anthocyanin_Adu.html', {"name": name})


# 生长素基因
def Auxin_genes_index1(request):
    return render(request, 'Auxin_genes_index1.html')


def Auxin_genes_index2(request):
    return render(request, 'Auxin_genes_index2.html')


def Auxin_genes_index3(request):
    return render(request, 'Auxin_genes_index3.html')


def Auxin(request, title):
    name = title
    # return render(request, f'Anthocyanin_genes/anthocyanin_{name}.html', {"name": name})
    return render(request, f'function_genes/Auxin.html', {"name": name})


# 花发育 基因
def flower_development_index1(request):
    return render(request, 'flower_development_index1.html')


def flower_development_index2(request):
    return render(request, 'flower_development_index2.html')


def flower_development_index3(request):
    return render(request, 'flower_development_index3.html')


def flower_development(request, title):
    name = title
    # return render(request, f'Anthocyanin_genes/anthocyanin_{name}.html', {"name": name})
    return render(request, f'function_genes/flower_development.html', {"name": name})


# 花发育 基因
def pending_flowler_time_index1(request):
    return render(request, 'pending_flowler_time_index1.html')


def pending_flowler_time_index2(request):
    return render(request, 'pending_flowler_time_index2.html')


def pending_flowler_time_index3(request):
    return render(request, 'pending_flowler_time_index3.html')


def pending_flowler_time(request, title):
    name = title
    # return render(request, f'Anthocyanin_genes/anthocyanin_{name}.html', {"name": name})
    return render(request, f'function_genes/pending_flowler_time.html', {"name": name})


# 开花时间 基因
def flowler_time_index1(request):
    return render(request, 'flowler_time_index1.html')


def flowler_time_index2(request):
    return render(request, 'flowler_time_index2.html')


def flowler_time_index3(request):
    return render(request, 'flowler_time_index3.html')


# 开花时间
def flowler_time(request, title):
    name = title
    # return render(request, f'Anthocyanin_genes/anthocyanin_{name}.html', {"name": name})
    return render(request, f'function_genes/flowler_time.html', {"name": name})


# TF 转录因子基因家族-相关基因 -- 页面
def TF_genes_index(request):
    return render(request, 'TF_gene_index.html')


def TF_genes(request, title):
    name = title
    return render(request, f'function_genes/TF_gene_family.html', {"name": name})


# TF 转录因子基因家族-相关基因 -- 页面
def Resistencegenes_genes_index(request):
    return render(request, 'Resistencegenes_genes_index.html')


def Resistencegenes_genes(request, title):
    name = title
    return render(request, f'function_genes/Resistencegenes_genes.html', {"name": name})


# 脂肪酸-相关基因
def Fatty_acid_genes_index(request):
    return render(request, 'Fatty_acid_genes_index.html')


def Fatty_acid_genes(request, title):
    name = title
    return render(request, f'function_genes/Fatty_acid_genes.html', {"name": name})


# 脂肪酸-相关基因
def Nitrogen_fixation_genes_index(request):
    return render(request, 'Nitrogen_fixation_genes_index.html')


def Nitrogen_fixation_genes(request, title):
    name = title
    return render(request, f'function_genes/Nitrogen_fixation_genes.html', {"name": name})


# m6a-Wirters 相关基因 --- 页面
def m6a_wirters_genes_index(request):
    return render(request, 'm6a_wirters_genes_index.html')


def m6a_wirters_genes(request, title):
    name = title
    return render(request, f'function_genes/m6a_wirters_genes.html', {"name": name})


# # m6a-Wirters 相关基因 --- 页面
# def m6a_readers_genes(request):
#     return render(request, 'function_genes/m6a_readers_genes.html')


def m6a_readers_genes(request):
    query_genome = request.POST.get('query_genome', None)
    first_class = request.POST.get('first_class', None)
    second_class = request.POST.get('second_class', None)
    if query_genome is None or first_class is None or second_class is None:
        return render(request, 'function_genes/m6a_readers_genes.html')

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM m6A_table WHERE sp_name = %s AND first_class = %s AND second_class = %s",
            [query_genome, first_class, second_class]
        )
        m6A_result = cursor.fetchall()
    connection.close()
    return render(request, 'm6A_gene_readers.html', {'m6A_result': m6A_result})



# # m6a-Erasers 相关基因 --- 页面
# def m6a_erasers_genes(request):
#     return render(request, 'function_genes/m6a_erasers_genes.html')


def m6a_erasers_genes(request):
    query_genome = request.POST.get('query_genome', None)
    first_class = request.POST.get('first_class', None)
    second_class = request.POST.get('second_class', None)
    if query_genome is None or first_class is None or second_class is None:
        return render(request, 'function_genes/m6a_erasers_genes.html')

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM m6A_table WHERE sp_name = %s AND first_class = %s AND second_class = %s",
            [query_genome, first_class, second_class]
        )
        m6A_result = cursor.fetchall()
    connection.close()
    return render(request, 'function_genes/m6a_erasers_genes.html', {'m6A_result': m6A_result})


# m6a-Wirters 相关基因 --- 页面
def L_pathway_index(request):
    return render(request, 'L_pathway_index.html')


def L_pathway(request, title):
    name = title
    return render(request, f'function_genes/L_pathway.html', {"name": name})


# TE
def TE_index1(request):
    return render(request, 'TE/TE_index1.html')


def TE_index2(request):
    return render(request, 'TE/TE_index2.html')


def TE_index3(request):
    return render(request, 'TE/TE_index3.html')


def TE_sp(request, sp_name):
    sp_name = sp_name
    return render(request, f'TE/{sp_name}.te.html')


def TE_type(request, sp_name, type):
    sp_name = sp_name
    type = type
    return render(request, f'TE/TE.html', {"sp_name": sp_name, "type": type})


# def gene_type(request):
#     return render(request, 'gene_type.html')



def TF_genes_run_index(request):
    query_genome = request.POST.get('query_genome', None)
    tf_type = request.POST.get('tf_type', None)
    tf_name = request.POST.get('tf_name', None)
    if query_genome is None or tf_type is None or tf_name is None:
        return render(request, 'TF_gene_index.html')

    with connection.cursor() as cursor:
        if query_genome == ALL_INTERPROSCAN_SPECIES_VALUE:
            cursor.execute(
                "SELECT * FROM TF_pfam_table WHERE type = %s AND family = %s ORDER BY species, gene_id",
                [tf_type, tf_name]
            )
        else:
            cursor.execute(
                "SELECT * FROM TF_pfam_table WHERE species = %s AND type = %s AND family = %s ORDER BY gene_id",
                [query_genome, tf_type, tf_name]
            )
        tf_result = cursor.fetchall()
    connection.close()
    return render(request, 'TF_gene_run_index.html', {
        'tf_result': tf_result,
        'selected_query_genome': query_genome,
    })


def TF_gene_v2(request, TF_name=None):
    # query_genome = request.POST.get('query_genome', None)
    # tf_type = request.POST.get('tf_type', None)
    # tf_name = request.POST.get('tf_name', None)
    not_found_geneids = []
    if not TF_name:
        return render(request, 'TF_gene_v2.html')
    print(TF_name)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM TF_pfam_table WHERE family = %s",
            [TF_name]
        )
        tf_result = cursor.fetchall()
    connection.close()
    return render(request, 'TF_gene_v2.html', {'not_found_geneids': not_found_geneids, 'result': tf_result})


def kegg_index(request):
    sp_data_1 = request.POST.get("sp_data_1")
    geneid = request.POST.get('geneid', '')
    query_sequence = request.POST.get('query_sequence', '')
    is_all_species = sp_data_1 == ALL_INTERPROSCAN_SPECIES_VALUE
    context = {
        'submitted_geneid': geneid,
        'submitted_query_sequence': query_sequence,
        'selected_species': sp_data_1 or 'Aann',
    }
    if request.method != "POST":
        return render(request, 'kegg_index.html', context)

    if not sp_data_1:
        context['error'] = 'Please select a query genome.'
        return render(request, 'kegg_index.html', context)

    if is_all_species and query_sequence:
        job_id = _create_kegg_all_species_job(query_sequence)
        _start_kegg_all_species_job(job_id)
        context.update({
            'kegg_job_id': job_id,
            'all_species_blast_target_limit': KEGG_ALL_SPECIES_BLAST_MAX_TARGETS,
        })
        return render(request, 'kegg_index.html', context)

    blast_results = None
    if query_sequence:
        c = name_set()
        output_directory = f"{path_get}/file_keep/{c}"
        temp_fasta_file = write_fasta_file(query_sequence, output_directory)

        nucl_or_prot = "prot"
        species_data = sp_data_1
        e = "1e-5"
        blast_result_file = os.path.join(output_directory, "result.txt")
        blast_return_code = run_blastp(temp_fasta_file, nucl_or_prot, species_data, e, blast_result_file)
        if blast_return_code != 0 or not os.path.exists(blast_result_file):
            context['error'] = 'BLAST failed. Please check BLAST+ and the protein database for the selected species.'
            return render(request, 'kegg_index.html', context)
        blast_results, geneids = parse_blastp_result(blast_result_file)
    else:
        geneids = geneid.replace('\r', '').split('\n')

    geneids = [item.strip() for item in geneids if item and item.strip()]
    if not geneids:
        if query_sequence:
            context['error'] = 'No BLAST hits were found for the submitted protein sequence.'
        else:
            context['error'] = 'Please enter at least one gene ID, KO number, or protein sequence.'
        return render(request, 'kegg_index.html', context)

    found_geneids = []
    not_found_geneids = []
    result = []
    result_limit_reached = False

    with connection.cursor() as cursor:
        for term in geneids:
            remaining = KEGG_RESULT_LIMIT - len(result)
            if remaining <= 0:
                result_limit_reached = True
                break

            if term.startswith("K") and len(term) == 6:
                where_clause = "ko = %s"
                params = [term]
            elif ";" in term:
                where_clause = "definition LIKE %s"
                params = ["%" + term + "%"]
            else:
                where_clause = "gene_id = %s"
                params = [term]

            if not is_all_species:
                where_clause += " AND sp_name = %s"
                params.append(sp_data_1)

            cursor.execute(
                f"SELECT * FROM kegg_table WHERE {where_clause} LIMIT %s",
                params + [remaining + 1],
            )
            rows = cursor.fetchall()

            if rows:
                if len(rows) > remaining:
                    result_limit_reached = True
                    rows = rows[:remaining]
                result.extend(rows)
                found_geneids.append(term)
            else:
                not_found_geneids.append(term)

            if result_limit_reached:
                break

    connection.close()
    context.update({
        'not_found_geneids': not_found_geneids,
        'result': result,
        'blast_results': blast_results,
        'result_limit': KEGG_RESULT_LIMIT,
        'result_limit_reached': result_limit_reached,
    })
    if not result:
        context['error'] = 'No matching KEGG annotations were found for the current query.'
    return render(request, 'kegg_index.html', context)


def kegg_job_status(request, job_id):
    if not _kegg_job_is_valid(job_id):
        return JsonResponse({'status': 'error', 'message': 'Invalid KEGG job id.'}, status=404)

    status = _read_kegg_job_status(job_id)
    if status.get('status') == 'done':
        status['result_url'] = reverse('kegg_job_result_url', args=[job_id])
        status['download_url'] = reverse('kegg_job_download_url', args=[job_id])
        if os.path.isfile(_kegg_job_blast_path(job_id)):
            status['blast_download_url'] = reverse('kegg_job_blast_download_url', args=[job_id])
    return JsonResponse(status)


def kegg_job_download(request, job_id):
    if not _kegg_job_is_valid(job_id):
        return HttpResponse('Invalid KEGG job id.', status=404)

    result_path = _kegg_job_result_path(job_id)
    if not os.path.isfile(result_path):
        return HttpResponse('The KEGG result file is not ready.', status=404)

    return FileResponse(
        open(result_path, 'rb'),
        as_attachment=True,
        filename=f'kegg_all_species_annotations_{job_id}.tsv',
    )


def kegg_job_blast_download(request, job_id):
    if not _kegg_job_is_valid(job_id):
        return HttpResponse('Invalid KEGG job id.', status=404)

    blast_path = _kegg_job_blast_path(job_id)
    if not os.path.isfile(blast_path):
        return HttpResponse('The BLAST hit file is not ready.', status=404)

    return FileResponse(
        open(blast_path, 'rb'),
        as_attachment=True,
        filename=f'kegg_all_species_blast_hits_{job_id}.tsv',
    )


def kegg_job_result(request, job_id):
    if not _kegg_job_is_valid(job_id):
        return HttpResponse('Invalid KEGG job id.', status=404)

    result_path = _kegg_job_result_path(job_id)
    headers, rows, truncated, total_rows = _read_tsv_result_table(result_path)
    return render(request, 'job_tsv_result.html', {
        'job_id': job_id,
        'page_title': 'KEGG-pathways Results',
        'table_id': 'keggJobTable',
        'filename': f'kegg_selected_rows_{job_id}.txt',
        'empty_message': 'The KEGG result file is not ready or contains no matching annotations.',
        'result_headers': headers,
        'result': rows,
        'result_count': total_rows,
        'shown_count': len(rows),
        'truncated': truncated,
        'table_limit': JOB_RESULT_TABLE_LIMIT,
        'result_file_ready': os.path.isfile(result_path),
        'download_url': reverse('kegg_job_download_url', args=[job_id]) if os.path.isfile(result_path) else None,
        'blast_download_url': reverse('kegg_job_blast_download_url', args=[job_id]) if os.path.isfile(_kegg_job_blast_path(job_id)) else None,
    })



def gene_type(request):
    sp_data_1 = request.POST.get("sp_data_1", None)
    geneid = request.POST.get('geneid', None)
    query_sequence = request.POST.get('query_sequence')
    if sp_data_1 is None or geneid is None:
        return render(request, 'gene_type.html')
    if query_sequence:
        c = name_set()
        output_directory = f"{path_get}/file_keep/{c}"
        temp_fasta_file = write_fasta_file(query_sequence, output_directory)

        nucl_or_prot = "prot"
        species_data = sp_data_1
        e = "1e-5"
        blast_result_file = os.path.join(output_directory, "result.txt")
        run_blastp(temp_fasta_file, nucl_or_prot, species_data, e, blast_result_file)
        blast_results, geneids = parse_blastp_result(blast_result_file)
    else:
        geneids = geneid.replace('\r', '').split('\n')

    geneid_placeholders = ','.join(['%s'] * len(geneids))
    sql_query = f"SELECT * FROM Genetype_table WHERE gene1 IN ({geneid_placeholders})"
    with connection.cursor() as cursor:
        cursor.execute(sql_query, geneids)
        result = cursor.fetchall()
    found_geneids = [row[2] for row in result if len(row) > 2 and row[2]]
    not_found_geneids = [item for item in geneids if item not in found_geneids]
    connection.close()
    return render(request, '../templates/gene_type.html', {
        'not_found_geneids': not_found_geneids,
        'result': result,
        'blast_results': blast_results if query_sequence else None  # 如果没有查询序列，则不返回 blast_results})
    })



def collinear_dotplot(request):
    return dotplot(request)





# ===================== DataTables JSON data APIs =====================
DATA_TABLE_JSON_NAME_RE = re.compile(r'^[A-Za-z0-9_.-]+$')


def _is_safe_data_token(value):
    return bool(value) and DATA_TABLE_JSON_NAME_RE.fullmatch(str(value)) is not None


def _read_static_json_response(relative_parts):
    """Return a JSON file from static/ through Django, bypassing Nginx /static/ handling."""
    candidate_paths = [os.path.join(settings.BASE_DIR, 'static', *relative_parts)]
    static_root = getattr(settings, 'STATIC_ROOT', None)
    if static_root:
        candidate_paths.append(os.path.join(static_root, *relative_parts))

    for json_path in candidate_paths:
        if os.path.isfile(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as json_file:
                    payload = json.load(json_file)
                if relative_parts[0] == 'collinear_kaks_mc':
                    from .data_integrity import available_analysis_links
                    payload = available_analysis_links(payload, os.path.join(settings.BASE_DIR, 'static'))
                return JsonResponse(payload, safe=False)
            except json.JSONDecodeError as exc:
                return JsonResponse({
                    'data': [],
                    'error': f'JSON format error in {json_path}: {exc}'
                }, status=500)
            except Exception as exc:
                return JsonResponse({
                    'data': [],
                    'error': f'Could not read {json_path}: {exc}'
                }, status=500)

    return JsonResponse({
        'data': [],
        'error': 'JSON file was not found.',
        'checked_paths': candidate_paths,
    }, status=404)


def transcriptome_run_data(request):
    sp_name = request.GET.get('sp_name')
    data_type = request.GET.get('type')
    if not (_is_safe_data_token(sp_name) and _is_safe_data_token(data_type)):
        return JsonResponse({
            'data': [],
            'error': 'Invalid transcriptome data parameters.'
        }, status=400)

    filename = f'{sp_name}_{data_type}.json'
    return _read_static_json_response(['transcriptome_json', filename])


def collinear_kaks_data(request):
    return _read_static_json_response(['collinear_kaks_mc', 'colinearscan_kaks.json'])


def dotplot_data(request):
    return _read_static_json_response(['collinear_kaks_mc', 'dotplot.json'])


HIERARCHICAL_ALIGNMENT_TABLES = {
    'Hean': {
        'model': HierarchicalAlignment_Hean,
        'filename': 'Hierarchical_alignment_Hean_selected_rows.txt',
        'fields': (
            'Hean_1', 'Cobi_1', 'Bial_1', 'Bial_2', 'Dapi_1', 'Dapi_2',
            'Hetu_1', 'Hetu_2', 'Hetu_3', 'Amtr_1', 'Smso_1', 'Smso_2',
            'Taer_1', 'Fro_1', 'Fso_1', 'Ftr_1', 'Fra_1', 'Fli_1',
            'Stre_1', 'Mimi_1', 'Hean_2', 'Cobi_2', 'Bial_3', 'Bial_4',
            'Dapi_3', 'Dapi_4', 'Hetu_4', 'Hetu_5', 'Hetu_6', 'Amtr_2',
            'Smso_3', 'Smso_4', 'Taer_2', 'Fro_2', 'Fso_2', 'Ftr_2',
            'Fra_2', 'Fli_2', 'Stre_2', 'Mimi_2',
        ),
    },
    'Lssa_all': {
        'model': HierarchicalAlignment_Lssa_all,
        'filename': 'Hierarchical_alignment_Lssa_all_selected_rows.txt',
        'row_id_field': 'number',
        'fields': (
            'Arla_1', 'Arla_2', 'Arla_3', 'Gehy_1', 'Armi_1', 'Sain_1',
            'Ceso_1', 'Cati_1', 'Ccar_1', 'Cien_1', 'Cich_1', 'Lssa_1',
            'Laca_1', 'Tako_1', 'Tamo_1', 'Pslu_1',
            'Lomi_1', 'Lomi_2', 'Enbr_1', 'Ecan_1', 'Soca_1', 'Glco_1',
            'Artr_1', 'Aary_1', 'Aary_2', 'Aann_1', 'Chma_1', 'Chmo_1',
            'Chmo_2', 'Chmo_3', 'Chla_1', 'Chna_1', 'Cind_1', 'Pdy_1',
            'Cobi_1', 'Hean_1', 'Bial_1', 'Bial_2', 'Dapi_1', 'Dapi_2',
            'Hetu_1', 'Hetu_2', 'Hetu_3', 'Amtr_1', 'Smso_1', 'Smso_2',
            'Taer_1', 'Fro_1', 'Fso_1', 'Ftr_1', 'Fra_1', 'Fli_1',
            'Stre_1', 'Mimi_1', 'Cobi_2', 'Hean_2', 'Bial_3', 'Bial_4',
            'Dapi_3', 'Dapi_4', 'Hetu_4', 'Hetu_5', 'Hetu_6', 'Amtr_2',
            'Smso_3', 'Smso_4', 'Taer_2', 'Fro_2', 'Fso_2', 'Ftr_2',
            'Fra_2', 'Fli_2', 'Stre_2', 'Mimi_2',
        ),
    },
    'Vivi': {
        'model': HierarchicalAlignment_Vivi,
        'filename': 'Hierarchical_alignment_Vivi_selected_rows.txt',
        'fields': (
            'Vivi_1', 'Arla_1', 'Armi_1', 'Sain_1', 'Ceso_1', 'Cati_1',
            'Ccar_1', 'Cien_1', 'Cich_1', 'Lssa_1', 'Laca_1', 'Tako_1',
            'Tamo_1', 'Pslu_1', 'Lomi_1', 'Lomi_2', 'Enbr_1', 'Ecan_1',
            'Soca_1', 'Glco_1', 'Artr_1', 'Aary_1', 'Aary_2', 'Aann_1',
            'Chma_1', 'Chmo_1', 'Chmo_2', 'Chmo_3', 'Chla_1', 'Chna_1',
            'Cind_1', 'Pdy_1', 'Cobi_1', 'Hean_1', 'Bial_1', 'Bial_2',
            'Dapi_1', 'Dapi_2', 'Hetu_1', 'Hetu_2', 'Hetu_3', 'Amtr_1',
            'Smso_1', 'Smso_2', 'Taer_1', 'Fro_1', 'Fso_1', 'Ftr_1',
            'Fra_1', 'Fli_1', 'Stre_1', 'Mimi_1', 'Cobi_2', 'Hean_2',
            'Bial_3', 'Bial_4', 'Dapi_3', 'Dapi_4', 'Hetu_4', 'Hetu_5',
            'Hetu_6', 'Amtr_2', 'Smso_3', 'Smso_4', 'Taer_2', 'Fro_2',
            'Fso_2', 'Ftr_2', 'Fra_2', 'Fli_2',
        ),
    },
    'Eupl': {
        'model': HierarchicalAlignment_Eupl,
        'filename': 'Hierarchical_alignment_Eupl_selected_rows.txt',
        'fields': (
            'Eupl_1', 'Eupl_2', 'Nenu_1', 'Nenu_2', 'Tesi_1', 'Tesi_2',
            'Tesi_3', 'Tesi_4', 'Busi_1', 'Busi_2', 'Vivi_1', 'Vivi_2',
            'Vivi_3', 'Nin_1', 'Nin_2', 'Nin_3', 'Arla_1', 'Arla_2',
            'Arla_3', 'Arla_4', 'Arla_5', 'Arla_6', 'Arla_7', 'Arla_8',
            'Arla_9',
        ),
    },
}


def _parse_datatables_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _hierarchical_gene_link(gene_id):
    text = '' if gene_id is None else str(gene_id)
    escaped_text = html.escape(text)
    if not text or text == '.':
        return escaped_text
    return f'<a href="{reverse("gene_detail", kwargs={"geneid": text})}">{escaped_text}</a>'


def _hierarchical_alignment_queryset(request, config):
    fields = config['fields']
    row_id_field = config.get('row_id_field', 'hhh_number')
    queryset = config['model'].objects.all()
    search_value = request.GET.get('search[value]', '').strip()

    if search_value:
        search_filter = Q()
        if search_value.isdigit():
            search_filter |= Q(**{row_id_field: int(search_value)})
        for field in fields:
            search_filter |= Q(**{f'{field}__icontains': search_value})
        queryset = queryset.filter(search_filter)

    order_column = _parse_datatables_int(request.GET.get('order[0][column]'), 0)
    order_direction = request.GET.get('order[0][dir]', 'asc')
    if order_column > 0 and order_column <= len(fields):
        order_field = fields[order_column - 1]
        if order_direction == 'desc':
            order_field = f'-{order_field}'
        queryset = queryset.order_by(order_field, row_id_field)
    else:
        queryset = queryset.order_by(row_id_field)

    return queryset


def _hierarchical_excluded_row_ids(request):
    excluded_ids = set()
    for raw_value in request.GET.getlist('exclude_row_id'):
        for value in str(raw_value).split(','):
            value = value.strip()
            if not value:
                continue
            try:
                excluded_ids.add(int(value))
            except ValueError:
                continue
    return excluded_ids


def _hierarchical_alignment_tsv_response(queryset, config, excluded_row_ids=None):
    fields = config['fields']
    row_id_field = config.get('row_id_field', 'hhh_number')
    if excluded_row_ids:
        queryset = queryset.exclude(**{f'{row_id_field}__in': excluded_row_ids})

    def rows():
        yield '\t'.join(fields) + '\n'
        for values in queryset.values_list(*fields).iterator(chunk_size=1000):
            yield '\t'.join('' if value is None else str(value) for value in values) + '\n'

    response = StreamingHttpResponse(rows(), content_type='text/tab-separated-values; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{config["filename"]}"'
    return response


def hierarchical_alignments_table_data(request, reference):
    config = HIERARCHICAL_ALIGNMENT_TABLES.get(reference)
    if not config:
        return JsonResponse({
            'data': [],
            'error': 'Unknown hierarchical alignment table.'
        }, status=404)

    queryset = _hierarchical_alignment_queryset(request, config)
    if request.GET.get('export') == 'tsv':
        return _hierarchical_alignment_tsv_response(queryset, config, _hierarchical_excluded_row_ids(request))

    draw = _parse_datatables_int(request.GET.get('draw'), 0)
    start = max(_parse_datatables_int(request.GET.get('start'), 0), 0)
    length = _parse_datatables_int(request.GET.get('length'), 10)
    if length < 0:
        length = 100
    length = max(1, min(length, 100))

    total_records = config['model'].objects.count()
    filtered_records = queryset.count()
    page_rows = queryset[start:start + length]

    data = []
    row_id_field = config.get('row_id_field', 'hhh_number')
    for row in page_rows:
        row_id = html.escape(str(getattr(row, row_id_field)))
        checkbox = (
            '<input type="checkbox" '
            'class="row-checkbox form-check-input" '
            f'data-row-id="{row_id}">'
        )
        data.append([checkbox] + [
            _hierarchical_gene_link(getattr(row, field, ''))
            for field in config['fields']
        ])

    return JsonResponse({
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': filtered_records,
        'data': data,
    })
# =================== End DataTables JSON data APIs ===================

def transcriptome(request):
    return render(request, 'transcriptome.html')


def transcriptome_run(request):
    sp_data_1 = request.POST.get("sp_data_1", None)
    sp_data_2 = request.POST.get("sp_data_2", None)
    return render(request, f'transcriptome_run.html', {"sp_name": sp_data_1, "type": sp_data_2})


def geneExpression(request):
    from .data_integrity import expression_page
    return expression_page(request)


def m6A_gene(request):
    query_genome = request.POST.get('query_genome', None)
    first_class = request.POST.get('first_class', None)
    hmm_id = request.POST.get('hmm_id', None) or request.POST.get('second_class', None)
    is_all_species = query_genome == ALL_INTERPROSCAN_SPECIES_VALUE
    context = {
        'selected_query_genome': query_genome or 'Aann',
        'selected_first_class': first_class or 'readers',
        'selected_hmm_id': hmm_id or 'YTH',
        'has_searched': False,
    }
    if query_genome is None or first_class is None or hmm_id is None:
        return render(request, 'm6A_gene.html', context)

    with connection.cursor() as cursor:
        if is_all_species:
            cursor.execute(
                """
                SELECT gene_id, sp_name, first_class, hmm_id, start, end, pfam_id, second_class, e_value, clan
                FROM m6A_table
                WHERE first_class = %s AND hmm_id = %s
                ORDER BY sp_name, gene_id, start
                """,
                [first_class, hmm_id]
            )
        else:
            cursor.execute(
                """
                SELECT gene_id, sp_name, first_class, hmm_id, start, end, pfam_id, second_class, e_value, clan
                FROM m6A_table
                WHERE sp_name = %s AND first_class = %s AND hmm_id = %s
                ORDER BY gene_id, start
                """,
                [query_genome, first_class, hmm_id]
            )
        m6A_result = cursor.fetchall()
    connection.close()
    context.update({
        'm6A_result': m6A_result,
        'has_searched': True,
    })
    return render(request, 'm6A_gene.html', context)


def interproscan_index(request):
    if request.method != "POST":
        return render(request, 'interproscan_index.html')

    geneid = (request.POST.get('geneid') or '').strip()
    sp_data_1 = (request.POST.get("sp_data_1") or '').strip()
    query_sequence = (request.POST.get('query_sequence') or '').strip()
    is_all_species = sp_data_1 == ALL_INTERPROSCAN_SPECIES_VALUE
    selected_databases = [
        db_name for db_name in INTERPROSCAN_DATABASES
        if request.POST.get(db_name) == 'on'
    ]
    species_scope = list(INTERPROSCAN_SPECIES) if is_all_species else [sp_data_1]

    context = {
        'submitted_geneid': geneid,
        'submitted_query_sequence': query_sequence,
        'selected_species': sp_data_1,
        'selected_databases': selected_databases,
        'searched_all_species': is_all_species,
    }

    if not is_all_species and sp_data_1 not in INTERPROSCAN_SPECIES:
        context['error'] = 'Please choose a valid species before searching.'
        return render(request, 'interproscan_index.html', context)

    if not selected_databases:
        context['error'] = 'Please select at least one analysis database.'
        return render(request, 'interproscan_index.html', context)

    if not geneid and not query_sequence:
        context['error'] = 'Please enter at least one gene ID, keyword, or protein sequence.'
        return render(request, 'interproscan_index.html', context)

    if is_all_species and query_sequence:
        job_id = _create_interproscan_all_species_job(query_sequence, selected_databases)
        _start_interproscan_all_species_job(job_id)
        context.update({
            'interproscan_job_id': job_id,
            'all_species_blast_target_limit': INTERPROSCAN_ALL_SPECIES_BLAST_MAX_TARGETS,
        })
        return render(request, 'interproscan_index.html', context)

    blast_results = None
    search_terms_by_species = {}
    if query_sequence:
        c = name_set()
        output_directory = f"{path_get}/file_keep/{c}"
        temp_fasta_file = write_fasta_file(query_sequence, output_directory)

        nucl_or_prot = "prot"
        e = "1e-5"
        if is_all_species:
            context['all_species_blast_target_limit'] = INTERPROSCAN_ALL_SPECIES_BLAST_MAX_TARGETS
            blast_result_file = os.path.join(output_directory, "result_all_species.txt")
            db_paths = [
                f"{path_get}/static/blast_match_database/{nucl_or_prot}/{species_code}"
                for species_code in INTERPROSCAN_SPECIES
            ]
            blast_return_code = run_blastp(
                temp_fasta_file,
                nucl_or_prot,
                ALL_INTERPROSCAN_SPECIES_VALUE,
                e,
                blast_result_file,
                db_paths=db_paths,
                max_target_seqs=INTERPROSCAN_ALL_SPECIES_BLAST_MAX_TARGETS,
            )
            if blast_return_code != 0:
                context['error'] = (
                    'All-species BLAST failed to run on the server. '
                    'Please check that blastdb_aliastool is available and all BLAST databases exist.'
                )
                return render(request, 'interproscan_index.html', context)
            if not os.path.exists(blast_result_file):
                geneids = []
                blast_results = []
            else:
                blast_results, geneids = parse_blastp_result(blast_result_file)
            for item in geneids:
                gene_id, species_code = _resolve_blast_subject_gene(item)
                if species_code in INTERPROSCAN_SPECIES:
                    species_terms = search_terms_by_species.setdefault(species_code, [])
                    if gene_id not in species_terms:
                        species_terms.append(gene_id)
        else:
            blast_results = []
            for species_data in species_scope:
                blast_result_file = os.path.join(output_directory, "result.txt")
                run_blastp(temp_fasta_file, nucl_or_prot, species_data, e, blast_result_file)
                if not os.path.exists(blast_result_file):
                    continue
                species_blast_results, geneids = parse_blastp_result(blast_result_file)
                blast_results.extend(species_blast_results)
                search_terms_by_species[species_data] = [
                    item.strip()
                    for item in geneids
                    if item and item.strip()
                ]
        search_terms = [
            term
            for terms in search_terms_by_species.values()
            for term in terms
        ]
    else:
        search_terms = [
            item.strip().rstrip(';')
            for item in geneid.replace('\r', '').split('\n')
            if item.strip()
        ]

    if not search_terms:
        if query_sequence:
            context['error'] = (
                'No BLAST hits with recognizable AGRP gene IDs were found for the submitted sequence.'
            )
        else:
            context['error'] = 'No matching gene IDs were found for the submitted query.'
        if blast_results is not None:
            context['blast_results'] = blast_results
        return render(request, 'interproscan_index.html', context)

    not_found_geneids = []
    result = []
    seen_rows = set()
    result_limit_reached = False
    analysis_placeholders = ','.join(['%s'] * len(selected_databases))

    def fetch_interproscan_rows(cursor, species_code, term, match_gene_id, limit):
        if limit <= 0:
            return []

        table_name = f"{species_code}_interproscan_table"
        if match_gene_id:
            sql_query = f"SELECT * FROM {table_name} WHERE analysis IN ({analysis_placeholders}) AND gene_id = %s LIMIT %s"
            query_params = selected_databases + [term]
        else:
            sql_query = f"SELECT * FROM {table_name} WHERE analysis IN ({analysis_placeholders}) AND description LIKE %s LIMIT %s"
            query_params = selected_databases + [f"%{term}%"]
        query_params.append(limit)
        cursor.execute(sql_query, query_params)
        return cursor.fetchall()

    def add_result_rows(species_code, rows):
        nonlocal result_limit_reached
        for row in rows:
            if len(result) >= INTERPROSCAN_RESULT_LIMIT:
                result_limit_reached = True
                return
            row_key = (species_code, row)
            if row_key not in seen_rows:
                seen_rows.add(row_key)
                result.append(_format_interproscan_result_row(species_code, row))

    def fetch_and_add_interproscan_rows(cursor, species_code, term, match_gene_id):
        nonlocal result_limit_reached
        remaining = INTERPROSCAN_RESULT_LIMIT - len(result)
        if remaining <= 0:
            result_limit_reached = True
            return False

        rows = fetch_interproscan_rows(cursor, species_code, term, match_gene_id, remaining + 1)
        found_rows = bool(rows)
        if len(rows) > remaining:
            result_limit_reached = True
            rows = rows[:remaining]
        add_result_rows(species_code, rows)
        return found_rows

    with connection.cursor() as cursor:
        if query_sequence:
            for species_code, terms in search_terms_by_species.items():
                for term in terms:
                    found_rows = fetch_and_add_interproscan_rows(cursor, species_code, term, True)
                    if found_rows:
                        if result_limit_reached:
                            break
                    else:
                        not_found_geneids.append(term)
                if result_limit_reached:
                    break
        else:
            for term in search_terms:
                term_found = False
                if is_all_species:
                    resolved_species = _resolve_gene_species(term)
                    if resolved_species and _is_interpro_gene_id(term, resolved_species):
                        query_species_codes = [resolved_species]
                        match_gene_id = True
                    else:
                        query_species_codes = species_scope
                        match_gene_id = False
                else:
                    query_species_codes = species_scope
                    match_gene_id = _is_interpro_gene_id(term, sp_data_1)

                for species_code in query_species_codes:
                    found_rows = fetch_and_add_interproscan_rows(cursor, species_code, term, match_gene_id)
                    if found_rows:
                        term_found = True
                    if result_limit_reached:
                        break

                if not term_found:
                    not_found_geneids.append(term)
                if result_limit_reached:
                    break

    context.update({
        'not_found_geneids': not_found_geneids,
        'result': result,
        'result_limit': INTERPROSCAN_RESULT_LIMIT,
        'result_limit_reached': result_limit_reached,
    })

    if blast_results is not None:
        context['blast_results'] = blast_results

    if not result:
        context['error'] = 'No matching annotations were found for the current query.'

    return render(request, 'interproscan_index.html', context)


def interproscan_job_status(request, job_id):
    if not _interproscan_job_is_valid(job_id):
        return JsonResponse({'status': 'error', 'message': 'Invalid InterProScan job id.'}, status=404)

    status = _read_interproscan_job_status(job_id)
    if status.get('status') == 'done':
        status['result_url'] = reverse('interproscan_job_result_url', args=[job_id])
        status['download_url'] = reverse('interproscan_job_download_url', args=[job_id])
        if os.path.isfile(_interproscan_job_blast_path(job_id)):
            status['blast_download_url'] = reverse('interproscan_job_blast_download_url', args=[job_id])
    return JsonResponse(status)


def interproscan_job_download(request, job_id):
    if not _interproscan_job_is_valid(job_id):
        return HttpResponse('Invalid InterProScan job id.', status=404)

    result_path = _interproscan_job_result_path(job_id)
    if not os.path.isfile(result_path):
        return HttpResponse('The InterProScan result file is not ready.', status=404)

    return FileResponse(
        open(result_path, 'rb'),
        as_attachment=True,
        filename=f'interproscan_all_species_annotations_{job_id}.tsv',
    )


def interproscan_job_blast_download(request, job_id):
    if not _interproscan_job_is_valid(job_id):
        return HttpResponse('Invalid InterProScan job id.', status=404)

    blast_path = _interproscan_job_blast_path(job_id)
    if not os.path.isfile(blast_path):
        return HttpResponse('The BLAST hit file is not ready.', status=404)

    return FileResponse(
        open(blast_path, 'rb'),
        as_attachment=True,
        filename=f'interproscan_all_species_blast_hits_{job_id}.tsv',
    )


def interproscan_job_result(request, job_id):
    if not _interproscan_job_is_valid(job_id):
        return HttpResponse('Invalid InterProScan job id.', status=404)

    result_path = _interproscan_job_result_path(job_id)
    headers, rows, truncated, total_rows = _read_tsv_result_table(result_path)
    return render(request, 'job_tsv_result.html', {
        'job_id': job_id,
        'page_title': 'InterProScan Annotation Results',
        'table_id': 'interproscanJobTable',
        'filename': f'interproscan_selected_rows_{job_id}.txt',
        'empty_message': 'The InterProScan result file is not ready or contains no matching annotations.',
        'result_headers': headers,
        'result': rows,
        'result_count': total_rows,
        'shown_count': len(rows),
        'truncated': truncated,
        'table_limit': JOB_RESULT_TABLE_LIMIT,
        'result_file_ready': os.path.isfile(result_path),
        'download_url': reverse('interproscan_job_download_url', args=[job_id]) if os.path.isfile(result_path) else None,
        'blast_download_url': reverse('interproscan_job_blast_download_url', args=[job_id]) if os.path.isfile(_interproscan_job_blast_path(job_id)) else None,
    })


def _orthologous_overview_export(request):
    exclude_ids = [
        row_id.strip()
        for row_id in request.GET.getlist('exclude_row_id')
        if re.fullmatch(r'[A-Za-z0-9_.-]+', row_id.strip())
    ]

    def stream_rows():
        class Echo:
            def write(self, value):
                return value

        writer = csv.writer(Echo(), delimiter='\t', lineterminator='\n')
        with connection.cursor() as cursor:
            cursor.execute("SHOW COLUMNS FROM Orthofinder_num_table")
            columns = [row[0] for row in cursor.fetchall()]
            yield writer.writerow(columns)

            sql = "SELECT * FROM Orthofinder_num_table"
            params = []
            if exclude_ids:
                placeholders = ','.join(['%s'] * len(exclude_ids))
                sql += f" WHERE orthogroup NOT IN ({placeholders})"
                params.extend(exclude_ids)
            sql += " ORDER BY orthogroup"

            cursor.execute(sql, params)
            for row in cursor:
                yield writer.writerow(row)

    response = StreamingHttpResponse(stream_rows(), content_type='text/tab-separated-values; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="orthologous_orthogroups_selected_rows.tsv"'
    return response


def orthologous(request):
    geneid = request.POST.get('geneid', None)
    sp_data_1 = request.POST.get("sp_data_1", None)
    selected_value = request.POST.get('selected_value', None)
    orthogroup = request.POST.get('orthogroup', None)
    og_type = request.POST.get('og_type', None)
    query_sequence = request.POST.get('query_sequence', None)
    result_block = None  # 初始化

    if sp_data_1 is None or geneid is None:
        if request.GET.get('export') == 'tsv':
            return _orthologous_overview_export(request)

        per_page = 10
        page_number = request.GET.get('page', 1)

        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM Orthofinder_num_table")
            total_entries = cursor.fetchone()[0]

        paginator = Paginator(range(total_entries), per_page)
        page_obj = paginator.get_page(page_number)
        offset = (page_obj.number - 1) * per_page

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM Orthofinder_num_table ORDER BY orthogroup LIMIT %s OFFSET %s",
                [per_page, offset],
            )
            page_entries = cursor.fetchall()

        overview_page_range = [
            '...' if page is paginator.ELLIPSIS else page
            for page in paginator.get_elided_page_range(
                number=page_obj.number,
                on_each_side=2,
                on_ends=1,
            )
        ]

        return render(request, 'orthologous.html', {
            'alignment_data': page_entries,  # 当前页的数据
            'page_obj': page_obj,  # 当前分页对象
            'total_pages': paginator.num_pages,  # 总页数
            'current_page': page_obj.number,  # 当前页码
            'overview_page_range': overview_page_range,
            'hhh_page': "NO"
        })

    if query_sequence:
        c = name_set()
        output_directory = f"{path_get}/file_keep/{c}"
        blast_results, geneids = _run_selected_species_blast(query_sequence, output_directory, sp_data_1)
        if not geneids:
            return render(request, 'orthologous.html', {
                'geneid': '',
                'sp_data_1': sp_data_1,
                'blast_results': blast_results,
                'hhh_page': "NO",
            })
        geneid = geneids[0]
    else:
        geneid = geneid

    sql_query_genes_table = f"SELECT orthogroup FROM Orthofinder_genes_table WHERE gene_id = %s"
    with connection.cursor() as cursor:
        cursor.execute(sql_query_genes_table, [geneid])
        orthogroup_row = cursor.fetchone()
        if orthogroup_row:
            orthogroup = orthogroup_row[0]

    print(sql_query_genes_table)
    result = None
    orthofinder_genes = None

    if orthogroup:
        sql_query_number_table = "SELECT * FROM Orthofinder_num_table WHERE orthogroup = %s"
        with connection.cursor() as cursor:
            cursor.execute(sql_query_number_table, [orthogroup])
            result = cursor.fetchall()

        sql_block_query_number_table = "SELECT * FROM block_Orthogroups_number WHERE orthogroup = %s"
        with connection.cursor() as cursor:
            cursor.execute(sql_block_query_number_table, [orthogroup])
            result_block = cursor.fetchall()

        if selected_value:
            if selected_value == "Total":
                if og_type == "block":
                    sql_query = "SELECT * FROM block_Orthofinder_genes_table WHERE orthogroup = %s"
                    with connection.cursor() as cursor:
                        cursor.execute(sql_query, [orthogroup])
                        orthofinder_genes = cursor.fetchall()
                else:
                    sql_query = "SELECT * FROM Orthofinder_genes_table WHERE orthogroup = %s"
                    with connection.cursor() as cursor:
                        cursor.execute(sql_query, [orthogroup])
                        orthofinder_genes = cursor.fetchall()
            else:
                if og_type == "block":
                    sql_query = "SELECT * FROM block_Orthofinder_genes_table WHERE orthogroup = %s AND species = %s"
                    with connection.cursor() as cursor:
                        cursor.execute(sql_query, [orthogroup, selected_value])
                        orthofinder_genes = cursor.fetchall()
                else:
                    sql_query = "SELECT * FROM Orthofinder_genes_table WHERE orthogroup = %s AND species = %s"
                    with connection.cursor() as cursor:
                        cursor.execute(sql_query, [orthogroup, selected_value])
                        orthofinder_genes = cursor.fetchall()

    connection.close()
    # first_value = result[0][-1]
    return render(request, 'orthologous.html', {
        'result': result,
        # 'first_value': first_value,
        'result_block': result_block,
        'genes_table': orthofinder_genes,
        'geneid': geneid,
        'sp_data_1': sp_data_1,
        'blast_results': blast_results if query_sequence else None  # 如果没有查询序列，则不返回 blast_results
    })



# Hean 为参考的共线性列表
def hierarchical_alignments_Hean(request):
    global blast_results
    geneid = request.POST.get('geneid')
    sp_data_1 = request.POST.get("sp_data_1")
    query_sequence = request.POST.get('query_sequence')

    # 设置 line_number 默认值为 4
    line_number = 4

    # 初始化变量
    blast_results = None
    genes_table = []  # 初始化为空列表
    result_objects = []
    temp_modified_data = []
    page_obj = None
    total_pages = None
    orthofinder_strand_genes = []  # 初始化这个变量

    if sp_data_1 is None or geneid is None:
        alignment_data_query = HierarchicalAlignment_Hean.objects.all()
        per_page = 10
        paginator = Paginator(alignment_data_query, per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        total_pages = paginator.num_pages

        result_objects = page_obj.object_list[:]
        result_objects_2 = page_obj.object_list[:]
        gene_strand_result = result_objects_2.values_list("hhh_number", "Hean_1", "Cobi_1", "Bial_1", "Bial_2",
                                                          "Dapi_1", "Dapi_2", "Hetu_1", "Hetu_2", "Hetu_3", "Amtr_1",
                                                          "Smso_1", "Smso_2", "Taer_1", "Fro_1", "Fso_1", "Ftr_1",
                                                          "Fra_1", "Fli_1", "Stre_1", "Mimi_1", "Hean_2", "Cobi_2",
                                                          "Bial_3", "Bial_4", "Dapi_3", "Dapi_4", "Hetu_4", "Hetu_5",
                                                          "Hetu_6", "Amtr_2", "Smso_3", "Smso_4", "Taer_2", "Fro_2",
                                                          "Fso_2", "Ftr_2", "Fra_2", "Fli_2", "Stre_2", "Mimi_2")

        gene_strand = [item for gene in gene_strand_result for item in gene if item != "."]
        orthofinder_strand_genes = HierarchicalGene.objects.filter(new_gene__in=gene_strand).values_list('chromosome',
                                                                                                         'start', 'end',
                                                                                                         'strend',
                                                                                                         'old_gene',
                                                                                                         'new_gene',
                                                                                                         'num')
        genes_table = list(orthofinder_strand_genes)  # 转换为列表

        temp_modified_data = result_objects_2

        # 更新基因的属性：遍历所有匹配的基因
        for gene_info in orthofinder_strand_genes:
            chromosome, start, end, strend, old_gene, new_gene, num = gene_info
            # 初始化 sp_name 和 suffixes
            sp_name = None
            suffixes = []
            # 映射前缀到sp_name的字典
            prefix_map = {
                "Hean": "Hean", "Cobi": "Cobi", "Bial": "Bial", "Dapi": "Dapi", "Hetu": "Hetu",
                "Amtr": "Amtr", "Smso": "Smso", "Taer": "Taer", "Fro": "Fro", "Fso": "Fso", "Ftr": "Ftr", "Fra": "Fra",
                "Fli": "Fli", "Stre": "Stre", "Mimi": "Mimi"
            }

            # 根据 new_gene 设置 sp_name
            for prefix, name in prefix_map.items():
                if new_gene.startswith(prefix):
                    sp_name = name
                    break

            if sp_name:
                # 根据sp_name生成suffixes
                if sp_name in ['Hean', 'Cobi', 'Amtr', 'Taer', 'Fro', 'Fso', 'Ftr', 'Fli', 'Fra', 'Stre', 'Mimi']:
                    suffixes.extend([f"{sp_name}_{i}" for i in range(1, 3)])
                elif sp_name in ['Bial', 'Dapi', 'Smso']:
                    suffixes.extend([f"{sp_name}_{i}" for i in range(1, 5)])
                elif sp_name == 'Hetu':
                    suffixes.extend([f"{sp_name}_{i}" for i in range(1, 7)])

                # 遍历 temp_modified_data，修改相应的基因数据
                for obj in temp_modified_data:
                    for suffix in suffixes:
                        obj_attr_value = getattr(obj, suffix, None)
                        if obj_attr_value and re.match(f"^{new_gene}$", obj_attr_value, re.IGNORECASE):
                            new_value = f"{new_gene}_{strend}"
                            setattr(obj, suffix, new_value)

        return render(request, 'hierarchical_alignments_Hean.html', {
            'alignment_data': result_objects,
            'alignment_data_draw': temp_modified_data,
            'genes_table': genes_table,
            'hhh_page': "NO",
            'page_obj': page_obj,
            'total_pages': total_pages
        })

    else:
        # 处理有搜索条件的情况
        if query_sequence:
            c = name_set()
            output_directory = f"{path_get}/file_keep/{c}"
            temp_fasta_file = write_fasta_file(query_sequence, output_directory)

            nucl_or_prot = "prot"
            species_data = sp_data_1
            e = "1e-5"
            blast_result_file = os.path.join(output_directory, "result.txt")
            run_blastp(temp_fasta_file, nucl_or_prot, species_data, e, blast_result_file)
            blast_results, geneids = parse_blastp_result(blast_result_file)

            if geneids and len(geneids) > 0:
                geneid = geneids[0]
            else:
                # 如果没有找到结果，返回空结果
                return render(request, 'hierarchical_alignments_Hean.html', {
                    'alignment_data': [],
                    'alignment_data_draw': [],
                    'genes_table': [],
                    'blast_results': blast_results
                })
        else:
            geneid = geneid

        # 根据物种构建查询条件
        if sp_data_1 in ['Hean', 'Cobi', 'Amtr', 'Taer', 'Fro', 'Fso', 'Ftr', 'Fli', 'Fra', 'Stre', 'Mimi']:
            condition = Q(**{f'{sp_data_1}_1': geneid}) | Q(**{f'{sp_data_1}_2': geneid})
        elif sp_data_1 in ['Bial', 'Dapi', 'Smso']:
            condition = Q(**{f'{sp_data_1}_1': geneid}) | Q(**{f'{sp_data_1}_2': geneid}) | Q(
                **{f'{sp_data_1}_3': geneid}) | Q(**{f'{sp_data_1}_4': geneid})
        elif sp_data_1 in ['Arla']:
            condition = Q(**{f'{sp_data_1}_1': geneid}) | Q(**{f'{sp_data_1}_2': geneid}) | Q(
                **{f'{sp_data_1}_3': geneid})
        elif sp_data_1 in ['Hetu']:
            condition = Q(**{f'{sp_data_1}_1': geneid}) | Q(**{f'{sp_data_1}_2': geneid}) | Q(
                **{f'{sp_data_1}_3': geneid}) | Q(**{f'{sp_data_1}_4': geneid}) | Q(**{f'{sp_data_1}_5': geneid}) | Q(
                **{f'{sp_data_1}_6': geneid})
        else:
            condition = Q(**{f'{sp_data_1}1': geneid})

        # 执行查询
        result = HierarchicalAlignment_Hean.objects.filter(condition)
        hhh_numbers = [obj.hhh_number for obj in result]

        # 获取目标行号
        target_numbers = set()
        for id in hhh_numbers:
            id = int(id)
            for i in range(id - line_number, id + line_number + 1):
                target_numbers.add(i)

        # 获取目标数据
        result_objects = HierarchicalAlignment_Hean.objects.filter(hhh_number__in=target_numbers)
        result_objects_2 = HierarchicalAlignment_Hean.objects.filter(hhh_number__in=target_numbers)

        # 获取基因信息
        if result_objects_2.exists():
            gene_strand_result = result_objects_2.values_list("hhh_number", "Hean_1", "Cobi_1", "Bial_1", "Bial_2",
                                                              "Dapi_1", "Dapi_2", "Hetu_1", "Hetu_2", "Hetu_3",
                                                              "Amtr_1", "Smso_1", "Smso_2", "Taer_1", "Fro_1", "Fso_1",
                                                              "Ftr_1", "Fra_1", "Fli_1", "Stre_1", "Mimi_1", "Hean_2",
                                                              "Cobi_2", "Bial_3", "Bial_4", "Dapi_3", "Dapi_4",
                                                              "Hetu_4", "Hetu_5", "Hetu_6", "Amtr_2", "Smso_3",
                                                              "Smso_4", "Taer_2", "Fro_2", "Fso_2", "Ftr_2", "Fra_2",
                                                              "Fli_2", "Stre_2", "Mimi_2")

            gene_strand = [item for gene in gene_strand_result for item in gene if item != "."]

            if gene_strand:
                orthofinder_strand_genes = list(HierarchicalGene.objects.filter(new_gene__in=gene_strand).values_list(
                    'chromosome', 'start', 'end', 'strend', 'old_gene', 'new_gene', 'num'))
                genes_table = orthofinder_strand_genes

        temp_modified_data = result_objects_2

        # 更新基因的属性 - 只在 genes_table 不为空时执行
        if genes_table:
            for gene_info in genes_table:
                chromosome, start, end, strend, old_gene, new_gene, num = gene_info
                sp_name = None
                suffixes = []
                prefix_map = {
                    "Hean": "Hean", "Cobi": "Cobi", "Bial": "Bial", "Dapi": "Dapi", "Hetu": "Hetu",
                    "Amtr": "Amtr", "Smso": "Smso", "Taer": "Taer", "Fro": "Fro", "Fso": "Fso",
                    "Ftr": "Ftr", "Fra": "Fra", "Fli": "Fli", "Stre": "Stre", "Mimi": "Mimi"
                }

                # 根据 new_gene 设置 sp_name
                for prefix, name in prefix_map.items():
                    if new_gene.startswith(prefix):
                        sp_name = name
                        break

                if sp_name:
                    if sp_name in ['Hean', 'Cobi', 'Amtr', 'Taer', 'Fro', 'Fso', 'Ftr', 'Fli', 'Fra', 'Stre', 'Mimi']:
                        suffixes.extend([f"{sp_name}_{i}" for i in range(1, 3)])
                    elif sp_name in ['Bial', 'Dapi', 'Smso']:
                        suffixes.extend([f"{sp_name}_{i}" for i in range(1, 5)])
                    elif sp_name == 'Hetu':
                        suffixes.extend([f"{sp_name}_{i}" for i in range(1, 7)])

                    for obj in temp_modified_data:
                        for suffix in suffixes:
                            obj_attr_value = getattr(obj, suffix, None)
                            if obj_attr_value and re.match(f"^{new_gene}$", obj_attr_value, re.IGNORECASE):
                                new_value = f"{new_gene}_{strend}"
                                setattr(obj, suffix, new_value)

        # 渲染模板
        return render(request, 'hierarchical_alignments_Hean.html', {
            'alignment_data': list(result_objects),
            'alignment_data_draw': list(temp_modified_data),
            'genes_table': genes_table,
            'blast_results': blast_results,
            'hhh_page': None,  # 有搜索条件时不显示分页
            'page_obj': None,
            'total_pages': None
        })


# Lssa_all 为参考的共线性列表
def hierarchical_alignments_Lssa_all(request):
    global blast_results
    geneid = request.POST.get('geneid')
    sp_data_1 = request.POST.get("sp_data_1")
    query_sequence = request.POST.get('query_sequence')

    # 设置 line_number 默认值为 4
    line_number = 4

    # 初始化变量
    blast_results = None
    genes_table = []  # 初始化为空列表
    result_objects = []
    temp_modified_data = []
    page_obj = None
    total_pages = None
    orthofinder_strand_genes = []  # 初始化这个变量

    if sp_data_1 is None or geneid is None:
        alignment_data_query = HierarchicalAlignment_Lssa_all.objects.order_by('number')
        per_page = 10
        paginator = Paginator(alignment_data_query, per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        total_pages = paginator.num_pages

        result_objects = page_obj.object_list[:]
        result_objects_2 = page_obj.object_list[:]
        gene_strand_result = result_objects_2.values_list("Arla_1", "Arla_2", "Arla_3", "Gehy_1",
                                                          "Armi_1", "Sain_1", "Ceso_1", "Cati_1",
                                                          "Ccar_1", "Cien_1", "Cich_1", "Lssa_1", "Laca_1", "Tako_1",
                                                          "Tamo_1", "Pslu_1", "Lomi_1", "Lomi_2", "Enbr_1", "Ecan_1",
                                                          "Soca_1", "Glco_1", "Artr_1", "Aary_1", "Aary_2", "Aann_1",
                                                          "Chma_1", "Chmo_1", "Chmo_2", "Chmo_3", "Chla_1", "Chna_1",
                                                          "Cind_1", "Pdy_1", "Cobi_1", "Hean_1", "Bial_1", "Bial_2",
                                                          "Dapi_1", "Dapi_2", "Hetu_1", "Hetu_2", "Hetu_3", "Amtr_1",
                                                          "Smso_1", "Smso_2", "Taer_1", "Fro_1", "Fso_1", "Ftr_1",
                                                          "Fra_1", "Fli_1", "Stre_1", "Mimi_1", "Cobi_2", "Hean_2",
                                                          "Bial_3", "Bial_4", "Dapi_3", "Dapi_4", "Hetu_4", "Hetu_5",
                                                          "Hetu_6", "Amtr_2", "Smso_3", "Smso_4", "Taer_2", "Fro_2",
                                                          "Fso_2", "Ftr_2", "Fra_2", "Fli_2", "Stre_2", "Mimi_2")

        gene_strand = [item for gene in gene_strand_result for item in gene if item != "."]
        orthofinder_strand_genes = HierarchicalGene.objects.filter(new_gene__in=gene_strand).values_list('chromosome',
                                                                                                         'start', 'end',
                                                                                                         'strend',
                                                                                                         'old_gene',
                                                                                                         'new_gene',
                                                                                                         'num')

        genes_table = list(orthofinder_strand_genes)  # 转换为列表

        temp_modified_data = result_objects_2

        # 更新基因的属性：遍历所有匹配的基因
        for gene_info in orthofinder_strand_genes:
            chromosome, start, end, strend, old_gene, new_gene, num = gene_info
            # 初始化 sp_name 和 suffixes
            sp_name = None
            suffixes = []
            # 映射前缀到sp_name的字典
            prefix_map = {
                "Aary": "Aary",
                "Aann": "Aann",
                "Amtr": "Amtr",
                "Arla": "Arla",
                "Armi": "Armi",
                "Artr": "Artr",
                "Bial": "Bial",
                "Cbi": "Cbi",
                "Ccar": "Ccar",
                "Ceso": "Ceso",
                "Chla": "Chla",
                "Chma": "Chma",
                "Chmo": "Chmo",
                "Chna": "Chna",
                "Cich": "Cich",
                "Cien": "Cien",
                "Cind": "Cind",
                "Cobi": "Cobi",
                "Dapi": "Dapi",
                "Ecan": "Ecan",
                "Enbr": "Enbr",
                "Fra": "Fra",
                "Fro": "Fro",
                "Fso": "Fso",
                "Ftr": "Ftr",
                "Fli": "Fli",
                "Gehy": "Gehy",
                "Glco": "Glco",
                "Hean": "Hean",
                "Hetu": "Hetu",
                "Laca": "Laca",
                "Lomi": "Lomi",
                "Lssa": "Lssa",
                "Mimi": "Mimi",
                "Pdy": "Pdy",
                "Pslu": "Pslu",
                "Sain": "Sain",
                "Smso": "Smso",
                "Soca": "Soca",
                "Stre": "Stre",
                "Taer": "Taer",
                "Tako": "Tako",
                "Tamo": "Tamo",
            }

            # 根据 new_gene 设置 sp_name
            for prefix, name in prefix_map.items():
                if new_gene.startswith(prefix):
                    sp_name = name
                    break

            if sp_name:
                if sp_name in ['Aary', 'Amtr', 'Cobi', 'Fli', 'Fra', 'Fro', 'Fso', 'Ftr', 'Hean', 'Lomi', 'Mimi',
                               'Stre', 'Taer']:
                    suffixes.extend([f"{sp_name}_{i}" for i in range(1, 3)])
                elif sp_name in ['Aann', 'Armi', 'Artr', 'Cati', 'Ccar', 'Ceso', 'Chla', 'Chma', 'Chna', 'Cich', 'Cien',
                                 'Cind', 'Ecan', 'Enbr', 'Gehy', 'Glco', 'Laca', 'Lssa', 'Pdy', 'Sain', 'Soca', 'Tako', 'Tamo']:
                    suffixes.extend([f"{sp_name}_{i}" for i in range(1, 2)])
                elif sp_name == 'Arla':
                    suffixes.extend([f"{sp_name}_{i}" for i in range(1, 4)])
                elif sp_name == 'Chmo':
                    suffixes.extend([f"{sp_name}_{i}" for i in range(1, 4)])
                elif sp_name in ['Bial', 'Dapi', 'Smso']:
                    suffixes.extend([f"{sp_name}_{i}" for i in range(1, 5)])
                elif sp_name == 'Hetu':
                    suffixes.extend([f"{sp_name}_{i}" for i in range(1, 7)])

                # 遍历 temp_modified_data，修改相应的基因数据
                for obj in temp_modified_data:
                    for suffix in suffixes:
                        obj_attr_value = getattr(obj, suffix, None)
                        if obj_attr_value and re.match(f"^{new_gene}$", obj_attr_value, re.IGNORECASE):
                            new_value = f"{new_gene}_{strend}"
                            setattr(obj, suffix, new_value)

        return render(request, 'hierarchical_alignments_Lssa_all.html', {
            'alignment_data': result_objects,
            'alignment_data_draw': temp_modified_data,
            'genes_table': genes_table,
            'hhh_page': "NO",
            'page_obj': page_obj,
            'total_pages': total_pages
        })

    else:
        # 处理有搜索条件的情况
        if query_sequence:
            c = name_set()
            output_directory = f"{path_get}/file_keep/{c}"
            temp_fasta_file = write_fasta_file(query_sequence, output_directory)
            nucl_or_prot = "prot"
            species_data = sp_data_1
            e = "1e-5"
            blast_result_file = os.path.join(output_directory, "result.txt")
            run_blastp(temp_fasta_file, nucl_or_prot, species_data, e, blast_result_file)
            blast_results, geneids = parse_blastp_result(blast_result_file)

            if geneids and len(geneids) > 0:
                geneid = geneids[0]
            else:
                # 如果没有找到结果，返回空结果
                return render(request, 'hierarchical_alignments_Lssa_all.html', {
                    'alignment_data': [],
                    'alignment_data_draw': [],
                    'genes_table': [],
                    'blast_results': blast_results
                })
        else:
            geneid = geneid

        # 修正：构建查询条件时需要考虑更多的物种
        if sp_data_1 in ['Aary', 'Amtr', 'Cobi', 'Fli', 'Fra', 'Fro', 'Fso', 'Ftr', 'Hean', 'Lomi', 'Mimi', 'Stre',
                         'Taer']:
            condition = Q(**{f'{sp_data_1}_1': geneid}) | Q(**{f'{sp_data_1}_2': geneid})
        elif sp_data_1 in ['Chmo']:
            condition = Q(**{f'{sp_data_1}_1': geneid}) | Q(**{f'{sp_data_1}_2': geneid}) | Q(
                **{f'{sp_data_1}_3': geneid})
        elif sp_data_1 in ['Bial', 'Dapi', 'Smso']:
            condition = Q(**{f'{sp_data_1}_1': geneid}) | Q(**{f'{sp_data_1}_2': geneid}) | Q(
                **{f'{sp_data_1}_3': geneid}) | Q(**{f'{sp_data_1}_4': geneid})
        elif sp_data_1 in ['Hetu']:
            condition = Q(**{f'{sp_data_1}_1': geneid}) | Q(**{f'{sp_data_1}_2': geneid}) | Q(
                **{f'{sp_data_1}_3': geneid}) | Q(**{f'{sp_data_1}_4': geneid}) | Q(**{f'{sp_data_1}_5': geneid}) | Q(
                **{f'{sp_data_1}_6': geneid})
        else:
            # 对于只有一个字段的物种，使用对应的字段名
            # 检查字段是否存在
            field_name = f"{sp_data_1}_1"
            condition = Q(**{field_name: geneid})

        # 执行查询 - 修正：使用正确的模型
        try:
            result = HierarchicalAlignment_Lssa_all.objects.filter(condition)
        except Exception as e:
            # 如果字段不存在，返回空结果
            print(f"查询错误: {e}")
            return render(request, 'hierarchical_alignments_Lssa_all.html', {
                'alignment_data': [],
                'alignment_data_draw': [],
                'genes_table': [],
                'blast_results': blast_results,
                'error': f"查询字段不存在: {sp_data_1}"
            })

        hhh_numbers = [obj.number for obj in result]

        # 获取目标行号
        target_numbers = set()
        for id in hhh_numbers:
            id = int(id)
            for i in range(id - line_number, id + line_number + 1):
                target_numbers.add(i)

        # 获取目标数据
        result_objects = HierarchicalAlignment_Lssa_all.objects.filter(number__in=target_numbers)
        result_objects_2 = HierarchicalAlignment_Lssa_all.objects.filter(number__in=target_numbers)

        # 获取基因信息
        if result_objects_2.exists():
            gene_strand_result = result_objects_2.values_list("Arla_1", "Arla_2", "Arla_3", "Gehy_1",
                                                              "Armi_1", "Sain_1", "Ceso_1", "Cati_1",
                                                              "Ccar_1", "Cien_1", "Cich_1", "Lssa_1", "Laca_1",
                                                              "Tako_1", "Tamo_1", "Pslu_1", "Lomi_1", "Lomi_2",
                                                              "Enbr_1", "Ecan_1", "Soca_1", "Glco_1", "Artr_1",
                                                              "Aary_1", "Aary_2", "Aann_1", "Chma_1", "Chmo_1",
                                                              "Chmo_2", "Chmo_3", "Chla_1", "Chna_1", "Cind_1", "Pdy_1",
                                                              "Cobi_1", "Hean_1", "Bial_1", "Bial_2", "Dapi_1",
                                                              "Dapi_2", "Hetu_1", "Hetu_2", "Hetu_3", "Amtr_1",
                                                              "Smso_1", "Smso_2", "Taer_1", "Fro_1", "Fso_1", "Ftr_1",
                                                              "Fra_1", "Fli_1", "Stre_1", "Mimi_1", "Cobi_2", "Hean_2",
                                                              "Bial_3", "Bial_4", "Dapi_3", "Dapi_4", "Hetu_4",
                                                              "Hetu_5", "Hetu_6", "Amtr_2", "Smso_3", "Smso_4",
                                                              "Taer_2", "Fro_2", "Fso_2", "Ftr_2", "Fra_2", "Fli_2",
                                                              "Stre_2", "Mimi_2")

            gene_strand = [item for gene in gene_strand_result for item in gene if item != "."]

            if gene_strand:
                orthofinder_strand_genes = list(HierarchicalGene.objects.filter(new_gene__in=gene_strand).values_list(
                    'chromosome', 'start', 'end', 'strend', 'old_gene', 'new_gene', 'num'))
                genes_table = orthofinder_strand_genes

        temp_modified_data = result_objects_2

        # 更新基因的属性 - 只在 genes_table 不为空时执行
        if genes_table:
            for gene_info in genes_table:
                chromosome, start, end, strend, old_gene, new_gene, num = gene_info
                sp_name = None
                suffixes = []
                prefix_map = {
                    "Aary": "Aary",
                    "Aann": "Aann",
                    "Amtr": "Amtr",
                    "Arla": "Arla",
                    "Armi": "Armi",
                    "Artr": "Artr",
                    "Bial": "Bial",
                    "Cbi": "Cbi",
                    "Ccar": "Ccar",
                    "Ceso": "Ceso",
                    "Chla": "Chla",
                    "Chma": "Chma",
                    "Chmo": "Chmo",
                    "Chna": "Chna",
                    "Cich": "Cich",
                    "Cien": "Cien",
                    "Cind": "Cind",
                    "Cobi": "Cobi",
                    "Dapi": "Dapi",
                    "Ecan": "Ecan",
                    "Enbr": "Enbr",
                    "Fra": "Fra",
                    "Fro": "Fro",
                    "Fso": "Fso",
                "Ftr": "Ftr",
                "Fli": "Fli",
                "Gehy": "Gehy",
                "Glco": "Glco",
                    "Hean": "Hean",
                    "Hetu": "Hetu",
                    "Laca": "Laca",
                    "Lomi": "Lomi",
                    "Lssa": "Lssa",
                    "Mimi": "Mimi",
                    "Pdy": "Pdy",
                    "Pslu": "Pslu",
                    "Sain": "Sain",
                    "Smso": "Smso",
                    "Soca": "Soca",
                    "Stre": "Stre",
                    "Taer": "Taer",
                    "Tako": "Tako",
                    "Tamo": "Tamo",
                }

                # 根据 new_gene 设置 sp_name
                for prefix, name in prefix_map.items():
                    if new_gene.startswith(prefix):
                        sp_name = name
                        break

                if sp_name:
                    # 根据sp_name生成suffixes
                    if sp_name in ['Aary', 'Amtr', 'Cobi', 'Fli', 'Fra', 'Fro', 'Fso', 'Ftr', 'Hean', 'Lomi', 'Mimi',
                                   'Stre', 'Taer']:
                        suffixes.extend([f"{sp_name}_{i}" for i in range(1, 3)])
                    elif sp_name in ['Aann', 'Armi', 'Artr', 'Cati', 'Ccar', 'Ceso', 'Chla', 'Chma', 'Chna', 'Cich',
                                     'Cien', 'Cind', 'Ecan', 'Enbr', 'Gehy', 'Glco', 'Laca', 'Lssa', 'Pdy', 'Sain', 'Soca',
                                     'Tako', 'Tamo']:
                        suffixes.extend([f"{sp_name}_{i}" for i in range(1, 2)])
                    elif sp_name == 'Arla':
                        suffixes.extend([f"{sp_name}_{i}" for i in range(1, 4)])
                    elif sp_name == 'Chmo':
                        suffixes.extend([f"{sp_name}_{i}" for i in range(1, 4)])
                    elif sp_name in ['Bial', 'Dapi', 'Smso']:
                        suffixes.extend([f"{sp_name}_{i}" for i in range(1, 5)])
                    elif sp_name == 'Hetu':
                        suffixes.extend([f"{sp_name}_{i}" for i in range(1, 7)])

                    for obj in temp_modified_data:
                        for suffix in suffixes:
                            obj_attr_value = getattr(obj, suffix, None)
                            if obj_attr_value and re.match(f"^{new_gene}$", obj_attr_value, re.IGNORECASE):
                                new_value = f"{new_gene}_{strend}"
                                setattr(obj, suffix, new_value)

        # 渲染模板
        return render(request, 'hierarchical_alignments_Lssa_all.html', {
            'alignment_data': list(result_objects),
            'alignment_data_draw': list(temp_modified_data),
            'genes_table': genes_table,
            'blast_results': blast_results,
            'hhh_page': None,  # 有搜索条件时不显示分页
            'page_obj': None,
            'total_pages': None
        })


# Vivi 为参考的共线性列表
def hierarchical_alignments_Vivi(request):
    global blast_results
    geneid = request.POST.get('geneid')
    sp_data_1 = request.POST.get("sp_data_1")
    query_sequence = request.POST.get('query_sequence')

    # 设置 line_number 默认值为 4
    line_number = 4

    # 初始化变量
    blast_results = None
    genes_table = []  # 初始化为空列表
    result_objects = []
    temp_modified_data = []
    page_obj = None
    total_pages = None
    orthofinder_strand_genes = []  # 初始化这个变量

    if sp_data_1 is None or geneid is None:
        alignment_data_query = HierarchicalAlignment_Vivi.objects.all()
        per_page = 10
        paginator = Paginator(alignment_data_query, per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        total_pages = paginator.num_pages

        result_objects = page_obj.object_list[:]
        result_objects_2 = page_obj.object_list[:]
        gene_strand_result = result_objects_2.values_list("hhh_number", "Vivi_1", "Arla_1", "Armi_1", "Sain_1",
                                                          "Ceso_1", "Cati_1", "Ccar_1", "Cien_1", "Cich_1", "Lssa_1",
                                                          "Laca_1", "Tako_1", "Tamo_1", "Pslu_1", "Lomi_1", "Lomi_2",
                                                          "Enbr_1", "Ecan_1", "Soca_1", "Glco_1", "Artr_1", "Aary_1",
                                                          "Aary_2", "Aann_1", "Chma_1", "Chmo_1", "Chmo_2", "Chmo_3",
                                                          "Chla_1", "Chna_1", "Cind_1", "Pdy_1", "Cobi_1", "Hean_1",
                                                          "Bial_1", "Bial_2", "Dapi_1", "Dapi_2", "Hetu_1", "Hetu_2",
                                                          "Hetu_3", "Amtr_1", "Smso_1", "Smso_2", "Taer_1", "Fro_1",
                                                          "Fso_1", "Ftr_1", "Fra_1", "Fli_1", "Stre_1", "Mimi_1",
                                                          "Cobi_2", "Hean_2", "Bial_3", "Bial_4", "Dapi_3", "Dapi_4",
                                                          "Hetu_4", "Hetu_5", "Hetu_6", "Amtr_2", "Smso_3", "Smso_4",
                                                          "Taer_2", "Fro_2", "Fso_2", "Ftr_2", "Fra_2", "Fli_2",
                                                          "Stre_2", "Mimi_2", "Arla_2", "Armi_2", "Sain_2", "Ceso_2",
                                                          "Cati_2", "Ccar_2", "Cien_2", "Cich_2", "Lssa_2", "Laca_2",
                                                          "Tako_2", "Tamo_2", "Pslu_2", "Lomi_3", "Lomi_4", "Enbr_2",
                                                          "Ecan_2", "Soca_2", "Glco_2", "Artr_2", "Aary_3", "Aary_4",
                                                          "Aann_2", "Chma_2", "Chmo_4", "Chmo_5", "Chmo_6", "Chla_2",
                                                          "Chna_2", "Cind_2", "Pdy_2", "Cobi_3", "Hean_3", "Bial_5",
                                                          "Bial_6", "Dapi_5", "Dapi_6", "Hetu_7", "Hetu_8", "Hetu_9",
                                                          "Amtr_3", "Smso_5", "Smso_6", "Taer_3", "Fro_3", "Fso_3",
                                                          "Ftr_3", "Fra_3", "Fli_3", "Stre_3", "Mimi_3", "Cobi_4",
                                                          "Hean_4", "Bial_7", "Bial_8", "Dapi_7", "Dapi_8", "Hetu_10",
                                                          "Hetu_11", "Hetu_12", "Amtr_4", "Smso_7", "Smso_8", "Taer_4",
                                                          "Fro_4", "Fso_4", "Ftr_4", "Fra_4", "Fli_4")

        gene_strand = [item for gene in gene_strand_result for item in gene if item != "."]
        orthofinder_strand_genes = HierarchicalGene.objects.filter(new_gene__in=gene_strand).values_list('chromosome',
                                                                                                         'start', 'end',
                                                                                                         'strend',
                                                                                                         'old_gene',
                                                                                                         'new_gene',
                                                                                                         'num')

        genes_table = list(orthofinder_strand_genes)  # 转换为列表

        temp_modified_data = result_objects_2

        # 更新基因的属性：遍历所有匹配的基因
        for gene_info in orthofinder_strand_genes:
            chromosome, start, end, strend, old_gene, new_gene, num = gene_info
            # 初始化 sp_name 和 suffixes
            sp_name = None
            suffixes = []
            # 映射前缀到sp_name的字典
            prefix_map = {
                "Aann": "Aann",
                "Aary": "Aary",
                "Amtr": "Amtr",
                "Arla": "Arla",
                "Armi": "Armi",
                "Artr": "Artr",
                "Bial": "Bial",
                "Cati": "Cati",
                "Ccar": "Ccar",
                "Ceso": "Ceso",
                "Chla": "Chla",
                "Chma": "Chma",
                "Chmo": "Chmo",
                "Chna": "Chna",
                "Cich": "Cich",
                "Cien": "Cien",
                "Cind": "Cind",
                "Cobi": "Cobi",
                "Dapi": "Dapi",
                "Ecan": "Ecan",
                "Enbr": "Enbr",
                "Fli": "Fli",
                "Fra": "Fra",
                "Fro": "Fro",
                "Fso": "Fso",
                "Ftr": "Ftr",
                "Glco": "Glco",
                "Hean": "Hean",
                "Hetu": "Hetu",
                "Laca": "Laca",
                "Lomi": "Lomi",
                "Lssa": "Lssa",
                "Mimi": "Mimi",
                "Pdy": "Pdy",
                "Pslu": "Pslu",
                "Sain": "Sain",
                "Smso": "Smso",
                "Soca": "Soca",
                "Stre": "Stre",
                "Taer": "Taer",
                "Tako": "Tako",
                "Tamo": "Tamo",
                "Vivi": "Vivi"
            }

            # 根据 new_gene 设置 sp_name
            for prefix, name in prefix_map.items():
                if new_gene.startswith(prefix):
                    sp_name = name
                    break

            if sp_name:
                # 根据sp_name生成suffixes
                if sp_name in ['Aann', 'Arla', 'Armi', 'Artr', 'Cati', 'Ccar', 'Ceso', 'Chla', 'Chma', 'Chna', 'Cich',
                               'Cien', 'Cind', 'Ecan', 'Enbr', 'Glco', 'Laca', 'Lssa', 'Pdy', 'Pslu', 'Sain', 'Soca',
                               'Tako', 'Tamo']:
                    suffixes.extend([f"{sp_name}_{i}" for i in range(1, 3)])
                elif sp_name == 'Chmo':
                    suffixes.extend([f"{sp_name}_{i}" for i in range(1, 7)])
                elif sp_name == 'Mimi':
                    suffixes.extend([f"{sp_name}_{i}" for i in range(1, 4)])
                elif sp_name in ['Aary', 'Amtr', 'Cobi', 'Fli', 'Fra', 'Fro', 'Fso', 'Ftr', 'Hean', 'Lomi', 'Taer']:
                    suffixes.extend([f"{sp_name}_{i}" for i in range(1, 5)])
                elif sp_name in ['Bial', 'Dapi', 'Smso']:
                    suffixes.extend([f"{sp_name}_{i}" for i in range(1, 9)])
                elif sp_name == 'Hetu':
                    suffixes.extend([f"{sp_name}_{i}" for i in range(1, 13)])
                elif sp_name == 'Vivi':
                    suffixes.extend([f"{sp_name}_{i}" for i in range(1, 2)])  # Vivi只有1个字段

                # 遍历 temp_modified_data，修改相应的基因数据
                for obj in temp_modified_data:
                    for suffix in suffixes:
                        obj_attr_value = getattr(obj, suffix, None)
                        if obj_attr_value and re.match(f"^{new_gene}$", obj_attr_value, re.IGNORECASE):
                            new_value = f"{new_gene}_{strend}"
                            setattr(obj, suffix, new_value)

        return render(request, 'hierarchical_alignments_Vivi.html', {
            'alignment_data': result_objects,
            'alignment_data_draw': temp_modified_data,
            'genes_table': genes_table,
            'hhh_page': "NO",
            'page_obj': page_obj,
            'total_pages': total_pages
        })

    else:
        # 处理有搜索条件的情况
        if query_sequence:
            c = name_set()
            output_directory = f"{path_get}/file_keep/{c}"
            temp_fasta_file = write_fasta_file(query_sequence, output_directory)
            nucl_or_prot = "prot"
            species_data = sp_data_1
            e = "1e-5"
            blast_result_file = os.path.join(output_directory, "result.txt")
            run_blastp(temp_fasta_file, nucl_or_prot, species_data, e, blast_result_file)
            blast_results, geneids = parse_blastp_result(blast_result_file)

            if geneids and len(geneids) > 0:
                geneid = geneids[0]
            else:
                # 如果没有找到结果，返回空结果
                return render(request, 'hierarchical_alignments_Vivi.html', {
                    'alignment_data': [],
                    'alignment_data_draw': [],
                    'genes_table': [],
                    'blast_results': blast_results
                })
        else:
            geneid = geneid

        # 构建查询条件
        if sp_data_1 in ['Aann', 'Arla', 'Armi', 'Artr', 'Cati', 'Ccar', 'Ceso', 'Chla', 'Chma', 'Chna', 'Cich', 'Cien',
                         'Cind', 'Ecan', 'Enbr', 'Glco', 'Laca', 'Lssa', 'Pdy', 'Pslu', 'Sain', 'Soca', 'Tako', 'Tamo']:
            condition = Q(**{f'{sp_data_1}_1': geneid}) | Q(**{f'{sp_data_1}_2': geneid})
        elif sp_data_1 in ['Mimi']:
            condition = Q(**{f'{sp_data_1}_1': geneid}) | Q(**{f'{sp_data_1}_2': geneid}) | Q(
                **{f'{sp_data_1}_3': geneid})
        elif sp_data_1 in ['Aary', 'Amtr', 'Cobi', 'Fli', 'Fra', 'Fro', 'Fso', 'Ftr', 'Hean', 'Lomi', 'Taer']:
            condition = Q(**{f'{sp_data_1}_1': geneid}) | Q(**{f'{sp_data_1}_2': geneid}) | Q(
                **{f'{sp_data_1}_3': geneid}) | Q(**{f'{sp_data_1}_4': geneid})
        elif sp_data_1 in ['Chmo']:
            condition = Q(**{f'{sp_data_1}_1': geneid}) | Q(**{f'{sp_data_1}_2': geneid}) | Q(
                **{f'{sp_data_1}_3': geneid}) | Q(**{f'{sp_data_1}_4': geneid}) | Q(**{f'{sp_data_1}_5': geneid}) | Q(
                **{f'{sp_data_1}_6': geneid})
        elif sp_data_1 in ['Bial', 'Dapi', 'Smso']:
            condition = Q(**{f'{sp_data_1}_1': geneid}) | Q(**{f'{sp_data_1}_2': geneid}) | Q(
                **{f'{sp_data_1}_3': geneid}) | Q(**{f'{sp_data_1}_4': geneid}) | Q(**{f'{sp_data_1}_5': geneid}) | Q(
                **{f'{sp_data_1}_6': geneid}) | Q(**{f'{sp_data_1}_7': geneid}) | Q(**{f'{sp_data_1}_8': geneid})
        elif sp_data_1 in ['Hetu']:
            condition = Q(**{f'{sp_data_1}_1': geneid}) | Q(**{f'{sp_data_1}_2': geneid}) | Q(
                **{f'{sp_data_1}_3': geneid}) | Q(**{f'{sp_data_1}_4': geneid}) | Q(**{f'{sp_data_1}_5': geneid}) | Q(
                **{f'{sp_data_1}_6': geneid}) | Q(**{f'{sp_data_1}_7': geneid}) | Q(**{f'{sp_data_1}_8': geneid}) | Q(
                **{f'{sp_data_1}_9': geneid}) | Q(**{f'{sp_data_1}_10': geneid}) | Q(**{f'{sp_data_1}_11': geneid}) | Q(
                **{f'{sp_data_1}_12': geneid})
        elif sp_data_1 == 'Vivi':
            condition = Q(**{f'{sp_data_1}_1': geneid})  # Vivi只有1个字段
        else:
            # 对于其他物种，默认使用_1后缀
            field_name = f"{sp_data_1}_1"
            condition = Q(**{field_name: geneid})

        # 执行查询 - 使用正确的模型
        try:
            result = HierarchicalAlignment_Vivi.objects.filter(condition)
        except Exception as e:
            print(f"查询错误: {e}")
            return render(request, 'hierarchical_alignments_Vivi.html', {
                'alignment_data': [],
                'alignment_data_draw': [],
                'genes_table': [],
                'blast_results': blast_results,
                'error': f"查询字段不存在: {sp_data_1}"
            })

        hhh_numbers = [obj.hhh_number for obj in result]

        # 获取目标行号
        target_numbers = set()
        for id in hhh_numbers:
            id = int(id)
            for i in range(id - line_number, id + line_number + 1):
                target_numbers.add(i)

        # 获取目标数据
        result_objects = HierarchicalAlignment_Vivi.objects.filter(hhh_number__in=target_numbers)
        result_objects_2 = HierarchicalAlignment_Vivi.objects.filter(hhh_number__in=target_numbers)

        # 获取基因信息
        if result_objects_2.exists():
            gene_strand_result = result_objects_2.values_list("hhh_number", "Vivi_1", "Arla_1", "Armi_1", "Sain_1",
                                                              "Ceso_1", "Cati_1", "Ccar_1", "Cien_1", "Cich_1",
                                                              "Lssa_1", "Laca_1", "Tako_1", "Tamo_1", "Pslu_1",
                                                              "Lomi_1", "Lomi_2", "Enbr_1", "Ecan_1", "Soca_1",
                                                              "Glco_1", "Artr_1", "Aary_1", "Aary_2", "Aann_1",
                                                              "Chma_1", "Chmo_1", "Chmo_2", "Chmo_3", "Chla_1",
                                                              "Chna_1", "Cind_1", "Pdy_1", "Cobi_1", "Hean_1", "Bial_1",
                                                              "Bial_2", "Dapi_1", "Dapi_2", "Hetu_1", "Hetu_2",
                                                              "Hetu_3", "Amtr_1", "Smso_1", "Smso_2", "Taer_1", "Fro_1",
                                                              "Fso_1", "Ftr_1", "Fra_1", "Fli_1", "Stre_1", "Mimi_1",
                                                              "Cobi_2", "Hean_2", "Bial_3", "Bial_4", "Dapi_3",
                                                              "Dapi_4", "Hetu_4", "Hetu_5", "Hetu_6", "Amtr_2",
                                                              "Smso_3", "Smso_4", "Taer_2", "Fro_2", "Fso_2", "Ftr_2",
                                                              "Fra_2", "Fli_2", "Stre_2", "Mimi_2", "Arla_2", "Armi_2",
                                                              "Sain_2", "Ceso_2", "Cati_2", "Ccar_2", "Cien_2",
                                                              "Cich_2", "Lssa_2", "Laca_2", "Tako_2", "Tamo_2",
                                                              "Pslu_2", "Lomi_3", "Lomi_4", "Enbr_2", "Ecan_2",
                                                              "Soca_2", "Glco_2", "Artr_2", "Aary_3", "Aary_4",
                                                              "Aann_2", "Chma_2", "Chmo_4", "Chmo_5", "Chmo_6",
                                                              "Chla_2", "Chna_2", "Cind_2", "Pdy_2", "Cobi_3", "Hean_3",
                                                              "Bial_5", "Bial_6", "Dapi_5", "Dapi_6", "Hetu_7",
                                                              "Hetu_8", "Hetu_9", "Amtr_3", "Smso_5", "Smso_6",
                                                              "Taer_3", "Fro_3", "Fso_3", "Ftr_3", "Fra_3", "Fli_3",
                                                              "Stre_3", "Mimi_3", "Cobi_4", "Hean_4", "Bial_7",
                                                              "Bial_8", "Dapi_7", "Dapi_8", "Hetu_10", "Hetu_11",
                                                              "Hetu_12", "Amtr_4", "Smso_7", "Smso_8", "Taer_4",
                                                              "Fro_4", "Fso_4", "Ftr_4", "Fra_4", "Fli_4")

            gene_strand = [item for gene in gene_strand_result for item in gene if item != "."]

            if gene_strand:
                orthofinder_strand_genes = list(HierarchicalGene.objects.filter(new_gene__in=gene_strand).values_list(
                    'chromosome', 'start', 'end', 'strend', 'old_gene', 'new_gene', 'num'))
                genes_table = orthofinder_strand_genes

        temp_modified_data = result_objects_2

        # 更新基因的属性 - 只在 genes_table 不为空时执行
        if genes_table:
            for gene_info in genes_table:
                chromosome, start, end, strend, old_gene, new_gene, num = gene_info
                sp_name = None
                suffixes = []
                prefix_map = {
                    "Aann": "Aann",
                    "Aary": "Aary",
                    "Amtr": "Amtr",
                    "Arla": "Arla",
                    "Armi": "Armi",
                    "Artr": "Artr",
                    "Bial": "Bial",
                    "Cati": "Cati",
                    "Ccar": "Ccar",
                    "Ceso": "Ceso",
                    "Chla": "Chla",
                    "Chma": "Chma",
                    "Chmo": "Chmo",
                    "Chna": "Chna",
                    "Cich": "Cich",
                    "Cien": "Cien",
                    "Cind": "Cind",
                    "Cobi": "Cobi",
                    "Dapi": "Dapi",
                    "Ecan": "Ecan",
                    "Enbr": "Enbr",
                    "Fli": "Fli",
                    "Fra": "Fra",
                    "Fro": "Fro",
                    "Fso": "Fso",
                    "Ftr": "Ftr",
                    "Glco": "Glco",
                    "Hean": "Hean",
                    "Hetu": "Hetu",
                    "Laca": "Laca",
                    "Lomi": "Lomi",
                    "Lssa": "Lssa",
                    "Mimi": "Mimi",
                    "Pdy": "Pdy",
                    "Pslu": "Pslu",
                    "Sain": "Sain",
                    "Smso": "Smso",
                    "Soca": "Soca",
                    "Stre": "Stre",
                    "Taer": "Taer",
                    "Tako": "Tako",
                    "Tamo": "Tamo",
                    "Vivi": "Vivi"
                }

                # 根据 new_gene 设置 sp_name
                for prefix, name in prefix_map.items():
                    if new_gene.startswith(prefix):
                        sp_name = name
                        break

                if sp_name:
                    # 根据sp_name生成suffixes
                    if sp_name in ['Aann', 'Arla', 'Armi', 'Artr', 'Cati', 'Ccar', 'Ceso', 'Chla', 'Chma', 'Chna',
                                   'Cich', 'Cien', 'Cind', 'Ecan', 'Enbr', 'Glco', 'Laca', 'Lssa', 'Pdy', 'Pslu',
                                   'Sain', 'Soca', 'Tako', 'Tamo']:
                        suffixes.extend([f"{sp_name}_{i}" for i in range(1, 3)])
                    elif sp_name == 'Chmo':
                        suffixes.extend([f"{sp_name}_{i}" for i in range(1, 7)])
                    elif sp_name == 'Mimi':
                        suffixes.extend([f"{sp_name}_{i}" for i in range(1, 4)])
                    elif sp_name in ['Aary', 'Amtr', 'Cobi', 'Fli', 'Fra', 'Fro', 'Fso', 'Ftr', 'Hean', 'Lomi', 'Taer']:
                        suffixes.extend([f"{sp_name}_{i}" for i in range(1, 5)])
                    elif sp_name in ['Bial', 'Dapi', 'Smso']:
                        suffixes.extend([f"{sp_name}_{i}" for i in range(1, 9)])
                    elif sp_name == 'Hetu':
                        suffixes.extend([f"{sp_name}_{i}" for i in range(1, 13)])
                    elif sp_name == 'Vivi':
                        suffixes.extend([f"{sp_name}_{i}" for i in range(1, 2)])  # Vivi只有1个字段

                    for obj in temp_modified_data:
                        for suffix in suffixes:
                            obj_attr_value = getattr(obj, suffix, None)
                            if obj_attr_value and re.match(f"^{new_gene}$", obj_attr_value, re.IGNORECASE):
                                new_value = f"{new_gene}_{strend}"
                                setattr(obj, suffix, new_value)

        # 渲染模板
        return render(request, 'hierarchical_alignments_Vivi.html', {
            'alignment_data': list(result_objects),
            'alignment_data_draw': list(temp_modified_data),
            'genes_table': genes_table,
            'blast_results': blast_results,
            'hhh_page': None,  # 有搜索条件时不显示分页
            'page_obj': None,
            'total_pages': None
        })



# Eupl 为参考的共线性列表
def hierarchical_alignments_Eupl(request):
    global blast_results
    geneid = request.POST.get('geneid')
    sp_data_1 = request.POST.get("sp_data_1")
    query_sequence = request.POST.get('query_sequence')

    # 设置 line_number 默认值为 4
    line_number = 4

    # 初始化变量
    blast_results = None
    genes_table = []  # 初始化为空列表
    result_objects = []
    temp_modified_data = []
    page_obj = None
    total_pages = None
    orthofinder_strand_genes = []  # 初始化这个变量

    if sp_data_1 is None or geneid is None:
        alignment_data_query = HierarchicalAlignment_Eupl.objects.all()
        per_page = 10
        paginator = Paginator(alignment_data_query, per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        total_pages = paginator.num_pages

        result_objects = page_obj.object_list[:]
        result_objects_2 = page_obj.object_list[:]
        gene_strand_result = result_objects_2.values_list("hhh_number", "Eupl_1", "Eupl_2", "Nenu_1", "Nenu_2",
                                                          "Tesi_1", "Tesi_2", "Tesi_3", "Tesi_4", "Busi_1", "Busi_2",
                                                          "Vivi_1", "Vivi_2", "Vivi_3", "Nin_1", "Nin_2", "Nin_3",
                                                          "Arla_1", "Arla_2", "Arla_3", "Arla_4", "Arla_5", "Arla_6",
                                                          "Arla_7", "Arla_8", "Arla_9")

        gene_strand = [item for gene in gene_strand_result for item in gene if item != "."]
        orthofinder_strand_genes = HierarchicalGene.objects.filter(new_gene__in=gene_strand).values_list('chromosome',
                                                                                                         'start', 'end',
                                                                                                         'strend',
                                                                                                         'old_gene',
                                                                                                         'new_gene',
                                                                                                         'num')

        genes_table = list(orthofinder_strand_genes)  # 转换为列表

        temp_modified_data = result_objects_2

        # 更新基因的属性：遍历所有匹配的基因
        for gene_info in orthofinder_strand_genes:
            chromosome, start, end, strend, old_gene, new_gene, num = gene_info
            # 初始化 sp_name 和 suffixes
            sp_name = None
            suffixes = []
            # 映射前缀到sp_name的字典
            prefix_map = {
                "Busi": "Busi",
                "Nenu": "Nenu",
                "Eupl": "Eupl",
                "Nin": "Nin",
                "Vivi": "Vivi",
                "Tesi": "Tesi",
                "Arla": "Arla"
            }

            # 根据 new_gene 设置 sp_name
            for prefix, name in prefix_map.items():
                if new_gene.startswith(prefix):
                    sp_name = name
                    break

            if sp_name:
                # 根据sp_name生成suffixes
                if sp_name in ['Eupl', 'Nenu', 'Busi']:
                    suffixes.extend([f"{sp_name}_{i}" for i in range(1, 3)])
                elif sp_name == 'Tesi':
                    suffixes.extend([f"{sp_name}_{i}" for i in range(1, 5)])
                elif sp_name == 'Arla':
                    suffixes.extend([f"{sp_name}_{i}" for i in range(1, 10)])
                elif sp_name in ['Vivi', 'Nin']:
                    suffixes.extend([f"{sp_name}_{i}" for i in range(1, 4)])

                # 遍历 temp_modified_data，修改相应的基因数据
                for obj in temp_modified_data:
                    for suffix in suffixes:
                        obj_attr_value = getattr(obj, suffix, None)
                        if obj_attr_value and re.match(f"^{new_gene}$", obj_attr_value, re.IGNORECASE):
                            new_value = f"{new_gene}_{strend}"
                            setattr(obj, suffix, new_value)

        return render(request, 'hierarchical_alignments_eupl.html', {
            'alignment_data': result_objects,
            'alignment_data_draw': temp_modified_data,
            'genes_table': genes_table,
            'hhh_page': "NO",
            'page_obj': page_obj,
            'total_pages': total_pages
        })

    else:
        # 处理有搜索条件的情况
        if query_sequence:
            c = name_set()
            output_directory = f"{path_get}/file_keep/{c}"
            temp_fasta_file = write_fasta_file(query_sequence, output_directory)
            nucl_or_prot = "prot"
            species_data = sp_data_1
            e = "1e-5"
            blast_result_file = os.path.join(output_directory, "result.txt")
            run_blastp(temp_fasta_file, nucl_or_prot, species_data, e, blast_result_file)
            blast_results, geneids = parse_blastp_result(blast_result_file)

            if geneids and len(geneids) > 0:
                geneid = geneids[0]
            else:
                # 如果没有找到结果，返回空结果
                return render(request, 'hierarchical_alignments_eupl.html', {
                    'alignment_data': [],
                    'alignment_data_draw': [],
                    'genes_table': [],
                    'blast_results': blast_results
                })
        else:
            geneid = geneid

        # 构建查询条件
        if sp_data_1 in ['Eupl', 'Nenu', 'Busi']:
            condition = Q(**{f'{sp_data_1}_1': geneid}) | Q(**{f'{sp_data_1}_2': geneid})
        elif sp_data_1 in ['Vivi', 'Nin']:
            condition = Q(**{f'{sp_data_1}_1': geneid}) | Q(**{f'{sp_data_1}_2': geneid}) | Q(
                **{f'{sp_data_1}_3': geneid})
        elif sp_data_1 == 'Tesi':
            condition = Q(**{f'{sp_data_1}_1': geneid}) | Q(**{f'{sp_data_1}_2': geneid}) | Q(
                **{f'{sp_data_1}_3': geneid}) | Q(**{f'{sp_data_1}_4': geneid})
        elif sp_data_1 == 'Arla':
            # Arla有9个字段
            condition = Q()
            for i in range(1, 10):
                condition = condition | Q(**{f'Arla_{i}': geneid})
        else:
            # 对于其他物种，默认使用_1后缀
            field_name = f"{sp_data_1}_1"
            condition = Q(**{field_name: geneid})

        # 执行查询
        try:
            result = HierarchicalAlignment_Eupl.objects.filter(condition)
        except Exception as e:
            print(f"查询错误: {e}")
            return render(request, 'hierarchical_alignments_eupl.html', {
                'alignment_data': [],
                'alignment_data_draw': [],
                'genes_table': [],
                'blast_results': blast_results,
                'error': f"查询字段不存在: {sp_data_1}"
            })

        hhh_numbers = [obj.hhh_number for obj in result]

        # 获取目标行号
        target_numbers = set()
        for id in hhh_numbers:
            id = int(id)
            for i in range(id - line_number, id + line_number + 1):
                target_numbers.add(i)

        # 获取目标数据
        result_objects = HierarchicalAlignment_Eupl.objects.filter(hhh_number__in=target_numbers)
        result_objects_2 = HierarchicalAlignment_Eupl.objects.filter(hhh_number__in=target_numbers)

        # 获取基因信息
        if result_objects_2.exists():
            gene_strand_result = result_objects_2.values_list("hhh_number", "Eupl_1", "Eupl_2", "Nenu_1", "Nenu_2",
                                                              "Tesi_1", "Tesi_2", "Tesi_3", "Tesi_4", "Busi_1",
                                                              "Busi_2", "Vivi_1", "Vivi_2", "Vivi_3", "Nin_1", "Nin_2",
                                                              "Nin_3", "Arla_1", "Arla_2", "Arla_3", "Arla_4", "Arla_5",
                                                              "Arla_6", "Arla_7", "Arla_8", "Arla_9")

            gene_strand = [item for gene in gene_strand_result for item in gene if item != "."]

            if gene_strand:
                orthofinder_strand_genes = list(HierarchicalGene.objects.filter(new_gene__in=gene_strand).values_list(
                    'chromosome', 'start', 'end', 'strend', 'old_gene', 'new_gene', 'num'))
                genes_table = orthofinder_strand_genes

        temp_modified_data = result_objects_2

        # 更新基因的属性 - 只在 genes_table 不为空时执行
        if genes_table:
            for gene_info in genes_table:
                chromosome, start, end, strend, old_gene, new_gene, num = gene_info
                sp_name = None
                suffixes = []
                prefix_map = {
                    "Busi": "Busi",
                    "Nenu": "Nenu",
                    "Eupl": "Eupl",
                    "Nin": "Nin",
                    "Vivi": "Vivi",
                    "Tesi": "Tesi",
                    "Arla": "Arla"
                }

                # 根据 new_gene 设置 sp_name
                for prefix, name in prefix_map.items():
                    if new_gene.startswith(prefix):
                        sp_name = name
                        break

                if sp_name:
                    # 根据sp_name生成suffixes
                    if sp_name in ['Eupl', 'Nenu', 'Busi']:
                        suffixes.extend([f"{sp_name}_{i}" for i in range(1, 3)])
                    elif sp_name == 'Tesi':
                        suffixes.extend([f"{sp_name}_{i}" for i in range(1, 5)])
                    elif sp_name == 'Arla':
                        suffixes.extend([f"{sp_name}_{i}" for i in range(1, 10)])
                    elif sp_name in ['Vivi', 'Nin']:
                        suffixes.extend([f"{sp_name}_{i}" for i in range(1, 4)])

                    for obj in temp_modified_data:
                        for suffix in suffixes:
                            obj_attr_value = getattr(obj, suffix, None)
                            if obj_attr_value and re.match(f"^{new_gene}$", obj_attr_value, re.IGNORECASE):
                                new_value = f"{new_gene}_{strend}"
                                setattr(obj, suffix, new_value)

        # 渲染模板
        return render(request, 'hierarchical_alignments_eupl.html', {
            'alignment_data': list(result_objects),
            'alignment_data_draw': list(temp_modified_data),
            'genes_table': genes_table,
            'blast_results': blast_results,
            'hhh_page': None,  # 有搜索条件时不显示分页
            'page_obj': None,
            'total_pages': None
        })


# 将序列信息写入一个临时文件中
def write_fasta_file(query_sequence, output_directory):
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    temp_fasta_file = os.path.join(output_directory, "temp_query.fasta")
    query_sequence = (query_sequence or '').strip()
    with open(temp_fasta_file, "w") as f:
        current_gene_id = None
        current_sequence = ""
        has_header = any(line.strip().startswith(">") for line in query_sequence.splitlines())
        if not has_header and query_sequence:
            cleaned_sequence = ''.join(line.strip() for line in query_sequence.splitlines() if line.strip())
            f.write(f">query_sequence_1\n{cleaned_sequence}\n")
            return temp_fasta_file
        for line in query_sequence.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if current_gene_id and current_sequence:
                    f.write(f">{current_gene_id}\n{current_sequence}\n")
                current_gene_id = line[1:].strip() or 'query_sequence'
                current_sequence = ""
            else:
                current_sequence += line
        if current_gene_id and current_sequence:
            f.write(f">{current_gene_id}\n{current_sequence}\n")
    return temp_fasta_file


# 调用 blastp
def run_blastp(query_file, nucl_or_prot, species_data, evalue, output_file, db_paths=None, max_target_seqs=1):
    output_directory = os.path.dirname(query_file)
    print({output_directory})
    setup_cmd = ""
    if db_paths is None:
        db_value = f"{path_get}/static/blast_match_database/{nucl_or_prot}/{species_data}"
    else:
        db_type = "prot" if nucl_or_prot == "prot" else "nucl"
        db_alias = os.path.join(output_directory, f"{species_data}_blastdb_alias")
        db_list = " ".join(db_paths)
        setup_cmd = f'blastdb_aliastool -dblist "{db_list}" -dbtype {db_type} -out "{db_alias}" -title "{species_data}"'
        db_value = db_alias
    cmd = f"""
    source /etc/profile
    cd "{output_directory}"
    {setup_cmd}
    blastp -query "{query_file}" -db "{db_value}" -outfmt 6 -evalue {evalue} -out "{output_file}" -num_threads 8 -max_target_seqs {int(max_target_seqs)}
    """
    run_kwargs = {
        'shell': True,
        'capture_output': True,
        'text': True,
    }
    if os.name != 'nt' and os.path.exists('/bin/bash'):
        run_kwargs['executable'] = '/bin/bash'
    completed = subprocess.run(cmd, **run_kwargs)
    log_path = os.path.join(output_directory, 'blast_command.log')
    try:
        with open(log_path, 'a', encoding='utf-8') as log_file:
            log_file.write('\n===== BLAST command =====\n')
            log_file.write(cmd)
            log_file.write(f'\nreturncode: {completed.returncode}\n')
            if completed.stdout:
                log_file.write('stdout:\n')
                log_file.write(completed.stdout)
            if completed.stderr:
                log_file.write('stderr:\n')
                log_file.write(completed.stderr)
    except Exception:
        pass
    if completed.returncode != 0:
        print(completed.stderr)
    return completed.returncode


# 解析 blastp 结果文件
def _parse_nonnegative_float(value, label):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise ValueError(f'Please enter a valid {label}.')
    if parsed < 0:
        raise ValueError(f'{label} must be greater than or equal to 0.')
    return parsed


def _blast_row_passes_filters(fields, max_evalue=None, min_score=None, min_identity=None):
    identity = float(fields[2])
    evalue = float(fields[10])
    bitscore = float(fields[11])

    if max_evalue is not None and evalue > max_evalue:
        return False
    if min_score is not None and bitscore < min_score:
        return False
    if min_identity is not None and identity < min_identity:
        return False
    return True


def _format_blast_row(fields, ancestor=None):
    row = (
        fields[0],
        _subject_gene_id_from_blast_fields(fields) if '_subject_gene_id_from_blast_fields' in globals() else fields[1],
        float(fields[2]),
        int(fields[3]),
        int(fields[4]),
        int(fields[5]),
        int(fields[6]),
        int(fields[7]),
        int(fields[8]),
        int(fields[9]),
        f"{float(fields[10]):.2e}",
        f"{float(fields[11]):.2e}",
    )
    if ancestor is not None:
        row = row + (ancestor,)
    return row


def write_filtered_blast_result_file(
        source_file,
        output_file,
        max_evalue,
        min_score,
        min_identity,
        ancestor=None,
        mode='w'):
    total_hits = 0
    kept_hits = 0
    with open(source_file, 'r') as source, open(output_file, mode) as output:
        for line in source:
            fields = line.strip().split("\t")
            if len(fields) < 12:
                continue
            try:
                passed = _blast_row_passes_filters(
                    fields,
                    max_evalue=max_evalue,
                    min_score=min_score,
                    min_identity=min_identity,
                )
            except ValueError:
                continue

            total_hits += 1
            if passed:
                row = line.rstrip("\n")
                if ancestor is not None:
                    row = f"{row}\t{ancestor}"
                output.write(f"{row}\n")
                kept_hits += 1
    return total_hits, kept_hits


def parse_blastp_result(
        blast_result_file,
        max_evalue=None,
        min_score=None,
        min_identity=None,
        include_ancestor=False,
        default_ancestor=None):
    blast_results = []
    with open(blast_result_file, "r") as f:
        for line in f:
            fields = line.strip().split("\t")
            if len(fields) < 12:
                continue
            try:
                if not _blast_row_passes_filters(
                    fields,
                    max_evalue=max_evalue,
                    min_score=min_score,
                    min_identity=min_identity,
                ):
                    continue
                ancestor = None
                if include_ancestor:
                    if len(fields) >= 14:
                        ancestor = fields[-1]
                    elif len(fields) >= 13 and _normalize_ancestor_code(fields[12]) in ANCESTRAL_DATASETS:
                        ancestor = fields[12]
                    else:
                        ancestor = default_ancestor
                blast_results.append(_format_blast_row(fields, ancestor=ancestor))
            except ValueError:
                continue
    subject_ids = [result[1] for result in blast_results]
    return blast_results, subject_ids


def build_ancestral_alignment_payload(blast_results, metadata):
    selected_codes = []
    for code in metadata.get('species_codes') or []:
        normalized = _normalize_ancestor_code(code)
        if normalized in ANCESTRAL_DATASETS and normalized not in selected_codes:
            selected_codes.append(normalized)

    selected_set = set(selected_codes)
    summaries = {
        code: {
            'code': code,
            'label': _ancestor_label(code),
            'selected': True,
            'hit_count': 0,
            'top_hits': [],
        }
        for code in selected_codes
    }

    for row in blast_results:
        if len(row) < 13:
            continue
        code = _normalize_ancestor_code(row[12])
        if code not in ANCESTRAL_DATASETS:
            continue

        summary = summaries.setdefault(code, {
            'code': code,
            'label': _ancestor_label(code),
            'selected': code in selected_set,
            'hit_count': 0,
            'top_hits': [],
        })
        summary['hit_count'] += 1
        try:
            score_value = float(row[11])
        except (TypeError, ValueError):
            score_value = 0.0
        try:
            evalue_value = float(row[10])
        except (TypeError, ValueError):
            evalue_value = float('inf')

        summary['top_hits'].append({
            'query': row[0],
            'subject': row[1],
            'identity': row[2],
            'length': row[3],
            'qstart': row[6],
            'qend': row[7],
            'sstart': row[8],
            'send': row[9],
            'evalue': row[10],
            'bit_score': row[11],
            'score_value': score_value,
            'evalue_value': evalue_value,
        })

    for summary in summaries.values():
        summary['top_hits'].sort(key=lambda hit: (-hit['score_value'], hit['evalue_value']))
        summary['top_hits'] = [
            {
                key: value
                for key, value in hit.items()
                if key not in ('score_value', 'evalue_value')
            }
            for hit in summary['top_hits'][:5]
        ]
        summary['best_hit'] = summary['top_hits'][0] if summary['top_hits'] else None

    return {
        'query_name': metadata.get('query_name', ''),
        'selected_ancestors': selected_codes,
        'summaries': summaries,
    }


def event_gene(request):
    sp_data_1 = (request.POST.get("sp_data_1") or '').strip()
    geneid = (request.POST.get('geneid') or '').strip()
    query_sequence = (request.POST.get('query_sequence') or '').strip()
    context = {
        'selected_sp_data_1': sp_data_1,
        'submitted_geneid': geneid,
        'submitted_query_sequence': query_sequence,
        'has_searched': request.method == 'POST',
    }

    if request.method != 'POST':
        return render(request, 'event_gene.html', context)

    if not sp_data_1 or (not geneid and not query_sequence):
        context['info_message'] = 'Please enter at least one gene ID or protein sequence.'
        return render(request, 'event_gene.html', context)

    if query_sequence:
        c = name_set()
        output_directory = f"{path_get}/file_keep/{c}"
        blast_results, geneids = _run_selected_species_blast(query_sequence, output_directory, sp_data_1)
    else:
        blast_results = None
        geneids = [item.strip() for item in geneid.replace('\r', '').split('\n') if item.strip()]

    if not geneids:
        context.update({
            'blast_results': blast_results,
            'info_message': 'No matching genes were found for the submitted query.'
        })
        return render(request, 'event_gene.html', context)

    geneid_placeholders = ','.join(['%s'] * len(geneids))
    sql_query = f"SELECT * FROM Event_genes_table WHERE gene1 IN ({geneid_placeholders}) OR gene2 IN ({geneid_placeholders})"
    with connection.cursor() as cursor:
        cursor.execute(sql_query, geneids * 2)  # 重复两次以匹配 OR 条件中的参数数量
        result = cursor.fetchall()
    found_geneids = [str(item) for row in result for item in row[1:3]]
    print(found_geneids)
    orthofinder_strand_genes = HierarchicalGene.objects.filter(new_gene__in=found_geneids).values_list('chromosome',
                                                                                                       'start', 'end',
                                                                                                       'strend',
                                                                                                       'old_gene',
                                                                                                       'new_gene',
                                                                                                       'num')
    connection.close()

    context.update({
        'result': result,
        'genes_table': orthofinder_strand_genes,
        'blast_results': blast_results if query_sequence else None
    })
    if not result:
        context['info_message'] = 'No event genes were found for the current query.'
    return render(request, 'event_gene.html', context)



from django.core.paginator import Paginator
from django.shortcuts import render
# from .models import TEModel

def te_information(request):
    return TE_index1(request)



def gene_detail(request, geneid=None):  # 让geneid可选
    global blast_results

    def render_gene_error(message, submitted_geneid=None):
        return render(request, 'gene_detail.html', {
            'error': message,
            'submitted_geneid': submitted_geneid or '',
        })

    # 处理两种输入方式
    query_sequence = (request.POST.get('query_sequence') or '').strip()
    post_geneid = (request.POST.get('geneid') or '').strip()

    # 确定最终的geneid和搜索类型
    if query_sequence:
        species_data = (request.POST.get('species') or '').strip()
        if species_data not in INTERPROSCAN_SPECIES:
            return render_gene_error('Please choose a valid species before searching.')

        # 序列搜索模式
        try:
            c = name_set()
            output_directory = f"{path_get}/file_keep/{c}"
            temp_fasta_file = write_fasta_file(query_sequence, output_directory)

            nucl_or_prot = "prot"
            e = "1e-5"
            blast_result_file = os.path.join(output_directory, "result.txt")
            run_blastp(temp_fasta_file, nucl_or_prot, species_data, e, blast_result_file)
            blast_results, geneids = parse_blastp_result(blast_result_file)
            geneids = [item.strip() for item in geneids if item and item.strip()]
        except Exception as exc:
            print(f"Gene detail BLAST search failed: {exc}")
            return render_gene_error('Sequence search failed. Please check the sequence format and try again.')

        # 使用BLAST结果中的第一个geneid
        if geneids:
            geneid = geneids[0]  # 使用BLAST找到的最佳匹配
        else:
            # 如果没有找到匹配，返回错误或空结果
            return render_gene_error('No matching genes found for the submitted sequence.')
    else:
        # 基因ID搜索模式
        if post_geneid:
            geneid = post_geneid  # 使用POST中的geneid
        # 否则使用URL中的geneid（如果存在）

    geneid = (geneid or '').strip()
    if not geneid:
        return render_gene_error('Please enter a gene ID or protein sequence before searching.')

    if geneid == 'PLACEHOLDER' or not GENE_ID_ALLOWED_RE.fullmatch(geneid):
        return render_gene_error('Please enter a valid gene ID, for example Aann9g00954.', geneid)

    # 现在确定物种名称
    sp_name = _resolve_gene_species(geneid)
    if not sp_name:
        return render_gene_error('The gene ID does not start with a supported species code.', geneid)

    print(sp_name, geneid)
    # cds - pep
    sql_query = f"SELECT * FROM {sp_name}_cds_pep WHERE gene_id = %s"
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql_query, [geneid])
            cds_pep_infor = cursor.fetchall()
    except Exception as exc:
        print(f"Gene detail sequence query failed: {exc}")
        return render_gene_error('Gene search is temporarily unavailable. Please try again later.', geneid)

    if not cds_pep_infor:
        return render_gene_error(f'No records were found for gene ID: {geneid}', geneid)
    from .agrp_switch import build_switch_context
    context = build_switch_context(geneid, sp_name, cds_pep_infor, str(settings.BASE_DIR))
    return render(request, 'gene_detail.html', context)


def process_lens_files(sp_data_1, chromosome_data_1, sp_data_2, chromosome_data_2, path_get, c):
    result_1 = {}
    result_2 = {}
    # 处理 sp_data_1.lens 文件
    lens_file_1 = os.path.join(path_get, f'file_keep/{c}', f'{sp_data_1}.lens')
    with open(lens_file_1, 'r') as file:
        for line in file:
            chromosome, genes = line.strip().split()
            if int(chromosome) in chromosome_data_1:
                result_1[chromosome] = int(genes)

    # 处理 sp_data_2.lens 文件
    lens_file_2 = os.path.join(path_get, f'file_keep/{c}', f'{sp_data_2}.lens')
    with open(lens_file_2, 'r') as file:
        for line in file:
            chromosome, genes = line.strip().split()
            if int(chromosome) in chromosome_data_2:
                result_2[chromosome] = int(genes)

    return result_1, result_2


def write_lens_files(result_1, result_2, sp_data_1, sp_data_2, path_get, c):
    lens_file_1 = os.path.join(path_get, f'file_keep/{c}', f'{sp_data_1}.lens')
    with open(lens_file_1, 'w') as file:
        for chromosome, genes in result_1.items():
            file.write(f"{chromosome}\t{genes}\n")

    lens_file_2 = os.path.join(path_get, f'file_keep/{c}', f'{sp_data_2}.lens')
    with open(lens_file_2, 'w') as file:
        for chromosome, genes in result_2.items():
            file.write(f"{chromosome}\t{genes}\n")


class DotPlot:
    def __init__(self, num_process, suffix, bed_path, blast_path, result_path, name_change):
        self.num_process = num_process
        self.suffix = suffix
        self.name_change = name_change
        self.bed = os.path.join('.', bed_path)
        self.blast_path = os.path.join('.', blast_path)
        self.result_path = os.path.join('.', result_path)

        self.colors = ['red', 'blue', 'white']
        # self.colors = ['orangered', 'blue', 'gray']
        self.hitnum = 5
        self.align = dict(family='Times New Roman', horizontalalignment="center",
                          verticalalignment="center", weight='semibold')

    @staticmethod
    def check_file(file_path):
        n = os.path.isfile(file_path)
        file_name = os.path.basename(file_path)
        if not n:
            print(f'{file_name}---File not exist!!!')

    @staticmethod
    def get_spec_chr(spec_chr):
        spec_chr = re.sub('^\\D+', '', spec_chr)
        spec_chr = re.sub('^0', '', spec_chr)
        return spec_chr

    def gene_location(self, spec, gl):
        len_pos, gff_pos = 1, 6
        chr_dict, chr_lens, loc_gene, n = {}, {}, {}, 0
        self.check_file(f'{self.bed}/{spec}.lens')
        for li in open(f'{self.bed}/{spec}.lens'):
            lis = li.strip().split()
            spec_chr = self.get_spec_chr(lis[0])
            chr_lens[spec_chr] = float(lis[len_pos])
            chr_dict[spec_chr] = float(n)
            n += float(lis[len_pos])
        total_lens = reduce(lambda x, y: int(x) + int(y), chr_lens.values())
        step = gl / total_lens
        self.check_file(f'{self.bed}/{spec}.new.gff')
        for li in open(f'{self.bed}/{spec}.new.gff'):
            lis = li.strip().split()
            spec_chr = self.get_spec_chr(lis[0])
            if spec_chr not in chr_dict:
                continue
            loc = (chr_dict[spec_chr] + float(lis[gff_pos])) * step
            loc_gene[lis[5]] = loc

        return loc_gene, step, chr_lens

    def getnewblast(self, blast, score, evalue, repnum, loc_1, loc_2):
        newblast = {}
        for li in open(blast):
            lis = li.strip().split()
            if not all((float(lis[11]) >= score, float(lis[10]) < evalue, lis[0] != lis[1])):
                continue
            if not all((lis[0] in loc_1, lis[1] in loc_2)):
                continue
            if lis[0] in newblast and lis[1] in newblast[lis[0]]:
                continue
            if lis[0] in newblast and len(newblast[lis[0]]) < repnum:
                newblast[lis[0]].append(lis[1])
            else:
                newblast[lis[0]] = [lis[1]]
        return newblast

    def pair_positon(self, blast, loc1, loc2):
        pos1, pos2, newcolor = [], [], []
        gl_start1, gl_start2 = 11 / 12, 1 / 12
        for k, v in blast.items():
            for i in range(len(v)):
                if i == 0:
                    color = self.colors[0]
                elif i <= self.hitnum:
                    color = self.colors[1]
                else:
                    color = self.colors[2]
                pos1.append(gl_start2 + loc2[v[i]])
                pos2.append(gl_start1 - loc1[k])
                newcolor.append(color)
        return pos1, pos2, newcolor

    def plot_line(self, x, y):
        plt.plot(x, y, linestyle='-', color='black', linewidth=0.25)
        plt.plot(x, y, linestyle='-', color='black', linewidth=0.75, alpha=0.5)

    def plot_chr1(self, lens, gl, gl2, step, mark, name):
        gl_start, n, start_x = 11 / 12, 0, 1 / 12
        mark_y = 17 / 240
        for k in lens.keys():
            n += lens[k]
            mark_new = str(mark) + str(k)
            x = gl_start - float(n) * step
            mark_x = x + 0.5 * lens[k] * step
            self.plot_line([start_x, start_x + gl2], [x, x])
            plt.text(mark_y, mark_x, mark_new, color='black', fontsize=14, rotation=0, **self.align, style='normal')
        self.plot_line([start_x, start_x + gl2], [gl_start, gl_start])
        plt.text(mark_y - 0.03, 0.5 * (2 * gl_start - gl), name, color='black', fontsize=18, rotation=90,
                 **self.align, fontstyle='italic')

    def plot_chr2(self, lens, gl, gl2, step, mark, name):
        gl_start, n, start_x = 1 / 12, 0, 11 / 12
        mark_y = 223 / 240
        for k in lens.keys():
            n += lens[k]
            mark_new = str(mark) + str(k)
            x = gl_start + float(n) * step
            mark_x = x - 0.5 * lens[k] * step
            self.plot_line([x, x], [start_x, start_x - gl2])
            plt.text(mark_x, mark_y, mark_new, color='black', fontsize=14, rotation=0, **self.align, style='normal')
        self.plot_line([gl_start, gl_start], [start_x, start_x - gl2])
        plt.text(0.5 * (2 * gl_start + gl), mark_y + 0.03, name, color='black', fontsize=18, rotation=0,
                 **self.align, fontstyle='italic')

    def plotfig(self, spec1, spec2):
        plt.figure(figsize=(8, 8), dpi=300)
        root = plt.axes([0, 0, 1, 1])
        gl1, gl2 = 5 / 6, 5 / 6
        gene_loc_1, step1, chr1_lens = self.gene_location(spec1, gl1)
        gene_loc_2, step2, chr2_lens = self.gene_location(spec2, gl2)
        self.plot_chr1(chr1_lens, gl1, gl2, step1, '', self.name_change[spec1])
        self.plot_chr2(chr2_lens, gl1, gl2, step2, '', self.name_change[spec2])
        score, evalue, repnum = 100, 1e-5, 20
        blast = f'{self.blast_path}/{spec1}_{spec2}.{self.suffix}'
        blast = self.getnewblast(blast, score, evalue, repnum, gene_loc_1, gene_loc_2)
        x, y, colors = self.pair_positon(blast, gene_loc_1, gene_loc_2)
        plt.scatter(x, y, s=0.5, c=colors, alpha=0.5, edgecolors=None, linewidths=0, marker='o')
        root.set_xlim(0, 1)
        root.set_ylim(0, 1)
        root.set_axis_off()
        plt.savefig(f'{self.result_path}/{spec1}_{spec2}.png')
        # plt.savefig(f'{self.result_path}/{spec1}_{spec2}.pdf')

    def main(self):
        p = Pool(self.num_process)
        blasts = glob.glob(f'{self.blast_path}/*.{self.suffix}')
        for file in blasts:
            fna = os.path.basename(file)
            spec1, spec2 = fna.split('.')[0].split('_')
            # self.plotfig(spec1, spec2)
            p.apply_async(self.plotfig, args=(spec1, spec2))

        p.close()
        p.join()


class DotplotBlock:
    def __init__(self, num_process, suffix, block_num, bed_path, block_blast_path, result_path, name_change):
        self.num_process = num_process
        self.suffix = suffix
        self.name_change = name_change
        self.block_num = block_num
        self.bed = os.path.join('.', bed_path)
        self.block_blast_path = os.path.join('.', block_blast_path)
        self.result_path = os.path.join('.', result_path)

    def select_blast(self, blast_path, block_path):
        gene_pair_list, pair_pos, last_na1, last_na2, result_pair, num = [], {}, '', '', [], 1
        gene_dit = self.get_block(block_path)
        for li in open(blast_path):
            lis = li.strip().split()
            if 'Scaffold' in li or lis[0] == lis[1]:
                continue
            if lis[0] in gene_dit and lis[1] == gene_dit[lis[0]]:
                gene_pair_list.append(f'{lis[0]}\t{lis[1]}')
            if last_na1 == lis[0] and last_na2 != lis[1]:
                num += 1
            else:
                num = 1
            pair_pos[f'{lis[0]}\t{lis[1]}'] = str(num)
            last_na1, last_na2 = lis[0], lis[1]

        for pair in gene_pair_list:
            if pair in pair_pos:
                row = pair.split('\t')
                row.append(pair_pos[pair])
                result_pair.append(row)

        blast = pd.DataFrame(result_pair)
        return blast

    def get_block(self, path):
        gene_dit = {}
        block, blocks = [], []
        for li in open(path):
            li = li.strip()
            if '>' in li:
                if len(block) >= self.block_num:
                    for row in block:
                        rows = re.split('\\s', row)
                        gene_dit[rows[0]] = rows[2]
                    # blocks.append(block)
                block = []
            elif any(([x in li for x in ['overlap', 'LOCALE',
                                         'self', 'the', '>']])):
                continue
            elif li:
                block.append(li)

        return gene_dit

    def plot_chr1(self, lens, gl, gl2, step, mark, name):  # 竖物种
        gl_start, n, start_x = 11/12, 0, 1/12
        mark_y = 17/240
        align = dict(family='Times New Roman', style='normal', horizontalalignment="center", verticalalignment="center")###染色体号
        align1 = dict(family='Times New Roman', style='italic', horizontalalignment="center", verticalalignment="center")###物种拉丁文
        for k in lens.index:
            n += float(lens.at[k, 1])
            mark_new = str(mark) + str(k)
            x = gl_start - float(n) * step
            mark_x = x + 0.5 * float(lens.at[k, 1]) * step
            plt.plot([start_x, start_x + gl2], [x, x], linestyle='-', color='black', linewidth=0.125)
            plt.plot([start_x, start_x + gl2], [x, x], linestyle='-', color='black', linewidth=0.375, alpha=0.5)
            plt.text(mark_y, mark_x, mark_new, color='black', fontsize=15, rotation=0, weight='semibold', **align)
        plt.plot([start_x, start_x + gl2], [gl_start, gl_start], linestyle='-', color='black', linewidth=0.375,
                 alpha=0.5)
        plt.plot([start_x, start_x + gl2], [gl_start, gl_start], linestyle='-', color='black', linewidth=0.125)
        plt.text(mark_y-0.04, 0.5 * (2 * gl_start - gl), name, color='black', fontsize=20, rotation=90,
                 weight='semibold', **align1)

    def plot_chr2(self, lens, gl, gl2, step, mark, name):
        gl_start, n, start_x = 1/12, 0, 11/12
        mark_y = 223/240
        align = dict(family='Times New Roman', style='normal', horizontalalignment="center", verticalalignment="center")
        align1 = dict(family='Times New Roman', style='italic', horizontalalignment="center", verticalalignment="center")
        for k in lens.index:
            n += float(lens.at[k, 1])
            mark_new = str(mark) + str(k)
            x = gl_start + float(n) * step
            mark_x = x - 0.5 * float(lens.at[k, 1]) * step
            plt.plot([x, x], [start_x, start_x - gl2], linestyle='-', color='black', linewidth=0.125)
            plt.plot([x, x], [start_x, start_x - gl2], linestyle='-', color='black', linewidth=0.375, alpha=0.5)
            plt.text(mark_x, mark_y, mark_new, color='black', fontsize=15, rotation=0, weight='semibold', **align)
        plt.plot([gl_start, gl_start], [start_x, start_x - gl2], linestyle='-', color='black', linewidth=0.375,
                 alpha=0.5)
        plt.plot([gl_start, gl_start], [start_x, start_x - gl2], linestyle='-', color='black', linewidth=0.125)
        plt.text(0.5 * (2 * gl_start + gl)+0.07, mark_y + 0.03, name, color='black', fontsize=20, rotation=0,
                 weight='semibold', **align1)

    def gene_location(self, gff, lens, step):
        loc_gene, dict_chr, n = {}, {}, 0
        for i in lens.index:
            dict_chr[str(i)] = n
            n += float(lens.at[i, 1])
        for k in gff.index:
            if gff.loc[k, 0] not in dict_chr:
                continue
            loc = (float(dict_chr[gff.loc[k, 0]]) + float(gff.loc[k, 6])) * step
            loc_gene[gff.loc[k, 5]] = loc
        return loc_gene

    def pair_positon(self, data, loc1, loc2, colors):
        pos1, pos2, newcolor = [], [], []
        gl_start1, gl_start2 = 11 / 12, 1 / 12
        for index, k in data.iterrows():
            x = gl_start1 - loc1[k[0]]
            y = gl_start2 + loc2[k[1]]
            pos1.append(y)
            pos2.append(x)
            if k[2] == '1':
                color = colors[0]
            else:
                color = colors[1]

            newcolor.append(color)
        return pos1, pos2, newcolor

    def plotfig(self, spec1, spec2):
        plt.figure(figsize=(8, 8), dpi=300)
        root = plt.axes([0, 0, 1, 1])
        gff_1 = pd.read_csv(f'{self.bed}/{spec1}.new.gff', sep="\t", header=None)
        gff_2 = pd.read_csv(f'{self.bed}/{spec2}.new.gff', sep="\t", header=None)
        gff_1[0] = gff_1[0].astype('str')
        gff_2[0] = gff_2[0].astype('str')
        lens_1 = pd.read_csv(f'{self.bed}/{spec1}.lens', sep="\t", header=None, index_col=0)
        lens_2 = pd.read_csv(f'{self.bed}/{spec2}.lens', sep="\t", header=None, index_col=0)
        gl1, gl2 = 5/6, 5/6
        step1 = gl1 / float(lens_1[1].sum())
        step2 = gl2 / float(lens_2[1].sum())
        self.plot_chr1(lens_1, gl1, gl2, step1, '', self.name_change[spec1])
        self.plot_chr2(lens_2, gl1, gl2, step2, '', self.name_change[spec2])
        gene_loc_1 = self.gene_location(gff_1, lens_1, step1)
        gene_loc_2 = self.gene_location(gff_2, lens_2, step2)
        blast = self.select_blast(f'{self.block_blast_path}/{spec1}_{spec2}.{self.suffix}',
                                  f'{self.block_blast_path}/{spec1}_{spec2}.block.rr.txt')
        blast = blast[(blast[0].isin(gene_loc_1.keys())) & (blast[1].isin(gene_loc_2.keys()))]
        colors = ['orangered', 'gray']
        x, y, colors = self.pair_positon(blast, gene_loc_1, gene_loc_2, colors)
        plt.scatter(x, y, s=1, c=colors, alpha=0.5, edgecolors=None, linewidths=0)
        root.set_xlim(0, 1)
        root.set_ylim(0, 1)
        root.set_axis_off()
        plt.savefig(f'{self.result_path}/{spec1}_{spec2}.{self.block_num}.2400.png')
        # plt.savefig(f'{self.result_path}/{spec1}_{spec2}.{self.block_num}.2400.pdf')

    def main(self):
        p = Pool(self.num_process)
        blasts = glob.glob(f'{self.block_blast_path}/*.blast')
        for file in blasts:
            fna = os.path.basename(file)
            spec1, spec2 = fna.split('.')[0].split('_')
            p.apply_async(self.plotfig, args=(spec1, spec2))

        p.close()
        p.join()


def dotplot(request):
    if request.method == 'POST':
        sp_data_1 = request.POST.get('sp_data_1')
        chromosome_data_1 = [int("".join(filter(str.isdigit, item))) for item in request.POST.getlist("chromosome_data_1[]")]
        sp_data_2 = request.POST.get("sp_data_2")
        chromosome_data_2 = [int("".join(filter(str.isdigit, item))) for item in request.POST.getlist('chromosome_data_2[]')]
        options_1 = request.POST.get('options_1')
        block_number = request.POST.get('block_number', None)

        print(sp_data_1, chromosome_data_1, sp_data_2, chromosome_data_2, options_1)

        if not chromosome_data_1 or not chromosome_data_2:
            return HttpResponse('Chromosome data cannot be empty')

        c = name_set()
        sp_dict = {"Aarg":"Artemisia argyi ","Aann":"Artemisia annua","Amar":"Ambrosia artemisiifolia","Amtr":"Ambrosia trifida","Arla":"Arctium lappa","Armi":"Arctium minus","Artr":"Artemisia tridentata","Bial":"Bidens alba","Busi":"Buxus sinica","Cati":"Carthamus tinctorius","Ccar":"Cynara cardunculus","Ceso":"Centaurea solstitialis","Chla":"Chrysanthemum lavandulifolium","Chma":"Chrysanthemum makinoi","Chmo":"Chrysanthemum morifolium","Chna":"Chrysanthemum nankingense","Cich":"Cichorium intybus","Cien":"Cichorium endivia","Cind":"Chrysanthemum indicum","Cobi":"Cosmos bipinnata","Cpa":"Centrapalus pauciflorus","Dapi":"Dahlia pinnata.nucleus","Desu":"Deinandra increscens subsp. villosa","Ecan":"Erigeron canadensis","Enbr":"Erigeron breviscapus","Eupl":"Euptelea pleiosperma","Fbi":"Flaveria bidentis","Fbr":"Flaveria brownii","Ffl":"Flaveria floridana","Fli":"Flaveria linearis","Fra":"Flaveria ramosissima","Fro":"Flaveria robusta","Fso":"Flaveria sonorensis","Ftr":"Flaveria trinervia","Glco":"Glebionis coronaria","Hean":"Helianthus annuus","Hetu":"Helianthus tuberosus","Heub":"Helichrysum umbraculigerum","Laca":"Lactuca saligna","Lomi":"Logfia minima","Lssa":"Lactuca sativa","Mimi":"Mikania micrantha","Nenu":"Nelumbo nucifera","Nin":"Nymphoides indica","Pdy":"Pulicaria dysenterica","Pin":"Pluchea indica","Pslu":"Pseudognaphalium luteoalbum","Sain":"Saussurea involucrata","Scae":"Solidago caesia","Sesq":"Senecio squalidus","Smso":"Smallanthus sonchifolius","Soca":"Solidago canadensis","Stre":"Stevia rebaudiana","Taer":"Tagetes erecta","Tako":"Taraxacum koksaghyz","Tamo":"Taraxacum mongolicum","Tesi":"Tetracentron sinense","Vivi":"Vitis vinifera"}
        # Aann_Aann.blast.zip
        target_folder = f"{path_get}/file_keep/{c}"
        shutil.copyfile(os.path.join(path_get, 'static', 'blastp_blk_ks_zip', f'{sp_data_1}.new.gff'), os.path.join(target_folder, f'{sp_data_1}.new.gff'))
        shutil.copyfile(os.path.join(path_get, 'static', 'blastp_blk_ks_zip', f'{sp_data_1}.lens'), os.path.join(target_folder, f'{sp_data_1}.lens'))
        shutil.copyfile(os.path.join(path_get, 'static', 'blastp_blk_ks_zip', f'{sp_data_2}.new.gff'), os.path.join(target_folder, f'{sp_data_2}.new.gff'))
        shutil.copyfile(os.path.join(path_get, 'static', 'blastp_blk_ks_zip', f'{sp_data_2}.lens'), os.path.join(target_folder, f'{sp_data_2}.lens'))

        result_1, result_2 = process_lens_files(sp_data_1, chromosome_data_1, sp_data_2, chromosome_data_2, path_get, c)
        write_lens_files(result_1, result_2, sp_data_1, sp_data_2, path_get, c)

        if options_1 == "blastp":
            with zipfile.ZipFile(os.path.join(path_get, 'static', 'blastp_blk_ks_zip', f'{sp_data_1}_{sp_data_2}.blast.zip'), 'r') as zip_ref:
                zip_ref.extractall(target_folder)
            num_process = 1
            blast_suffix = 'blast'
            bed_path = target_folder
            blast_path = target_folder
            result_path = target_folder
            name_change = {sp_data_1: sp_dict[sp_data_1], sp_data_2: sp_dict[sp_data_2]}
            p = DotPlot(num_process, blast_suffix, bed_path, blast_path, result_path, name_change)
            p.main()

            png_file = os.path.join(f"../file_keep/{c}/{sp_data_1}_{sp_data_2}.png")
            return render(request, 'dotplot.html', {'image_url': png_file})

        # Aann_Aann.block.rr.txt.zip
        elif  options_1 == "block":
            with zipfile.ZipFile(os.path.join(path_get, 'static', 'blastp_blk_ks_zip', f'{sp_data_1}_{sp_data_2}.blast.zip'), 'r') as zip_ref:
                zip_ref.extractall(target_folder)
            with zipfile.ZipFile(os.path.join(path_get, 'static', 'blastp_blk_ks_zip', f'{sp_data_1}_{sp_data_2}.block.rr.txt.zip'), 'r') as zip_ref:
                zip_ref.extractall(target_folder)

            num_process = 1
            blast_suffix = 'blast'
            block_num = int(block_number)
            bed_path = target_folder
            block_blast_path = target_folder
            result_path = target_folder
            name_change = {sp_data_1: sp_dict[sp_data_1], sp_data_2: sp_dict[sp_data_2]}
            p = DotplotBlock(num_process, blast_suffix, block_num, bed_path, block_blast_path, result_path, name_change)
            p.main()

            png_file = os.path.join(f"../file_keep/{c}/{sp_data_1}_{sp_data_2}.{block_num}.2400.png")
            return render(request, 'dotplot.html', {'image_url': png_file})
        # Aann_Aann.ks.txt.zip
        elif options_1 == "ks":
            with zipfile.ZipFile(os.path.join(path_get, 'static', 'blastp_blk_ks_zip', f'{sp_data_1}_{sp_data_2}.blast.zip'), 'r') as zip_ref:
                zip_ref.extractall(target_folder)
            with zipfile.ZipFile(os.path.join(path_get, 'static', 'blastp_blk_ks_zip', f'{sp_data_1}_{sp_data_2}.block.rr.txt.zip'), 'r') as zip_ref:
                zip_ref.extractall(target_folder)
            with zipfile.ZipFile(os.path.join(path_get, 'static', 'blastp_blk_ks_zip', f'{sp_data_1}_{sp_data_2}.ks.txt.zip'), 'r') as zip_ref:
                zip_ref.extractall(target_folder)

            source_folder = os.path.join(path_get, 'file_keep', 'ks_dot_programe')
            # 复制文件夹中的所有文件到目标文件夹中
            for root, dirs, files in os.walk(source_folder):
                for file in files:
                    source_file = os.path.join(root, file)
                    target_file = os.path.join(target_folder, file)
                    shutil.copy2(source_file, target_file)

            from tools.command_safety import run_tool
            for script in ('rename.pl', '1.blastsort.pl', 'run_ks_dot.pl'):
                run_tool('perl', [script], cwd=target_folder)

            png_file = os.path.join(f"../file_keep/{c}/{sp_data_2}_{sp_data_1}.Ksdotplot.png")
            return render(request, 'dotplot.html', {'image_url': png_file})
    else:
        return render(request, 'dotplot.html')


# 第二个版本
# views.py - 性能优化版（不限制数量，不提示，完全显示）
from django.db import connection
from django.shortcuts import render
import numpy as np
from collections import defaultdict


def collinear_kaks_run(request):
    if request.method == 'POST':
        block = request.GET.get('block', None)
        if block:
            query_genome = block.split('_')[0]
            table_name = f"{query_genome}_blocksyn_pair"
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"SELECT * FROM {table_name} WHERE unique_id = %s",
                        [block]
                    )
                    results = cursor.fetchall()
            except Exception as e:
                return render(request, 'collinear_kaks_run_2.html', {
                    'error': f"Database error：{str(e)}",
                    'block_name': block
                })
            if not results:
                return render(request, 'collinear_kaks_run_2.html', {
                    'error': 'The relevant block information was not found。',
                    'block_name': block
                })
            return render(request, 'collinear_kaks_run_2.html', {
                'results': results,
                'block_name': block
            })

        # 处理表单提交
        query_genome = request.POST.get('query_genome')
        chromosome_data_1 = [int("".join(filter(str.isdigit, item))) for item in
                             request.POST.getlist("chromosome_data_1[]")]
        subject_genome = request.POST.get("subject_genome")
        chromosome_data_2 = [int("".join(filter(str.isdigit, item))) for item in
                             request.POST.getlist('chromosome_data_2[]')]

        if not query_genome or not chromosome_data_1 or not subject_genome or not chromosome_data_2:
            return render(request, 'collinear_kaks.html', {
                'error': 'Lack of necessary parameters。'
            })

        blocksyn_block_table = f"{query_genome}_blocksyn_block"
        blocksyn_pair_table = f"{query_genome}_blocksyn_pair"

        try:
            with connection.cursor() as cursor:
                conditions = ["Query_Genome = %s"]
                params = [query_genome]

                if isinstance(chromosome_data_1, (list, tuple)) and chromosome_data_1:
                    placeholders = ', '.join(['%s'] * len(chromosome_data_1))
                    conditions.append(f"Query_Chromosome IN ({placeholders})")
                    params.extend(chromosome_data_1)
                elif isinstance(chromosome_data_1, int):
                    conditions.append("Query_Chromosome = %s")
                    params.append(chromosome_data_1)
                else:
                    return render(request, 'collinear_kaks.html', {
                        'error': 'Invalid chromosomal parameters。'
                    })

                conditions.append("Reference_Genome = %s")
                params.append(subject_genome)

                if isinstance(chromosome_data_2, (list, tuple)) and chromosome_data_2:
                    placeholders = ', '.join(['%s'] * len(chromosome_data_2))
                    conditions.append(f"Reference_Chromosome IN ({placeholders})")
                    params.extend(chromosome_data_2)
                elif isinstance(chromosome_data_2, int):
                    conditions.append("Reference_Chromosome = %s")
                    params.append(chromosome_data_2)
                else:
                    return render(request, 'collinear_kaks.html', {
                        'error': 'Invalid chromosomal parameters。'
                    })

                # 查询block数据
                sql = f"SELECT * FROM {blocksyn_block_table} WHERE " + " AND ".join(conditions)
                cursor.execute(sql, params)
                collinear_block_pairs = cursor.fetchall()

                if not collinear_block_pairs:
                    return render(request, 'collinear_kaks_run.html', {
                        'error': 'Collinear blocks were not found。',
                        'sp_data_1': query_genome,
                        'sp_data_2': subject_genome
                    })

                unique_ids = [pair[1] for pair in collinear_block_pairs]
                
                # ========== 批量查询所有详情（核心优化） ==========
                collinear_block_details_dict = {}
                
                # 分批处理，每批500个ID，避免SQL语句过长
                batch_size = 500
                for i in range(0, len(unique_ids), batch_size):
                    batch_ids = unique_ids[i:i+batch_size]
                    placeholders = ', '.join(['%s'] * len(batch_ids))
                    
                    # 使用 IN 查询一次性获取多个unique_id的数据
                    batch_sql = f"SELECT * FROM {blocksyn_pair_table} WHERE unique_id IN ({placeholders})"
                    cursor.execute(batch_sql, batch_ids)
                    batch_details = cursor.fetchall()
                    
                    # 按照unique_id分组，保持与原代码完全相同的数据结构
                    for detail in batch_details:
                        uid = detail[1]  # unique_id 在第二列
                        if uid not in collinear_block_details_dict:
                            collinear_block_details_dict[uid] = []
                        # 完全保持原格式：[detail[2], detail[3], detail[4], detail[5], detail[6], detail[8], detail[9], detail[10]]
                        collinear_block_details_dict[uid].append([
                            detail[2], detail[3], detail[4], detail[5], detail[6],
                            detail[8], detail[9], detail[10]
                        ])

                # 处理数据，与原代码完全相同
                merged_dict = []
                for pair in unique_ids:
                    pairs_data = [item for item in collinear_block_pairs if item[1] == pair]
                    details_data = collinear_block_details_dict.get(pair, [])
                    ks_values = [float(item[6]) for item in details_data if 0 <= float(item[6]) <= 2]

                    if not ks_values:
                        continue

                    median_ks = np.round(np.median(ks_values), 4)
                    mean_ks = np.round(np.mean(ks_values), 4)
                    merged_dict.append((
                        [pairs_data[0], median_ks, mean_ks],
                        details_data
                    ))

                if not merged_dict:
                    return render(request, 'collinear_kaks_run.html', {
                        'error': 'There is no usable data after screening。',
                        'sp_data_1': query_genome,
                        'sp_data_2': subject_genome
                    })

        except Exception as e:
            return render(request, 'collinear_kaks.html', {
                'error': f"Database error：{str(e)}"
            })

        return render(request, 'collinear_kaks_run.html', {
            'merged_dict': merged_dict,
            'sp_data_1': query_genome,
            'sp_data_2': subject_genome,
            'success': True
        })

    return render(request, 'collinear_kaks.html')


# 共线性可视化
def genome_synteny_viewer(request, sp_data_1, sp_data_2):
    return render(request, 'synvisio_run_browse.html', {'sp_data_1': sp_data_1, 'sp_data_2': sp_data_2})


def inulin_gene(request):
    sp_data_1 = request.POST.get("sp_data_1", None)
    geneid = request.POST.get('geneid', None)
    query_sequence = request.POST.get('query_sequence')
    if sp_data_1 is None or geneid is None:
        return render(request, 'inulin_gene.html')
    if query_sequence:
        c = name_set()
        output_directory = f"{path_get}/file_keep/{c}"
        blast_results, geneids = _run_selected_species_blast(query_sequence, output_directory, sp_data_1)
    else:
        geneids = [item.strip() for item in geneid.replace('\r', '').split('\n') if item.strip()]

    if not geneids:
        return render(request, 'inulin_gene.html', {
            'not_found_geneids': [],
            'result': [],
            'blast_results': blast_results if query_sequence else None,
            'sp_data_1': sp_data_1,
        })

    geneid_placeholders = ','.join(['%s'] * len(geneids))
    sql_query = f"SELECT * FROM Inulin_GF_table WHERE gene_id IN ({geneid_placeholders})"
    with connection.cursor() as cursor:
        cursor.execute(sql_query, geneids)
        result = cursor.fetchall()
    found_geneids = [row[2] for row in result]
    # print(result)
    not_found_geneids = [geneid for geneid in geneids if geneid not in found_geneids]
    connection.close()
    return render(request, 'inulin_gene.html', {
        'not_found_geneids': not_found_geneids,
        'result': result,
        'blast_results': blast_results if query_sequence else None  # 如果没有查询序列，则不返回 blast_results})
    })

def rubber_gene(request):
    sp_data_1 = request.POST.get("sp_data_1", None)
    geneid = request.POST.get('geneid', None)
    query_sequence = request.POST.get('query_sequence')
    if sp_data_1 is None or geneid is None:
        return render(request, 'rubber_gene.html')
    if query_sequence:
        c = name_set()
        output_directory = f"{path_get}/file_keep/{c}"
        blast_results, geneids = _run_selected_species_blast(query_sequence, output_directory, sp_data_1)
    else:
        geneids = [item.strip() for item in geneid.replace('\r', '').split('\n') if item.strip()]

    if not geneids:
        return render(request, 'rubber_gene.html', {
            'not_found_geneids': [],
            'result': [],
            'blast_results': blast_results if query_sequence else None,
            'sp_data_1': sp_data_1,
        })

    geneid_placeholders = ','.join(['%s'] * len(geneids))
    sql_query = f"SELECT * FROM rubber_GF_table WHERE gene_id IN ({geneid_placeholders})"
    with connection.cursor() as cursor:
        cursor.execute(sql_query, geneids)
        result = cursor.fetchall()
    found_geneids = [row[2] for row in result]
    # print(result)
    not_found_geneids = [geneid for geneid in geneids if geneid not in found_geneids]
    connection.close()
    return render(request, 'rubber_gene.html', {
        'not_found_geneids': not_found_geneids,
        'result': result,
        'blast_results': blast_results if query_sequence else None  # 如果没有查询序列，则不返回 blast_results})
    })


def function_gene(request):
    """输入序列、基因id、序列名字进行搜索的方式"""
    sp_data_1 = request.POST.get("sp_data_1", None)
    geneid = request.POST.get('geneid', None)
    function = request.POST.get('function', None)
    query_sequence = request.POST.get('query_sequence')
    is_all_species = sp_data_1 == ALL_INTERPROSCAN_SPECIES_VALUE

    if sp_data_1 is None:
        return render(request, 'function_gene.html')

    found_geneids = []
    not_found_geneids = []
    result = []

    if query_sequence:
        c = name_set()
        output_directory = f"{path_get}/file_keep/{c}"
        blast_results, geneids = _run_selected_species_blast(query_sequence, output_directory, sp_data_1)

        for geneid in geneids:
            if geneid:
                if is_all_species:
                    sql_query = "SELECT * FROM function_GF_table WHERE gene_id = %s"
                    params = (geneid,)
                else:
                    sql_query = "SELECT * FROM function_GF_table WHERE gene_id = %s AND query_genome = %s"
                    params = (geneid, sp_data_1)
                with connection.cursor() as cursor:
                    cursor.execute(sql_query, params)
                    rows = cursor.fetchall()
                if rows:
                    result.extend(rows)
                    found_geneids.append(geneid)
                else:
                    not_found_geneids.append(geneid)
        connection.close()

        return render(request, 'function_gene.html', {
            'not_found_geneids': not_found_geneids,
            'result': result,
            'blast_results': blast_results if query_sequence else None,
            'sp_data_1': sp_data_1
        })

    else:
        # 处理基因ID或功能名称的搜索逻辑
        if geneid:
            geneids = [item.strip() for item in geneid.replace('\r', '').split('\n') if item.strip()]
            print(geneids)

            for geneid in geneids:
                if geneid:
                    if ";" in geneid:  # 如果是功能的英文描述
                        geneid = geneid.rstrip(';')  # 移除末尾的分号
                        if is_all_species:
                            sql_query = "SELECT * FROM function_GF_table WHERE function_name LIKE %s"
                            params = ("%" + geneid + "%",)
                        else:
                            sql_query = "SELECT * FROM function_GF_table WHERE function_name LIKE %s AND query_genome = %s"
                            params = ("%" + geneid + "%", sp_data_1)
                        with connection.cursor() as cursor:
                            cursor.execute(sql_query, params)
                            rows = cursor.fetchall()
                        if rows:
                            result.extend(rows)
                            found_geneids.append(geneid)
                        else:
                            not_found_geneids.append(geneid)
                    else:  # 如果是基因ID
                        print(geneid, sp_data_1)
                        if is_all_species:
                            sql_query = "SELECT * FROM function_GF_table WHERE gene_id = %s"
                            params = (geneid,)
                        else:
                            sql_query = "SELECT * FROM function_GF_table WHERE gene_id = %s AND query_genome = %s"
                            params = (geneid, sp_data_1)
                        with connection.cursor() as cursor:
                            cursor.execute(sql_query, params)
                            rows = cursor.fetchall()
                        if rows:
                            result.extend(rows)
                            found_geneids.append(geneid)
                        else:
                            not_found_geneids.append(geneid)
        elif function:  # 处理功能搜索
            function = function.rstrip(';') if function.endswith(';') else function
            print("Function search:", function)
            if is_all_species:
                sql_query = "SELECT * FROM function_GF_table WHERE function_name LIKE %s"
                params = ("%" + function + "%",)
            else:
                sql_query = "SELECT * FROM function_GF_table WHERE function_name LIKE %s AND query_genome = %s"
                params = ("%" + function + "%", sp_data_1)
            with connection.cursor() as cursor:
                cursor.execute(sql_query, params)
                rows = cursor.fetchall()
            if rows:
                result.extend(rows)
                found_geneids.append(function)
            else:
                not_found_geneids.append(function)

        connection.close()
        return render(request, 'function_gene.html', {
            'not_found_geneids': not_found_geneids,
            'result': result,
            'sp_data_1': sp_data_1
        })




def function_gene(request):
    """Search function gene families by sequence, gene ID, or function name."""
    sp_data_1 = (request.POST.get("sp_data_1") or '').strip()
    geneid = (request.POST.get('geneid') or '').strip()
    function = (request.POST.get('function') or '').strip()
    query_sequence = (request.POST.get('query_sequence') or '').strip()
    is_all_species = sp_data_1 == ALL_INTERPROSCAN_SPECIES_VALUE

    if not sp_data_1:
        return render(request, 'function_gene.html')

    if function == 'None;':
        function = ''

    if is_all_species and query_sequence:
        job_id = _create_function_gene_all_species_job(query_sequence)
        _start_function_gene_all_species_job(job_id)
        return render(request, 'function_gene.html', {
            'not_found_geneids': [],
            'result': [],
            'blast_results': None,
            'sp_data_1': sp_data_1,
            'selected_sp_data_1': sp_data_1,
            'function_gene_job_id': job_id,
            'submitted_query_sequence': query_sequence,
            'all_species_blast_target_limit': FUNCTION_GENE_ALL_SPECIES_BLAST_MAX_TARGETS,
        })

    found_geneids = []
    not_found_geneids = []
    result = []
    blast_results = None
    result_limit_reached = False

    def fetch_limited_rows(sql_query, params):
        nonlocal result_limit_reached
        remaining = FUNCTION_GENE_RESULT_LIMIT - len(result)
        if remaining <= 0:
            result_limit_reached = True
            return []
        with connection.cursor() as cursor:
            cursor.execute(f"{sql_query} LIMIT %s", tuple(params) + (remaining + 1,))
            rows = cursor.fetchall()
        if len(rows) > remaining:
            result_limit_reached = True
            rows = rows[:remaining]
        return rows

    def add_rows(label, rows):
        if rows:
            result.extend(rows)
            found_geneids.append(label)
        else:
            not_found_geneids.append(label)

    if query_sequence:
        c = name_set()
        output_directory = f"{path_get}/file_keep/{c}"
        blast_target_limit = FUNCTION_GENE_ALL_SPECIES_BLAST_MAX_TARGETS if is_all_species else PAGE_ALL_SPECIES_BLAST_MAX_TARGETS
        blast_results, geneids = _run_selected_species_blast(
            query_sequence,
            output_directory,
            sp_data_1,
            max_target_seqs=blast_target_limit,
        )
        for query_geneid in geneids:
            if result_limit_reached:
                break
            if not query_geneid:
                continue
            if is_all_species:
                sql_query = "SELECT * FROM function_GF_table WHERE gene_id = %s"
                params = (query_geneid,)
            else:
                sql_query = "SELECT * FROM function_GF_table WHERE gene_id = %s AND query_genome = %s"
                params = (query_geneid, sp_data_1)
            add_rows(query_geneid, fetch_limited_rows(sql_query, params))

    elif geneid:
        geneids = [item.strip() for item in geneid.replace('\r', '').split('\n') if item.strip()]
        for query_term in geneids:
            if result_limit_reached:
                break
            if not query_term:
                continue
            if ";" in query_term:
                function_term = query_term.rstrip(';')
                if is_all_species:
                    sql_query = "SELECT * FROM function_GF_table WHERE function_name LIKE %s"
                    params = (f"%{function_term}%",)
                else:
                    sql_query = "SELECT * FROM function_GF_table WHERE function_name LIKE %s AND query_genome = %s"
                    params = (f"%{function_term}%", sp_data_1)
                add_rows(function_term, fetch_limited_rows(sql_query, params))
            else:
                if is_all_species:
                    sql_query = "SELECT * FROM function_GF_table WHERE gene_id = %s"
                    params = (query_term,)
                else:
                    sql_query = "SELECT * FROM function_GF_table WHERE gene_id = %s AND query_genome = %s"
                    params = (query_term, sp_data_1)
                add_rows(query_term, fetch_limited_rows(sql_query, params))

    elif function:
        function_term = function.rstrip(';') if function.endswith(';') else function
        if is_all_species:
            sql_query = "SELECT * FROM function_GF_table WHERE function_name LIKE %s"
            params = (f"%{function_term}%",)
        else:
            sql_query = "SELECT * FROM function_GF_table WHERE function_name LIKE %s AND query_genome = %s"
            params = (f"%{function_term}%", sp_data_1)
        add_rows(function_term, fetch_limited_rows(sql_query, params))

    connection.close()
    return render(request, 'function_gene.html', {
        'not_found_geneids': not_found_geneids,
        'result': result,
        'blast_results': blast_results,
        'sp_data_1': sp_data_1,
        'result_limit': FUNCTION_GENE_RESULT_LIMIT,
        'result_limit_reached': result_limit_reached,
    })


def function_gene_job_status(request, job_id):
    if not _function_gene_job_is_valid(job_id):
        return JsonResponse({'status': 'error', 'message': 'Invalid function gene job id.'}, status=404)

    status = _read_function_gene_job_status(job_id)
    if status.get('status') == 'done':
        status['result_url'] = reverse('function_gene_job_result_url', args=[job_id])
        status['download_url'] = reverse('function_gene_job_download_url', args=[job_id])
        if os.path.isfile(_function_gene_job_blast_path(job_id)):
            status['blast_download_url'] = reverse('function_gene_job_blast_download_url', args=[job_id])
    return JsonResponse(status)


def function_gene_job_download(request, job_id):
    if not _function_gene_job_is_valid(job_id):
        return HttpResponse('Invalid function gene job id.', status=404)

    result_path = _function_gene_job_result_path(job_id)
    if not os.path.isfile(result_path):
        return HttpResponse('The function gene result file is not ready.', status=404)

    return FileResponse(
        open(result_path, 'rb'),
        as_attachment=True,
        filename=f'function_gene_all_species_{job_id}.tsv',
    )


def function_gene_job_blast_download(request, job_id):
    if not _function_gene_job_is_valid(job_id):
        return HttpResponse('Invalid function gene job id.', status=404)

    blast_path = _function_gene_job_blast_path(job_id)
    if not os.path.isfile(blast_path):
        return HttpResponse('The BLAST hit file is not ready.', status=404)

    return FileResponse(
        open(blast_path, 'rb'),
        as_attachment=True,
        filename=f'function_gene_all_species_blast_hits_{job_id}.tsv',
    )


def function_gene_job_result(request, job_id):
    if not _function_gene_job_is_valid(job_id):
        return HttpResponse('Invalid function gene job id.', status=404)

    status = _read_function_gene_job_status(job_id)
    result_path = _function_gene_job_result_path(job_id)
    rows = _read_function_gene_result_rows(result_path)

    return render(request, 'function_gene_job_result.html', {
        'job_id': job_id,
        'status': status,
        'result': rows,
        'result_count': len(rows),
        'result_headers': FUNCTION_GENE_RESULT_HEADERS,
        'result_file_ready': os.path.isfile(result_path),
        'download_url': reverse('function_gene_job_download_url', args=[job_id]) if os.path.isfile(result_path) else None,
        'blast_download_url': reverse('function_gene_job_blast_download_url', args=[job_id]) if os.path.isfile(_function_gene_job_blast_path(job_id)) else None,
    })


def draw_tree(request):
    import os
    import re
    import json
    import shutil
    import traceback
    import subprocess
    import sys

    if request.method == 'POST':
        try:
            # =========================
            # 1. 接收前端数据
            # =========================
            received_data = json.loads(request.body)

            # 前端现在直接传一维列表
            # ["Aann1g00001", "Aann1g00002"]
            selected_rows_raw = received_data.get('selectedRows', [])

            # ========== 关键修改：展平为一维列表 ==========
            selected_rows = []
            for item in selected_rows_raw:
                if isinstance(item, list):
                    selected_rows.extend(item)  # 如果是列表，展开
                else:
                    selected_rows.append(item)   # 如果是字符串，直接添加
            
            print("Selected rows (flattened):", selected_rows)

            min_ks = received_data.get('minKs')
            max_ks = received_data.get('maxKs')

            print(f"Received minKs: {min_ks}, maxKs: {max_ks}")

            if not selected_rows:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No genes selected'
                }, status=400)

            # =========================
            # 2. 获取物种名（修改这里）
            # =========================
            # 取第一个基因ID，提取物种名（通常是前4个字符）
            first_gene = selected_rows[0]
            # 提取开头的字母部分（如 Aann 或 Dapi）
            import re
            match = re.match(r'^([A-Za-z]+)', first_gene)
            if match:
                sp_name = match.group(1)
            else:
                sp_name = first_gene[:4]  # 备选方案
            
            print("Species:", sp_name)

            # =========================
            # 3. 创建工作目录
            # =========================
            c = name_set()

            work_dir = os.path.join(path_get, 'file_keep', c)

            os.makedirs(work_dir, exist_ok=True)

            print("Work dir:", work_dir)

            # =========================
            # 4. 复制脚本
            # =========================
            for script in ['draw_tree.py', 'draw_tree2.py']:
                source_script = os.path.join(
                    path_get,
                    'file_keep',
                    script
                )
                target_script = os.path.join(
                    work_dir,
                    script
                )
                shutil.copy(source_script, target_script)

            # =========================
            # 5. 找到pep文件
            # =========================
            pep_file = os.path.join(
                settings.BASE_DIR,
                'file_keep',
                'species_data',
                f"{sp_name}.pep"
            )

            print("PEP file:", pep_file)

            if not os.path.exists(pep_file):
                return JsonResponse({
                    'status': 'error',
                    'message': f'Protein file not found: {pep_file}'
                }, status=404)

            # =========================
            # 6. 提取目标序列
            # =========================
            all_pep_path = os.path.join(work_dir, 'all.pep')

            found_count = 0

            with open(pep_file, 'r') as infile, open(all_pep_path, 'w') as outfile:
                write_flag = False
                for line in infile:
                    if line.startswith('>'):
                        gene_id_in_file = line[1:].split()[0].strip()
                        write_flag = gene_id_in_file in selected_rows
                        if write_flag:
                            found_count += 1
                            outfile.write(line)
                    elif write_flag:
                        outfile.write(line)

            print("Found sequences:", found_count)

            if found_count == 0:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No matching sequences found in pep file'
                }, status=400)

            # =========================
            # 7. 运行系统发育树脚本（彻底修复版）
            # =========================
            python_path = '/usr/bin/python3.6'  # 或者 /usr/local/bin/python3.13

            result = subprocess.run(
                [python_path, 'draw_tree.py'],
                cwd=work_dir,
                capture_output=True,
                text=True,
            )

            # =========================
            # 8. 检查图片是否生成
            # =========================
            image_file = os.path.join(work_dir, 'result.png')

            if not os.path.exists(image_file):
                return JsonResponse({
                    'status': 'error',
                    'message': 'result.png not generated',
                    'stderr': result.stderr,
                    'stdout': result.stdout
                }, status=500)

            # =========================
            # 9. 拷贝图片到static
            # =========================
            static_folder = os.path.join(path_get, 'static')
            os.makedirs(static_folder, exist_ok=True)

            img_filename = f"result_{c}.png"
            target_path = os.path.join(static_folder, img_filename)
            shutil.copy(image_file, target_path)

            # =========================
            # 10. session保存路径
            # =========================
            request.session['tree_img_png'] = f"/static/{img_filename}"

            # =========================
            # 11. 返回成功
            # =========================
            return JsonResponse({
                'status': 'success',
                'image_url': f"/static/{img_filename}"
            })

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=400)



from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache

@never_cache
@csrf_exempt
def tree_img(request):
    """显示系统发育树图片 - 完全不使用模板和数据库"""
    
    img_path = request.session.get('tree_img_png', '')
    print(f"Session image path: {img_path}")
    
    # 直接返回 HTML 字符串，不经过任何模板引擎
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Phylogenetic Tree</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background: #f5f5f5;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #d35400;
            text-align: center;
            border-bottom: 2px solid #d35400;
            padding-bottom: 10px;
        }}
        .img-container {{
            text-align: center;
            margin: 20px 0;
        }}
        img {{
            max-width: 100%;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
        .btn {{
            display: inline-block;
            padding: 10px 20px;
            margin: 0 10px;
            background: #d35400;
            color: white;
            text-decoration: none;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }}
        .btn:hover {{
            background: #e67e22;
        }}
        .btn-gray {{
            background: #6c757d;
        }}
        .btn-gray:hover {{
            background: #5a6268;
        }}
        .error {{
            color: red;
            text-align: center;
            padding: 20px;
        }}
        .buttons {{
            text-align: center;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Phylogenetic Tree Result</h1>
        {content}
    </div>
</body>
</html>'''
    
    if img_path:
        content = f'''
        <div class="img-container">
            <img id="treeImg" src="{img_path}" alt="Phylogenetic Tree">
        </div>
        <div class="buttons">
            <button class="btn" onclick="downloadImage()">Download Image</button>
            <button class="btn btn-gray" onclick="goBack()">Back to Search</button>
        </div>
        <script>
            function downloadImage() {{
                var img = document.getElementById('treeImg');
                var link = document.createElement('a');
                link.href = img.src;
                link.download = 'phylogenetic_tree.png';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }}
            function goBack() {{
                window.location.href = '/browse/orthologous';
            }}
        </script>
        '''
    else:
        content = '''
        <div class="error">
            <p>No image available. Please build the phylogenetic tree first.</p>
        </div>
        <div class="buttons">
            <button class="btn btn-gray" onclick="goBack()">Back to Search</button>
        </div>
        <script>
            function goBack() {
                window.location.href = '/browse/orthologous';
            }
        </script>
        '''
    
    return HttpResponse(html.format(content=content))


def function_gene_v2(request, function_name=None):
    """第二种直接点击的方式"""
    found_geneids = []
    not_found_geneids = []
    result = []

    # 如果没有传入 function_name，渲染默认表格页面
    if not function_name:
        return render(request, 'function_gene_v2.html')

    # 否则执行查询逻辑
    geneid = function_name
    sql_query = "SELECT * FROM function_GF_table WHERE function_name LIKE %s"

    with connection.cursor() as cursor:
        cursor.execute(sql_query, ("%" + geneid + "%",))
        rows = cursor.fetchall()

    if rows:
        result.extend(rows)
        found_geneids.append(geneid)
    else:
        not_found_geneids.append(geneid)

    # 渲染结果页面
    connection.close()
    return render(request, 'function_gene_v2.html', {'not_found_geneids': not_found_geneids, 'result': result})


# 对 ks 值进行高斯函数进行拟合，然后绘图
def plot_ks_lists(list1, list2, list3):
    def plot_ks(data, label):
        # print(data)
        if len(data) < 2:
            # print(f"Not enough data points for {label}. At least 2 required.")
            return  # 不执行后续操作

        kde = gaussian_kde(data)
        x = np.linspace(min(data), max(data), 1000)
        y = kde(x)
        plt.plot(x, y, label=label)

    # Plot KS plots for each list
    plot_ks(list1, 'block median')
    plot_ks(list2, 'block average')
    plot_ks(list3, 'all pairs')
    # Plot settings
    plt.xlabel('Ks', fontstyle='italic')
    plt.ylabel('Frequency')
    plt.legend()

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    plt.close()
    plot_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return plot_data


def draw_ks_peak(request):
    if request.method == 'POST':
        received_data = json.loads(request.body)  # 解析发送过来的JSON数据
        selected_rows = received_data.get('selectedRows', [])  # 获取选中的行数据
        print("Received data:", selected_rows)  # 添加调试信息

        min_value, max_value = 0, 2  # 限制 0- 2 的范围内

        median_list = []
        average_list = []
        all_list = []

        for row in selected_rows:
            print(f"Processing row: {row}, length: {len(row)}")  # 调试每一行

            try:
                # 处理 median 数据
                if len(row) >= 1:
                    try:
                        median_val = float(row[0])
                        if min_value <= median_val <= max_value:
                            median_list.append(median_val)
                    except (ValueError, TypeError) as e:
                        print(f"Error converting median value '{row[0]}': {e}")

                # 处理 average 数据
                if len(row) >= 2:
                    try:
                        # 先检查是否是 'Undefined' 或类似字符串
                        if isinstance(row[1], str) and row[1].strip().lower() in ['undefined', 'nan', 'null', '']:
                            print(f"Skipping undefined average value in row: {row}")
                        else:
                            average_val = float(row[1])
                            if min_value <= average_val <= max_value:
                                average_list.append(average_val)
                    except (ValueError, TypeError) as e:
                        print(f"Error converting average value '{row[1]}': {e}")

                # 处理 all 数据 (从第3个元素开始)
                if len(row) >= 3:
                    for i in range(2, len(row)):
                        try:
                            all_val = float(row[i])
                            if min_value <= all_val <= max_value:
                                all_list.append(all_val)
                        except (ValueError, TypeError) as e:
                            print(f"Error converting all value '{row[i]}' at index {i}: {e}")

            except Exception as e:
                print(f"Unexpected error processing row {row}: {e}")
                continue

        plot_data = plot_ks_lists(median_list, average_list, all_list)
        request.session['plot_data'] = plot_data  # 将 plot_data 保存在会话中
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=400)

def ks_peak_img(request):
    plot_data = request.session.get('plot_data')  # 从会话中获取 plot_data
    if plot_data:
        return render(request, 'ks_peak_draw.html', {'plot_data': plot_data})
    else:
        return HttpResponse('Plot data not found in session.')


def ks_circos_deal_gff(input_file, output_file, selected_rows):
    with open(input_file, 'r') as f_in:
        with open(output_file, 'w') as f_out:
            for line in f_in:
                elements = line.strip().split('\t')
                if elements[1] in selected_rows:
                    f_out.write(line)
# def ks_circos_pair_deal(input_file, output_file, output_file2, selected_rows):
#     with open(input_file, 'r') as f_in, open(output_file, 'w') as f_out, open(output_file2, 'w') as f_out2:
#         for line in f_in:
#             elements = line.strip().split('\t')
#             if elements[0] in selected_rows and elements[1] in selected_rows:
#                 f_out.write(line)
#                 f_out2.write('\t'.join(elements[:2] + elements[3:]) + '\n')
def ks_circos_pair_deal(input_file, output_file, selected_rows):
    with open(input_file, 'r') as f_in, open(output_file, 'w') as f_out:
        for line in f_in:
            elements = line.strip().split('\t')
            if elements[0] in selected_rows and elements[1] in selected_rows:
                f_out.write(line)
                # f_out2.write('\t'.join(elements[:2] + elements[3:]) + '\n')


def ks_circos_class_deal(selected_rows, output_file):
    with open(output_file, 'w') as f_out:
        for line in selected_rows:
            f_out.write(f"{line}\t1\n")
def write_to_conf_file(c, sp_name, min_ks, max_ks):
    str_infor = f"""
[excircle]
savefig = genefam.png
specieslist = {sp_name}
lens_file = {sp_name}.lens
gff_file = {sp_name}.new.gff
ks_file = {sp_name}_{sp_name}.ks2.txt
pair_file = {sp_name}.pair
classifyfile = {sp_name}.class

classify_color = 1:#CC99FF,2:orange,3:#FF1493,4:red,5:blue,6:c,7:black
young_genes_ks=#
young_genes_color=#
axes_limit = 0.9
alpha = 0.9
line_color = #dcdcdd
label_pos = 0.85
dpi=300
max_ks = {max_ks}
min_ks = {min_ks}
"""
    with open(f"{path_get}/file_keep/{c}/excircle.conf", 'w') as f:
        f.write(str_infor)


def copy_image_to_static(image_path):
    static_folder = os.path.join(path_get, 'static')
    target_path = os.path.join(static_folder, 'genefam.png')
    shutil.copy(image_path, target_path)


def draw_ks_circos(request):
    if request.method == 'POST':
        received_data = json.loads(request.body)  # 解析发送过来的JSON数据

        selected_rows = [item for sublist in received_data.get('selectedRows', []) for item in sublist]
        min_ks = received_data.get('minKs')
        max_ks = received_data.get('maxKs')
        events = received_data.get('events')
        print(f"Received minKs: {min_ks}, maxKs: {max_ks}, event {events}")
        # print(received_data)

        selected_rows = [item for sublist in received_data.get('selectedRows', []) for item in sublist]
        sp_name = re.match(r'[a-zA-Z]+', selected_rows[0]).group()
        print(selected_rows, sp_name)
        c = name_set()
        # 复制文件
        shutil.copy(f"{path_get}/file_keep/run.py", f'{path_get}/file_keep/{c}')
        shutil.copytree(f"{path_get}/file_keep/famcicle", f"{path_get}/file_keep/{c}/famcicle")
        files_to_copy = glob.glob(f'{path_get}/file_keep/ks_circos_files/{sp_name}*')
        for file in files_to_copy:
            shutil.copy(file, f'{path_get}/file_keep/{c}')

        files_to_copy_2 = glob.glob(f'{path_get}/file_keep/ks_circos_files/{events}/{sp_name}*')
        for file in files_to_copy_2:
            # shutil.copy(file, f'{path_get}/file_keep/{c}')
            new_file_path = os.path.join(f'{path_get}/file_keep/{c}', f"{sp_name}.pair")
            shutil.copy(file, new_file_path)

            df = pd.read_csv(new_file_path, header=None, sep='\t')
            if df.shape[1] > 2:  # 检查是否存在至少3列
                df.drop(df.columns[2], axis=1, inplace=True)
            df.to_csv(new_file_path, index=False, header=False, sep='\t')


        ks_circos_deal_gff(f'{path_get}/file_keep/{c}/{sp_name}.new.gff', f'{path_get}/file_keep/{c}/{sp_name}.new2.gff', selected_rows)
        # ks_circos_pair_deal(f'{path_get}/file_keep/{c}/{sp_name}_{sp_name}.ks.txt', f'{path_get}/file_keep/{c}/{sp_name}_{sp_name}.ks2.txt', f'{path_get}/file_keep/{c}/{sp_name}.pair', selected_rows)
        ks_circos_pair_deal(f'{path_get}/file_keep/{c}/{sp_name}_{sp_name}.ks.txt', f'{path_get}/file_keep/{c}/{sp_name}_{sp_name}.ks2.txt', selected_rows)
        # f'{path_get}/file_keep/{c}/{sp_name}.pair',



        ks_circos_class_deal(selected_rows, f'{path_get}/file_keep/{c}/{sp_name}.class')
        write_to_conf_file(c, sp_name, min_ks, max_ks)

        # 本地运行
        subprocess.run("python run.py excircle -c excircle.conf", shell=True, cwd=f"{path_get}/file_keep/{c}")

        # command = f"cd {path_get}/file_keep/{c} && python3 run.py excircle -c excircle.conf"
        # os.system(command)

        # subprocess.run("python run.py excircle -c excircle.conf", shell=True, cwd=f"{path_get}/file_keep/{c}")
        sp_name_genefam_png_path = f"{path_get}/file_keep/{c}/genefam.png"
        static_folder = os.path.join(path_get, 'static')
        target_path = os.path.join(static_folder, 'genefam.png')
        shutil.copy(sp_name_genefam_png_path, target_path)
        request.session['plot_data_2'] = "hh"  # 将 plot_data 保存在会话中
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=400)


def ks_circos_img(request):
    plot_data_2 = request.session.get('plot_data_2')  # 从会话中获取 plot_data
    if plot_data_2:
        return render(request, 'ks_circos_draw.html', {'plot_data_2': plot_data_2})
    else:
        return HttpResponse('Plot data not found in session.')


def get_diamond_binary():
    configured = getattr(settings, 'DIAMOND_BIN', None)
    candidates = [configured, '/www/tools/soft_tools/diamond', 'diamond']
    for candidate in candidates:
        if candidate and (candidate == 'diamond' or os.path.exists(candidate)):
            return candidate
    return 'diamond'


def get_ancestral_db_prefix(species_data):
    return os.path.join(path_get, 'file_keep', 'Ancestral_chromosome', f'{species_data}.nr')


def get_ancestral_nucl_db_prefix(species_data):
    return os.path.join(path_get, 'static', 'ancestral_data', species_data, species_data)


def _blast_outfmt_with_title():
    return '6 qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore stitle'


def run_diamond(query_file, nucl_or_prot, species_data, evalue, output_file):
    db_prefix = get_ancestral_db_prefix(species_data)
    if not os.path.exists(db_prefix) and not os.path.exists(f'{db_prefix}.dmnd'):
        raise FileNotFoundError(
            f'Missing DIAMOND database for {species_data}: {db_prefix}.dmnd'
        )

    cmd = [
        get_diamond_binary(),
        'blastp',
        '-d', db_prefix,
        '-q', query_file,
        '-e', str(evalue),
        '-f', '6',
        '-p', '4',
        '-o', output_file,
        '-k', '50',
    ]
    try:
        subprocess.run(
            cmd,
            cwd=os.path.dirname(query_file),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr or exc.stdout or str(exc)
        raise RuntimeError(f'DIAMOND failed: {detail}') from exc

    if not os.path.exists(output_file):
        raise FileNotFoundError(f'DIAMOND did not create output file: {output_file}')


def _ncbi_blast_binary(program):
    configured_dir = getattr(settings, 'NCBI_BLAST_BIN_DIR', None)
    candidates = []
    if configured_dir:
        candidates.append(os.path.join(configured_dir, program))
    candidates.extend([
        os.path.join('/wangjp/yuzijian/tools/ncbi-blast-2.15.0+/bin', program),
        program,
    ])
    for candidate in candidates:
        if not candidate:
            continue
        if candidate == program or os.path.exists(candidate):
            return candidate
    return program


def _append_ancestral_blast_log(output_directory, title, cmd, completed):
    log_path = os.path.join(output_directory, 'ancestral_blast_command.log')
    try:
        with open(log_path, 'a', encoding='utf-8') as log_file:
            log_file.write(f'\n===== {title} =====\n')
            if isinstance(cmd, (list, tuple)):
                log_file.write(' '.join(str(part) for part in cmd))
            else:
                log_file.write(str(cmd))
            log_file.write(f'\nreturncode: {completed.returncode}\n')
            if completed.stdout:
                log_file.write('stdout:\n')
                log_file.write(completed.stdout)
            if completed.stderr:
                log_file.write('stderr:\n')
                log_file.write(completed.stderr)
    except Exception:
        pass


def run_ncbi_blast(query_file, sequence_type, evalue, output_file, db_value=None, db_paths=None,
                   alias_name='blastdb_alias', max_target_seqs=50):
    sequence_type = SEQUENCE_TYPE_NUCLEOTIDE if sequence_type == SEQUENCE_TYPE_NUCLEOTIDE else SEQUENCE_TYPE_PROTEIN
    blast_program = 'blastn' if sequence_type == SEQUENCE_TYPE_NUCLEOTIDE else 'blastp'
    db_type = 'nucl' if sequence_type == SEQUENCE_TYPE_NUCLEOTIDE else 'prot'
    output_directory = os.path.dirname(query_file)

    if db_paths is not None:
        if not db_paths:
            raise FileNotFoundError('No BLAST databases were found for the selected sequence type.')
        db_alias = os.path.join(output_directory, alias_name)
        db_list = ' '.join(db_paths)
        alias_cmd = [
            _ncbi_blast_binary('blastdb_aliastool'),
            '-dblist', db_list,
            '-dbtype', db_type,
            '-out', db_alias,
            '-title', alias_name,
        ]
        alias_completed = subprocess.run(
            alias_cmd,
            cwd=output_directory,
            capture_output=True,
            text=True,
        )
        _append_ancestral_blast_log(output_directory, 'Create BLAST alias database', alias_cmd, alias_completed)
        if alias_completed.returncode != 0:
            detail = alias_completed.stderr or alias_completed.stdout or 'Failed to create BLAST alias database.'
            raise RuntimeError(detail)
        db_value = db_alias
    elif not db_value:
        raise ValueError('A BLAST database path or database list is required.')

    if db_paths is None and not _blast_db_exists(db_value, sequence_type):
        raise FileNotFoundError(f'Missing BLAST database: {db_value}')

    blast_cmd = [
        _ncbi_blast_binary(blast_program),
        '-query', query_file,
        '-db', db_value,
        '-outfmt', _blast_outfmt_with_title(),
        '-evalue', str(evalue),
        '-out', output_file,
        '-num_threads', '8',
        '-max_target_seqs', str(int(max_target_seqs)),
    ]
    completed = subprocess.run(
        blast_cmd,
        cwd=output_directory,
        capture_output=True,
        text=True,
    )
    _append_ancestral_blast_log(output_directory, f'Run {blast_program.upper()}', blast_cmd, completed)

    if completed.returncode != 0:
        detail = completed.stderr or completed.stdout or f'{blast_program} failed.'
        raise RuntimeError(detail)
    if not os.path.exists(output_file):
        raise FileNotFoundError(f'{blast_program} did not create output file: {output_file}')


def _read_fasta_sequence_letters(fasta_file):
    letters = []
    with open(fasta_file, 'r', encoding='utf-8', errors='replace') as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith('>'):
                continue
            letters.extend(re.findall(r'[A-Za-z]', line.upper()))
    return ''.join(letters)


def _validate_sequence_type_for_search(fasta_file, sequence_type):
    if sequence_type != SEQUENCE_TYPE_NUCLEOTIDE:
        return
    sequence = _read_fasta_sequence_letters(fasta_file)
    if not sequence:
        raise ValueError('No sequence letters were found in the submitted query.')
    allowed = set('ACGTUNRYSWKMBDHV')
    invalid_count = sum(1 for char in sequence if char not in allowed)
    if invalid_count / max(len(sequence), 1) > 0.02:
        raise ValueError(
            'The selected nucleotide search requires DNA/RNA sequences. '
            'Please choose Protein sequence (BLASTP) for amino acid sequences.'
        )


def _gene_id_prefix_pattern():
    prefixes = sorted(set(INTERPROSCAN_SPECIES) | set(ANCESTRAL_DATASETS) | {'CAAK'}, key=len, reverse=True)
    return r'(?:' + '|'.join(re.escape(prefix) for prefix in prefixes) + r')[A-Za-z0-9]*g\d+(?:\.\d+)?'


def _normalize_gene_id_for_lookup(gene_id):
    gene_id = str(gene_id or '').strip()
    gene_id = gene_id.lstrip('>')
    gene_id = gene_id.split()[0] if gene_id else ''
    gene_id = gene_id.strip('|,;')
    gene_id = re.sub(r'\.\d+$', '', gene_id)
    return gene_id


def _extract_gene_id_from_text(*values):
    pattern = re.compile(_gene_id_prefix_pattern(), re.IGNORECASE)
    for value in values:
        value = str(value or '').strip()
        if not value:
            continue
        match = pattern.search(value)
        if match:
            return _normalize_gene_id_for_lookup(match.group(0))
    fallback = str(values[0] if values else '').strip()
    return _normalize_gene_id_for_lookup(fallback) if fallback else ''


def _gene_lookup_candidates(gene_id):
    candidates = []
    gene_id = _normalize_gene_id_for_lookup(gene_id)
    if gene_id:
        candidates.append(gene_id)
        candidates.append(re.sub(r'[._-]t\d+$', '', gene_id, flags=re.IGNORECASE))
        candidates.append(re.sub(r'[._-]p\d+$', '', gene_id, flags=re.IGNORECASE))
    seen = set()
    ordered = []
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            ordered.append(candidate)
    return ordered


def _subject_gene_id_from_blast_fields(fields):
    stitle = ''
    if len(fields) > 13:
        stitle = fields[12]
    elif len(fields) == 13 and _normalize_ancestor_code(fields[12]) not in ANCESTRAL_DATASETS:
        stitle = fields[12]
    return _extract_gene_id_from_text(stitle, fields[1]) or fields[1]


def _ancestor_code_from_gene_id(gene_id):
    gene_id = _normalize_gene_id_for_lookup(gene_id).upper()
    for code in sorted(ANCESTRAL_DATASETS, key=len, reverse=True):
        if gene_id.startswith(code):
            return code
    if re.match(r'^CAAK\d+G\d+', gene_id):
        return 'CAAKI'
    return None


def _ancestor_sort_key(code):
    try:
        return list(ANCESTRAL_DISPLAY_LABELS.keys()).index(code)
    except ValueError:
        return 999


def _extract_ancestor_genes_from_row(row_values):
    grouped = {}
    for value in row_values:
        value = str(value or '').strip()
        if not value or value == '.':
            continue
        gene_id = _extract_gene_id_from_text(value)
        code = _ancestor_code_from_gene_id(gene_id)
        if not code:
            continue
        grouped.setdefault(code, [])
        if gene_id not in grouped[code]:
            grouped[code].append(gene_id)
    return grouped


def _format_ancestor_gene_summary(grouped):
    if not grouped:
        return ''
    parts = []
    for code in sorted(grouped, key=_ancestor_sort_key):
        parts.append(f"{_ancestor_label(code)}: {', '.join(grouped[code])}")
    return '; '.join(parts)


def _combined_trace_table_dir():
    return os.path.join(path_get, 'static', 'ancestral_combined')


def _combined_trace_table_paths():
    base_dir = _combined_trace_table_dir()
    return {
        source_name: os.path.join(base_dir, filename)
        for source_name, filename in COMBINED_TRACE_TABLES.items()
    }


def _combined_trace_signature(paths):
    signature = []
    for source_name, table_path in sorted(paths.items()):
        if os.path.isfile(table_path):
            stat = os.stat(table_path)
            signature.append((source_name, table_path, stat.st_mtime, stat.st_size))
        else:
            signature.append((source_name, table_path, None, None))
    return tuple(signature)


def _counted_majority(counts):
    if not counts:
        return ''
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _increment_count(counts, key):
    if not key:
        return
    counts[key] = counts.get(key, 0) + 1


def _classify_combined_trace_columns(rows):
    max_columns = max((len(row) for row in rows), default=0)
    columns = []
    species_totals = {}
    ancestor_totals = {}

    for column_index in range(max_columns):
        species_counts = {}
        ancestor_counts = {}
        non_empty_count = 0

        for row_values in rows:
            raw_value = row_values[column_index] if column_index < len(row_values) else ''
            raw_value = str(raw_value or '').strip()
            if not raw_value or raw_value == '.':
                continue
            gene_id = _extract_gene_id_from_text(raw_value)
            if not gene_id or gene_id == '.':
                continue
            non_empty_count += 1

            ancestor_code = _ancestor_code_from_gene_id(gene_id)
            if ancestor_code:
                _increment_count(ancestor_counts, ancestor_code)
                continue

            species_code = _resolve_gene_species(gene_id)
            if species_code:
                _increment_count(species_counts, species_code)

        ancestor_total = sum(ancestor_counts.values())
        species_total = sum(species_counts.values())
        if ancestor_total and ancestor_total >= species_total:
            ancestor_code = _counted_majority(ancestor_counts)
            _increment_count(ancestor_totals, ancestor_code)
            columns.append({
                'index': column_index,
                'role': 'ancestor',
                'ancestor_code': ancestor_code,
                'species': '',
                'label': _ancestor_label(ancestor_code),
                'non_empty_count': non_empty_count,
            })
        elif species_total:
            species_code = _counted_majority(species_counts)
            _increment_count(species_totals, species_code)
            columns.append({
                'index': column_index,
                'role': 'species',
                'ancestor_code': '',
                'species': species_code,
                'label': species_code,
                'non_empty_count': non_empty_count,
            })
        else:
            columns.append({
                'index': column_index,
                'role': 'empty',
                'ancestor_code': '',
                'species': '',
                'label': f'Column {column_index + 1}',
                'non_empty_count': non_empty_count,
            })

    seen_species = {}
    for column in columns:
        if column.get('role') != 'species':
            continue
        species_code = column.get('species') or 'Species'
        seen_species[species_code] = seen_species.get(species_code, 0) + 1
        column['copy_index'] = seen_species[species_code]
        if species_totals.get(species_code, 0) > 1:
            column['label'] = f"{species_code}-{column['copy_index']}"

    seen_ancestors = {}
    for column in columns:
        if column.get('role') != 'ancestor':
            continue
        ancestor_code = column.get('ancestor_code') or 'Ancestor'
        seen_ancestors[ancestor_code] = seen_ancestors.get(ancestor_code, 0) + 1
        column['copy_index'] = seen_ancestors[ancestor_code]
        if ancestor_totals.get(ancestor_code, 0) > 1:
            column['label'] = f"{_ancestor_label(ancestor_code)}-{column['copy_index']}"

    return columns


def _load_combined_trace_index():
    paths = _combined_trace_table_paths()
    signature = _combined_trace_signature(paths)
    if _COMBINED_TRACE_INDEX_CACHE['signature'] == signature and _COMBINED_TRACE_INDEX_CACHE['index'] is not None:
        return _COMBINED_TRACE_INDEX_CACHE['index'], paths

    index = {}
    tables = {}
    for source_name, table_path in paths.items():
        if not os.path.isfile(table_path):
            continue
        table_rows = []
        with open(table_path, 'r', encoding='utf-8', errors='replace') as handle:
            for line in handle:
                row_values = [value.strip() for value in line.rstrip('\n').split('\t')]
                table_rows.append(row_values)

        columns = _classify_combined_trace_columns(table_rows)
        tables[source_name] = {
            'source': source_name,
            'path': table_path,
            'rows': table_rows,
            'columns': columns,
            'ancestor_column_indices': [
                column['index'] for column in columns if column.get('role') == 'ancestor'
            ],
            'species_column_indices': [
                column['index'] for column in columns if column.get('role') == 'species'
            ],
        }

        for row_index, row_values in enumerate(table_rows, start=1):
            non_empty_genes = []
            for value in row_values:
                if not value or value == '.':
                    continue
                gene_id = _extract_gene_id_from_text(value)
                if gene_id:
                    non_empty_genes.append(gene_id)
            if not non_empty_genes:
                continue
            ancestor_genes = _extract_ancestor_genes_from_row(non_empty_genes)
            row_summary = {
                'source': source_name,
                'row_index': row_index,
                'ancestor_genes': ancestor_genes,
                'ancestor_gene_summary': _format_ancestor_gene_summary(ancestor_genes),
                'all_genes': non_empty_genes,
                'row_values': row_values,
            }
            for gene_id in non_empty_genes:
                for candidate in _gene_lookup_candidates(gene_id):
                    index.setdefault(candidate, []).append(row_summary)
    _COMBINED_TRACE_INDEX_CACHE['signature'] = signature
    _COMBINED_TRACE_INDEX_CACHE['index'] = index
    _COMBINED_TRACE_INDEX_CACHE['tables'] = tables
    return index, paths


def _load_combined_trace_tables():
    _load_combined_trace_index()
    return _COMBINED_TRACE_INDEX_CACHE.get('tables') or {}, _combined_trace_table_paths()


def _blast_row_to_dict(fields):
    return {
        'query_id': fields[0],
        'subject_id': _subject_gene_id_from_blast_fields(fields),
        'identity': float(fields[2]),
        'length': int(fields[3]),
        'mismatch': int(fields[4]),
        'gapopen': int(fields[5]),
        'qstart': int(fields[6]),
        'qend': int(fields[7]),
        'sstart': int(fields[8]),
        'send': int(fields[9]),
        'evalue': float(fields[10]),
        'bitscore': float(fields[11]),
    }


def _best_hit_sort_key(hit):
    return (hit['bitscore'], -hit['evalue'], hit['identity'], hit['length'])


def _select_best_hits(blast_result_file, max_evalue=None, min_score=None, min_identity=None):
    best_hits = {}
    total_hits = 0
    kept_hits = 0
    if not os.path.isfile(blast_result_file):
        return best_hits, total_hits, kept_hits
    with open(blast_result_file, 'r', encoding='utf-8', errors='replace') as handle:
        for line in handle:
            fields = line.rstrip('\n').split('\t')
            if len(fields) < 12:
                continue
            total_hits += 1
            try:
                if not _blast_row_passes_filters(fields, max_evalue=max_evalue, min_score=min_score, min_identity=min_identity):
                    continue
                hit = _blast_row_to_dict(fields)
            except (ValueError, TypeError):
                continue
            kept_hits += 1
            current = best_hits.get(hit['query_id'])
            if current is None or _best_hit_sort_key(hit) > _best_hit_sort_key(current):
                best_hits[hit['query_id']] = hit
    return best_hits, total_hits, kept_hits


def _trace_best_hits_to_ancestors(best_hits):
    index, paths = _load_combined_trace_index()
    available_sources = [source for source, table_path in paths.items() if os.path.isfile(table_path)]
    if not available_sources:
        raise FileNotFoundError('Ancestral tracing reference data are not available. Please contact the AGRP team.')
    rows = []
    traced_queries = set()

    for query_id, hit in best_hits.items():
        subject_gene = hit['subject_id']
        matched_rows = []
        seen_row_keys = set()
        for candidate in _gene_lookup_candidates(subject_gene):
            for row_summary in index.get(candidate, []):
                row_key = (row_summary['source'], row_summary['row_index'])
                if row_key in seen_row_keys:
                    continue
                seen_row_keys.add(row_key)
                matched_rows.append(row_summary)

        matched_species = _resolve_gene_species(subject_gene) or 'Unknown'
        if not matched_rows:
            rows.append({
                'query_id': query_id,
                'best_gene': subject_gene,
                'matched_species': matched_species,
                'reference_set': '-',
                'ancestor_gene_summary': 'No ancestral chromosome relationship is currently available for this gene.',
                'ancestor_gene_map': {},
                'ancestor_codes': [],
                'identity': f"{hit['identity']:.2f}",
                'length': hit['length'],
                'evalue': f"{hit['evalue']:.2e}",
                'bitscore': f"{hit['bitscore']:.2f}",
                'status': 'No ancestral relationship',
            })
            continue

        for row_summary in matched_rows:
            ancestor_codes = sorted(row_summary['ancestor_genes'].keys(), key=_ancestor_sort_key)
            if ancestor_codes:
                traced_queries.add(query_id)
            rows.append({
                'query_id': query_id,
                'best_gene': subject_gene,
                'matched_species': matched_species,
                'reference_set': row_summary['source'],
                'combined_source': row_summary['source'],
                'combined_row_index': row_summary['row_index'],
                'ancestor_gene_summary': row_summary['ancestor_gene_summary'] or 'No ancestral chromosome relationship is currently available for this gene.',
                'ancestor_gene_map': row_summary.get('ancestor_genes') or {},
                'ancestor_codes': ancestor_codes,
                'identity': f"{hit['identity']:.2f}",
                'length': hit['length'],
                'evalue': f"{hit['evalue']:.2e}",
                'bitscore': f"{hit['bitscore']:.2f}",
                'status': 'Traced' if ancestor_codes else 'No ancestral relationship',
            })
    return rows, traced_queries, available_sources


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _ancestor_genes_for_trace_row(row, code):
    gene_map = row.get('ancestor_gene_map') or row.get('ancestor_genes') or {}
    candidates = [code, _ancestor_label(code), _normalize_ancestor_code(code)]
    genes = []
    for key in candidates:
        value = gene_map.get(key) if isinstance(gene_map, dict) else None
        if isinstance(value, (list, tuple)):
            genes.extend(str(item).strip() for item in value if str(item).strip())
        elif value:
            genes.extend(part.strip() for part in str(value).split(',') if part.strip())
    deduped_genes = []
    seen_genes = set()
    for gene in genes:
        if gene and gene not in seen_genes:
            seen_genes.add(gene)
            deduped_genes.append(gene)
    return deduped_genes


def build_ancestral_trace_payload(trace_results, metadata):
    summaries = {}
    selected_codes = []
    for row in trace_results or []:
        for code in row.get('ancestor_codes') or []:
            code = _normalize_ancestor_code(code)
            if code not in ANCESTRAL_DATASETS:
                continue
            if code not in selected_codes:
                selected_codes.append(code)
            summary = summaries.setdefault(code, {
                'code': code,
                'label': _ancestor_label(code),
                'selected': True,
                'hit_count': 0,
                'top_hits': [],
            })
            ancestor_genes = _ancestor_genes_for_trace_row(row, code)
            ancestor_gene_text = ', '.join(ancestor_genes) if ancestor_genes else (row.get('ancestor_gene_summary') or row.get('best_gene') or '')
            bit_score = row.get('bitscore')
            evalue = row.get('evalue')
            hit = {
                'query': row.get('query_id'),
                'subject': ancestor_gene_text,
                'ancestor_gene': ancestor_gene_text,
                'best_extant_gene': row.get('best_gene'),
                'matched_species': row.get('matched_species'),
                'reference_set': row.get('reference_set'),
                'identity': row.get('identity'),
                'length': row.get('length'),
                'qstart': '',
                'qend': '',
                'sstart': '',
                'send': '',
                'evalue': evalue,
                'bit_score': bit_score,
                'trace_mode': True,
                '_score_value': _safe_float(bit_score, 0.0),
                '_evalue_value': _safe_float(evalue, float('inf')),
            }
            summary['hit_count'] += 1
            summary['top_hits'].append(hit)

    for summary in summaries.values():
        summary['top_hits'].sort(key=lambda hit: (-hit.get('_score_value', 0.0), hit.get('_evalue_value', float('inf'))))
        summary['top_hits'] = [
            {
                key: value
                for key, value in hit.items()
                if key not in ('_score_value', '_evalue_value')
            }
            for hit in summary['top_hits'][:5]
        ]
        summary['best_hit'] = summary['top_hits'][0] if summary['top_hits'] else None

    return {
        'selected_ancestors': selected_codes,
        'summaries': summaries,
        'meta': metadata or {},
    }



_ANCESTRAL_GFF_CACHE = {
    'signature': {},
    'records': {},
}


def _ancestral_gff_path(code):
    code = _normalize_ancestor_code(code)
    candidates = [
        os.path.join(path_get, 'static', 'ancestral_data', code, f'{code}.new.gff'),
        os.path.join(str(settings.BASE_DIR), 'static', 'ancestral_data', code, f'{code}.new.gff'),
        os.path.join(path_get, 'static', 'ancestral_data', code, f'{code}.gff'),
        os.path.join(str(settings.BASE_DIR), 'static', 'ancestral_data', code, f'{code}.gff'),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return candidates[0]


def _parse_gff_float(value, default=0.0):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def _parse_gff_int(value, default=0):
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def _extract_gene_id_from_gff_attributes(attributes):
    attributes = str(attributes or '').strip()
    if not attributes:
        return ''
    for key in ('ID', 'Name', 'gene_id', 'transcript_id'):
        match = re.search(r'(?:^|[;\s])' + re.escape(key) + r'=([^;\s]+)', attributes)
        if match:
            return match.group(1).strip()
    match = re.search(r'gene_id\s+"([^"]+)"', attributes)
    if match:
        return match.group(1).strip()
    match = re.search(r'[A-Za-z][A-Za-z0-9_.:-]{1,120}', attributes)
    return match.group(0).strip() if match else ''


def _parse_ancestral_gff_row(fields, row_index):
    fields = [str(item).strip() for item in fields]
    if not fields or not fields[0] or fields[0].startswith('#'):
        return None

    # AGRP *.new.gff files used by the genome page are usually:
    # chromosome, start, end, strand, old_gene, new_gene, order/position.
    if len(fields) >= 6 and re.fullmatch(r'[+-]', fields[3] if len(fields) > 3 else ''):
        gene_id = fields[5]
        if gene_id and gene_id != '.':
            return {
                'gene': gene_id,
                'chromosome': fields[0],
                'start': _parse_gff_int(fields[1], row_index),
                'end': _parse_gff_int(fields[2], row_index),
                'strand': fields[3],
                'order': _parse_gff_float(fields[6], row_index) if len(fields) > 6 else row_index,
            }

    # Standard GFF/GFF3 fallback.
    if len(fields) >= 9:
        gene_id = _extract_gene_id_from_gff_attributes(fields[8])
        if gene_id:
            return {
                'gene': gene_id,
                'chromosome': fields[0],
                'start': _parse_gff_int(fields[3], row_index),
                'end': _parse_gff_int(fields[4], row_index),
                'strand': fields[6] if fields[6] in ('+', '-') else '+',
                'order': _parse_gff_float(fields[3], row_index),
            }

    # Loose fallback for small custom tables.
    gene_id = ''
    for value in reversed(fields):
        if value and value != '.' and re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{1,120}', value):
            gene_id = value
            break
    if not gene_id:
        return None
    return {
        'gene': gene_id,
        'chromosome': fields[0],
        'start': _parse_gff_int(fields[1], row_index) if len(fields) > 1 else row_index,
        'end': _parse_gff_int(fields[2], row_index) if len(fields) > 2 else row_index,
        'strand': fields[3] if len(fields) > 3 and fields[3] in ('+', '-') else '+',
        'order': row_index,
    }


def _load_ancestral_gff_records(code):
    code = _normalize_ancestor_code(code)
    gff_path = _ancestral_gff_path(code)
    if not os.path.isfile(gff_path):
        return [], gff_path

    stat = os.stat(gff_path)
    signature = (gff_path, stat.st_mtime, stat.st_size)
    if _ANCESTRAL_GFF_CACHE['signature'].get(code) == signature:
        return _ANCESTRAL_GFF_CACHE['records'].get(code, []), gff_path

    records = []
    with open(gff_path, 'r', encoding='utf-8', errors='replace') as handle:
        for row_index, line in enumerate(handle, start=1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            row = _parse_ancestral_gff_row(line.split('\t'), row_index)
            if row and row.get('gene'):
                records.append(row)

    records.sort(key=lambda item: (str(item.get('chromosome', '')), _parse_gff_float(item.get('order'), 0), _parse_gff_float(item.get('start'), 0)))
    _ANCESTRAL_GFF_CACHE['signature'][code] = signature
    _ANCESTRAL_GFF_CACHE['records'][code] = records
    return records, gff_path


_SPECIES_GFF_CACHE = {
    'signature': {},
    'records': {},
}


def _species_gff_path(species_code):
    species_code = str(species_code or '').strip()
    candidates = [
        os.path.join(path_get, 'static', 'Species_data', f'{species_code}.new.gff'),
        os.path.join(str(settings.BASE_DIR), 'static', 'Species_data', f'{species_code}.new.gff'),
        os.path.join(path_get, 'static', 'Species_data', f'{species_code}.gff'),
        os.path.join(str(settings.BASE_DIR), 'static', 'Species_data', f'{species_code}.gff'),
        os.path.join(path_get, 'static', 'blastp_blk_ks_zip', f'{species_code}.new.gff'),
        os.path.join(str(settings.BASE_DIR), 'static', 'blastp_blk_ks_zip', f'{species_code}.new.gff'),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return candidates[0]


def _load_species_gff_records(species_code):
    species_code = str(species_code or '').strip()
    gff_path = _species_gff_path(species_code)
    if not species_code or not os.path.isfile(gff_path):
        return [], gff_path

    stat = os.stat(gff_path)
    signature = (gff_path, stat.st_mtime, stat.st_size)
    if _SPECIES_GFF_CACHE['signature'].get(species_code) == signature:
        return _SPECIES_GFF_CACHE['records'].get(species_code, []), gff_path

    records = []
    with open(gff_path, 'r', encoding='utf-8', errors='replace') as handle:
        for row_index, line in enumerate(handle, start=1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            row = _parse_ancestral_gff_row(line.split('\t'), row_index)
            if row and row.get('gene'):
                records.append(row)

    records.sort(key=lambda item: (str(item.get('chromosome', '')), _parse_gff_float(item.get('order'), 0), _parse_gff_float(item.get('start'), 0)))
    _SPECIES_GFF_CACHE['signature'][species_code] = signature
    _SPECIES_GFF_CACHE['records'][species_code] = records
    return records, gff_path


def _merge_trace_meta_list(target, key, values):
    if not isinstance(values, (list, tuple, set)):
        values = [values]
    bucket = target.setdefault(key, [])
    for value in values:
        value = str(value or '').strip()
        if value and value != '-' and value not in bucket:
            bucket.append(value)


def _build_decobrowse_local_track(records, target_gene, target_meta, all_targets, flank, used_track_keys=None, source_key=''):
    record_lookup = {}
    for index, record in enumerate(records):
        gene = record.get('gene')
        for key in _gene_lookup_keys_for_decobrowse(gene):
            record_lookup.setdefault(key, []).append(index)

    target_indexes = []
    for lookup_key in _gene_lookup_keys_for_decobrowse(target_gene):
        target_indexes.extend(record_lookup.get(lookup_key, []))
    target_indexes = sorted(set(target_indexes))
    if not target_indexes:
        return [], [target_gene]

    tracks = []
    missing_targets = []
    used_track_keys = used_track_keys if used_track_keys is not None else set()
    for target_index in target_indexes:
        target_record = records[target_index]
        chromosome = target_record.get('chromosome')
        same_chr_indexes = [idx for idx, rec in enumerate(records) if rec.get('chromosome') == chromosome]
        try:
            local_position = same_chr_indexes.index(target_index)
        except ValueError:
            local_position = 0
        start_position = max(0, local_position - flank)
        end_position = min(len(same_chr_indexes), local_position + flank + 1)
        window_indexes = same_chr_indexes[start_position:end_position]
        track_key = (source_key, chromosome, tuple(window_indexes), target_gene)
        if track_key in used_track_keys:
            continue
        used_track_keys.add(track_key)
        genes = []
        for idx in window_indexes:
            rec = records[idx]
            rec_gene = rec.get('gene') or ''
            is_target = any(
                rec_gene == candidate or rec_gene.upper() == str(candidate).upper()
                for candidate in all_targets
            )
            meta = all_targets.get(rec_gene) or next(
                (value for key, value in all_targets.items() if str(key).upper() == rec_gene.upper()),
                None,
            )
            genes.append({
                'gene': rec_gene,
                'chromosome': rec.get('chromosome'),
                'start': rec.get('start'),
                'end': rec.get('end'),
                'strand': rec.get('strand') if rec.get('strand') in ('+', '-') else '+',
                'is_target': bool(is_target),
                'queries': (meta or {}).get('queries', []),
                'best_extant_genes': (meta or {}).get('best_extant_genes', []),
                'matched_species': (meta or {}).get('matched_species', []),
                'reference_sets': (meta or {}).get('reference_sets', []),
                'ancestor_codes': (meta or {}).get('ancestor_codes', []),
            })
        tracks.append({
            'chromosome': chromosome,
            'target_gene': target_gene,
            'target_queries': target_meta.get('queries', []),
            'target_best_extant_genes': target_meta.get('best_extant_genes', []),
            'matched_species': target_meta.get('matched_species', []),
            'reference_sets': target_meta.get('reference_sets', []),
            'ancestor_codes': target_meta.get('ancestor_codes', []),
            'genes': genes,
        })
    return tracks, missing_targets

def _gene_lookup_keys_for_decobrowse(gene_id):
    keys = []
    for candidate in _gene_lookup_candidates(gene_id):
        if candidate:
            keys.append(candidate)
            keys.append(candidate.upper())
    seen = set()
    ordered = []
    for key in keys:
        if key and key not in seen:
            seen.add(key)
            ordered.append(key)
    return ordered


def _split_trace_gene_values(values):
    genes = []
    iterable = values if isinstance(values, (list, tuple, set)) else [values]
    for value in iterable:
        for part in re.split(r'[,;\s]+', str(value or '')):
            part = part.strip()
            if part and part != '.':
                genes.append(part)
    return genes


def _dedupe_preserve_order(values):
    deduped = []
    seen = set()
    for value in values or []:
        value = str(value or '').strip()
        if not value or value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _combined_trace_gene_keys(gene_id):
    keys = []
    for candidate in _gene_lookup_candidates(gene_id):
        if candidate:
            keys.append(candidate)
            keys.append(candidate.upper())
    return _dedupe_preserve_order(keys)


def _combined_trace_genes_match(left_gene, right_gene):
    left_keys = set(_combined_trace_gene_keys(left_gene))
    right_keys = set(_combined_trace_gene_keys(right_gene))
    return bool(left_keys and right_keys and left_keys.intersection(right_keys))


def _combined_cell_gene_ids(raw_value):
    raw_value = str(raw_value or '').strip()
    if not raw_value or raw_value == '.':
        return []
    genes = []
    for part in re.split(r'[,;\s]+', raw_value):
        part = part.strip()
        if not part or part == '.':
            continue
        gene_id = _extract_gene_id_from_text(part)
        if gene_id and gene_id != '.':
            genes.append(gene_id)
    if not genes:
        gene_id = _extract_gene_id_from_text(raw_value)
        if gene_id and gene_id != '.':
            genes.append(gene_id)
    return _dedupe_preserve_order(genes)


def _combined_row_cell_value(row_values, column_index):
    if not isinstance(column_index, int) or column_index < 0:
        return ''
    if not row_values or column_index >= len(row_values):
        return ''
    return row_values[column_index]


def _combined_gene_record(gene_id, record_lookup_cache):
    gene_id = _normalize_gene_id_for_lookup(gene_id)
    if not gene_id:
        return None

    ancestor_code = _ancestor_code_from_gene_id(gene_id)
    if ancestor_code:
        source_key = ('ancestor', ancestor_code)
        if source_key not in record_lookup_cache:
            records, _gff_path = _load_ancestral_gff_records(ancestor_code)
            lookup = {}
            for record in records:
                for key in _combined_trace_gene_keys(record.get('gene')):
                    lookup.setdefault(key, record)
            record_lookup_cache[source_key] = lookup
    else:
        species_code = _resolve_gene_species(gene_id)
        if not species_code:
            return None
        source_key = ('species', species_code)
        if source_key not in record_lookup_cache:
            records, _gff_path = _load_species_gff_records(species_code)
            lookup = {}
            for record in records:
                for key in _combined_trace_gene_keys(record.get('gene')):
                    lookup.setdefault(key, record)
            record_lookup_cache[source_key] = lookup

    for key in _combined_trace_gene_keys(gene_id):
        record = record_lookup_cache.get(source_key, {}).get(key)
        if record:
            return record
    return None


def _combined_gene_display(genes, limit=2):
    genes = _dedupe_preserve_order(genes)
    if not genes:
        return ''
    text = ', '.join(genes[:limit])
    if len(genes) > limit:
        text += ' ...'
    return text


def _combined_display_column_indices(column_indices):
    display_indices = []
    seen = set()
    for index in column_indices or []:
        try:
            zero_based_index = int(index)
        except (TypeError, ValueError):
            continue
        one_based_index = zero_based_index + 1
        if one_based_index in seen:
            continue
        seen.add(one_based_index)
        display_indices.append(one_based_index)
    return display_indices


def _combined_trace_cell_payload(genes, role, label, row_context, record_lookup_cache,
                                 species='', ancestor_code='', column_indices=None, is_target=False):
    genes = _dedupe_preserve_order(genes)
    primary_gene = genes[0] if genes else ''
    record = _combined_gene_record(primary_gene, record_lookup_cache) if primary_gene else None
    return {
        'role': role,
        'label': label or '',
        'species': species or '',
        'ancestor_code': ancestor_code or '',
        'column_indices': _combined_display_column_indices(column_indices),
        'gene': primary_gene,
        'genes': genes,
        'display': primary_gene,
        'is_empty': not bool(genes),
        'is_target': bool(is_target),
        'strand': (record or {}).get('strand') if (record or {}).get('strand') in ('+', '-') else '+',
        'chromosome': (record or {}).get('chromosome', ''),
        'start': (record or {}).get('start', ''),
        'end': (record or {}).get('end', ''),
        'query_id': row_context.get('query_id', ''),
        'best_gene': row_context.get('best_gene', ''),
        'matched_species': row_context.get('matched_species', ''),
        'reference_set': row_context.get('reference_set', ''),
    }


def _combined_trace_species_cell(row_values, column, row_context, target_column_index, record_lookup_cache):
    column_index = column.get('index')
    genes = _combined_cell_gene_ids(_combined_row_cell_value(row_values, column_index))
    return _combined_trace_cell_payload(
        genes,
        'species',
        column.get('label') or column.get('species') or f"Column {column_index + 1}",
        row_context,
        record_lookup_cache,
        species=column.get('species') or '',
        column_indices=[column_index],
        is_target=column_index == target_column_index,
    )


def _build_combined_trace_matrix_row(table_row_values, columns, columns_by_index, window_indices, row_context,
                                     target_column_index, record_lookup_cache, ancestor_codes_for_row, is_center_row):
    neighbor_context = dict(row_context)
    ancestor_cells = _combined_trace_ancestor_cells(table_row_values, columns, neighbor_context, record_lookup_cache)
    species_cells = []
    for column_index in window_indices:
        column = columns_by_index.get(column_index)
        if not column:
            continue
        cell = _combined_trace_species_cell(
            table_row_values,
            column,
            neighbor_context,
            target_column_index,
            record_lookup_cache,
        )
        if not is_center_row:
            cell['is_target'] = False
        species_cells.append(cell)

    all_ancestor_cell = _combined_trace_cell_payload(
        [
            gene
            for code in ancestor_codes_for_row
            for gene in (ancestor_cells.get(code, {}).get('genes') or [])
        ],
        'ancestor',
        'Ancestor',
        neighbor_context,
        record_lookup_cache,
        ancestor_code='__all__',
        column_indices=[
            index - 1
            for code in ancestor_codes_for_row
            for index in (ancestor_cells.get(code, {}).get('column_indices') or [])
            if isinstance(index, int)
        ],
    )

    return {
        'query_id': neighbor_context.get('query_id', ''),
        'best_gene': neighbor_context.get('best_gene', ''),
        'matched_species': neighbor_context.get('matched_species', ''),
        'reference_set': neighbor_context.get('reference_set', ''),
        'combined_row_index': neighbor_context.get('combined_row_index'),
        'center_row_index': neighbor_context.get('center_row_index'),
        'is_center_row': bool(is_center_row),
        'row_label': neighbor_context.get('query_id', '') if is_center_row else f"Row {neighbor_context.get('combined_row_index')}",
        'ancestor_codes': ancestor_codes_for_row,
        'ancestor_cells': ancestor_cells,
        'all_ancestor_cell': all_ancestor_cell,
        'species_cells': species_cells,
    }


def _combined_trace_ancestor_cells(row_values, columns, row_context, record_lookup_cache):
    grouped = {}
    for column in columns:
        if column.get('role') != 'ancestor':
            continue
        column_index = column.get('index')
        genes = _combined_cell_gene_ids(_combined_row_cell_value(row_values, column_index))
        for gene_id in genes:
            ancestor_code = column.get('ancestor_code') or _ancestor_code_from_gene_id(gene_id)
            if not ancestor_code:
                continue
            bucket = grouped.setdefault(ancestor_code, {
                'genes': [],
                'columns': [],
                'label': _ancestor_label(ancestor_code),
            })
            bucket['genes'].append(gene_id)
            bucket['columns'].append(column_index)

    cells = {}
    for ancestor_code, bucket in grouped.items():
        cells[ancestor_code] = _combined_trace_cell_payload(
            bucket.get('genes', []),
            'ancestor',
            bucket.get('label') or _ancestor_label(ancestor_code),
            row_context,
            record_lookup_cache,
            ancestor_code=ancestor_code,
            column_indices=bucket.get('columns', []),
        )
    return cells


def _find_combined_row_for_trace_result(row, index):
    source_name = str(row.get('combined_source') or row.get('reference_set') or '').strip()
    row_index = row.get('combined_row_index')
    try:
        row_index = int(row_index)
    except (TypeError, ValueError):
        row_index = None
    if source_name and source_name != '-' and row_index:
        return source_name, row_index

    best_gene = str(row.get('best_gene') or '').strip()
    if not best_gene:
        return source_name, None
    for candidate in _gene_lookup_candidates(best_gene):
        for row_summary in index.get(candidate, []):
            summary_source = row_summary.get('source')
            if source_name and source_name != '-' and summary_source != source_name:
                continue
            return summary_source, row_summary.get('row_index')
    return source_name, None


def _find_combined_target_species_column(row_values, columns, target_gene, matched_species):
    candidates = []
    for column in columns:
        if column.get('role') != 'species':
            continue
        column_index = column.get('index')
        genes = _combined_cell_gene_ids(_combined_row_cell_value(row_values, column_index))
        if not any(_combined_trace_genes_match(gene_id, target_gene) for gene_id in genes):
            continue
        score = 0
        if matched_species and column.get('species') == matched_species:
            score += 10
        if any(str(gene_id) == str(target_gene) for gene_id in genes):
            score += 5
        candidates.append((score, column_index))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], item[1]))
    return candidates[0][1]


def _balanced_trace_window_bounds(center_position, total_count, flank):
    """Return an exclusive window that keeps the target visible and fills from the other side near edges."""
    try:
        center_position = int(center_position)
        total_count = int(total_count)
        flank = int(flank)
    except (TypeError, ValueError):
        return 0, 0

    if total_count <= 0:
        return 0, 0

    center_position = max(0, min(center_position, total_count - 1))
    target_width = min(total_count, flank * 2 + 1)
    window_start = max(0, center_position - flank)
    window_end = min(total_count, center_position + flank + 1)
    missing_width = target_width - (window_end - window_start)

    if missing_width > 0:
        grow_left = min(window_start, missing_width)
        window_start -= grow_left
        missing_width -= grow_left
        window_end = min(total_count, window_end + missing_width)

    return window_start, window_end


def build_trace_decobrowse_payload(trace_results, flank=5):
    """Build a transposed combined-table matrix for tracing DecoBrowse."""
    combined_index, _paths = _load_combined_trace_index()
    tables, _table_paths = _load_combined_trace_tables()
    record_lookup_cache = {}
    ancestor_map = {}
    query_map = {}
    matrix_rows = []
    warnings = []

    for row in trace_results or []:
        query_id = str(row.get('query_id') or '').strip()
        best_gene = str(row.get('best_gene') or '').strip()
        matched_species = str(row.get('matched_species') or '').strip()
        reference_set = str(row.get('reference_set') or '').strip()
        if best_gene and (not matched_species or matched_species == 'Unknown'):
            matched_species = _resolve_gene_species(best_gene) or matched_species or 'Unknown'

        query_summary = query_map.setdefault(query_id or 'Unknown query', {
            'id': query_id or 'Unknown query',
            'target_count': 0,
            'ancestor_labels': [],
            'ancestor_codes': [],
            'matched_species': [],
            'best_extant_genes': [],
        })
        _merge_trace_meta_list(query_summary, 'matched_species', matched_species)
        _merge_trace_meta_list(query_summary, 'best_extant_genes', best_gene)

        source_name, row_index = _find_combined_row_for_trace_result(row, combined_index)
        table = tables.get(source_name)
        if not table or not row_index:
            if best_gene:
                warnings.append(f'No combined-table row was found for {best_gene}.')
            continue

        table_rows = table.get('rows') or []
        if row_index < 1 or row_index > len(table_rows):
            warnings.append(f'Combined-table row {row_index} is unavailable in {source_name}.')
            continue

        row_values = table_rows[row_index - 1]
        columns = table.get('columns') or []
        species_column_indices = table.get('species_column_indices') or []
        target_column_index = _find_combined_target_species_column(
            row_values,
            columns,
            best_gene,
            matched_species,
        )
        if target_column_index is None:
            warnings.append(f'No species column was found for {best_gene} in {source_name} row {row_index}.')
            continue

        try:
            target_species_position = species_column_indices.index(target_column_index)
        except ValueError:
            warnings.append(f'Target column for {best_gene} was classified outside species columns.')
            continue

        window_start, window_end = _balanced_trace_window_bounds(
            target_species_position,
            len(species_column_indices),
            flank,
        )
        window_indices = species_column_indices[window_start:window_end]
        columns_by_index = {column.get('index'): column for column in columns}
        row_context = dict(row)
        row_context.update({
            'query_id': query_id,
            'best_gene': best_gene,
            'matched_species': matched_species,
            'reference_set': source_name,
            'combined_source': source_name,
            'combined_row_index': row_index,
        })

        ancestor_cells = _combined_trace_ancestor_cells(row_values, columns, row_context, record_lookup_cache)
        ancestor_codes_for_row = sorted(ancestor_cells.keys(), key=_ancestor_sort_key)
        gene_map = row.get('ancestor_gene_map') or row.get('ancestor_genes') or {}
        if isinstance(gene_map, dict):
            for raw_code, raw_genes in gene_map.items():
                code = _normalize_ancestor_code(raw_code)
                if code not in ANCESTRAL_DATASETS:
                    continue
                if code not in ancestor_codes_for_row:
                    ancestor_codes_for_row.append(code)
        ancestor_codes_for_row = sorted(_dedupe_preserve_order(ancestor_codes_for_row), key=_ancestor_sort_key)

        if ancestor_codes_for_row:
            query_summary['target_count'] += 1

        for code in ancestor_codes_for_row:
            _merge_trace_meta_list(query_summary, 'ancestor_codes', code)
            _merge_trace_meta_list(query_summary, 'ancestor_labels', _ancestor_label(code))
            ancestor_summary = ancestor_map.setdefault(code, {
                'code': code,
                'label': _ancestor_label(code),
                'target_count': 0,
                'query_ids': [],
                'matched_species': [],
            })
            ancestor_summary['target_count'] += 1
            _merge_trace_meta_list(ancestor_summary, 'query_ids', query_id)
            _merge_trace_meta_list(ancestor_summary, 'matched_species', matched_species)

        center_row_zero_based = row_index - 1
        row_window_start = max(0, center_row_zero_based - flank)
        row_window_end = min(len(table_rows), center_row_zero_based + flank + 1)
        for neighbor_row_zero_based in range(row_window_start, row_window_end):
            is_center_row = neighbor_row_zero_based == center_row_zero_based
            neighbor_context = dict(row_context)
            neighbor_context.update({
                'combined_row_index': neighbor_row_zero_based + 1,
                'center_row_index': row_index,
            })
            matrix_row = _build_combined_trace_matrix_row(
                table_rows[neighbor_row_zero_based],
                columns,
                columns_by_index,
                window_indices,
                neighbor_context,
                target_column_index,
                record_lookup_cache,
                ancestor_codes_for_row,
                is_center_row,
            )
            matrix_row.update({
                'target_species_position': target_species_position,
                'target_column_index': target_column_index + 1,
                'left_species_count': target_species_position - window_start,
                'right_species_count': window_end - target_species_position - 1,
            })
            matrix_rows.append(matrix_row)

    queries = []
    for query_id, query_summary in query_map.items():
        if not query_id or query_id == 'Unknown query':
            continue
        queries.append(query_summary)
    queries.sort(key=lambda item: item.get('id') or '')

    ancestors = []
    for code in sorted(ancestor_map, key=_ancestor_sort_key):
        summary = ancestor_map[code]
        ancestors.append({
            'code': summary['code'],
            'label': summary['label'],
            'target_count': summary['target_count'],
            'query_count': len(summary.get('query_ids') or []),
            'matched_species': summary.get('matched_species') or [],
        })

    return {
        'ancestors': ancestors,
        'rows': matrix_rows,
        'queries': queries,
        'flank': flank,
        'warnings': _dedupe_preserve_order(warnings)[:12],
    }

def _ancestral_meta_path(output_directory):
    return os.path.join(output_directory, 'ancestral_chromosome_meta.json')


def _write_json_file(path, payload):
    tmp_path = f'{path}.tmp'
    with open(tmp_path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def _read_ancestral_meta(output_directory):
    meta_path = _ancestral_meta_path(output_directory)
    if not os.path.exists(meta_path):
        return {}
    try:
        with open(meta_path, 'r', encoding='utf-8') as handle:
            return json.load(handle)
    except Exception:
        return {}


def _update_ancestral_meta(output_directory, updates):
    metadata = _read_ancestral_meta(output_directory)
    metadata.update(updates)
    _write_json_file(_ancestral_meta_path(output_directory), metadata)
    return metadata


def _run_ancestral_trace_job(c):
    output_directory = os.path.join(path_get, 'file_keep', c)
    close_old_connections()
    try:
        metadata = _read_ancestral_meta(output_directory)
        query_file = os.path.join(output_directory, metadata.get('query_file') or 'temp_query.fasta')
        sequence_type = metadata.get('sequence_type') or SEQUENCE_TYPE_PROTEIN
        e_value_cutoff = float(metadata.get('e_value_cutoff', metadata.get('e_value', '1e-5')))
        score_cutoff = float(metadata.get('score_cutoff', metadata.get('score', '0')))
        identity_cutoff = float(metadata.get('identity_cutoff', metadata.get('identity', '0')))
        result_file = os.path.join(output_directory, metadata.get('result_file') or 'all_species_results.tsv')
        trace_file = os.path.join(output_directory, metadata.get('trace_result_file') or 'ancestral_trace_results.json')

        _update_ancestral_meta(output_directory, {
            'job_status': 'running',
            'job_message': 'Searching traceable extant species databases with available ancestral chromosome relationships. This may take a few minutes.',
        })

        db_paths = _traceable_species_db_paths(sequence_type)
        run_ncbi_blast(
            query_file,
            sequence_type,
            e_value_cutoff,
            result_file,
            db_paths=db_paths,
            alias_name=f'traceable_species_{sequence_type}',
            max_target_seqs=50,
        )

        best_hits, total_hits, filtered_hits = _select_best_hits(
            result_file,
            max_evalue=e_value_cutoff,
            min_score=score_cutoff,
            min_identity=identity_cutoff,
        )
        trace_results, traced_queries, available_sources = _trace_best_hits_to_ancestors(best_hits)
        _write_json_file(trace_file, trace_results)

        _update_ancestral_meta(output_directory, {
            'job_status': 'finished',
            'job_message': 'Ancestral gene tracing completed.',
            'total_hits': total_hits,
            'filtered_hits': filtered_hits,
            'best_hit_count': len(best_hits),
            'traced_query_count': len(traced_queries),
            'trace_result_count': len(trace_results),
            'available_reference_sets': available_sources,
            'searched_species': list(TRACEABLE_EXTANT_SPECIES),
        })
    except Exception as exc:
        try:
            import traceback
            error_detail = traceback.format_exc()
            with open(os.path.join(output_directory, 'ancestral_trace_error.log'), 'w', encoding='utf-8') as handle:
                handle.write(error_detail)
        except Exception:
            pass
        _update_ancestral_meta(output_directory, {
            'job_status': 'failed',
            'job_message': str(exc) or 'Ancestral gene tracing failed.',
        })
    finally:
        close_old_connections()


def _start_ancestral_trace_job(c):
    worker = threading.Thread(target=_run_ancestral_trace_job, args=(c,), daemon=True)
    worker.start()
    return worker

ANCESTRAL_KS_DOTPLOT_JOB_ID_RE = re.compile(r'^[A-Za-z0-9_-]{8,80}$')


def _ancestral_ks_dotplot_jobs_root():
    return os.path.join(str(settings.BASE_DIR), 'file_keep')


def _ancestral_ks_dotplot_job_is_valid(job_id):
    return ANCESTRAL_KS_DOTPLOT_JOB_ID_RE.fullmatch(str(job_id or '')) is not None


def _ancestral_ks_dotplot_job_dir(job_id):
    return os.path.join(_ancestral_ks_dotplot_jobs_root(), str(job_id))


def _ancestral_ks_dotplot_status_path(job_id):
    return os.path.join(_ancestral_ks_dotplot_job_dir(job_id), 'status.json')


def _ancestral_ks_dotplot_request_path(job_id):
    return os.path.join(_ancestral_ks_dotplot_job_dir(job_id), 'request.json')


def _ancestral_ks_dotplot_result_zip_path(job_id):
    return os.path.join(_ancestral_ks_dotplot_job_dir(job_id), 'result.zip')


def _collect_ancestral_ks_dotplot_plot_files(job_id):
    """Return final plot files that should be exposed to users.

    Intermediate WGDI files are intentionally excluded from the default
    download.  The main output for the current tool is ks.dotplot.pdf.
    If future modes generate several dotplot images, expose them directly
    when there are at most three files and package only larger groups.
    """
    job_dir = _ancestral_ks_dotplot_job_dir(job_id)
    patterns = [
        'ks.dotplot.pdf',
        '*.dotplot.pdf',
        '*.dotplot.png',
        '*.dotplot.svg',
        '*.dotplot.jpg',
        '*.dotplot.jpeg',
    ]
    matched_files = []
    seen = set()
    for pattern in patterns:
        for file_path in glob.glob(os.path.join(job_dir, pattern)):
            if not os.path.isfile(file_path):
                continue
            normalized_path = os.path.abspath(file_path)
            if normalized_path in seen:
                continue
            seen.add(normalized_path)
            matched_files.append(file_path)

    preferred_path = os.path.join(job_dir, 'ks.dotplot.pdf')
    matched_files.sort(key=lambda item: (0 if os.path.abspath(item) == os.path.abspath(preferred_path) else 1, os.path.basename(item)))
    return matched_files


def _ancestral_ks_dotplot_file_download_url(job_id, file_path):
    return (
        reverse('ancestral_ks_dotplot_download_url', args=[job_id])
        + '?file='
        + quote(os.path.basename(file_path))
    )


def _build_ancestral_ks_dotplot_download_payload(job_id):
    plot_files = _collect_ancestral_ks_dotplot_plot_files(job_id)
    if not plot_files:
        return {}

    if len(plot_files) > 3:
        zip_path = _ancestral_ks_dotplot_result_zip_path(job_id)
        if not os.path.isfile(zip_path) or os.path.getsize(zip_path) == 0:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_path in plot_files:
                    zip_file.write(file_path, arcname=os.path.basename(file_path))
        return {
            'download_mode': 'zip',
            'download_file_count': len(plot_files),
            'download_url': reverse('ancestral_ks_dotplot_download_url', args=[job_id]),
            'download_label': f'ks_dotplot_{job_id}.zip',
            'download_urls': [
                {
                    'url': reverse('ancestral_ks_dotplot_download_url', args=[job_id]),
                    'label': f'ks_dotplot_{job_id}.zip',
                }
            ],
        }

    download_urls = [
        {
            'url': _ancestral_ks_dotplot_file_download_url(job_id, file_path),
            'label': os.path.basename(file_path),
        }
        for file_path in plot_files
    ]
    return {
        'download_mode': 'direct_files',
        'download_file_count': len(plot_files),
        'download_url': download_urls[0]['url'],
        'download_label': download_urls[0]['label'],
        'download_urls': download_urls,
    }


def _write_ancestral_ks_dotplot_status(job_id, status, message='', extra=None):
    job_dir = _ancestral_ks_dotplot_job_dir(job_id)
    os.makedirs(job_dir, exist_ok=True)
    payload = {
        'status': status,
        'message': str(message or ''),
        'updated_at': time.time(),
    }
    if extra:
        payload.update(extra)
    with open(_ancestral_ks_dotplot_status_path(job_id), 'w', encoding='utf-8') as status_file:
        json.dump(payload, status_file, ensure_ascii=False, indent=2)


def _read_ancestral_ks_dotplot_status(job_id):
    status_path = _ancestral_ks_dotplot_status_path(job_id)
    if not os.path.isfile(status_path):
        return {'status': 'queued', 'message': 'Waiting to start.'}
    try:
        with open(status_path, 'r', encoding='utf-8') as status_file:
            return json.load(status_file)
    except Exception as exc:
        return {'status': 'error', 'message': f'Could not read ks dotplot status: {exc}'}


def _ancestral_ks_dotplot_iframe_response(script_body):
    return HttpResponse(
        '<html><head><script data-cfasync="false">' + script_body + '</script></head><body></body></html>',
        content_type='text/html; charset=utf-8',
    )


def _ancestral_ks_dotplot_start_response(job_id):
    return _ancestral_ks_dotplot_iframe_response(
        'if (window.top && window.top.startAncestralKsDotplotPolling) {'
        f'window.top.startAncestralKsDotplotPolling({json.dumps(str(job_id))});'
        '}'
    )


def _ancestral_ks_dotplot_error_response(message):
    return _ancestral_ks_dotplot_iframe_response(
        'if (window.top && window.top.showAncestralKsDotplotError) {'
        f'window.top.showAncestralKsDotplotError({json.dumps(str(message or "ks dotplot job failed."))});'
        '}'
    )


def _is_ancestral_ks_dotplot_json_request(request):
    requested_with = request.headers.get('X-Requested-With', '')
    accept_header = request.headers.get('Accept', '')
    return requested_with == 'XMLHttpRequest' or 'application/json' in accept_header.lower()


def _ancestral_ks_dotplot_json_start_response(job_id):
    return JsonResponse({
        'status': 'submitted',
        'job_id': str(job_id),
        'message': 'ks dotplot job submitted.',
    })


def _ancestral_ks_dotplot_json_error_response(message, status=400):
    return JsonResponse({
        'status': 'error',
        'message': str(message or 'ks dotplot job failed.'),
    }, status=status)


def _safe_ks_species_label(value, fallback='Query'):
    value = re.sub(r'[^A-Za-z0-9_.-]+', '_', str(value or '').strip())
    value = value.strip('_.-')
    return value[:60] or fallback


def _save_uploaded_file_to_path(uploaded_file, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'wb') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)


def _copy_text_or_binary_file(source_path, target_path):
    import shutil
    if not os.path.isfile(source_path):
        raise FileNotFoundError(source_path)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    shutil.copyfile(source_path, target_path)


def _append_file_with_newline(source_path, output_handle):
    with open(source_path, 'rb') as source_file:
        content = source_file.read()
    output_handle.write(content)
    if content and not content.endswith(b'\n'):
        output_handle.write(b'\n')


def _concat_fasta_files(output_path, *input_paths):
    with open(output_path, 'wb') as output_handle:
        for input_path in input_paths:
            _append_file_with_newline(input_path, output_handle)


def _read_fasta_ids(fasta_path, max_records=None):
    ids = []
    seen = set()
    with open(fasta_path, 'r', encoding='utf-8', errors='ignore') as fasta_file:
        for line in fasta_file:
            if not line.startswith('>'):
                continue
            seq_id = line[1:].strip().split()[0]
            if seq_id and seq_id not in seen:
                seen.add(seq_id)
                ids.append(seq_id)
                if max_records and len(ids) >= max_records:
                    break
    return ids


def _gene_id_aliases(value):
    value = str(value or '').strip().strip('"').strip("'")
    if not value:
        return set()

    aliases = {value}
    cleaned = re.sub(r'^(gene|transcript|rna|mrna|cds|protein|pep|id):', '', value, flags=re.IGNORECASE)
    aliases.add(cleaned)

    # Common FASTA/GFF naming variations:
    # gene.1 / gene.t1 / gene.p1 / gene-mRNA-1 / gene-RA / gene-PA
    patterns = [
        r'([._-](t|p|mrna|rna|cds|protein|pep)\d*)$',
        r'([._-](RA|RB|RC|RD|RE|PA|PB|PC|PD|PE))$',
        r'(\.\d+)$',
    ]
    changed = True
    while changed:
        changed = False
        for item in list(aliases):
            for pattern in patterns:
                stripped = re.sub(pattern, '', item, flags=re.IGNORECASE)
                if stripped and stripped not in aliases:
                    aliases.add(stripped)
                    changed = True

    more_aliases = set()
    for item in aliases:
        for token in re.split(r'[|,;\s]+', item):
            token = token.strip()
            if token:
                more_aliases.add(token)
                more_aliases.add(re.sub(r'^(gene|transcript|rna|mrna|cds|protein|pep|id):', '', token, flags=re.IGNORECASE))
    aliases.update(item for item in more_aliases if item)
    return aliases


def _build_unique_id_alias_map(ids):
    alias_to_real = {}
    ambiguous_aliases = set()
    for real_id in ids:
        for alias in _gene_id_aliases(real_id):
            if not alias:
                continue
            previous = alias_to_real.get(alias)
            if previous is None:
                alias_to_real[alias] = real_id
            elif previous != real_id:
                ambiguous_aliases.add(alias)
    for alias in ambiguous_aliases:
        alias_to_real.pop(alias, None)
    return alias_to_real

def _parse_gff_attributes(attribute_text):
    attributes = {}
    for item in str(attribute_text or '').strip().split(';'):
        item = item.strip()
        if not item:
            continue
        if '=' in item:
            key, value = item.split('=', 1)
        elif ' ' in item:
            key, value = item.split(None, 1)
        else:
            continue
        attributes[key.strip()] = value.strip().strip('"')
    return attributes


def _gff_candidate_ids(feature_type, attributes):
    feature_type = str(feature_type or '').lower()
    if feature_type in ('mrna', 'transcript', 'primary_transcript'):
        preferred_keys = ['ID', 'transcript_id', 'Name', 'Parent', 'gene_id']
    elif feature_type == 'gene':
        preferred_keys = ['ID', 'gene_id', 'Name']
    elif feature_type == 'cds':
        preferred_keys = ['Parent', 'protein_id', 'ID', 'transcript_id', 'gene_id', 'Name']
    else:
        preferred_keys = ['ID', 'Parent', 'Name', 'gene_id', 'transcript_id']

    candidates = []
    for key in preferred_keys:
        value = attributes.get(key)
        if not value:
            continue
        for item in re.split(r'[,\s]+', value):
            item = item.strip()
            if item:
                candidates.append(item)
    return candidates


def _resolve_gff_gene_id(candidates, alias_map):
    for candidate in candidates:
        if candidate in alias_map:
            return alias_map[candidate]
        cleaned = re.sub(r'^(gene|transcript|rna|cds|protein):', '', candidate)
        if cleaned in alias_map:
            return alias_map[cleaned]
        if '.' in cleaned:
            stripped = cleaned.rsplit('.', 1)[0]
            if stripped in alias_map:
                return alias_map[stripped]
    return None

def _resolve_fasta_id_to_target(raw_id, alias_map):
    candidates = [raw_id]
    candidates.extend(sorted(_gene_id_aliases(raw_id), key=lambda item: (len(item), item), reverse=True))
    for candidate in candidates:
        if candidate in alias_map:
            return alias_map[candidate]
    return None


def _normalize_fasta_ids_to_target_ids(fasta_path, target_ids, label):
    """Rewrite FASTA headers so CDS/PEP files share the same gene IDs.

    WGDI -ks requires one gene ID to exist in both cds.fasta and pep.fasta.
    Many source files differ only by transcript/protein suffixes such as .1,
    .t1, .p1, or gene:/transcript: prefixes.  This function rewrites the
    FASTA at ``fasta_path`` to the canonical IDs from ``target_ids`` whenever
    the mapping is unique.
    """
    target_ids = [item for item in target_ids if item]
    alias_map = _build_unique_id_alias_map(target_ids)
    target_id_set = set(target_ids)
    temp_path = fasta_path + '.normalized.tmp'
    backup_path = fasta_path + '.before_id_normalization'

    total_records = 0
    matched_records = 0
    unmatched_records = 0
    duplicate_records = 0
    unmatched_examples = []
    duplicate_examples = []
    seen_targets = set()
    keep_current_record = False

    with open(fasta_path, 'r', encoding='utf-8', errors='ignore') as input_file, open(temp_path, 'w', encoding='utf-8') as output_file:
        for line in input_file:
            if line.startswith('>'):
                total_records += 1
                raw_header = line[1:].strip()
                raw_id = raw_header.split()[0] if raw_header else ''
                resolved_id = _resolve_fasta_id_to_target(raw_id, alias_map)
                if not resolved_id:
                    keep_current_record = False
                    unmatched_records += 1
                    if len(unmatched_examples) < 12:
                        unmatched_examples.append(raw_id or raw_header)
                    continue
                if resolved_id in seen_targets:
                    keep_current_record = False
                    duplicate_records += 1
                    if len(duplicate_examples) < 12:
                        duplicate_examples.append(raw_id)
                    continue
                seen_targets.add(resolved_id)
                keep_current_record = True
                matched_records += 1
                output_file.write(f'>{resolved_id}\n')
            elif keep_current_record:
                output_file.write(line)

    if matched_records == 0:
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise RuntimeError(
            f'No sequence IDs in {label} could be matched to the corresponding PEP FASTA IDs. '
            f'{label} examples: {", ".join(unmatched_examples) or "none"}. '
            f'PEP examples: {", ".join(target_ids[:8]) or "none"}.'
        )

    if not os.path.exists(backup_path):
        try:
            os.replace(fasta_path, backup_path)
        except OSError:
            backup_path = None
    os.replace(temp_path, fasta_path)

    return {
        'label': label,
        'total_records': total_records,
        'matched_records': matched_records,
        'unmatched_records': unmatched_records,
        'duplicate_records': duplicate_records,
        'target_id_count': len(target_id_set),
        'unmatched_examples': unmatched_examples,
        'duplicate_examples': duplicate_examples,
        'backup_file': os.path.basename(backup_path) if backup_path else None,
    }



def _parse_user_gff_to_wgdi_files(gff_path, pep_ids, normalized_gff_path, lens_path):
    alias_map = _build_unique_id_alias_map(pep_ids)
    records = {}
    total_feature_rows = 0
    matched_feature_rows = 0
    pep_examples = list(pep_ids[:8])
    gff_candidate_examples = []

    def _is_int_text(value):
        return re.fullmatch(r'[+-]?\d+', str(value or '').strip()) is not None

    def _to_int(value):
        return int(str(value).strip())

    def _remember_candidates(candidates):
        for candidate in candidates:
            candidate = str(candidate or '').strip()
            if candidate and candidate not in gff_candidate_examples and len(gff_candidate_examples) < 16:
                gff_candidate_examples.append(candidate)

    with open(gff_path, 'r', encoding='utf-8', errors='ignore') as gff_file:
        for line in gff_file:
            if not line.strip() or line.startswith('#'):
                continue
            parts = line.rstrip('\n').split('\t')
            if len(parts) < 2:
                parts = line.strip().split()

            gene_id = None

            # Standard GFF3/GTF: seqid source type start end score strand phase attributes
            if len(parts) >= 9 and _is_int_text(parts[3]) and _is_int_text(parts[4]):
                total_feature_rows += 1
                chrom = parts[0]
                feature_type = parts[2]
                start = _to_int(parts[3])
                end = _to_int(parts[4])
                strand = parts[6] if parts[6] in ('+', '-') else '+'
                attributes = _parse_gff_attributes(parts[8])
                candidates = _gff_candidate_ids(feature_type, attributes)
                # Also scan every attribute value because many GFF files use custom keys.
                for value in attributes.values():
                    for item in re.split(r'[,\s]+', str(value)):
                        item = item.strip()
                        if item:
                            candidates.append(item)
                _remember_candidates(candidates)
                gene_id = _resolve_gff_gene_id(candidates, alias_map)

            # Already normalized WGDI-like table: chr gene start end strand [order]
            elif len(parts) >= 5 and _is_int_text(parts[2]) and _is_int_text(parts[3]):
                total_feature_rows += 1
                chrom = parts[0]
                start = _to_int(parts[2])
                end = _to_int(parts[3])
                strand = parts[4] if parts[4] in ('+', '-') else '+'
                candidates = [parts[1]]
                if len(parts) >= 6:
                    candidates.append(parts[5])
                _remember_candidates(candidates)
                gene_id = _resolve_gff_gene_id(candidates, alias_map)

            # Common custom table exported from AGRP/example files:
            # chr start end strand old_gene_id gene_id order
            elif len(parts) >= 7 and _is_int_text(parts[1]) and _is_int_text(parts[2]) and parts[3] in ('+', '-'):
                total_feature_rows += 1
                chrom = parts[0]
                start = _to_int(parts[1])
                end = _to_int(parts[2])
                strand = parts[3]
                candidates = [parts[5], parts[4]]
                _remember_candidates(candidates)
                gene_id = _resolve_gff_gene_id(candidates, alias_map)

            # Slightly shorter custom table: chr start end strand gene_id [order]
            elif len(parts) >= 5 and _is_int_text(parts[1]) and _is_int_text(parts[2]) and parts[3] in ('+', '-'):
                total_feature_rows += 1
                chrom = parts[0]
                start = _to_int(parts[1])
                end = _to_int(parts[2])
                strand = parts[3]
                candidates = [parts[4]]
                if len(parts) >= 6:
                    candidates.append(parts[5])
                _remember_candidates(candidates)
                gene_id = _resolve_gff_gene_id(candidates, alias_map)

            else:
                continue

            if not gene_id:
                continue
            matched_feature_rows += 1

            if start > end:
                start, end = end, start
            previous = records.get(gene_id)
            if previous is None:
                records[gene_id] = {
                    'chrom': str(chrom),
                    'start': start,
                    'end': end,
                    'strand': strand,
                }
            else:
                previous['start'] = min(previous['start'], start)
                previous['end'] = max(previous['end'], end)

    if not records:
        raise RuntimeError(
            'No gene IDs in the uploaded GFF/GFF3 could be matched to the uploaded PEP FASTA IDs. '
            'Please check whether FASTA IDs and GFF attributes use the same gene/transcript IDs. '
            f'PEP examples: {", ".join(pep_examples) or "none"}. '
            f'GFF candidate examples: {", ".join(gff_candidate_examples) or "none"}.'
        )

    def natural_key(value):
        return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', str(value))]

    chromosomes = sorted({record['chrom'] for record in records.values()}, key=natural_key)
    chrom_to_records = {chrom: [] for chrom in chromosomes}
    for gene_id, record in records.items():
        chrom_to_records[record['chrom']].append((gene_id, record))

    with open(normalized_gff_path, 'w', encoding='utf-8') as gff_out, open(lens_path, 'w', encoding='utf-8') as lens_out:
        for chrom in chromosomes:
            gene_rows = sorted(chrom_to_records[chrom], key=lambda item: (item[1]['start'], item[1]['end'], item[0]))
            max_end = 0
            for order, (gene_id, record) in enumerate(gene_rows, start=1):
                max_end = max(max_end, record['end'])
                gff_out.write('\t'.join([
                    chrom,
                    gene_id,
                    str(record['start']),
                    str(record['end']),
                    record['strand'],
                    str(order),
                ]) + '\n')
            lens_out.write('\t'.join([chrom, str(max_end), str(len(gene_rows))]) + '\n')

    return {
        'matched_gene_count': len(records),
        'chromosome_count': len(chromosomes),
        'total_feature_rows': total_feature_rows,
        'matched_feature_rows': matched_feature_rows,
    }

def _safe_int_from_text(value, field_name):
    value = str(value or '').strip().replace(',', '')
    if not value:
        raise ValueError(f'{field_name} is empty.')
    try:
        number = float(value)
    except ValueError:
        raise ValueError(f'{field_name} must be numeric.')
    if number <= 0:
        raise ValueError(f'{field_name} must be greater than 0.')
    return int(round(number))


def _read_wgdi_gff_chrom_stats(gff_path):
    chrom_stats = {}
    if not os.path.isfile(gff_path):
        return chrom_stats
    with open(gff_path, 'r', encoding='utf-8', errors='ignore') as gff_file:
        for line in gff_file:
            if not line.strip() or line.startswith('#'):
                continue
            parts = line.rstrip('\n').split('\t')
            if len(parts) < 4:
                parts = line.strip().split()
            if len(parts) < 4:
                continue
            chrom = str(parts[0]).strip()
            try:
                end = int(float(parts[3]))
            except ValueError:
                continue
            stats = chrom_stats.setdefault(chrom, {'max_end': 0, 'gene_count': 0})
            stats['max_end'] = max(stats['max_end'], end)
            stats['gene_count'] += 1
    return chrom_stats


def _normalize_uploaded_lens_to_wgdi_file(uploaded_lens_path, normalized_lens_path, normalized_gff_path=None):
    chrom_stats = _read_wgdi_gff_chrom_stats(normalized_gff_path) if normalized_gff_path else {}
    lens_rows = {}
    total_rows = 0

    with open(uploaded_lens_path, 'r', encoding='utf-8', errors='ignore') as lens_file:
        for line in lens_file:
            raw_line = line.strip()
            if not raw_line or raw_line.startswith('#'):
                continue
            parts = [part for part in re.split(r'[\t, ]+', raw_line) if part]
            if len(parts) < 2:
                continue

            chrom = parts[0].strip()
            try:
                length = _safe_int_from_text(parts[1], f'Length for chromosome {chrom}')
            except ValueError:
                # Common header lines such as "Chr Length" are ignored.
                if total_rows == 0:
                    continue
                raise

            gene_count = None
            if len(parts) >= 3:
                try:
                    gene_count = _safe_int_from_text(parts[2], f'Gene count for chromosome {chrom}')
                except ValueError:
                    gene_count = None
            if gene_count is None and chrom in chrom_stats:
                gene_count = chrom_stats[chrom]['gene_count']

            total_rows += 1
            previous = lens_rows.get(chrom)
            if previous is None:
                lens_rows[chrom] = {'length': length, 'gene_count': gene_count}
            else:
                previous['length'] = max(previous['length'], length)
                if gene_count is not None:
                    previous['gene_count'] = max(previous.get('gene_count') or 0, gene_count)

    if not lens_rows:
        raise RuntimeError('The uploaded query lens file did not contain valid chromosome length rows.')

    if chrom_stats:
        lens_chroms = set(lens_rows)
        gff_chroms = set(chrom_stats)
        if not (lens_chroms & gff_chroms):
            raise RuntimeError(
                'Chromosome names in the uploaded query lens file do not match the uploaded query GFF/GFF3 file. '
                'Please make sure both files use the same chromosome IDs.'
            )

    def natural_key(value):
        return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', str(value))]

    with open(normalized_lens_path, 'w', encoding='utf-8') as lens_out:
        for chrom in sorted(lens_rows, key=natural_key):
            row = lens_rows[chrom]
            gene_count = row.get('gene_count')
            if gene_count is None:
                lens_out.write('\t'.join([chrom, str(row['length'])]) + '\n')
            else:
                lens_out.write('\t'.join([chrom, str(row['length']), str(gene_count)]) + '\n')

    return {
        'source': 'uploaded_lens',
        'chromosome_count': len(lens_rows),
        'total_lens_rows': total_rows,
        'matched_gff_chromosome_count': len(set(lens_rows) & set(chrom_stats)) if chrom_stats else None,
    }


def _natural_sort_key_for_wgdi(value):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', str(value))]


def _deduplicate_wgdi_gff_file(gff_path, label='WGDI GFF'):
    """Ensure WGDI GFF gene IDs are unique before calling WGDI.

    WGDI maps BLAST gene IDs to the GFF ``order`` column through a pandas
    Series indexed by gene ID. If one gene ID appears more than once in the GFF,
    pandas raises ``InvalidIndexError: Reindexing only valid with uniquely valued
    Index objects``. This helper collapses repeated rows for the same gene on the
    same chromosome and raises a clear error if the same ID appears on multiple
    chromosomes.
    """
    records = {}
    duplicate_gene_ids = set()
    cross_chromosome_duplicates = {}
    total_rows = 0
    skipped_rows = 0

    with open(gff_path, 'r', encoding='utf-8', errors='ignore') as gff_in:
        for line_number, line in enumerate(gff_in, start=1):
            raw_line = line.strip()
            if not raw_line or raw_line.startswith('#'):
                continue
            parts = line.rstrip('\n').split('\t')
            if len(parts) < 5:
                parts = raw_line.split()
            if len(parts) < 5:
                skipped_rows += 1
                continue

            total_rows += 1
            chrom = str(parts[0]).strip()
            gene_id = str(parts[1]).strip()
            if not chrom or not gene_id:
                skipped_rows += 1
                continue
            try:
                start = int(float(parts[2]))
                end = int(float(parts[3]))
            except (TypeError, ValueError):
                raise RuntimeError(
                    f'{label} contains a non-numeric start/end value at line {line_number}: {raw_line[:160]}'
                )
            if start > end:
                start, end = end, start
            strand = parts[4] if len(parts) >= 5 and parts[4] in ('+', '-') else '+'

            previous = records.get(gene_id)
            if previous is None:
                records[gene_id] = {
                    'chrom': chrom,
                    'start': start,
                    'end': end,
                    'strand': strand,
                }
                continue

            duplicate_gene_ids.add(gene_id)
            if previous['chrom'] != chrom:
                cross_chromosome_duplicates.setdefault(gene_id, {previous['chrom']}).add(chrom)
                continue

            # Same gene repeated on the same chromosome, commonly caused by
            # transcript/CDS-like duplicated rows. Collapse it into one gene span.
            previous['start'] = min(previous['start'], start)
            previous['end'] = max(previous['end'], end)
            if previous.get('strand') not in ('+', '-') and strand in ('+', '-'):
                previous['strand'] = strand

    if not records:
        raise RuntimeError(f'{label} did not contain any valid WGDI GFF rows.')

    if cross_chromosome_duplicates:
        examples = []
        for gene_id, chroms in list(cross_chromosome_duplicates.items())[:10]:
            examples.append(f'{gene_id}({",".join(sorted(chroms, key=_natural_sort_key_for_wgdi))})')
        raise RuntimeError(
            f'{label} contains duplicated gene IDs located on different chromosomes, so it cannot be safely merged. '
            f'Please make gene IDs unique or fix the GFF. Examples: {"; ".join(examples)}'
        )

    chromosomes = sorted({record['chrom'] for record in records.values()}, key=_natural_sort_key_for_wgdi)
    rows_by_chrom = {chrom: [] for chrom in chromosomes}
    for gene_id, record in records.items():
        rows_by_chrom[record['chrom']].append((gene_id, record))

    tmp_path = f'{gff_path}.dedup.tmp'
    with open(tmp_path, 'w', encoding='utf-8') as gff_out:
        for chrom in chromosomes:
            gene_rows = sorted(rows_by_chrom[chrom], key=lambda item: (item[1]['start'], item[1]['end'], item[0]))
            for order, (gene_id, record) in enumerate(gene_rows, start=1):
                gff_out.write('\t'.join([
                    chrom,
                    gene_id,
                    str(record['start']),
                    str(record['end']),
                    record.get('strand') if record.get('strand') in ('+', '-') else '+',
                    str(order),
                ]) + '\n')
    os.replace(tmp_path, gff_path)

    return {
        'label': label,
        'total_rows': total_rows,
        'valid_gene_count': len(records),
        'duplicate_gene_count': len(duplicate_gene_ids),
        'skipped_rows': skipped_rows,
    }


def _read_wgdi_gff_gene_ids(gff_path):
    gene_ids = set()
    with open(gff_path, 'r', encoding='utf-8', errors='ignore') as gff_in:
        for line in gff_in:
            raw_line = line.strip()
            if not raw_line or raw_line.startswith('#'):
                continue
            parts = line.rstrip('\n').split('\t')
            if len(parts) < 2:
                parts = raw_line.split()
            if len(parts) >= 2 and parts[1].strip():
                gene_ids.add(parts[1].strip())
    return gene_ids


def _filter_ancestral_ks_blast_to_gff_genes(job_dir, blast_filename='diamond.fasta'):
    """Drop DIAMOND hits whose query/subject IDs are absent from normalized WGDI GFF files."""
    blast_path = os.path.join(job_dir, blast_filename)
    query_gene_ids = _read_wgdi_gff_gene_ids(os.path.join(job_dir, '11.gff'))
    reference_gene_ids = _read_wgdi_gff_gene_ids(os.path.join(job_dir, '22.gff'))

    total_rows = 0
    kept_rows = 0
    missing_query_examples = []
    missing_reference_examples = []
    kept_lines = []

    with open(blast_path, 'r', encoding='utf-8', errors='ignore') as blast_in:
        for line in blast_in:
            raw_line = line.strip()
            if not raw_line:
                continue
            parts = raw_line.split()
            if len(parts) < 2:
                continue
            total_rows += 1
            query_gene = parts[0]
            reference_gene = parts[1]
            query_ok = query_gene in query_gene_ids
            reference_ok = reference_gene in reference_gene_ids
            if query_ok and reference_ok:
                kept_lines.append(line if line.endswith('\n') else line + '\n')
                kept_rows += 1
                continue
            if not query_ok and len(missing_query_examples) < 10 and query_gene not in missing_query_examples:
                missing_query_examples.append(query_gene)
            if not reference_ok and len(missing_reference_examples) < 10 and reference_gene not in missing_reference_examples:
                missing_reference_examples.append(reference_gene)

    if kept_rows == 0:
        raise RuntimeError(
            'DIAMOND generated hits, but none of them matched the normalized WGDI GFF gene IDs. '
            'Please check that PEP FASTA IDs and GFF gene IDs are consistent. '
            f'Missing query examples: {", ".join(missing_query_examples) or "none"}. '
            f'Missing reference examples: {", ".join(missing_reference_examples) or "none"}.'
        )

    tmp_path = f'{blast_path}.filtered.tmp'
    with open(tmp_path, 'w', encoding='utf-8') as blast_out:
        blast_out.writelines(kept_lines)
    os.replace(tmp_path, blast_path)

    return {
        'total_rows': total_rows,
        'kept_rows': kept_rows,
        'removed_rows': total_rows - kept_rows,
        'query_gff_gene_count': len(query_gene_ids),
        'reference_gff_gene_count': len(reference_gene_ids),
    }


def _find_ancestral_file_path(ancestor, suffix_candidates):
    ancestral_dir = os.path.join(str(settings.BASE_DIR), 'static', 'ancestral_data', ancestor)
    for suffix in suffix_candidates:
        candidate = os.path.join(ancestral_dir, f'{ancestor}{suffix}')
        if os.path.isfile(candidate):
            return candidate
    raise FileNotFoundError(f'Missing local ancestral file for {ancestor}: {", ".join(ancestor + suffix for suffix in suffix_candidates)}')


def _find_diamond_executable():
    import shutil
    candidates = [
        shutil.which('diamond'),
        '/usr/bin/diamond',
        '/usr/local/bin/diamond',
        '/www/tools/soft_tools/diamond',
        '/www/server/pyporject_evn/Asteraceae_venv/bin/diamond',
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    raise RuntimeError('DIAMOND executable was not found on the server PATH.')


def _run_logged_subprocess(command, cwd, log_handle, step_name):
    log_handle.write(f'\n[STEP] {step_name}\n')
    log_handle.write('COMMAND: ' + ' '.join(map(str, command)) + '\n')
    log_handle.flush()
    completed = subprocess.run(
        command,
        cwd=cwd,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f'{step_name} failed with exit code {completed.returncode}. Please check run.log in the result directory.')


def _run_diamond_for_ancestral_ks_dotplot(job_dir, evalue, threads, log_handle):
    diamond = _find_diamond_executable()
    query_pep = os.path.join(job_dir, 'query.pep')
    reference_pep = os.path.join(job_dir, 'reference.pep')
    db_prefix = os.path.join(job_dir, 'reference_diamond_db')
    blast_output = os.path.join(job_dir, 'diamond.fasta')

    _run_logged_subprocess(
        [diamond, 'makedb', '--in', reference_pep, '-d', db_prefix],
        cwd=job_dir,
        log_handle=log_handle,
        step_name='DIAMOND makedb',
    )
    _run_logged_subprocess(
        [
            diamond,
            'blastp',
            '-q', query_pep,
            '-d', db_prefix,
            '-o', blast_output,
            '-e', str(evalue),
            '-k', '1000',
            '-f', '6',
            '--threads', str(threads),
        ],
        cwd=job_dir,
        log_handle=log_handle,
        step_name='DIAMOND blastp',
    )
    if not os.path.isfile(blast_output) or os.path.getsize(blast_output) == 0:
        raise RuntimeError('DIAMOND finished but no BLAST hits were generated. The two genomes may be too distant or the input PEP files may be invalid.')
    return blast_output


def _zip_ancestral_ks_dotplot_results(job_id, query_species, reference_ancestor):
    download_payload = _build_ancestral_ks_dotplot_download_payload(job_id)
    if not download_payload:
        raise RuntimeError('ks dotplot output file was not generated.')
    return download_payload


def run_ancestral_ks_dotplot_job(job_id):
    if not _ancestral_ks_dotplot_job_is_valid(job_id):
        return

    close_old_connections()
    job_dir = _ancestral_ks_dotplot_job_dir(job_id)
    log_path = os.path.join(job_dir, 'run.log')
    try:
        with open(_ancestral_ks_dotplot_request_path(job_id), 'r', encoding='utf-8') as request_file:
            payload = json.load(request_file)

        ancestor = payload['ancestor']
        query_species = payload['query_species']
        evalue = payload.get('evalue') or '1e-5'
        score = payload.get('score') or '100'
        repeat_number = payload.get('repeat_number') or '5'
        threads = int(payload.get('threads') or 4)

        from tools.views import (
            normalize_wgdi_gff_file,
            normalize_wgdi_lens_file,
            validate_wgdi_ks_file,
            wgdimcs_run_tools,
            wgdikaks_run_tools,
            wgdi_blockinfo_run_tools,
            wgdikaks_dot_run_tools,
        )

        with open(log_path, 'a', encoding='utf-8') as log_handle:
            log_handle.write(f'ks dotplot job: {job_id}\n')
            log_handle.write(f'query species: {query_species}\nreference ancestor: {ancestor}\n')

            _write_ancestral_ks_dotplot_status(job_id, 'running', 'Checking input FASTA and GFF files.', {'progress': 5})
            query_pep_ids = _read_fasta_ids(os.path.join(job_dir, 'query.pep'))
            query_cds_ids = _read_fasta_ids(os.path.join(job_dir, 'query.cds'))
            if not query_pep_ids:
                raise RuntimeError('No sequence IDs were found in the uploaded query PEP file.')
            if not query_cds_ids:
                raise RuntimeError('No sequence IDs were found in the uploaded query CDS file.')
            query_cds_normalization = _normalize_fasta_ids_to_target_ids(
                os.path.join(job_dir, 'query.cds'),
                query_pep_ids,
                'uploaded query CDS',
            )
            query_cds_ids = _read_fasta_ids(os.path.join(job_dir, 'query.cds'))
            query_cds_id_set = set(query_cds_ids)
            query_pep_id_set = set(query_pep_ids)
            if not (query_pep_id_set & query_cds_id_set):
                raise RuntimeError('No shared IDs were found between the uploaded query PEP and CDS files after CDS ID normalization.')

            reference_pep_ids = _read_fasta_ids(os.path.join(job_dir, 'reference.pep'))
            reference_cds_ids = _read_fasta_ids(os.path.join(job_dir, 'reference.cds'))
            if not reference_pep_ids:
                raise RuntimeError(f'No sequence IDs were found in the {ancestor} reference PEP file.')
            if not reference_cds_ids:
                raise RuntimeError(f'No sequence IDs were found in the {ancestor} reference CDS file.')
            reference_cds_normalization = _normalize_fasta_ids_to_target_ids(
                os.path.join(job_dir, 'reference.cds'),
                reference_pep_ids,
                f'{ancestor} reference CDS',
            )
            reference_cds_ids = _read_fasta_ids(os.path.join(job_dir, 'reference.cds'))
            if not (set(reference_pep_ids) & set(reference_cds_ids)):
                raise RuntimeError(f'No shared IDs were found between the {ancestor} reference PEP and CDS files after CDS ID normalization.')

            overlapping_ids = query_pep_id_set & set(reference_pep_ids)
            if overlapping_ids:
                example_ids = ', '.join(sorted(list(overlapping_ids))[:10])
                raise RuntimeError(
                    'Query PEP IDs overlap with the selected ancestral dataset IDs. '
                    f'Please rename query gene IDs before uploading. Examples: {example_ids}'
                )

            _write_ancestral_ks_dotplot_status(job_id, 'running', 'Normalizing query GFF and query lens.', {'progress': 12})
            generated_lens_path = os.path.join(job_dir, '11.generated.len')
            gff_summary = _parse_user_gff_to_wgdi_files(
                os.path.join(job_dir, 'query.raw.gff'),
                query_pep_ids,
                os.path.join(job_dir, '11.gff'),
                generated_lens_path,
            )
            uploaded_lens_path = os.path.join(job_dir, 'query.raw.len')
            lens_source = 'generated_from_gff'
            lens_summary = {
                'source': lens_source,
                'chromosome_count': gff_summary.get('chromosome_count'),
            }
            if os.path.isfile(uploaded_lens_path) and os.path.getsize(uploaded_lens_path) > 0:
                lens_summary = _normalize_uploaded_lens_to_wgdi_file(
                    uploaded_lens_path,
                    os.path.join(job_dir, '11.len'),
                    os.path.join(job_dir, '11.gff'),
                )
                lens_source = 'uploaded_lens'
            else:
                _copy_text_or_binary_file(generated_lens_path, os.path.join(job_dir, '11.len'))

            input_summary = {
                'query_species': query_species,
                'reference_ancestor': ancestor,
                'query_pep_count': len(query_pep_ids),
                'query_cds_count': len(query_cds_ids),
                'query_gff_summary': gff_summary,
                'query_lens_summary': lens_summary,
                'query_lens_source': lens_source,
                'query_cds_normalization': query_cds_normalization,
                'reference_cds_normalization': reference_cds_normalization,
                'reference_pep_count': len(reference_pep_ids),
                'reference_cds_count': len(reference_cds_ids),
                'evalue': evalue,
                'score': score,
                'repeat_number': repeat_number,
            }
            with open(os.path.join(job_dir, 'input_summary.json'), 'w', encoding='utf-8') as summary_file:
                json.dump(input_summary, summary_file, ensure_ascii=False, indent=2)

            _write_ancestral_ks_dotplot_status(job_id, 'running', 'Running DIAMOND BLASTP.', {'progress': 22})
            _run_diamond_for_ancestral_ks_dotplot(job_dir, evalue, threads, log_handle)

            _write_ancestral_ks_dotplot_status(job_id, 'running', 'Running WGDI collinearity analysis.', {'progress': 42})
            normalize_wgdi_gff_file(job_id, '11.gff')
            normalize_wgdi_gff_file(job_id, '22.gff')
            query_gff_dedup_summary = _deduplicate_wgdi_gff_file(os.path.join(job_dir, '11.gff'), 'query GFF')
            reference_gff_dedup_summary = _deduplicate_wgdi_gff_file(os.path.join(job_dir, '22.gff'), f'{ancestor} reference GFF')
            normalize_wgdi_lens_file(job_id, '11.len', '11.gff')
            normalize_wgdi_lens_file(job_id, '22.len', '22.gff')
            blast_filter_summary = _filter_ancestral_ks_blast_to_gff_genes(job_dir)
            log_handle.write('WGDI GFF cleanup: ' + json.dumps({
                'query_gff': query_gff_dedup_summary,
                'reference_gff': reference_gff_dedup_summary,
                'blast_filter': blast_filter_summary,
            }, ensure_ascii=False) + '\n')
            log_handle.flush()
            wgdimcs_run_tools(place=job_id, evalue=evalue, score=score)
            collinearity_path = os.path.join(job_dir, 'result.collinearity.txt')
            if not os.path.isfile(collinearity_path):
                raise RuntimeError('WGDI collinearity result was not generated.')
            _copy_text_or_binary_file(collinearity_path, os.path.join(job_dir, 'colinearity.txt'))

            _write_ancestral_ks_dotplot_status(job_id, 'running', 'Calculating Ks values.', {'progress': 62})
            _concat_fasta_files(os.path.join(job_dir, 'pep.fasta'), os.path.join(job_dir, 'query.pep'), os.path.join(job_dir, 'reference.pep'))
            _concat_fasta_files(os.path.join(job_dir, 'cds.fasta'), os.path.join(job_dir, 'query.cds'), os.path.join(job_dir, 'reference.cds'))
            wgdikaks_run_tools(place=job_id)
            ks_result_path = os.path.join(job_dir, 'ks_result.txt')
            if not os.path.isfile(ks_result_path):
                raise RuntimeError('WGDI Ks result was not generated.')

            _write_ancestral_ks_dotplot_status(job_id, 'running', 'Generating block information.', {'progress': 76})
            _copy_text_or_binary_file(os.path.join(job_dir, 'diamond.fasta'), os.path.join(job_dir, 'blast.txt'))
            _copy_text_or_binary_file(collinearity_path, os.path.join(job_dir, 'block.txt'))
            _copy_text_or_binary_file(ks_result_path, os.path.join(job_dir, 'ks.txt'))
            validate_wgdi_ks_file(job_id, 'ks.txt')
            wgdi_blockinfo_run_tools(
                place=job_id,
                evalue=evalue,
                score=score,
                repeat_number=repeat_number,
                heng_species=query_species,
                shu_species=ancestor,
            )
            blockinfo_candidates = glob.glob(os.path.join(job_dir, '*_block_information.csv'))
            if not blockinfo_candidates:
                raise RuntimeError('WGDI block information file was not generated.')
            blockinfo_path = blockinfo_candidates[0]
            _copy_text_or_binary_file(blockinfo_path, os.path.join(job_dir, 'blockinfo.csv'))

            _write_ancestral_ks_dotplot_status(job_id, 'running', 'Drawing ks dotplot.', {'progress': 88})
            wgdikaks_dot_run_tools(place=job_id, heng_species=query_species, shu_species=ancestor)

            _write_ancestral_ks_dotplot_status(job_id, 'running', 'Preparing ks dotplot download link.', {'progress': 96})
            download_payload = _zip_ancestral_ks_dotplot_results(job_id, query_species, ancestor)
            done_payload = {'progress': 100}
            done_payload.update(download_payload)
            _write_ancestral_ks_dotplot_status(job_id, 'done', 'ks dotplot result is ready.', done_payload)
    except Exception as exc:
        try:
            import traceback
            with open(log_path, 'a', encoding='utf-8') as log_handle:
                log_handle.write('\n[ERROR]\n')
                log_handle.write(traceback.format_exc())
        except Exception:
            pass
        _write_ancestral_ks_dotplot_status(job_id, 'error', exc, {'progress': 100})
    finally:
        close_old_connections()


def _start_ancestral_ks_dotplot_job(job_id):
    job_dir = _ancestral_ks_dotplot_job_dir(job_id)
    os.makedirs(job_dir, exist_ok=True)
    log_path = os.path.join(job_dir, 'background.log')
    python_executable = get_real_python_executable()
    runner_script = r'''
import os
import sys
import traceback
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LGBP.settings')
try:
    import django
    django.setup()
    from browse.views import run_ancestral_ks_dotplot_job
    run_ancestral_ks_dotplot_job(sys.argv[1])
except Exception:
    traceback.print_exc()
    raise
'''
    command = [python_executable, '-c', runner_script, str(job_id)]
    popen_kwargs = {
        'cwd': str(settings.BASE_DIR),
        'stdout': subprocess.PIPE,
        'stderr': subprocess.STDOUT,
        'text': True,
    }
    if os.name == 'nt':
        popen_kwargs['creationflags'] = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
    else:
        popen_kwargs['start_new_session'] = True
    from api.compute_limits import launch_background
    launch_background(command, cwd=str(settings.BASE_DIR), log_path=log_path,
                      status_path=_ancestral_ks_dotplot_status_path(job_id))


def ancestral_ks_dotplot(request):
    is_json_request = _is_ancestral_ks_dotplot_json_request(request)

    def error_response(message, status=400):
        if is_json_request:
            return _ancestral_ks_dotplot_json_error_response(message, status=status)
        return _ancestral_ks_dotplot_error_response(message)

    if request.method != 'POST':
        if is_json_request:
            return _ancestral_ks_dotplot_json_error_response('Only POST requests are allowed.', status=405)
        return HttpResponse(status=405)

    ancestor = _normalize_ancestor_code(request.POST.get('reference_ancestor'))
    if ancestor not in ANCESTRAL_DATASETS:
        return error_response('Please select a valid reference ancestor.')

    query_species = _safe_ks_species_label(request.POST.get('query_species'), fallback='Query')
    evalue = (request.POST.get('ks_evalue') or '1e-5').strip()
    score = (request.POST.get('ks_score') or '100').strip()
    repeat_number = (request.POST.get('ks_repeat_number') or '5').strip()
    threads = (request.POST.get('ks_threads') or '4').strip()

    try:
        _parse_nonnegative_float(evalue, 'E-value')
        _parse_nonnegative_float(score, 'Score')
        if not repeat_number.isdigit():
            raise ValueError('Repeat number must be a positive integer.')
        repeat_number_value = int(repeat_number)
        if repeat_number_value < 1:
            raise ValueError('Repeat number must be at least 1.')
        if not threads.isdigit():
            raise ValueError('Threads must be a positive integer.')
        threads_value = max(1, min(16, int(threads)))
    except ValueError as exc:
        return error_response(str(exc))

    query_pep = request.FILES.get('query_pep')
    query_cds = request.FILES.get('query_cds')
    query_gff = request.FILES.get('query_gff')
    query_lens = request.FILES.get('query_lens')
    if query_pep is None or query_cds is None or query_gff is None:
        return error_response('Please upload query PEP, CDS, and GFF/GFF3 files.')

    job_id = 'aks_' + uuid.uuid4().hex
    job_dir = _ancestral_ks_dotplot_job_dir(job_id)
    from api.download_access import create_job_directory
    create_job_directory(job_dir)

    try:
        _save_uploaded_file_to_path(query_pep, os.path.join(job_dir, 'query.pep'))
        _save_uploaded_file_to_path(query_cds, os.path.join(job_dir, 'query.cds'))
        _save_uploaded_file_to_path(query_gff, os.path.join(job_dir, 'query.raw.gff'))
        if query_lens is not None and getattr(query_lens, 'size', 0) > 0:
            _save_uploaded_file_to_path(query_lens, os.path.join(job_dir, 'query.raw.len'))

        _copy_text_or_binary_file(_find_ancestral_file_path(ancestor, ['.pep']), os.path.join(job_dir, 'reference.pep'))
        _copy_text_or_binary_file(_find_ancestral_file_path(ancestor, ['.cds']), os.path.join(job_dir, 'reference.cds'))
        _copy_text_or_binary_file(_find_ancestral_file_path(ancestor, ['.lens', '.len', '.lens.txt']), os.path.join(job_dir, '22.len'))
        _copy_text_or_binary_file(_find_ancestral_file_path(ancestor, ['.new.gff', '.gff', '.gff3']), os.path.join(job_dir, '22.gff'))

        request_payload = {
            'ancestor': ancestor,
            'query_species': query_species,
            'evalue': evalue,
            'score': score,
            'repeat_number': str(repeat_number_value),
            'threads': threads_value,
            'query_lens_uploaded': query_lens is not None and getattr(query_lens, 'size', 0) > 0,
            'created_at': time.time(),
        }
        with open(_ancestral_ks_dotplot_request_path(job_id), 'w', encoding='utf-8') as request_file:
            json.dump(request_payload, request_file, ensure_ascii=False, indent=2)

        _write_ancestral_ks_dotplot_status(job_id, 'queued', 'ks dotplot job submitted.', {'progress': 0})
        _start_ancestral_ks_dotplot_job(job_id)
    except Exception as exc:
        _write_ancestral_ks_dotplot_status(job_id, 'error', exc, {'progress': 100})
        return error_response(exc)

    if is_json_request:
        return _ancestral_ks_dotplot_json_start_response(job_id)
    return _ancestral_ks_dotplot_start_response(job_id)


def ancestral_ks_dotplot_status(request, job_id):
    if not _ancestral_ks_dotplot_job_is_valid(job_id):
        return JsonResponse({'status': 'error', 'message': 'Invalid ks dotplot job id.'}, status=404)

    status = _read_ancestral_ks_dotplot_status(job_id)
    response_payload = {
        'status': status.get('status', 'running'),
        'message': status.get('message', ''),
        'progress': status.get('progress'),
    }

    download_payload = _build_ancestral_ks_dotplot_download_payload(job_id)
    if status.get('status') == 'done' and download_payload:
        response_payload.update({
            'status': 'done',
            'message': 'ks dotplot result is ready.',
            'progress': 100,
        })
        response_payload.update(download_payload)
    elif os.path.isfile(_ancestral_ks_dotplot_result_zip_path(job_id)):
        # Backward compatibility for old jobs generated before the direct-PDF
        # download behavior was introduced.
        response_payload.update({
            'status': 'done',
            'message': 'ks dotplot result is ready.',
            'progress': 100,
            'download_mode': 'zip',
            'download_file_count': 1,
            'download_url': reverse('ancestral_ks_dotplot_download_url', args=[job_id]),
            'download_label': f'ks_dotplot_{job_id}.zip',
            'download_urls': [
                {
                    'url': reverse('ancestral_ks_dotplot_download_url', args=[job_id]),
                    'label': f'ks_dotplot_{job_id}.zip',
                }
            ],
        })
    return JsonResponse(response_payload)


def ancestral_ks_dotplot_download(request, job_id):
    if not _ancestral_ks_dotplot_job_is_valid(job_id):
        return HttpResponse(status=404)

    plot_files = _collect_ancestral_ks_dotplot_plot_files(job_id)
    plot_files_by_name = {os.path.basename(file_path): file_path for file_path in plot_files}

    requested_file = request.GET.get('file')
    if requested_file:
        requested_name = os.path.basename(unquote(str(requested_file)))
        requested_path = plot_files_by_name.get(requested_name)
        if not requested_path or not os.path.isfile(requested_path):
            return HttpResponse('Requested ks dotplot file was not found.', status=404)
        return FileResponse(open(requested_path, 'rb'), as_attachment=True, filename=requested_name)

    if len(plot_files) == 1:
        file_path = plot_files[0]
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=os.path.basename(file_path))

    if 1 < len(plot_files) <= 3:
        # The status endpoint returns one link per file for this case.  When the
        # base download URL is opened directly, return the main dotplot PDF.
        file_path = plot_files[0]
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=os.path.basename(file_path))

    if len(plot_files) > 3:
        zip_path = _ancestral_ks_dotplot_result_zip_path(job_id)
        if not os.path.isfile(zip_path) or os.path.getsize(zip_path) == 0:
            _build_ancestral_ks_dotplot_download_payload(job_id)
        if os.path.isfile(zip_path):
            return FileResponse(open(zip_path, 'rb'), as_attachment=True, filename=f'ks_dotplot_{job_id}.zip')

    # Backward compatibility for old jobs that only have result.zip.
    zip_path = _ancestral_ks_dotplot_result_zip_path(job_id)
    if os.path.isfile(zip_path):
        return FileResponse(open(zip_path, 'rb'), as_attachment=True, filename=f'ks_dotplot_{job_id}.zip')

    return HttpResponse('ks dotplot result file was not found.', status=404)


from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


# def ancestral_chromosome(request):
#     return render(request, 'ancestral_chromosome.html')
from django.shortcuts import redirect


def ancestral_chromosome(request):
    if request.method == 'POST':
        file1 = request.FILES.get("file1", None)
        query_sequence = request.POST.get('query_sequence')
        patten = request.POST.get("patten")
        search_mode = request.POST.get('search_mode') or ANCESTRAL_SEARCH_MODE_CANDIDATE
        species_data = request.POST.get("species_data") or ALL_ANCESTRAL_DATASETS_VALUE
        e_value = request.POST.get('e_value')
        score = request.POST.get('score_1')
        identity = request.POST.get('identity_1')

        submitted_context = {'submitted_search_mode': search_mode}
        try:
            e_value_cutoff = _parse_nonnegative_float(e_value, 'E-value')
            score_cutoff = _parse_nonnegative_float(score, 'Score value')
            identity_cutoff = _parse_nonnegative_float(identity, 'Identity value')
        except ValueError as exc:
            return render(request, 'ancestral_chromosome.html', ancestral_context({
                'error_message': str(exc),
                **submitted_context,
            }))

        if patten == 'blastn':
            nucl_or_prot = SEQUENCE_TYPE_NUCLEOTIDE
            sequence_type_label = 'Nucleotide sequence (BLASTN)'
        else:
            nucl_or_prot = SEQUENCE_TYPE_PROTEIN
            sequence_type_label = 'Protein sequence (BLASTP)'

        if file1 is None and not query_sequence:
            return render(request, 'ancestral_chromosome.html', ancestral_context({
                'error_message': 'Please provide a query sequence or upload a FASTA file.',
                **submitted_context,
            }))

        c = name_set()
        output_directory = f"{path_get}/file_keep/{c}"
        if query_sequence:
            temp_fasta_file = write_fasta_file(query_sequence, output_directory)
            up_file_name = "temp_query"
        else:
            up_file_name = file1.name.rsplit('.', 1)[0]
            keep_file(na=file1, c=c)
            temp_fasta_file = os.path.join(output_directory, file1.name)

        try:
            _validate_sequence_type_for_search(temp_fasta_file, nucl_or_prot)
        except ValueError as exc:
            return render(request, 'ancestral_chromosome.html', ancestral_context({
                'error_message': str(exc),
                **submitted_context,
            }))

        if search_mode == ANCESTRAL_SEARCH_MODE_TRACE:
            blast_result_file = os.path.join(output_directory, f"{up_file_name}_traceable_species_{nucl_or_prot}.tsv")
            trace_result_file = os.path.join(output_directory, 'ancestral_trace_results.json')
            result_meta = {
                'search_mode': ANCESTRAL_SEARCH_MODE_TRACE,
                'mode_label': ANCESTRAL_SEARCH_MODE_LABELS[ANCESTRAL_SEARCH_MODE_TRACE],
                'job_status': 'running',
                'job_message': 'Searching traceable extant species databases with available ancestral chromosome relationships. This may take a few minutes.',
                'query_name': up_file_name,
                'query_file': os.path.basename(temp_fasta_file),
                'sequence_type': nucl_or_prot,
                'sequence_type_label': sequence_type_label,
                'species_data': TRACEABLE_EXTANT_SPECIES_LABEL,
                'species_codes': list(TRACEABLE_EXTANT_SPECIES),
                'e_value': e_value,
                'score': score,
                'identity': identity,
                'e_value_cutoff': e_value_cutoff,
                'score_cutoff': score_cutoff,
                'identity_cutoff': identity_cutoff,
                'total_hits': 0,
                'filtered_hits': 0,
                'best_hit_count': 0,
                'traced_query_count': 0,
                'trace_result_count': 0,
                'available_reference_sets': [],
                'result_file': os.path.basename(blast_result_file),
                'trace_result_file': os.path.basename(trace_result_file),
                'unavailable_relationship_message': 'The sequence matched a gene in the database, but this gene has not yet been linked to an ancestral chromosome relationship in the current system.',
            }
            _write_json_file(os.path.join(output_directory, 'ancestral_chromosome_meta.json'), result_meta)
            _start_ancestral_trace_job(c)
            return redirect('ancestral_chromosome_run', c=c)

        if species_data == ALL_ANCESTRAL_DATASETS_VALUE:
            selected_ancestors = list(ANCESTRAL_DATASETS)
            result_species_label = 'all_ancestors'
            display_species_label = 'All ancestors'
        else:
            selected_ancestors = [species_data]
            result_species_label = species_data
            display_species_label = species_data

        if not selected_ancestors or any(ancestor not in ANCESTRAL_DATASETS for ancestor in selected_ancestors):
            return render(request, 'ancestral_chromosome.html', ancestral_context({
                'error_message': 'Please select a valid ancestral chromosome database.',
                **submitted_context,
            }))

        result_suffix = 'diamond' if nucl_or_prot == SEQUENCE_TYPE_PROTEIN else 'blastn'
        blast_result_file = os.path.join(output_directory, f"{up_file_name}_{result_species_label}.{result_suffix}")
        raw_result_files = []
        total_hits = 0
        filtered_hits = 0

        for index, ancestor in enumerate(selected_ancestors):
            raw_blast_result_file = os.path.join(output_directory, f"{up_file_name}_{ancestor}.raw.tsv")
            raw_result_files.append(os.path.basename(raw_blast_result_file))
            try:
                if nucl_or_prot == SEQUENCE_TYPE_PROTEIN:
                    run_diamond(temp_fasta_file, nucl_or_prot, ancestor, e_value_cutoff, raw_blast_result_file)
                else:
                    ancestor_db = get_ancestral_nucl_db_prefix(ancestor)
                    run_ncbi_blast(
                        temp_fasta_file,
                        nucl_or_prot,
                        e_value_cutoff,
                        raw_blast_result_file,
                        db_value=ancestor_db,
                        max_target_seqs=50,
                    )
            except (FileNotFoundError, RuntimeError, ValueError) as exc:
                program_name = 'DIAMOND' if nucl_or_prot == SEQUENCE_TYPE_PROTEIN else 'BLASTN'
                return render(request, 'ancestral_chromosome.html', ancestral_context({
                    'error_message': f'{program_name} search failed for {ancestor}: {exc}',
                    **submitted_context,
                }))
            ancestor_total_hits, ancestor_filtered_hits = write_filtered_blast_result_file(
                raw_blast_result_file,
                blast_result_file,
                max_evalue=e_value_cutoff,
                min_score=score_cutoff,
                min_identity=identity_cutoff,
                ancestor=ancestor,
                mode='w' if index == 0 else 'a',
            )
            total_hits += ancestor_total_hits
            filtered_hits += ancestor_filtered_hits

        result_meta = {
            'search_mode': ANCESTRAL_SEARCH_MODE_CANDIDATE,
            'mode_label': ANCESTRAL_SEARCH_MODE_LABELS[ANCESTRAL_SEARCH_MODE_CANDIDATE],
            'query_name': up_file_name,
            'sequence_type': nucl_or_prot,
            'sequence_type_label': sequence_type_label,
            'species_data': display_species_label,
            'species_codes': selected_ancestors,
            'e_value': e_value,
            'score': score,
            'identity': identity,
            'total_hits': total_hits,
            'filtered_hits': filtered_hits,
            'result_file': os.path.basename(blast_result_file),
            'raw_result_files': raw_result_files,
        }
        with open(os.path.join(output_directory, 'ancestral_chromosome_meta.json'), 'w', encoding='utf-8') as meta_file:
            json.dump(result_meta, meta_file, ensure_ascii=False, indent=2)

        return redirect('ancestral_chromosome_run', c=c)
    else:
        return render(request, 'ancestral_chromosome.html', ancestral_context())


from django.shortcuts import render
from django.core.paginator import Paginator
import glob


def ancestral_chromosome_run(request, c):
    if not re.fullmatch(r'\d{9}', c):
        return HttpResponse('Invalid result id.', status=400)

    output_directory = os.path.join(path_get, 'file_keep', c)
    metadata = {}
    metadata_path = os.path.join(output_directory, 'ancestral_chromosome_meta.json')
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r', encoding='utf-8') as meta_file:
            try:
                metadata = json.load(meta_file)
            except json.JSONDecodeError:
                metadata = {}

    search_mode = metadata.get('search_mode') or ANCESTRAL_SEARCH_MODE_CANDIDATE
    page_mode_label = ANCESTRAL_SEARCH_MODE_LABELS.get(search_mode) or metadata.get('mode_label') or 'Blast Results'
    result_section_label = page_mode_label if search_mode == ANCESTRAL_SEARCH_MODE_CANDIDATE else ''
    job_status = metadata.get('job_status') or ('finished' if search_mode != ANCESTRAL_SEARCH_MODE_TRACE else 'finished')
    trace_results = []
    blast_results = []
    result_file = None
    trace_decobrowse_payload = {'ancestors': [], 'flank': 6}

    if search_mode == ANCESTRAL_SEARCH_MODE_TRACE and job_status in ('running', 'queued'):
        result_count = 0
        alignment_payload = build_ancestral_trace_payload([], metadata)
    elif search_mode == ANCESTRAL_SEARCH_MODE_TRACE:
        trace_file = None
        if metadata.get('trace_result_file'):
            candidate = os.path.join(output_directory, metadata['trace_result_file'])
            if os.path.exists(candidate):
                trace_file = candidate
        if trace_file is None:
            candidate = os.path.join(output_directory, 'ancestral_trace_results.json')
            if os.path.exists(candidate):
                trace_file = candidate
        if trace_file:
            with open(trace_file, 'r', encoding='utf-8') as handle:
                try:
                    trace_results = json.load(handle)
                except json.JSONDecodeError:
                    trace_results = []
        result_count = len(trace_results)
        alignment_payload = build_ancestral_trace_payload(trace_results, metadata)
        trace_decobrowse_payload = build_trace_decobrowse_payload(trace_results)
    else:
        if metadata.get('result_file'):
            candidate = os.path.join(output_directory, metadata['result_file'])
            if os.path.exists(candidate):
                result_file = candidate
        if result_file is None:
            blast_results_files = glob.glob(os.path.join(output_directory, '*.diamond')) + glob.glob(os.path.join(output_directory, '*.blastn'))
            result_file = blast_results_files[0] if blast_results_files else None

        if result_file and os.path.exists(result_file):
            blast_results, geneids = parse_blastp_result(
                result_file,
                include_ancestor=True,
                default_ancestor=metadata.get('species_data'),
            )
        result_count = len(blast_results)
        alignment_payload = build_ancestral_alignment_payload(blast_results, metadata)

    return render(request, 'ancestral_chromosome_run.html', {
        'blast_results': blast_results,
        'trace_results': trace_results,
        'metadata': metadata,
        'search_mode': search_mode,
        'page_mode_label': page_mode_label,
        'result_section_label': result_section_label,
        'alignment_payload': alignment_payload,
        'trace_decobrowse_payload': trace_decobrowse_payload,
        'result_count': result_count,
        'total_hits': metadata.get('total_hits', result_count),
        'filtered_hits': metadata.get('filtered_hits', result_count),
        'job_status': job_status,
        'job_message': metadata.get('job_message', ''),
    })






















































































































# ncRNA
def ncRNA(request):
    return render(request, 'ncRNA.html')


def ncRNA_run(request):
    sp_data_1 = request.POST.get("sp_data_1", None)
    sp_data_2 = request.POST.get("sp_data_2", None)
    return render(request, f'ncRNA_run.html', {"sp_name": sp_data_1, "type": sp_data_2})



def Pfam_index(request):
    return render(request, 'pfam_index.html')


def pfam_index_run(request):
    sp_data_1 = request.POST.get("sp_data_1", None)
    return render(request, f'pfam_{sp_data_1}.html')


def file_iterator(file_name, chunk_size=8192, offset=0, length=None):
    with open(file_name, "rb") as f:
        f.seek(offset, os.SEEK_SET)
        remaining = length
        while True:
            bytes_length = chunk_size if remaining is None else min(remaining, chunk_size)
            data = f.read(bytes_length)
            if not data:
                break
            if remaining:
                remaining -= len(data)
            yield data


def stream_video(request):
    """将视频文件以流媒体的方式响应"""
    range_header = request.META.get('HTTP_RANGE', '').strip()
    range_re = re.compile(r'bytes\s*=\s*(\d+)\s*-\s*(\d*)', re.I)
    range_match = range_re.match(range_header)
    path = request.GET.get('path')
    # 这里根据实际情况改变，我的views.py在core文件夹下但是folder_path却只到core的上一层，media也在core文件夹下
    folder_path = os.getcwd().replace('\\', '/')
    path = folder_path + '/core/' + path  # path就是template ？后面的参数的值
    size = os.path.getsize(path)
    content_type, encoding = mimetypes.guess_type(path)
    content_type = content_type or 'application/octet-stream'
    if range_match:
        first_byte, last_byte = range_match.groups()
        first_byte = int(first_byte) if first_byte else 0
        last_byte = first_byte + 1024 * 1024 * 10
        if last_byte >= size:
            last_byte = size - 1
        length = last_byte - first_byte + 1
        resp = StreamingHttpResponse(file_iterator(path, offset=first_byte, length=length), status=206,
                                     content_type=content_type)
        resp['Content-Length'] = str(length)
        resp['Content-Range'] = 'bytes %s-%s/%s' % (first_byte, last_byte, size)
    else:
        resp = StreamingHttpResponse(FileWrapper(open(path, 'rb')), content_type=content_type)
        resp['Content-Length'] = str(size)
    resp['Accept-Ranges'] = 'bytes'
    return resp


def readFile(filename, chunk_size=512):
    with open(filename, 'rb') as f:
        while True:
            c = f.read(chunk_size)
            if c:
                yield c
            else:
                break


def Download_file(request, name_path):
    # print(name_path)
    file_name = name_path.split("-")[1]
    file_path = name_path.split("-")[0]
    the_file_name = file_name  # 显示在弹出对话框中的默认的下载文件名

    filename = os.path.join(path_get, "file_keep", file_path, file_name)  # 要下载的文件路径

    if not os.path.exists(filename):
        return HttpResponse("Build file not found! Please change the sequence and try again.")

    response = StreamingHttpResponse(readFile(filename))
    response['Content-Type'] = 'application/octet-stream'
    response['Content-Disposition'] = 'attachment;filename="{0}"'.format(the_file_name)
    return response



def vvi_syntenic(request):
    return render(request, 'vvi_syntenic.html')

def ACH_event(request):
    return render(request, 'ACH_event_genes.html')

def AST_event(request):
    return render(request, 'AST_event_genes.html')


def Metabolomics(request):
    return render(request, 'Metabolomics.html')

SCAFFOLD_SPECIES = {
    "Amar", "Cpa", "Desu", "Fbi", "Fbr", "Ffl", "Pin", "Scae", "Sesq"
}

def get_species_data_file(sp_name, suffix):
    candidates = [
        os.path.join(settings.BASE_DIR, "static", "Species_data", f"{sp_name}.{suffix}"),
        os.path.join(settings.BASE_DIR, f"{sp_name}.{suffix}"),
    ]

    for path in candidates:
        if os.path.exists(path):
            return path

    raise FileNotFoundError(f"Cannot find file for {sp_name}.{suffix}")


def resolve_seqids(df, sp_name, chromosome_number):
    chrom = str(chromosome_number).strip()
    seqids = (
        df[0]
        .dropna()
        .astype(str)
        .str.strip()
        .drop_duplicates()
        .tolist()
    )

    # 1. exact match
    if chrom in seqids:
        return [chrom]

    # 2. UI value like Aann01 / Bial13 / Tako01
    m = re.search(r"(\d+)$", chrom)
    if m:
        target = int(m.group(1))

        # 2a. match numeric seqid like 1 / 01 / 0001
        numeric_matches = []
        for seqid in seqids:
            base = seqid.split(".")[0]
            if base.isdigit() and int(base) == target:
                numeric_matches.append(seqid)

        if numeric_matches:
            return numeric_matches

        # 2b. fallback: treat 01/02/03 as the nth seqid in file order
        if 1 <= target <= len(seqids):
            return [seqids[target - 1]]

    return []


def genome_scaffolds(request):
    sp_name = (request.GET.get("sp_name") or "").strip()
    if not sp_name:
        return JsonResponse({"error": "sp_name is required", "scaffolds": []}, status=400)

    try:
        gff_file = get_species_data_file(sp_name, "new.gff")
        df = pd.read_csv(gff_file, sep="\t", header=None, dtype={0: str}, usecols=[0])

        scaffolds = (
            df[0]
            .dropna()
            .astype(str)
            .str.strip()
            .loc[lambda s: s.ne("")]
            .drop_duplicates()
            .tolist()
        )

        return JsonResponse({"scaffolds": scaffolds})
    except FileNotFoundError as e:
        return JsonResponse({"error": str(e), "scaffolds": []}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e), "scaffolds": []}, status=500)


def genome(request):
    sp_name = request.POST.get("sp_name")
    chromosome_number = request.POST.get("chromosome_number")
    start = request.POST.get("start")
    end = request.POST.get("end")

    if request.method != "POST" or start is None or end is None:
        return render(request, "genome.html", {
            "selected_species": "",
            "selected_chromosome": "",
            "selected_start": "1000",
            "selected_end": "400000",
        })

    form_state = {
        "selected_species": sp_name or "",
        "selected_chromosome": chromosome_number or "",
        "selected_start": start or "1000",
        "selected_end": end or "400000",
    }

    try:
        start = int(start)
        end = int(end)
    except (TypeError, ValueError):
        return render(request, "genome.html", {
            **form_state,
            "result": [],
            "searched": True,
            "message": "Start/End position is invalid.",
        })

    if start > end:
        start, end = end, start

    form_state["selected_start"] = str(start)
    form_state["selected_end"] = str(end)

    try:
        gff_file = get_species_data_file(sp_name, "new.gff")
        pep_seq_file = get_species_data_file(sp_name, "pep")
        cds_seq_file = get_species_data_file(sp_name, "cds")
    except FileNotFoundError as e:
        return render(request, "genome.html", {
            **form_state,
            "result": [],
            "searched": True,
            "message": str(e),
        })

    df = pd.read_csv(gff_file, sep="\t", header=None, dtype={0: str})
    df[0] = df[0].astype(str).str.strip()
    df[1] = pd.to_numeric(df[1], errors="coerce")
    df[2] = pd.to_numeric(df[2], errors="coerce")

    seqids = resolve_seqids(df, sp_name, chromosome_number)
    if not seqids:
        return render(request, "genome.html", {
            **form_state,
            "result": [],
            "searched": True,
            "message": f"Cannot resolve {chromosome_number} for {sp_name}.",
        })

    filtered_df = df[df[0].isin(seqids)]
    final_filtered_df = filtered_df[(filtered_df[2] >= start) & (filtered_df[1] <= end)]
    gene_ids = final_filtered_df[5].astype(str).tolist()

    pep_sequences = extract_sequences_by_id(pep_seq_file, gene_ids)
    cds_sequences = extract_sequences_by_id(cds_seq_file, gene_ids)
    result = compile_gene_info(cds_sequences, pep_sequences)

    return render(request, "genome.html", {
        **form_state,
        "result": result,
        "searched": True,
        "message": "" if result else "No genes found in this interval.",
    })

# def genome(request):
#     sp_name = request.POST.get("sp_name")
#     chromosome_number = request.POST.get('chromosome_number')  # 格式如 "Aann01"
#     start = request.POST.get('start')
#     end = request.POST.get('end')

#     print(sp_name, chromosome_number, start, end)

#     if start is None or end is None:
#         return render(request, 'genome.html')

#     start = int(start)
#     end = int(end)

#     # 文件夹路径
#     folder_path = os.path.join(settings.BASE_DIR, 'static', 'Species_data')
#     gff_file = os.path.join(folder_path, f"{sp_name}.new.gff")

#     # 解析染色体编号 - 从 "Aann01" 中提取数字部分
#     # 方法1: 使用正则表达式提取所有数字
#     import re
#     chr_number_match = re.search(r'\d+', chromosome_number)
#     if chr_number_match:
#         chr_number = int(chr_number_match.group())
#     else:
#         # 如果没有数字（如 "Amar"），默认为1
#         chr_number = 1

#     gene_ids = get_gene_ids(gff_file, start, end, chr_number)

#     pep_seq_file = os.path.join(folder_path, f"{sp_name}.pep")
#     pep_sequences = extract_sequences_by_id(pep_seq_file, gene_ids)

#     cds_seq_file = os.path.join(folder_path, f"{sp_name}.cds")
#     cds_sequences = extract_sequences_by_id(cds_seq_file, gene_ids)

#     # 汇总基因信息
#     result = compile_gene_info(cds_sequences, pep_sequences)
#     print(f"Result length: {len(result)}")

#     return render(request, 'genome.html', {'result': result})

def dupgen_finders(request):
    sp_data_1 = request.POST.get("sp_data_1", "Aann")
    geneid = (request.POST.get('geneid') or '').strip()
    query_sequence = (request.POST.get('query_sequence') or '').strip()
    is_all_species = sp_data_1 == ALL_INTERPROSCAN_SPECIES_VALUE
    context = {
        'selected_sp_data_1': sp_data_1,
        'geneid_value': geneid,
        'query_sequence_value': query_sequence,
        'not_found_geneids': [],
        'result': [],
        'searched': request.method == 'POST',
        'searched_all_species': is_all_species,
    }
    if request.method != 'POST':
        return render(request, 'dupgen_finders.html', context)
    if not query_sequence and not geneid:
        context['error_message'] = 'Please enter a query sequence or at least one gene ID.'
        return render(request, 'dupgen_finders.html', context)
    if is_all_species and query_sequence:
        job_id = _create_dupgen_all_species_job(query_sequence)
        _start_dupgen_all_species_job(job_id)
        context.update({
            'dupgen_job_id': job_id,
            'all_species_blast_target_limit': DUPGEN_ALL_SPECIES_BLAST_MAX_TARGETS,
        })
        return render(request, 'dupgen_finders.html', context)

    blast_results = None
    if query_sequence:
        c = name_set()
        output_directory = f"{path_get}/file_keep/{c}"
        temp_fasta_file = write_fasta_file(query_sequence, output_directory)

        nucl_or_prot = "prot"
        species_data = sp_data_1
        e = "1e-5"
        blast_result_file = os.path.join(output_directory, "result.txt")
        blast_return_code = run_blastp(temp_fasta_file, nucl_or_prot, species_data, e, blast_result_file)
        if blast_return_code != 0 or not os.path.exists(blast_result_file):
            context['error_message'] = 'BLAST failed. Please check BLAST+ and the protein database for the selected species.'
            return render(request, 'dupgen_finders.html', context)
        blast_results, geneids = parse_blastp_result(blast_result_file)
        geneids = [item.strip() for item in geneids if item and item.strip()]
    else:
        geneids = [item.strip() for item in geneid.replace('\r', '').split('\n') if item.strip()]

    if not geneids:
        context['info_message'] = 'No matching genes were found for the submitted query.'
        context['blast_results'] = blast_results
        return render(request, 'dupgen_finders.html', context)

    geneid_placeholders = ','.join(['%s'] * len(geneids))
    sql_params = list(geneids)
    if is_all_species:
        sql_query = f"SELECT * FROM Genetype_table WHERE gene1 IN ({geneid_placeholders})"
    else:
        sql_query = f"SELECT * FROM Genetype_table WHERE gene1 IN ({geneid_placeholders}) AND sp_name = %s"
        sql_params.append(sp_data_1)
    with connection.cursor() as cursor:
        cursor.execute(sql_query, sql_params)
        result = cursor.fetchall()
    found_geneids = [row[2] for row in result if len(row) > 2 and row[2]]
    not_found_geneids = [item for item in geneids if item not in found_geneids]
    connection.close()
    context.update({
        'not_found_geneids': not_found_geneids,
        'result': result,
        'blast_results': blast_results,
    })
    if not result and not not_found_geneids:
        context['info_message'] = 'No duplication records were found for the submitted query.'
    return render(request, 'dupgen_finders.html', context)
    return render(request, '../templates/dupgen_finders.html', {
        'not_found_geneids': not_found_geneids,
        'result': result,
        'blast_results': blast_results if query_sequence else None  # 如果没有查询序列，则不返回 blast_results})
    })


def dupgen_job_status(request, job_id):
    if not _dupgen_job_is_valid(job_id):
        return JsonResponse({'status': 'error', 'message': 'Invalid DupGen job id.'}, status=404)

    status = _read_dupgen_job_status(job_id)
    if status.get('status') == 'done':
        status['result_url'] = reverse('dupgen_job_result_url', args=[job_id])
        status['download_url'] = reverse('dupgen_job_download_url', args=[job_id])
        if os.path.isfile(_dupgen_job_blast_path(job_id)):
            status['blast_download_url'] = reverse('dupgen_job_blast_download_url', args=[job_id])
    return JsonResponse(status)


def dupgen_job_download(request, job_id):
    if not _dupgen_job_is_valid(job_id):
        return HttpResponse('Invalid DupGen job id.', status=404)

    result_path = _dupgen_job_result_path(job_id)
    if not os.path.isfile(result_path):
        return HttpResponse('The DupGen result file is not ready.', status=404)

    return FileResponse(
        open(result_path, 'rb'),
        as_attachment=True,
        filename=f'dupgen_all_species_results_{job_id}.tsv',
    )


def dupgen_job_blast_download(request, job_id):
    if not _dupgen_job_is_valid(job_id):
        return HttpResponse('Invalid DupGen job id.', status=404)

    blast_path = _dupgen_job_blast_path(job_id)
    if not os.path.isfile(blast_path):
        return HttpResponse('The BLAST hit file is not ready.', status=404)

    return FileResponse(
        open(blast_path, 'rb'),
        as_attachment=True,
        filename=f'dupgen_all_species_blast_hits_{job_id}.tsv',
    )


def dupgen_job_result(request, job_id):
    if not _dupgen_job_is_valid(job_id):
        return HttpResponse('Invalid DupGen job id.', status=404)

    result_path = _dupgen_job_result_path(job_id)
    headers, rows, truncated, total_rows = _read_tsv_result_table(result_path)
    return render(request, 'job_tsv_result.html', {
        'job_id': job_id,
        'page_title': 'DupGen Results',
        'table_id': 'dupgenJobTable',
        'filename': f'dupgen_selected_rows_{job_id}.txt',
        'empty_message': 'The DupGen result file is not ready or contains no matching records.',
        'result_headers': headers,
        'result': rows,
        'result_count': total_rows,
        'shown_count': len(rows),
        'truncated': truncated,
        'table_limit': JOB_RESULT_TABLE_LIMIT,
        'result_file_ready': os.path.isfile(result_path),
        'download_url': reverse('dupgen_job_download_url', args=[job_id]) if os.path.isfile(result_path) else None,
        'blast_download_url': reverse('dupgen_job_blast_download_url', args=[job_id]) if os.path.isfile(_dupgen_job_blast_path(job_id)) else None,
    })



def hierarchical_alignments_eupl(request):
    return render(request, 'hierarchical_alignments_eupl.html')

def Deinandra_increscens(request):
    return render(request, 'karyotype/Deinandra_increscens.html')

def Taraxacum_mongolicum(request):
    return render(request, 'karyotype/Taraxacum_mongolicum.html')

def ASAK_III(request):
    return render(request, 'karyotype/ASAK-III.html')

def Saussurea_involucrata(request):
    return render(request, 'karyotype/Saussurea_involucrata.html')

def CAAK_II(request):
    return render(request, 'karyotype/CAAK-II.html')

def AAK_II(request):
    return render(request, 'karyotype/AAK-II.html')

def ASAK_XIII(request):
    return render(request, 'karyotype/ASAK-XIII.html')

def Stevia_rebaudiana(request):
    return render(request, 'karyotype/Stevia_rebaudiana.html')

def ASAK_VIII(request):
    return render(request, 'karyotype/ASAK-VIII.html')

def ASAK_IV(request):
    return render(request, 'karyotype/ASAK-IV.html')

def Erigeron_canadensis(request):
    return render(request, 'karyotype/Erigeron_canadensis.html')

def CAAK_I(request):
    return render(request, 'karyotype/CAAK-I.html')

def ASAK_XI(request):
    return render(request, 'karyotype/ASAK-XI.html')

def Senecio_squalidus(request):
    return render(request, 'karyotype/Senecio_squalidus.html')

def Bidens_alba(request):
    return render(request, 'karyotype/Bidens_alba.html')

def ASAK_XVII(request):
    return render(request, 'karyotype/ASAK-XVII.html')

def Lactuca_sativa(request):
    return render(request, 'karyotype/Lactuca_sativa.html')

def Chrysanthemum_lavandulifolium(request):
    return render(request, 'karyotype/Chrysanthemum_lavandulifolium.html')

def Cosmos_bipinnatus(request):
    return render(request, 'karyotype/Cosmos_bipinnatus.html')

def ASAK_VII(request):
    return render(request, 'karyotype/ASAK-VII.html')

def ASAK_VI(request):
    return render(request, 'karyotype/ASAK-VI.html')

def ASAK_XIX(request):
    return render(request, 'karyotype/ASAK-XIX.html')

def Solidago_canadensis(request):
    return render(request, 'karyotype/Solidago_canadensis.html')

def Logfia_minima(request):
    return render(request, 'karyotype/Logfia_minima.html')

def ASAK_X(request):
    return render(request, 'karyotype/ASAK-X.html')

def Arctium_lappa(request):
    return render(request, 'karyotype/Arctium_lappa.html')

def Smallanthus_sonchifolius(request):
    return render(request, 'karyotype/Smallanthus_sonchifolius.html')

def Solidago_caesia(request):
    return render(request, 'karyotype/Solidago_caesia.html')

def ASAK_II(request):
    return render(request, 'karyotype/ASAK-II.html')

def Flaveria_linearis(request):
    return render(request, 'karyotype/Flaveria_linearis.html')

def Pseudognaphalium_luteoalbum(request):
    return render(request, 'karyotype/Pseudognaphalium_luteoalbum.html')

def ASAK_XII(request):
    return render(request, 'karyotype/ASAK-XII.html')

def Cynara_cardunculus(request):
    return render(request, 'karyotype/Cynara_cardunculus.html')

def AAK_I(request):
    return render(request, 'karyotype/AAK_I.html')

def ASAK_XVI(request):
    return render(request, 'karyotype/ASAK-XVI.html')

def CAAK_III(request):
    return render(request, 'karyotype/CAAK-III.html')

def Pulicaria_dysenterica(request):
    return render(request, 'karyotype/Pulicaria_dysenterica.html')

def ASAK_XV(request):
    return render(request, 'karyotype/ASAK-XV.html')

def Tagetes_erecta(request):
    return render(request, 'karyotype/Tagetes_erecta.html')

def ASAK_XVIII(request):
    return render(request, 'karyotype/ASAK-XVIII.html')

def Helianthus_annuus(request):
    return render(request, 'karyotype/Helianthus_annuus.html')

def ASAK_IX(request):
    return render(request, 'karyotype/ASAK-IX.html')

def CAAK_IV(request):
    return render(request, 'karyotype/CAAK-IV.html')

def Carthamus_tinctorius(request):
    return render(request, 'karyotype/Carthamus_tinctorius.html')

def ASAK_I(request):
    return render(request, 'karyotype/ASAK-I.html')

def Cichorium_intybus(request):
    return render(request, 'karyotype/Cichorium_intybus.html')

def Glebionis_coronaria(request):
    return render(request, 'karyotype/Glebionis_coronaria.html')

def ACAK(request):
    return render(request, 'karyotype/ACAK.html')

def ASAK_V(request):
    return render(request, 'karyotype/ASAK-V.html')

def Dahlia_pinnata(request):
    return render(request, 'karyotype/Dahlia_pinnata.html')

def ASAK_XIV(request):
    return render(request, 'karyotype/ASAK-XIV.html')

def CIAK_II(request):
    return render(request, 'karyotype/CIAK-II.html')

def Centaurea_solstitialis(request):
    return render(request, 'karyotype/Centaurea_solstitialis.html')

def CIAK_I(request):
    return render(request, 'karyotype/CIAK-I.html')

def Mikania_micrantha(request):
    return render(request, 'karyotype/Mikania_micrantha.html')

def Ambrosia_trifida(request):
    return render(request, 'karyotype/Ambrosia_trifida.html')
