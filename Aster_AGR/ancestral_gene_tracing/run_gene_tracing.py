#!/usr/bin/env python3
"""Standalone adapter: best extant hit -> recorded ancestral relationships."""
import argparse
import csv
import json
import math
from pathlib import Path
from types import SimpleNamespace

import source_core as core


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--query', type=Path, help='Query FASTA; search the Fli, Gehy and Arla databases.')
    mode.add_argument('--blast-results', type=Path, help='Existing raw 12-column or 12-column-plus-title BLAST results.')
    parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parent / 'reference_data',
                        help='Root containing static/ancestral_combined and optional website database/GFF directories.')
    parser.add_argument('--db', action='append', metavar='SPECIES=PREFIX',
                        help='Database override; query mode requires Fli, Gehy and Arla together when overrides are supplied.')
    parser.add_argument('--blast-bin-dir', type=Path)
    parser.add_argument('--sequence-type', choices=['prot', 'nucl'], default='prot')
    parser.add_argument('--evalue', type=float, default=1e-5)
    parser.add_argument('--min-score', type=float, default=100)
    parser.add_argument('--min-identity', type=float, default=60)
    parser.add_argument('--flank', type=int, default=5, help='Neighboring combined-table rows/columns in the context payload.')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        if any(not math.isfinite(value) or value < 0 for value in [args.evalue, args.min_score, args.min_identity]) or args.flank < 0:
            raise ValueError('Use finite nonnegative thresholds and a nonnegative flank.')
        input_file = args.query or args.blast_results
        if not input_file.is_file():
            raise FileNotFoundError(input_file)
        output = args.out.resolve()
        names = ['trace_results.json', 'trace_results.tsv', 'metadata.json', 'tracing_payload.json', 'decobrowse_payload.json']
        if any((output / name).exists() for name in names):
            raise ValueError('The output directory contains previous results; choose a new --out directory.')
        core.path_get = str(args.project_root.resolve())
        core.settings = SimpleNamespace(BASE_DIR=str(args.project_root.resolve()),
            NCBI_BLAST_BIN_DIR=str(args.blast_bin_dir.resolve()) if args.blast_bin_dir else None)
        db_paths = None
        if args.query:
            core._validate_sequence_type_for_search(str(args.query.resolve()), args.sequence_type)
            if args.db:
                databases = {}
                for item in args.db:
                    code, separator, prefix = item.partition('=')
                    if not separator or code not in core.TRACEABLE_EXTANT_SPECIES or not prefix or code in databases:
                        raise ValueError(f'Invalid or duplicate SPECIES=PREFIX: {item}')
                    databases[code] = str(Path(prefix).resolve())
                if set(databases) != set(core.TRACEABLE_EXTANT_SPECIES):
                    raise ValueError('Supply database prefixes for Fli, Gehy and Arla together.')
                db_paths = [databases[code] for code in core.TRACEABLE_EXTANT_SPECIES]
            else:
                db_paths = core._traceable_species_db_paths(args.sequence_type)
        if not any(Path(path).is_file() for path in core._combined_trace_table_paths().values()):
            raise FileNotFoundError('No combined reference tables found under the supplied --project-root.')
        output.mkdir(parents=True, exist_ok=True)
        blast_file = args.blast_results.resolve() if args.blast_results else output / 'extant_search.raw.tsv'
        if args.query:
            core.run_ncbi_blast(str(args.query.resolve()), args.sequence_type, args.evalue,
                str(blast_file), db_paths=db_paths, alias_name=f'traceable_species_{args.sequence_type}',
                max_target_seqs=50)
        best_hits, total, kept = core._select_best_hits(str(blast_file), args.evalue, args.min_score, args.min_identity)
        results, traced_queries, sources = core._trace_best_hits_to_ancestors(best_hits)
        metadata = {'search_mode': 'best_hit_trace', 'mode_label': 'Ancestral Gene Tracing',
            'total_hits': total, 'filtered_hits': kept, 'best_hit_count': len(best_hits),
            'traced_query_count': len(traced_queries), 'trace_result_count': len(results),
            'available_reference_sets': sources, 'searched_species': list(core.TRACEABLE_EXTANT_SPECIES),
            'e_value_cutoff': args.evalue, 'score_cutoff': args.min_score,
            'identity_cutoff': args.min_identity,
            'input_mode': 'search' if args.query else 'existing_search_results'}
        payloads = {'trace_results.json': results, 'metadata.json': metadata,
            'tracing_payload.json': core.build_ancestral_trace_payload(results, metadata),
            'decobrowse_payload.json': core.build_trace_decobrowse_payload(results, flank=args.flank)}
        for name, value in payloads.items():
            (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        fields = ['query_id', 'best_gene', 'matched_species', 'reference_set', 'ancestor_gene_summary',
                  'identity', 'length', 'evalue', 'bitscore', 'status']
        with (output / 'trace_results.tsv').open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, delimiter='\t', extrasaction='ignore')
            writer.writeheader()
            writer.writerows(results)
        print(f'{len(best_hits)} best-hit queries; {len(traced_queries)} queries with recorded ancestral relationships.')
        print(output)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(2, f'Error: {error}\n')


if __name__ == '__main__':
    main()
