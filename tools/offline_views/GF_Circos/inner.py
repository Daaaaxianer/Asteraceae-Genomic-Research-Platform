import sys
import os

# 确保能找到 func_
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from functools import reduce
from func_ import *


class run_inner():
    def __init__(self,options):
        self.savefig ='savefig'
        self.specieslist = 'chr list'
        self.lens_file = 'lens hmm_model'
        self.gff_file = 'gff hmm_model'
        self.ks_file = 'ks hmm_model'
        self.classifyfile = 'classify hmm_model'
        self.classify_color = '1:blue,2:orange'
        self.ks_interval_color = 'ks interval color'
        self.young_genes_ks = 0.1
        self.young_genes_color = 'red'
        self.axes_limit = 0.5
        self.label_pos = 1.1
        self.dpi = '300'
        for k, v in options:
            setattr(self, str(k), v)
        self.chrolist = [chr.upper() for chr in self.specieslist.split(',')]

        self.fpchrolen = open(self.lens_file,'r')
        self.fpgff = open(self.gff_file,'r')
        self.fpgenefamilyinf = open(self.ks_file,'r')
        self.classify = open(self.classifyfile, 'r')

        figure(1, (8, 8))
        self.root =axes([0, 0, 1, 1])

        self.specieslist,self.iscompletegenome = get_species_and_chr(self.chrolist)

        self.chro2len,self.labels = get_chr_lenth(self.specieslist,self.fpchrolen,self.iscompletegenome)

        self.gene2pos,self.gene2chain,self.gene_labels = input_gff(self.fpgff)

        self.genes,self.genepair2Ks = input_ka_ks(self.fpgenefamilyinf,self.gene_labels)

        self.fullchrolen = reduce(add,list(self.chro2len.values()))

        self.chr_number = len(self.labels)
        GAP = self.fullchrolen/GAP_RATIO/self.chr_number
        self.total_size = self.fullchrolen + self.chr_number * GAP

        self.start_list = [0]*self.chr_number
        for i in range(1, self.chr_number):
            self.start_list[i] = self.start_list[i-1] + self.chro2len[self.labels[i-1]] + GAP
        self.stop_list = [(self.start_list[i] + self.chro2len[self.labels[i]]) for i in range(self.chr_number)]

        self.genessorted = sort_gene(self.genes,self.gene2pos,self.start_list,self.labels,self.gene_labels)
        self.toclassify()

        j = 0
        for start, stop in zip(self.start_list, self.stop_list):
            start, stop = to_radian(start, self.total_size), to_radian(stop, self.total_size)

            plot_arc(start, stop, radius_a)
            plot_arc(start, stop, radius_b)

            plot_cap(start, clockwise=False)
            plot_cap(stop)

            label_x, label_y = rad_to_coord((start+stop)/2, radius_b*float(self.label_pos))
            text(label_x, label_y, self.labels[j], horizontalalignment="center", verticalalignment="center")
            j+=1

        shiftlevel = 0
        gene2shift = {}
        gene2location = {}
        cho = self.gene_labels[self.genessorted[0]]
        pos0 = self.gene2pos[self.genessorted[0]] + self.start_list[self.labels.index(cho)]
        start = to_radian(pos0, self.total_size)
        gene2location[self.genessorted[0]]= start
        gene2shift[self.genessorted[0]] = shiftlevel
        laststart = start

        for i in range(len(self.genessorted)):
            chi = self.gene_labels[self.genessorted[i]]
            posi = self.gene2pos[self.genessorted[i]] + self.start_list[self.labels.index(chi)]
            start = to_radian(posi, self.total_size)
            if start-laststart < blocklength:
                shiftlevel = shiftlevel + 1
            else:
                 shiftlevel=0

            if self.genessorted[i] in self.gene_classify.keys():
                clsnum = self.gene_classify[self.genessorted[i]]
                col =self.classify_col_dit[clsnum]
                plot_arc_block1(start, radius_a - (shiftlevel + 1) * shiftratio * blockthick, col)

            gene2location[self.genessorted[i]] = start
            gene2shift[self.genessorted[i]] = shiftlevel
            laststart = start

        for genepair in self.genepair2Ks.keys():
            gene1, gene2 = genepair.split(' ')
            Ks = self.genepair2Ks[genepair]
            start1 = gene2location[gene1]
            shift1 = gene2shift[gene1]
            start2 = gene2location[gene2]
            shift2 = gene2shift[gene2]

            self.ks_interval(Ks, start1, start2, shift1, shift2)

            if Ks < float(self.young_genes_ks) and Ks >0:
                 color = self.young_genes_color
                 if abs(start1-start2) < 0.002:
                    self.plot_bez_Ks3(start1, radius_a - (shift1+1) * shiftratio * blockthick,
                                      start2, radius_a - (shift2+1) * shiftratio * blockthick, color)

        for i in range(self.chr_number):
           pos = 0
           while pos < self.chro2len[self.labels[i]]:
              xx1, yy1 = self.transform_pt(i, int(pos), radius_b)
              xx2, yy2 = self.transform_pt(i, int(pos), radius_b-0.003)
              plot([xx1, xx2], [yy1, yy2], "k-", lw = .2)
              pos = pos + 10000000

        self.root.set_xlim(-float(self.axes_limit), float(self.axes_limit))
        self.root.set_ylim(-float(self.axes_limit), float(self.axes_limit))
        self.root.set_axis_off()

        savefig(self.savefig,dpi=float(self.dpi))

    def toclassify(self):
        self.gene_classify = {}
        self.classify_col_dit = {}
        for l in self.classify:
            ls = l.strip().split('\t')
            self.gene_classify[ls[0]] = ls[1]
        colors = self.classify_color.split(',')
        for col in colors:
            cols = col.split(':')
            self.classify_col_dit[cols[0]] = cols[1]

    def ks_interval(self,Ks,start1,start2,shift1,shift2):
        intervals = self.ks_interval_color.split(',')
        inters = re.findall('(.*)-(.*):(.*)',intervals[0])[0]
        if Ks >= float(min(inters[0:2])) and Ks < float(max(inters[0:2])):
            color = inters[2]
            if abs(start1 - start2) < 0.005:
                self.plot_bez_Ks2(start1, radius_a - (shift1 + 1) * shiftratio * blockthick,
                                  start2, radius_a - (shift2 + 1) * shiftratio * blockthick, color)
        for i in range(1,len(intervals)):
            inters = re.findall('(.*)-(.*):(.*)', intervals[i])[0]
            if Ks >= float(min(inters[0:2])) and Ks < float(max(inters[0:2])):
                color = inters[2]
                if abs(start1 - start2) < 0.05:
                    self.plot_bez_Ks2(start1, radius_a - (shift1 + 1) * shiftratio * blockthick,
                                      start2, radius_a - (shift2 + 1) * shiftratio * blockthick, color)
    def transform_deg(self,ch, pos):
        return to_deg(pos + self.start_list[ch], self.total_size)

    def transform_pt(self,ch, pos, r):
        rad = to_radian(pos + self.start_list[ch], self.total_size)
        return r * cos(rad), r * sin(rad)

    def transform_pt2(self,rad, r):
        return r * cos(rad), r * sin(rad)

    def plot_bez_Ks(self,rad1, r1, rad2, r2, col):
        ex1x, ex1y = self.transform_pt2(rad1, r1)
        ex2x, ex2y = self.transform_pt2(rad2, r2)
        ratio = 0.5
        x = [ex1x, ex1x * ratio, ex2x * ratio, ex2x]
        y = [ex1y, ex1y * ratio, ex2y * ratio, ex2y]
        step = .01
        t = arange(0, 1 + step, step)
        xt = Bezier(x, t)
        yt = Bezier(y, t)
        plot(xt, yt, '-', color=col, lw=.4)

    def plot_bez_Ks2(self,rad1, r1, rad2, r2, col):
        ex1x, ex1y = self.transform_pt2(rad1, r1)
        ex2x, ex2y = self.transform_pt2(rad2, r2)
        ratio = 0.5
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
        plot(xt, yt, '-', color=col, lw=0.4)

    def plot_bez_Ks3(self,rad1, r1, rad2, r2, col):
        ex1x, ex1y = self.transform_pt2(rad1, r1)
        ex2x, ex2y = self.transform_pt2(rad2, r2)
        ratio = -0.5
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
        plot(xt, yt, '-', color=col, lw=0.4)
