# Collinearity Analysis Pipeline

A set of scripts for a genome collinearity analysis between any number of species:

1. **BLAST** – all-vs-all protein search (BLASTP or DIAMOND) and a BLAST dot plot
2. **Collinear blocks** – ColinearScan on the BLAST hits and a block dot plot
3. **Ks** – Ks/Ka of the gene pairs in the blocks and a Ks dot plot

Species are identified by a short abbreviation (for example `Elu`, `Ddev`); a species pair is written `<sp1>_<sp2>` (query_database). A worked example (collinear blocks and a multiple-collinearity table for *Elaeis guineensis*, Elu, vs *Dendrobium devonianum*, Ddev) is in the companion repository `Elu-Ddev`.

## 1. Workflow

```
<sp>.pep ──► 1_blast/run_blast_diamond.py ──► <sp1>_<sp2>.blast / .diamond
                                                   │
              1_blast/dotplot_blast.py  ◄──────────┤  (needs bed/<sp>.lens, bed/<sp>.new.gff)
                                                   ▼
             2_block/run_colinearscan.py ──► blk/<sp1>_<sp2>.block.rr.txt
                                                   │
              2_block/dotplot_block.py  ◄──────────┤
                                                   ▼
<sp>.cds ──► 3_ks/run_ks.py ──────────────► ks/<sp1>_<sp2>.ks.txt
                                                   │
              3_ks/run_ks_dot.py  ◄────────────────┘  ──► <sp2>_<sp1>.Ksdotplot.png
```

## 2. Repository layout

```
.
├── species_names.tsv            abbreviation -> full species name (axis labels of the plots)
├── 1_blast/
│   ├── run_blast_diamond.py     all-vs-all BLASTP / DIAMOND
│   └── dotplot_blast.py         dot plot of the BLAST hits
├── 2_block/
│   ├── run_colinearscan.py      BLAST filtering + ColinearScan + redundancy removal
│   └── dotplot_block.py         dot plot of the collinear blocks
└── 3_ks/
    ├── run_ks.py                Ks of the block gene pairs (parallel driver)
    ├── calculate_ks.pl          alignment and Ks calculation for one species pair
    ├── SeqStatistics.pm         Ka/Ks routines used by calculate_ks.pl
    ├── run_ks_dot.py            data preparation + Ks dot plots (parallel driver)
    └── ks_dotplot.pl            draws one Ks dot plot
```

## 3. Requirements

| For | Needs |
|---|---|
| all Python scripts | Python 3, `pandas`, `matplotlib` |
| `run_blast_diamond.py` | BLAST+ (`makeblastdb`, `blastp`) or DIAMOND |
| `run_colinearscan.py` | `blockscan` from ColinearScan, on `PATH` |
| `run_ks.py`, `calculate_ks.pl` | Perl, BioPerl, `clustalw2` on `PATH` |
| `ks_dotplot.pl` | Perl modules `GD` and `GD::Text::Align` (and the system libgd), a TrueType font |

The Ks part was developed with GD 2.83 and BioPerl 1.7.8. These libraries are **not** bundled in this repository; install them with your package manager, for example with conda (`perl-bioperl`, `perl-gd`, `clustalw`; package names depend on the channel) or with `cpanm GD GD::Text Bio::Perl`.

`ks_dotplot.pl` uses `/usr/share/fonts/dejavu/DejaVuSans.ttf`. To use another font, set the environment variable `KS_DOTPLOT_FONT` to the path of a TrueType file. The Python dot plots ask matplotlib for Times New Roman and fall back to the default font if it is not installed.

## 4. Input files

**Gene IDs** must start with the species abbreviation (letters only), followed by the chromosome number and `g`: `Elu1g00001`, `Ddev12g04567`. The scripts read the species and the chromosome from the ID. Species abbreviations must not contain `_` or `.`.

| File | Format |
|---|---|
| `<sp>.pep` | protein FASTA, one file per species (stage 1) |
| `<sp>.cds` | CDS FASTA of the same genes (`<sp>.cds.fasta` also accepted; stage 3) |
| `bed/<sp>.new.gff` | tab-separated: chromosome, start, end, strand, original ID, new gene ID, gene order in the genome (1, 2, 3, ...) |
| `bed/<sp>.lens` | chromosome name, number of genes on it, cumulative pixel end position on the plot (see `Elu-Ddev/bed` for an example) |

Hits to genes whose ID contains `Un`, `Scaffold` or `random` are ignored in stage 2.

## 5. Usage

Run each script with `--help` for all options.

### Stage 1 – BLAST

```bash
# in the directory with <sp>.pep files
python 1_blast/run_blast_diamond.py                          # BLASTP, all ordered pairs incl. A_A
python 1_blast/run_blast_diamond.py --program diamond --processes 4 --threads 8
python 1_blast/run_blast_diamond.py --pairs Elu_Ddev Ddev_Elu Elu_Elu Ddev_Ddev
python 1_blast/run_blast_diamond.py --add-species Tpr        # one new species vs all others

python 1_blast/dotplot_blast.py --bed bed --blast . --out blast_dot --suffix blast
```

By default every ordered pair is run, so the forward (A_B), reverse (B_A) and self (A_A) comparisons are all produced. BLASTP uses `-evalue 1e-5 -max_target_seqs 10` and writes `<pair>.blast`; DIAMOND uses `-e 1e-5 -k 50` and writes `<pair>.diamond`. **The later stages look for `*.blast`**, so rename DIAMOND output (`for f in *.diamond; do mv "$f" "${f%.diamond}.blast"; done`) or pass `--suffix diamond` to the dot plot.

`dotplot_blast.py` keeps hits with bitscore ≥ 100 and E-value < 1e-5 (at most 20 per gene). The best hit of each gene is drawn red, the next ones (up to 5) blue.

### Stage 2 – collinear blocks

```bash
# blastp/<sp1>_<sp2>.blast, bed/<sp>.new.gff, bed/<sp>.lens
python 2_block/run_colinearscan.py --blast-dir blastp --bed-dir bed --out-dir blk

# put the BLAST files and the block files of a pair in one directory
python 2_block/dotplot_block.py --bed bed --data block_blast --out block_dot --min-genes 10
```

For every pair the script keeps hits with bitscore ≥ 100 (no self hits), drops genes with 50 or more hits (repeat masking), splits the gene pairs by chromosome pair, runs `blockscan -mg1 50 -mg2 50` and merges the blocks. A block is dropped when it is self-homologous or lies inside an earlier block (reason written in the file). Output: `blk/<sp1>_<sp2>.block.rr.txt`; for self comparisons also `<sp>_<sp>.partially.block.rr.txt` (each chromosome pair only once).

`dotplot_block.py` draws only blocks with at least `--min-genes` gene pairs.

### Stage 3 – Ks

```bash
# blk/<sp1>_<sp2>.block.rr.txt and cds/<sp>.cds
python 3_ks/run_ks.py --blk-dir blk --cds-dir cds --ks-dir ks --processes 12
```

Output `ks/<sp1>_<sp2>.ks.txt`: one line per block gene pair, `id1  id2  Dn  Ds`; `-2` means the value could not be calculated.

For the Ks dot plot, collect for each pair in one directory the files `<sp1>_<sp2>.blast`, `<sp1>_<sp2>.block.rr.txt`, `<sp1>_<sp2>.ks.txt`, `<sp>.new.gff` and `<sp>.lens`, then run **inside that directory**:

```bash
python /path/to/3_ks/run_ks_dot.py --processes 8
```

It first ranks every hit within its query gene (`*.blastp.new.order.m8`), adds Ks and rank to the block file (`*_block_rr.latest.txt`) and then calls `ks_dotplot.pl`. The plot is named `<sp2>_<sp1>.Ksdotplot.png` (second species first). In the plot, the best hit of a gene is a red dot, the second a blue dot and the others gray dots. A block's label is its median Ks (values between 0 and 2 only); it is red when that median is below 1.325 (`KS_CUTOFF` at the top of `run_ks_dot.py`). The other filters (p-value 1e-10, 8–10000 gene pairs per block) are fixed in the call to `ks_dotplot.pl`.

## 6. Species names

The dot plots label the axes with the full species name found in `species_names.tsv` (tab-separated: abbreviation, name). A species that is not listed is labelled with its abbreviation, so nothing breaks, but add a line for each of your own species. Use `--names` to point to another table.

## 7. Notes

- **Block order.** The redundancy removal depends on the order in which chromosome-pair blocks are compared. `run_colinearscan.py` now processes them in sorted order, so repeated runs give the same result; earlier versions used the order returned by the file system.
- **Temporary files.** `run_colinearscan.py` and `run_ks.py` write their temporary files under `<out-dir>/.colinearscan_tmp` and `<ks-dir>/.tmp` and remove them afterwards.
- **Errors in parallel jobs** are now raised instead of being silently ignored.
- **Tested.** The BLAST driver, the file handling of `run_colinearscan.py`, `run_ks.py` and the data-preparation steps of `run_ks_dot.py`, and both Python dot plots were run on test data, with small stand-ins for `blastp`, `blockscan` and `perl`. `blockscan`, the Ks calculation (BioPerl and ClustalW2) and the GD plotting were not run here (the tools are not installed in the test environment); the Perl files were only syntax-checked. Please run one small species pair end to end before a large analysis.
- Some script headers keep the original author tags.

## 8. Citation and contact

- ColinearScan, BLAST+ / DIAMOND, ClustalW2 and BioPerl are used by these scripts; please cite them.
