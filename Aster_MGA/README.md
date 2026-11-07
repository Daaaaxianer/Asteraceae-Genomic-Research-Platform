# Elu–Ddev Collinearity Analysis (*Elaeis guineensis* vs *Dendrobium devonianum*)

Genome collinearity analysis between *Elaeis guineensis* (oil palm, **Elu**, 16 chromosomes) and *Dendrobium devonianum* (**Ddev**, 19 chromosomes). The repository holds the input files, the scripts, and the results: collinear blocks detected with ColinearScan, manually delineated homologous regions (A1–A4), and an Elu-referenced multiple-collinearity table (mc table) with up to four Ddev copies per Elu gene.

## 1. Repository layout

```
.
├── bed/                       gene positions and chromosome sizes
│   ├── Elu.new.gff   Ddev.new.gff
│   └── Elu.lens      Ddev.lens
├── blastp/
│   └── Elu_Ddev.blast         genome-wide BLASTP, Elu vs Ddev (outfmt 6)
├── blk/
│   └── Elu_Ddev.block.rr.txt  ColinearScan blocks, redundancy removed
├── regions/                   manually delineated homologous regions
│   ├── Elu_Ddev.regions_pixel.txt      box coordinates read off the plot
│   └── Elu_Ddev.correspondence.txt     same regions in gene-index coordinates
├── mc_table/                  main result
│   ├── Elu_v_Ddev.mc.txt               comma-separated, with depth
│   ├── Elu_v_Ddev.mc.tab.txt           tab-separated
│   ├── Elu_v_Ddev.mc.tab.dot.txt       tab-separated, empty cells = "."
│   └── Elu_Ddev.new.blast              BLAST hits restricted to mc-table pairs
├── figures/
│   ├── Elu_Ddev.frame.png     dot plot with hand-drawn A1–A4 boxes
│   └── Elu_Ddev.mc.png        dot plot of the mc-table pairs
└── scripts/
    ├── run_colinearscan.py             BLAST filtering + ColinearScan
    ├── dotplot.py                      dot plots
    ├── step0_pixel_to_gene.pl          pixel -> gene-index coordinates
    ├── step1_build_mc_table.pl         build the mc table
    ├── step2_to_tab.pl                 comma -> tab
    ├── step3_fill_dots.pl              fill empty cells with "."
    └── step4_filter_blast.pl           extract mc-table pairs from the BLAST
```

## 2. Workflow

```
bed/*  blastp/Elu_Ddev.blast
   │  scripts/run_colinearscan.py
   ▼
blk/Elu_Ddev.block.rr.txt
   │  scripts/dotplot.py (full BLAST) → draw A1–A4 boxes by hand → figures/Elu_Ddev.frame.png
   ▼
regions/Elu_Ddev.regions_pixel.txt
   │  step0_pixel_to_gene.pl
   ▼
regions/Elu_Ddev.correspondence.txt
   │  step1_build_mc_table.pl   (also reads blk/ and bed/)
   ▼
mc_table/Elu_v_Ddev.mc.txt → step2 → .mc.tab.txt → step3 → .mc.tab.dot.txt
   │  step4_filter_blast.pl     (also reads blastp/)
   ▼
mc_table/Elu_Ddev.new.blast → scripts/dotplot.py → figures/Elu_Ddev.mc.png
```

## 3. Requirements

- Perl 5
- Python 3 with `pandas` and `matplotlib`
- `blockscan` (ColinearScan) on your `PATH` — only needed by `run_colinearscan.py`

## 4. Usage

Run everything from the repository root.

```bash
# 1. Collinear blocks  ->  blk/Elu_Ddev.block.rr.txt
#    (expects blastp/*.blast and bed/{species}.new.gff / .lens)
python scripts/run_colinearscan.py

# 2. Dot plot of the full BLAST, used to draw the A1–A4 boxes by hand
python scripts/dotplot.py --bed bed --blast blastp --out figures_tmp --suffix blast
#    Read the box coordinates and write them to regions/Elu_Ddev.regions_pixel.txt

# 3. Pixel coordinates -> gene-index coordinates
perl scripts/step0_pixel_to_gene.pl bed/Elu.lens bed/Ddev.lens \
     regions/Elu_Ddev.regions_pixel.txt regions/Elu_Ddev.correspondence.txt

# 4. Build the mc table
perl scripts/step1_build_mc_table.pl bed/Elu.new.gff bed/Ddev.new.gff \
     regions/Elu_Ddev.correspondence.txt blk/Elu_Ddev.block.rr.txt \
     mc_table/Elu_v_Ddev.mc.txt Ddev
perl scripts/step2_to_tab.pl   mc_table/Elu_v_Ddev.mc.txt     mc_table/Elu_v_Ddev.mc.tab.txt
perl scripts/step3_fill_dots.pl mc_table/Elu_v_Ddev.mc.tab.txt mc_table/Elu_v_Ddev.mc.tab.dot.txt
perl scripts/step4_filter_blast.pl mc_table/Elu_v_Ddev.mc.txt blastp/Elu_Ddev.blast \
     mc_table/Elu_Ddev.new.blast

# 5. Dot plot of the mc-table pairs  ->  figures/Elu_Ddev.mc.png
python scripts/dotplot.py --bed bed --blast mc_table --out figures --suffix new.blast
```

`dotplot.py` needs the species abbreviations to be listed in its `NAME_CHANGE` dictionary (Elu and Ddev already are). The Times New Roman font is used for labels; matplotlib falls back to another font if it is not installed.

## 5. File formats

**`bed/*.new.gff`** — tab-separated, 7 columns: chromosome, start, end, strand, original gene ID, new gene ID (e.g. `Elu1g00001`), gene index in the whole genome. Elu has 27,479 genes and Ddev has 29,786.

**`bed/*.lens`** — 3 columns: chromosome name, number of genes, cumulative end position in pixels on the dot plot (used by step 0). 16 rows for Elu, 19 for Ddev.

**`blastp/Elu_Ddev.blast`** — BLAST outfmt 6, 12 columns, about 207,000 lines.

**`blk/Elu_Ddev.block.rr.txt`** — ColinearScan blocks after removing self-homologous and overlapping blocks. Each block lists its gene pairs (Elu gene, index, Ddev gene, index, orientation) followed by a `>` line with statistics. A block judged redundant is followed by a line giving the reason (`self homologous` or `overlap with block ...`). About 3,390 block records, about 590 of them marked redundant.

**`regions/Elu_Ddev.regions_pixel.txt`** — one entry per hand-drawn box, `type:Elu_chr:start-end:Ddev_chr:start-end`, e.g. `A3:Elu1:0-322:Ddev2:398-1`. `0` is the chromosome start, `1` the chromosome end, anything else is a pixel position on the plot.

**`regions/Elu_Ddev.correspondence.txt`** — the same regions in gene-index coordinates, e.g. `A3:Elu1:0-1675:Ddev2:763-2232`. 153 regions: 37 A1, 34 A2, 43 A3, 39 A4. A1–A4 are the four homologous copies of an Elu region in Ddev; one Elu region corresponds to at most four Ddev regions.

**`mc_table/Elu_v_Ddev.mc*.txt`** — one row per Elu gene (27,479 rows, same order as `Elu.new.gff`).

| File | Format |
|---|---|
| `Elu_v_Ddev.mc.txt` | Comma-separated: `Elu gene, A1, A2, A3, A4, depth`. Empty cell = a space; gap inside a block = `.`. `depth` is the number of A1–A4 columns covered by a collinear block (counting `.`), 0–4. |
| `Elu_v_Ddev.mc.tab.txt` | Same without `depth`, tab-separated. |
| `Elu_v_Ddev.mc.tab.dot.txt` | Tab-separated, every empty cell filled with `.`. |
| `Elu_Ddev.new.blast` | The BLAST hits whose Elu–Ddev gene pair appears in the mc table (12,085 lines). |

Summary of the mc table:

| Item | Count |
|---|---|
| Elu genes | 27,479 |
| Ddev genes in column A1 | 3,553 |
| Ddev genes in column A2 | 2,833 |
| Ddev genes in column A3 | 3,068 |
| Ddev genes in column A4 | 2,365 |

`depth` distribution: 0 → 1,847; 1 → 4,093; 2 → 7,156; 3 → 8,125; 4 → 6,258.

## 6. How step 1 assigns blocks

A collinear block is put into an A region only if all of the following hold:

- its Elu and Ddev chromosomes match those of the region;
- its start and end gene indices lie inside the region (a margin of 10 genes is allowed at each end);
- its p-value is ≤ 0.001 and it has more than 4 gene pairs;
- its Ddev genes have not already been used in the same region or taken by a longer block.

After a block is written to the table, empty rows between two consecutive Ddev genes in the same column (same chromosome, indices within 50 of each other) are filled with `.` to mark gaps inside the block.

## 7. Notes

- Delineating the homologous regions (and thus step 0) relies on coordinates read manually from the plot. Repeating the analysis requires redrawing the boxes, and the result may differ slightly from the one provided.
- `run_colinearscan.py` uses fixed relative paths (`blastp/`, `bed/`, `blk/`) and 3 processes × 3 threads; edit the bottom of the file to change that. It requires `blockscan`, which is not included here.
- Step 3 fills `.` in all five columns. An earlier version of the script stopped at the fourth column and left the A4 column blank in the `.tab.dot.txt` file.
- Step 1 takes the other species' gene-ID prefix as an optional sixth argument (default `Ddev`), so the scripts can be reused for other species pairs that follow the same naming scheme.
- The scripts were checked by rerunning steps 0–4 on the included data: the correspondence file, the mc table, the tab table and `Elu_Ddev.new.blast` were reproduced exactly. `run_colinearscan.py` was not rerun here.

## 8. Citation and contact

- The analysis uses ColinearScan; please also cite the original ColinearScan publication.
- Author / contact: (to be added)
- License: (to be added)
