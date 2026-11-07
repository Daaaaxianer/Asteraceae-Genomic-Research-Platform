# Ancestral Candidate Search

Search query sequences against selected ancestral databases and retain all hits passing the E-value, bitscore, and percent-identity thresholds. This corresponds to `search_mode=candidate` on the AGRP ancestral chromosome page.

## Files and dependencies

- `source_core.py`: unchanged computational functions and constants extracted from `browse/views.py`.
- `run_candidate_search.py`: a standalone file-based adapter with explicit paths and output settings.
- `examples/`: real query sequences, an eight-record nucleotide reference, raw BLASTN results, and expected offline outputs.
- `web_reference/`: the original candidate query form fragment and shared Django result template.

Offline filtering requires Python 3 only. Fresh protein searches use **DIAMOND `blastp`**; fresh nucleotide searches use **NCBI BLASTN**. The webpage's protein option is labeled BLASTP, while its candidate-search backend calls DIAMOND.

## Run the included offline example

From this directory:

```bash
python run_candidate_search.py \
  --raw-results AAKI=examples/AAKI.raw.tsv \
  --sequence-type nucl --out work/offline_demo
```

The example contains two raw hits from a real BLASTN search of two AAKI CDS sequences against an eight-sequence reference. Both pass the default thresholds. Compare the output with `examples/expected/`.

## Run a fresh small BLASTN search

Install NCBI BLAST+ so that `makeblastdb` and `blastn` are on `PATH`. In Bash:

```bash
mkdir -p work/db
makeblastdb -in examples/mini_AAKI.cds.fasta \
  -dbtype nucl -parse_seqids -out work/db/AAKI

python run_candidate_search.py \
  --query examples/query.cds.fasta --sequence-type nucl \
  --ancestors AAKI --db AAKI=work/db/AAKI \
  --out work/fresh_search
```

The example preserves the actual AAKI sequences from the supplied archive and uses eight distinct identifiers. It tests search mechanics and filtering rather than the biological validity of an ancestral assignment. BLAST versions can affect exact numerical formatting.

## Use your own databases

`--db ANCESTOR=PREFIX` overrides a prepared database prefix. Repeat it for selected ancestors. `--ancestors` accepts registered ancestor codes; `ALL` selects the 29 codes registered in the webpage implementation. With a query and no selection, the command-line adapter defaults to `AAKI` to make the small example practical.

For protein searches, build a DIAMOND database from a curated PEP file:

```bash
diamond makedb --in your_unique_ids.pep --db work/db/AAKI.nr
python run_candidate_search.py \
  --query query.pep --sequence-type prot --ancestors AAKI \
  --db AAKI=work/db/AAKI.nr --out work/protein_search
```

If explicit database overrides are omitted, `--project-root /path/to/AGRP` uses the original website layout:

| Sequence type | Database prefix under the project root |
| --- | --- |
| Protein | `file_keep/Ancestral_chromosome/<ancestor>.nr` (DIAMOND) |
| Nucleotide | `static/ancestral_data/<ancestor>/<ancestor>` (BLAST) |

Use `--diamond /path/to/diamond` or `--blast-bin-dir /path/to/blast/bin` when the executables are not found on `PATH`. Prepared database indexes are not bundled.

The full AAKI files in the extraction module retain repeated identifiers from the supplied archive. See the [data status](../ancestral_genome_extraction/README.md#identifier-status) before preparing a production reference from them.

## Filter existing search results

Supply a standard twelve-column BLAST/DIAMOND `outfmt 6` table. An additional subject-title column is supported. Use raw results without an ancestor column already appended:

```bash
python run_candidate_search.py \
  --raw-results AAKI=AAKI.raw.tsv \
  --raw-results AAKII=AAKII.raw.tsv \
  --evalue 1e-5 --min-score 100 --min-identity 60 \
  --out work/two_ancestors
```

The tool appends the source ancestor code to each retained raw row. It keeps every passing hit rather than choosing one best hit per query.

## Parameters and outputs

| Parameter or setting | Behavior |
| --- | --- |
| `--evalue` | Maximum E-value, inclusive; default `1e-5`. |
| `--min-score` | Minimum bitscore, inclusive; default `100`. |
| `--min-identity` | Minimum percent identity, inclusive; default `60`. |
| DIAMOND search | Four threads, E-value cutoff from the command, at most 50 targets per query per selected database. |
| BLASTN search | Eight threads, E-value cutoff from the command, at most 50 targets per query per selected database. |

Outputs:

- `candidate_hits.tsv`: passing raw hits with the ancestor code appended as the last column. The optional subject-title column is retained when present.
- `metadata.json`: thresholds, ancestor selection, input-hit count, and retained-hit count.
- `alignment_payload.json`: per-ancestor counts and up to five leading hits, using the website's summary function.
- Fresh searches also produce per-ancestor `.raw.tsv` files and, for BLASTN, a command log.

The output directory may already exist, but named results from an earlier run are not overwritten. Choose a fresh `--out` path when repeating an example. Run `python run_candidate_search.py --help` for all options.

The shared result template is supplied for reference; uploading this folder does not by itself register new Django URLs or background jobs.
