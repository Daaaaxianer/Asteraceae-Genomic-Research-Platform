# Ancestral Genome Resource Extraction

The three Python scripts and the content of the five AAKI data files are preserved from the supplied ancestral-genome archive. The CDS is stored as `AAKI.cds.gz`; decompression restores the original bytes. They extract and rename ancestor resources from existing ancestor–extant mappings and extant gene files.

## Contents

| File | Role |
| --- | --- |
| `ancestral_gene_extract.py` | Filter an ordered mapping table and retain its first two columns. |
| `ancestral_gff_extract.py` | Select mapped genes from an extant seven-column GFF table, rename them, and reassign gene order within ancestor chromosomes. |
| `ancestral_cds_pep_extract.py` | Extract and rename matching extant CDS and protein records. |
| `AAKI.cds.gz` | Losslessly compressed AAK-I CDS resource; decompress locally before use. |
| `AAKI.pep` | Supplied AAK-I protein resource. |
| `AAKI.new.gff` | Supplied custom seven-column AAK-I annotation. |
| `AAKI.lens` | Supplied two-column chromosome/count summary. |
| `AAKI.lens.txt` | Supplied three-column companion summary. |
| `AAKI_duplicate_ids.tsv` | Added report of identifiers occurring more than once in the supplied data. |
| `data_validation.json` | Added record and identifier counts. |
| `examples/` | Synthetic input-format demonstration and its expected outputs. |

The original archive does not include the ordered mapping input, `ancestors_gene.txt`, or the original `Arla_genome` inputs needed to regenerate the full AAK-I resource. The examples supplied here demonstrate script mechanics and do not reconstruct the biological dataset.

## Compressed CDS file

`AAKI.cds.gz` keeps the uploaded file below 25,000,000 bytes. The original CDS is 30,375,640 bytes, and is not included as an uncompressed file in this upload directory.

From this module directory, restore the CDS locally with Python (Windows, Linux, or macOS):

```bash
python -c "import gzip, shutil; shutil.copyfileobj(gzip.open('AAKI.cds.gz', 'rb'), open('AAKI.cds', 'xb'))"
```

The `xb` mode prevents overwriting an existing CDS file. Alternatively, on Linux, use `gzip -dk AAKI.cds.gz`. Keep the `.gz` file in the repository; the expanded CDS is for local analysis and is excluded by the supplied `.gitignore`.

The decompressed content has been checked against the original SHA-256 recorded in `SOURCE_MANIFEST.json`.

## Identifier status

The supplied CDS, PEP, and GFF each contain 22,382 records and 16,211 unique gene IDs. Their identifier sets and multiplicities agree, but 5,386 identifier groups occur more than once, accounting for 6,171 additional records. Some IDs occur four times.

The scripts construct a name by appending the portion starting at `g` in the extant identifier to the ancestor prefix. For example, two extant genes with the same `g00001` suffix mapped to the same ancestor prefix can both become `AAKI1g00001`. This naming rule can create collisions across extant chromosomes.

The original files are retained to preserve provenance. Correcting the resource requires the original mapping, gene identities, and corresponding sequences. Do not simply remove repeated headers or change names independently in the three files: distinct records need to remain linked consistently.

See [the duplicate list](AAKI_duplicate_ids.tsv) and [validation counts](data_validation.json). Resolve the identifier scheme before using the full files as a unique-ID search database or lookup reference.

## Original input assumptions

The scripts use Python 3 and the standard library. Two scripts read fixed relative paths based on the current working directory:

```text
workspace/
├── Arla_genome/
│   ├── Arla.new.gff
│   ├── Arla.cds
│   └── Arla.pep
└── run/
    ├── ordered_mapping.tsv
    └── ancestors_gene.txt        Output of the first step
```

Run all three steps from `run/`. The fixed source paths are `../Arla_genome/Arla.new.gff`, `../Arla_genome/Arla.cds`, and `../Arla_genome/Arla.pep`.

### 1. Select ancestor–extant mappings

```bash
python /path/to/ancestral_gene_extract.py ordered_mapping.tsv ancestors_gene.txt
```

The input is tab-separated with no header. Column 1 is an ancestor/chromosome prefix, column 2 is the representative extant gene, and subsequent columns contain supporting genes or `.` for missing entries.

The original script uses the first row's number of columns to choose its rule:

| Support columns after the first two | Selection rule |
| --- | --- |
| At most 2 | At least 2 nonempty, non-`.` support cells. |
| More than 2 | More than 3 nonempty, non-`.` support cells, meaning at least 4. |

These are counts of filled cells, not a count of distinct species. An input with exactly three support columns cannot satisfy the second rule. The selected output contains only the first two columns; its default filename is `ancestors_gene.txt`.

### 2. Extract and rename the gene table

```bash
python /path/to/ancestral_gff_extract.py ancestor.new.gff
```

The script reads `ancestors_gene.txt` and the fixed Arla GFF input. The GFF is a custom tab-separated table with chromosome, start, end, strand, original ID, analysis gene ID, and chromosome-local gene order. It is not standard nine-column GFF3.

For selected genes, the script replaces the chromosome using the first number in the ancestor prefix, constructs the ancestor gene ID, and renumbers column 7 from 1 within each ancestor chromosome. Remaining columns retain their source values. Consequently, the preserved start/end coordinates are source gene coordinates rather than newly inferred ancestral physical coordinates.

### 3. Extract matching CDS and proteins

```bash
python /path/to/ancestral_cds_pep_extract.py ancestor.cds ancestor.pep
```

FASTA headers must exactly match the mapped extant identifiers; descriptions after an ID are not stripped by this original script. The rename rule is the same as in the GFF step. CDS lines are wrapped at 60 characters, while protein sequences are written on one line.

The original console counter increments for processed FASTA records even when a record is not selected. Inspect output FASTA headers for the actual number written. The three scripts do not generate `.lens` files.

## Run the small format example

The files under `examples/Arla_genome` and `examples/demo_run` are explicitly synthetic format fixtures. They contain four extant genes: three pass the support rule, and one is excluded.

From this module directory:

```bash
cd examples/demo_run
python ../../ancestral_gene_extract.py ancestral_order.tsv
python ../../ancestral_gff_extract.py demo.new.gff
python ../../ancestral_cds_pep_extract.py demo.cds demo.pep
```

Expected generated identifiers are `AAKI1g00001`, `AAKI1g00002`, and `AAKI2g00003`. Gene orders in the output table are `1`, `2`, and `1`. Compare the generated files with `examples/expected/`.

The small example validates filtering, fixed relative paths, gene selection, consistent renaming across GFF/CDS/PEP, and chromosome-local numbering. It does not validate the full supplied resource or repair its repeated identifiers.

Source archive hashes and original member hashes are recorded in [SOURCE_MANIFEST.json](../SOURCE_MANIFEST.json).
