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


def _subject_gene_id_from_blast_fields(fields):
    stitle = ''
    if len(fields) > 13:
        stitle = fields[12]
    elif len(fields) == 13 and _normalize_ancestor_code(fields[12]) not in ANCESTRAL_DATASETS:
        stitle = fields[12]
    return _extract_gene_id_from_text(stitle, fields[1]) or fields[1]
