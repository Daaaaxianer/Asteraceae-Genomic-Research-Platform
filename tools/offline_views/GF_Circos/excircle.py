#!/usr/bin/env python
# -*- coding:utf-8 -*-

import sys
import os
import traceback
from operator import add  # 用于 reduce(add, ...)
from math import atan, pi, sin, cos, sqrt  # 【关键修复】引入数学函数
from numpy import arange # 用于贝塞尔曲线计算
from matplotlib.pyplot import * # 用于绘图函数 figure, plot, text 等

# 确保能找到 func_
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from functools import reduce

try:
    from func_ import *
except ImportError:
    # 尝试相对导入
    from .func_ import *

class run_excircle():
    def __init__(self, options):
        # 1. 设置默认参数 (防止 Config 文件缺少某些字段导致报错)
        self.defaults = {
            'savefig': 'result.png',
            'specieslist': '',
            'lens_file': '',
            'gff_file': '',
            'ks_file': '',
            'pair_file': '',
            'classifyfile': '',
            'classify_color': '1:blue,2:orange',
            'young_genes_ks': 0.1,
            'young_genes_color': 'red',
            'axes_limit': 0.9,
            'alpha': 0.7,
            'line_color': '#dcdcdd',
            'label_pos': 0.85,
            'dpi': 300,
            'min_ks': "0;0.5;1;1.5;2",
            'max_ks': 100  # 默认一个较大的值，不做限制
        }

        # 2. 先加载默认值，再加载传入的配置
        for k, v in self.defaults.items():
            setattr(self, k, v)
        
        for k, v in options:
            setattr(self, str(k), v)

        # 3. 类型转换与数据预处理
        self.min_ks = str(self.min_ks)
        self.label_pos = float(self.label_pos)
        self.dpi = float(self.dpi)
        self.axes_limit = float(self.axes_limit)
        
        # 解析 Ks 区间
        try:
            self.min_ks_list = list(map(float, self.min_ks.split(';')))
        except ValueError:
            print("Warning: Invalid min_ks format, using default.")
            self.min_ks_list = [0, 0.5, 1, 1.5, 2]

        self.chrolist = [chr for chr in self.specieslist.split(',')]

        # 4. 打开文件资源
        self.fpchrolen = open(self.lens_file, 'r')
        self.fpgff = open(self.gff_file, 'r')
        self.fpgenefamilyinf = open(self.ks_file, 'r')
        self.alphagenepairs = open(self.pair_file, 'r')
        self.classify = open(self.classifyfile, 'r')
        
        blockthick = 0.006
        shiftratio = -2.1  # 保持原代码参数

        # 5. 初始化绘图
        figure(figsize=(12, 12))
        self.root = axes([0, 0, 1, 1])

        # 读取数据
        self.specieslist, self.iscompletegenome = get_species_and_chr(self.chrolist)
        self.chro2len, self.labels = get_chr_lenth(self.specieslist, self.fpchrolen, self.iscompletegenome)
        self.gene2pos, self.gene2chain, self.gene_labels = input_gff(self.fpgff)
        self.genes, self.genepair2Ks = input_ka_ks(self.fpgenefamilyinf, self.gene_labels)

        # 计算圆周参数
        self.fullchrolen = reduce(add, list(self.chro2len.values()))
        chr_number = len(self.labels)
        if chr_number == 0:
            print("Error: No chromosomes found in lens file.")
            return

        # 假设 GAP_RATIO 在 func_ 中定义，如果没有则给个默认值
        try:
            GAP = self.fullchrolen / GAP_RATIO / chr_number
        except NameError:
             GAP = self.fullchrolen / 50 / chr_number

        self.total_size = self.fullchrolen + chr_number * GAP

        self.start_list = [0] * chr_number
        for i in range(1, chr_number):
            self.start_list[i] = self.start_list[i-1] + self.chro2len[self.labels[i-1]] + GAP
        self.stop_list = [(self.start_list[i] + self.chro2len[self.labels[i]]) for i in range(chr_number)]

        self.genessorted = sort_gene(self.genes, self.gene2pos, self.start_list, self.labels, self.gene_labels)
        self.toclassify()

        # 确保 radius_a 和 radius_b 存在
        # 这些变量通常在 func_ 中定义为全局变量，如果报错请在此处手动定义
        # radius_a = 0.8
        # radius_b = 0.85

        # ---------------------------------------------------------
        # 第一层绘图：绘制背景灰色连线 (Pair file)
        # ---------------------------------------------------------
        for row in self.alphagenepairs:
            parts = row.split()
            if len(parts) < 3: continue
            id1, id2, ks1 = parts[0], parts[1], parts[2]
            try:
                Ks1 = float(ks1)
                if id1 not in self.gene2pos or id2 not in self.gene2pos: continue
                
                pos1 = self.gene2pos[id1]
                pos2 = self.gene2pos[id2]
                chro1 = self.gene_labels[id1]
                chro2 = self.gene_labels[id2]
                
                if chro1 not in self.labels or chro2 not in self.labels: continue

                order1 = self.labels.index(chro1)
                order2 = self.labels.index(chro2)

                if 0 < Ks1 <= 2:
                    self.plot_bez_inner((order1, pos1, radius_a), (order2, pos2, radius_a), self.line_color)
            except Exception:
                pass
        self.alphagenepairs.close()

        # ---------------------------------------------------------
        # 第二层绘图：绘制染色体骨架和标签
        # ---------------------------------------------------------
        j = 0
        for start, stop in zip(self.start_list, self.stop_list):
            start_rad, stop_rad = to_radian(start, self.total_size), to_radian(stop, self.total_size)
            plot_arc(start_rad, stop_rad, radius_a)
            plot_arc(start_rad, stop_rad, radius_b)
            plot_cap(start_rad, clockwise=False)
            plot_cap(stop_rad)

            label_x, label_y = rad_to_coord((start_rad + stop_rad) / 2, radius_b * float(self.label_pos))
            text(label_x, label_y, self.labels[j], horizontalalignment="center", verticalalignment="center", fontsize=14, color='black')
            j += 1

        # ---------------------------------------------------------
        # 第三层绘图：绘制基因位置色块 (方块)
        # ---------------------------------------------------------
        shiftlevel = 0
        gene2shift = {}
        gene2location = {}

        # 确保 blocklength 存在
        try:
             _ = blocklength
        except NameError:
             blocklength = 0.01 # 默认值防止报错

        if self.genessorted:
            # 初始化
            cho = self.gene_labels[self.genessorted[0]]
            pos0 = self.gene2pos[self.genessorted[0]] + self.start_list[self.labels.index(cho)]
            start = to_radian(pos0, self.total_size)
            gene2location[self.genessorted[0]] = start
            gene2shift[self.genessorted[0]] = shiftlevel
            laststart = start

            for i in range(len(self.genessorted)):
                gene = self.genessorted[i]
                chi = self.gene_labels[gene]
                posi = self.gene2pos[gene] + self.start_list[self.labels.index(chi)]
                start = to_radian(posi, self.total_size)
                
                if start - laststart < blocklength:
                    shiftlevel += 1
                else:
                    shiftlevel = 0
                
                # 绘制 Classify 颜色
                if gene in self.gene_classify:
                    clsnum = self.gene_classify[gene]
                    if '-' in clsnum:
                        c1, c2 = clsnum.split('-')
                        col1 = self.classify_col_dit.get(c1, 'gray')
                        col2 = self.classify_col_dit.get(c2, 'gray')
                        plot_arc_block1(start, radius_a - (shiftlevel + 1) * shiftratio * blockthick, col1)
                        plot_arc_block2(start, radius_a - (shiftlevel + 1) * shiftratio * blockthick, col2)
                    else:
                        col = self.classify_col_dit.get(clsnum, 'gray')
                        plot_arc_block1(start, radius_a - (shiftlevel + 1) * shiftratio * blockthick, col)
                
                gene2location[gene] = start
                gene2shift[gene] = shiftlevel
                laststart = start

        # ---------------------------------------------------------
        # 第四层绘图：绘制彩色 Ks 连线 (通用逻辑核心)
        # ---------------------------------------------------------
        # 定义通用调色盘
        palette = ["#e6ab02", "#1f78b4", "#988dd6", "#D02724", "#e31a1c", "#fdbf6f", "#ff7f00", "#cab2d6", "#6a3d9a", "#b15928"]
        num_ranges = len(self.min_ks_list)

        for genepair in self.genepair2Ks.keys():
            gene1, gene2 = genepair.split(' ')
            if gene1 not in gene2location or gene2 not in gene2location: continue

            Ks = self.genepair2Ks[genepair]
            start1 = gene2location[gene1]
            shift1 = gene2shift[gene1]
            start2 = gene2location[gene2]
            shift2 = gene2shift[gene2]
            a_pos = self.gene2pos[gene1]
            b_pos = self.gene2pos[gene2]

            # 核心修改：根据 min_ks_list 自动分配颜色，不再依赖硬编码的物种名
            color = None
            for i in range(num_ranges - 1):
                lower_bound = self.min_ks_list[i]
                upper_bound = self.min_ks_list[i + 1]
                
                if lower_bound < Ks <= upper_bound:
                    # 循环使用颜色，防止索引越界
                    color = palette[i % len(palette)]
                    break
            
            # 如果匹配到了颜色，且 Ks > 0
            if color and Ks > 0:
                # 绘制条件判断
                if abs(start1 - start2) < float(self.max_ks):
                     if abs(b_pos - a_pos) < 500000: # cluster 阈值
                        self.plot_bez_Ks6(
                            start1, radius_a - (shift1 + 1) * shiftratio * blockthick, 
                            start2, radius_a - (shift2 + 1) * shiftratio * blockthick, 
                            color
                        )

        # ---------------------------------------------------------
        # 第五层绘图：绘制刻度线
        # ---------------------------------------------------------
        for i in range(chr_number):
            pos = 0
            while pos < self.chro2len[self.labels[i]]:
                xx1, yy1 = self.transform_pt(i, int(pos), radius_b)
                xx2, yy2 = self.transform_pt(i, int(pos), radius_b - 0.003)
                plot([xx1, xx2], [yy1, yy2], "k-", lw=.2)
                pos = pos + 10000000

        # 设置坐标轴并保存
        self.root.set_xlim(-float(self.axes_limit), float(self.axes_limit))
        self.root.set_ylim(-float(self.axes_limit), float(self.axes_limit))
        self.root.set_axis_off()
        savefig(self.savefig, dpi=float(self.dpi))

    # ---------------------------------------------------------
    # 辅助函数保持原样
    # ---------------------------------------------------------
    def toclassify(self):
        self.gene_classify = {}
        self.classify_col_dit = {}
        for l in self.classify:
            ls = l.strip().split('\t')
            if len(ls) >= 2:
                self.gene_classify[ls[0]] = ls[1]
        colors = self.classify_color.split(',')
        for col in colors:
            if ':' in col:
                cols = col.split(':')
                self.classify_col_dit[cols[0]] = cols[1]

    def transform_deg(self, ch, pos):
        return to_deg(pos + self.start_list[ch], self.total_size)

    def transform_pt(self, ch, pos, r):
        rad = to_radian(pos + self.start_list[ch], self.total_size)
        return r * cos(rad), r * sin(rad)

    def transform_pt2(self, rad, r):
        return r * cos(rad), r * sin(rad)

    def plot_bez_inner(self, p1, p2, cl):
        a, b, c = p1
        ex1x, ex1y = self.transform_pt(a, b, c)
        a, b, c = p2
        ex2x, ex2y = self.transform_pt(a, b, c)
        ratio = .5
        x = [ex1x, ex1x * ratio, ex2x * ratio, ex2x]
        y = [ex1y, ex1y * ratio, ex2y * ratio, ex2y]
        step = .01
        t = arange(0, 1 + step, step)
        xt = Bezier(x, t)
        yt = Bezier(y, t)
        plot(xt, yt, '-', color=cl, lw=.4, alpha=float(self.alpha))

    def plot_bez_Ks2(self, rad1, r1, rad2, r2, col):
        self._plot_bez_generic(rad1, r1, rad2, r2, col, ratio=-0.7, lw=0.4)

    def plot_bez_Ks3(self, rad1, r1, rad2, r2, col):
        self._plot_bez_generic(rad1, r1, rad2, r2, col, ratio=0.5, lw=0.4)

    def plot_bez_Ks4(self, rad1, r1, rad2, r2, col):
        self._plot_bez_generic(rad1, r1, rad2, r2, col, ratio=-0.5, lw=0.4)

    def plot_bez_Ks5(self, rad1, r1, rad2, r2, col):
        self._plot_bez_generic(rad1, r1, rad2, r2, col, ratio=0.4, lw=0.4)

    def plot_bez_Ks6(self, rad1, r1, rad2, r2, col):
        self._plot_bez_generic(rad1, r1, rad2, r2, col, ratio=0.6, lw=0.6)

    def _plot_bez_generic(self, rad1, r1, rad2, r2, col, ratio, lw):
        ex1x, ex1y = self.transform_pt2(rad1, r1)
        ex2x, ex2y = self.transform_pt2(rad2, r2)
        sita = pi / 2
        if ex1x != ex2x:
            sita = atan((ex2y - ex1y) / (ex2x - ex1x))
        d = sqrt((ex2x - ex1x) ** 2 + (ex2y - ex1y) ** 2)
        L = d * ratio
        P1x = ex1x + L * sin(sita)
        P1y = ex1y - L * cos(sita)
        P2x = ex2x + L * sin(sita)
        P2y = ex2y - L * cos(sita)
        step = .01
        t = arange(0, 1 + step, step)
        x = [ex1x, P1x, P2x, ex2x]
        y = [ex1y, P1y, P2y, ex2y]
        xt = Bezier(x, t)
        yt = Bezier(y, t)
        plot(xt, yt, '-', color=col, lw=lw)