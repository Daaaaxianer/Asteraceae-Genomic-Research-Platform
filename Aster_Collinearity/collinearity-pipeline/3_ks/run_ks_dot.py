#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author :yzj
# @FileName :run_ks_dot.py
# @Time :2023/5/30 18:41
"""
Draw Ks dot plots: collinear blocks coloured by gene-pair rank and labelled with
their median Ks.

Run it inside a directory that holds, for every species pair <sp1>_<sp2>:
    <sp1>_<sp2>.blast            BLAST output (sorted by query gene, as written by BLAST)
    <sp1>_<sp2>.block.rr.txt     ColinearScan blocks         (2_block/run_colinearscan.py)
    <sp1>_<sp2>.ks.txt           Ks values of the block pairs (3_ks/run_ks.py)
    <sp>.new.gff, <sp>.lens      gene positions and chromosome sizes

Steps (per pair):
    1. rank of each hit among the hits of its query gene -> <pair>.blastp.new.order.m8
    2. attach the rank to the Ks table                    -> <pair>_block_rr.ks.new.txt
    3. insert Ks and rank into the block file             -> <pair>_block_rr.latest.txt
    4. draw the plot with ks_dotplot.pl                   -> <sp2>_<sp1>.Ksdotplot.png

Example:
    cd my_ks_dot_dir
    python /path/to/3_ks/run_ks_dot.py --processes 8
"""
import argparse
import glob
import os
import subprocess
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
KS_DOTPLOT = os.path.join(HERE, 'ks_dotplot.pl')

# Ks below this value: the block label is drawn in red
KS_CUTOFF = '1.325'


def load_names(path):
    """Read the abbreviation -> full species name table (tab-separated)."""
    names = {}
    if path and os.path.isfile(path):
        for line in open(path, encoding='utf8'):
            line = line.rstrip('\n')
            if not line.strip() or line.startswith('#'):
                continue
            cols = line.split('\t')
            if len(cols) >= 2:
                names[cols[0].strip()] = cols[1].strip()
    return names


def deal_file(file):
    name = file.split(".")[0]
    species = name.split("_")

    blastfile = f"{species[0]}_{species[1]}.blast"
    with open(blastfile) as BLAST:
        genename = [line.split("\t")[0] for line in BLAST]

    # 1. rank of every hit within its query gene (0 for the first hit)
    outfile = f"{species[0]}_{species[1]}.blastp.new.order.m8"
    with open(outfile, "w") as OUT:
        number = -1
        for i, gene in enumerate(genename):
            if i == len(genename) - 1 or gene != genename[i+1]:
                lastnumber = 1 + number
                OUT.write(f"{gene}\t{lastnumber}\n")
                number = -1
            else:
                number += 1

    # 2. add that rank to the Ks table
    with open(f"{species[0]}_{species[1]}.blastp.new.order.m8") as OD, \
         open(f"{species[0]}_{species[1]}_block_rr.ks.new.txt", "w") as OUT:

        hash = {}
        for line in OD:
            line = line.strip()
            array = line.split("\t")
            hash[array[0]] = array[1]

        with open(f"{species[0]}_{species[1]}.ks.txt") as KS:
            for line in KS:
                line = line.strip()
                arr = line.split("\t")
                OUT.write(f"{arr[0]}\t{arr[1]}\t{arr[2]}\t{arr[3]}\t{hash[arr[0]]}\n")

    # 3. insert Ks and rank after every gene pair of the block file
    with open(f"{species[0]}_{species[1]}_block_rr.ks.new.txt") as KS, \
         open(f"{species[0]}_{species[1]}_block_rr.latest.txt", "w") as OUT:

        pair_ks = {}
        pair_order = {}
        for line in KS:
            line = line.strip()
            array = line.split("\t")
            pair = array[0] + "_" + array[1]
            pair_ks[pair] = array[3]
            pair_order[pair] = array[4]

        with open(f"{species[0]}_{species[1]}.block.rr.txt") as CF:
            for line in CF:
                line = line.strip()
                arr = line.split()
                if species[0] not in line:
                    OUT.write(line + "\n")
                    continue

                pair1 = arr[0] + "_" + arr[2]
                OUT.write(line + "\n" + arr[0] + "\t" + arr[2] + "\t1\t" + pair_ks[pair1] + "\t" + pair_order[pair1] + "\n")


def run_dot(file, species_list):
    if not file.endswith("blast"):
        return
    species = file.split(".")[0].split("_")
    with open(f"{species[0]}.lens") as Len1, open(f"{species[1]}.lens") as Len2:
        ch1 = max(
            int("".join(filter(str.isdigit, line.split()[0])))
            for line in Len1
            if line.strip()
        )
        ch2 = max(
            int("".join(filter(str.isdigit, line.split()[0])))
            for line in Len2
            if line.strip()
        )

    A = species_list.get(species[0], species[0])
    B = species_list.get(species[1], species[1])

    Chr1 = "_".join(str(i) for i in range(1, ch1+1))
    Chr2 = "_".join(str(i) for i in range(1, ch2+1))

    # arguments of ks_dotplot.pl: see the usage line printed by the script
    subprocess.run(["perl", KS_DOTPLOT, Chr1, Chr2,
                    f"{species[0]}.new.gff", f"{species[1]}.new.gff",
                    f"{species[0]}_{species[1]}_block_rr.latest.txt",
                    "order", "queryinitial", "sbjctinitial", "1e-10", "8", "10000",
                    KS_CUTOFF, A, B], check=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Draw Ks dot plots for every *.blast file in the current directory.')
    ap.add_argument('--processes', type=int, default=8, help='number of processes [default: 8]')
    ap.add_argument('--names', default=os.path.join(HERE, '..', 'species_names.tsv'),
                    help='tab-separated file: abbreviation <TAB> full species name '
                         '[default: species_names.tsv in the repository root]')
    args = ap.parse_args()
    names = load_names(args.names)
    with Pool(processes=args.processes) as pool:
        pool.map(deal_file, glob.glob("*blast"))
        pool.starmap(run_dot, [(f, names) for f in os.listdir(".")])
