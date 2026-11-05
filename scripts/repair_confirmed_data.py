"""Apply only source-verified Desu CDS and canonical Tako download repairs.

Run on the project server with --backup-dir /private/path; add --apply to write.
Original records/files are retained before any persistent change.
"""
import argparse
import ast
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil

import pymysql
from Bio import SeqIO
from Bio.Seq import Seq

ROOT = Path(__file__).resolve().parents[1]


def database():
    tree = ast.parse((ROOT / 'LGBP/settings.py').read_text())
    config = next(ast.literal_eval(n.value)['default'] for n in tree.body
                  if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and
                                                       t.id == 'DATABASES' for t in n.targets))
    return pymysql.connect(host=config['HOST'], user=config['USER'], password=config['PASSWORD'],
                           database=config['NAME'], charset='utf8mb4', autocommit=False)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--backup-dir', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    backup = args.backup_dir.resolve()
    assert not str(backup).startswith(str(ROOT.resolve()) + os.sep), 'Backup must be outside public project'
    if args.apply:
        backup.mkdir(parents=True, exist_ok=True, mode=0o700)
    db = database()
    with db.cursor() as cur:
        cur.execute('SELECT * FROM Desu_cds_pep')
        fields = [c[0] for c in cur.description]
        old_rows = cur.fetchall()
        records = [dict(zip(fields, row)) for row in old_rows]
    source = {}
    conflicts = set()
    for record in SeqIO.parse(ROOT / 'static/Species_data/Desu.cds', 'fasta'):
        seq = str(record.seq).upper()
        if record.id in source and source[record.id] != seq:
            conflicts.add(record.id)
        source[record.id] = seq
    peptides = {record.id: str(record.seq) for record in
                SeqIO.parse(ROOT / 'static/Species_data/Desu.pep', 'fasta')}
    changes = []
    partial = []
    for row in records:
        gene = row['gene_id']
        assert gene in source and gene not in conflicts, gene
        dna = source[gene]
        assert set(dna) <= set('ACGTRYSWKMBDHVN') and dna, gene
        assert row['pep_sequence'] == peptides[gene], gene
        if len(dna) % 3:
            partial.append(gene)
        gc = round(100 * (dna.count('G') + dna.count('C')) / len(dna), 2)
        changes.append((gene, dna, len(dna), gc, digest(row['cds_sequence']), digest(row['pep_sequence'])))
    assert len(records) == len({r['gene_id'] for r in records}) == 33093
    assert len(partial) == 100
    with db.cursor() as cur:
        cur.execute('SELECT gene_id,cds_sequence,pep_sequence FROM Tako_cds_pep ORDER BY gene_id')
        tako = cur.fetchall()
        cur.execute("SELECT chromosome,start,end,strend,old_gene,new_gene,num FROM Hierarchicalgene "
                    "WHERE new_gene LIKE 'Tako%' ORDER BY chromosome,num")
        coordinates = cur.fetchall()
    assert len(tako) == len(coordinates) == 45406
    assert {r[0] for r in tako} == {r[5] for r in coordinates}
    for gene, dna, pep in tako:
        assert str(Seq(dna).translate()).rstrip('*') == pep.rstrip('*'), gene
    lens = {}
    counts = {}
    for chrom, start, end, strand, old, gene, num in coordinates:
        assert int(start) <= int(end) and str(strand) in ('+', '-'), gene
        lens[chrom] = max(lens.get(chrom, 0), int(num))
        counts[chrom] = counts.get(chrom, 0) + 1
    assert lens == counts
    print(json.dumps({'Desu_rows': len(records), 'Desu_partial_source_CDS': len(partial),
                      'Tako_rows': len(tako), 'Tako_chromosomes': lens, 'apply': args.apply}), flush=True)
    if not args.apply:
        db.rollback()
        return
    old_backup = backup / 'Desu_cds_pep.before.json.gz'
    assert not old_backup.exists(), 'Refusing to overwrite original backup'
    with gzip.open(old_backup, 'wt', encoding='utf-8') as handle:
        json.dump({'columns': fields, 'rows': old_rows, 'partial_source_gene_ids': partial}, handle)
    stage = backup / 'tako_verified'
    stage.mkdir()
    for suffix, seq_column in [('cds', 1), ('pep', 2)]:
        with (stage / ('Tako.' + suffix)).open('w') as handle:
            for row in tako:
                handle.write('>' + row[0] + '\n' + row[seq_column] + '\n')
        assert {r.id: str(r.seq) for r in SeqIO.parse(stage / ('Tako.' + suffix), 'fasta')} == {
            r[0]: r[seq_column] for r in tako}
    with (stage / 'Tako.new.gff').open('w') as handle:
        for row in coordinates:
            handle.write('\t'.join(map(str, row)) + '\n')
    with (stage / 'Tako.lens').open('w') as handle:
        for chrom in sorted(lens):
            handle.write(str(chrom) + '\t' + str(lens[chrom]) + '\n')
    for file in stage.iterdir():
        shutil.copy2(ROOT / 'static/Species_data' / file.name, backup / (file.name + '.before'))
    try:
        with db.cursor() as cur:
            cur.execute('CREATE TEMPORARY TABLE confirmed_desu_fix ('
                        'gene_id VARCHAR(255) PRIMARY KEY, cds LONGTEXT, n INT, gc DOUBLE, '
                        'old_sha CHAR(64), pep_sha CHAR(64)) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci')
            cur.executemany('INSERT INTO confirmed_desu_fix VALUES (%s,%s,%s,%s,%s,%s)', changes)
            cur.execute('UPDATE Desu_cds_pep d JOIN confirmed_desu_fix f ON d.gene_id=f.gene_id '
                        'SET d.cds_sequence=f.cds,d.len_cds_seq=f.n,d.gc_content=f.gc '
                        'WHERE SHA2(d.cds_sequence,256)=f.old_sha AND SHA2(d.pep_sequence,256)=f.pep_sha')
            updated = cur.rowcount
            cur.execute('SELECT COUNT(*) FROM Desu_cds_pep d JOIN confirmed_desu_fix f ON d.gene_id=f.gene_id '
                        'WHERE BINARY d.cds_sequence=BINARY f.cds AND d.len_cds_seq=f.n '
                        'AND ABS(d.gc_content-f.gc)<0.00001 AND SHA2(d.pep_sequence,256)=f.pep_sha')
            assert cur.fetchone()[0] == 33093, 'Post-update verification failed'
        db.commit()
    except BaseException:
        db.rollback()
        raise
    print('DESU_COMMITTED', updated, flush=True)
    for file in sorted(stage.iterdir()):
        target = ROOT / 'static/Species_data' / file.name
        temporary = target.with_name(target.name + '.confirmed.tmp')
        shutil.copy2(file, temporary)
        os.replace(temporary, target)
        assert hashlib.sha256(target.read_bytes()).digest() == hashlib.sha256(file.read_bytes()).digest()
        print('TAKO_PUBLISHED', file.name, target.stat().st_size, flush=True)
    db.close()


if __name__ == '__main__':
    main()
