"""Gene-centred AGRP resource queries, using column names rather than tuple offsets."""

import logging
import math
import re
from pathlib import Path
from urllib.parse import quote

from django.db import connection

logger = logging.getLogger(__name__)
LIMIT = 1000
ANCESTORS = (
    'AAKI', 'AAKII', 'AAKIII', 'ACAK', 'CAAKI', 'CAAKII', 'CAAKIII', 'CAAKIV',
    'CIAKI', 'CIAKII',
) + tuple('ASAK' + n for n in (
    'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII',
    'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX',
))


def exact_token(value, token):
    """Match delimited IDs without matching a longer gene ID or transcript ID."""
    return bool(re.search(r'(?<![A-Za-z0-9_.-])' + re.escape(token) +
                          r'(?![A-Za-z0-9_.-])', str(value or '')))


def ko_terms(value):
    return list(dict.fromkeys(re.findall(r'(?<![A-Za-z0-9])K\d{5}(?!\d)', str(value or ''))))


def cell(value, url=None):
    result = {'value': '' if value is None else value}
    if url:
        result['url'] = url
    return result


def gene_cell(value):
    value = str(value or '')
    return cell(value, '/browse/gene_' + quote(value, safe='') + '/')


def named_rows(records, fields):
    result = []
    for record in records:
        values = {key.lower(): value for key, value in record.items()}
        result.append([cell(values.get(field.lower())) for field in fields])
    return result


class SwitchData:
    def __init__(self, db=None):
        self.db = db or connection
        self.schemas = {}

    def query(self, sql, params=()):
        with self.db.cursor() as cursor:
            cursor.execute(sql, params)
            fields = [item[0] for item in cursor.description]
            return [dict(zip(fields, row)) for row in cursor.fetchall()]

    def schema(self, table):
        if table not in self.schemas:
            rows = self.query(
                'SELECT COLUMN_NAME FROM information_schema.COLUMNS '
                'WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s '
                'ORDER BY ORDINAL_POSITION', [table])
            self.schemas[table] = [row['COLUMN_NAME'] for row in rows]
        return self.schemas[table]

    def select(self, table, where, params=(), limit=LIMIT + 1):
        if not self.schema(table):
            return []
        if not re.fullmatch(r'[A-Za-z0-9_]+', table):
            raise ValueError('Invalid resource table')
        return self.query('SELECT * FROM `' + table + '` WHERE ' + where + ' LIMIT %s',
                          list(params) + [limit])


def expression_data(data, species, gene):
    table = species + '_express_table'
    columns = data.schema(table)
    key = next((c for c in columns if c.lower() in ('geneid', 'gene_id')), None)
    if not key:
        return [], []
    rows = data.select(table, '`' + key + '` = %s', [gene])
    # Keep every installed sample and every expression unit (FPKM, TPM, etc.).
    return columns, named_rows(rows, columns)


def build_switch_context(gene, species, sequence_rows, root, db=None):
    data = SwitchData(db)
    sections = []

    def section(key, title, columns=(), rows=(), note='', links=()):
        item = {'id': 'table_' + key, 'plot_id': 'table_' + key + '_plotdata',
                'anchor': 'switch_' + key, 'title': title,
                'columns': list(columns), 'rows': list(rows)[:LIMIT], 'note': note,
                'links': list(links), 'limited': len(rows) > LIMIT,
                'empty_message': 'No associated records are available for this gene.'}
        sections.append(item)
        return item

    def optional(item, work):
        try:
            work()
        except Exception:
            logger.exception('AGRP-Switch resource failed: %s / %s', gene, item['title'])
            item['empty_message'] = 'This resource is temporarily unavailable. Please try again later.'
            item['unavailable'] = True

    sequence = sequence_rows[0]
    section('protein', 'Protein sequence', ['Gene', 'Protein sequence', 'Length'],
            [[cell(gene), cell(sequence[3]), cell(sequence[5])]])
    section('sequence', 'Gene sequence (CDS)', ['Gene', 'CDS', 'Length', 'GC content (%)'],
            [[cell(gene), cell(sequence[2]), cell(sequence[4]), cell(sequence[6])]],
            'Coding sequence (CDS). Introns and flanking genomic DNA are not included.' +
            (' This source annotation is partial; the original CDS is preserved without padding.'
             if species == 'Desu' and len(str(sequence[2])) % 3 else ''))

    annotation = section('annotation', 'GO annotations and protein domains',
                         ['Gene', 'Length', 'Analysis', 'Description', 'Start', 'End', 'IPR', 'GO'])
    optional(annotation, lambda: annotation.update(rows=named_rows(data.select(
        species + '_interproscan_table', '`gene_id` = %s', [gene]),
        ['gene_id', 'length', 'analysis', 'description', 'start', 'end', 'ipr', 'go'])))

    kegg = section('kegg', 'KEGG pathways', ['Gene', 'KO', 'Definition'], note=
                   'Open a KO entry to view its KEGG pathway memberships. '
                   'A KO annotation alone does not establish activity in a pathway.')
    kos = []

    def load_kegg():
        for row in data.select('kegg_table', '`gene_id` = %s AND `sp_name` = %s', [gene, species]):
            terms = ko_terms(row.get('ko'))
            kos.extend(k for k in terms if k not in kos)
            if terms:
                kegg['rows'].append([cell(gene), cell(row['ko'],
                    'https://www.kegg.jp/entry/' + quote(terms[0])), cell(row.get('definition'))])
    optional(kegg, load_kegg)

    gff = section('gff', 'Genomic elements and gene position',
                  ['Chromosome', 'Start', 'End', 'Strand', 'Original gene ID', 'AGRP gene ID', 'Ordinal'],
                  links=[{'label': 'Browse transposable element resources', 'url': '/browse/TE_index1'}])
    optional(gff, lambda: gff.update(rows=named_rows(data.select('Hierarchicalgene', '`new_gene` = %s', [gene]),
        ['chromosome', 'start', 'end', 'strend', 'old_gene', 'new_gene', 'num'])))

    duplication = section('duplication', 'Gene duplication type',
                          ['Gene 1', 'Location 1', 'Gene 2', 'Location 2', 'E-value', 'Duplication type'])
    optional(duplication, lambda: duplication.update(rows=named_rows(data.select(
        'Genetype_table', '`gene1` = %s OR `gene2` = %s', [gene, gene]),
        ['gene1', 'Location1', 'gene2', 'Location2', 'E-value', 'Type'])))

    blocks = section('blocks', 'Blocks information',
                     ['Block', 'Query genome', 'Query chromosome', 'Reference genome',
                      'Reference chromosome', 'Matches', 'P-value'])
    dotplots = section('dotplot', 'Dotplots information', ['Block', 'Gene 1', 'Gene 2', 'Gene 1 ordinal', 'Gene 2 ordinal'],
                       note='The plot shows gene ordinals within one associated syntenic block. '
                            'The queried gene is highlighted. Other blocks are listed below.')
    ks = section('ks', 'Ks analysis', ['Block', 'Gene 1', 'Gene 2', 'Ka', 'Ks', 'Ka/Ks'],
                 note='Precomputed values for syntenic gene pairs. Missing or negative estimates are shown as a dash.')

    def load_blocks():
        pairs = data.select(species + '_blocksyn_pair', '`Gene1` = %s OR `Gene2` = %s', [gene, gene])
        ids = list(dict.fromkeys(row['unique_id'] for row in pairs))
        if ids:
            records = data.select(species + '_blocksyn_block', '`unique_id` IN (' + ','.join(['%s'] * len(ids)) + ')', ids)
            blocks['rows'] = named_rows(records, ['unique_id', 'Query_Genome', 'Query_Chromosome',
                'Reference_Genome', 'Reference_Chromosome', 'Number_matches', 'P-value'])
            for query, reference in dict.fromkeys((r['Query_Genome'], r['Reference_Genome']) for r in records):
                dotplots['links'].append({'label': query + ' / ' + reference + ' genome view',
                    'url': '/browse/genome_synteny_viewer/' + quote(query) + '_' + quote(reference) + '/'})
            plot_pairs = data.select(species + '_blocksyn_pair', '`unique_id` = %s', [ids[0]], limit=4001)
            points = []
            for r in plot_pairs[:4000]:
                try:
                    points.append({'x': float(r['Gene1_num']), 'y': float(r['Gene2_num']),
                        'selected': gene in (r['Gene1'], r['Gene2']),
                        'label': str(r['Gene1']) + ' / ' + str(r['Gene2'])})
                except (TypeError, ValueError):
                    continue
            if points:
                dotplots['plot'] = {'block': ids[0], 'points': points,
                    'x_label': ids[0].split('_')[0] + ' gene ordinal',
                    'y_label': ids[0].split('_')[2] + ' gene ordinal'}
                dotplots['plot_limited'] = len(plot_pairs) > 4000
        dotplots['rows'] = named_rows(pairs, ['unique_id', 'Gene1', 'Gene2', 'Gene1_num', 'Gene2_num'])
        for row in pairs:
            estimates = []
            for field in ['Ka', 'Ks', 'Ka_Ks']:
                try:
                    value = float(row.get(field))
                    estimates.append(value if math.isfinite(value) and value >= 0 else '-')
                except (TypeError, ValueError):
                    estimates.append('-')
            ks['rows'].append([cell(row['unique_id']), gene_cell(row['Gene1']), gene_cell(row['Gene2'])] +
                               [cell(v) for v in estimates])
        for item in (blocks, dotplots, ks):
            item['limited'] = len(pairs) > LIMIT
            item['rows'] = item['rows'][:LIMIT]
    optional(blocks, load_blocks)
    if blocks.get('unavailable'):
        for item in (dotplots, ks):
            item.update(unavailable=True, empty_message=blocks['empty_message'])

    mgas = section('mgas', 'MGAs results', ['Reference', 'Alignment', 'Column', 'Gene'],
                   note='Genes in multiple-genome alignment rows containing the queried gene.')

    def load_mgas():
        for reference in ['Hean', 'Lssa_all', 'Vivi', 'Eupl']:
            table = 'Hierarchical_alignment_' + reference + '_table'
            columns = data.schema(table)
            target_columns = [c for c in columns if re.fullmatch(re.escape(species) + r'_?\d+', c)]
            if not target_columns:
                continue
            where = ' OR '.join('`' + c + '` LIKE %s' for c in target_columns)
            records = data.select(table, where, ['%' + gene + '%'] * len(target_columns), limit=51)
            for index, row in enumerate(records):
                if not any(exact_token(row[c], gene) for c in target_columns):
                    continue
                lower = {c.lower(): v for c, v in row.items()}
                alignment = lower.get('hhh_number', lower.get('number', index + 1))
                for col in columns:
                    value = str(row[col] or '').strip()
                    if re.search(r'[A-Za-z][A-Za-z0-9]*[gG]\d+', value):
                        mgas['rows'].append([cell('Arla' if reference == 'Lssa_all' else reference),
                                             cell(alignment), cell(col), cell(value)])
            mgas['links'].append({'label': ('Arla' if reference == 'Lssa_all' else reference) + '-MGAs',
                'url': '/browse/hierarchical_alignments_' + reference})
            if len(records) > 50:
                mgas['limited'] = True
    optional(mgas, load_mgas)

    ancestral = section('ancestral', 'Ancestral genome', ['Alignment source', 'Alignment row', 'Ancestor', 'Ancestral gene'],
                         note='Ancestral gene relationships recorded in the installed combined alignments.')

    def load_ancestral():
        folder = Path(root) / 'static' / 'ancestral_combined'
        seen = set()
        for path in sorted(folder.glob('*_all_with_combined.txt')):
            with path.open(encoding='utf-8', errors='replace') as handle:
                for line_number, line in enumerate(handle, 1):
                    if gene not in line or not exact_token(line, gene):
                        continue
                    for token in re.findall(r'[A-Za-z][A-Za-z0-9]*[gG]\d+(?:\.\d+)?', line):
                        code = next((c for c in sorted(ANCESTORS, key=len, reverse=True)
                                     if token.upper().startswith(c)), None)
                        if not code:
                            continue
                        key = (path.name, line_number, token)
                        if key in seen:
                            continue
                        seen.add(key)
                        ancestral['rows'].append([cell(path.name.split('_')[0]), cell(line_number), cell(code), cell(token)])
        for code in dict.fromkeys(row[2]['value'] for row in ancestral['rows']):
            for suffix in ['cds', 'pep', 'lens', 'new.gff']:
                path = Path(root) / 'static' / 'ancestral_data' / code / (code + '.' + suffix)
                if path.is_file():
                    ancestral['links'].append({'label': code + ' ' + suffix,
                        'url': '/static/ancestral_data/' + code + '/' + code + '.' + suffix})
        ancestral['actions'] = [{'label': 'Search ancestral genomes with this protein',
            'url': '/browse/ancestral_chromosome', 'fields': {
                'query_sequence': '>' + gene + '\n' + str(sequence[3]), 'patten': 'blastp',
                'search_mode': 'candidate', 'species_data': 'ALL_ANCESTRAL_DATASETS',
                'e_value': '1e-5', 'score_1': '0', 'identity_1': '0'}}]
    optional(ancestral, load_ancestral)

    orthogroups = section('block_ortho', 'Orthogroups', ['Orthogroup', 'Species', 'Gene'],
                          note='Members of orthogroups containing the queried gene.')

    def load_orthogroups():
        groups = data.select('Orthofinder_genes_table', '`gene_id` = %s', [gene])
        names = list(dict.fromkeys(r['orthogroup'] for r in groups))
        if names:
            rows = data.select('Orthofinder_genes_table', '`orthogroup` IN (' + ','.join(['%s'] * len(names)) + ')', names)
            orthogroups['rows'] = [[cell(r['orthogroup']), cell(r['species']), gene_cell(r['gene_id'])] for r in rows[:LIMIT]]
            orthogroups['limited'] = len(rows) > LIMIT
    optional(orthogroups, load_orthogroups)

    family = section('gene_family', 'Gene family identification',
                     ['Gene', 'Family', 'Reference gene', 'Identity (%)', 'E-value', 'Score'])

    def load_family():
        matches = data.select('function_GF_table', '`gene_id` = %s', [gene])
        names = list(dict.fromkeys(r['function_name'] for r in matches
                                   if r.get('function_name') not in (None, '', '.', '-')))
        if not names:
            return
        rows = data.select('function_GF_table', '`query_genome` = %s AND `function_name` IN (' +
                           ','.join(['%s'] * len(names)) + ')', [species] + names)
        # Use the live column names; legacy table versions differ outside these core fields.
        family['columns'] = [c for c in data.schema('function_GF_table') if c != 'hhh_number']
        family['rows'] = named_rows(rows[:LIMIT], family['columns'])
        family['limited'] = len(rows) > LIMIT
    optional(family, load_family)

    expression = section('expression', 'Gene expression')

    def load_expression():
        columns, rows = expression_data(data, species, gene)
        expression.update(columns=columns, rows=rows)
        expression['note'] = 'Sample accessions and expression units are shown as recorded in the expression dataset.'
    optional(expression, load_expression)

    metabolic = section('metabolic', 'Metabolomics-related information',
                         ['Source', 'Association', 'Compound', 'CID', 'Species', 'CAS', 'KO'],
                         note='Recorded gene links and shared-KO candidates are distinguished. '
                              'A shared KO is a candidate association, not experimental validation.')

    def load_metabolic():
        for table, label in [('Metabolomics_plant', 'Plant'), ('Metabolomics_scent', 'Floral scent')]:
            if not data.schema(table):
                continue
            records = data.select(table, '`Gene_IDs` LIKE %s', ['%' + gene + '%'])
            limited = len(records) > LIMIT
            if kos:
                candidates = data.select(table, '`KO_Number` REGEXP %s', [
                    '(^|[^A-Za-z0-9])(' + '|'.join(kos) + ')([^0-9]|$)'])
                limited = limited or len(candidates) > LIMIT
                records += candidates
            seen = set()
            for row in records:
                direct = exact_token(row.get('Gene_IDs'), gene)
                if not direct and not set(kos).intersection(ko_terms(row.get('KO_Number'))):
                    continue
                compound = row.get('Synonyms') or row.get('Compounds') or row.get('IUPAC_Name')
                cid = str(row.get('CID') or '')
                key = (cid, str(compound), row.get('Species'), row.get('CAS'))
                if key in seen:
                    continue
                seen.add(key)
                url = 'https://pubchem.ncbi.nlm.nih.gov/compound/' + cid if cid.isdigit() else None
                metabolic['rows'].append([cell(label), cell('Recorded gene link' if direct else 'Shared KO (candidate)'),
                    cell(compound), cell(cid, url), cell(row.get('Species')), cell(row.get('CAS')), cell(row.get('KO_Number'))])
            if limited:
                metabolic['limited'] = True
        metabolic['rows'].sort(key=lambda r: r[1]['value'] != 'Recorded gene link')
    optional(metabolic, load_metabolic)

    # Preserve additional resources already exposed by the original Switch page.
    tf = section('tf', 'Transcription factors and regulatory families',
                 ['Gene', 'Type', 'Family', 'HMM accession', 'HMM name', 'Score', 'Clan'])
    optional(tf, lambda: tf.update(rows=named_rows(data.select('TF_pfam_table', '`gene_id` = %s', [gene]),
        ['gene_id', 'type', 'family', 'hmm_acc', 'hmm_name', 'score', 'clan'])))
    events = section('event_genes', 'Event-related genes', ['Gene 1', 'Gene 2', 'Event'])
    optional(events, lambda: events.update(rows=named_rows(data.select('Event_genes_table', '`gene1` = %s OR `gene2` = %s',
        [gene, gene]), ['gene1', 'gene2', 'event'])))

    for item in sections:
        if len(item['rows']) > LIMIT:
            item['limited'] = True
            item['rows'] = item['rows'][:LIMIT]
    return {'switch_gene': gene, 'switch_species': species, 'switch_sections': sections,
            'cds_pep_infor': sequence_rows}
