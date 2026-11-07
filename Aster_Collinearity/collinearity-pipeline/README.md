# Collinearity Analysis Pipeline

Command-line scripts for protein homology searches, ColinearScan block identification, Ka/Ks calculation, and three types of genome dot plots. Comparisons are named `<query>_<subject>`; for example, `Aoff_Ases` and `Ases_Aoff` are separate comparisons.

For a ready-to-plot dataset and figure previews, start with the [module overview](../README.md) and [precomputed example](../examples/Aoff_Ases/README.md).

## Scripts

| Script | Purpose |
| --- | --- |
| `1_blast/run_blast_diamond.py` | Run protein homology searches for selected species pairs. |
| `1_blast/dotplot_blast.py` | Draw BLAST or DIAMOND hits. |
| `2_block/run_colinearscan.py` | Prepare gene pairs, run ColinearScan, and remove redundant blocks. |
| `2_block/dotplot_block.py` | Draw selected collinear gene pairs. |
| `3_ks/run_ks.py` | Run Ka/Ks calculations for gene pairs in block files. |
| `3_ks/calculate_ks.pl` | Align translated proteins, project the alignment to CDS, and calculate Ka/Ks. |
| `3_ks/SeqStatistics.pm` | Local substitution-rate routines used by the Perl calculation. |
| `3_ks/run_ks_dot.py` | Prepare block annotations and call the Ks plotter. |
| `3_ks/ks_dotplot.pl` | Draw collinear blocks with median Ks labels. |

## Requirements

The commands below use Bash on Linux or WSL. Use a working path without spaces, because several scripts construct shell commands from filenames.

| Component | Required for |
| --- | --- |
| Python 3 | All Python drivers |
| `pandas` | ColinearScan input preparation |
| `matplotlib` | BLAST and block dot plots |
| BLAST+ (`makeblastdb`, `blastp`) or DIAMOND | Protein searches |
| ColinearScan `blockscan` | Collinear block identification |
| Perl, BioPerl, and `clustalw2` | Ka/Ks calculation |
| Perl modules `GD` and `GD::Text::Align`, with TrueType font support | Ks dot plots |

Install external executables on `PATH`. The local `SeqStatistics.pm` is supplied with the scripts; external programs and Perl libraries are not bundled.

```bash
python -m pip install pandas matplotlib

# Check the tools needed for a BLASTP-based complete run.
command -v makeblastdb blastp blockscan clustalw2 perl
perl -MBio::SeqIO -e 'print "BioPerl OK\n"'
perl -MGD -MGD::Text::Align -e 'print "GD modules OK\n"'
```

The Ks plotter defaults to `/usr/share/fonts/dejavu/DejaVuSans.ttf`. If necessary, select an installed TrueType font:

```bash
export KS_DOTPLOT_FONT=/path/to/DejaVuSans.ttf
```

The Python plots request Times New Roman through matplotlib. A fallback font may be used if it is unavailable.

## Input files

Gene identifiers must match across FASTA headers, annotations, search results, blocks, and Ks tables. Use a letter-based species abbreviation and numeric chromosome identifiers, for example `Aoff1g00001` or `Ases01g00001`. Avoid underscores and dots in the species abbreviation; the scripts use these characters to split pair names and filenames.

The scripts do not convert arbitrary genome annotations into their required gene naming and table formats. Prepare the files before running the workflow.

| File | Description |
| --- | --- |
| `<sp>.pep` | Protein FASTA; the search driver reads these files from its current directory. |
| `<sp>.cds` | Matching CDS FASTA for Ka/Ks calculation; `<sp>.cds.fasta` is also accepted. |
| `<sp>.new.gff` | Custom seven-column, tab-separated gene table described below. |
| `<sp>.lens` | Chromosome identifier and number of genes, described below. |
| `<query>_<subject>.blast` | Twelve-column tabular BLAST format (`outfmt 6`), with query hits grouped together and best hits first. |

### Gene annotation: `<sp>.new.gff`

This is a custom table, not a standard nine-column GFF3 file. Use tabs, no header, and no blank records. Keep genes grouped by chromosome and ordered along each chromosome.

| Column | Meaning |
| --- | --- |
| 1 | Numeric chromosome identifier |
| 2 | Gene start coordinate |
| 3 | Gene end coordinate |
| 4 | Strand: `+` or `-` |
| 5 | Original gene identifier |
| 6 | Renamed gene identifier used by the analysis |
| 7 | Gene order within that chromosome, starting at 1 |

Example records from the supplied annotations:

```text
1	2167	2946	-	LOC109828828	Aoff1g00001	1
1	71380	73656	-	LOC109844852	Aoff1g00002	2
1	94514	99394	+	LOC109844874	Aoff1g00003	3
```

The gene order restarts on each chromosome. Both Python dot plotters use column 7 for gene positions, and add chromosome offsets from the `.lens` file. The Perl Ks plotter also depends on the row order of the annotations.

### Chromosome gene counts: `<sp>.lens`

Two columns are required: chromosome identifier and number of genes on that chromosome. The identifier may contain the species prefix, but its numeric chromosome must agree with the annotations and gene IDs.

```text
Aoff1	3075
Aoff2	1967
Aoff3	2804
```

These values are gene counts, not chromosome lengths in base pairs or pixel coordinates. A third column is not required by this pipeline. Keep rows in the intended chromosome display order, and ensure the counts agree with the gene-order range in the annotation table.

### Intermediate files

Preserve the complete ColinearScan block structure, including the `the ... path length ...` records and closing `>LOCALE p-value ...` lines. A block file is not a plain two-column gene-pair table.

The Ks table has four tab-separated columns and no header:

```text
gene_id_1    gene_id_2    Dn    Ds
```

`Dn` is the nonsynonymous rate (Ka), and `Ds` is the synonymous rate (Ks). The file does not contain a separately calculated Ka/Ks ratio column. A value of `-2` denotes an unavailable calculation.

## Run the workflow

The following example runs one comparison, `Aoff_Ases`. Replace the abbreviations with your own species names. Start in the `collinearity-pipeline` directory and prepare the input directories:

```bash
PIPELINE_DIR="$(pwd)"
mkdir -p work/{pep,cds,bed,blast,blk,ks,block_plot_input,ks_plot_input}
cd work
```

Place `Aoff.pep` and `Ases.pep` in `pep/`, their corresponding `.cds` files in `cds/`, and both species' `.new.gff` and `.lens` files in `bed/`. Run the remaining commands from this `work` directory in the same shell so that `PIPELINE_DIR` remains defined.

### 1. Protein searches and BLAST dot plots

```bash
(
  cd pep
  python "$PIPELINE_DIR/1_blast/run_blast_diamond.py" \
    --program blast --pairs Aoff_Ases --processes 1 --threads 4
)
cp pep/Aoff_Ases.blast blast/

python "$PIPELINE_DIR/1_blast/dotplot_blast.py" \
  --bed bed --blast blast --out blast_dot --processes 1
```

Without `--pairs`, the search driver processes every ordered pair of species found in the current directory, including self comparisons. For `N` species, this gives `N × N` comparisons. `--no-repeat` selects unordered interspecies pairs; `--exclude` skips selected pairs, and `--add-species` selects comparisons involving new species.

BLASTP uses E-value `1e-5` and `-max_target_seqs 10`. DIAMOND uses E-value `1e-5` and `-k 50`, and writes `.diamond` files. If you use DIAMOND, copy the selected output to the `.blast` name required by the downstream calculation scripts:

```bash
cp pep/Aoff_Ases.diamond blast/Aoff_Ases.blast
```

The Python plotters can also read `.diamond` directly with `--suffix diamond` when their input filenames use that suffix.

The BLAST dot plot keeps non-self hits with bitscore ≥ 100 and E-value < `1e-5`. The first retained hit for each query is red, the next five are blue, and later retained hits are white. Hit order comes from the input file. Output: `blast_dot/Aoff_Ases.png`.

### 2. Collinear blocks and block dot plots

```bash
python "$PIPELINE_DIR/2_block/run_colinearscan.py" \
  --blast-dir blast --bed-dir bed --out-dir blk \
  --processes 1 --threads 4

# The block plotter reads both files from the same input directory.
cp blast/Aoff_Ases.blast block_plot_input/
cp blk/Aoff_Ases.block.rr.txt block_plot_input/

python "$PIPELINE_DIR/2_block/dotplot_block.py" \
  --bed bed --data block_plot_input --out block_dot \
  --min-genes 10 --processes 1
```

The block driver selects hits with bitscore ≥ 100, removes self hits, ignores identifiers containing `Un`, `Scaffold`, or `random`, and masks genes participating in 50 or more retained hits. It runs `blockscan` for each chromosome pair using `-mg1 50 -mg2 50`, then applies its self-homology and overlap removal rules.

Outputs:

- `blk/Aoff_Ases.block.rr.txt`
- For self comparisons, an additional `<sp>_<sp>.partially.block.rr.txt`
- `block_dot/Aoff_Ases.10.2400.png`

The current block plot draws gene pairs from blocks with at least `--min-genes` records. It displays first-hit pairs in orange-red and second-hit pairs in gray; hits ranked third or later are not drawn by the active plotting function.

### 3. Ka/Ks calculation

```bash
python "$PIPELINE_DIR/3_ks/run_ks.py" \
  --blk-dir blk --cds-dir cds --ks-dir ks --processes 1
```

Use relative directory arguments for this step, as shown above; the Perl helper constructs relative paths to its temporary alignment files. Each block gene pair needs both CDS records. Protein alignment uses `clustalw2`, followed by CDS alignment and substitution-rate calculation through the supplied Perl code.

Output: `ks/Aoff_Ases.ks.txt`. Files whose names contain `partially` or `less` are skipped by the driver.

### 4. Ks dot plots

```bash
cp bed/Aoff.new.gff bed/Ases.new.gff bed/Aoff.lens bed/Ases.lens ks_plot_input/
cp blast/Aoff_Ases.blast blk/Aoff_Ases.block.rr.txt ks/Aoff_Ases.ks.txt ks_plot_input/

(
  cd ks_plot_input
  python "$PIPELINE_DIR/3_ks/run_ks_dot.py" --processes 1
)
```

Keep a pair's `.blast`, `.block.rr.txt`, and `.ks.txt` files, together with both species' annotations and lens files, in the plotting directory. Every block pair must have a matching Ks record, and every query in the Ks table must occur in the BLAST input.

The helper writes intermediate annotation files and calls `ks_dotplot.pl`. The output filename reverses the input pair order: `Ases_Aoff.Ksdotplot.png` for `Aoff_Ases`.

The current call selects blocks with p-value < `1e-10` and 8–10,000 gene pairs. Block medians use Ks values from 0 to 2 inclusive; labels are drawn for blocks of at least 10 pairs. Median Ks below `1.325` is labeled red. These settings are fixed in the scripts rather than exposed as command-line options.

## Species names and resource settings

`species_names.tsv` maps abbreviations to the full species names used for axis labels. Add a tab-separated record for each new species, or use `--names /path/to/species_names.tsv` with a plotting script. Missing names fall back to their abbreviations.

Run any Python script with `--help` to see its supported options. Choose concurrency for your available hardware:

| Driver | Default concurrency |
| --- | --- |
| Protein searches | 10 pair jobs, 8 threads per search |
| ColinearScan | 3 pair jobs, 8 chromosome-pair threads per pair |
| Ka/Ks calculation | 12 pair jobs |
| Ks plotting | 8 processes |
| Python dot plots | 1 process |

## Current behavior and validation

- The bundled example provides selected, precomputed plotting data. Re-running searches or block detection on a different sequence subset can change hits and block boundaries.
- The Ks plotting preparation currently stores one hit-count value per query in its extra annotation field. Its point colors should not be interpreted as a verified rank for each individual query–subject pair.
- Some external-program failures are printed as warnings. Check output files and logs before treating a calculation as successful.
- ColinearScan and Ka/Ks drivers remove their pair-specific temporary directories after processing. Retain the original inputs and final outputs for reproducibility.
- BLAST and block plotting have been checked with the included example. The complete search–ColinearScan–Ka/Ks workflow and Perl/GD Ks rendering have not been validated end to end as part of this documentation update.

## Citation

Cite the original tools and methods used for your results: BLAST+ or DIAMOND, ColinearScan, ClustalW2, and BioPerl. Retain the existing author attributions in the source files and report the actual versions, search settings, and block-selection criteria used in your analysis.
