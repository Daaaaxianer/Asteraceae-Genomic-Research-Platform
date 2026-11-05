"""Refresh the statistics page from actual current database counts."""
import json
from datetime import datetime, timezone
from pathlib import Path
from repair_confirmed_data import database

ROOT = Path(__file__).resolve().parents[1]


def main():
    db = database()
    with db.cursor() as cur:
        cur.execute('SHOW TABLES')
        tables = {r[0] for r in cur.fetchall()}
        sequence = []
        expression = []
        for table in sorted(tables):
            if table.endswith('_cds_pep'):
                cur.execute('SELECT COUNT(*) FROM `' + table + '`')
                sequence.append({'code': table[:-len('_cds_pep')], 'count': cur.fetchone()[0]})
            if table.endswith('_express_table'):
                cur.execute('SHOW COLUMNS FROM `' + table + '`')
                expression.append({'code': table[:-len('_express_table')],
                                   'samples': [r[0] for r in cur.fetchall()
                                               if r[0].lower() not in ('geneid', 'express_index')]})
        metrics = [
            {'label': 'Sequence datasets', 'count': len(sequence), 'scope': 'Current CDS/peptide tables; not a species count'},
            {'label': 'Sequence records', 'count': sum(r['count'] for r in sequence), 'scope': 'Rows in current CDS/peptide tables'},
            {'label': 'Expression datasets', 'count': len(expression), 'scope': 'Tables with expression measurements'},
        ]
        for table, label, scope in [
            ('Metabolomics_plant', 'Plant metabolomics records', 'Compound–species associations; not unique compounds'),
            ('Metabolomics_scent', 'Scent metabolomics records', 'Current table rows; not unique compounds'),
            ('TF_pfam_table', 'Regulatory-family annotations', 'Annotation rows; a gene may have multiple rows'),
            ('m6A_table', 'm6A-related annotations', 'Annotation rows; a gene may have multiple rows'),
            ('function_GF_table', 'Functional-family matches', 'Alignment rows; a gene may have multiple matches'),
            ('Orthofinder_num_table', 'Orthogroup summary rows', 'Historical summary scope; membership totals require version reconciliation'),
            ('Hierarchical_alignment_Eupl_table', 'Eupl alignment rows', 'Current multiple-genome alignment table'),
            ('Hierarchical_alignment_Hean_table', 'Hean alignment rows', 'Current multiple-genome alignment table'),
            ('Hierarchical_alignment_Lssa_all_table', 'Lssa alignment rows', 'Current multiple-genome alignment table'),
            ('Hierarchical_alignment_Vivi_table', 'Vivi alignment rows', 'Current multiple-genome alignment table'),
        ]:
            if table not in tables:
                continue
            cur.execute('SELECT COUNT(*) FROM `' + table + '`')
            metrics.append({'label': label, 'count': cur.fetchone()[0], 'scope': scope})
    db.close()
    payload = {'verified_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M'),
               'metrics': metrics, 'sequence_datasets': sequence, 'expression_datasets': expression}
    path = ROOT / 'browse/data/current_statistics.json'
    path.parent.mkdir(exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)
    print(json.dumps({'datasets': len(sequence), 'expression': len(expression), 'metrics': metrics}), flush=True)


if __name__ == '__main__':
    main()
