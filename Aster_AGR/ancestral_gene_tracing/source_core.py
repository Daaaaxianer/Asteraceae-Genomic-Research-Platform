"""Computational functions extracted from AGRP browse/views.py.

Original author attribution: yuzijian; see SOURCE_MANIFEST.json at the module root.
Functions are copied without body changes. The CLI configures path_get and settings.
"""
import os
import re
import json
import csv
import glob
import html
import subprocess
from types import SimpleNamespace

settings = SimpleNamespace()

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


ANCESTRAL_DATASETS = (
    'AAKI', 'AAKII', 'AAKIII', 'ACAK',
    'ASAKI', 'ASAKII', 'ASAKIII', 'ASAKIV', 'ASAKV', 'ASAKVI', 'ASAKVII',
    'ASAKVIII', 'ASAKIX', 'ASAKX', 'ASAKXI', 'ASAKXII', 'ASAKXIII',
    'ASAKXIV', 'ASAKXV', 'ASAKXVI', 'ASAKXVII', 'ASAKXVIII', 'ASAKXIX',
    'CAAKI', 'CAAKII', 'CAAKIII', 'CAAKIV', 'CIAKI', 'CIAKII',
)


SEQUENCE_TYPE_PROTEIN = 'prot'


SEQUENCE_TYPE_NUCLEOTIDE = 'nucl'


COMBINED_TRACE_TABLES = {
    'Fli': 'Fli_all_with_combined.txt',
    'Gehy': 'Gehy_all_with_combined.txt',
    'Arla': 'Arla_all_with_combined.txt',
}


TRACEABLE_EXTANT_SPECIES = tuple(COMBINED_TRACE_TABLES.keys())


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


def _resolve_gene_species(geneid):
    for species in sorted(INTERPROSCAN_SPECIES, key=len, reverse=True):
        if geneid.startswith(species):
            return species
    return None


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


def _blast_outfmt_with_title():
    return '6 qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore stitle'


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
