# Aoff–Ases Precomputed Plotting Example

This example demonstrates the file formats and plotting steps of the collinearity pipeline using selected records from a supplied tutorial dataset.

- `Aoff`: *Asparagus officinalis* (query species).
- `Ases`: *Angraecum sesquipedale* (subject species).
- Scope: six complete precomputed blocks and their associated BLAST and Ka/Ks records, displayed against the supplied chromosome annotations.

The example is intended for learning the formats and running the plotters. It does not include protein/CDS FASTA files or demonstrate the output of a fresh end-to-end calculation. Both species are outside Asteraceae; they illustrate how the same scripts can be used with other plant genomes.

## Files

| Directory or file | Contents |
| --- | --- |
| `bed/Aoff.new.gff` | Original seven-column annotation: 24,907 genes across 10 chromosomes. |
| `bed/Ases.new.gff` | Original seven-column annotation: 23,712 genes across 19 chromosomes. |
| `bed/*.lens` | Chromosome gene counts generated from the corresponding annotation tables. |
| `blast/Aoff_Ases.blast` | 2,240 BLAST records for queries in the selected blocks and subjects present in the annotations. |
| `block/Aoff_Ases.block.rr.txt` | Six complete blocks, containing 315 gene-pair records. |
| `ks/Aoff_Ases.ks.txt` | 315 corresponding precomputed `gene1`, `gene2`, `Dn`, `Ds` records. |
| `expected/Aoff_Ases.blast.png` | BLAST dot plot generated with this example. |
| `expected/Aoff_Ases.block.png` | Block dot plot generated with this example and `--min-genes 10`. |
| `preparation.json` | Selection rules, record counts, and source-file SHA-256 hashes. |

## How the records were selected

The original tutorial collection contains some records that do not correspond across all files. This demonstration therefore uses the six largest complete blocks for which every gene pair occurs in the supplied BLAST results, Ks table, and both gene annotation tables. The selected block lengths are 56, 43, 55, 47, 64, and 50 pairs, retained in their source order.

BLAST records are selected for the blocks' query genes, with subject genes restricted to the supplied annotations. Their original order, alignments, scores, and E-values are retained. The matching Ks records retain their original numeric values; identical duplicate records are removed. No alignment or substitution rates were recalculated during preparation.

The original annotation tables are retained. The `.lens` files are regenerated from their gene-order ranges: the source `Ases.lens` listed chromosome 20, but the supplied `Ases.new.gff` has no chromosome-20 records, so that chromosome is omitted from this example.

The annotations include all represented chromosomes, while the selected blocks cover only a few regions. Empty parts of the example plots are expected and do not indicate an error. This subset should not be used as a genome-wide collinearity result or to estimate genome-wide Ks distributions.

## Draw the BLAST and block plots

Follow the runnable commands in the [module quick start](../../README.md#quick-start-draw-the-example-plots). They start from the `Aster_Collinearity` directory and write new figures under `work/`.

The expected figures were generated with the supplied Python scripts. Both commands completed successfully. Image dimensions are 2,400 × 2,400 pixels; exact text appearance can vary with installed fonts and matplotlib versions.

## Optional: draw the Ks plot

This step requires Perl, `GD`, `GD::Text::Align`, and a working TrueType font. It uses the precomputed Ks table and does not require BioPerl or ClustalW2 unless you also want to recalculate Ks from CDS sequences.

From the `Aster_Collinearity` directory, in Bash:

```bash
PIPELINE_DIR="$(pwd)/collinearity-pipeline"
mkdir -p work/example_ks
cp examples/Aoff_Ases/bed/*.new.gff examples/Aoff_Ases/bed/*.lens work/example_ks/
cp examples/Aoff_Ases/blast/Aoff_Ases.blast work/example_ks/
cp examples/Aoff_Ases/block/Aoff_Ases.block.rr.txt work/example_ks/
cp examples/Aoff_Ases/ks/Aoff_Ases.ks.txt work/example_ks/

(
  cd work/example_ks
  python "$PIPELINE_DIR/3_ks/run_ks_dot.py" --processes 1
)
```

Expected output filename: `work/example_ks/Ases_Aoff.Ksdotplot.png`. The species order in this filename is reversed relative to the input pair. Consult the [pipeline guide](../../collinearity-pipeline/README.md#4-ks-dot-plots) for the fixed block filters, median labels, and the current limitation in point-color annotations.

Perl/GD rendering and complete Ka/Ks recalculation were not run as part of this documentation update; no reference Ks figure is supplied.

## Recalculate with your own data

Prepare complete, matching protein and CDS sequences together with their annotations and chromosome gene counts, then follow the [full workflow](../../collinearity-pipeline/README.md#run-the-workflow). Recomputed search and block results may differ from this selected precomputed dataset.
