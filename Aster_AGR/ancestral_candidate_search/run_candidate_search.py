#!/usr/bin/env python3
"""Standalone file-based adapter for the webpage's candidate-search functions."""
import argparse
import json
import math
from pathlib import Path
from types import SimpleNamespace

import source_core as core


def specifications(items, allowed):
    result = {}
    for item in items or []:
        key, separator, value = item.partition('=')
        if not separator or key not in allowed or not value or key in result:
            raise ValueError(f'Use a unique CODE=PATH specification; invalid value: {item}')
        result[key] = str(Path(value).resolve())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--query', type=Path, help='Query FASTA; protein uses DIAMOND, nucleotide uses BLASTN.')
    mode.add_argument('--raw-results', action='append', metavar='ANCESTOR=TSV',
                      help='Filter existing raw 12-column or 12-column-plus-title search results; repeat for ancestors.')
    parser.add_argument('--sequence-type', choices=['prot', 'nucl'], default='prot')
    parser.add_argument('--ancestors', nargs='+', help='Ancestor codes, or ALL; query-mode default: AAKI.')
    parser.add_argument('--db', action='append', metavar='ANCESTOR=PREFIX', help='Override a search database prefix.')
    parser.add_argument('--project-root', type=Path, default=Path.cwd(), help='AGRP project root for default database paths.')
    parser.add_argument('--diamond', help='DIAMOND executable path.')
    parser.add_argument('--blast-bin-dir', type=Path, help='Directory containing NCBI BLAST+ executables.')
    parser.add_argument('--evalue', type=float, default=1e-5)
    parser.add_argument('--min-score', type=float, default=100)
    parser.add_argument('--min-identity', type=float, default=60)
    parser.add_argument('--out', type=Path, required=True, help='Output directory; existing named results are not replaced.')
    args = parser.parse_args()
    try:
        for value in [args.evalue, args.min_score, args.min_identity]:
            if not math.isfinite(value) or value < 0:
                raise ValueError('Thresholds must be finite, nonnegative numbers.')
        raw = specifications(args.raw_results, core.ANCESTRAL_DATASETS)
        databases = specifications(args.db, core.ANCESTRAL_DATASETS)
        ancestors = args.ancestors or (list(raw) if raw else ['AAKI'])
        if ancestors == ['ALL']:
            ancestors = list(core.ANCESTRAL_DATASETS)
        if not ancestors or len(set(ancestors)) != len(ancestors) or any(code not in core.ANCESTRAL_DATASETS for code in ancestors):
            raise ValueError('Select unique registered ancestor codes, or ALL.')
        if raw and any(code not in raw for code in ancestors):
            raise ValueError('Every selected ancestor needs a --raw-results input.')
        for path in raw.values():
            if not Path(path).is_file():
                raise FileNotFoundError(path)
        if args.query and not args.query.is_file():
            raise FileNotFoundError(args.query)
        output = args.out.resolve()
        reserved = ['candidate_hits.tsv', 'metadata.json', 'alignment_payload.json']
        if any((output / name).exists() for name in reserved):
            raise ValueError('The output directory contains previous results; choose a new --out directory.')
        output.mkdir(parents=True, exist_ok=True)
        core.path_get = str(args.project_root.resolve())
        core.settings = SimpleNamespace(DIAMOND_BIN=args.diamond,
            NCBI_BLAST_BIN_DIR=str(args.blast_bin_dir.resolve()) if args.blast_bin_dir else None)
        default_protein_prefix = core.get_ancestral_db_prefix
        core.get_ancestral_db_prefix = lambda code: databases.get(code, default_protein_prefix(code))
        if args.query:
            core._validate_sequence_type_for_search(str(args.query.resolve()), args.sequence_type)
        total_hits = filtered_hits = 0
        result_file = output / 'candidate_hits.tsv'
        for index, ancestor in enumerate(ancestors):
            source = raw.get(ancestor)
            if source is None:
                source = str(output / f'{ancestor}.raw.tsv')
                if args.sequence_type == 'prot':
                    core.run_diamond(str(args.query.resolve()), 'prot', ancestor, args.evalue, source)
                else:
                    prefix = databases.get(ancestor, core.get_ancestral_nucl_db_prefix(ancestor))
                    core.run_ncbi_blast(str(args.query.resolve()), 'nucl', args.evalue,
                                        source, db_value=prefix, max_target_seqs=50)
            seen, kept = core.write_filtered_blast_result_file(source, str(result_file),
                args.evalue, args.min_score, args.min_identity, ancestor=ancestor,
                mode='w' if index == 0 else 'a')
            total_hits += seen
            filtered_hits += kept
        metadata = {'search_mode': 'candidate', 'mode_label': 'Ancestral Candidate Search',
            'query_name': args.query.stem if args.query else 'existing_search_results',
            'sequence_type': args.sequence_type, 'species_codes': ancestors,
            'e_value_cutoff': args.evalue, 'score_cutoff': args.min_score,
            'identity_cutoff': args.min_identity, 'total_hits': total_hits,
            'filtered_hits': filtered_hits, 'result_file': result_file.name}
        rows, _ = core.parse_blastp_result(str(result_file), include_ancestor=True)
        payload = core.build_ancestral_alignment_payload(rows, metadata)
        for name, value in [('metadata.json', metadata), ('alignment_payload.json', payload)]:
            (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'Kept {filtered_hits} of {total_hits} valid hits across {len(ancestors)} ancestor database(s).')
        print(output)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(2, f'Error: {error}\n')


if __name__ == '__main__':
    main()
