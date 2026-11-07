# Ancestral Gene Tracing

Identify the best matching extant gene for each query, then retrieve the ancestral relationships recorded for that gene in the combined reference tables. This corresponds to `search_mode=best_hit_trace` on the AGRP ancestral chromosome page.

## Workflow

1. Search the currently traceable extant species: `Fli`, `Gehy`, and `Arla`.
2. Apply the E-value, bitscore, and identity thresholds.
3. Select one best hit per query, prioritizing higher bitscore, lower E-value, higher identity, and longer alignment, in that order.
4. Look up the best gene in the combined tables and report the corresponding ancestor genes and reference rows.
5. Build per-ancestor summaries and the combined-table neighborhood payload used by the result viewer.

When the best gene has no recorded relationship, the result is `No ancestral relationship`. The implementation does not move to a lower-scoring hit to obtain an ancestral assignment.

## Files and dependencies

| File or directory | Purpose |
| --- | --- |
| `run_gene_tracing.py` | Standalone command-line adapter. |
| `source_core.py` | Extracted best-hit, lookup, summary, annotation, and neighborhood functions. |
| `reference_data/static/ancestral_combined/` | The three complete combined reference tables copied from the local project. |
| `examples/reference_project/` | Small subset containing the first 12 actual rows of each reference table. |
| `examples/illustrative_hits.tsv` | Explicitly synthetic BLAST-format records demonstrating selection and lookup. |
| `examples/expected/` | Expected outputs for that small demonstration. |
| `web_reference/` | Original tracing query form fragment and shared result template. |

Python 3 is sufficient for existing-result tracing. Fresh sequence searches additionally require NCBI BLAST+ (`blastp` or `blastn`, plus `blastdb_aliastool`) and matching prepared databases for all three extant species.

## Small offline example

From this directory:

```bash
python run_gene_tracing.py \
  --blast-results examples/illustrative_hits.tsv \
  --project-root examples/reference_project \
  --out work/demo
```

The scores and alignment fields in this example are synthetic format fixtures. The combined reference rows are actual source rows. Expected behavior:

- `demo_traced`: two passing hits; `Arla1g00001` is selected and has recorded ancestral relationships.
- `demo_unmapped`: its passing best hit has no matching reference row, so it remains unassigned.
- `demo_filtered`: its hit fails the default thresholds and contributes no best hit.

Two queries have passing best hits, and one query has a recorded ancestral relationship. Compare the results with `examples/expected/`.

## Trace real existing results

Provide standard twelve-column `outfmt 6` results, optionally followed by a subject-title column. For consistency with the webpage's workflow, these results should come from searches against the Fli/Gehy/Arla databases.

```bash
python run_gene_tracing.py \
  --blast-results extant_search.tsv \
  --evalue 1e-5 --min-score 100 --min-identity 60 \
  --out work/real_trace
```

Without `--project-root`, the adapter uses the three complete reference tables bundled under `reference_data`. Initial indexing of full tables can take longer and require more memory than the small demonstration. One query can produce several output rows if its best gene occurs in several combined-table rows.

The combined tables have no header, are tab-separated, and use `.` for missing entries. Column roles are classified from recognized ancestor and extant-species gene prefixes. Gene identifiers must follow the naming scheme recognized by the extracted implementation.

## Run a fresh sequence search

With an AGRP data directory containing all required databases and combined tables:

```bash
python run_gene_tracing.py \
  --query query.pep --sequence-type prot \
  --project-root /path/to/AGRP \
  --out work/fresh_trace
```

The original layout uses:

```text
<project-root>/
└── static/
    ├── ancestral_combined/
    │   ├── Fli_all_with_combined.txt
    │   ├── Gehy_all_with_combined.txt
    │   └── Arla_all_with_combined.txt
    └── blast_match_database/
        ├── prot/Fli, prot/Gehy, prot/Arla
        └── nucl/Fli, nucl/Gehy, nucl/Arla
```

Entries such as `prot/Fli` are database prefixes, not individual sequence files. Use `--sequence-type nucl` for nucleotide queries. The adapter can alternatively accept three explicit `--db CODE=PREFIX` overrides; supply Fli, Gehy, and Arla together.

The search creates a combined database alias and runs BLASTP or BLASTN with eight threads and `-max_target_seqs 50`, matching the website job's settings. Configure a nonstandard executable location with `--blast-bin-dir`.

## Outputs and interpretation

| File | Contents |
| --- | --- |
| `trace_results.tsv` | Readable table of query, best extant gene, source, ancestral summary, alignment statistics, and status. |
| `trace_results.json` | Full tracing records, including ancestor maps and source row identifiers. |
| `metadata.json` | Input/filtered hit counts, best-hit count, traced-query count, and thresholds. |
| `tracing_payload.json` | Per-ancestor summaries for the result view. |
| `decobrowse_payload.json` | Combined-table neighborhood rows, columns, query summaries, and warnings. |

Neighborhood size is controlled by `--flank` (default 5). Where matching species or ancestral GFF files are available under the project root, the original lookup functions use them for gene details. This package bundles the relationship tables; missing GFFs result in fallback gene records without full coordinate annotation.

The JSON neighborhood payload is data for a viewer. The web application's templates, styles, URL handling, access controls, and job lifecycle provide the surrounding interactive page.

The small example checks best-hit selection, threshold filtering, matched/unmapped lookup, and neighborhood construction. Fresh searches against the complete production databases have not been run for this package. Use a new `--out` path for each run, and see `python run_gene_tracing.py --help` for all options.
