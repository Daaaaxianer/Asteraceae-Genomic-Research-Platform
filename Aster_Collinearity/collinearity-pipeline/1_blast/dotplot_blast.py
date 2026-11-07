#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2021/11/4 12:25
# @Author  : wjq
# @File    : dotplot.nopd.py
# @Software: PyCharm
"""
Genome-wide BLAST / DIAMOND dot plot, one PNG per species pair.

Input (per pair <sp1>_<sp2>):
    <bed>/<sp>.lens, <bed>/<sp>.new.gff   chromosome sizes and gene positions
    <blast>/<sp1>_<sp2>.<suffix>          tabular BLAST / DIAMOND output
Output:
    <out>/<sp1>_<sp2>.png

For every gene the best hit is drawn red, the next hits (up to 5) blue and the
remaining ones white. Hits are filtered by bitscore >= 100 and E-value < 1e-5,
and at most 20 hits per gene are kept.

Example:
    python dotplot_blast.py --bed bed --blast blast --out blast_dot --suffix blast
"""

import argparse
import glob
import os
import re
from functools import reduce
from multiprocessing import Pool
import matplotlib.pyplot as plt


class DotPlot:
    def __init__(self, num_process, suffix, bed_path, blast_path, result_path, name_change):
        self.num_process = num_process
        self.suffix = suffix
        self.name_change = name_change
        self.bed = os.path.join('.', bed_path)
        self.blast_path = os.path.join('.', blast_path)
        self.result_path = os.path.join('.', result_path)

        self.colors = ['red', 'blue', 'white']
        # self.colors = ['orangered', 'blue', 'gray']
        self.hitnum = 5
        self.align = dict(family='Times New Roman', horizontalalignment="center",
                          verticalalignment="center", weight='semibold')

    @staticmethod
    def check_file(file_path):
        n = os.path.isfile(file_path)
        file_name = os.path.basename(file_path)
        if not n:
            print(f'{file_name}---File not exist!!!')

    @staticmethod
    def get_spec_chr(spec_chr):
        spec_chr = re.sub('^\\D+', '', spec_chr)
        spec_chr = re.sub('^0', '', spec_chr)
        return spec_chr

    def gene_location(self, spec, gl):
        len_pos, gff_pos = 1, 6
        chr_dict, chr_lens, loc_gene, n = {}, {}, {}, 0
        self.check_file(f'{self.bed}/{spec}.lens')
        for li in open(f'{self.bed}/{spec}.lens'):
            lis = li.strip().split()
            spec_chr = self.get_spec_chr(lis[0])
            chr_lens[spec_chr] = float(lis[len_pos])
            chr_dict[spec_chr] = float(n)
            n += float(lis[len_pos])
        total_lens = reduce(lambda x, y: int(x) + int(y), chr_lens.values())
        step = gl / total_lens
        self.check_file(f'{self.bed}/{spec}.new.gff')
        for li in open(f'{self.bed}/{spec}.new.gff'):
            lis = li.strip().split()
            spec_chr = self.get_spec_chr(lis[0])
            if spec_chr not in chr_dict:
                continue
            loc = (chr_dict[spec_chr] + float(lis[gff_pos])) * step
            loc_gene[lis[5]] = loc

        return loc_gene, step, chr_lens

    def getnewblast(self, blast, score, evalue, repnum, loc_1, loc_2):
        newblast = {}
        for li in open(blast):
            lis = li.strip().split()
            if not all((float(lis[11]) >= score, float(lis[10]) < evalue, lis[0] != lis[1])):
                continue
            if not all((lis[0] in loc_1, lis[1] in loc_2)):
                continue
            if lis[0] in newblast and lis[1] in newblast[lis[0]]:
                continue
            if lis[0] in newblast and len(newblast[lis[0]]) < repnum:
                newblast[lis[0]].append(lis[1])
            else:
                newblast[lis[0]] = [lis[1]]
        return newblast

    def pair_positon(self, blast, loc1, loc2):
        pos1, pos2, newcolor = [], [], []
        gl_start1, gl_start2 = 11 / 12, 1 / 12
        for k, v in blast.items():
            for i in range(len(v)):
                if i == 0:
                    color = self.colors[0]
                elif i <= self.hitnum:
                    color = self.colors[1]
                else:
                    color = self.colors[2]
                pos1.append(gl_start2 + loc2[v[i]])
                pos2.append(gl_start1 - loc1[k])
                newcolor.append(color)
        return pos1, pos2, newcolor

    def plot_line(self, x, y):
        plt.plot(x, y, linestyle='-', color='black', linewidth=0.25)
        plt.plot(x, y, linestyle='-', color='black', linewidth=0.75, alpha=0.5)

    def plot_chr1(self, lens, gl, gl2, step, mark, name):
        gl_start, n, start_x = 11 / 12, 0, 1 / 12
        mark_y = 17 / 240
        for k in lens.keys():
            n += lens[k]
            mark_new = str(mark) + str(k)
            x = gl_start - float(n) * step
            mark_x = x + 0.5 * lens[k] * step
            self.plot_line([start_x, start_x + gl2], [x, x])
            plt.text(mark_y, mark_x, mark_new, color='black', fontsize=14, rotation=0, **self.align, style='normal')
        self.plot_line([start_x, start_x + gl2], [gl_start, gl_start])
        plt.text(mark_y - 0.03, 0.5 * (2 * gl_start - gl), name, color='black', fontsize=18, rotation=90,
                 **self.align, fontstyle='italic')

    def plot_chr2(self, lens, gl, gl2, step, mark, name):
        gl_start, n, start_x = 1 / 12, 0, 11 / 12
        mark_y = 223 / 240
        for k in lens.keys():
            n += lens[k]
            mark_new = str(mark) + str(k)
            x = gl_start + float(n) * step
            mark_x = x - 0.5 * lens[k] * step
            self.plot_line([x, x], [start_x, start_x - gl2])
            plt.text(mark_x, mark_y, mark_new, color='black', fontsize=14, rotation=0, **self.align, style='normal')
        self.plot_line([gl_start, gl_start], [start_x, start_x - gl2])
        plt.text(0.5 * (2 * gl_start + gl), mark_y + 0.03, name, color='black', fontsize=18, rotation=0,
                 **self.align, fontstyle='italic')

    def plotfig(self, spec1, spec2):
        plt.figure(figsize=(8, 8), dpi=300)
        root = plt.axes([0, 0, 1, 1])
        gl1, gl2 = 5 / 6, 5 / 6
        gene_loc_1, step1, chr1_lens = self.gene_location(spec1, gl1)
        gene_loc_2, step2, chr2_lens = self.gene_location(spec2, gl2)
        self.plot_chr1(chr1_lens, gl1, gl2, step1, '', self.name_change.get(spec1, spec1))
        self.plot_chr2(chr2_lens, gl1, gl2, step2, '', self.name_change.get(spec2, spec2))
        score, evalue, repnum = 100, 1e-5, 20
        blast = f'{self.blast_path}/{spec1}_{spec2}.{self.suffix}'
        blast = self.getnewblast(blast, score, evalue, repnum, gene_loc_1, gene_loc_2)
        x, y, colors = self.pair_positon(blast, gene_loc_1, gene_loc_2)
        plt.scatter(x, y, s=0.5, c=colors, alpha=0.5, edgecolors=None, linewidths=0, marker='o')
        root.set_xlim(0, 1)
        root.set_ylim(0, 1)
        root.set_axis_off()
        plt.savefig(f'{self.result_path}/{spec1}_{spec2}.png')
        # plt.savefig(f'{self.result_path}/{spec1}_{spec2}.pdf')

    def main(self):
        p = Pool(self.num_process)
        blasts = glob.glob(f'{self.blast_path}/*.{self.suffix}')
        jobs = []
        for file in blasts:
            fna = os.path.basename(file)
            spec1, spec2 = fna.split('.')[0].split('_')
            jobs.append(p.apply_async(self.plotfig, args=(spec1, spec2)))

        p.close()
        p.join()
        for job in jobs:
            job.get()  # re-raise errors from the workers instead of failing silently


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


if __name__ == '__main__':
    default_names = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'species_names.tsv')
    ap = argparse.ArgumentParser(description='Draw genome-wide BLAST dot plots (one PNG per BLAST file).')
    ap.add_argument('--bed', required=True, help='directory with {sp}.lens and {sp}.new.gff')
    ap.add_argument('--blast', required=True, help='directory with {sp1}_{sp2}.<suffix> files')
    ap.add_argument('--out', required=True, help='output directory')
    ap.add_argument('--suffix', default='blast', help='BLAST file suffix, "blast" or "diamond" [default: blast]')
    ap.add_argument('--processes', type=int, default=1, help='number of processes [default: 1]')
    ap.add_argument('--names', default=default_names,
                    help='tab-separated file: abbreviation <TAB> full species name '
                         '[default: species_names.tsv in the repository root]; '
                         'species that are not listed are labelled with their abbreviation')
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    DotPlot(args.processes, args.suffix, args.bed, args.blast, args.out, load_names(args.names)).main()
