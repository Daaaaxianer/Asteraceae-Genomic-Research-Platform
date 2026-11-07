#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2021/10/26 19:46
# @Author  : wjq
# @File    : dotplot_block.py
# @Software: PyCharm
"""
Dot plot of the collinear blocks, one PNG per species pair.

Input (per pair <sp1>_<sp2>):
    <bed>/<sp>.lens, <bed>/<sp>.new.gff        chromosome sizes and gene positions
    <data>/<sp1>_<sp2>.<suffix>                BLAST / DIAMOND output
    <data>/<sp1>_<sp2>.block.rr.txt            ColinearScan blocks (run_colinearscan.py)
Output:
    <out>/<sp1>_<sp2>.<min_genes>.2400.png

Only blocks with at least --min-genes gene pairs are drawn. Gene pairs that are the
best hit of a gene are orange-red, the other hits gray.

Example:
    python dotplot_block.py --bed bed --data block_blast --out dot --min-genes 10
"""

import argparse
import re
import os
import glob
from functools import reduce
from multiprocessing import Pool


import matplotlib.pyplot as plt



class DotplotBlock:
    def __init__(self, num_process, suffix, block_num, bed_path, block_blast_path, result_path, name_change):
        self.num_process = num_process
        self.suffix = suffix
        self.block_num = block_num
        self.name_change = name_change
        self.bed = os.path.join('.', bed_path)
        self.block_blast_path = os.path.join('.', block_blast_path)
        self.result_path = os.path.join('.', result_path)


        self.colors = ['orangered', 'gray']
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
        total_lens = reduce(lambda x, y: int(x)+int(y), chr_lens.values())
        step = gl/total_lens
        self.check_file(f'{self.bed}/{spec}.new.gff')
        for li in open(f'{self.bed}/{spec}.new.gff'):
            lis = li.strip().split()
            spec_chr = self.get_spec_chr(lis[0])
            if spec_chr not in chr_dict:
                continue
            loc = (chr_dict[spec_chr] + float(lis[gff_pos]))*step
            loc_gene[lis[5]] = loc

        return loc_gene, step, chr_lens

    def select_blast(self, blast_path, block_path):
        gene_pair_list, pair_pos, last_na1, last_na2, result_pair, num = [], {}, '', '', [], 1
        gene_dit = self.get_block(block_path)
        for li in open(blast_path):
            lis = li.strip().split()
            if 'Scaffold' in li or lis[0] == lis[1]:
                continue
            if lis[0] in gene_dit and lis[1] in gene_dit[lis[0]]:
                gene_pair_list.append(f'{lis[0]}\t{lis[1]}')
            if last_na1 == lis[0] and last_na2 != lis[1]:
                num += 1
            else:
                num = 1
            pair_pos[f'{lis[0]}\t{lis[1]}'] = str(num)
            last_na1, last_na2 = lis[0], lis[1]

        for pair in gene_pair_list:
            if pair in pair_pos:
                row = pair.split('\t')
                row.append(pair_pos[pair])
                result_pair.append(row)

        return result_pair

    def get_block(self, path):
        gene_dit = {}
        block, blocks = [], []
        for li in open(path):
            li = li.strip()
            if '>' in li:
                if len(block) >= self.block_num:
                    for row in block:
                        rows = re.split('\\s', row)
                        if rows[0] in gene_dit:
                            gene_dit[rows[0]].append(rows[2])
                        else:
                            gene_dit[rows[0]] = [rows[2]]
                    # blocks.append(block)
                block = []
            elif any(([x in li for x in ['overlap', 'LOCALE',
                                         'self', 'the', '>']])):
                continue
            elif li:
                block.append(li)

        return gene_dit

    def plot_line(self, x, y):
        plt.plot(x, y, linestyle='-', color='black', linewidth=0.25)
        plt.plot(x, y, linestyle='-', color='black', linewidth=0.75, alpha=0.5)

    def plot_chr1(self, lens, gl, gl2, step, mark, name):
        gl_start, n, start_x = 11/12, 0, 1/12
        mark_y = 17/240
        for k in lens.keys():
            n += lens[k]
            mark_new = str(mark) + str(k)
            x = gl_start - float(n) * step
            mark_x = x + 0.5 * lens[k] * step
            self.plot_line([start_x, start_x + gl2], [x, x])
            plt.text(mark_y-0.01, mark_x, mark_new, color='black', fontsize=15, rotation=0, **self.align, style='normal')
        self.plot_line([start_x, start_x + gl2], [gl_start, gl_start])
        plt.text(mark_y - 0.04, 0.5 * (2 * gl_start - gl), name, color='black', fontsize=20, rotation=90,
                 **self.align, fontstyle='italic')

    def plot_chr2(self, lens, gl, gl2, step, mark, name):
        gl_start, n, start_x = 1/12, 0, 11/12
        mark_y = 223/240
        for k in lens.keys():
            n += lens[k]
            mark_new = str(mark) + str(k)
            x = gl_start + float(n) * step
            mark_x = x - 0.5 * lens[k] * step
            self.plot_line([x, x], [start_x, start_x - gl2])
            plt.text(mark_x, mark_y+0.01, mark_new, color='black', fontsize=15, rotation=0, **self.align, style='normal')
        self.plot_line([gl_start, gl_start], [start_x, start_x - gl2])
        plt.text(0.5 * (2 * gl_start + gl), mark_y + 0.04, name, color='black', fontsize=20, rotation=0,
                 **self.align, fontstyle='italic')

    def getnewblast(self, blast, loc_1, loc_2):
        newblast = []
        for lis in blast:
            if not all((lis[0] in loc_1, lis[1] in loc_2)):
                continue
            newblast.append(lis)
        return newblast

    def pair_positon(self, data, loc1, loc2, colors):
        pos1, pos2, newcolor = [], [], []
        gl_start1, gl_start2 = 11 / 12, 1 / 12
        for row in data:
            x = gl_start1 - loc1[row[0]]
            y = gl_start2 + loc2[row[1]]
            pos1.append(y)
            pos2.append(x)
            if row[2] == '1':
                color = colors[0]
            else:
                color = colors[1]

            newcolor.append(color)
        return pos1, pos2, newcolor

    def pair_positon1(self, data, loc1, loc2, colors):
        pos1, pos2, newcolor = [], [], []
        pos11, pos21, newcolor1 = [], [], []
        gl_start1, gl_start2 = 11 / 12, 1 / 12
        for row in data:
            x = gl_start1 - loc1[row[0]]
            y = gl_start2 + loc2[row[1]]

            if row[2] == '1':
                color = colors[0]
                pos1.append(y)
                pos2.append(x)
                newcolor.append(color)
            elif row[2] == '2':
                color = colors[1]
                pos11.append(y)
                pos21.append(x)
                newcolor1.append(color)

        return pos1, pos2, newcolor, pos11, pos21, newcolor1


    def pair_positon2(self, data, loc1, loc2, colors):
        pos1, pos2, newcolor = [], [], []
        gl_start1, gl_start2 = 11 / 12, 1 / 12
        for row in data:
            x = gl_start1 - loc1[row[0]]
            y = gl_start2 + loc2[row[1]]

            if row[2] == '1':
                color = colors[0]
                pos1.append(y)
                pos2.append(x)
                newcolor.append(color)
            elif row[2] == '2':
                color = colors[1]
                pos1.append(y)
                pos2.append(x)
                newcolor.append(color)

        return pos1, pos2, newcolor

    def plotfig(self, spec1, spec2):
        plt.figure(figsize=(8, 8), dpi=300)
        root = plt.axes([0, 0, 1, 1])
        gl1, gl2 = 5/6, 5/6
        gene_loc_1, step1, lens_1 = self.gene_location(spec1, gl1)
        gene_loc_2, step2, lens_2 = self.gene_location(spec2, gl2)
        self.plot_chr1(lens_1, gl1, gl2, step1, '', self.name_change.get(spec1, spec1))
        self.plot_chr2(lens_2, gl1, gl2, step2, '', self.name_change.get(spec2, spec2))
        blast = self.select_blast(f'{self.block_blast_path}/{spec1}_{spec2}.{self.suffix}',
                                  f'{self.block_blast_path}/{spec1}_{spec2}.block.rr.txt')
        blast = self.getnewblast(blast, gene_loc_1, gene_loc_2)
        # x, y, colors, x1, y1, colors1 = self.pair_positon1(blast, gene_loc_1, gene_loc_2, self.colors)
        x, y, colors = self.pair_positon2(blast, gene_loc_1, gene_loc_2, self.colors)
        # plt.scatter(x1, y1, s=0.3+0.6, c=colors1, alpha=1, edgecolors=None, linewidths=0)
        plt.scatter(x, y, s=0.3+0.6, c=colors, alpha=1, edgecolors=None, linewidths=0)
        root.set_xlim(0, 1)
        root.set_ylim(0, 1)
        root.set_axis_off()
        plt.savefig(f'{self.result_path}/{spec1}_{spec2}.{self.block_num}.2400.png')
        # plt.savefig(f'{self.result_path}/{spec1}_{spec2}.{self.block_num}.2400.pdf')

    def main(self):
        p = Pool(self.num_process)
        blasts = glob.glob(f'{self.block_blast_path}/*.{self.suffix}')
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
    ap = argparse.ArgumentParser(description='Dot plot of ColinearScan blocks (one PNG per species pair).')
    ap.add_argument('--bed', required=True, help='directory with {sp}.lens and {sp}.new.gff')
    ap.add_argument('--data', required=True,
                    help='directory with {sp1}_{sp2}.<suffix> and {sp1}_{sp2}.block.rr.txt')
    ap.add_argument('--out', required=True, help='output directory')
    ap.add_argument('--suffix', default='blast', help='BLAST file suffix [default: blast]')
    ap.add_argument('--min-genes', type=int, default=10,
                    help='draw only blocks with at least this many gene pairs [default: 10]')
    ap.add_argument('--processes', type=int, default=1, help='number of processes [default: 1]')
    ap.add_argument('--names', default=default_names,
                    help='tab-separated file: abbreviation <TAB> full species name '
                         '[default: species_names.tsv in the repository root]')
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    DotplotBlock(args.processes, args.suffix, args.min_genes, args.bed, args.data, args.out,
                 load_names(args.names)).main()
