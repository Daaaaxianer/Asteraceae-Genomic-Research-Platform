# Aster AGR: Ancestral Genome Resources and Tools

Three complementary modules for ancestral candidate searches, gene tracing through recorded chromosome relationships, and extraction of ancestral gene resources.

The first two modules contain computational functions extracted from the AGRP `ancestral_chromosome` page and command-line adapters for file-based use. The third preserves the supplied ancestral-genome scripts and AAK-I files.

## Choose a module

| Module | Input | Main operation | Output |
| --- | --- | --- | --- |
| [Ancestral Candidate Search](ancestral_candidate_search/README.md) | Query protein/CDS sequences or existing search results | Search selected ancestor databases and retain every hit meeting the thresholds | Candidate hit table and per-ancestor summaries |
| [Ancestral Gene Tracing](ancestral_gene_tracing/README.md) | Query sequences or existing extant-species BLAST results | Select one best extant hit per query, then look up recorded ancestral relationships | Tracing tables, ancestor summaries, and neighborhood payloads |
| [Ancestral Genome Extraction](ancestral_genome_extraction/README.md) | Ordered ancestor–extant mappings, extant annotations, and extant sequences | Select supported mappings, rename genes, and extract GFF/CDS/PEP records | Ancestor resource files |

Candidate search returns similarity-based candidates. Gene tracing uses the relationships recorded in the supplied combined tables. Resource extraction starts from an existing reconstruction/mapping table; the scripts do not infer that table themselves.

## Directory structure

```text
Aster_AGR/
├── README.md
├── SOURCE_MANIFEST.json
├── ancestral_candidate_search/
│   ├── run_candidate_search.py
│   ├── source_core.py
│   ├── examples/
│   └── web_reference/
├── ancestral_gene_tracing/
│   ├── run_gene_tracing.py
│   ├── source_core.py
│   ├── reference_data/static/ancestral_combined/
│   ├── examples/
│   └── web_reference/
└── ancestral_genome_extraction/
    ├── ancestral_gene_extract.py
    ├── ancestral_gff_extract.py
    ├── ancestral_cds_pep_extract.py
    ├── AAKI.cds.gz / AAKI.pep / AAKI.new.gff
    ├── AAKI.lens / AAKI.lens.txt
    ├── AAKI_duplicate_ids.tsv
    ├── data_validation.json
    └── examples/
```

## Quick start

Use Python 3. The offline examples and extraction scripts use the Python standard library. The multi-line commands below use Bash (Linux or WSL); run them from `Aster_AGR`:

```bash
# Filter a small example produced by a real BLASTN search.
cd ancestral_candidate_search
python run_candidate_search.py \
  --raw-results AAKI=examples/AAKI.raw.tsv \
  --sequence-type nucl --out work/candidate_demo
cd ..

# Trace illustrative best hits using a small subset of real reference rows.
cd ancestral_gene_tracing
python run_gene_tracing.py \
  --blast-results examples/illustrative_hits.tsv \
  --project-root examples/reference_project --out work/tracing_demo
cd ..
```

Each example includes expected outputs. The tracing example's BLAST-format scores are explicitly synthetic fixtures; they demonstrate best-hit selection and relationship lookup rather than measured sequence similarity.

See the [extraction example](ancestral_genome_extraction/README.md#run-the-small-format-example) for the three original resource-extraction scripts. Fresh sequence searches additionally require DIAMOND and/or NCBI BLAST+, with prepared databases as described in the module guides.

## Status of the supplied AAK-I data

The content of the five original AAKI data files is preserved. To keep every uploaded file below 25 MB, the CDS is distributed as `AAKI.cds.gz`; decompression restores the original `AAKI.cds` byte-for-byte. See the [decompression instructions](ancestral_genome_extraction/README.md#compressed-cds-file). CDS, PEP, and GFF each contain **22,382 records but 16,211 unique gene identifiers**. There are **5,386 identifier groups with multiple records** and 6,171 additional records using repeated identifiers.

These files retain the supplied identifiers for provenance. A corrected one-to-one identifier scheme is needed before using them as a reference that requires unique gene IDs. Do not resolve the issue by deleting repeated IDs: distinct records may represent different genes.

The [identifier report](ancestral_genome_extraction/AAKI_duplicate_ids.tsv), [validation summary](ancestral_genome_extraction/data_validation.json), and [extraction guide](ancestral_genome_extraction/README.md#identifier-status) document this issue. The small candidate-search database contains eight distinct identifiers and is separate from the full supplied resource.

## Source and validation

`SOURCE_MANIFEST.json` records the source file, original line ranges, function hashes, archive hash, and hashes of the eight original archive members. Its `distribution` section maps the gzip file to the original CDS content; original member hashes refer to the decompressed bytes. Computational function bodies are retained from `browse/views.py`; the new entry scripts configure file paths and expose command-line options.

`web_reference/` contains the mode-specific query form and the shared result template for integration reference. Their Django layout, URL handling, download access, and task lifecycle belong to the AGRP web application. The command-line tools write results to local files.

Validation for this package covers a real small BLASTN search, offline candidate filtering, tracing with matched/unmapped/filtered cases, neighborhood payload construction, and all three original extraction scripts on a synthetic format example. Fresh DIAMOND searches and full searches of the Fli/Gehy/Arla production databases were not run for this packaging update.

Please retain the original source author attributions and cite the search methods and ancestral reconstruction resources used in your research.
